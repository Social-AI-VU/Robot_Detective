"""Project-local runtime patches for nardial behavior.

These overrides keep episode behavior stable even if the installed package is updated.
"""

import asyncio
from os import environ
import base64
import re
import websockets
from json import loads, dumps

from nardial.conversation_agent import ConversationAgent
from nardial.mini_dialogs import MiniDialog
from nardial.tts_manager import ElevenLabsTTSConf, ElevenLabsTTS


_PATCH_APPLIED = False

# ---------------------------------------------------------------------------
# Character voice registry
# Maps character key → ElevenLabs voice_id string.
# Populated by register_character_voices() before the session starts.
# ---------------------------------------------------------------------------
CHARACTER_VOICE_MAP: dict = {}

# ---------------------------------------------------------------------------
# Character TTS pool
# Maps voice_id → pre-connected ElevenLabsTTS instance.
# Built lazily by _get_or_create_tts() on first use of each voice.
# ---------------------------------------------------------------------------
_TTS_POOL: dict = {}          # voice_id → ElevenLabsTTS
_TTS_POOL_ORCH = None         # reference to the InteractionOrchestrator


def register_character_voices(characters: dict) -> None:
    """Register character → voice_id from a dialog's characters block.

    Accepts ``dialog["characters"]``:
    ``{ "robin": { "voice_settings": { "voice_id": "..." } }, ... }``
    """
    for char_key, char_conf in (characters or {}).items():
        voice_id = (char_conf.get("voice_settings") or {}).get("voice_id")
        if voice_id and not voice_id.startswith("REPLACE_WITH"):
            CHARACTER_VOICE_MAP[char_key] = voice_id


def _get_or_create_tts(voice_id: str, orch) -> "ElevenLabsTTS | None":
    """Return a pre-connected ElevenLabsTTS for *voice_id*, creating it if needed."""
    global _TTS_POOL, _TTS_POOL_ORCH
    _TTS_POOL_ORCH = orch

    if voice_id in _TTS_POOL:
        tts = _TTS_POOL[voice_id]
        # Ping to ensure the connection is still alive; reconnect if not.
        try:
            alive = asyncio.run_coroutine_threadsafe(
                tts.ping_connection(), orch.background_loop
            ).result(timeout=4)
        except Exception:
            alive = False
        if not alive:
            try:
                asyncio.run_coroutine_threadsafe(
                    tts.connect(), orch.background_loop
                ).result(timeout=8)
            except Exception as e:
                print(f"[voice-pool] Reconnect failed for {voice_id}: {e}")
                return None
        return tts

    # Create and connect a brand-new TTS client for this voice.
    api_key = environ.get("ELEVENLABS_API_KEY", "")
    tts = ElevenLabsTTS(
        elevenlabs_key=api_key,
        voice_id=voice_id,
        model_id=orch.tts_conf.model_id,
        sample_rate=getattr(orch, "sample_rate", 22050),
        speaking_rate=orch.tts_conf.speaking_rate,
    )
    try:
        asyncio.run_coroutine_threadsafe(
            tts.connect(), orch.background_loop
        ).result(timeout=8)
        _TTS_POOL[voice_id] = tts
        print(f"[voice-pool] Pre-connected voice {voice_id}")
        return tts
    except Exception as e:
        print(f"[voice-pool] Could not connect voice {voice_id}: {e}")
        return None


def preconnect_all_character_voices(orch) -> None:
    """Pre-connect a WebSocket for every registered character voice.

    Call this once after the InteractionOrchestrator is initialized but before
    the session starts, so voice switches are instant (no reconnect latency).
    """
    default_voice = orch.tts_conf.voice_id
    voice_ids = set(CHARACTER_VOICE_MAP.values())
    voice_ids.discard(default_voice)   # default already connected

    for vid in sorted(voice_ids):
        _get_or_create_tts(vid, orch)

    print(f"[voice-pool] Pool ready: {len(_TTS_POOL)} character voice(s) + 1 default")


def apply_nardial_overrides() -> None:
    """Apply runtime monkey patches used by Robot Detective episodes."""
    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        return

    # ── ask_yesno keyboard fallback ─────────────────────────────────────────
    original_ask_yesno = ConversationAgent.ask_yesno

    def ask_yesno_with_text_fallback(self, question, max_attempts=1):
        attempts = 0
        while attempts < max_attempts:
            self.say(question)
            reply, intent = self.orchestrator.listen()

            if intent:
                print(f"context: answer_yesno, recognized_intent: {str(intent)}")
                if intent == "yesno_yes":
                    return "yes"
                if intent == "yesno_no":
                    return "no"
                if intent == "yesno_dontknow":
                    return "dontknow"

            if reply:
                normalized = str(reply).strip().lower()
                yes_values = {
                    "yes", "y", "yeah", "yep", "sure", "ok", "okay",
                    "ja", "jazeker", "zeker", "jawel",
                }
                no_values = {"no", "n", "nope", "nee", "neen"}
                dontknow_values = {
                    "dontknow", "don't know", "do not know", "idk", "not sure",
                    "weet niet", "ik weet het niet", "geen idee", "misschien",
                }
                if normalized in yes_values:
                    return "yes"
                if normalized in no_values:
                    return "no"
                if normalized in dontknow_values:
                    return "dontknow"

            attempts += 1
        return None

    ConversationAgent.ask_yesno = ask_yesno_with_text_fallback
    ConversationAgent._robot_detective_original_ask_yesno = original_ask_yesno

    # ── Character voice switching — pool-based, no per-line reconnect ────────
    # For each say move with a "character" field:
    #   1. Look up (or lazily create) a pre-connected ElevenLabsTTS for that voice.
    #   2. Swap orch.tts to the character's client and update tts_conf.voice_id
    #      (so the cache key matches).
    #   3. Speak.
    #   4. Swap back to the default TTS client.
    # No WebSocket reconnect happens mid-session — all sockets stay open.

    original_handle_move_say = MiniDialog.handle_move_say

    def handle_move_say_with_character(self, move):
        character = move.get("character") if isinstance(move, dict) else None
        target_voice_id = CHARACTER_VOICE_MAP.get(character) if character else None

        orch = self.conversation_agent.orchestrator if self.conversation_agent else None
        default_tts = None
        default_voice_id = None
        swapped = False
        prev_char = getattr(orch, "_rd_current_character", None) if orch is not None else None

        if target_voice_id and orch and isinstance(getattr(orch, "tts_conf", None), ElevenLabsTTSConf):
            default_voice_id = orch.tts_conf.voice_id
            if target_voice_id != default_voice_id:
                char_tts = _get_or_create_tts(target_voice_id, orch)
                if char_tts is not None:
                    default_tts = orch.tts
                    orch.tts = char_tts
                    orch.tts_conf.voice_id = target_voice_id
                    swapped = True
                    print(f"[voice] {character} → {target_voice_id}")
                else:
                    print(f"[voice] WARNING: no TTS for '{character}' ({target_voice_id}), using default.")

        # Expose active character for pacing logic in elevenlabs_say_safe.
        if orch is not None:
            orch._rd_current_character = character

        # Speak (via the now-active orch.tts)
        try:
            original_handle_move_say(self, move)
        except TypeError as e:
            # Guard against None audio_bytes from a broken voice connection
            print(f"[voice] TTS error for '{character}': {e} — skipping line.")
        finally:
            if orch is not None:
                orch._rd_current_character = prev_char

        # Restore default TTS client
        if swapped and default_tts is not None and orch is not None:
            orch.tts = default_tts
            orch.tts_conf.voice_id = default_voice_id

    MiniDialog.handle_move_say = handle_move_say_with_character
    MiniDialog._robot_detective_original_handle_move_say = original_handle_move_say

    # ── Guard: None audio bytes must not crash the WAV writer ───────────────
    from nardial.interaction_orchestrator import InteractionOrchestrator
    from sic_framework.core.message_python2 import AudioRequest as _AudioRequest
    from time import sleep as _sleep

    original_elevenlabs_generate_chunk_audio = InteractionOrchestrator.elevenlabs_generate_chunk_audio
    original_elevenlabs_say = InteractionOrchestrator.elevenlabs_say

    def elevenlabs_generate_chunk_audio_safe(self, text, amplified=False):
        # Keep the original cache key behavior, but never let None audio reach
        # the WAV writer or speaker request path.
        tts_key = self.tts_cacher.make_tts_key(text, self.tts_conf)

        audio_bytes = asyncio.run_coroutine_threadsafe(
            self.tts.speak(text), self.background_loop
        ).result()

        if not audio_bytes:
            self.logger.warning(f"[TTS] No audio returned for {text!r}")
            return None

        if amplified:
            audio_bytes = self._amplify_audio(audio_bytes)

        self.tts_cacher.save_audio_file(tts_key, audio_bytes, self.sample_rate)
        return audio_bytes

    def elevenlabs_say_safe(self, text, post_speech_delay=None, amplified=False,
                            always_regenerate=False, chunking=True):
        # Choppiness fix: keep each line as a single synthesis request.
        # Splitting into short chunks introduces audible seams for some voices.
        text_chunks = [text]

        # If earlier runs cached truncated clips, replaying cache will preserve
        # the truncation forever. Default to cache OFF for ElevenLabs until
        # playback is stable. Set ELEVENLABS_USE_CACHE=1 to re-enable.
        use_cache = environ.get("ELEVENLABS_USE_CACHE", "0") == "1"

        for chunk in text_chunks:
            tts_key = self.tts_cacher.make_tts_key(chunk, self.tts_conf)

            if use_cache and (not always_regenerate):
                audio_file = self.tts_cacher.load_audio_file(tts_key)
                if audio_file:
                    self.log_utterance(speaker='robot', text=f'{chunk} (cache)')
                    self.play_audio(audio_file, log=False)
                    continue

            audio_bytes = self.elevenlabs_generate_chunk_audio(chunk, amplified)
            if audio_bytes is None:
                print(f"[TTS] No audio for chunk: {chunk!r:.80} — skipping.")
                continue

            self.speaker.request(_AudioRequest(audio_bytes, self.sample_rate))
            self.log_utterance(speaker='robot', text=chunk)
            if use_cache:
                self.tts_cacher.save_audio_file(tts_key, audio_bytes, self.sample_rate)

            # Block until playback is done.
            # PCM: 16-bit mono → 2 bytes per sample.
            duration_s = len(audio_bytes) / (self.sample_rate * 2)
            current_char = getattr(self, "_rd_current_character", None)
            # Minimal tail for natural pacing; adaptive tail handles inter-sentence timing.
            tail_s = 0.02 if current_char in {"robin", "yoyo"} else 0.01
            _sleep(duration_s + tail_s)

            # The base config has post_speech_delay=0.5, which is too large once
            # we already wait for real audio duration. Cap it to a tiny value.
            if post_speech_delay and post_speech_delay > 0:
                cap = float(environ.get("RD_POST_SPEECH_CAP", "0.02"))
                _sleep(min(post_speech_delay, cap))

    InteractionOrchestrator.elevenlabs_say = elevenlabs_say_safe

    # ── play_audio blocking fix ──────────────────────────────────────────────
    # play_audio (used for cached WAV files) also calls speaker.request() and
    # returns immediately. Patch it to sleep for the audio duration so cached
    # lines don't cut off either.
    import wave as _wave
    from os.path import exists as _exists
    from sic_framework.core.message_python2 import AudioRequest as _AR2

    original_play_audio = InteractionOrchestrator.play_audio

    def play_audio_blocking(self, audio_file, amplified=False, log=True):
        if not _exists(audio_file):
            self.logger.error(f"Audio file not found: {audio_file}")
            return
        with _wave.open(audio_file, 'rb') as wf:
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            if sample_width != 2:
                raise ValueError(f"WAV not 16-bit; sample_width={sample_width}")
            audio = wf.readframes(n_frames)
            if amplified:
                audio = self._amplify_audio(audio)
            self.speaker.request(_AR2(audio, framerate))
            if log:
                self.log_utterance(speaker='robot', text=f'plays {audio_file}')
            # Block until the speaker is done playing
            duration_s = n_frames / framerate
            _sleep(duration_s + 0.05)

    InteractionOrchestrator.play_audio = play_audio_blocking

    # ── ElevenLabs full-stream fix ──────────────────────────────────────────
    # Some voices return multiple audio chunks per sentence. The default
    # speak() implementation may return after the first chunk, which sounds
    # like cut-off speech. Patch speak() to aggregate all chunks until isFinal.
    from nardial.tts_manager import ElevenLabsTTS

    original_elevenlabs_speak = ElevenLabsTTS.speak

    async def speak_full_stream(self, text):
        if not self.websocket or self.websocket.closed:
            self.logger.warning("[TTS] Websocket not connected. Initiating reconnect.")
            await self.connect()
        if not await self.ping_connection():
            self.logger.warning("[TTS] Websocket ping failed. Initiating reconnect.")
            await self.connect()

        await self.drain_socket()
        await self.websocket.send(dumps({"text": text, "flush": True}))

        audio_parts = []
        while True:
            try:
                # Longer timeout helps slower voices avoid premature cut-off.
                recv_timeout = max(float(environ.get("RD_ELEVENLABS_RECV_TIMEOUT", "1.0")), 0.1)
                message = await asyncio.wait_for(self.websocket.recv(), timeout=recv_timeout)
                data = loads(message)

                if data.get("audio"):
                    audio_parts.append(base64.b64decode(data["audio"]))

                if data.get("isFinal"):
                    if audio_parts:
                        return b"".join(audio_parts)
                    return None
            except asyncio.TimeoutError:
                self.logger.error("[TTS] Timeout while waiting for ElevenLabs stream")
                self.websocket = None
                return b"".join(audio_parts) if audio_parts else None
            except websockets.exceptions.ConnectionClosedOK:
                self.logger.warning("[TTS] WebSocket closed cleanly by server.")
                self.websocket = None
                return b"".join(audio_parts) if audio_parts else None
            except websockets.exceptions.ConnectionClosedError as e:
                self.logger.error(f"[TTS] WebSocket closed with error: {e}")
                self.websocket = None
                return b"".join(audio_parts) if audio_parts else None
            except Exception as e:
                self.logger.error(f"[TTS] Other failure in elevenlabs tts: {e}")
                self.websocket = None
                return b"".join(audio_parts) if audio_parts else None

    ElevenLabsTTS.speak = speak_full_stream
    ElevenLabsTTS._robot_detective_original_speak = original_elevenlabs_speak
    InteractionOrchestrator.elevenlabs_generate_chunk_audio = elevenlabs_generate_chunk_audio_safe
    InteractionOrchestrator._robot_detective_original_elevenlabs_generate_chunk_audio = original_elevenlabs_generate_chunk_audio

    # ── LLM response character voice ──────────────────────────────────────────
    # ask_llm is handled by MiniDialog.handle_move_ask_llm in the installed
    # nardial version. Patch that method so the active character is known while
    # _run_llm_exchange() is speaking the generated text.
    original_handle_move_ask_llm = MiniDialog.handle_move_ask_llm

    def infer_ask_llm_character(move) -> str | None:
        if not isinstance(move, dict):
            return None

        explicit = move.get("character")
        if explicit:
            return explicit

        prompt = str(move.get("prompt") or "").strip().lower()
        if not prompt:
            return None

        aliases = {
            "robin": ["robin de robotdetective", "je bent robin", "jij bent robin"],
            "trudy": ["je bent trudy", "jij bent trudy"],
            "eddy": ["professor eddy", "je bent professor eddy", "je bent eddy", "jij bent eddy"],
            "yoyo": ["meneer yoyo", "je bent meneer yoyo", "je bent yoyo", "jij bent yoyo"],
            "jennifer": ["je bent jennifer", "jij bent jennifer"],
            "dj_kata": ["dj kata", "je bent dj kata", "jij bent dj kata"],
        }

        for character, needles in aliases.items():
            if any(needle in prompt for needle in needles):
                return character

        m = re.search(r"je bent\s+([\w\- ]+?)(?:\.|,|\s+uit\b|\s+de\b|\s+het\b|\s+en\b|$)", prompt)
        if m:
            candidate = m.group(1).strip().lower().replace("-", "_")
            candidate = candidate.replace(" ", "_")
            if candidate in CHARACTER_VOICE_MAP:
                return candidate

        return None

    def handle_move_ask_llm_with_character(self, move):
        character = infer_ask_llm_character(move)
        target_voice_id = CHARACTER_VOICE_MAP.get(character) if character else None

        orch = self.conversation_agent.orchestrator if self.conversation_agent else None
        prev_char = getattr(orch, "_rd_current_character", None) if orch is not None else None

        try:
            if orch is not None:
                orch._rd_current_character = character
            if target_voice_id and orch and isinstance(getattr(orch, "tts_conf", None), ElevenLabsTTSConf):
                default_voice_id = orch.tts_conf.voice_id
                if target_voice_id != default_voice_id:
                    char_tts = _get_or_create_tts(target_voice_id, orch)
                    if char_tts is not None:
                        orch.tts = char_tts
                        orch.tts_conf.voice_id = target_voice_id
                        print(f"[voice-llm] {character} → {target_voice_id}")
                    else:
                        print(f"[voice-llm] WARNING: no TTS for '{character}' ({target_voice_id}), using default.")

            original_handle_move_ask_llm(self, move)
        finally:
            if orch is not None:
                orch._rd_current_character = prev_char

    MiniDialog.handle_move_ask_llm = handle_move_ask_llm_with_character
    MiniDialog._robot_detective_original_handle_move_ask_llm = original_handle_move_ask_llm
    print("[patch] MiniDialog ask_llm character voice handler registered")

    # ── InteractionOrchestrator.say() character voice wrapper ────────────────
    # When orchestrator.say() is called during LLM response generation,
    # check if _rd_current_character is set and switch voice if needed.
    original_orch_say = InteractionOrchestrator.say
    
    def say_with_character_voice(self, text, **kwargs):
        current_char = getattr(self, "_rd_current_character", None)
        target_voice_id = CHARACTER_VOICE_MAP.get(current_char) if current_char else None
        
        default_tts = None
        default_voice_id = None
        swapped = False
        
        if target_voice_id and isinstance(getattr(self, "tts_conf", None), ElevenLabsTTSConf):
            default_voice_id = self.tts_conf.voice_id
            if target_voice_id != default_voice_id:
                char_tts = _get_or_create_tts(target_voice_id, self)
                if char_tts is not None:
                    default_tts = self.tts
                    self.tts = char_tts
                    self.tts_conf.voice_id = target_voice_id
                    swapped = True
                    print(f"[voice-orch-say] {current_char} (char={target_voice_id}) replaces default={default_voice_id}")
                else:
                    print(f"[voice-orch-say] WARNING: Could not get TTS for {current_char} ({target_voice_id}), using default")
        
        try:
            original_orch_say(self, text, **kwargs)
        finally:
            if swapped and default_tts is not None:
                self.tts = default_tts
                self.tts_conf.voice_id = default_voice_id
    
    InteractionOrchestrator.say = say_with_character_voice
    print("[patch] InteractionOrchestrator.say character voice wrapper registered")

    _PATCH_APPLIED = True


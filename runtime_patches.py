"""Runtime compatibility and resiliency patches for Robot Detective."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path


def _install_nardial_tts_manager_shim() -> None:
    module_name = "nardial.tts_manager"
    if module_name in sys.modules:
        return
    try:
        from sic_framework.services.elevenlabs_tts.elevenlabs_tts import (  # type: ignore
            ElevenLabsTTS,
            ElevenLabsTTSConf,
            GetElevenLabsSpeechRequest,
        )
    except Exception:
        return

    shim = types.ModuleType(module_name)
    shim.ElevenLabsTTS = ElevenLabsTTS
    shim.ElevenLabsTTSConf = ElevenLabsTTSConf
    shim.GetElevenLabsSpeechRequest = GetElevenLabsSpeechRequest
    sys.modules[module_name] = shim


def _install_rag_timeout_and_fallback_patch() -> None:
    try:
        import sic_framework.services.datastore.redis_datastore as rd  # type: ignore
    except Exception:
        return

    try:
        timeout_sec = float(os.getenv("OPENAI_EMBED_TIMEOUT_SEC", "20"))
    except Exception:
        timeout_sec = 20.0

    # One client per API key: a new client opens a new connection to OpenAI for every RAG query,
    # which measured ~1.5 s slower per question than reusing the connection.
    clients = {}

    def _openai_embed_texts_with_timeout(texts: list[str], *, model: str, api_key: str) -> list[list[float]]:
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency: openai.\n"
                "Install it with: pip install openai\n"
                "Original import error: {}".format(e)
            ) from e
        if not api_key:
            raise RuntimeError("openai_api_key parameter is required")

        client = clients.get(api_key)
        if client is None:
            client = clients[api_key] = OpenAI(api_key=api_key, timeout=timeout_sec)
        resp = client.embeddings.create(model=model, input=texts)
        data = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in data]

    rd._openai_embed_texts = _openai_embed_texts_with_timeout

    original_handle = rd.RedisDatastoreComponent.handle_datastore_actions

    def _safe_handle(self, request):
        try:
            return original_handle(self, request)
        except Exception as exc:
            if rd.is_sic_instance(request, rd.QueryVectorDBRequest):
                self.logger.error("QueryVectorDBRequest failed: {}".format(exc))
                index_name = rd.sanitize_index_name(getattr(request, "index_name", "index"))
                return rd.VectorDBResultsMessage(
                    payload={
                        "index": index_name,
                        "total": 0,
                        "results": [],
                        "error": str(exc),
                    }
                )
            raise

    rd.RedisDatastoreComponent.handle_datastore_actions = _safe_handle


def _install_connector_rag_timeout_patch() -> None:
    """
    Guard client-side RAG requests so the interview loop does not block when datastore
    replies are missing or delayed.
    """
    try:
        from sic_framework.core.connector import SICConnector  # type: ignore
        from sic_framework.services.datastore.redis_datastore import VectorDBResultsMessage  # type: ignore
    except Exception:
        return

    import time

    original_request = SICConnector.request

    try:
        rag_timeout_sec = float(os.getenv("RAG_QUERY_TIMEOUT_SEC", "12"))
    except Exception:
        rag_timeout_sec = 12.0
    try:
        user_model_timeout_sec = float(os.getenv("USER_MODEL_TIMEOUT_SEC", "3"))
    except Exception:
        user_model_timeout_sec = 3.0
    try:
        datastore_retry_sec = float(os.getenv("DATASTORE_RETRY_SEC", "60"))
    except Exception:
        datastore_retry_sec = 60.0

    # Participant data (the user model) is read and written through the datastore service on almost
    # every step of a scene, with a default timeout of 100 s. When that service hangs, every step waited
    # 100 s and the episode looked frozen. nardial already falls back to its in-memory copy when such a
    # request fails, so: fail fast, and after a timeout skip the datastore for DATASTORE_RETRY_SEC.
    user_model_requests = {
        "GetScopedRecordRequest", "SetScopedKeyValuesRequest", "GetScopedKeyValuesRequest",
        "GetScopedKeysRequest", "DeleteScopedKeyValuesRequest",
    }
    datastore_down_until = [0.0]

    def _safe_request(self, request, timeout=100.0, block=True):
        name = request.__class__.__name__
        is_rag_query = name == "QueryVectorDBRequest"
        if name in user_model_requests:
            if time.monotonic() < datastore_down_until[0]:
                raise TimeoutError("datastore unavailable, using the in-memory user model")
            try:
                return original_request(self, request, timeout=min(float(timeout), user_model_timeout_sec), block=block)
            except TimeoutError:
                datastore_down_until[0] = time.monotonic() + datastore_retry_sec
                self.logger.error(
                    "Datastore did not answer {} within {}s; continuing with the in-memory user model and "
                    "skipping the datastore for {}s. Check the run-redis / run_datastore window.".format(
                        name, user_model_timeout_sec, datastore_retry_sec))
                raise
        if not is_rag_query:
            return original_request(self, request, timeout=timeout, block=block)

        effective_timeout = min(float(timeout), rag_timeout_sec)
        try:
            if time.monotonic() < datastore_down_until[0]:
                raise TimeoutError("datastore unavailable")
            return original_request(self, request, timeout=effective_timeout, block=block)
        except TimeoutError as exc:
            datastore_down_until[0] = max(datastore_down_until[0], time.monotonic() + datastore_retry_sec)
            self.logger.error("RAG query timed out after {}s: {}".format(effective_timeout, exc))
            return VectorDBResultsMessage(
                payload={
                    "index": getattr(request, "index_name", ""),
                    "total": 0,
                    "results": [],
                    "error": "rag_query_timeout",
                }
            )
        except Exception as exc:
            self.logger.error("RAG query failed: {}".format(exc))
            return VectorDBResultsMessage(
                payload={
                    "index": getattr(request, "index_name", ""),
                    "total": 0,
                    "results": [],
                    "error": str(exc),
                }
            )

    SICConnector.request = _safe_request


def _install_vector_store_quality_patch() -> None:
    """Improve RAG snippet quality to reduce prompt-echo behavior."""
    try:
        from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider  # type: ignore
        from sic_framework.services.datastore.redis_datastore import (  # type: ignore
            QueryVectorDBRequest,
            VectorDBResultsMessage,
        )
    except Exception:
        return

    def _is_low_signal_query(text: str) -> bool:
        normalized = " ".join((text or "").strip().lower().split())
        if not normalized:
            return True
        greetings = {"hoi", "hallo", "hey", "yo", "oke", "ok", "hi", "goedemorgen", "goedemiddag"}
        if normalized in greetings:
            return True
        return len(normalized.split()) <= 2 and "?" not in normalized

    def _clean_snippet(content: str) -> str:
        heading_drops = {
            "personal history trudy",
            "personal relationships trudy",
            "mystery knowlegde",
            "ep1 mystery knowledge trudy",
            "conversation guidelines",
        }
        lines = []
        for raw in (content or "").replace("\ufeff", "").splitlines():
            line = raw.strip()
            if not line:
                continue
            low = line.lower()
            if low in heading_drops:
                continue
            if "haal dit uit de rag" in low:
                continue
            lines.append(line)
        cleaned = " ".join(lines).strip()
        if len(cleaned) > 420:
            cleaned = cleaned[:420].rsplit(" ", 1)[0] + "..."
        return cleaned

    def _query(self, text: str, index_name: str | None = None, k: int = 5) -> list[str]:
        user_text = str(text or "").strip()
        if _is_low_signal_query(user_text):
            return []

        query_index = index_name or self._index_name
        if not query_index:
            raise ValueError("RedisVectorStoreProvider.query requires an index name")

        result = self._datastore.request(
            QueryVectorDBRequest(
                index_name=query_index,
                query_text=user_text,
                openai_api_key=self._openai_api_key,
                k=max(1, min(int(k), 3)),
                partition="default",
                embedding_model=self._embedding_model,
            )
        )

        if not isinstance(result, VectorDBResultsMessage):
            return []

        snippets = []
        for idx, item in enumerate(result.payload.get("results", []), start=1):
            cleaned = _clean_snippet(item.get("content") or "")
            if not cleaned:
                continue
            source = Path(item.get("doc_path") or "unknown").name
            snippets.append(f"[{idx}] Source: {source}\nFacts: {cleaned}")
            if len(snippets) >= 3:
                break
        return snippets

    RedisVectorStoreProvider.query = _query


def _strip_speaker_labels(text: str) -> str:
    """
    Remove a speaker label the LLM copied from the transcript ("Eddy: Wat leuk..." -> "Wat leuk..."), and
    cut the reply off where it starts writing someone else's turn ("... \nKind: ...").
    """
    import re

    try:
        from character_styles import CHARACTER_STYLES
        names = [name.replace("_", " ") for name in CHARACTER_STYLES]
    except Exception:
        names = []
    names += ["professor eddy", "dj kata", "stoep tegel", "robot", "verteller", "kind"]
    label = r"(?:{})\s*:".format("|".join(sorted({re.escape(n) for n in names}, key=len, reverse=True)))
    text = re.sub(r"^\s*(?:{}\s*)+".format(label), "", text or "", flags=re.IGNORECASE)
    other_turn = re.search(r"\n\s*{}".format(label), text, flags=re.IGNORECASE)
    return (text[:other_turn.start()] if other_turn else text).strip()


def _single_topic_question(question: str) -> str:
    """
    Cut a double-barreled question down to its first part:
    "Heb je een favoriete groep of een nummer dat je vaak luistert?" -> "Heb je een favoriete groep?"
    "Speel je vaak nummers die je leuk vindt, of maak je ook je eigen muziek?" -> "Speel je vaak nummers die je leuk vindt?"
    A simple choice like "Vind je het spannend of eng?" is left alone.
    """
    import re

    body = question.rstrip().rstrip("?").rstrip()
    joins = [
        r",\s+(?:of|en)\s+",
        r"\s+of\s+(?=(?:een|ook|maak|speel|heb|ben|vind|ga|doe|wil|zou|kun|kan|zing|luister|bouw)\b)",
        r"\s+en\s+(?=(?:wat|waar|waarom|hoe|wie|welk\w*|wanneer|hoeveel)\b)",
    ]
    cuts = [m.start() for pattern in joins for m in re.finditer(pattern, body, re.IGNORECASE)
            if len(body[:m.start()].split()) >= 3]
    return body[:min(cuts)].rstrip(" ,") + "?" if cuts else question


def _limit_questions(text: str, max_questions: int) -> str:
    """
    Make an LLM reply ask children at most one thing, and end on that question.

    Short reactions like "Echt waar?" (3 words or fewer), tag questions like "..., nietwaar?" or
    "..., vind je ook niet?" and hints like "Wist je dat ...?" do not count as questions. With
    max_questions=1, only the last real question is kept (the model usually ends on the question it
    means), cut down to a single topic, and moved to the very end, so children hear that it is their
    turn ("Wat zing jij? Ik zing graag!" becomes "Ik zing graag! Wat zing jij?"). With
    max_questions=0 all real questions are removed; if nothing is left, the text is kept as is.
    """
    import re

    sentences = [s for s in re.split(r"(?<=[.!?…])\s+", (text or "").strip()) if s]
    rhetorical = re.compile(
        r"(?:\b(?:nietwaar|toch|h[eè]|of niet|vind je ook niet|weet je wel)\?$)|(?:^wist je dat\b)", re.IGNORECASE
    )

    def is_real_question(sentence: str) -> bool:
        sentence = sentence.strip().rstrip(" \"'”’)")
        return sentence.endswith("?") and len(sentence.split()) > 3 and not rhetorical.search(sentence)

    questions = [s for s in sentences if is_real_question(s)]
    others = [s for s in sentences if not is_real_question(s)]
    if not questions:
        return text
    if max_questions <= 0:
        return " ".join(others) or text
    return " ".join(others + [_single_topic_question(questions[-1])])


_voice_to_character_cache: dict | None = None


async def _while_thinking(agent, voice_settings, llm_call, think: bool = True):
    """
    Await `llm_call` while the character says a short thinking sound ("Hmm...") with a thinking
    gesture, so the wait for the answer does not feel empty. The sounds are per character in
    character_styles.py and come from the voice cache after their first use.
    Disable with THINKING_SOUNDS=0 in conf/.env.
    """
    import asyncio
    import random

    task = asyncio.ensure_future(llm_call)
    if not think or os.getenv("THINKING_SOUNDS", "1").strip().lower() not in {"1", "true", "yes", "y"}:
        return await task
    try:
        from character_styles import CHARACTER_STYLES, DEFAULT_CHARACTER, THINKING_GESTURES

        global _voice_to_character_cache
        if _voice_to_character_cache is None:
            _voice_to_character_cache = _voice_id_to_character()
        voice_id = (voice_settings or {}).get("voice_id")
        character = _voice_to_character_cache.get(voice_id, DEFAULT_CHARACTER) if voice_id else DEFAULT_CHARACTER
        sounds = (CHARACTER_STYLES.get(character) or {}).get("thinking")
        if sounds:
            device = agent.orchestrator.device
            if THINKING_GESTURES and hasattr(device, "play_animation"):
                device.play_animation(random.choice(THINKING_GESTURES), run_async=True)
            # animated=False: the thinking gesture replaces the usual speaking gesture.
            await agent.say(random.choice(sounds), voice_settings=voice_settings, animated=False)
    except Exception as exc:
        print("Thinking sound failed: {}".format(exc))
    return await task


def _install_llm_memory_patch() -> None:
    """
    Give llm_based scenes a real conversation memory.

    Stock nardial only keeps the children's answers as plain strings, which
    request_from_llm then drops, so every LLM turn sees nothing but the latest
    answer. That makes characters repeat questions (e.g. asking twice which song
    the children would sing). This patch:

    - passes the full exchange as user/assistant messages;
    - adds a transcript of what was just said in the session (including the
      scripted lines that set up the chat) to the system prompt;
    - fills %variables% from the user model into the prompt;
    - lets the character close on the last turn instead of asking a question
      nobody answers;
    - matches quit phrases on whole words ("dag" no longer matches "vandaag").
    """
    try:
        import re
        from time import monotonic

        import nardial.mini_dialogs as md
        from nardial.moves import MOVE_ANSWER_LLM, MOVE_ASK_LLM
    except Exception:
        return

    try:
        transcript_lines = int(os.getenv("LLM_TRANSCRIPT_LINES", "40"))
    except Exception:
        transcript_lines = 40
    try:
        closing_margin_sec = float(os.getenv("LLM_CLOSING_MARGIN_SEC", "20"))
    except Exception:
        closing_margin_sec = 20.0

    speaker_names = {"robin": "Robin", "s_tegel": "Stoep Tegel", "dj_kata": "Kata", "narrator": "Verteller"}
    no_answer = "(Het kind zei niets, of het was niet te verstaan.)"
    start_chat = "(Begin het gesprek.)"

    memory_rules = (
        "\n\nGEHEUGEN EN GESPREK\n"
        "- Hieronder staat wat er zojuist gezegd is. Gebruik dit als je geheugen: stel nooit een vraag "
        "die al gesteld of beantwoord is, en bouw voort op wat de kinderen al verteld hebben.\n"
        "- De antwoorden van de kinderen komen uit spraakherkenning en kunnen fouten bevatten. Klinkt iets "
        "vreemd, ga dan uit van wat het kind waarschijnlijk bedoelde.\n"
        f"- Staat er '{no_answer}', herhaal je vraag dan niet letterlijk: stel hem korter en makkelijker, "
        "of vertel zelf iets en ga verder.\n"
        "- Alles wat je schrijft wordt hardop uitgesproken tegen kinderen: houd je aan de lengte uit je "
        "instructies (meestal 1 of 2 korte zinnen). "
        "Geen emojis, aanhalingstekens, opsommingen of beschrijvingen tussen haakjes.\n"
        "- Schrijf alleen wat jij zelf nu hardop zegt, in de ik-vorm. De namen met een dubbele punt "
        "hieronder bij 'ZOJUIST GEZEGD' zijn alleen om te laten zien wie wat zei: zet nooit zelf een naam "
        "voor je tekst (dus niet 'Eddy: ...') en schrijf nooit wat een ander zegt.\n"
        "- Stel per beurt hooguit één vraag, over maar één ding, en zet die helemaal aan het eind. "
        "Dus niet 'Wat luister je graag? Of maak je zelf muziek?' en niet 'Welk liedje zing je, en waar "
        "zing je het?', maar alleen 'Welk liedje zing jij het liefst?'. Geen keuzelijstjes in je vraag."
    )
    # Repeated as the very last instruction (after the transcript): gpt-4o-mini follows the end of
    # the prompt best, and kept asking two things at once when this was only in the middle.
    one_question_rule = (
        "\n\nBELANGRIJK: stel hooguit één korte vraag, over maar één ding. Dus geen 'of' of 'en' met "
        "een tweede vraag erin. Zet die vraag als allerlaatste zin: zeg na je vraag niets meer."
    )
    no_question_rule = (
        "\n\nStel zelf geen vraag: na jouw antwoord gaat het gesprek meteen verder met iets anders."
    )
    last_turn_rule = (
        "\n\nDIT IS JE LAATSTE BEURT: reageer kort op wat er net gezegd is. Stel GEEN vraag meer, "
        "en neem alleen afscheid als je instructies daarom vragen."
    )

    def _speaker(entry) -> str:
        if entry.get("role") == "user":
            return "Kind"
        character = entry.get("character")
        if not character:
            return "Robot"
        return speaker_names.get(character, str(character).replace("_", " ").title())

    def _transcript(session_history) -> list[str]:
        lines = []
        for entry in session_history or []:
            if not isinstance(entry, dict) or entry.get("role") not in ("robot", "user"):
                continue
            entry_type = str(entry.get("type") or "")
            if not (entry_type in ("say", "llm_followup") or entry_type.startswith(("ask_", "answer_"))):
                continue
            text = str(entry.get("text") or "").strip() or (no_answer if entry.get("role") == "user" else "")
            if text:
                lines.append(f"{_speaker(entry)}: {text}")
        return lines[-transcript_lines:]

    def _fill_variables(text: str, user_model) -> str:
        try:
            items = list(user_model.items())
        except Exception:
            return text
        for var, value in items:
            text = text.replace(f"%{var}%", str(value))
        return text

    def _said_quit(user_input: str, quit_phrases) -> bool:
        for phrase in quit_phrases or []:
            if phrase and re.search(r"\b" + re.escape(phrase) + r"\b", user_input, re.IGNORECASE):
                return True
        return False

    original_say = md.MiniDialog.handle_move_say

    async def handle_move_say(self, move):
        # Remember who spoke each scripted line so the transcript can name them.
        before = len(self.session_history)
        await original_say(self, move)
        character = self._get(move, "character")
        if character and len(self.session_history) > before:
            self.session_history[-1].setdefault("character", character)

    async def _run_llm_exchange(self, prompt: str, max_turns: int, set_variable=None, quit_phrases=None,
                                quit_signal=None, speak_first: bool = True, duration=None,
                                rag_enabled: bool = False, index_name=None, voice_settings=None):
        agent = self.conversation_agent
        character = getattr(self, "character", None)
        start_time = monotonic()

        def remaining_time():
            if duration is None:
                return None
            return max(0.0, duration - (monotonic() - start_time))

        transcript = _transcript(self.session_history)
        system_prompt = _fill_variables(prompt or "", self.user_model) + memory_rules
        if transcript:
            system_prompt += "\n\nZOJUIST GEZEGD:\n" + "\n".join(transcript)

        messages: list[dict] = []
        user_input = start_chat
        # The scene `duration` only decides whether a new round starts. Once the robot listens, the
        # child gets the full listen window (NAO_LISTEN_TIMEOUT_SEC); cutting it to the scene time
        # left chopped children off mid-question.
        if not speak_first:
            timeout = remaining_time()
            if timeout is not None and timeout <= 0:
                return
            result = await agent.orchestrator.listen()
            heard = (result.transcript or "").strip()
            self._record_user(MOVE_ANSWER_LLM, heard)
            if _said_quit(heard, quit_phrases):
                return
            user_input = heard or no_answer

        turns = max_turns or md.MAX_LLM_TURNS
        for turn in range(turns):
            timeout = remaining_time()
            child_spoke = user_input not in (no_answer, start_chat)
            # Out of time, but a child just asked or said something: still answer it, as the closing
            # turn, before the scene ends (and Robin says there is time for one more question).
            if timeout is not None and timeout <= 0 and not child_spoke:
                return
            last_turn = turn == turns - 1 or (timeout is not None and (timeout <= 0 or timeout < closing_margin_sec))

            llm_text = await _while_thinking(
                agent,
                voice_settings,
                agent.ask_llm(
                    user_prompt=user_input,
                    context_messages=messages,
                    system_prompt=system_prompt + (last_turn_rule if last_turn else one_question_rule),
                    rag_enabled=rag_enabled and user_input not in (no_answer, start_chat),
                    index_name=index_name,
                ),
                # Only when reacting to something a child actually said.
                think=user_input not in (no_answer, start_chat),
            )
            if llm_text is None:
                return

            llm_text = _strip_speaker_labels(llm_text)
            ended = bool(quit_signal and quit_signal in llm_text)
            reply = llm_text.replace(quit_signal, "").strip() if quit_signal else llm_text.strip()
            # Nobody listens after a closing turn, so it gets no question at all.
            reply = _limit_questions(reply, 0 if (ended or last_turn) else 1)
            messages.append({"role": "user", "content": user_input})
            if reply:
                messages.append({"role": "assistant", "content": reply})
                await agent.say(reply, voice_settings=voice_settings)
                self._record_robot(MOVE_ASK_LLM, reply, **({"character": character} if character else {}))
            if ended or last_turn:
                return

            timeout = remaining_time()
            if timeout is not None and timeout <= 0:
                return
            result = await agent.orchestrator.listen()
            heard = (result.transcript or "").strip()
            self._record_user(MOVE_ANSWER_LLM, heard)
            if set_variable and heard:
                self.user_model[set_variable] = self.extract_open_value(heard)
            if _said_quit(heard, quit_phrases):
                return
            user_input = heard or no_answer

    async def _generate_llm_followup(self, user_answer: str, system_prompt: str, voice_settings=None):
        # The next scripted move follows right after a followup, so a question here would stack on
        # top of the next scripted question.
        context_messages = [
            entry.get("text", "") for entry in self.session_history if entry.get("text") is not None
        ]
        rag_enabled, index_name = getattr(self, "_followup_rag", None) or (False, None)
        llm_text = await _while_thinking(
            self.conversation_agent,
            voice_settings,
            self.conversation_agent.ask_llm(
                user_prompt=user_answer,
                context_messages=context_messages,
                system_prompt=(system_prompt or "") + no_question_rule,
                rag_enabled=rag_enabled and bool((user_answer or "").strip()),
                index_name=index_name,
            ),
            think=bool((user_answer or "").strip()),
        )
        llm_text = _limit_questions(_strip_speaker_labels(llm_text or ""), 0)
        if llm_text:
            await self.conversation_agent.say(llm_text, voice_settings=voice_settings)
            self._record_robot(md.MOVE_LLM_FOLLOWUP, llm_text)

    def _with_followup_rag(original_handler):
        # nardial drops "rag_enabled" and "index_name" from ask moves, so an llm_followup never used
        # the knowledge base (e.g. Robin answering the children's questions in episode 0).
        async def handler(self, move):
            if isinstance(move, dict) and move.get("rag_enabled"):
                self._followup_rag = (True, move.get("index_name"))
            try:
                return await original_handler(self, move)
            finally:
                self._followup_rag = None

        return handler

    md.MiniDialog.handle_move_say = handle_move_say
    md.MiniDialog._run_llm_exchange = _run_llm_exchange
    md.MiniDialog._generate_llm_followup = _generate_llm_followup
    md.MiniDialog.handle_move_ask_open = _with_followup_rag(md.MiniDialog.handle_move_ask_open)
    md.MiniDialog.handle_move_ask_yesno = _with_followup_rag(md.MiniDialog.handle_move_ask_yesno)


def _install_listen_timeout_patch() -> None:
    """
    Give children NAO_LISTEN_TIMEOUT_SEC seconds (default 12) to answer every question.

    nardial hardcodes a 10 second listen window for scripted questions, and LLM exchanges with
    a scene `duration` listened for the whole remaining scene time. Both now use this one window.
    A caller can still pass a shorter timeout explicitly.
    """
    try:
        from nardial.interaction_orchestrator import InteractionOrchestrator
    except Exception:
        return

    original_listen = InteractionOrchestrator.listen

    def _listen_timeout_sec() -> float:
        # Read at call time: the episode scripts load conf/.env after applying the patches.
        try:
            return float(os.getenv("NAO_LISTEN_TIMEOUT_SEC", "12"))
        except Exception:
            return 12.0

    async def listen(self, context=None, timeout=None):
        window = _listen_timeout_sec()
        timeout = window if timeout is None else min(float(timeout), window)
        return await original_listen(self, context=context, timeout=timeout)

    InteractionOrchestrator.listen = listen


def _make_beep(freq_hz: float = 880.0, duration_sec: float = 0.15, sample_rate: int = 16000) -> bytes:
    """Short sine beep as 16-bit mono PCM, with a fade in/out so it does not click."""
    import math
    import struct

    n = int(sample_rate * duration_sec)
    fade = int(sample_rate * 0.01)
    samples = []
    for i in range(n):
        envelope = min(1.0, i / fade, (n - 1 - i) / fade)
        samples.append(int(0.5 * 32767 * envelope * math.sin(2 * math.pi * freq_hz * i / sample_rate)))
    return struct.pack("<{}h".format(n), *samples)


def _install_listen_beep_patch() -> None:
    """
    Play a short beep on the NAO right before it starts listening, next to the green eyes,
    so children hear that it is their turn. Disable with LISTEN_BEEP=0 in conf/.env.
    """
    try:
        from nardial.providers.device.nao import NaoAdapter
    except Exception:
        return

    original_signal = NaoAdapter.signal_listening
    sample_rate = 16000
    beep = _make_beep(sample_rate=sample_rate)

    def signal_listening(self, start: bool = True) -> None:
        # Beep before the eyes turn green: the speaker request blocks until the beep has played,
        # so the microphone does not pick it up as the child's answer.
        if start and os.getenv("LISTEN_BEEP", "1").strip().lower() in {"1", "true", "yes", "y"}:
            try:
                self.play_audio_bytes(beep, sample_rate)
            except Exception as exc:
                if self._logger:
                    self._logger.error("Listen beep failed: {}".format(exc))
        original_signal(self, start)

    NaoAdapter.signal_listening = signal_listening


def _voice_id_to_character() -> dict:
    """Map each ElevenLabs voice id to its character name, from all episode dialog files."""
    import json

    mapping = {}
    for path in sorted((Path(__file__).resolve().parent / "RobotDetective_Narrative_Jsons").glob("*.json")):
        try:
            dialogs = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for dialog in dialogs if isinstance(dialogs, list) else []:
            for name, definition in (dialog.get("characters") or {}).items():
                voice_id = ((definition or {}).get("voice_settings") or {}).get("voice_id")
                if voice_id:
                    mapping.setdefault(voice_id, name)
    return mapping


def _install_character_style_patch() -> None:
    """
    Give each character on the NAO their own eye colour and gestures (see character_styles.py),
    so children can see who is talking. The speaker is recognised by the voice used for the line.
    Disable with CHARACTER_STYLES=0 in conf/.env.
    """
    try:
        import random

        from nardial.interaction_orchestrator import InteractionOrchestrator
        from nardial.providers.device.nao import NaoAdapter

        from character_styles import CHARACTER_STYLES, DEFAULT_CHARACTER
    except Exception:
        return

    voice_to_character = _voice_id_to_character()
    original_say = InteractionOrchestrator.say
    original_speaking_animation = NaoAdapter.play_speaking_animation

    def _enabled() -> bool:
        return os.getenv("CHARACTER_STYLES", "1").strip().lower() in {"1", "true", "yes", "y"}

    async def say(self, text, *args, voice_settings=None, **kwargs):
        if _enabled() and isinstance(self.device, NaoAdapter):
            voice_id = (voice_settings or {}).get("voice_id")
            character = voice_to_character.get(voice_id, DEFAULT_CHARACTER) if voice_id else DEFAULT_CHARACTER
            style = CHARACTER_STYLES.get(character)
            self.device._character_style = style
            if style and style.get("eyes"):
                try:
                    self.device.set_leds(*style["eyes"])
                except Exception as exc:
                    self.logger.error("Setting eye colour for {} failed: {}".format(character, exc))
        return await original_say(self, text, *args, voice_settings=voice_settings, **kwargs)

    def play_speaking_animation(self, style) -> None:
        gestures = (getattr(self, "_character_style", None) or {}).get("gestures")
        if not gestures:
            return original_speaking_animation(self, style)
        self.play_animation(random.choice(gestures), run_async=True)

    InteractionOrchestrator.say = say
    NaoAdapter.play_speaking_animation = play_speaking_animation


def _install_pause_patch() -> None:
    """
    Short pauses so children can follow the conversation:
    - SPEAKER_CHANGE_PAUSE_SEC (default 0.6) before a line when a different character starts talking;
    - PRE_LISTEN_PAUSE_SEC (default 0.5) after a question, before the beep and listening start.
    Only pauses where it helps, so the episodes do not get much longer. Set either to 0 to disable.
    """
    try:
        import asyncio

        from nardial.interaction_orchestrator import InteractionOrchestrator
    except Exception:
        return

    voice_to_character = _voice_id_to_character()
    original_say = InteractionOrchestrator.say
    original_listen = InteractionOrchestrator.listen

    def _seconds(name: str, default: str) -> float:
        # Read at call time: the episode scripts load conf/.env after applying the patches.
        try:
            return max(0.0, float(os.getenv(name, default)))
        except Exception:
            return float(default)

    async def say(self, text, *args, voice_settings=None, **kwargs):
        voice_id = (voice_settings or {}).get("voice_id")
        # Lines without their own voice use the default voice, which is Robin's.
        speaker = voice_to_character.get(voice_id, "robin") if voice_id else "robin"
        previous = getattr(self, "_last_speaker", None)
        if previous is not None and previous != speaker:
            await asyncio.sleep(_seconds("SPEAKER_CHANGE_PAUSE_SEC", "0.6"))
        self._last_speaker = speaker
        return await original_say(self, text, *args, voice_settings=voice_settings, **kwargs)

    async def listen(self, *args, **kwargs):
        await asyncio.sleep(_seconds("PRE_LISTEN_PAUSE_SEC", "0.5"))
        return await original_listen(self, *args, **kwargs)

    InteractionOrchestrator.say = say
    InteractionOrchestrator.listen = listen


def _install_ask_character_voice_patch() -> None:
    """
    Let question moves (ask_open, ask_yesno, ask_options) speak in their character's voice.

    nardial drops the "character" field when it turns these moves into objects, so every question
    was asked in the default (Robin) voice, even when Stoep Tegel or a resident asks it.
    """
    try:
        from nardial.moves import MoveAskOpen, MoveAskOptions, MoveAskYesNo
    except Exception:
        return

    def _keep_character(move_class) -> None:
        original_from_dict = move_class.from_dict.__func__

        @classmethod
        def from_dict(cls, data: dict):
            move = original_from_dict(cls, data)
            if isinstance(data, dict) and data.get("character") and not getattr(move, "character", None):
                move.character = data["character"]
            return move

        move_class.from_dict = from_dict

    for move_class in (MoveAskOpen, MoveAskYesNo, MoveAskOptions):
        _keep_character(move_class)


def _install_tts_prefetch_patch() -> None:
    """
    Generate the next piece of a line with ElevenLabs while the current piece is playing.

    nardial splits longer lines into pieces of ~80 characters and only requested the next piece after
    the previous one had finished playing, so every piece added a silent gap (~0.7 s) mid-answer.
    """
    try:
        from concurrent.futures import ThreadPoolExecutor

        from nardial.providers.tts.elevenlabs import (
            ElevenLabsTTSProvider,
            GetElevenLabsSpeechRequest,
            _amplify_audio,
            _read_wav_bytes,
        )
    except Exception:
        return

    def speak(self, text: str, amplified: bool = False, always_regenerate: bool = False,
              chunk_audio: bool = True, voice_settings=None, **kwargs) -> None:
        voice_settings = self._validate_and_normalize_voice_settings(voice_settings)
        voice_id = voice_settings.get("voice_id", self._conf.voice_id)
        speaking_rate = voice_settings.get("speaking_rate", self._conf.speaking_rate)
        model_id = voice_settings.get("model_id", self._conf.model_id)
        chunks = [text] if (not chunk_audio or model_id == "eleven_v3") else self._split_text(text)

        def fetch(chunk: str):
            """Return (audio, sample_rate), from the cache or freshly generated (and then cached)."""
            normalized_text = self._tts_cacher.normalize_text(chunk)
            tts_key = self._tts_cacher.make_tts_key({
                "text": normalized_text,
                "tts_service": "ELEVENLABS",
                "speaking_rate": speaking_rate,
                "voice_id": voice_id,
                "model_id": model_id,
            })
            if not always_regenerate:
                cached_path = self._tts_cacher.load_audio_file(tts_key)
                if cached_path:
                    return _read_wav_bytes(cached_path)
            req_kwargs = {"text": normalized_text}
            if voice_id is not None:
                req_kwargs["voice_id"] = voice_id
            if speaking_rate is not None:
                req_kwargs["speaking_rate"] = speaking_rate
            if model_id is not None:
                req_kwargs["model_id"] = model_id
            with self._request_lock:
                reply = self._tts.request(GetElevenLabsSpeechRequest(**req_kwargs))
            if reply is None or not reply.waveform:
                return None, None
            self._tts_cacher.save_audio_file(tts_key, reply.waveform, reply.sample_rate)
            return reply.waveform, reply.sample_rate

        if not chunks:
            return
        with ThreadPoolExecutor(max_workers=1) as pool:
            upcoming = pool.submit(fetch, chunks[0])
            for i in range(len(chunks)):
                audio, sample_rate = upcoming.result()
                if i + 1 < len(chunks):
                    upcoming = pool.submit(fetch, chunks[i + 1])
                if audio:
                    self._device.play_audio_bytes(_amplify_audio(audio) if amplified else audio, sample_rate)

    ElevenLabsTTSProvider.speak = speak


def _install_empty_tts_chunk_patch() -> None:
    """
    Never send empty text to ElevenLabs.

    nardial splits each line into sentence chunks and strips punctuation before synthesis, so a
    stray ' .' or '...' at the end of a line becomes an empty request. The ElevenLabs service
    never answers that request, and the robot hangs forever mid-scene.
    """
    try:
        from nardial.providers.tts.cacher import TTSCacher
        from nardial.providers.tts.elevenlabs import ElevenLabsTTSProvider
    except Exception:
        return

    original_split = ElevenLabsTTSProvider._split_text
    original_speak = ElevenLabsTTSProvider.speak

    def _normalize_for_check(chunk: str) -> str:
        return TTSCacher.normalize_text(chunk)

    def _split_text(text: str, *args, **kwargs) -> list[str]:
        return [c for c in original_split(text, *args, **kwargs) if _normalize_for_check(c)]

    def speak(self, text: str, *args, **kwargs):
        if not _normalize_for_check(text or ""):
            return None
        return original_speak(self, text, *args, **kwargs)

    ElevenLabsTTSProvider._split_text = staticmethod(_split_text)
    ElevenLabsTTSProvider.speak = speak


def apply_datastore_service_patches() -> None:
    """Patches for the separate `run-redis` datastore service process (see run_datastore.py)."""
    _install_rag_timeout_and_fallback_patch()


def apply_runtime_patches() -> None:
    _install_nardial_tts_manager_shim()
    _install_rag_timeout_and_fallback_patch()
    _install_connector_rag_timeout_patch()
    _install_vector_store_quality_patch()
    _install_llm_memory_patch()
    # Before the empty-chunk patch, so that patch still guards this faster speak().
    _install_tts_prefetch_patch()
    _install_empty_tts_chunk_patch()
    _install_listen_timeout_patch()
    _install_listen_beep_patch()
    # Before the character style patch, so the eyes change colour first and the pause follows.
    _install_pause_patch()
    _install_character_style_patch()
    _install_ask_character_voice_patch()

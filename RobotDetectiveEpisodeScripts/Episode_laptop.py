r"""
Robot Detective — any episode on the laptop only (no robot)
===========================================================
Plays an episode through the laptop's speakers and listens through the laptop's microphone
(Dialogflow), or with --typing, lets you type the answers (handy for testing).

    python RobotDetectiveEpisodeScripts/Episode_laptop.py --episode 2
    python RobotDetectiveEpisodeScripts/Episode_laptop.py --episode 2 --typing

It follows the robot runner of the same episode (Episode_<n>_..._NAO / Episode_2_gigagiebels.py, ...):
the same dialog file (EPISODE_VERSION: full, short or 3 interviews), the same scene list (commented-out
scenes are skipped here too) and the same children's names. Change those in the robot runner.

Services needed: Redis, ElevenLabs TTS, GPT, and (unless --typing) Dialogflow.
Optional in conf/.env: LAPTOP_MIC_NAME / LAPTOP_MIC_INDEX to pick the microphone (see laptop_mic.py).
"""
import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

_REPO_ROOT_FOR_IMPORT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT_FOR_IMPORT not in sys.path:
    sys.path.insert(0, _REPO_ROOT_FOR_IMPORT)

from runtime_patches import apply_runtime_patches

apply_runtime_patches()

import numpy as np
from dotenv import load_dotenv
from sic_framework.devices.common_desktop.desktop_microphone import MicrophoneConf
from sic_framework.devices.common_desktop.desktop_speakers import SpeakersConf
from sic_framework.devices.desktop import Desktop
from sic_framework.services.dialogflow.dialogflow import DialogflowConf

from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig
from nardial.providers.device.desktop import DesktopAdapter
from local_llm import make_llm_provider  # OpenAI or a local model, see LLM_BACKEND in conf/.env
from nardial.providers.nlu.dialogflow import DialogflowNLUProvider
from nardial.providers.nlu.written_keyword import WrittenKeywordNLUProvider
from nardial.providers.tts.elevenlabs import ElevenLabsTTSConf, ElevenLabsTTSProvider
from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider
from nardial.session_manager import SessionManager

from laptop_mic import describe_laptop_mic, resolve_laptop_mic_index
from start_gate import wait_for_start

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
JSON_DIR = REPO_ROOT / "RobotDetective_Narrative_Jsons"
GOOGLE_KEYFILE_PATH = REPO_ROOT / "conf" / "google" / "google-key.json"
ENV_FILE_PATH = REPO_ROOT / "conf" / ".env"
load_dotenv(dotenv_path=ENV_FILE_PATH)

# The robot runner each episode follows for its settings.
ROBOT_RUNNERS = {
    0: "Episode_0_NAO.py",
    1: "Episode_1_NAO.py",
    2: "Episode_2_gigagiebels.py",
    3: "Episode_3_kapotte_intercom.py",
    4: "Episode_4_parkietenplaag.py",
}
SPEAKER_RATE = 24000          # laptop speaker; all audio is converted to this rate
LAPTOP_MIC_SAMPLE_RATE = 44100
PARTICIPANT_ID = os.getenv("PARTICIPANT_ID", "3")


class LaptopSpeakerAdapter(DesktopAdapter):
    """The desktop speaker plays everything at one fixed rate, so convert each sound to that rate first."""

    def play_audio_bytes(self, audio_bytes: bytes, sample_rate: int) -> None:
        if sample_rate and sample_rate != SPEAKER_RATE and audio_bytes:
            samples = np.frombuffer(audio_bytes, dtype=np.int16)
            n = max(1, int(round(len(samples) * SPEAKER_RATE / sample_rate)))
            positions = np.linspace(0, len(samples) - 1, n)
            audio_bytes = np.interp(positions, np.arange(len(samples)), samples).astype(np.int16).tobytes()
        super().play_audio_bytes(audio_bytes, SPEAKER_RATE)


def robot_runner_settings(episode: int) -> dict:
    """Read the dialog file, scene list and children's names from the episode's robot runner."""
    src = (BASE_DIR / ROBOT_RUNNERS[episode]).read_text(encoding="utf-8")
    files = re.findall(r'"(Episode_\w+?\.json)"', src)
    default = re.search(r'EPISODE_VERSION = os\.getenv\("EPISODE_VERSION", "(\w+)"\)', src)
    version = os.getenv("EPISODE_VERSION", default.group(1) if default else "kort").strip().lower()
    suffix = {"vol": "_all_dialogs.json", "kort": "_all_dialogs_kort.json", "3": "_all_dialogs_3.json"}[version]
    dialog_file = next(f for f in files if f.endswith(suffix))
    agenda_block = re.search(r"(?:session_agenda|SESSION_AGENDA) = \[(.*?)\n\s*\]", src, re.S).group(1)
    agenda = re.findall(r'^\s*"(Ep\d+_[^"]+)"', agenda_block, re.M)  # commented-out lines start with '#'
    names = dict(re.findall(r'"(user_\w+)":\s*"([^"]*)"', src))
    return {"dialog_file": dialog_file, "agenda": agenda, "names": names}


def fill_missing_character_definitions(dialogs) -> None:
    """Give every scene a voice for each character it uses, taken from other scenes if needed."""
    known = {}
    for d in dialogs:
        for name, definition in d.get("characters", {}).items():
            known.setdefault(name, definition)

    def used(node):
        if isinstance(node, dict):
            if isinstance(node.get("character"), str):
                yield node["character"]
            for v in node.values():
                yield from used(v)
        elif isinstance(node, list):
            for v in node:
                yield from used(v)

    for d in dialogs:
        chars = d.setdefault("characters", {})
        for name in used(d.get("moves", [])):
            if name not in chars and name in known:
                chars[name] = known[name]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Robot Detective episode on the laptop (no robot).")
    parser.add_argument("--episode", type=int, required=True, choices=sorted(ROBOT_RUNNERS))
    parser.add_argument("--typing", action="store_true", help="type the answers instead of speaking them")
    args = parser.parse_args()

    settings = robot_runner_settings(args.episode)
    print(f"[LAPTOP] Episode {args.episode}: {settings['dialog_file']}, {len(settings['agenda'])} scenes, "
          f"answers by {'typing' if args.typing else 'speaking'}")

    mic_index = None if args.typing else resolve_laptop_mic_index()
    if not args.typing:
        print(f"[LAPTOP] Microphone: {describe_laptop_mic(mic_index)}")
    laptop = Desktop(
        speakers_conf=SpeakersConf(sample_rate=SPEAKER_RATE),
        **({} if args.typing else {"mic_conf": MicrophoneConf(sample_rate=LAPTOP_MIC_SAMPLE_RATE,
                                                               device_index=mic_index)}),
    )
    device = LaptopSpeakerAdapter(laptop)

    tts = ElevenLabsTTSProvider(
        conf=ElevenLabsTTSConf(api_key=os.getenv("ELEVENLABS_API_KEY", ""), voice_id="f2yUVfK5jdm78zlpcZ8C",
                               model_id="eleven_flash_v2_5"),
        device=device,
    )
    if args.typing:
        nlu = WrittenKeywordNLUProvider()
    else:
        keyfile_json = json.loads(GOOGLE_KEYFILE_PATH.read_text(encoding="utf-8"))
        nlu = DialogflowNLUProvider(
            conf=DialogflowConf(keyfile_json=keyfile_json, sample_rate_hertz=LAPTOP_MIC_SAMPLE_RATE, language="nl"),
            mic=laptop.mic,
        )

    interaction_config = InteractionConfig(language="nl", post_speech_delay=0, signal_listening_behavior=False)
    interaction_config.chunk_audio = False  # same as on the robot: one request per line
    agent = ConversationAgent(
        device=device,
        tts_provider=tts,
        nlu_provider=nlu,
        llm_provider=make_llm_provider(),
        vector_store=RedisVectorStoreProvider(
            embedding_model="text-embedding-3-large",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            index_name=f"episode_{args.episode}_docs",
            ingest_docs=False,
            input_path=str(REPO_ROOT / "Detective_Data"),
        ),
        int_config=interaction_config,
    )

    all_dialogs = json.loads((JSON_DIR / settings["dialog_file"]).read_text(encoding="utf-8"))
    fill_missing_character_definitions(all_dialogs)
    by_id = {d["id"]: d for d in all_dialogs}
    agenda = [s for s in settings["agenda"] if s in by_id]
    with tempfile.NamedTemporaryFile(mode="w", suffix=f"_episode{args.episode}_laptop.json", delete=False,
                                     encoding="utf-8") as temp_file:
        json.dump([by_id[s] for s in agenda], temp_file, ensure_ascii=False, indent=2)

    session_manager = SessionManager(session_agenda=agenda, agent=agent, dialog_json_path=temp_file.name,
                                     participant_id=PARTICIPANT_ID)
    session_manager.conversation_state.user_model.update(settings["names"])

    # Typing mode reads answers from the keyboard, so then only Enter starts the episode.
    wait_for_start(device=device, nlu=None if args.typing else nlu)
    session_manager.run()


if __name__ == "__main__":
    main()

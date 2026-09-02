import json
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from runtime_patches import apply_runtime_patches

apply_runtime_patches()

from sic_framework.devices.common_desktop.desktop_speakers import SpeakersConf
from sic_framework.devices.desktop import Desktop

from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig
from nardial.providers.device.desktop import DesktopAdapter
from nardial.providers.llm.openai_gpt import OpenAIGPTProvider
from nardial.providers.nlu.written_keyword import WrittenKeywordNLUProvider
from nardial.providers.tts.elevenlabs import ElevenLabsTTSConf, ElevenLabsTTSProvider
from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider
from nardial.session_manager import SessionManager


load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "conf" / ".env")

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

DOCS_DIR = BASE_DIR / "Detective_Data"
DIALOG_CONFIG_PATH = REPO_ROOT / "RobotDetective_Narrative_Jsons" / "Episode_0_all_dialogs.json"
PARTICIPANT_ID = os.getenv("PARTICIPANT_ID", "0")
DEFAULT_RAG_INDEX_NAME = "episode_0_robin_docs"

# Set MANUAL_MODE=True to enable filtering session_agenda
MANUAL_MODE = True


def iter_referenced_characters(node):
    if isinstance(node, dict):
        character = node.get("character")
        if isinstance(character, str):
            yield character
        for value in node.values():
            yield from iter_referenced_characters(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_referenced_characters(item)


def populate_missing_character_definitions(dialogs) -> None:
    known_character_defs = {}
    for dialog in dialogs:
        for character_name, character_def in dialog.get("characters", {}).items():
            known_character_defs.setdefault(character_name, character_def)

    unresolved = []
    for dialog in dialogs:
        characters = dialog.setdefault("characters", {})
        missing_in_dialog = []

        for character_name in dict.fromkeys(iter_referenced_characters(dialog.get("moves", []))):
            if character_name in characters:
                continue

            character_def = known_character_defs.get(character_name)
            if character_def is None:
                missing_in_dialog.append(character_name)
                continue

            characters[character_name] = character_def

        if missing_in_dialog:
            unresolved.append(
                f"{dialog.get('id', '<unknown>')}: {', '.join(sorted(missing_in_dialog))}"
            )

    if unresolved:
        raise ValueError(
            "Dialogs reference characters without definitions: " + "; ".join(unresolved)
        )


if __name__ == "__main__":
    desktop = Desktop(speakers_conf=SpeakersConf(sample_rate=22050))
    device = DesktopAdapter(desktop)

    tts_conf = ElevenLabsTTSConf(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id="f2yUVfK5jdm78zlpcZ8C",
        model_id="eleven_flash_v2_5",
    )
    tts = ElevenLabsTTSProvider(conf=tts_conf, device=device)

    interaction_config = InteractionConfig(post_speech_delay=0, signal_listening_behavior=False)
    nlu = WrittenKeywordNLUProvider()
    llm = OpenAIGPTProvider(api_key=os.getenv("OPENAI_API_KEY"))

    vector_store = RedisVectorStoreProvider(
        embedding_model="text-embedding-3-large",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        index_name=DEFAULT_RAG_INDEX_NAME,
        ingest_docs=False,
        input_path=str(DOCS_DIR),
    )

    agent = ConversationAgent(
        device=device,
        tts_provider=tts,
        nlu_provider=nlu,
        llm_provider=llm,
        vector_store=vector_store,
        int_config=interaction_config,
    )

    # =========================
    # SESSION AGENDA
    # Comment/uncomment scenes below as needed:
    # =========================
    session_agenda = [
        #"Ep0_Scene_1_Intro",           # Intro & waking up
        # "Ep0_Scene_2_Smaragd_Flat",     # Flat De Smaragd & map review
         "Ep0_Scene_3_Question_Intro",   # Question tutorial

        "Ep0_Scene_4_Student_Practice",    # Student Q&A practice (in-narrative)
    ]

    active_dialog_json_path = str(DIALOG_CONFIG_PATH)

    if MANUAL_MODE:
        all_dialogs = json.loads(DIALOG_CONFIG_PATH.read_text(encoding="utf-8"))
        populate_missing_character_definitions(all_dialogs)
        dialogs_by_id = {d.get("id"): d for d in all_dialogs if d.get("id")}

        # Check for invalid scene IDs remaining in session_agenda
        missing = [scene_id for scene_id in session_agenda if scene_id not in dialogs_by_id]
        if missing:
            raise ValueError(
                f"session_agenda contains unknown dialog ids: {missing}\n"
                f"Available IDs in JSON: {list(dialogs_by_id.keys())}"
            )

        # Build a temporary JSON with ONLY the active (uncommented) scenes
        filtered_dialogs = [dialogs_by_id[scene_id] for scene_id in session_agenda]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_episode0_manual_dialogs.json", delete=False, encoding="utf-8"
        ) as temp_file:
            json.dump(filtered_dialogs, temp_file, ensure_ascii=False, indent=2)
            active_dialog_json_path = temp_file.name

        print(f"[MANUAL MODE] Active scene count: {len(session_agenda)}")
        print(f"[MANUAL MODE] Running scenes: {session_agenda}")

    session_manager = SessionManager(
        session_agenda=session_agenda,
        agent=agent,
        dialog_json_path=active_dialog_json_path,
        participant_id=PARTICIPANT_ID,
    )

    session_manager.run()
    sys.exit()
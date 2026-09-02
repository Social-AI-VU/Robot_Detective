"""
Robot Detective — Episode 1: De Verdwenen Achtbaan (The Missing Rollercoaster)
===============================================================================
Robin de Robotdetective helpt de kinderen bij het oplossen van het mysterie van
de verdwenen achtbaan in torenflat De Smaragd. De episode bestaat uit 8 scenes
met gestructureerde dialogen en open LLM-gesprekken per personage.

Dialogen:  RobotDetective_Narrative_Jsons/Episode_1_all_dialogs.json
Taal:      Nederlands (nl-NL)
Stem:      Google TTS — nl-NL-Wavenet-A

-------------------------
1. Install dependencies
-------------------------
    pip install nardial
    pip install social-interaction-cloud
    pip install --upgrade social-interaction-cloud[dialogflow,google-tts,openai-gpt]

-------------------------
2. Configure credentials
-------------------------
You MUST create the following files:

    conf/google/google-key.json   ← Google Cloud / Dialogflow service account key
    conf/.env                     ← OpenAI API key, e.g.:  OPENAI_API_KEY="your key"

WARNING: Never commit these files to version control.

-------------------------
3. Start required services
-------------------------
Run these in separate terminals BEFORE starting the episode:

    run-redis --data-dir RAG_Vectors
    run-dialogflow
    run-google-tts
    run-gpt
    run-redis
    run-elevenlabs-tts

-------------------------
4. Run the episode
-------------------------
    python RobotDetectiveEpisodeScripts/Episode_1.py
=========================
"""
import os
import sys
from os.path import abspath, join

from dotenv import load_dotenv
from sic_framework.devices.common_desktop.desktop_speakers import SpeakersConf
from runtime_patches import apply_runtime_patches

apply_runtime_patches()

from sic_framework.devices.desktop import Desktop

from nardial.providers.device.desktop import DesktopAdapter
from nardial.providers.tts.elevenlabs import ElevenLabsTTSProvider, ElevenLabsTTSConf
from nardial.providers.nlu.written_keyword import WrittenKeywordNLUProvider
from nardial.providers.llm.openai_gpt import OpenAIGPTProvider
from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider
from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig
from nardial.session_manager import SessionManager

# import other libraries
from pathlib import Path
import json
import os
import sys
import tempfile


load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "conf" / ".env")

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent


DOCS_DIR = BASE_DIR / "Detective_Data"
DIALOG_CONFIG_PATH = REPO_ROOT / "RobotDetective_Narrative_Jsons" / "Episode_1_all_dialogs.json"
GOOGLE_KEYFILE_PATH = REPO_ROOT / "conf" / "google" / "google-key.json"
ENV_FILE_PATH = REPO_ROOT / "conf" / ".env"

INDEX_NAME = "episode_1_trudy_docs"
INGEST_DOCS = False
PARTICIPANT_ID = os.getenv("PARTICIPANT_ID", "3")
RESET_PARTICIPANT_STATE = os.getenv("RESET_PARTICIPANT_STATE", "1").strip().lower() in {"1", "true", "yes", "y"}
AUDIO_HEARTBEAT = os.getenv("AUDIO_HEARTBEAT", "1").strip().lower() in {"1", "true", "yes", "y"}


DEFAULT_RAG_INDEX_NAME = "episode_1_trudy_docs"

# =========================
# MANUAL MODE SETTINGS
# =========================
# Set MANUAL_MODE=True to use manual commenting only.
# When True, SessionManager will only see dialogs that are in session_agenda.
# Just comment/uncomment scenes normally in session_agenda without errors.
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


def print_startup_checks() -> None:
    # Fast local checks to explain why ask_llm blocks can get skipped.
    print(f"[CHECK] Dialog JSON exists: {DIALOG_CONFIG_PATH.exists()} -> {DIALOG_CONFIG_PATH}")
    print(f"[CHECK] Google key exists: {GOOGLE_KEYFILE_PATH.exists()} -> {GOOGLE_KEYFILE_PATH}")
    print(f"[CHECK] Env file exists: {ENV_FILE_PATH.exists()} -> {ENV_FILE_PATH}")

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("[CHECK] OPENAI_API_KEY found in environment")
    else:
        print("[WARN] OPENAI_API_KEY missing in environment; ask_llm/llm_based can be skipped/fail")

    print(f"[CHECK] Participant ID: {PARTICIPANT_ID}")
    print(f"[CHECK] RESET_PARTICIPANT_STATE: {RESET_PARTICIPANT_STATE}")

    try:
        all_dialogs = json.loads(DIALOG_CONFIG_PATH.read_text(encoding="utf-8"))
        rag_blocks = [
            d for d in all_dialogs
            if d.get("type") == "llm_based" and d.get("rag_enabled")
        ]
        print(f"[CHECK] RAG-enabled dialog blocks: {[d.get('id') for d in rag_blocks]}")
        print(f"[CHECK] Default RAG index: {DEFAULT_RAG_INDEX_NAME}")
        for block in rag_blocks:
            print(
                f"[CHECK] {block.get('id')} -> index={block.get('index_name', DEFAULT_RAG_INDEX_NAME)}"
            )
    except Exception as exc:
        print(f"[WARN] Could not inspect rag_enabled dialogs: {exc}")

if __name__ == '__main__':
    # Select device
    desktop = Desktop(speakers_conf=SpeakersConf(sample_rate=22050))
    device = DesktopAdapter(desktop)
    # device = PepperAdapter(Pepper(ip="10.0.0.148"))

    tts_conf = ElevenLabsTTSConf(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id="f2yUVfK5jdm78zlpcZ8C",  # Robin
        model_id="eleven_flash_v2_5",
    )
    tts = ElevenLabsTTSProvider(conf=tts_conf, device=device)

    # =========================
    # 2. CONFIGURE INTERACTION
    # =========================



    interaction_config = InteractionConfig(post_speech_delay=0,
                                           signal_listening_behavior=False)
    nlu = WrittenKeywordNLUProvider()
    llm = OpenAIGPTProvider(api_key=os.getenv("OPENAI_API_KEY"))
    vector_store = RedisVectorStoreProvider(
        embedding_model="text-embedding-3-large",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        index_name=DEFAULT_RAG_INDEX_NAME,
        ingest_docs=False,
        input_path=str(DOCS_DIR),
    )

    # =========================
    # 3. CREATE AGENT
    # =========================
    agent = ConversationAgent(device=device,
                              tts_provider=tts,
                              nlu_provider=nlu,
                              llm_provider=llm,
                              vector_store=vector_store,
                              int_config=interaction_config)

    # =========================
    # 4. DEFINE SESSION STRUCTURE
    # =========================
    # Each entry must match the "id" field of a dialog in Episode_1_all_dialogs.json.
    # Scenes play in order; LLM chats follow their paired scene.

    session_agenda = [
       # "Ep1_Scene_1_Intro",  # intro + meet Robin, collect name
       # "Ep1_Scene_2_Toon_Rami",  # Toon & Rami report the missing rollercoaster
        #"Ep1_Scene_3_Trudy",  # interview Trudy (karaoke plan)
        "Ep1_Scene_3_Trudy_RAG_Interview",  # RAG-backed Trudy interview
        "Ep1_Scene_4_Eddy",  # interview Professor Eddy (puzzl=e)
        "Ep1_Scene_4_Eddy_RAG_Interview",  # RAG-backed Eddy interview
        "Ep1_Scene_5_Yoyo",
        "Ep1_Scene_5_Yoyo_RAG_Interview", # interview Yoyo RAG
        "Ep1_Scene_6_Jennifer",  # interview Jennifer
        "Ep1_Scene_6_Jennifer_LLM_Chat",  # initial LLM chat with Jennifer
        "Ep1_Scene_6_Jennifer_RAG_Interview",  # RAG-backed Jennifer interview
        "Ep1_Scene_7_Dj_Kata",  # interview DJ Kata
        "Ep1_Scene_7_Dj_Kata_LLM_Chat",  # RAG-backed DJ Kata interview
        "Ep1_Scene_8_Ontknoping",
        "Ep1_Scene_9_Kelder_Disco"
    ]

    active_dialog_json_path = str(DIALOG_CONFIG_PATH)
    if MANUAL_MODE:
        all_dialogs = json.loads(DIALOG_CONFIG_PATH.read_text(encoding="utf-8"))
        populate_missing_character_definitions(all_dialogs)
        dialogs_by_id = {d.get("id"): d for d in all_dialogs if d.get("id")}
        missing = [scene_id for scene_id in session_agenda if scene_id not in dialogs_by_id]
        if missing:
            raise ValueError(f"session_agenda contains unknown dialog ids: {missing}")

        # Preserve agenda order and strip unrelated dialogs so manual commenting just works.
        filtered_dialogs = [dialogs_by_id[scene_id] for scene_id in session_agenda]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_episode1_manual_dialogs.json", delete=False, encoding="utf-8"
        ) as temp_file:
            json.dump(filtered_dialogs, temp_file, ensure_ascii=False, indent=2)
            active_dialog_json_path = temp_file.name

        print(f"[MANUAL MODE] Active scene count: {len(session_agenda)}")
        print(f"[MANUAL MODE] Using filtered dialog file: {active_dialog_json_path}")

    # =========================
    # 5. SESSION MANAGER
    # =========================

    session_manager = SessionManager(
        session_agenda=session_agenda,
        agent=agent,
        dialog_json_path=active_dialog_json_path,
        participant_id=PARTICIPANT_ID,
    )

    # =========================
    # 6. RUN SESSION
    # =========================


    session_manager.run()

    sys.exit()
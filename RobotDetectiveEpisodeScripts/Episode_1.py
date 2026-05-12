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

    conf/redis/redis-server.exe conf/redis/redis.conf
    run-dialogflow
    run-google-tts
    run-gpt

-------------------------
4. Run the episode
-------------------------
    python RobotDetectiveEpisodeScripts/Episode_1.py
=========================
"""

from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig
from nardial.session_manager import SessionManager
from nardial.tts_manager import GoogleTTSConf

# Import SIC device(s), message(s), and service(s) we will be using
from sic_framework.devices.common_desktop.desktop_speakers import SpeakersConf
from sic_framework.devices.desktop import Desktop

# import other libraries
from pathlib import Path
import json
import os
import sys
import tempfile


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent


DOCS_DIR = BASE_DIR / "Detective_Data" / "Ep1_Trudy"
DIALOG_CONFIG_PATH = REPO_ROOT / "RobotDetective_Narrative_Jsons" / "Episode_1_all_dialogs.json"
GOOGLE_KEYFILE_PATH = REPO_ROOT / "conf" / "google" / "google-key.json"
ENV_FILE_PATH = REPO_ROOT / "conf" / ".env"

INDEX_NAME = "episode_1_trudy_docs"
INGEST_DOCS = False


DEFAULT_RAG_INDEX_NAME = "episode_1_trudy_docs"

# =========================
# MANUAL MODE SETTINGS
# =========================
# Set MANUAL_MODE=True to use manual commenting only.
# When True, SessionManager will only see dialogs that are in session_agenda.
# Just comment/uncomment scenes normally in session_agenda without errors.
MANUAL_MODE = True


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
    print_startup_checks()

    # =========================
    # 1. SELECT DEVICE
    # =========================
    # Desktop uses your computer's mic + speakers.
    # Uncomment the Pepper line to connect to a robot instead.

    device = Desktop(
        speakers_conf=SpeakersConf(sample_rate=22050)
    )
    # device = Pepper(ip="XXX")  # Replace with your robot's IP

    # =========================
    # 2. CONFIGURE INTERACTION
    # =========================

    interaction_config = InteractionConfig(
        google_keyfile_path=str(GOOGLE_KEYFILE_PATH),
        env_file_path=str(ENV_FILE_PATH),
        keyboard_input=True,
        rag=True,
        ingest_docs=INGEST_DOCS,
        input_path=str(DOCS_DIR),
        index_name=INDEX_NAME,
        embedding_model="text-embedding-3-large",
        chunk_chars=900,
        chunk_overlap=120,
        override_existing=True,
        force_recreate_index=False,
        tts_conf=GoogleTTSConf(
            speaking_rate=1.0,
            google_tts_voice_name="nl-NL-Wavenet-A",
            google_tts_voice_gender="FEMALE"
        ),
        language="nl",
        # microphone_device=1,         # uncomment to select a specific mic
        post_speech_delay=0.5,       # pause in seconds after the agent speaks
        # signal_listening_behavior=True,  # visual cue while listening (robots)
    )

    # interaction_config = InteractionConfig(
    #     google_keyfile_path=GOOGLE_KEYFILE_PATH,
    #     keyboard_input=True,           # set False to use microphone instead
    #     env_file_path=ENV_FILE_PATH,
    #     rag=True,
    #     ingest_docs=INGEST_DOCS,
    #     input_path=str(DOCS_DIR),
    #     index_name=INDEX_NAME,
    #     embedding_model="text-embedding-3-large",
    #     chunk_chars=900,
    #     chunk_overlap=120,
    #     override_existing=False,
    #     force_recreate_index=False,
    #     tts_conf=GoogleTTSConf(
    #         speaking_rate=1.0,
    #         google_tts_voice_name="nl-NL-Wavenet-A",
    #         google_tts_voice_gender="FEMALE"
    #     ),
    #     language="nl",
    #     # microphone_device=1,         # uncomment to select a specific mic
    #     # post_speech_delay=0.5,       # pause in seconds after the agent speaks
    #     # signal_listening_behavior=True,  # visual cue while listening (robots)
    # )

    # =========================
    # 3. CREATE AGENT
    # =========================
    agent = ConversationAgent(
        device_manager=device,
        int_config=interaction_config
    )



    # =========================
    # 4. DEFINE SESSION STRUCTURE
    # =========================
    # Each entry must match the "id" field of a dialog in Episode_1_all_dialogs.json.
    # Scenes play in order; LLM chats follow their paired scene.



    session_agenda = [
        #"Ep1_Scene_1_Intro",  # intro + meet Robin, collect name
        #"Ep1_Scene_2_Toon_Rami",  # Toon & Rami report the missing rollercoaster
        "Ep1_Scene_3_Trudy",  # interview Trudy (karaoke plan)
        "Ep1_Scene_3_Trudy_RAG_Interview",  # RAG-backed Trudy interview
        "Ep1_Scene_4_Eddy",  # interview Professor Eddy (puzzle)
        "Ep1_Scene_5_Yoyo",  # interview Yoyo (alibi)
        "Ep1_Scene_5_Yoyo_LLM_Chat",  # RAG-backed Yoyo interview
        "Ep1_Scene_6_Jennifer",  # interview Jennifer
        "Ep1_Scene_6_Jennifer_LLM_Chat",  # RAG-backed Jennifer interview
        "Ep1_Scene_7_Dj_Kata",  # interview DJ Kata
        "Ep1_Scene_7_Dj_Kata_LLM_Chat",  # RAG-backed DJ Kata interview
        "Ep1_Scene_8_Ontknoping",  # denouement — wrap up the mystery
    ]

    active_dialog_json_path = str(DIALOG_CONFIG_PATH)
    if MANUAL_MODE:
        all_dialogs = json.loads(DIALOG_CONFIG_PATH.read_text(encoding="utf-8"))
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
        participant_id="2",
    )

    # =========================
    # 6. RUN SESSION
    # =========================
    session_manager.run()

    sys.exit()
r"""
Robot Detective — Episode 1 (NAO, laptop microphone)
====================================================
Copy of Episode_1_NAO.py that listens through the LAPTOP microphone instead of the NAO's own
microphones. Everything else (speech, gestures, eye colours, the beep) still happens on the NAO.
Optional: LAPTOP_MIC_NAME=<name> (or LAPTOP_MIC_INDEX=<number>) in conf/.env to pick the
microphone; see laptop_mic.py and `python utils/mic_check.py list`.

NAO-specific variant of Episode_1.py. This version uses:

- NAO microphone input via Dialogflow
- NAO speakers for ElevenLabs audio playback

Before running:

    run-redis --data-dir RAG_Vectors
    run-dialogflow
    run-elevenlabs-tts
    & "C:\\Users\\viq021\\repositories\\Robot_Detective\\conf\\redis\\redis-server.exe" "C:\\Users\\viq021\\repositories\\Robot_Detective\\conf\\redis\\redis.conf"

Then start the episode with:

    python RobotDetectiveEpisodeScripts/Episode_1_NAO_laptop_mic.py

Environment variables:


"""
import json
import os
import sys
import tempfile
from pathlib import Path

from nardial.providers.device import AnimationStyle


_REPO_ROOT_FOR_IMPORT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT_FOR_IMPORT not in sys.path:
    sys.path.insert(0, _REPO_ROOT_FOR_IMPORT)

from runtime_patches import apply_runtime_patches

apply_runtime_patches()

from dotenv import load_dotenv
from sic_framework.devices import Nao
from sic_framework.devices.common_desktop.desktop_microphone import MicrophoneConf
from sic_framework.devices.desktop import Desktop

from laptop_mic import describe_laptop_mic, resolve_laptop_mic_index
from sic_framework.services.dialogflow.dialogflow import DialogflowConf

from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_motion import NaoPostureRequest

from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig
from nardial.providers.device.nao import NaoAdapter
from nardial.providers.nlu.dialogflow import DialogflowNLUProvider
from local_llm import make_llm_provider  # OpenAI or a local model, see LLM_BACKEND in conf/.env
from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider
from nardial.providers.tts.elevenlabs import ElevenLabsTTSConf, ElevenLabsTTSProvider
from nardial.session_manager import SessionManager

from start_gate import connect_nao, log_startup, wait_for_start


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

DOCS_DIR = BASE_DIR / "Detective_Data"
# Which version of the episode (made by utils/make_short_episodes.py):
#   "vol"  = the full episode
#   "kort" = short version, 5 interviews (~60-65 min)
#   "3"    = 3 interviews + 2 note-keepers (~50 min); set the note-keepers' names below
# The launcher overrides this with the EPISODE_VERSION environment variable.
# Scenes in the agenda that a version leaves out are skipped.
EPISODE_VERSION = os.getenv("EPISODE_VERSION", "kort").strip().lower()
USE_SHORT_VERSION = EPISODE_VERSION != "vol"
DIALOG_CONFIG_PATH = REPO_ROOT / "RobotDetective_Narrative_Jsons" / {
    "vol": "Episode_1_all_dialogs.json",
    "kort": "Episode_1_all_dialogs_kort.json",
    "3": "Episode_1_all_dialogs_3.json",
}[EPISODE_VERSION]
GOOGLE_KEYFILE_PATH = REPO_ROOT / "conf" / "google" / "google-key.json"
ENV_FILE_PATH = REPO_ROOT / "conf" / ".env"

# Load conf/.env BEFORE reading any os.getenv()-based settings below,
# otherwise values like NAO_IP silently fall back to their hardcoded
# defaults even when set in the .env file.
load_dotenv(dotenv_path=ENV_FILE_PATH)

INDEX_NAME = "episode_1_trudy_docs"
INGEST_DOCS = False
PARTICIPANT_ID = os.getenv("PARTICIPANT_ID", "3")
RESET_PARTICIPANT_STATE = os.getenv("RESET_PARTICIPANT_STATE", "1").strip().lower() in {"1", "true", "yes", "y"}
AUDIO_HEARTBEAT = os.getenv("AUDIO_HEARTBEAT", "1").strip().lower() in {"1", "true", "yes", "y"}
# 44100 Hz is what laptop microphones support natively (also used by the SIC desktop demos).
LAPTOP_MIC_SAMPLE_RATE = 44100
# Which laptop microphone: LAPTOP_MIC_NAME or LAPTOP_MIC_INDEX in conf/.env (see laptop_mic.py).
LAPTOP_MIC_INDEX = resolve_laptop_mic_index()
NAO_IP = os.getenv("NAO_IP", "192.168.178.67") #192.168.0.250 home
NAO_LISTEN_TIMEOUT_SEC = float(os.getenv("NAO_LISTEN_TIMEOUT_SEC", "12"))  # applied in runtime_patches.py

DEFAULT_RAG_INDEX_NAME = "episode_1_trudy_docs"

# =========================
# MANUAL MODE SETTINGS
# =========================
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
    print(f"[CHECK] Dialog JSON exists: {DIALOG_CONFIG_PATH.exists()} -> {DIALOG_CONFIG_PATH}")
    print(f"[CHECK] Google key exists: {GOOGLE_KEYFILE_PATH.exists()} -> {GOOGLE_KEYFILE_PATH}")
    print(f"[CHECK] Env file exists: {ENV_FILE_PATH.exists()} -> {ENV_FILE_PATH}")
    print(f"[CHECK] NAO_IP: {NAO_IP}")
    print(f"[CHECK] Microphone: laptop, {describe_laptop_mic(LAPTOP_MIC_INDEX)}")
    print(f"[CHECK] NAO_LISTEN_TIMEOUT_SEC: {os.getenv('NAO_LISTEN_TIMEOUT_SEC', '12')}")

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


if __name__ == "__main__":
    load_dotenv(dotenv_path=ENV_FILE_PATH)
    print_startup_checks()



    nao = connect_nao(NAO_IP)  # skips SIC's slow install check on the robot, see start_gate.py
    device = NaoAdapter(nao)

    nao.motion.request(NaoPostureRequest("Stand", 0.8))
    log_startup("robot standing")

    tts_conf = ElevenLabsTTSConf(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id="f2yUVfK5jdm78zlpcZ8C",  # Robin
        model_id="eleven_flash_v2_5",
    )
    tts = ElevenLabsTTSProvider(conf=tts_conf, device=device)

    # Listen through the laptop microphone; only the microphone of the laptop is started,
    # so all speech still comes out of the NAO.
    laptop = Desktop(mic_conf=MicrophoneConf(
        sample_rate=LAPTOP_MIC_SAMPLE_RATE,
        device_index=LAPTOP_MIC_INDEX,
    ))
    keyfile_json = json.loads(GOOGLE_KEYFILE_PATH.read_text(encoding="utf-8"))
    nlu = DialogflowNLUProvider(
        conf=DialogflowConf(keyfile_json=keyfile_json, sample_rate_hertz=LAPTOP_MIC_SAMPLE_RATE, language="nl"),
        mic=laptop.mic,
    )

    interaction_config = InteractionConfig(
        language="nl",
        post_speech_delay=0,
        signal_listening_behavior=True,
    )
    interaction_config.animation_style = AnimationStyle.EXPRESSIVE
    # Synthesize each line in one piece instead of per sentence: saves ~2 s per sentence on the NAO.
    interaction_config.chunk_audio = False
    llm = make_llm_provider()
    vector_store = RedisVectorStoreProvider(
        embedding_model="text-embedding-3-large",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        index_name=DEFAULT_RAG_INDEX_NAME,
        ingest_docs=False,
        input_path=str(DOCS_DIR),
    )

    log_startup("TTS, mic, NLU, LLM ready")
    agent = ConversationAgent(
        device=device,
        tts_provider=tts,
        nlu_provider=nlu,
        llm_provider=llm,
        vector_store=vector_store,
        int_config=interaction_config,
    )

    session_agenda = [
          "Ep1_Scene_1_Intro",  # intro + meet Robin, collect name
        "Ep1_Scene_2_Toon_Rami",  # Toon & Rami report the missing rollercoaster
        "Ep1_Scene_3_Trudy",  # interview Trudy (karaoke plan)
        "Ep1_Scene_3_Trudy_RAG_Chitchat",  # RAG-backed Trudy chitchat
        "Ep1_Scene_3_Trudy_After_Chitchat",  # Robin/trudy bridge after chitchat
        "Ep1_Scene_3_Trudy_RAG_Interview",  # RAG-backed Trudy interview
        "Ep1_Scene_3_Trudy_Interview_Laatste_RAG",
       "Ep1_Scene_3_Trudy_RAG_Interview_Laatste_Vraag",
        "Ep1_Scene_3_Trudy_After_Interview",
          "Ep1_Scene_4_Eddy",  # intro Eddy
           "Ep1_Scene_4_Eddy_RAG_Chitchat",  # Eddy chitchat
          "Ep1_Scene_4_Eddy_After_Chitchat",  # bridge after Eddy chitchat
           "Ep1_Scene_4_Eddy_RAG_Interview",  # RAG-backed Eddy interview
           "Ep1_Scene_4_Eddy_Interview_Laatste_RAG",  # last-question setup
           "Ep1_Scene_4_Eddy_RAG_Interview_Laatste_Vraag",  # final Eddy clue
           "Ep1_Scene_4_Eddy_Interview_Afsluiten",  # close Eddy scene
           "Ep1_Scene_5_Yoyo",
            "Ep1_Scene_5_Yoyo_RAG_Chitchat",
           "Ep1_Scene_5_Yoyo_After_Chitchat",
           "Ep1_Scene_5_Yoyo_RAG_Interview",# interview Yoyo RAG
           "Ep1_Scene_5_Yoyo_Interview_Laatste_RAG",
           "Ep1_Scene_5_Yoyo_RAG_Interview_Laatste_Vraag",
           "Ep1_Scene_5_Yoyo_Interview_Afsluiten",

          "Ep1_Scene_6_Jennifer",
           "Ep1_Scene_6_Jennifer_RAG_Chitchat",
           "Ep1_Scene_6_Jennifer_After_Chitchat",
          "Ep1_Scene_6_Jennifer_RAG_Interview",
           "Ep1_Scene_6_Jennifer_Interview_Laatste_RAG",
           "Ep1_Scene_6_Jennifer_RAG_Interview_Laatste_Vraag",
           "Ep1_Scene_6_Jennifer_Interview_Afsluiten",
        "Ep1_Scene_7_Dj_Kata",
        "Ep1_Scene_7_Dj_Kata_RAG_Chitchat",  # Kata chitchat over muziek
        "Ep1_Scene_7_Dj_Kata_After_Chitchat",  # bridge naar Kata interview
        "Ep1_Scene_7_Dj_Kata_RAG_Interview",  # RAG-backed Kata interview
        "Ep1_Scene_7_Dj_Kata_Interview_Laatste_RAG",  # last-question setup
        "Ep1_Scene_7_Dj_Kata_RAG_Interview_Laatste_Vraag",  # final Kata clue
        "Ep1_Scene_7_Dj_Kata_Interview_Afsluiten",  # close Kata scene
        "Ep1_Scene_8_Ontknoping",
        "Ep1_Scene_9_Trilling",  # flat trilt, glijbaan naar de kelder
        "Ep1_Scene_10_Kelder_Disco",  # onthulling onder het glitterdoek
        "Ep1_Scene_11_Outro",  # outro Stoep Tegel
    ]

    active_dialog_json_path = str(DIALOG_CONFIG_PATH)
    if MANUAL_MODE:
        all_dialogs = json.loads(DIALOG_CONFIG_PATH.read_text(encoding="utf-8"))
        populate_missing_character_definitions(all_dialogs)
        dialogs_by_id = {d.get("id"): d for d in all_dialogs if d.get("id")}
        if USE_SHORT_VERSION:
            session_agenda = [scene_id for scene_id in session_agenda if scene_id in dialogs_by_id]
        missing = [scene_id for scene_id in session_agenda if scene_id not in dialogs_by_id]
        if missing:
            raise ValueError(f"session_agenda contains unknown dialog ids: {missing}")

        filtered_dialogs = [dialogs_by_id[scene_id] for scene_id in session_agenda]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_episode1_nao_laptop_mic_manual_dialogs.json", delete=False, encoding="utf-8"
        ) as temp_file:
            json.dump(filtered_dialogs, temp_file, ensure_ascii=False, indent=2)
            active_dialog_json_path = temp_file.name

        print(f"[MANUAL MODE] Active scene count: {len(session_agenda)}")
        print(f"[MANUAL MODE] Using filtered dialog file: {active_dialog_json_path}")

    session_manager = SessionManager(
        session_agenda=session_agenda,
        agent=agent,
        dialog_json_path=active_dialog_json_path,
        participant_id=PARTICIPANT_ID,
    )

    try:
        session_manager.conversation_state.user_model.update({"user_trudy": "Anita"})
        session_manager.conversation_state.user_model.update({"user_eddy": "Lilly"})
        session_manager.conversation_state.user_model.update({"user_yoyo": "Julianna"})
        session_manager.conversation_state.user_model.update({"user_jennifer": "Eva"})
        session_manager.conversation_state.user_model.update({"user_kata": "Reachy"})
        # Only used in the 3-interview version: the two note-keepers.
        session_manager.conversation_state.user_model.update({"user_notulist_1": "Anita"})
        session_manager.conversation_state.user_model.update({"user_notulist_2": "Lilly"})
        session_manager.conversation_state.user_model.update({"user_teacher": "Soyun3"})
        # Wait for Enter, a touch on the NAO's head/chest, or the word 'start'.
        wait_for_start(nao=nao, device=device, nlu=nlu)
        session_manager.run()
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        nao.autonomous.request(NaoRestRequest())

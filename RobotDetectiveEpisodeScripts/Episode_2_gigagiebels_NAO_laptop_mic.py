r"""
Robot Detective — Episode 2: Het mysterie van de Gigagiebels (NAO, laptop microphone)
=====================================================================================
Copy of Episode_2_gigagiebels.py that listens through the LAPTOP microphone instead of the NAO's own
microphones. Everything else (speech, gestures, eye colours, the beep) still happens on the NAO.
Optional: LAPTOP_MIC_NAME=<name> (or LAPTOP_MIC_INDEX=<number>) in conf/.env to pick the
microphone; see laptop_mic.py and `python utils/mic_check.py list`.

Same setup as Episode_1_NAO.py:

- NAO microphone input via Dialogflow
- NAO speakers for ElevenLabs audio playback

Before running:

    run-redis --data-dir RAG_Vectors
    run-dialogflow
    run-elevenlabs-tts

Ingest this episode's character knowledge once (RAG_Vectors/RAG_Ingestion_Episodes_2_4.py),
then start the episode from the repository root (sound effects are looked up in ./sounds):

    python RobotDetectiveEpisodeScripts/Episode_2_gigagiebels_NAO_laptop_mic.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

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
from nardial.providers.device import AnimationStyle
from nardial.providers.device.nao import NaoAdapter
from nardial.providers.nlu.dialogflow import DialogflowNLUProvider
from local_llm import make_llm_provider  # OpenAI or a local model, see LLM_BACKEND in conf/.env
from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider
from nardial.providers.tts.elevenlabs import ElevenLabsTTSConf, ElevenLabsTTSProvider
from nardial.session_manager import SessionManager

from start_gate import connect_nao, log_startup, wait_for_start


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

DOCS_DIR = REPO_ROOT / "Detective_Data" / "Episode_2_Detective_Data"
# Which version of the episode (made by utils/make_short_episodes.py):
#   "vol"  = the full episode
#   "kort" = short version, 5 interviews (~60-65 min)
#   "3"    = 3 interviews + 2 note-keepers (~50 min); set the note-keepers' names below
# The launcher overrides this with the EPISODE_VERSION environment variable.
# Scenes in the agenda that a version leaves out are skipped.
EPISODE_VERSION = os.getenv("EPISODE_VERSION", "kort").strip().lower()
USE_SHORT_VERSION = EPISODE_VERSION != "vol"
DIALOG_CONFIG_PATH = REPO_ROOT / "RobotDetective_Narrative_Jsons" / {
    "vol": "Episode_2_gigagiebels_all_dialogs.json",
    "kort": "Episode_2_gigagiebels_all_dialogs_kort.json",
    "3": "Episode_2_gigagiebels_all_dialogs_3.json",
}[EPISODE_VERSION]
GOOGLE_KEYFILE_PATH = REPO_ROOT / "conf" / "google" / "google-key.json"
ENV_FILE_PATH = REPO_ROOT / "conf" / ".env"

load_dotenv(dotenv_path=ENV_FILE_PATH)

PARTICIPANT_ID = os.getenv("PARTICIPANT_ID", "3")
# 16000 Hz: what Google recommends for speech recognition, and 2.75x less audio to upload than 44100 Hz.
# On a slow connection (phone hotspot) 44100 Hz made the stream lag behind, so transcripts came in late
# and pieces of speech were lost. Set LAPTOP_MIC_SAMPLE_RATE=44100 in conf/.env if a microphone
# does not support 16000.
LAPTOP_MIC_SAMPLE_RATE = int(os.getenv("LAPTOP_MIC_SAMPLE_RATE", "16000"))
# Which laptop microphone: LAPTOP_MIC_NAME or LAPTOP_MIC_INDEX in conf/.env (see laptop_mic.py).
LAPTOP_MIC_INDEX = resolve_laptop_mic_index()
NAO_IP = os.getenv("NAO_IP", "192.168.0.250")
DEFAULT_RAG_INDEX_NAME = "episode_2_heike_docs"

# Names of the children, keyed by the character each child interviews.
USER_NAMES = {
    "user_heike": "Anita",
    "user_choukri": "Smita",
    "user_eddy": "Frita",
    "user_jennifer": "Mimimimi2",
    "user_toon": "Mimimimi",
    # Only used in the 3-interview version: the two note-keepers.
    "user_notulist_1": "Notulist1",
    "user_notulist_2": "Notulist2",
    "user_teacher": "Juffrouw Egel",
}

SESSION_AGENDA = [
  #  "Ep2_Scene_1_Intro",
   # "Ep2_Scene_2_Mysterie",
  #  "Ep2_Scene_3_Robin_Intro",
    # "Ep2_Scene_3_Robin_Oefenvragen",  # chitchat skipped; Robin_Intro now explains the beep and green eyes
    "Ep2_Scene_3_Robin_Spelregels",
    "Ep2_Scene_4_Rebus",
    "Ep2_Scene_5_Heike",
    "Ep2_Scene_5_Heike_RAG_Chitchat",
    "Ep2_Scene_5_Heike_After_Chitchat",
    "Ep2_Scene_5_Heike_RAG_Interview",
    "Ep2_Scene_5_Heike_Interview_Laatste_RAG",
    "Ep2_Scene_5_Heike_RAG_Interview_Laatste_Vraag",
    "Ep2_Scene_5_Heike_Interview_Afsluiten",
    "Ep2_Scene_6_Choukri",
    "Ep2_Scene_6_Choukri_RAG_Chitchat",
    "Ep2_Scene_6_Choukri_After_Chitchat",
    "Ep2_Scene_6_Choukri_RAG_Interview",
    "Ep2_Scene_6_Choukri_Interview_Laatste_RAG",
    "Ep2_Scene_6_Choukri_RAG_Interview_Laatste_Vraag",
    "Ep2_Scene_6_Choukri_Interview_Afsluiten",
    "Ep2_Scene_7_Eddy",
    "Ep2_Scene_7_Eddy_RAG_Chitchat",
    "Ep2_Scene_7_Eddy_After_Chitchat",
    "Ep2_Scene_7_Eddy_RAG_Interview",
    "Ep2_Scene_7_Eddy_Interview_Laatste_RAG",
    "Ep2_Scene_7_Eddy_RAG_Interview_Laatste_Vraag",
    "Ep2_Scene_7_Eddy_Interview_Afsluiten",
    "Ep2_Scene_7b_Jennifer",
    "Ep2_Scene_7b_Jennifer_RAG_Chitchat",
    "Ep2_Scene_7b_Jennifer_After_Chitchat",
    "Ep2_Scene_7b_Jennifer_RAG_Interview",
    "Ep2_Scene_7b_Jennifer_Interview_Laatste_RAG",
    "Ep2_Scene_7b_Jennifer_RAG_Interview_Laatste_Vraag",
    "Ep2_Scene_7b_Jennifer_Interview_Afsluiten",
    "Ep2_Scene_8_Tegel_Belt",
    "Ep2_Scene_9_Toon_Rami",
    "Ep2_Scene_9_Toon_Rami_RAG_Chitchat",
    "Ep2_Scene_9_Toon_Rami_After_Chitchat",
    "Ep2_Scene_9_Toon_Rami_RAG_Interview",
    "Ep2_Scene_9_Toon_Rami_Interview_Laatste_RAG",
    "Ep2_Scene_9_Toon_Rami_RAG_Interview_Laatste_Vraag",
    "Ep2_Scene_9_Toon_Rami_Interview_Afsluiten",
    "Ep2_Scene_10_Ontknoping",
]


def print_startup_checks() -> None:
    print(f"[CHECK] Dialog JSON exists: {DIALOG_CONFIG_PATH.exists()} -> {DIALOG_CONFIG_PATH}")
    print(f"[CHECK] Google key exists: {GOOGLE_KEYFILE_PATH.exists()} -> {GOOGLE_KEYFILE_PATH}")
    print(f"[CHECK] NAO_IP: {NAO_IP}")
    print(f"[CHECK] Microphone: laptop, {describe_laptop_mic(LAPTOP_MIC_INDEX)}")
    if not os.getenv("OPENAI_API_KEY"):
        print("[WARN] OPENAI_API_KEY missing in environment; llm_based scenes will fail")
    print(f"[CHECK] Participant ID: {PARTICIPANT_ID}")


if __name__ == "__main__":
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

    # Only the scenes in SESSION_AGENDA are loaded, so commenting a scene out skips it
    # without tripping nardial's position-order check.
    all_dialogs = json.loads(DIALOG_CONFIG_PATH.read_text(encoding="utf-8"))
    dialogs_by_id = {d["id"]: d for d in all_dialogs}
    if USE_SHORT_VERSION:
        SESSION_AGENDA = [scene_id for scene_id in SESSION_AGENDA if scene_id in dialogs_by_id]
    missing = [scene_id for scene_id in SESSION_AGENDA if scene_id not in dialogs_by_id]
    if missing:
        raise ValueError(f"SESSION_AGENDA contains unknown dialog ids: {missing}")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_episode2_nao_laptop_mic_dialogs.json", delete=False, encoding="utf-8"
    ) as temp_file:
        json.dump([dialogs_by_id[s] for s in SESSION_AGENDA], temp_file, ensure_ascii=False, indent=2)
        active_dialog_json_path = temp_file.name

    session_manager = SessionManager(
        session_agenda=SESSION_AGENDA,
        agent=agent,
        dialog_json_path=active_dialog_json_path,
        participant_id=PARTICIPANT_ID,
    )

    try:
        session_manager.conversation_state.user_model.update(USER_NAMES)
        # Wait for Enter, a touch on the NAO's head/chest, or the word 'start'.
        wait_for_start(nao=nao, device=device, nlu=nlu)
        session_manager.run()
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        nao.autonomous.request(NaoRestRequest())

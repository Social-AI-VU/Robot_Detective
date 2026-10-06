r"""
Robot Detective — Episode 2: Het mysterie van de Gigagiebels (NAO)
==================================================================
Same setup as Episode_1_NAO.py:

- NAO microphone input via Dialogflow
- NAO speakers for ElevenLabs audio playback

Before running:

    run-redis --data-dir RAG_Vectors
    run-dialogflow
    run-elevenlabs-tts

Ingest this episode's character knowledge once (RAG_Vectors/RAG_Ingestion_Episodes_2_4.py),
then start the episode from the repository root (sound effects are looked up in ./sounds):

    python RobotDetectiveEpisodeScripts/Episode_2_gigagiebels.py
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
from sic_framework.services.dialogflow.dialogflow import DialogflowConf

from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_motion import NaoPostureRequest

from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig
from nardial.providers.device import AnimationStyle
from nardial.providers.device.nao import NaoAdapter
from nardial.providers.nlu.dialogflow import DialogflowNLUProvider
from nardial.providers.llm.openai_gpt import OpenAIGPTProvider
from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider
from nardial.providers.tts.elevenlabs import ElevenLabsTTSConf, ElevenLabsTTSProvider
from nardial.session_manager import SessionManager


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

DOCS_DIR = REPO_ROOT / "Detective_Data" / "Episode_2_Detective_Data"
DIALOG_CONFIG_PATH = REPO_ROOT / "RobotDetective_Narrative_Jsons" / "Episode_2_gigagiebels_all_dialogs.json"
GOOGLE_KEYFILE_PATH = REPO_ROOT / "conf" / "google" / "google-key.json"
ENV_FILE_PATH = REPO_ROOT / "conf" / ".env"

load_dotenv(dotenv_path=ENV_FILE_PATH)

PARTICIPANT_ID = os.getenv("PARTICIPANT_ID", "3")
NAO_IP = os.getenv("NAO_IP", "192.168.0.250")
DEFAULT_RAG_INDEX_NAME = "episode_2_heike_docs"

# Names of the children, keyed by the character each child interviews.
USER_NAMES = {
    "user_heike": "Anita",
    "user_choukri": "Smita",
    "user_eddy": "Frita",
    "user_rami": "Mimimimi",
    "user_teacher": "Juffrouw Egel",
}

SESSION_AGENDA = [
    "Ep2_Scene_1_Intro",
    "Ep2_Scene_2_Mysterie",
    "Ep2_Scene_3_Robin_Intro",
    "Ep2_Scene_3_Robin_Oefenvragen",
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
    if not os.getenv("OPENAI_API_KEY"):
        print("[WARN] OPENAI_API_KEY missing in environment; llm_based scenes will fail")
    print(f"[CHECK] Participant ID: {PARTICIPANT_ID}")


if __name__ == "__main__":
    print_startup_checks()

    nao = Nao(ip=NAO_IP)
    device = NaoAdapter(nao)
    nao.motion.request(NaoPostureRequest("Stand", 0.8))

    tts_conf = ElevenLabsTTSConf(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id="f2yUVfK5jdm78zlpcZ8C",  # Robin
        model_id="eleven_flash_v2_5",
    )
    tts = ElevenLabsTTSProvider(conf=tts_conf, device=device)

    keyfile_json = json.loads(GOOGLE_KEYFILE_PATH.read_text(encoding="utf-8"))
    nlu = DialogflowNLUProvider(
        conf=DialogflowConf(keyfile_json=keyfile_json, sample_rate_hertz=16000, language="nl"),
        mic=device.get_mic(),
    )

    interaction_config = InteractionConfig(
        language="nl",
        post_speech_delay=0,
        signal_listening_behavior=True,
    )
    interaction_config.animation_style = AnimationStyle.EXPRESSIVE
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

    # Only the scenes in SESSION_AGENDA are loaded, so commenting a scene out skips it
    # without tripping nardial's position-order check.
    all_dialogs = json.loads(DIALOG_CONFIG_PATH.read_text(encoding="utf-8"))
    dialogs_by_id = {d["id"]: d for d in all_dialogs}
    missing = [scene_id for scene_id in SESSION_AGENDA if scene_id not in dialogs_by_id]
    if missing:
        raise ValueError(f"SESSION_AGENDA contains unknown dialog ids: {missing}")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_episode2_nao_dialogs.json", delete=False, encoding="utf-8"
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
        session_manager.run()
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        nao.autonomous.request(NaoRestRequest())

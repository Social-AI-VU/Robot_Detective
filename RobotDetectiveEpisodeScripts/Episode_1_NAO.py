r"""
Robot Detective — Episode 1 (NAO)
=================================
NAO-specific variant of Episode_1.py. This version uses:

- NAO microphone input via Dialogflow
- NAO speakers for ElevenLabs audio playback

Before running:

    run-redis --data-dir RAG_Vectors
    run-dialogflow
    run-elevenlabs-tts
    & "C:\\Users\\viq021\\repositories\\Robot_Detective\\conf\\redis\\redis-server.exe" "C:\\Users\\viq021\\repositories\\Robot_Detective\\conf\\redis\\redis.conf"

Then start the episode with:

    python RobotDetectiveEpisodeScripts/Episode_1_NAO.py

Environment variables:

    NAO_IP=169.254.47.183
"""
import json
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from sic_framework.devices import Nao
from sic_framework.services.dialogflow.dialogflow import DialogflowConf

from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_motion import NaoPostureRequest

from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig
from nardial.providers.device.nao import NaoAdapter
from nardial.providers.nlu.dialogflow import DialogflowNLUProvider
from nardial.providers.tts.elevenlabs import ElevenLabsTTSConf, ElevenLabsTTSProvider
from nardial.session_manager import SessionManager


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
NAO_IP = os.getenv("NAO_IP", "192.168.0.250")

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



    nao = Nao(ip=NAO_IP)
    device = NaoAdapter(nao)

    nao.motion.request(NaoPostureRequest("Stand", 0.8))

    tts_conf = ElevenLabsTTSConf(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id="9BWtsMINqrJLrRacOk9x",
        model_id="eleven_flash_v2_5",
    )
    tts = ElevenLabsTTSProvider(conf=tts_conf, device=device)

    keyfile_json = json.loads(GOOGLE_KEYFILE_PATH.read_text(encoding="utf-8"))
    nlu = DialogflowNLUProvider(
        conf=DialogflowConf(keyfile_json=keyfile_json, sample_rate_hertz=16000),
        mic=device.get_mic(),
    )

    interaction_config = InteractionConfig(
        language="nl",
        post_speech_delay=0,
        signal_listening_behavior=True,
    )

    agent = ConversationAgent(
        device=device,
        tts_provider=tts,
        nlu_provider=nlu,
        int_config=interaction_config,
    )

    session_agenda = [
        "Ep1_Scene_1_Intro",
        "Ep1_Scene_2_Toon_Rami",
        "Ep1_Scene_3_Trudy",
        "Ep1_Scene_3_Trudy_RAG_Interview",
        "Ep1_Scene_4_Eddy",
        "Ep1_Scene_4_Eddy_RAG_Interview",
        "Ep1_Scene_5_Yoyo",
        "Ep1_Scene_5_Yoyo_RAG_Interview",
        "Ep1_Scene_6_Jennifer",
        "Ep1_Scene_6_Jennifer_LLM_Chat",
        "Ep1_Scene_6_Jennifer_RAG_Interview",
        "Ep1_Scene_7_Dj_Kata",
        "Ep1_Scene_7_Dj_Kata_LLM_Chat",
        "Ep1_Scene_8_Ontknoping",
        "Ep1_Scene_9_Kelder_Disco",
    ]

    active_dialog_json_path = str(DIALOG_CONFIG_PATH)
    if MANUAL_MODE:
        all_dialogs = json.loads(DIALOG_CONFIG_PATH.read_text(encoding="utf-8"))
        populate_missing_character_definitions(all_dialogs)
        dialogs_by_id = {d.get("id"): d for d in all_dialogs if d.get("id")}
        missing = [scene_id for scene_id in session_agenda if scene_id not in dialogs_by_id]
        if missing:
            raise ValueError(f"session_agenda contains unknown dialog ids: {missing}")

        filtered_dialogs = [dialogs_by_id[scene_id] for scene_id in session_agenda]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_episode1_nao_manual_dialogs.json", delete=False, encoding="utf-8"
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
        session_manager.run()
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        nao.autonomous.request(NaoRestRequest())

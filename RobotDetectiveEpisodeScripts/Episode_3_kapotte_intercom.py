"""
Robot Detective — Episode 3: Het mysterie van de kapotte intercom
=================================================================
Control file for the Episode 3 intercom script.
Scene execution can be commented out here while keeping the dialog JSON intact.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from sic_framework.devices.common_desktop.desktop_speakers import SpeakersConf

from runtime_patches import apply_runtime_patches

apply_runtime_patches()

from sic_framework.devices.desktop import Desktop

from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig
from nardial.providers.device.desktop import DesktopAdapter
from nardial.providers.llm.openai_gpt import OpenAIGPTProvider
from nardial.providers.nlu.written_keyword import WrittenKeywordNLUProvider
from nardial.providers.tts.null import NullTTSProvider
from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider
from nardial.session_manager import SessionManager

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DOCS_DIR = REPO_ROOT / "Detective_Data" / "Episode Scripts"
DOC_JSON_PATH = DOCS_DIR / "kort verhaal Het mysterie van de kapotte intercom.docx.txt"
DIALOG_CONFIG_PATH = REPO_ROOT / "RobotDetective_Narrative_Jsons" / "Episode_3_kapotte_intercom_all_dialogs.json"
ENV_FILE_PATH = REPO_ROOT / "conf" / ".env"

INDEX_NAME = "episode_3_kapotte_intercom_docs"
DEFAULT_RAG_INDEX_NAME = INDEX_NAME
PARTICIPANT_ID = os.getenv("PARTICIPANT_ID", "3")
RESET_PARTICIPANT_STATE = os.getenv("RESET_PARTICIPANT_STATE", "1").strip().lower() in {"1", "true", "yes", "y"}
MANUAL_MODE = True
SCENES = [
    "Ep3_Scene_1_Intro",
    "Ep3_Scene_2_Robin_Intro",
    "Ep3_Scene_3_DJ_Kata",
    "Ep3_Scene_3_Kata_RAG_Interview",
    "Ep3_Scene_4_Trudy",
    "Ep3_Scene_4_Trudy_RAG_Interview",
    "Ep3_Scene_5_Heike",
    "Ep3_Scene_5_Heike_RAG_Interview",
    "Ep3_Scene_6_Choukri",
    "Ep3_Scene_6_Choukri_RAG_Interview",
    "Ep3_Scene_6_S_toe_Tegel",
    "Ep3_Scene_7_Stoep_Tegel",
    "Ep3_Scene_7_Stoep_Tegel_RAG_Interview",
    "Ep3_Scene_8_Ontknoping",
]


def print_startup_checks() -> None:
    print(f"[CHECK] Storyboard exists: {DOC_JSON_PATH.exists()} -> {DOC_JSON_PATH}")
    print(f"[CHECK] Dialog JSON exists: {DIALOG_CONFIG_PATH.exists()} -> {DIALOG_CONFIG_PATH}")
    print(f"[CHECK] Env file exists: {ENV_FILE_PATH.exists()} -> {ENV_FILE_PATH}")
    print(f"[CHECK] Participant ID: {PARTICIPANT_ID}")
    print(f"[CHECK] RESET_PARTICIPANT_STATE: {RESET_PARTICIPANT_STATE}")


def reset_participant_state_if_needed() -> None:
    if not RESET_PARTICIPANT_STATE:
        return

    candidate_paths = [
        Path.cwd() / "participants" / f"{PARTICIPANT_ID}.json",
        REPO_ROOT / "participants" / f"{PARTICIPANT_ID}.json",
        BASE_DIR / "participants" / f"{PARTICIPANT_ID}.json",
    ]
    for path in candidate_paths:
        if path.exists():
            path.unlink()
            print(f"[RESET] Deleted participant state: {path}")


def load_storyboard() -> str:
    return DOC_JSON_PATH.read_text(encoding="utf-8")


if __name__ == "__main__":
    load_dotenv(dotenv_path=ENV_FILE_PATH)
    print_startup_checks()
    reset_participant_state_if_needed()

    desktop = Desktop(speakers_conf=SpeakersConf(sample_rate=22050))
    device = DesktopAdapter(desktop)
    tts = NullTTSProvider()

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

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix="_episode3_kapotte_intercom_manual_dialogs.json",
        delete=False,
        encoding="utf-8",
    ) as temp_file:
        temp_file.write(load_storyboard())
        active_dialog_json_path = temp_file.name

    print(f"[MANUAL MODE] Using storyboard source: {DOC_JSON_PATH}")
    print(f"[MANUAL MODE] Using filtered dialog file: {active_dialog_json_path}")

    session_manager = SessionManager(
        session_agenda=[],
        agent=agent,
        dialog_json_path=active_dialog_json_path,
        participant_id=PARTICIPANT_ID,
    )
    session_manager.run()

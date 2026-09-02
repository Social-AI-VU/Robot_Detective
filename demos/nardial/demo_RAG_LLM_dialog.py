"""
Nardial RAG + LLM Conversation Demo

This demo shows how to run a Nardial conversation that uses retrieval-augmented
generation (RAG) for selected llm_based dialog blocks.

The conversation flow is defined in:
    dialog_configs/rag_llm_dialogs.json

Before running this demo, make sure you have completed the required setup steps.
This demo depends on external services for speech, LLM, and vector search.
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

- Google credentials: conf/google/google-key.json
- OpenAI API key: conf/.env
Example `.env` entry:
    OPENAI_API_KEY="your key"

WARNING: Never commit credential files to version control.
-------------------------
3. Start required services
-------------------------
You MUST run these in separate terminals BEFORE starting the demo:

.\.venv\Scripts\Activate.ps1
    run-redis --data-dir <path to where you want to save vector database>
    run-google-tts
    run-gpt

NOTE: you need to have Docker installed to be able to use the RedisStack image (includes the Vector Search module) when you run 'run-redis'.
=========================
"""

# Import Nardial basics
from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig
from nardial.session_manager import SessionManager
from nardial.providers.device.desktop import DesktopAdapter
from nardial.providers.nlu.written_keyword import WrittenKeywordNLUProvider
from nardial.providers.tts.google import GoogleTTSProvider, GoogleTTSConf
from nardial.providers.llm.openai_gpt import OpenAIGPTProvider
from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider

# Import SIC device(s), message(s), and service(s) we will be using
from sic_framework.devices.common_desktop.desktop_speakers import SpeakersConf
from sic_framework.devices.desktop import Desktop

# import other libraries
from pathlib import Path
import os
import sys
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
SIC_APPLICATIONS_DIR = BASE_DIR.parents[1]

DOCS_DIR = BASE_DIR / "RAG_example_docs"
DIALOG_CONFIG_PATH = BASE_DIR / "dialog_configs" / "rag_llm_dialogs.json"
GOOGLE_KEYFILE_PATH = "C:\\Users\\viq021\\repositories\\Robot_Detective\\conf\\google\\google-key.json"
ENV_FILE_PATH = SIC_APPLICATIONS_DIR / "conf" / ".env"

INDEX_NAME = "nardial_pip_lantern_docs"
INGEST_DOCS = False


if __name__ == "__main__":
    load_dotenv(dotenv_path=ENV_FILE_PATH)

    # =========================
    # 1. SELECT DEVICE
    # =========================
    # Desktop uses local microphone/speakers.
    desktop = Desktop(
        speakers_conf=SpeakersConf(
            sample_rate=22050
        )
    )
    device = DesktopAdapter(desktop)

    # =========================
    # 2. CONFIGURE INTERACTION
    # =========================
    interaction_config = InteractionConfig(
        language="en",
        post_speech_delay=0,
        signal_listening_behavior=False,
    )

    # =========================
    # 3. CREATE PROVIDERS
    # =========================
    tts = GoogleTTSProvider(
        conf=GoogleTTSConf(
            speaking_rate=1.0,
            google_tts_voice_name="en-US-Neural2-C",
            google_tts_voice_gender="FEMALE",
        ),
        device=device,
        keyfile_path=str(GOOGLE_KEYFILE_PATH),
    )
    nlu = WrittenKeywordNLUProvider()
    llm = OpenAIGPTProvider(api_key=os.getenv("OPENAI_API_KEY"))
    vector_store = RedisVectorStoreProvider(
        embedding_model="text-embedding-3-large",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        index_name=INDEX_NAME,
        ingest_docs=INGEST_DOCS,
        input_path=str(DOCS_DIR),
        chunk_chars=900,
        chunk_overlap=120,
        override_existing=True,
        force_recreate_index=False,
    )

    # =========================
    # 4. CREATE AGENT
    # =========================
    agent = ConversationAgent(
        device=device,
        tts_provider=tts,
        nlu_provider=nlu,
        llm_provider=llm,
        vector_store=vector_store,
        int_config=interaction_config,
    )

    # =========================
    # 5. SESSION MANAGER
    # =========================
    # Run a mixed sequence of non-RAG and RAG llm_based blocks.
    session_manager = SessionManager(
        session_agenda=[
            "rag_llm_welcome",
            "non_rag_warmup",
            "rag_character_backstory",
            "rag_practical_help",
            "non_rag_reflection",
            "rag_llm_goodbye",
        ],
        agent=agent,
        dialog_json_path=str(DIALOG_CONFIG_PATH),
        participant_id="2",
    )

    # =========================
    # 6. RUN SESSION
    # =========================
    session_manager.run()
    
    # =========================
    # 7. CLEAN EXIT
    # =========================
    sys.exit()

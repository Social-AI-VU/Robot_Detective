"""
Nardial Simple LLM Conversation Demo

This demo shows a minimal llm_based conversation flow without RAG.

The conversation flow is defined in:
    dialog_configs/simple_llm_dialogs.json

Before running this demo, make sure you have completed the required setup steps.
This demo depends on external services for speech and LLM responses.
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

    run-google-tts
    run-gpt
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

# Import SIC device(s), message(s), and service(s) we will be using
from sic_framework.devices.common_desktop.desktop_speakers import SpeakersConf
from sic_framework.devices.desktop import Desktop

# Import other necessary libraries
from pathlib import Path
import os
import sys
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
SIC_APPLICATIONS_DIR = BASE_DIR.parents[1]

DIALOG_CONFIG_PATH = BASE_DIR / "dialog_configs" / "simple_llm_dialogs.json"
GOOGLE_KEYFILE_PATH = SIC_APPLICATIONS_DIR / "conf" / "google" / "google-key.json"
ENV_FILE_PATH = SIC_APPLICATIONS_DIR / "conf" / ".env"


if __name__ == "__main__":
    load_dotenv(dotenv_path=ENV_FILE_PATH)

    # =========================
    # 1. SELECT DEVICE
    # =========================
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
        language="nl",
        post_speech_delay=0,
        signal_listening_behavior=False,
    )

    # =========================
    # 3. CREATE PROVIDERS
    # =========================
    tts = GoogleTTSProvider(
        conf=GoogleTTSConf(
            speaking_rate=1.0,
            google_tts_voice_name="nl-NL-Wavenet-A",
            google_tts_voice_gender="MALE",
        ),
        device=device,
        keyfile_path=str(GOOGLE_KEYFILE_PATH),
    )
    nlu = WrittenKeywordNLUProvider()
    llm = OpenAIGPTProvider(api_key=os.getenv("OPENAI_API_KEY"))

    # =========================
    # 4. CREATE AGENT
    # =========================
    agent = ConversationAgent(
        device=device,
        tts_provider=tts,
        nlu_provider=nlu,
        llm_provider=llm,
        int_config=interaction_config,
    )

    # =========================
    # 5. SESSION MANAGER
    # =========================
    session_manager = SessionManager(
        session_agenda=[
            "simple_llm_welcome",
            "simple_llm_chat",
            "simple_llm_goodbye",
        ],
        agent=agent,
        dialog_json_path=str(DIALOG_CONFIG_PATH),
        participant_id="1",
    )

    # =========================
    # 6. RUN SESSION
    # =========================
    session_manager.run()

    # =========================
    # 7. CLEAN EXIT
    # =========================
    sys.exit()

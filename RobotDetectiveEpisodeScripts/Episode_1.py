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

from sic_framework.devices.common_desktop.desktop_speakers import SpeakersConf
from sic_framework.devices.desktop import Desktop

import sys
from os.path import abspath, dirname, join

# Resolve project files relative to this script so the episode can be launched
# from any working directory inside the repository.
script_dir = dirname(abspath(__file__))
repo_root = dirname(script_dir)

# Paths used by the interaction config and session manager.
google_keyfile_path = abspath(join(repo_root, "conf", "google", "google-key.json"))
env_file_path = abspath(join(repo_root, "conf", ".env"))
dialog_json_path = abspath(join(repo_root, "RobotDetective_Narrative_Jsons", "Episode_1_all_dialogs.json"))

# =========================
# MANUAL MODE SETTINGS
# =========================
# Set MANUAL_MODE=True to use manual commenting only.
# When True, SessionManager will only see dialogs that are in session_agenda.
# Just comment/uncomment scenes normally in session_agenda without errors.
MANUAL_MODE = True

if __name__ == '__main__':
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
        google_keyfile_path=google_keyfile_path,
        keyboard_input=True,           # set False to use microphone instead
        env_file_path=env_file_path,
        tts_conf=GoogleTTSConf(
            speaking_rate=1.0,
            google_tts_voice_name="nl-NL-Wavenet-A",
            google_tts_voice_gender="FEMALE"
        ),
        language="nl",
        # microphone_device=1,         # uncomment to select a specific mic
        # post_speech_delay=0.5,       # pause in seconds after the agent speaks
        # signal_listening_behavior=True,  # visual cue while listening (robots)
    )

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
        "Ep1_Scene_1_Intro",             # intro + meet Robin, collect name
        "Ep1_Scene_2_Toon_Rami",         # Toon & Rami report the missing rollercoaster
        "Ep1_Scene_3_Trudy",             # interview Trudy (karaoke plan)

        "Ep1_Scene_4_Eddy",              # interview Professor Eddy (puzzle)
        "Ep1_Scene_4_Eddy_LLM_Chat",     # open chat with Eddy
        "Ep1_Scene_5_Yoyo",              # interview Yoyo (alibi)
        "Ep1_Scene_5_Yoyo_LLM_Chat",     # open chat with Yoyo
        "Ep1_Scene_6_Jennifer",          # interview Jennifer
        "Ep1_Scene_6_Jennifer_LLM_Chat", # open chat with Jennifer
        "Ep1_Scene_7_Dj_Kata",           # interview DJ Kata
        "Ep1_Scene_7_Dj_Kata_LLM_Chat",  # open chat with DJ Kata
        "Ep1_Scene_8_Ontknoping",        # denouement — wrap up the mystery
    ]

    # =========================
    # 5. SESSION MANAGER
    # =========================
    active_dialog_json_path = dialog_json_path

    if MANUAL_MODE:
        import json
        import tempfile

        with open(dialog_json_path, "r", encoding="utf-8") as f:
            all_dialogs = json.load(f)

        # Filter dialogs to only include those in session_agenda
        filtered_dialogs = [d for d in all_dialogs if d.get("id") in session_agenda]

        # Write filtered dialogs to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_episode1_manual_dialogs.json", delete=False, encoding="utf-8"
        ) as temp_file:
            json.dump(filtered_dialogs, temp_file, ensure_ascii=False, indent=2)
            active_dialog_json_path = temp_file.name

        print(f"[MANUAL MODE] Session agenda has {len(session_agenda)} scene(s)")
        print(f"[MANUAL MODE] Filtered dialogs: {[d['id'] for d in filtered_dialogs]}")
        print(f"[MANUAL MODE] Using temp dialog file: {active_dialog_json_path}")

    session_manager = SessionManager(
        session_agenda=session_agenda,
        agent=agent,
        dialog_json_path=active_dialog_json_path,
        participant_id="999",   # change per participant for personalisation / logging
    )

    # =========================
    # 6. RUN SESSION
    # =========================
    session_manager.run()

    sys.exit()
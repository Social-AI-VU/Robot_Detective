"""
Episode 1 RAG Ingestor — NarDial InteractionConfig style
=========================================================
Uses the same InteractionConfig + ConversationAgent pattern as demo_RAG_LLM_dialog.py
so that ingestion goes through the same Redis datastore pipeline that actually works.

How to use:
1. Start required services in separate terminals:
       run-redis --data-dir <path>
       run-dialogflow
       run-google-tts
       run-gpt
2. Toggle characters you want to ingest below (INGEST_TOGGLES).
3. Run:  python RAG_Vectors/RAG_Ingestion_Episode_1.py
"""

from pathlib import Path
import sys

from nardial.conversation_agent import ConversationAgent
from nardial.interaction_orchestrator import InteractionConfig

from sic_framework.devices.common_desktop.desktop_speakers import SpeakersConf
from sic_framework.devices.desktop import Desktop


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

GOOGLE_KEYFILE_PATH = REPO_ROOT / "conf" / "google" / "google-key.json"
ENV_FILE_PATH = REPO_ROOT / "conf" / ".env"
DETECTIVE_DATA_DIR = REPO_ROOT / "Detective_Data"

EMBEDDING_MODEL = "text-embedding-3-large"
CHUNK_CHARS = 900
CHUNK_OVERLAP = 120
OVERRIDE_EXISTING = True
FORCE_RECREATE_INDEX = False

# ─── Toggle per character: True = ingest, False = skip ───────────────────────
INGEST_TOGGLES = {
    "Trudy":   False,
    "Eddy":    False,   # ← enable to ingest Eddy documents
    "Jennifer": False,
    "Robin":   False,
    "Yoyo":    False,
    "Dj_Kata": True,
}

# ─── Character source folders and target index names ─────────────────────────
CHARACTER_CONFIG = {
    "Trudy":    {"docs_dir": DETECTIVE_DATA_DIR / "Ep1_Trudy",    "index_name": "episode_1_trudy_docs"},
    "Eddy":     {"docs_dir": DETECTIVE_DATA_DIR / "Ep1_Eddy",     "index_name": "episode_1_eddy_docs"},
    "Jennifer": {"docs_dir": DETECTIVE_DATA_DIR / "Ep1_Jennifer", "index_name": "episode_1_jennifer_docs"},
    "Robin":    {"docs_dir": DETECTIVE_DATA_DIR / "Ep1_Robin",    "index_name": "episode_1_robin_docs"},
    "Yoyo":     {"docs_dir": DETECTIVE_DATA_DIR / "Ep1_Yoyo",     "index_name": "episode_1_yoyo_docs"},
    "Dj_Kata":  {"docs_dir": DETECTIVE_DATA_DIR / "Ep1_Dj_Kata",  "index_name": "episode_1_dj_kata_docs"},
}


def ingest_character(character: str, docs_dir: Path, index_name: str) -> tuple[bool, str]:
    if not docs_dir.exists():
        return False, f"docs directory not found: {docs_dir}"

    pdf_files = list(docs_dir.rglob("*.txt"))
    if not pdf_files:
        return False, f"no PDF files found in: {docs_dir}"

    print(f"  [INFO] Found {len(pdf_files)} PDF file(s) in {docs_dir}")
    print(f"  [INFO] Ingesting into index '{index_name}' ...")

    # Use same InteractionConfig pattern as demo_RAG_LLM_dialog.py
    interaction_config = InteractionConfig(
        google_keyfile_path=str(GOOGLE_KEYFILE_PATH),
        env_file_path=str(ENV_FILE_PATH),
        keyboard_input=True,
        rag=True,
        ingest_docs=True,
        input_path=str(docs_dir),
        index_name=index_name,
        embedding_model=EMBEDDING_MODEL,
        chunk_chars=CHUNK_CHARS,
        chunk_overlap=CHUNK_OVERLAP,
        override_existing=OVERRIDE_EXISTING,
        force_recreate_index=FORCE_RECREATE_INDEX,
    )

    device = Desktop(speakers_conf=SpeakersConf(sample_rate=22050))

    # ConversationAgent.__init__ triggers ingestion via InteractionOrchestrator._setup_rag
    _agent = ConversationAgent(device_manager=device, int_config=interaction_config)
    del _agent

    return True, f"ingested {len(pdf_files)} PDF(s) -> index '{index_name}'"


def main() -> int:
    enabled = [c for c, on in INGEST_TOGGLES.items() if on]
    if not enabled:
        print("[INFO] No characters enabled for ingestion.")
        print("[INFO] Set the desired character(s) to True in INGEST_TOGGLES and rerun.")
        return 0

    print(f"[INFO] Characters to ingest: {enabled}")
    print(f"[INFO] Google key: {GOOGLE_KEYFILE_PATH}")
    print(f"[INFO] Env file:   {ENV_FILE_PATH}")

    failures = []

    for character in enabled:
        cfg = CHARACTER_CONFIG.get(character)
        if not cfg:
            msg = f"no CHARACTER_CONFIG entry for '{character}'"
            print(f"\n[FAIL] {character}: {msg}")
            failures.append((character, msg))
            continue

        print(f"\n[INGEST] {character}")
        try:
            ok, message = ingest_character(character, cfg["docs_dir"], cfg["index_name"])
            if ok:
                print(f"  [OK] {message}")
            else:
                print(f"  [FAIL] {message}")
                failures.append((character, message))
        except Exception as exc:
            msg = str(exc)
            print(f"  [FAIL] {msg}")
            failures.append((character, msg))

    print()
    if failures:
        print("[SUMMARY] Ingestion finished with failures:")
        for character, reason in failures:
            print(f"  - {character}: {reason}")
        return 1

    print("[SUMMARY] Ingestion completed successfully for all enabled characters.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


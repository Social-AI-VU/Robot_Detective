"""
Episode 3 RAG Ingestor (De kapotte intercom) — NarDial InteractionConfig style
======================================================================
Uses the RedisVectorStoreProvider directly to ingest character docs into Redis Vector DB.

How to use:
1. Start required services in separate terminals:
       python run_datastore.py --data-dir RAG_Vectors
       run-gpt
2. Toggle characters you want to ingest below (INGEST_TOGGLES).
3. Run:  python RAG_Vectors/RAG_Ingestion_Episode_3.py

Robin's practice chat in this episode uses episode_1_robin_docs: ingest that with
RAG_Ingestion_Episode_1.py (toggle "Robin").
"""

from pathlib import Path
import os
import sys

from dotenv import load_dotenv
from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

ENV_FILE_PATH = REPO_ROOT / "conf" / ".env"
DETECTIVE_DATA_DIR = REPO_ROOT / "Detective_Data" / "Episode_3_Detective_Data"

EMBEDDING_MODEL = "text-embedding-3-large"
CHUNK_CHARS = 350
CHUNK_OVERLAP = 60
OVERRIDE_EXISTING = True
FORCE_RECREATE_INDEX = False

# ─── Toggle per character: True = ingest, False = skip ───────────────────────
INGEST_TOGGLES = {
    "Kata":    True,
    "Trudy":   True,
    "Heike":   True,
    "Choukri": True,
    "S_Tegel": True,
}

# ─── Character source folders and target index names ─────────────────────────
CHARACTER_CONFIG = {
    "Kata":    {"docs_dir": DETECTIVE_DATA_DIR / "Ep3_Kata", "index_name": "episode_3_kata_docs"},
    "Trudy":   {"docs_dir": DETECTIVE_DATA_DIR / "Ep3_Trudy", "index_name": "episode_3_trudy_docs"},
    "Heike":   {"docs_dir": DETECTIVE_DATA_DIR / "Ep3_Heike", "index_name": "episode_3_heike_docs"},
    "Choukri": {"docs_dir": DETECTIVE_DATA_DIR / "Ep3_Choukri", "index_name": "episode_3_choukri_docs"},
    "S_Tegel": {"docs_dir": DETECTIVE_DATA_DIR / "Ep3_S_Tegel", "index_name": "episode_3_s_tegel_docs"},
}


def ingest_character(character: str, docs_dir: Path, index_name: str) -> tuple[bool, str]:
    if not docs_dir.exists():
        return False, f"docs directory not found: {docs_dir}"

    doc_files = list(docs_dir.rglob("*.txt"))
    if not doc_files:
        return False, f"no .txt files found in: {docs_dir}"

    print(f"  [INFO] Found {len(doc_files)} text file(s) in {docs_dir}")
    print(f"  [INFO] Ingesting into index '{index_name}' ...")

    vector_store = RedisVectorStoreProvider(
        embedding_model=EMBEDDING_MODEL,
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        index_name=index_name,
        ingest_docs=True,
        input_path=str(docs_dir),
        chunk_chars=CHUNK_CHARS,
        chunk_overlap=CHUNK_OVERLAP,
        override_existing=OVERRIDE_EXISTING,
        force_recreate_index=FORCE_RECREATE_INDEX,
    )
    vector_store.close()

    return True, f"ingested {len(doc_files)} text file(s) -> index '{index_name}'"


def main() -> int:
    load_dotenv(dotenv_path=ENV_FILE_PATH)
    enabled = [c for c, on in INGEST_TOGGLES.items() if on]
    if not enabled:
        print("[INFO] No characters enabled for ingestion.")
        print("[INFO] Set the desired character(s) to True in INGEST_TOGGLES and rerun.")
        return 0

    print(f"[INFO] Characters to ingest: {enabled}")
    print(f"[INFO] Env file:   {ENV_FILE_PATH}")
    print(f"[INFO] OPENAI_API_KEY present: {bool(os.getenv('OPENAI_API_KEY'))}")

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

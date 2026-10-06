"""
Start the SIC Redis datastore service (same as `run-redis`), with the Robot Detective patches applied.

The RAG lookups (embedding the child's question) run inside this service process, so patches in the
episode scripts do not reach them. Use this instead of `run-redis`, with the same arguments:

    python run_datastore.py --data-dir RAG_Vectors

Start only ONE datastore service (this or `run-redis`, never both): two copies answer every request
twice and can both get stuck on the same request.

Without --data-dir, RAG_Vectors is used anyway. `run-redis` recreates the Redis container whenever it
is started with different settings than last time; without a data folder that container (and all
ingested knowledge) is wiped.
"""

import sys
from pathlib import Path

import sic_framework.services.datastore.redis_datastore as redis_datastore

from runtime_patches import apply_datastore_service_patches

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "RAG_Vectors"

if __name__ == "__main__":
    if not any(arg == "--data-dir" or arg.startswith("--data-dir=") for arg in sys.argv[1:]):
        sys.argv += ["--data-dir", str(DEFAULT_DATA_DIR)]
        print("[run_datastore] No --data-dir given, using {}".format(DEFAULT_DATA_DIR))
    apply_datastore_service_patches()
    redis_datastore.main()

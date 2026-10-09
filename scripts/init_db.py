"""Create schema, seed data and embeddings in an empty database (e.g. Neon).

    DATABASE_URL=postgresql://... .venv/bin/python scripts/init_db.py

Does nothing if the schema already exists.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app import db  # noqa: E402
from scripts.backfill_embeddings import main as backfill  # noqa: E402


def main() -> None:
    with db.connect() as conn:
        exists = conn.execute("SELECT to_regclass('public.jobs') IS NOT NULL").fetchone()[0]
        if exists:
            print("schema already exists, skipping SQL files")
        else:
            for sql_file in sorted((ROOT / "db").glob("*.sql")):
                conn.execute(sql_file.read_text())
                print(f"applied {sql_file.name}")
    backfill()


if __name__ == "__main__":
    main()

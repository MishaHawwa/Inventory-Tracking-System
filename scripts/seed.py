#!/usr/bin/env python3
"""
scripts/seed.py  — Reset the database and re-seed with fresh demo data.

Usage:
    python scripts/seed.py           # Reset and seed
    python scripts/seed.py --drop    # Drop DB file first, then seed
"""

import asyncio
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import init_db, DB_PATH


async def main():
    drop = "--drop" in sys.argv
    if drop and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[seed] Dropped: {DB_PATH}")

    await init_db()
    print(f"[seed] Database ready with sample data at: {DB_PATH}")
    print("[seed] Run the server with:  uvicorn main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())

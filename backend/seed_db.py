"""
One-time script: seeds brands and stores from local JSON files into Supabase.

Usage:
    python backend/seed_db.py

Requires SUPABASE_URL and SUPABASE_KEY in your .env file.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

_HERE = Path(__file__).parent


def seed():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_KEY in .env")

    db = create_client(url, key)

    # Seed brands
    with open(_HERE / "brands.json") as f:
        brands = json.load(f)

    print(f"Seeding {len(brands)} brands...")
    for brand in brands:
        try:
            db.table("brands").insert({"name": brand["name"], "color": brand["color"]}).execute()
            print(f"  + {brand['name']}")
        except Exception:
            print(f"  ~ {brand['name']} (already exists, skipped)")

    # Seed stores
    with open(_HERE / "stores.json") as f:
        stores = json.load(f)

    print(f"\nSeeding {len(stores)} stores...")
    ok = skipped = 0
    for store in stores:
        try:
            db.table("stores").insert({
                "brand": store["brand"],
                "group": store["group"],
                "store_number": store["store_number"],
                "name": store["name"],
                "address": store["address"],
                "google_maps_url": store.get("google_maps_url", ""),
            }).execute()
            ok += 1
        except Exception:
            skipped += 1

    print(f"  {ok} inserted, {skipped} skipped (already exist)")
    print("\nDone. Supabase is seeded.")


if __name__ == "__main__":
    seed()

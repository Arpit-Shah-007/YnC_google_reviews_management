import argparse
import json
import os
import time
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN")
if not APIFY_TOKEN:
    raise SystemExit("Missing APIFY_API_TOKEN in .env")

ACTOR_ID = "compass~Google-Maps-Reviews-Scraper"
BASE = "https://api.apify.com/v2"


def load_stores(path: str = "stores.json") -> list[dict]:
    with open(path) as f:
        return json.load(f)


def select_stores(stores: list[dict], test_mode: bool) -> list[dict]:
    if not test_mode:
        return stores
    seen = set()
    selected = []
    for store in stores:
        if store["group"] not in seen:
            selected.append(store)
            seen.add(store["group"])
    return selected


def start_run(store_urls: list[str], start_date: str) -> str:
    payload = {
        "language": "en",
        "maxReviews": 50,
        "personalData": False,
        "reviewsOrigin": "all",
        "reviewsSort": "newest",
        "reviewsStartDate": start_date,
        "startUrls": [{"url": url} for url in store_urls],
    }
    resp = requests.post(
        f"{BASE}/acts/{ACTOR_ID}/runs",
        params={"token": APIFY_TOKEN},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if "data" not in body or "id" not in body.get("data", {}):
        raise SystemExit(f"Unexpected Apify response: {body}")
    run_id = body["data"]["id"]
    print(f"Apify run started: {run_id}")
    return run_id


def poll_run(run_id: str) -> str:
    print("Waiting for Apify run to finish", end="", flush=True)
    while True:
        resp = requests.get(
            f"{BASE}/actor-runs/{run_id}",
            params={"token": APIFY_TOKEN},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data["status"]
        if status == "SUCCEEDED":
            print(" done.")
            return data["defaultDatasetId"]
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise SystemExit(f"Apify run ended with status {status}. Run ID: {run_id}")
        print(".", end="", flush=True)
        time.sleep(30)


def download_dataset(dataset_id: str) -> list[dict]:
    resp = requests.get(
        f"{BASE}/datasets/{dataset_id}/items",
        params={"token": APIFY_TOKEN, "format": "json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Scrape Google Maps reviews via Apify")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD (e.g. 2025-03-01)")
    parser.add_argument("--end", help="End date YYYY-MM-DD (informational label only)")
    parser.add_argument("--test", action="store_true", help="Run 1 store per brand (3 stores total)")
    args = parser.parse_args()

    stores = load_stores()
    selected = select_stores(stores, args.test)
    label = " (TEST MODE — 1 store per brand)" if args.test else ""
    print(f"Scraping {len(selected)} stores{label}")
    for s in selected:
        print(f"  [{s['group']}] {s['name']} — {s['address']}")

    urls = [s["google_maps_url"] for s in selected]
    run_id = start_run(urls, args.start)
    dataset_id = poll_run(run_id)
    reviews = download_dataset(dataset_id)

    today = date.today().isoformat()
    suffix = "_test" if args.test else ""
    os.makedirs("data", exist_ok=True)
    out_path = f"data/reviews_{today}{suffix}.json"

    with open(out_path, "w") as f:
        json.dump(reviews, f, indent=2)

    print(f"Saved {len(reviews)} reviews to {out_path}")


if __name__ == "__main__":
    main()

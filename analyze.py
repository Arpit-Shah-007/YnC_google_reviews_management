import glob
import json
import os
from urllib.parse import parse_qs, urlparse


def load_latest_reviews(data_dir: str = "data") -> list[dict]:
    files = sorted(glob.glob(os.path.join(data_dir, "reviews_*.json")))
    if not files:
        raise SystemExit(f"No review files found in {data_dir}/. Run scrape.py first.")
    latest = files[-1]
    print(f"Loading reviews from {latest}")
    with open(latest) as f:
        return json.load(f)


def _extract_query(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    return qs.get("query", [""])[0].lower().strip()


def group_reviews_by_store(reviews: list[dict], stores: list[dict]) -> list[dict]:
    store_by_query = {_extract_query(s["google_maps_url"]): s for s in stores}

    grouped: dict[str, dict] = {s["google_maps_url"]: {"store": s, "reviews": []} for s in stores}

    for review in reviews:
        query = _extract_query(review.get("url", ""))
        store = store_by_query.get(query)
        if store:
            grouped[store["google_maps_url"]]["reviews"].append(review)

    return list(grouped.values())


def calculate_avg_rating(reviews: list[dict]) -> float | None:
    ratings = [r["stars"] for r in reviews if r.get("stars") is not None]
    if not ratings:
        return None
    return round(sum(ratings) / len(ratings), 1)

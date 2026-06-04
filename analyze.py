import glob
import json
import os
import re
from urllib.parse import parse_qs, urlparse

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_gemini_model = None  # lazy init — avoids crashing tests that don't call analyze_store


def _get_model():
    global _gemini_model
    if _gemini_model is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise SystemExit("Missing GEMINI_API_KEY in .env")
        genai.configure(api_key=key)
        _gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    return _gemini_model


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


def build_gemini_prompt(store_name: str, address: str, reviews: list[dict]) -> str:
    review_lines = []
    for i, r in enumerate(reviews, 1):
        stars = r.get("stars", "?")
        text = (r.get("text") or "").strip()
        if text:
            review_lines.append(f"{i}. [{stars} stars] {text}")

    reviews_block = "\n".join(review_lines) if review_lines else "No review text available."

    return f"""You are an operations analyst for Yum and Chill Restaurant Group, a fast-food franchise operator.

Analyze the following {len(reviews)} Google Maps customer reviews for {store_name} located at {address}.

REVIEWS:
{reviews_block}

Provide a concise analysis for the store manager in this exact format:
SUMMARY: [2-3 sentences describing the main themes, recurring complaints, and any positives]
ACTIONS: 1. [specific action] 2. [specific action] 3. [specific action]

Be specific and actionable. Address the store manager directly."""


def parse_gemini_response(raw: str) -> dict:
    summary = ""
    actions = []

    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("SUMMARY:"):
            summary = line[len("SUMMARY:"):].strip()
        elif line.startswith("ACTIONS:"):
            actions_str = line[len("ACTIONS:"):].strip()
            actions = re.findall(r"\d+\.\s(.+?)(?=\s\d+\.|$)", actions_str)
            actions = [a.strip() for a in actions if a.strip()]

    if not summary:
        summary = raw.strip()[:500]
    if not actions:
        actions = ["Review customer feedback and address recurring issues."]

    return {"summary": summary, "actions": actions}


def analyze_store(store_name: str, address: str, reviews: list[dict]) -> dict:
    if not reviews:
        return {
            "summary": "No reviews found in this period.",
            "actions": [],
            "avg_rating": None,
            "review_count": 0,
        }

    avg_rating = calculate_avg_rating(reviews)
    prompt = build_gemini_prompt(store_name, address, reviews)

    try:
        response = _get_model().generate_content(prompt)
        parsed = parse_gemini_response(response.text)
    except Exception as e:
        print(f"  WARNING: Gemini call failed for {store_name}: {e}")
        parsed = {"summary": "Analysis unavailable.", "actions": []}

    return {
        "summary": parsed["summary"],
        "actions": parsed["actions"],
        "avg_rating": avg_rating,
        "review_count": len(reviews),
    }

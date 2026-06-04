# YANDC Google Review Analysis System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-script Python pipeline that scrapes Google Maps reviews via Apify and produces a branded Excel report with per-store AI summaries for YANDC's 51 restaurant locations.

**Architecture:** `generate_stores.py` runs once to build a master store config with Google Maps URLs. `scrape.py` calls the Apify API to fetch reviews and save raw JSON. `analyze.py` reads that JSON, calls Gemini 1.5 Flash per store, and writes a 3-tab Excel report.

**Tech Stack:** Python 3.10+, `requests`, `google-generativeai`, `openpyxl`, `python-dotenv`, Apify REST API, Gemini 1.5 Flash

---

## File Map

| File | Role |
|---|---|
| `generate_stores.py` | One-time script: reads `Site List.xlsx`, outputs `stores.json` with Google Maps URLs |
| `stores.json` | Master store config used by both scripts |
| `scrape.py` | Calls Apify API, polls until complete, saves raw reviews to `data/` |
| `analyze.py` | Reads raw reviews, calls Gemini per store, writes Excel to `output/` |
| `.env` | `APIFY_API_TOKEN` and `GEMINI_API_KEY` (never committed) |
| `.env.example` | Template for the above |
| `data/reviews_YYYY-MM-DD.json` | Raw Apify output, named by run date |
| `data/reviews_YYYY-MM-DD_test.json` | Raw output from `--test` runs |
| `output/YANDC_Review_Analysis_MMMYYYY.xlsx` | Final Excel report |
| `tests/test_generate_stores.py` | Tests for store parsing and URL generation |
| `tests/test_analyze.py` | Tests for review grouping, Gemini prompt, rating calculation |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create `requirements.txt`**

```
requests==2.32.3
google-generativeai==0.8.3
openpyxl==3.1.5
python-dotenv==1.0.1
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: all packages install without error

- [ ] **Step 3: Create `.env.example`**

```
APIFY_API_TOKEN=your_apify_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

- [ ] **Step 4: Create `.env` (your real keys, never commit this)**

Copy `.env.example` to `.env` and fill in your actual keys.

- [ ] **Step 5: Create `.gitignore`**

```
.env
data/
output/
__pycache__/
*.pyc
.superpowers/
```

- [ ] **Step 6: Create `data/` and `output/` directories and `tests/` package**

```bash
mkdir data output tests
echo. > tests\__init__.py
```

- [ ] **Step 7: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore tests/
git commit -m "chore: project setup"
```

---

## Task 2: Generate stores.json

**Files:**
- Create: `generate_stores.py`
- Create: `tests/test_generate_stores.py`
- Output: `stores.json`

**How matching works in analyze.py (read this now):** When we submit a search URL like `https://www.google.com/maps/search/?api=1&query=Taco+Bell+3+Path+Plaza+Jersey+City+NJ` to Apify, the output items' `url` field will be that same URL with `&query_place_id=XXXX` appended. So matching output items back to stores is done by extracting and comparing the `query` URL parameter from both sides.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_generate_stores.py
import json
from generate_stores import build_google_maps_url, parse_site_list


def test_build_google_maps_url_encodes_address():
    url = build_google_maps_url("Taco Bell", "3 Path Plaza, Jersey City, NJ 07036")
    assert url.startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "Taco+Bell" in url or "Taco%20Bell" in url
    assert "Jersey+City" in url or "Jersey%20City" in url


def test_build_google_maps_url_no_spaces():
    url = build_google_maps_url("Taco Bell", "3 Path Plaza, Jersey City, NJ 07036")
    assert " " not in url


def test_parse_site_list_returns_correct_counts(tmp_path):
    # This test runs against the real Site List.xlsx in the project root
    stores = parse_site_list("Site List.xlsx")
    taco = [s for s in stores if s["group"] == "Taco Bell"]
    north = [s for s in stores if s["group"] == "Wendy's North"]
    south = [s for s in stores if s["group"] == "Wendy's South"]
    assert len(taco) == 14
    assert len(north) > 0
    assert len(south) > 0


def test_parse_site_list_store_has_required_fields():
    stores = parse_site_list("Site List.xlsx")
    for store in stores:
        assert "brand" in store
        assert "group" in store
        assert "store_number" in store
        assert "name" in store
        assert "address" in store
        assert "google_maps_url" in store
        assert store["google_maps_url"].startswith("https://")


def test_parse_site_list_no_section_headers_in_output():
    stores = parse_site_list("Site List.xlsx")
    names = [s["name"] for s in stores]
    assert "Taco Bells" not in names
    assert "Wendy's North" not in names
    assert "Wendy's South" not in names
```

- [ ] **Step 2: Run tests — expect failure**

Run: `python -m pytest tests/test_generate_stores.py -v`
Expected: `ImportError` or `ModuleNotFoundError` (generate_stores.py doesn't exist yet)

- [ ] **Step 3: Implement `generate_stores.py`**

```python
import json
import urllib.parse
import openpyxl


SECTION_HEADERS = {"Taco Bells", "Wendy's North", "Wendy's South"}
GROUP_MAP = {
    "Taco Bells": "Taco Bell",
    "Wendy's North": "Wendy's North",
    "Wendy's South": "Wendy's South",
}
BRAND_MAP = {
    "Taco Bell": "Taco Bell",
    "Wendy's North": "Wendy's",
    "Wendy's South": "Wendy's",
}


def build_google_maps_url(store_name: str, address: str) -> str:
    query = urllib.parse.quote_plus(f"{store_name} {address}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def parse_site_list(path: str = "Site List.xlsx") -> list[dict]:
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    stores = []
    current_group = None

    for row in ws.iter_rows(min_row=2, values_only=True):
        name, store_num, addr1, addr2, city, state, zipcode = row

        if name in SECTION_HEADERS:
            current_group = GROUP_MAP[name]
            continue

        if not name or not addr1 or not current_group:
            continue

        parts = [addr1]
        if addr2:
            parts.append(addr2)
        zip_str = str(zipcode).split(".")[0].zfill(5) if zipcode else ""
        parts.append(f"{city}, {state} {zip_str}".strip())
        full_address = ", ".join(parts)

        brand = BRAND_MAP[current_group]
        store_num_str = str(store_num).split(".")[0] if store_num else "unknown"

        stores.append({
            "brand": brand,
            "group": current_group,
            "store_number": store_num_str,
            "name": f"{brand} #{store_num_str}",
            "address": full_address,
            "google_maps_url": build_google_maps_url(brand, full_address),
        })

    return stores


if __name__ == "__main__":
    stores = parse_site_list()
    with open("stores.json", "w") as f:
        json.dump(stores, f, indent=2)
    print(f"Generated stores.json with {len(stores)} stores")
    for group in ["Taco Bell", "Wendy's North", "Wendy's South"]:
        count = sum(1 for s in stores if s["group"] == group)
        print(f"  {group}: {count} stores")
```

- [ ] **Step 4: Run tests — expect pass**

Run: `python -m pytest tests/test_generate_stores.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Generate `stores.json`**

Run: `python generate_stores.py`
Expected output:
```
Generated stores.json with 51 stores
  Taco Bell: 14 stores
  Wendy's North: 11 stores
  Wendy's South: 26 stores
```

Open `stores.json` and spot-check 3 entries — verify the address looks right and the Google Maps URL contains the address encoded.

- [ ] **Step 6: Commit**

```bash
git add generate_stores.py tests/test_generate_stores.py stores.json
git commit -m "feat: generate stores.json from Site List.xlsx with Google Maps URLs"
```

---

## Task 3: scrape.py

**Files:**
- Create: `scrape.py`

- [ ] **Step 1: Implement `scrape.py`**

```python
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
    run_id = resp.json()["data"]["id"]
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
```

- [ ] **Step 2: Do a test scrape run**

Run: `python scrape.py --start 2025-03-01 --test`

Expected console output:
```
Scraping 3 stores (TEST MODE — 1 store per brand)
  [Taco Bell] Taco Bell #041966 — 3 Path Plaza, Jersey City, NJ 07036
  [Wendy's North] Wendy's #13392 — 449 Main Avenue, Passaic, NJ 07055
  [Wendy's South] Wendy's #5327 — 101 Jack Martin Blvd, Brick, NJ 08724
Apify run started: <run-id>
Waiting for Apify run to finish.......... done.
Saved N reviews to data/reviews_YYYY-MM-DD_test.json
```

Open `data/reviews_YYYY-MM-DD_test.json` and confirm it contains objects with `title`, `url`, `stars`, and `text` fields.

- [ ] **Step 3: Commit**

```bash
git add scrape.py
git commit -m "feat: scrape.py calls Apify and saves raw reviews with --test flag support"
```

---

## Task 4: analyze.py — Data Loading and Store Matching

**Files:**
- Create: `analyze.py`
- Create: `tests/test_analyze.py`

**Matching logic:** When Apify processes our search URL, it appends `&query_place_id=XXX` to the URL. So the `url` field in the output will contain the same `query` parameter as our submitted URL. We extract and compare that `query` parameter to match reviews back to stores.

- [ ] **Step 1: Write failing tests for data loading**

```python
# tests/test_analyze.py
from analyze import load_latest_reviews, group_reviews_by_store, calculate_avg_rating


def test_load_latest_reviews_returns_list(tmp_path, monkeypatch):
    import json
    (tmp_path / "reviews_2025-06-01_test.json").write_text(
        json.dumps([{"title": "Taco Bell", "url": "https://maps?query=TB", "stars": 4, "text": "Good"}])
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "reviews_2025-06-01_test.json").write_text(
        json.dumps([{"title": "Taco Bell", "url": "https://maps?query=TB", "stars": 4, "text": "Good"}])
    )
    reviews = load_latest_reviews(data_dir=str(tmp_path / "data"))
    assert isinstance(reviews, list)
    assert len(reviews) == 1


def test_group_reviews_by_store_matches_by_query_param():
    stores = [
        {
            "group": "Taco Bell",
            "name": "Taco Bell #1",
            "address": "123 Main St, Newark, NJ 07101",
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Taco+Bell+123+Main+St",
        }
    ]
    reviews = [
        {"title": "Taco Bell", "url": "https://www.google.com/maps/search/?api=1&query=Taco+Bell+123+Main+St&query_place_id=ABC123", "stars": 5, "text": "Great!"},
        {"title": "Taco Bell", "url": "https://www.google.com/maps/search/?api=1&query=Taco+Bell+123+Main+St&query_place_id=ABC123", "stars": 3, "text": "Okay"},
    ]
    grouped = group_reviews_by_store(reviews, stores)
    assert len(grouped) == 1
    assert grouped[0]["store"]["name"] == "Taco Bell #1"
    assert len(grouped[0]["reviews"]) == 2


def test_group_reviews_by_store_no_match_skips_gracefully():
    stores = [
        {
            "group": "Taco Bell",
            "name": "Taco Bell #1",
            "address": "123 Main St",
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Taco+Bell+123+Main+St",
        }
    ]
    reviews = [
        {"title": "Taco Bell", "url": "https://www.google.com/maps/search/?api=1&query=Completely+Different&query_place_id=ZZZ", "stars": 4, "text": "Fine"},
    ]
    grouped = group_reviews_by_store(reviews, stores)
    assert len(grouped) == 1
    assert grouped[0]["reviews"] == []


def test_calculate_avg_rating_correct():
    reviews = [{"stars": 5}, {"stars": 3}, {"stars": 4}]
    assert calculate_avg_rating(reviews) == 4.0


def test_calculate_avg_rating_empty_returns_none():
    assert calculate_avg_rating([]) is None
```

- [ ] **Step 2: Run tests — expect failure**

Run: `python -m pytest tests/test_analyze.py -v`
Expected: `ImportError` (analyze.py doesn't exist yet)

- [ ] **Step 3: Implement data loading functions in `analyze.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect pass**

Run: `python -m pytest tests/test_analyze.py::test_group_reviews_by_store_matches_by_query_param tests/test_analyze.py::test_group_reviews_by_store_no_match_skips_gracefully tests/test_analyze.py::test_calculate_avg_rating_correct tests/test_analyze.py::test_calculate_avg_rating_empty_returns_none -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add analyze.py tests/test_analyze.py
git commit -m "feat: analyze.py data loading and store matching by URL query param"
```

---

## Task 5: analyze.py — Gemini Analysis Per Store

**Files:**
- Modify: `analyze.py`
- Modify: `tests/test_analyze.py`

- [ ] **Step 1: Add failing test for Gemini prompt builder**

Add to `tests/test_analyze.py`:

```python
from analyze import build_gemini_prompt, parse_gemini_response


def test_build_gemini_prompt_contains_store_name():
    reviews = [{"stars": 4, "text": "Great food"}, {"stars": 2, "text": "Slow service"}]
    prompt = build_gemini_prompt("Taco Bell #041966", "3 Path Plaza, Jersey City, NJ 07036", reviews)
    assert "Taco Bell #041966" in prompt
    assert "Jersey City" in prompt
    assert "Great food" in prompt
    assert "Slow service" in prompt


def test_parse_gemini_response_extracts_summary_and_actions():
    raw = "SUMMARY: Food quality is consistently praised but drive-through wait times are too long.\nACTIONS: 1. Add a second order-taker during peak hours. 2. Review drive-through staffing schedule. 3. Set a target of under 4 minutes per car."
    result = parse_gemini_response(raw)
    assert "Food quality" in result["summary"]
    assert len(result["actions"]) == 3
    assert "Add a second" in result["actions"][0]


def test_parse_gemini_response_handles_unexpected_format():
    raw = "Some unexpected response without the expected format."
    result = parse_gemini_response(raw)
    assert "summary" in result
    assert "actions" in result
    assert isinstance(result["actions"], list)
```

- [ ] **Step 2: Run tests — expect failure**

Run: `python -m pytest tests/test_analyze.py::test_build_gemini_prompt_contains_store_name tests/test_analyze.py::test_parse_gemini_response_extracts_summary_and_actions -v`
Expected: `ImportError` (functions not defined yet)

- [ ] **Step 3: Add Gemini functions to `analyze.py`**

Add these imports at the top of `analyze.py`:

```python
import os
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
```

Add these functions to `analyze.py`:

```python
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
            import re
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
```

- [ ] **Step 4: Run tests — expect pass**

Run: `python -m pytest tests/test_analyze.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add analyze.py tests/test_analyze.py
git commit -m "feat: Gemini prompt builder and per-store analysis in analyze.py"
```

---

## Task 6: analyze.py — Excel Generation

**Files:**
- Modify: `analyze.py`

Brand colors:
- **Taco Bell:** header bg `#702082` (purple), text `#F5D619` (gold)
- **Wendy's:** header bg `#CC2222` (red), text `#FFFFFF` (white)

Rating cell colors: red `#FFCCCC` (≤ 3.4), yellow `#FFFFCC` (3.5–3.9), green `#CCFFCC` (≥ 4.0)

- [ ] **Step 1: Add `write_excel` function to `analyze.py`**

Add these imports at the top of `analyze.py`:

```python
from datetime import date as date_type
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
```

Add this function:

```python
BRAND_STYLES = {
    "Taco Bell": {"bg": "702082", "fg": "F5D619"},
    "Wendy's": {"bg": "CC2222", "fg": "FFFFFF"},
}

RATING_FILLS = {
    "red":    PatternFill("solid", fgColor="FFCCCC"),
    "yellow": PatternFill("solid", fgColor="FFFFCC"),
    "green":  PatternFill("solid", fgColor="CCFFCC"),
}

THIN_BORDER = Border(
    left=Side(style="thin", color="DDDDDD"),
    right=Side(style="thin", color="DDDDDD"),
    top=Side(style="thin", color="DDDDDD"),
    bottom=Side(style="thin", color="DDDDDD"),
)

COLUMN_WIDTHS = {
    "Store #": 12,
    "Store Name": 28,
    "Full Address": 40,
    "Avg Rating": 12,
    "Reviews Analyzed": 18,
    "Period": 16,
    "AI Summary & Action Items": 80,
}
HEADERS = list(COLUMN_WIDTHS.keys())


def _rating_fill(rating: float | None) -> PatternFill | None:
    if rating is None:
        return None
    if rating <= 3.4:
        return RATING_FILLS["red"]
    if rating <= 3.9:
        return RATING_FILLS["yellow"]
    return RATING_FILLS["green"]


def _write_sheet(ws, group_stores: list[dict], brand: str, period_label: str):
    style = BRAND_STYLES.get(brand, {"bg": "333333", "fg": "FFFFFF"})
    header_fill = PatternFill("solid", fgColor=style["bg"])
    header_font = Font(bold=True, color=style["fg"], size=11)

    # Write header row
    for col_idx, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    ws.row_dimensions[1].height = 30

    # Write data rows
    for row_idx, entry in enumerate(group_stores, 2):
        store = entry["store"]
        analysis = entry["analysis"]

        actions_text = ""
        if analysis["actions"]:
            actions_text = " ".join(
                f"{i}. {a}" for i, a in enumerate(analysis["actions"], 1)
            )

        summary_full = analysis["summary"]
        if actions_text:
            summary_full = f"{summary_full}\n\n{actions_text}"

        rating = analysis["avg_rating"]
        rating_display = f"{rating:.1f} ⭐" if rating is not None else "—"

        row_values = [
            store["store_number"],
            store["name"],
            store["address"],
            rating_display,
            analysis["review_count"] or "—",
            period_label,
            summary_full,
        ]

        # Alternating row background
        row_fill = PatternFill("solid", fgColor="F9F9F9") if row_idx % 2 == 0 else None

        for col_idx, value in enumerate(row_values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=(col_idx == len(HEADERS)))

            if row_fill:
                cell.fill = row_fill

            # Rating column conditional color (overrides row fill)
            if col_idx == 4:
                fill = _rating_fill(rating)
                if fill:
                    cell.fill = fill
                cell.alignment = Alignment(horizontal="center", vertical="top")

        ws.row_dimensions[row_idx].height = max(60, 15 * (summary_full.count("\n") + 3))

    # Set column widths
    for col_idx, header in enumerate(HEADERS, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = COLUMN_WIDTHS[header]

    # Freeze header row
    ws.freeze_panes = "A2"


def write_excel(grouped: list[dict], start_date: str, out_dir: str = "output") -> str:
    os.makedirs(out_dir, exist_ok=True)
    month_label = date_type.fromisoformat(start_date).strftime("%b%Y")
    today_label = date_type.today().strftime("%b %d, %Y")
    period_label = f"{date_type.fromisoformat(start_date).strftime('%b %Y')} – {today_label}"
    filename = f"YANDC_Review_Analysis_{month_label}.xlsx"
    out_path = os.path.join(out_dir, filename)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    tab_groups = [
        ("Taco Bell", "Taco Bell"),
        ("Wendy's North", "Wendy's"),
        ("Wendy's South", "Wendy's"),
    ]

    for tab_name, brand in tab_groups:
        ws = wb.create_sheet(title=tab_name)
        ws.sheet_properties.tabColor = (
            "702082" if brand == "Taco Bell" else "CC2222"
        )
        group_stores = [e for e in grouped if e["store"]["group"] == tab_name]
        _write_sheet(ws, group_stores, brand, period_label)

    wb.save(out_path)
    print(f"Excel report saved to {out_path}")
    return out_path
```

- [ ] **Step 2: Add `main()` function to `analyze.py`**

```python
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze reviews and write Excel report")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD matching your scrape")
    args = parser.parse_args()

    with open("stores.json") as f:
        stores = json.load(f)

    reviews = load_latest_reviews()
    grouped_raw = group_reviews_by_store(reviews, stores)

    print(f"Analyzing {len(grouped_raw)} stores with Gemini...")
    grouped = []
    for entry in grouped_raw:
        store = entry["store"]
        store_reviews = entry["reviews"]
        print(f"  {store['name']} ({len(store_reviews)} reviews)")
        analysis = analyze_store(store["name"], store["address"], store_reviews)
        grouped.append({"store": store, "analysis": analysis})

    out_path = write_excel(grouped, args.start)
    print(f"\nDone. Report: {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add analyze.py
git commit -m "feat: Excel generation with brand colors, conditional rating formatting, 3 brand tabs"
```

---

## Task 7: End-to-End Test Run

- [ ] **Step 1: Run the full test pipeline**

```bash
python scrape.py --start 2025-03-01 --test
```

Confirm `data/reviews_YYYY-MM-DD_test.json` exists and has content.

- [ ] **Step 2: Run analysis on test data**

```bash
python analyze.py --start 2025-03-01
```

Confirm `output/YANDC_Review_Analysis_Mar2025.xlsx` is created.

- [ ] **Step 3: Open and inspect the Excel**

Open the file and verify:
- [ ] 3 tabs: Taco Bell, Wendy's North, Wendy's South
- [ ] Taco Bell tab has purple header with gold text
- [ ] Wendy's tabs have red header with white text
- [ ] Avg Rating column is color-coded
- [ ] AI Summary column has both a paragraph summary and numbered actions
- [ ] Tab colors match brands (purple vs red)
- [ ] Stores with no reviews show "No reviews found in this period"

- [ ] **Step 4: Run full analysis for real (all 51 stores)**

Once test run looks correct, do a full scrape:

```bash
python scrape.py --start 2025-03-01
python analyze.py --start 2025-03-01
```

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "chore: verified end-to-end pipeline works for 3-store test and full 51-store run"
```

---

## Quick Reference

```bash
# Setup (run once)
pip install -r requirements.txt
python generate_stores.py

# Test run (3 stores, minimal Apify cost)
python scrape.py --start YYYY-MM-DD --test
python analyze.py --start YYYY-MM-DD

# Full run (all 51 stores)
python scrape.py --start YYYY-MM-DD
python analyze.py --start YYYY-MM-DD
```

# Y&C Google Review Analysis

Automated Google Maps review scraper and AI analysis pipeline for Yum & Chill Restaurant Group (51 stores — Taco Bell NJ, Wendy's North NJ/NY, Wendy's South NJ/PA).

Produces a branded Excel report with AI-generated summaries and improvement areas per store, ready to share with the ops team.

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in APIFY_API_TOKEN and GROQ_API_KEY in .env
```

---

## Run

### Full run — all 51 stores

```bash
python scrape.py --start 2025-03-01
python analyze.py --start 2025-03-01
```

Output: `output/Y&C_Google_Review_Analysis_Mar2025.xlsx`

### Test run — 1 store per brand (3 stores, saves Apify credits)

```bash
python scrape.py --start 2025-03-01 --test
python analyze.py --start 2025-03-01
```

### Re-run analysis only (no re-scrape, uses existing JSON in data/)

```bash
python analyze.py --start 2025-03-01
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scrape.py` | Calls Apify to scrape Google Maps reviews for all stores, saves raw JSON to `data/` |
| `analyze.py` | Loads latest JSON, runs Groq AI analysis per store, writes branded Excel to `output/` |
| `generate_stores.py` | One-time utility — parses `Site List.xlsx` and generates `stores.json` |

---

## AI Model

Uses **Groq** (`llama-3.3-70b-versatile`) with automatic fallback to `llama-3.1-8b-instant` if rate limited. Free tier handles the full 51-store run without issues.

---

## Notes

- `scrape.py` consumes Apify credits — use `--test` when verifying changes
- `analyze.py` can be re-run as many times as needed against saved JSON (no cost)
- Raw JSON files are gitignored — keep `data/` locally if you want to avoid re-scraping
- To regenerate `stores.json` after adding stores to `Site List.xlsx`: `python generate_stores.py`

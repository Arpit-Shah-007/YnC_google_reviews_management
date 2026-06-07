# Y&C Google Review Analysis — Project Context

## What This Project Does

Two-script Python pipeline for Yum & Chill Restaurant Group (51 stores):
- `scrape.py` — pulls Google Maps reviews via Apify for all stores, saves raw JSON to `data/`
- `analyze.py` — loads latest JSON, runs per-store AI analysis via Groq, writes branded Excel to `output/`

Output: `Y&C_Google_Review_Analysis_<Month><Year>.xlsx` — 3 tabs (Taco Bell, Wendy's North, Wendy's South), shared with the ops team.

---

## Run Commands

```bash
# Full run — all 51 stores
python scrape.py --start 2025-03-01
python analyze.py --start 2025-03-01

# Test run — 1 store per brand (3 stores), saves Apify credits
python scrape.py --start 2025-03-01 --test
python analyze.py --start 2025-03-01

# Re-analyze only — no re-scrape, uses existing JSON in data/
python analyze.py --start 2025-03-01

# Regenerate stores.json after adding stores to Site List.xlsx
python generate_stores.py
```

---

## Store Structure

| Group | Brand | Count | States |
|-------|-------|-------|--------|
| Taco Bell | Taco Bell | 14 | NJ |
| Wendy's North | Wendy's | 11 | NJ, NY |
| Wendy's South | Wendy's | 26 | NJ, PA |

Store config lives in `stores.json` (gitignored). Source of truth is `Site List.xlsx`.

---

## AI Model

- **Primary:** `llama-3.3-70b-versatile` (Groq)
- **Fallback:** `llama-3.1-8b-instant` (Groq) — auto-triggered when 70b hits free tier rate limit
- **Last resort:** `gemma2-9b-it` (Groq)
- 2-second throttle between calls to stay under free tier RPM limit
- On full 51-store batch, 70b consistently rate-limits — 8b fallback handles all overflow cleanly

Output format per store:
```
SUMMARY:
• [descriptive bullet referencing actual review patterns]
• ...

IMPROVEMENTS:
• [2-5 word area]
• ...
```

---

## Excel Output

Columns: Store #, Store Name, Full Address, Avg Rating (color-coded), Reviews Analyzed, Period, AI Summary & Action Items, Customer Reviews

Rating colors: red ≤ 3.4, yellow 3.5–3.9, green ≥ 4.0

Tab colors: Taco Bell = purple (#702082), Wendy's = red (#CC2222)

---

## Known Gotchas

**Store matching** — `analyze.py` matches reviews to stores using the review's `address` field (street_number, zip_code) as the primary key, NOT searchString. This was fixed after Apify tagged 45 South Road (Wendy's #9549, Poughkeepsie) reviews with the Main Street store's searchString because both stores are in the same city. Never revert to searchString-only matching.

**PermissionError on Excel save** — if `analyze.py` crashes with `PermissionError`, the output Excel is open in Excel. Close it and re-run.

**Decommissioned Groq models** — `llama3-70b-8192` and `llama3-8b-8192` are decommissioned as of mid-2026. Do not add them back as fallbacks.

**load_latest_reviews** — uses `os.path.getmtime` (not alphabetical sort) to pick the most recent JSON. `reviews_YYYY-MM-DD_test.json` sorts after `reviews_YYYY-MM-DD.json` alphabetically, so mtime is the only reliable method.

**Patching one store** — if only one store needs to be updated (e.g. wrong review match), patch that row directly in the existing Excel using openpyxl. Do NOT re-run the full 51-store analysis.

---

## Environment

- Python 3.14.5
- `.env` needs: `APIFY_API_TOKEN`, `GROQ_API_KEY`
- `pip install -r requirements.txt`
- `data/` and `output/` are gitignored — keep locally

## GitHub

https://github.com/Arpit-Shah-007/YnC_google_reviews_management (master branch)
Git user: Arpit Shah <ashah10@stevens.edu>

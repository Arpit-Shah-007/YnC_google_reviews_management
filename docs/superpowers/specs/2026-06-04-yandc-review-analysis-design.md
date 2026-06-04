# YANDC Google Review Analysis System — Design Spec

**Date:** 2026-06-04
**Author:** Arpit Shah
**Status:** Approved

---

## Overview

Yum and Chill Restaurant Group (YANDC) operates 14 Taco Bells in New Jersey and ~37 Wendy's across NJ, NY, and PA. The operations team needs per-store insights from Google Maps reviews so they can inform store managers of recurring issues and improvement actions.

This system is a two-script Python pipeline that:
1. Scrapes Google Maps reviews via Apify on demand
2. Analyzes them with Gemini AI and produces a branded Excel report

---

## Scope

- **In scope:** Scraping, AI analysis, Excel report generation for all ~51 stores
- **Out of scope:** Web dashboard, user authentication, scheduled automation, email sending (Arpit emails manually)
- **Users:** Arpit runs both scripts; ops team and store managers receive the Excel by email

---

## Store Groups

| Group | Count | States |
|---|---|---|
| Taco Bell | 14 | NJ |
| Wendy's North | 11 | NJ, NY |
| Wendy's South | ~26 | NJ, PA |

Store data sourced from `Site List.xlsx`. Master store config stored in `stores.json` (auto-generated).

---

## Project Structure

```
yandc_google_review_management/
├── Site List.xlsx              ← original store list (untouched)
├── stores.json                 ← generated master config with Google Maps URLs
├── scrape.py                   ← Script 1: trigger Apify, download raw reviews
├── analyze.py                  ← Script 2: analyze reviews, write Excel report
├── .env                        ← API keys (Apify token, Gemini API key)
├── data/
│   └── reviews_YYYY-MM-DD.json ← raw Apify output, named by run date
└── output/
    └── YANDC_Review_Analysis_MMMYYYY.xlsx
```

---

## Script 1: scrape.py

**Purpose:** Fetch fresh reviews from Google Maps via Apify and save raw output.

**Usage:**
```bash
python scrape.py --start 2025-03-01 --end 2025-06-01         # full run, all stores
python scrape.py --start 2025-03-01 --end 2025-06-01 --test  # test run, 1 store per brand
```

**Behavior:**
1. Reads `stores.json` to get all store Google Maps URLs
2. If `--test` flag is passed, selects the first store from each brand group (Taco Bell, Wendy's North, Wendy's South) — 3 stores total — and skips the rest
3. Calls Apify REST API to start a run of the `compass/Google-Maps-Reviews-Scraper` actor
4. Input: selected store URLs, `maxReviews: 50`, `reviewsSort: newest`, `language: en`, `personalData: false`, `reviewsOrigin: all`, `reviewsStartDate` set to `--start` arg
5. Polls run status every 30 seconds until complete
6. Downloads dataset and saves to `data/reviews_YYYY-MM-DD.json` (named by today's date; `reviews_YYYY-MM-DD_test.json` for test runs)

**Environment variables:**
- `APIFY_API_TOKEN`

**Cost:** Consumes Apify credits. Only run when fresh data is needed.

---

## Script 2: analyze.py

**Purpose:** Read raw reviews, analyze per store with Gemini, write Excel report.

**Usage:**
```bash
python analyze.py
```

**Behavior:**
1. Finds the most recent file in `data/`
2. Groups reviews by store (matched by Google Maps URL)
3. For each store, sends reviews to Gemini 1.5 Flash with this prompt structure:
   - Role: "You are an operations analyst for a fast-food restaurant group"
   - Input: all review text and star ratings for the store
   - Output: a 2-3 sentence plain-English summary of the main themes, followed by 2-3 numbered action items addressed to the store manager
4. Calculates average star rating per store
5. Writes Excel report to `output/YANDC_Review_Analysis_MMMYYYY.xlsx`

**Environment variables:**
- `GEMINI_API_KEY`

**Cost:** Free within Gemini 1.5 Flash free tier (15 RPM, 1M TPD). Re-runnable at any time without re-scraping.

---

## stores.json Format

Generated once from `Site List.xlsx`. Structure:

```json
[
  {
    "brand": "Taco Bell",
    "group": "Taco Bell",
    "store_number": "041966",
    "name": "Taco Bell #041966",
    "address": "3 Path Plaza, Jersey City, NJ 07036",
    "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Taco+Bell+3+Path+Plaza+Jersey+City+NJ+07036"
  }
]
```

`group` is one of: `Taco Bell`, `Wendy's North`, `Wendy's South`.

---

## Excel Output

**Filename:** `YANDC_Review_Analysis_MMMYYYY.xlsx` (e.g., `YANDC_Review_Analysis_Jun2025.xlsx`)

**Sheets:** 3 brand tabs — `Taco Bell`, `Wendy's North`, `Wendy's South`

**Columns per sheet:**

| Column | Content |
|---|---|
| Store # | Store number from site list |
| Store Name | Brand + city (e.g., "Taco Bell - Somerville") |
| Full Address | Street, city, state, ZIP |
| Avg Rating | Average star rating (1 decimal, e.g., 3.8) |
| Reviews Analyzed | Count of reviews included |
| Period | Date range of reviews (e.g., "Mar–Jun 2025") |
| AI Summary & Action Items | 2-3 sentence summary + numbered actions |

**Formatting:**
- Header row: brand color (Taco Bell = purple/gold, Wendy's = red/white), bold white text
- Avg Rating column: conditional color — red ≤ 3.4, yellow 3.5–3.9, green ≥ 4.0
- AI Summary column: text-wrapped, row height auto-sized
- Rows: alternating light background for readability
- All columns auto-width except AI Summary (fixed wide)

---

## Error Handling

- If Apify run fails: print error and exit with non-zero code. Raw data is never partially written.
- If a store has zero reviews in the date range: write "No reviews found in this period" in the summary column, leave rating blank.
- If Gemini API call fails for a store: write "Analysis unavailable" and continue to next store (don't abort the whole run).
- Missing `.env` keys: fail fast at startup with a clear message naming the missing variable.

---

## Setup Requirements

- Python 3.9+
- Packages: `requests`, `google-generativeai`, `openpyxl`, `python-dotenv`
- Apify account with `compass/Google-Maps-Reviews-Scraper` actor access
- Google AI Studio API key (free at aistudio.google.com)

---

## Future Considerations (out of scope for v1)

- Automated scheduling (cron/Task Scheduler)
- Trend comparison between runs (this period vs. last period)
- Email delivery automation

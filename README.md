# Y&C Review Hub

A full-stack dashboard for managing and analyzing Google Maps reviews across all Yum & Chill Restaurant Group locations. Scrapes reviews via Apify, runs AI analysis with Groq, and exports a branded Excel report — all driven from a web UI or the command line.

---

## Live

| Service | URL |
|---------|-----|
| Dashboard | https://yandc-review-hub.onrender.com |
| API | https://yandc-review-hub-api.onrender.com |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript |
| Backend API | FastAPI (Python) |
| Database | Supabase (PostgreSQL) — persistent store/brand data |
| AI Analysis | Groq — `llama-3.3-70b-versatile` with automatic fallback |
| Review Scraping | Apify — Google Maps Reviews Scraper |
| Excel Export | openpyxl |
| Deployment | Render (API as web service, frontend as static site) |

---

## Project Structure

```
repo/
├── backend/
│   ├── main.py            # FastAPI app — all /api/* endpoints
│   ├── scrape.py          # Pulls reviews from Apify
│   ├── analyze.py         # Groq AI analysis + Excel export
│   ├── generate_stores.py # Utility: Site List.xlsx → stores.json
│   ├── seed_db.py         # One-time: seeds Supabase from local JSON files
│   ├── brands.json        # Brand reference data (source of truth for seeding)
│   └── stores.json        # Store reference data (source of truth for seeding)
├── frontend/
│   ├── app/               # Next.js App Router pages
│   ├── components/        # Dashboard, StoreSelector, ManagementPanel, etc.
│   ├── lib/               # API client, types, helpers
│   └── public/            # Static assets (logo)
├── requirements.txt
├── runtime.txt
└── render.yaml
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- `APIFY_API_TOKEN` — from [apify.com](https://apify.com)
- `GROQ_API_KEY` — from [console.groq.com](https://console.groq.com)
- `SUPABASE_URL` and `SUPABASE_KEY` — from [supabase.com](https://supabase.com)

---

## Supabase Setup (one-time)

Create two tables in your Supabase project via the SQL Editor:

```sql
CREATE TABLE brands (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  color TEXT NOT NULL
);

CREATE TABLE stores (
  id SERIAL PRIMARY KEY,
  brand TEXT NOT NULL,
  "group" TEXT NOT NULL,
  store_number TEXT NOT NULL,
  name TEXT NOT NULL,
  address TEXT NOT NULL,
  google_maps_url TEXT NOT NULL,
  UNIQUE ("group", store_number)
);
```

Then seed with existing data:

```bash
python backend/seed_db.py
```

---

## Local Setup

```bash
# Backend
pip install -r requirements.txt

# Create .env with:
# APIFY_API_TOKEN=...
# GROQ_API_KEY=...
# SUPABASE_URL=...
# SUPABASE_KEY=...

# Frontend
cd frontend && npm install
```

> Without `SUPABASE_URL` / `SUPABASE_KEY`, the backend falls back to the local
> `brands.json` and `stores.json` files automatically.

---

## Running the Web Dashboard

```bash
# Terminal 1 — backend API
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:3000`.

---

## Running from the CLI

All scripts live in `backend/` and are run from the repo root.

### Full run — all stores

```bash
python backend/scrape.py --start 2025-03-01
python backend/analyze.py --start 2025-03-01
```

### Test run — 1 store per brand (saves Apify credits)

```bash
python backend/scrape.py --start 2025-03-01 --test
python backend/analyze.py --start 2025-03-01
```

### Specific stores only

```bash
python backend/scrape.py --start 2025-03-01 --stores "Taco Bell::1234,Wendy's North::5678"
python backend/analyze.py --start 2025-03-01 --stores "Taco Bell::1234,Wendy's North::5678"
```

### Re-run analysis only (no re-scrape, uses existing JSON in backend/data/)

```bash
python backend/analyze.py --start 2025-03-01
```

Output: `backend/output/Y&C_Google_Review_Analysis_MM_YYYY.xlsx`

### Regenerate stores.json from Site List.xlsx

```bash
python backend/generate_stores.py
```

Then re-run `seed_db.py` to sync new stores into Supabase.

---

## AI Model

Primary: `llama-3.3-70b-versatile` (Groq)
Fallback 1: `llama-3.1-8b-instant` — auto-triggered on rate limit
Fallback 2: `gemma2-9b-it`

The free Groq tier handles the full run. On a 51-store batch the 70b model rate-limits mid-run and the 8b fallback picks up cleanly.

---

## Environment Variables

| Variable | Where to get it |
|----------|----------------|
| `APIFY_API_TOKEN` | apify.com → Settings → Integrations |
| `GROQ_API_KEY` | console.groq.com → API Keys |
| `SUPABASE_URL` | Supabase dashboard → Settings → API → Project URL |
| `SUPABASE_KEY` | Supabase dashboard → Settings → API → anon public key |

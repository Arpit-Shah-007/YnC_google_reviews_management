# Y&C Review Hub

A full-stack dashboard for managing and analyzing Google Maps reviews across all Yum & Chill Restaurant Group locations. Scrapes reviews via Apify, runs AI analysis with Groq, and exports a branded Excel report — all driven from a web UI or the command line.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript |
| Backend API | FastAPI (Python) |
| AI Analysis | Groq — `llama-3.3-70b-versatile` with automatic fallback |
| Review Scraping | Apify — Google Maps Reviews Scraper |
| Excel Export | openpyxl |
| Deployment | Render (API as web service, frontend as static site) |

---

## Project Structure

```
repo/
├── backend/
│   ├── main.py            # FastAPI app — serves all /api/* endpoints
│   ├── scrape.py          # Pulls reviews from Apify
│   ├── analyze.py         # Groq AI analysis + Excel export
│   ├── generate_stores.py # One-time utility: Site List.xlsx → stores.json
│   ├── brands.json        # Brand groups and their colors
│   └── stores.json        # All store locations
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

---

## Setup

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env
# Fill in APIFY_API_TOKEN and GROQ_API_KEY in .env

# Frontend
cd frontend
npm install
```

---

## Running the Web Dashboard

```bash
# Terminal 1 — backend API
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
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

### Re-run analysis only (no re-scrape, uses existing JSON)

```bash
python backend/analyze.py --start 2025-03-01
```

Output lands in `backend/output/Y&C_Google_Review_Analysis_MM_YYYY.xlsx`.

### Regenerate stores.json from Site List.xlsx

```bash
python backend/generate_stores.py
```

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

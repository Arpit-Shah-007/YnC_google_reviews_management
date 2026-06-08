import glob as glob_module
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT = Path(__file__).parent  # backend/

app = FastAPI(title="Y&C Review Hub API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Supabase client — optional. Falls back to JSON files if env vars not set.
# ---------------------------------------------------------------------------
_supabase = None


def _get_db():
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if url and key:
            from supabase import create_client
            _supabase = create_client(url, key)
    return _supabase


def _list_brands_data() -> list[dict]:
    db = _get_db()
    if db:
        return db.table("brands").select("*").order("id").execute().data
    path = ROOT / "brands.json"
    return json.load(open(path)) if path.exists() else []


def _list_stores_data() -> list[dict]:
    db = _get_db()
    if db:
        return db.table("stores").select("*").order("id").execute().data
    path = ROOT / "stores.json"
    if not path.exists():
        raise HTTPException(503, "stores.json not found — run generate_stores.py or configure Supabase")
    return json.load(open(path))


def _sync_json_from_db() -> None:
    """Dump latest Supabase data to local JSON files so pipeline scripts can read them."""
    db = _get_db()
    if db is None:
        return  # local dev: JSON files already on disk
    stores = db.table("stores").select("*").order("id").execute().data
    brands = db.table("brands").select("*").order("id").execute().data
    with open(ROOT / "stores.json", "w") as f:
        json.dump(stores, f)
    with open(ROOT / "brands.json", "w") as f:
        json.dump(brands, f)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    start_date: str
    end_date: Optional[str] = None
    test: bool = False
    selected_stores: Optional[list[str]] = None


class NewStore(BaseModel):
    store_number: str
    name: str
    address: str
    group: str
    google_maps_url: str = ""


class NewBrand(BaseModel):
    name: str
    color: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/run")
async def start_run(req: RunRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "phase": "starting", "progress": 0, "message": "Queued..."}
    background_tasks.add_task(_run_pipeline, job_id, req)
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/api/download")
def download_report():
    files = sorted(
        glob_module.glob(str(ROOT / "output" / "*.xlsx")),
        key=os.path.getmtime,
        reverse=True,
    )
    if not files:
        raise HTTPException(status_code=404, detail="No report found — run a job first")
    path = files[0]
    return FileResponse(
        path,
        filename=Path(path).name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/brands")
def list_brands():
    return _list_brands_data()


@app.post("/api/brands")
def add_brand(brand: NewBrand):
    db = _get_db()
    if db:
        existing = db.table("brands").select("id").eq("name", brand.name).execute().data
        if existing:
            raise HTTPException(status_code=409, detail="Brand already exists")
        db.table("brands").insert({"name": brand.name, "color": brand.color}).execute()
        total = len(db.table("brands").select("id").execute().data)
    else:
        brands_path = ROOT / "brands.json"
        brands = json.load(open(brands_path)) if brands_path.exists() else []
        if any(b["name"] == brand.name for b in brands):
            raise HTTPException(status_code=409, detail="Brand already exists")
        brands.append({"name": brand.name, "color": brand.color})
        with open(brands_path, "w") as f:
            json.dump(brands, f, indent=2)
        total = len(brands)
    return {"ok": True, "total": total}


@app.get("/api/stores")
def list_stores():
    return _list_stores_data()


@app.post("/api/stores")
def add_store(store: NewStore):
    maps_url = store.google_maps_url or (
        f"https://www.google.com/maps/search/?api=1&query={quote_plus(f'{store.group} #{store.store_number} {store.address}')}"
    )
    entry = {
        "brand": store.group,
        "group": store.group,
        "store_number": store.store_number,
        "name": f"{store.group} #{store.store_number}",
        "address": store.address,
        "google_maps_url": maps_url,
    }
    db = _get_db()
    if db:
        db.table("stores").insert(entry).execute()
        total = len(db.table("stores").select("id").execute().data)
    else:
        stores_path = ROOT / "stores.json"
        if not stores_path.exists():
            raise HTTPException(503, "stores.json not found")
        stores = json.load(open(stores_path))
        stores.append(entry)
        with open(stores_path, "w") as f:
            json.dump(stores, f, indent=2)
        total = len(stores)
    return {"ok": True, "total": total}


@app.post("/api/fill-maps-urls")
def fill_maps_urls():
    db = _get_db()
    if db:
        stores = db.table("stores").select("*").execute().data
        updated = 0
        for store in stores:
            if not store.get("google_maps_url"):
                query = quote_plus(f"{store['name']} {store['address']}")
                url = f"https://www.google.com/maps/search/?api=1&query={query}"
                db.table("stores").update({"google_maps_url": url}).eq("id", store["id"]).execute()
                updated += 1
        return {"updated": updated, "total": len(stores)}
    else:
        stores_path = ROOT / "stores.json"
        if not stores_path.exists():
            raise HTTPException(503, "stores.json not found")
        stores = json.load(open(stores_path))
        updated = 0
        for store in stores:
            if not store.get("google_maps_url"):
                query = quote_plus(f"{store['name']} {store['address']}")
                store["google_maps_url"] = f"https://www.google.com/maps/search/?api=1&query={query}"
                updated += 1
        with open(stores_path, "w") as f:
            json.dump(stores, f, indent=2)
        return {"updated": updated, "total": len(stores)}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def _update(job_id: str, phase: str, progress: int, message: str, status: str = "running") -> None:
    jobs[job_id] = {"status": status, "phase": phase, "progress": progress, "message": message}


def _run_pipeline(job_id: str, req: RunRequest) -> None:
    try:
        _update(job_id, "scraping", 10, "Scraping Google reviews via Apify...")

        # Sync latest stores/brands from Supabase to local JSON for the pipeline scripts
        _sync_json_from_db()

        cmd = ["python", str(ROOT / "scrape.py"), "--start", req.start_date]
        if req.end_date:
            cmd += ["--end", req.end_date]
        if req.test:
            cmd.append("--test")
        if req.selected_stores:
            cmd += ["--stores", ",".join(req.selected_stores)]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            err = (result.stderr or result.stdout)[-500:]
            _update(job_id, "scraping", 10, f"Scrape failed: {err}", status="error")
            return

        _update(job_id, "analyzing", 55, "Running AI analysis with Groq...")
        cmd2 = ["python", str(ROOT / "analyze.py"), "--start", req.start_date]
        if req.selected_stores:
            cmd2 += ["--stores", ",".join(req.selected_stores)]
        result2 = subprocess.run(cmd2, cwd=ROOT, capture_output=True, text=True, timeout=3600)
        if result2.returncode != 0:
            err = (result2.stderr or result2.stdout)[-500:]
            _update(job_id, "analyzing", 55, f"Analysis failed: {err}", status="error")
            return

        _update(job_id, "done", 100, "Report ready — click Download", status="done")

    except subprocess.TimeoutExpired:
        _update(job_id, "error", 0, "Job timed out after 60 minutes", status="error")
    except Exception as e:
        _update(job_id, "error", 0, str(e), status="error")

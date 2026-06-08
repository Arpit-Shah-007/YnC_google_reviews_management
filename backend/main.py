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
from fastapi.responses import FileResponse  # used by download endpoint
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


class RunRequest(BaseModel):
    start_date: str
    end_date: Optional[str] = None
    test: bool = False
    selected_stores: Optional[list[str]] = None  # composite keys "group::store_number"


class NewStore(BaseModel):
    store_number: str
    name: str
    address: str
    group: str
    google_maps_url: str = ""


class NewBrand(BaseModel):
    name: str
    color: str


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
    brands_path = ROOT / "brands.json"
    if not brands_path.exists():
        return []
    with open(brands_path) as f:
        return json.load(f)


@app.post("/api/brands")
def add_brand(brand: NewBrand):
    brands_path = ROOT / "brands.json"
    brands = json.load(open(brands_path)) if brands_path.exists() else []
    if any(b["name"] == brand.name for b in brands):
        raise HTTPException(status_code=409, detail="Brand already exists")
    brands.append({"name": brand.name, "color": brand.color})
    with open(brands_path, "w") as f:
        json.dump(brands, f, indent=2)
    return {"ok": True, "total": len(brands)}


@app.post("/api/fill-maps-urls")
def fill_maps_urls():
    stores_path = ROOT / "stores.json"
    if not stores_path.exists():
        raise HTTPException(status_code=503, detail="stores.json not found")
    with open(stores_path) as f:
        stores = json.load(f)
    updated = 0
    for store in stores:
        if not store.get("google_maps_url"):
            query = quote_plus(f"{store['name']} {store['address']}")
            store["google_maps_url"] = f"https://www.google.com/maps/search/?api=1&query={query}"
            updated += 1
    with open(stores_path, "w") as f:
        json.dump(stores, f, indent=2)
    return {"updated": updated, "total": len(stores)}


@app.get("/api/stores")
def list_stores():
    stores_path = ROOT / "stores.json"
    if not stores_path.exists():
        raise HTTPException(status_code=503, detail="stores.json not found — run generate_stores.py first")
    with open(stores_path) as f:
        return json.load(f)


@app.post("/api/stores")
def add_store(store: NewStore):
    stores_path = ROOT / "stores.json"
    if not stores_path.exists():
        raise HTTPException(status_code=503, detail="stores.json not found")
    with open(stores_path) as f:
        stores = json.load(f)
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
    stores.append(entry)
    with open(stores_path, "w") as f:
        json.dump(stores, f, indent=2)
    return {"ok": True, "total": len(stores)}


def _update(job_id: str, phase: str, progress: int, message: str, status: str = "running") -> None:
    jobs[job_id] = {"status": status, "phase": phase, "progress": progress, "message": message}


def _run_pipeline(job_id: str, req: RunRequest) -> None:
    try:
        _update(job_id, "scraping", 10, "Scraping Google reviews via Apify...")
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

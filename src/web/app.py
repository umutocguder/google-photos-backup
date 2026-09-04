import threading
from pathlib import Path
from typing import Optional
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.auth import GoogleAuthManager
from src.client import GooglePhotosClient
from src.config import config
from src.database import DatabaseManager
from src.downloader import MediaDownloader

app = FastAPI(title="Google Photos Backup Server", version="0.1.0")

templates_dir = Path(__file__).resolve().parent / "templates"
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

db = DatabaseManager()
auth_mgr = GoogleAuthManager()

# Track active background sync status
sync_state = {
    "is_running": False,
    "run_id": None,
    "scanned": 0,
    "downloaded": 0,
    "deduplicated": 0,
    "bytes": 0,
    "last_error": None,
}

def _run_background_sync(limit: Optional[int] = None, organize: str = "date"):
    global sync_state
    sync_state["is_running"] = True
    sync_state["scanned"] = 0
    sync_state["downloaded"] = 0
    sync_state["deduplicated"] = 0
    sync_state["bytes"] = 0
    sync_state["last_error"] = None

    run_id = db.start_sync_run()
    sync_state["run_id"] = run_id

    try:
        client = GooglePhotosClient()
        downloader = MediaDownloader(db_manager=db, max_workers=config.max_workers, organize_by=organize)

        batch = []
        for item in client.iterate_all_media_items(max_items=limit):
            batch.append(item)
            sync_state["scanned"] += 1

            if len(batch) >= 20:
                res = downloader.download_batch_concurrent(batch)
                sync_state["downloaded"] += res["downloaded"]
                sync_state["deduplicated"] += res["deduplicated"]
                sync_state["bytes"] += res["bytes"]
                batch = []

        if batch:
            res = downloader.download_batch_concurrent(batch)
            sync_state["downloaded"] += res["downloaded"]
            sync_state["deduplicated"] += res["deduplicated"]
            sync_state["bytes"] += res["bytes"]

        db.finish_sync_run(
            run_id,
            sync_state["scanned"],
            sync_state["downloaded"],
            sync_state["bytes"],
            "completed",
        )
    except Exception as e:
        sync_state["last_error"] = str(e)
        db.finish_sync_run(
            run_id,
            sync_state["scanned"],
            sync_state["downloaded"],
            sync_state["bytes"],
            "failed",
            str(e),
        )
    finally:
        sync_state["is_running"] = False

@app.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    """Render main dashboard view."""
    stats = db.get_stats()
    recent_items = db.get_recent_items(limit=12)
    albums = db.list_albums()
    is_auth = auth_mgr.is_authenticated()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "stats": stats,
            "recent_items": recent_items,
            "albums": albums,
            "is_auth": is_auth,
            "sync_state": sync_state,
        },
    )

@app.get("/api/stats")
async def api_stats():
    """Return live backup metrics."""
    return JSONResponse(db.get_stats())

@app.get("/api/status")
async def api_status():
    """Return background sync running status."""
    return JSONResponse(sync_state)

@app.post("/api/sync")
async def api_trigger_sync(background_tasks: BackgroundTasks, limit: Optional[int] = None):
    """Trigger an asynchronous incremental backup."""
    if sync_state["is_running"]:
        return JSONResponse({"status": "error", "message": "Sync is already in progress"}, status_code=409)

    background_tasks.add_task(_run_background_sync, limit=limit)
    return JSONResponse({"status": "started", "message": "Incremental backup initiated in background"})

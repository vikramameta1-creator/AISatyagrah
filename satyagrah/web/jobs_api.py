from __future__ import annotations

import csv
import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, APIRouter, Request, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


# ---------------------------------------------------------------------
# Paths (this file is: <ROOT>\satyagrah\web\jobs_api.py)
# ---------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
ROOT_DIR = THIS_FILE.parents[2]
UI_DIR = ROOT_DIR / "ui"
RUNS_DIR = ROOT_DIR / "data" / "runs"
PLAN_NAME = "newsroom_plan.jsonl"


# ---------------------------------------------------------------------
# Auth: if AUTH_TOKEN env var set, require x-auth header (or Bearer)
# ---------------------------------------------------------------------
def _required_token() -> str:
    return (os.getenv("AUTH_TOKEN") or "").strip()

def _get_request_token(req: Request) -> str:
    # Prefer x-auth header, fallback to Authorization: Bearer <token>
    tok = (req.headers.get("x-auth") or "").strip()
    if tok:
        return tok
    auth = (req.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""

def require_auth(req: Request) -> None:
    need = _required_token()
    if not need:
        return
    got = _get_request_token(req)
    if not got or got != need:
        raise HTTPException(status_code=401, detail="Invalid or missing x-auth token")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def ensure_dirs() -> None:
    UI_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

def norm_date(d: Optional[str]) -> str:
    if d and str(d).strip():
        return str(d).strip()
    return date.today().isoformat()

def run_dir(d: str) -> Path:
    return RUNS_DIR / d

def plan_path(d: str) -> Path:
    return run_dir(d) / PLAN_NAME

def read_jsonl(p: Path) -> List[Dict[str, Any]]:
    if not p.exists():
        return []
    items: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            # skip bad line
            continue
    return items

def write_jsonl(p: Path, items: List[Dict[str, Any]]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = "\n".join(json.dumps(it, ensure_ascii=False) for it in items) + ("\n" if items else "")
    p.write_text(txt, encoding="utf-8")

def latest_plan_date(platform: str = "telegram") -> Optional[str]:
    if not RUNS_DIR.exists():
        return None
    dates: List[str] = []
    for child in RUNS_DIR.iterdir():
        if not child.is_dir():
            continue
        pp = child / PLAN_NAME
        if not pp.exists():
            continue
        # If platform filter, ensure at least one item for that platform exists
        try:
            items = read_jsonl(pp)
            if platform:
                if any((it.get("platform") or "") == platform for it in items):
                    dates.append(child.name)
            else:
                dates.append(child.name)
        except Exception:
            continue
    dates.sort()
    return dates[-1] if dates else None

def ensure_ids(items: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
    # Guarantee id/topic_id exist (t1,t2,...)
    used = set()
    for it in items:
        if it.get("platform") == platform and it.get("id"):
            used.add(str(it["id"]))
    n = 1
    for it in items:
        if it.get("platform") != platform:
            continue
        if not it.get("id"):
            while f"t{n}" in used:
                n += 1
            it["id"] = f"t{n}"
            it["topic_id"] = it.get("topic_id") or it["id"]
            used.add(it["id"])
            n += 1
        if not it.get("topic_id"):
            it["topic_id"] = it["id"]
    return items

def counts_for(items: List[Dict[str, Any]], platform: str) -> Dict[str, int]:
    c = {"draft": 0, "approved": 0, "sent": 0}
    for it in items:
        if platform and it.get("platform") != platform:
            continue
        st = (it.get("status") or "draft").lower()
        if st not in c:
            st = "draft"
        c[st] += 1
    return c

def filter_items(items: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
    if not platform:
        return items
    return [it for it in items if (it.get("platform") or "") == platform]


# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------
router = APIRouter()


@router.get("/api/health")
def api_health():
    return {"ok": True}

@router.get("/api/version")
def api_version():
    return {"app": "AISatyagrah Jobs API", "newsroom": True}

@router.get("/favicon.ico")
def favicon():
    # avoid noisy 404s
    return PlainTextResponse("", status_code=204)


@router.get("/ui/newsroom", response_class=HTMLResponse)
def ui_newsroom():
    p = UI_DIR / "newsroom.html"
    if not p.exists():
        raise HTTPException(404, "newsroom.html not found")
    return FileResponse(str(p))


@router.get("/api/newsroom/latest")
def newsroom_latest(request: Request, platform: str = Query("telegram")):
    require_auth(request)
    d = latest_plan_date(platform=platform) or norm_date(None)
    return {"date": d, "platform": platform}


@router.get("/api/newsroom/plan")
def newsroom_plan(
    request: Request,
    date: Optional[str] = Query(None),
    platform: str = Query("telegram"),
):
    require_auth(request)
    ensure_dirs()

    d = norm_date(date)
    p = plan_path(d)
    items = read_jsonl(p)
    items = ensure_ids(items, platform)
    write_jsonl(p, items)

    out = filter_items(items, platform)
    return {
        "date": d,
        "platform": platform,
        "counts": counts_for(items, platform),
        "items": out,
    }


@router.post("/api/newsroom/status")
def newsroom_status(
    request: Request,
    date: str = Query(...),
    platform: str = Query("telegram"),
    payload: Dict[str, Any] = Body(...),
):
    require_auth(request)
    ensure_dirs()

    d = norm_date(date)
    item_id = str(payload.get("id") or "").strip()
    new_status = str(payload.get("status") or "").strip().lower()

    if not item_id:
        raise HTTPException(400, "Missing id")
    if new_status not in ("draft", "approved", "sent"):
        raise HTTPException(400, "Invalid status")

    p = plan_path(d)
    items = read_jsonl(p)
    changed = 0

    for it in items:
        if (it.get("platform") or "") == platform and str(it.get("id") or "") == item_id:
            prev = (it.get("status") or "draft").lower()
            it["prev_status"] = prev
            it["status"] = new_status
            changed = 1
            break

    write_jsonl(p, ensure_ids(items, platform))
    return {"date": d, "platform": platform, "id": item_id, "changed": changed, "status": new_status}


@router.post("/api/newsroom/undo")
def newsroom_undo(
    request: Request,
    date: str = Query(...),
    platform: str = Query("telegram"),
    payload: Dict[str, Any] = Body(...),
):
    require_auth(request)
    d = norm_date(date)
    item_id = str(payload.get("id") or "").strip()
    if not item_id:
        raise HTTPException(400, "Missing id")

    p = plan_path(d)
    items = read_jsonl(p)
    changed = 0
    for it in items:
        if (it.get("platform") or "") == platform and str(it.get("id") or "") == item_id:
            prev = (it.get("prev_status") or "draft").lower()
            if prev not in ("draft", "approved", "sent"):
                prev = "draft"
            it["status"] = prev
            changed = 1
            break

    write_jsonl(p, ensure_ids(items, platform))
    return {"date": d, "platform": platform, "id": item_id, "changed": changed}


@router.post("/api/newsroom/approve_all")
def newsroom_approve_all(
    request: Request,
    date: str = Query(...),
    platform: str = Query("telegram"),
):
    require_auth(request)
    ensure_dirs()

    d = norm_date(date)
    p = plan_path(d)
    items = read_jsonl(p)

    changed = 0
    for it in items:
        if (it.get("platform") or "") != platform:
            continue
        st = (it.get("status") or "draft").lower()
        if st == "draft":
            it["prev_status"] = st
            it["status"] = "approved"
            changed += 1

    write_jsonl(p, ensure_ids(items, platform))
    return {"date": d, "platform": platform, "approved": changed}


@router.post("/api/newsroom/run")
def newsroom_run(request: Request, payload: Dict[str, Any] = Body(...)):
    require_auth(request)
    ensure_dirs()

    d = norm_date(payload.get("date"))
    platform = str(payload.get("platform") or "telegram").strip()
    dry_run = bool(payload.get("dry_run", True))
    confirm = bool(payload.get("confirm", False))

    p = plan_path(d)
    items = read_jsonl(p)
    items = ensure_ids(items, platform)

    # candidates: approved (or draft if you really want — we keep approved only)
    candidates = [
        it for it in items
        if (it.get("platform") or "") == platform and (it.get("status") or "draft").lower() == "approved"
    ]

    sent = 0
    messages: List[str] = []

    for it in candidates:
        msg = ""
        if it.get("title"):
            msg += str(it["title"]).strip() + "\n"
        msg += str(it.get("snippet") or "").strip()
        h = str(it.get("hashtags") or "").strip()
        if h:
            msg += "\n" + h
        msg = msg.strip()
        messages.append(msg)

        if (not dry_run) and confirm:
            # Stub: mark as sent (real Telegram send can be wired later)
            it["prev_status"] = (it.get("status") or "approved").lower()
            it["status"] = "sent"
            it["sent_at"] = datetime.utcnow().isoformat() + "Z"
            sent += 1

    write_jsonl(p, ensure_ids(items, platform))

    return {
        "date": d,
        "platform": platform,
        "dry_run": dry_run,
        "confirm": confirm,
        "candidates": len(candidates),
        "sent": sent,
        "preview": messages[:50],  # cap
    }


@router.post("/api/newsroom/import_csv")
async def newsroom_import_csv(
    request: Request,
    date: str = Query(...),
    platform: str = Query("telegram"),
    file: UploadFile = File(...),
):
    require_auth(request)
    ensure_dirs()

    d = norm_date(date)
    raw = (await file.read()).decode("utf-8", errors="replace")
    reader = csv.DictReader(raw.splitlines())
    incoming: List[Dict[str, Any]] = []

    for row in reader:
        rid = (row.get("id") or row.get("topic_id") or "").strip() or None
        topic_id = (row.get("topic_id") or rid or "").strip() or None
        title = (row.get("title") or "").strip()
        snippet = (row.get("snippet") or row.get("text") or row.get("caption") or "").strip()
        hashtags = (row.get("hashtags") or "").strip()
        status = (row.get("status") or "draft").strip().lower()
        if status not in ("draft", "approved", "sent"):
            status = "draft"

        incoming.append({
            "date": d,
            "platform": platform,
            "status": status,
            "id": rid,
            "topic_id": topic_id,
            "title": title,
            "snippet": snippet,
            "hashtags": hashtags,
        })

    p = plan_path(d)
    items = read_jsonl(p)

    # Merge by (platform,id) when id exists
    idx: Dict[Tuple[str, str], int] = {}
    for i, it in enumerate(items):
        pid = str(it.get("id") or "").strip()
        if pid and (it.get("platform") or ""):
            idx[(it["platform"], pid)] = i

    added = 0
    updated = 0
    for it in incoming:
        pid = str(it.get("id") or "").strip()
        key = (platform, pid) if pid else None
        if key and key in idx:
            items[idx[key]].update(it)
            updated += 1
        else:
            items.append(it)
            added += 1

    items = ensure_ids(items, platform)
    write_jsonl(p, items)

    return {"date": d, "platform": platform, "added": added, "updated": updated, "total": len(filter_items(items, platform))}


@router.get("/api/newsroom/ig_captions")
def newsroom_ig_captions(
    request: Request,
    date: Optional[str] = Query(None),
):
    require_auth(request)
    ensure_dirs()

    d = norm_date(date)
    p = plan_path(d)
    items = read_jsonl(p)

    # simple captions file: one per line (title + snippet + hashtags)
    lines: List[str] = []
    for it in items:
        if (it.get("platform") or "") != "instagram":
            continue
        st = (it.get("status") or "draft").lower()
        if st not in ("approved", "sent"):
            continue
        cap = ""
        if it.get("title"):
            cap += str(it["title"]).strip() + "\n"
        cap += str(it.get("snippet") or "").strip()
        h = str(it.get("hashtags") or "").strip()
        if h:
            cap += "\n" + h
        cap = cap.strip()
        if cap:
            lines.append(cap)

    if not lines:
        lines = ["(no instagram captions for this date)"]

    txt = "\n\n---\n\n".join(lines) + "\n"
    fn = f"instagram_captions_{d}.txt"
    headers = {"Content-Disposition": f'attachment; filename="{fn}"'}
    return PlainTextResponse(txt, headers=headers)


def create_app() -> FastAPI:
    ensure_dirs()
    app = FastAPI(title="AISatyagrah Jobs API")

    # Static UI assets
    app.mount("/ui-static", StaticFiles(directory=str(UI_DIR)), name="ui-static")

    # API routes
    app.include_router(router)

    return app


# uvicorn satyagrah.web.jobs_api:app
app = create_app()

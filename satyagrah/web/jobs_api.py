from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import (
    APIRouter,
    FastAPI,
    File,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware


# ---------------------------
# Paths (NEVER depend on CWD)
# ---------------------------

HERE = Path(__file__).resolve()
# satyagrah/web/jobs_api.py -> project root is 3 levels up: D:\AISatyagrah
ROOT_DIR = HERE.parents[2]
DATA_DIR = ROOT_DIR / "data"
RUNS_DIR = DATA_DIR / "runs"
UI_DIR = ROOT_DIR / "ui"
AUTH_FILE_DEFAULT = ROOT_DIR / ".auth_token"


# ---------------------------
# Small JSONL utilities
# ---------------------------

def ensure_dirs() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def norm_date(d: Optional[str]) -> str:
    if not d:
        return datetime.utcnow().strftime("%Y-%m-%d")
    return d.strip()


def plan_path(date: str) -> Path:
    return RUNS_DIR / date / "newsroom_plan.jsonl"


def read_jsonl(p: Path) -> List[Dict[str, Any]]:
    if not p.exists():
        return []
    items: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                # ignore bad lines, don't crash UI
                continue
    return items


def write_jsonl(p: Path, rows: List[Dict[str, Any]]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def ensure_ids(items: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
    # stable-ish ids: t1..tN per platform if missing
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
            used.add(it["id"])
            n += 1
    return items


def filter_items(items: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
    plat = (platform or "").strip().lower()
    if plat in ("", "all", "*"):
        return items
    return [x for x in items if (x.get("platform") or "").strip().lower() == plat]


# ---------------------------
# Auth (robust, reloadable)
# ---------------------------

def _sha256_12(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def _read_text_no_bom(p: Path) -> str:
    # read as UTF-8, strip BOM and whitespace/newlines
    raw = p.read_text(encoding="utf-8", errors="strict")
    raw = raw.replace("\ufeff", "")
    return raw.strip()


@dataclass
class AuthState:
    enabled: bool
    header: str
    token: Optional[str]
    token_source: str  # "env" | "file" | "none"
    auth_file: str
    token_len: int
    token_sha256_12: str


class AuthManager:
    """
    Deterministic precedence:
      1) If AUTH_TOKEN is set (non-empty) -> use env
      2) Else if auth file exists and non-empty -> use file
      3) Else auth disabled
    Reload rules:
      - If file-based, re-read when file mtime changes
      - If env-based, re-check env every request (cheap)
    """

    def __init__(self, auth_file: Path, header: str = "x-auth"):
        self.auth_file = auth_file
        self.header = header
        self._cached_file_token: Optional[str] = None
        self._cached_file_mtime: Optional[float] = None

    def _get_env_token(self) -> Optional[str]:
        t = os.environ.get("AUTH_TOKEN")
        if t is None:
            return None
        t = t.strip()
        return t if t else None

    def _get_file_token(self) -> Optional[str]:
        if not self.auth_file.exists():
            self._cached_file_token = None
            self._cached_file_mtime = None
            return None

        try:
            mtime = self.auth_file.stat().st_mtime
        except Exception:
            return None

        if self._cached_file_mtime is not None and mtime == self._cached_file_mtime:
            return self._cached_file_token

        try:
            tok = _read_text_no_bom(self.auth_file)
        except Exception:
            tok = ""

        tok = tok.strip()
        self._cached_file_mtime = mtime
        self._cached_file_token = tok if tok else None
        return self._cached_file_token

    def state(self) -> AuthState:
        env_tok = self._get_env_token()
        if env_tok:
            return AuthState(
                enabled=True,
                header=self.header,
                token=env_tok,
                token_source="env",
                auth_file=str(self.auth_file),
                token_len=len(env_tok),
                token_sha256_12=_sha256_12(env_tok),
            )

        file_tok = self._get_file_token()
        if file_tok:
            return AuthState(
                enabled=True,
                header=self.header,
                token=file_tok,
                token_source="file",
                auth_file=str(self.auth_file),
                token_len=len(file_tok),
                token_sha256_12=_sha256_12(file_tok),
            )

        return AuthState(
            enabled=False,
            header=self.header,
            token=None,
            token_source="none",
            auth_file=str(self.auth_file),
            token_len=0,
            token_sha256_12="",
        )

    def check(self, request: Request) -> Tuple[bool, AuthState]:
        st = self.state()
        if not st.enabled:
            return True, st

        got = (request.headers.get(self.header) or "").strip()
        ok = bool(got) and (st.token is not None) and (got == st.token)
        return ok, st


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Returning JSONResponse avoids middleware exception-group weirdness.
    """

    def __init__(self, app, auth: AuthManager):
        super().__init__(app)
        self.auth = auth

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # always allow UI + version + auth status endpoints
        if (
            path.startswith("/ui")
            or path.startswith("/favicon")
            or path.startswith("/api/version")
            or path.startswith("/api/auth/enabled")
        ):
            return await call_next(request)

        ok, st = self.auth.check(request)
        if not ok:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": f"Invalid or missing {st.header} token",
                    "header": st.header,
                    "token_source": st.token_source,
                },
            )

        return await call_next(request)


# ---------------------------
# FastAPI app + routes
# ---------------------------

router = APIRouter()


@router.get("/api/version")
def api_version():
    return {
        "ok": True,
        "app": "AISatyagrah Jobs API",
        "root": str(ROOT_DIR / "satyagrah" / "web"),
    }


@router.get("/api/auth/enabled")
def api_auth_enabled(request: Request):
    auth: AuthManager = request.app.state.auth
    st = auth.state()
    # never return token itself
    return {
        "enabled": st.enabled,
        "header": st.header,
        "token_len": st.token_len,
        "token_sha256_12": st.token_sha256_12,
        "token_source": st.token_source,
        "auth_file": st.auth_file,
    }


@router.get("/api/newsroom/plan")
def newsroom_plan(date: Optional[str] = Query(None), platform: str = Query("all")):
    ensure_dirs()
    d = norm_date(date)
    p = plan_path(d)
    items = read_jsonl(p)
    plat = platform.strip() or "all"
    return {"date": d, "platform": plat, "items": filter_items(items, plat)}


@router.post("/api/newsroom/status")
async def newsroom_status(
    date: str = Query(...),
    platform: str = Query(...),
    item_id: str = Query(...),
    status: str = Query(...),
):
    ensure_dirs()
    d = norm_date(date)
    p = plan_path(d)
    items = read_jsonl(p)

    status = (status or "").strip().lower()
    if status not in ("draft", "approved", "sent"):
        status = "draft"

    updated = False
    for it in items:
        if (it.get("platform") or "") == platform and str(it.get("id") or "") == item_id:
            it["status"] = status
            it["updated_at"] = datetime.utcnow().isoformat() + "Z"
            updated = True
            break

    # keep ids stable for that platform
    items = ensure_ids(items, platform)
    write_jsonl(p, items)
    return {"date": d, "platform": platform, "updated": updated}


@router.post("/api/newsroom/approve_all")
def newsroom_approve_all(date: str = Query(...), platform: str = Query("telegram")):
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
            it["status"] = "approved"
            changed += 1

    items = ensure_ids(items, platform)
    write_jsonl(p, items)
    return {"date": d, "platform": platform, "approved": changed}


@router.post("/api/newsroom/run")
def newsroom_run(
    date: str = Query(...),
    platform: str = Query("telegram"),
    dry_run: bool = Query(True),
    confirm: bool = Query(False),
):
    """
    Simulated publisher for now:
      - dry_run: returns preview only
      - confirm=true: marks approved items as sent
    """
    ensure_dirs()
    d = norm_date(date)
    p = plan_path(d)
    items = read_jsonl(p)

    plat = (platform or "telegram").strip().lower()
    if plat in ("all", "*", ""):
        candidates = [it for it in items if (it.get("status") or "draft").lower() == "approved"]
    else:
        candidates = [
            it for it in items
            if (it.get("platform") or "").strip().lower() == plat
            and (it.get("status") or "draft").lower() == "approved"
        ]

    preview: List[str] = []
    sent = 0
    for it in candidates:
        msg = ""
        if it.get("title"):
            msg += str(it["title"]).strip() + "\n"
        msg += str(it.get("snippet") or "").strip()
        h = str(it.get("hashtags") or "").strip()
        if h:
            msg += "\n" + h
        msg = msg.strip()
        preview.append(msg)

        if (not dry_run) and confirm:
            it["prev_status"] = (it.get("status") or "approved").lower()
            it["status"] = "sent"
            it["sent_at"] = datetime.utcnow().isoformat() + "Z"
            sent += 1

    # keep ids stable per platform for all platforms present
    platforms = sorted({(it.get("platform") or "").strip() for it in items if (it.get("platform") or "").strip()})
    for pplat in platforms:
        items = ensure_ids(items, pplat)

    write_jsonl(p, items)
    return {
        "date": d,
        "platform": platform,
        "dry_run": dry_run,
        "confirm": confirm,
        "candidates": len(candidates),
        "sent": sent,
        "preview": preview[:50],
    }


@router.post("/api/newsroom/import_csv")
async def newsroom_import_csv(
    date: str = Query(...),
    platform: str = Query("telegram"),
    file: UploadFile = File(...),
):
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
        incoming.append(
            {
                "date": d,
                "platform": platform,
                "status": status,
                "id": rid,
                "topic_id": topic_id,
                "title": title,
                "snippet": snippet,
                "hashtags": hashtags,
            }
        )

    p = plan_path(d)
    items = read_jsonl(p)

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
    return {
        "date": d,
        "platform": platform,
        "added": added,
        "updated": updated,
        "total": len(filter_items(items, platform)),
    }


@router.get("/api/newsroom/ig_captions")
def newsroom_ig_captions(date: Optional[str] = Query(None)):
    ensure_dirs()
    d = norm_date(date)
    p = plan_path(d)
    items = read_jsonl(p)

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
    return PlainTextResponse(txt, headers={"Content-Disposition": f'attachment; filename="{fn}"'})


def create_app() -> FastAPI:
    ensure_dirs()
    app = FastAPI(title="AISatyagrah Jobs API")

    app.state.auth = AuthManager(auth_file=AUTH_FILE_DEFAULT, header="x-auth")
    app.add_middleware(AuthMiddleware, auth=app.state.auth)

    # --- UI route FIRST (so /ui/newsroom always works)
    @app.get("/ui/newsroom", include_in_schema=False, response_class=HTMLResponse)
    def _ui_newsroom():
        html_path = UI_DIR / "newsroom.html"
        if html_path.exists():
            return HTMLResponse(html_path.read_text(encoding="utf-8", errors="replace"))
        return HTMLResponse(f"<html><body><h2>Missing {html_path}</h2></body></html>")

    # static UI files (css/js/html)
    if UI_DIR.exists():
        app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")

    # API router
    app.include_router(router)

    return app


app = create_app()

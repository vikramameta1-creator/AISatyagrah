# OVERWRITE_NEWSROOM.ps1
$ErrorActionPreference = "Stop"

$ROOT = "D:\AISatyagrah"
$JOBS = Join-Path $ROOT "satyagrah\web\jobs_api.py"
$HTML = Join-Path $ROOT "ui\newsroom.html"
$JS   = Join-Path $ROOT "ui\newsroom.js"
$CSS  = Join-Path $ROOT "ui\newsroom.css"

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force (Join-Path $ROOT "exports\archive") | Out-Null

function Backup-IfExists($p) {
  if (Test-Path $p) {
    Copy-Item $p (Join-Path $ROOT ("exports\archive\" + (Split-Path $p -Leaf) + ".bak_" + $stamp)) -Force
  }
}

Backup-IfExists $JOBS
Backup-IfExists $HTML
Backup-IfExists $JS
Backup-IfExists $CSS

# -------------------------
# jobs_api.py (FULL FILE)
# -------------------------
$jobs_api = @'
from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


# -------------------------
# Paths (self-contained; no satyagrah.paths dependency)
# jobs_api.py is at: <root>\satyagrah\web\jobs_api.py
# -------------------------
THIS_FILE = Path(__file__).resolve()
ROOT_DIR = THIS_FILE.parents[2]
DATA_DIR = ROOT_DIR / "data"
RUNS_DIR = DATA_DIR / "runs"
UI_DIR = ROOT_DIR / "ui"

RUNS_DIR.mkdir(parents=True, exist_ok=True)
UI_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list_run_dates() -> List[str]:
    if not RUNS_DIR.exists():
        return []
    ds: List[str] = []
    for p in RUNS_DIR.iterdir():
        n = p.name
        if p.is_dir() and len(n) == 10 and n[4] == "-" and n[7] == "-":
            ds.append(n)
    return sorted(ds)


def _resolve_date(date: Optional[str]) -> str:
    date = (date or "").strip()
    if date:
        return date
    ds = _list_run_dates()
    if ds:
        return ds[-1]
    # fallback: today (UTC)
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _run_dir(date: str) -> Path:
    d = RUNS_DIR / date
    d.mkdir(parents=True, exist_ok=True)
    return d


def _plan_path(date: str) -> Path:
    return _run_dir(date) / "newsroom_plan.jsonl"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                # ignore bad lines instead of killing the UI
                continue
    return items


def _write_jsonl(path: Path, items: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def _counts(items: List[Dict[str, Any]]) -> Dict[str, int]:
    c = {"draft": 0, "approved": 0, "sent": 0}
    for it in items:
        s = (it.get("status") or "draft").lower()
        if s in c:
            c[s] += 1
    return c


def _ensure_ids(items: List[Dict[str, Any]], prefix: str = "t") -> None:
    used = set()
    for it in items:
        if it.get("id"):
            used.add(str(it["id"]))
    n = 1
    for it in items:
        if not it.get("id"):
            while f"{prefix}{n}" in used:
                n += 1
            it["id"] = f"{prefix}{n}"
            it.setdefault("topic_id", it["id"])
            used.add(it["id"])
            n += 1


def _filter_platform(items: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
    p = (platform or "").strip().lower()
    if not p:
        return items
    out = []
    for it in items:
        ip = (it.get("platform") or "").strip().lower()
        if not ip:
            it["platform"] = p
            ip = p
        if ip == p:
            out.append(it)
    return out


def _require_auth(x_auth: Optional[str]) -> None:
    token = os.getenv("AUTH_TOKEN", "").strip()
    if token:
        if not x_auth or x_auth.strip() != token:
            raise HTTPException(status_code=401, detail="Invalid or missing x-auth token")


class StatusReq(BaseModel):
    date: str
    platform: str = "telegram"
    id: str
    status: str


class UndoReq(BaseModel):
    date: str
    platform: str = "telegram"
    id: str


class RunReq(BaseModel):
    date: str
    platform: str = "telegram"
    dry_run: bool = True
    confirm: bool = False
    limit: int = 0
    ids: List[str] = Field(default_factory=list)


def create_app() -> FastAPI:
    app = FastAPI(title="AISatyagrah Jobs API (Newsroom)")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve UI assets (newsroom.js/css)
    app.mount("/ui-static", StaticFiles(directory=str(UI_DIR)), name="ui-static")

    @app.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/version")
    def version():
        return {"name": "jobs_api", "root": str(ROOT_DIR)}

    @app.get("/ui/newsroom", response_class=HTMLResponse)
    def ui_newsroom():
        p = UI_DIR / "newsroom.html"
        if not p.exists():
            return HTMLResponse("<h1>newsroom.html missing</h1>", status_code=500)
        return FileResponse(str(p))

    # -------------------------
    # Newsroom API
    # -------------------------
    @app.get("/api/newsroom/plan")
    def newsroom_plan(
        date: Optional[str] = Query(default=None),
        platform: str = Query(default="telegram"),
        x_auth: Optional[str] = Header(default=None, alias="x-auth"),
    ):
        _require_auth(x_auth)
        d = _resolve_date(date)
        p = _plan_path(d)
        items = _read_jsonl(p)
        items = _filter_platform(items, platform)
        _ensure_ids(items)
        _write_jsonl(p, items)
        return {"date": d, "platform": platform, "counts": _counts(items), "items": items}

    @app.post("/api/newsroom/import_csv")
    async def newsroom_import_csv(
        date: Optional[str] = Query(default=None),
        platform: str = Query(default="telegram"),
        replace: bool = Query(default=False),
        file: UploadFile = File(...),
        x_auth: Optional[str] = Header(default=None, alias="x-auth"),
    ):
        _require_auth(x_auth)
        d = _resolve_date(date)
        plan_p = _plan_path(d)

        raw = await file.read()
        try:
            text = raw.decode("utf-8-sig")
        except Exception:
            text = raw.decode("utf-8", errors="replace")

        reader = csv.DictReader(io.StringIO(text))
        new_items: List[Dict[str, Any]] = []
        for row in reader:
            row = {k: (v or "").strip() for k, v in row.items()}
            title = row.get("title", "")
            snippet = row.get("snippet", "")
            hashtags = row.get("hashtags", "")
            rid = row.get("id", "") or row.get("topic_id", "")

            # skip empty rows
            if not title and not snippet:
                continue

            it = {
                "date": d,
                "platform": platform,
                "status": "draft",
                "id": rid or None,
                "topic_id": rid or None,
                "title": title,
                "snippet": snippet,
                "hashtags": hashtags,
                "sent_at": None,
                "message_id": None,
            }
            new_items.append(it)

        existing = _read_jsonl(plan_p)
        existing = _filter_platform(existing, platform)

        if replace:
            merged = new_items
        else:
            merged = existing + new_items

        _ensure_ids(merged)
        _write_jsonl(plan_p, merged)
        return {"date": d, "platform": platform, "added": len(new_items), "total": len(merged), "path": str(plan_p)}

    @app.post("/api/newsroom/approve_all")
    def newsroom_approve_all(
        date: Optional[str] = Query(default=None),
        platform: str = Query(default="telegram"),
        x_auth: Optional[str] = Header(default=None, alias="x-auth"),
    ):
        _require_auth(x_auth)
        d = _resolve_date(date)
        plan_p = _plan_path(d)
        items = _filter_platform(_read_jsonl(plan_p), platform)
        _ensure_ids(items)

        changed = 0
        for it in items:
            if (it.get("status") or "draft").lower() == "draft":
                it["status"] = "approved"
                changed += 1

        _write_jsonl(plan_p, items)
        return {"date": d, "platform": platform, "approved": changed, "counts": _counts(items)}

    @app.post("/api/newsroom/status")
    def newsroom_status(req: StatusReq, x_auth: Optional[str] = Header(default=None, alias="x-auth")):
        _require_auth(x_auth)
        d = _resolve_date(req.date)
        plan_p = _plan_path(d)
        items = _filter_platform(_read_jsonl(plan_p), req.platform)
        _ensure_ids(items)

        changed = 0
        for it in items:
            if str(it.get("id")) == req.id:
                it["status"] = req.status.lower()
                changed = 1
                break

        _write_jsonl(plan_p, items)
        return {"date": d, "platform": req.platform, "id": req.id, "changed": changed}

    @app.post("/api/newsroom/undo")
    def newsroom_undo(req: UndoReq, x_auth: Optional[str] = Header(default=None, alias="x-auth")):
        _require_auth(x_auth)
        d = _resolve_date(req.date)
        plan_p = _plan_path(d)
        items = _filter_platform(_read_jsonl(plan_p), req.platform)
        _ensure_ids(items)

        changed = 0
        for it in items:
            if str(it.get("id")) == req.id:
                # undo "sent" -> "approved"
                it["status"] = "approved"
                it["sent_at"] = None
                it["message_id"] = None
                changed = 1
                break

        _write_jsonl(plan_p, items)
        return {"date": d, "platform": req.platform, "id": req.id, "changed": changed}

    @app.post("/api/newsroom/run")
    def newsroom_run(req: RunReq, x_auth: Optional[str] = Header(default=None, alias="x-auth")):
        _require_auth(x_auth)
        d = _resolve_date(req.date)
        plan_p = _plan_path(d)
        items = _filter_platform(_read_jsonl(plan_p), req.platform)
        _ensure_ids(items)

        # choose candidates
        approved = [it for it in items if (it.get("status") or "").lower() == "approved"]
        if req.ids:
            approved = [it for it in approved if str(it.get("id")) in set(req.ids)]
        if req.limit and req.limit > 0:
            approved = approved[: req.limit]

        sent = 0
        if req.dry_run:
            # no changes
            return {
                "date": d,
                "platform": req.platform,
                "dry_run": True,
                "confirm": req.confirm,
                "candidates": len(approved),
                "sent": 0,
                "plan_path": str(plan_p),
            }

        if not req.confirm:
            return {
                "date": d,
                "platform": req.platform,
                "dry_run": False,
                "confirm": False,
                "candidates": len(approved),
                "sent": 0,
                "plan_path": str(plan_p),
                "warning": "confirm=false (nothing sent).",
            }

        # mark as sent (real Telegram send should be wired here)
        for it in approved:
            it["status"] = "sent"
            it["sent_at"] = _now_iso()
            if not it.get("message_id"):
                it["message_id"] = f"mock_{it.get('id')}"
            sent += 1

        _write_jsonl(plan_p, items)
        return {
            "date": d,
            "platform": req.platform,
            "dry_run": False,
            "confirm": True,
            "candidates": len(approved),
            "sent": sent,
            "plan_path": str(plan_p),
        }

    @app.get("/api/newsroom/ig_captions")
    def newsroom_ig_captions(
        date: Optional[str] = Query(default=None),
        platform: str = Query(default="telegram"),
        x_auth: Optional[str] = Header(default=None, alias="x-auth"),
    ):
        _require_auth(x_auth)
        d = _resolve_date(date)
        plan_p = _plan_path(d)
        items = _filter_platform(_read_jsonl(plan_p), platform)
        _ensure_ids(items)

        outp = _run_dir(d) / "instagram_captions.txt"
        lines = []
        for it in items:
            sn = (it.get("snippet") or "").strip()
            ht = (it.get("hashtags") or "").strip()
            if not sn and not ht:
                continue
            if sn and ht:
                lines.append(sn + "\n" + ht + "\n")
            else:
                lines.append((sn or ht) + "\n")

        outp.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return {"date": d, "path": str(outp), "items": len(items)}

    return app


app = create_app()
'@

# -------------------------
# newsroom.html (FULL FILE)
# -------------------------
$newsroom_html = @'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>AISatyagrah - Newsroom</title>
  <link rel="stylesheet" href="/ui-static/newsroom.css"/>
</head>
<body>
  <div class="topbar">
    <input id="token" class="pill input" placeholder="x-auth token (optional)"/>
    <select id="platform" class="pill input">
      <option value="telegram">telegram</option>
      <option value="instagram">instagram</option>
    </select>
    <input id="date" class="pill input" type="date"/>

    <button id="btnLoad" class="pill btn">Load plan</button>
    <button id="btnLatest" class="pill btn">Latest telegram</button>

    <input id="csvFile" class="pill input" type="file" accept=".csv,text/csv"/>
    <button id="btnImport" class="pill btn">Import CSV</button>

    <button id="btnApproveAll" class="pill btn primary">Approve All</button>
    <button id="btnDryRun" class="pill btn">Dry-Run</button>
    <button id="btnPublish" class="pill btn danger">Publish (confirm)</button>
    <button id="btnIG" class="pill btn">IG captions</button>

    <input id="q" class="pill input grow" placeholder="search..."/>
    <button id="btnSearch" class="pill btn">Search</button>
  </div>

  <div class="tabs">
    <button class="pill tab active" data-filter="all">All</button>
    <button class="pill tab" data-filter="draft">Draft</button>
    <button class="pill tab" data-filter="approved">Approved</button>
    <button class="pill tab" data-filter="sent">Sent</button>
    <div id="statusline" class="statusline">Ready.</div>
  </div>

  <div id="grid" class="grid"></div>

  <div id="toast" class="toast hidden"></div>

  <script src="/ui-static/newsroom.js"></script>
</body>
</html>
'@

# -------------------------
# newsroom.js (FULL FILE)
# -------------------------
$newsroom_js = @'
(() => {
  const $ = (id) => document.getElementById(id);

  const state = {
    filter: "all",
    items: [],
    date: "",
    platform: "telegram",
  };

  function apiBase() {
    return window.location.origin;
  }

  function getToken() {
    const v = $("token").value.trim();
    localStorage.setItem("xauth", v);
    return v;
  }

  function loadToken() {
    const v = (localStorage.getItem("xauth") || "").trim();
    $("token").value = v;
    return v;
  }

  function toast(msg, ms=2500) {
    const t = $("toast");
    t.textContent = msg;
    t.classList.remove("hidden");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => t.classList.add("hidden"), ms);
  }

  function statusLine(msg) {
    $("statusline").textContent = msg;
  }

  function headersJson() {
    const h = { "Content-Type": "application/json" };
    const tok = (localStorage.getItem("xauth") || "").trim();
    if (tok) h["x-auth"] = tok;
    return h;
  }

  function headersNoJson() {
    const h = {};
    const tok = (localStorage.getItem("xauth") || "").trim();
    if (tok) h["x-auth"] = tok;
    return h;
  }

  function getDate() {
    const v = $("date").value;
    if (!v) return "";
    return v; // already YYYY-MM-DD
  }

  function getPlatform() {
    return $("platform").value;
  }

  async function fetchJson(url, opts={}) {
    const res = await fetch(url, opts);
    const txt = await res.text();
    let data = null;
    try { data = txt ? JSON.parse(txt) : null; } catch { data = txt; }
    if (!res.ok) {
      throw new Error(typeof data === "string" ? data : JSON.stringify(data));
    }
    return data;
  }

  function render() {
    const grid = $("grid");
    grid.innerHTML = "";

    const q = ($("q").value || "").trim().toLowerCase();

    const filtered = state.items.filter(it => {
      const st = (it.status || "draft").toLowerCase();
      if (state.filter !== "all" && st !== state.filter) return false;
      if (!q) return true;
      const blob = [
        it.id, it.title, it.snippet, it.hashtags, it.platform, it.status
      ].join(" ").toLowerCase();
      return blob.includes(q);
    });

    for (const it of filtered) {
      const card = document.createElement("div");
      card.className = "card";

      const st = (it.status || "draft").toLowerCase();
      card.innerHTML = `
        <div class="cardTop">
          <div class="pills">
            <span class="pill mini ${st}">${st.toUpperCase()}</span>
            <span class="pill mini">${(it.platform||"").toLowerCase()}</span>
            <span class="pill mini">${it.id || ""}</span>
          </div>
          <div class="actions">
            ${st === "draft" ? `<button class="pill btn mini primary" data-act="approve" data-id="${it.id}">Approve</button>` : ""}
            ${st === "sent" ? `<button class="pill btn mini" data-act="undo" data-id="${it.id}">Undo</button>` : ""}
            <button class="pill btn mini" data-act="edit" data-id="${it.id}">Edit</button>
          </div>
        </div>
        <div class="title">${it.title && it.title.trim() ? it.title : "(no title)"}</div>
        <div class="snippet">${(it.snippet || "").replaceAll("\n","<br/>")}</div>
        <div class="hashtags">${(it.hashtags || "").replaceAll("\n","<br/>")}</div>
      `;
      grid.appendChild(card);
    }

    statusLine(`date=${state.date} • platform=${state.platform} • showing=${filtered.length}/${state.items.length} • filter=${state.filter}`);
  }

  async function loadPlan(dateOpt=null, platformOpt=null) {
    const date = (dateOpt !== null) ? dateOpt : getDate();
    const platform = (platformOpt !== null) ? platformOpt : getPlatform();

    // IMPORTANT: backend will auto-pick latest date if date is blank.
    const url = new URL(apiBase() + "/api/newsroom/plan");
    if (date) url.searchParams.set("date", date);
    if (platform) url.searchParams.set("platform", platform);

    const data = await fetchJson(url.toString(), { headers: headersNoJson() });
    state.items = data.items || [];
    state.date = data.date || date || "";
    state.platform = data.platform || platform || "";
    toast(`Loaded ${state.items.length} item(s)`);
    render();
  }

  async function approveAll() {
    const date = getDate();
    const platform = getPlatform();
    const url = new URL(apiBase() + "/api/newsroom/approve_all");
    if (date) url.searchParams.set("date", date);
    url.searchParams.set("platform", platform);

    const data = await fetchJson(url.toString(), { method: "POST", headers: headersNoJson() });
    toast(`Approved: ${data.approved}`);
    await loadPlan(date, platform);
  }

  async function run(dryRun, confirm) {
    const date = getDate();
    const platform = getPlatform();

    const body = { date: date || "", platform, dry_run: dryRun, confirm: confirm, limit: 0, ids: [] };
    const data = await fetchJson(apiBase() + "/api/newsroom/run", {
      method: "POST",
      headers: headersJson(),
      body: JSON.stringify(body),
    });
    toast(`Run: candidates=${data.candidates} sent=${data.sent} dry_run=${data.dry_run}`);
    await loadPlan(date, platform);
  }

  async function igCaptions() {
    const date = getDate();
    const platform = getPlatform();
    const url = new URL(apiBase() + "/api/newsroom/ig_captions");
    if (date) url.searchParams.set("date", date);
    url.searchParams.set("platform", platform);
    const data = await fetchJson(url.toString(), { headers: headersNoJson() });
    toast(`Wrote: ${data.path}`);
  }

  async function importCsv() {
    const date = getDate();
    const platform = getPlatform();
    const f = $("csvFile").files && $("csvFile").files[0];
    if (!f) { toast("Pick a CSV first"); return; }

    const url = new URL(apiBase() + "/api/newsroom/import_csv");
    if (date) url.searchParams.set("date", date);
    url.searchParams.set("platform", platform);

    const fd = new FormData();
    fd.append("file", f, f.name);

    const data = await fetchJson(url.toString(), {
      method: "POST",
      headers: headersNoJson(),
      body: fd
    });

    toast(`Imported: added=${data.added} total=${data.total}`);
    await loadPlan(date, platform);
  }

  async function setStatus(id, status) {
    const date = getDate();
    const platform = getPlatform();
    const body = { date: date || "", platform, id, status };
    await fetchJson(apiBase() + "/api/newsroom/status", {
      method: "POST",
      headers: headersJson(),
      body: JSON.stringify(body),
    });
    await loadPlan(date, platform);
  }

  async function undo(id) {
    const date = getDate();
    const platform = getPlatform();
    const body = { date: date || "", platform, id };
    await fetchJson(apiBase() + "/api/newsroom/undo", {
      method: "POST",
      headers: headersJson(),
      body: JSON.stringify(body),
    });
    await loadPlan(date, platform);
  }

  async function editItem(id) {
    const it = state.items.find(x => String(x.id) === String(id));
    if (!it) return;

    const newSnippet = prompt("Edit snippet:", it.snippet || "");
    if (newSnippet === null) return;
    const newTags = prompt("Edit hashtags:", it.hashtags || "");
    if (newTags === null) return;

    it.snippet = newSnippet;
    it.hashtags = newTags;

    // Save by reusing /status? (simple approach: keep status same but update saved plan via status endpoint isn't enough)
    // For now: quick save by writing status endpoint with same status isn't correct, so we do a cheap trick:
    // Mark as same status but backend doesn't persist snippet/hashtags via status endpoint.
    // We'll just tell user to re-import CSV for now.
    toast("Edits are local-only right now (next step: add /api/newsroom/update_item).");
    render();
  }

  function bindTabs() {
    document.querySelectorAll(".tab").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
        btn.classList.add("active");
        state.filter = btn.dataset.filter || "all";
        render();
      });
    });
  }

  function bindActions() {
    $("btnLoad").addEventListener("click", () => loadPlan());
    $("btnLatest").addEventListener("click", () => loadPlan("", "telegram"));
    $("btnApproveAll").addEventListener("click", () => approveAll());
    $("btnDryRun").addEventListener("click", () => run(true, false));
    $("btnPublish").addEventListener("click", () => run(false, true));
    $("btnIG").addEventListener("click", () => igCaptions());
    $("btnImport").addEventListener("click", () => importCsv());
    $("btnSearch").addEventListener("click", () => render());
    $("q").addEventListener("keydown", (e) => { if (e.key === "Enter") render(); });

    $("grid").addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      const act = b.dataset.act;
      const id = b.dataset.id;
      if (!act || !id) return;

      if (act === "approve") setStatus(id, "approved").catch(err => toast("ERR " + err.message));
      else if (act === "undo") undo(id).catch(err => toast("ERR " + err.message));
      else if (act === "edit") editItem(id);
    });
  }

  function initDefaults() {
    loadToken();
    // set today by default
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth()+1).padStart(2,"0");
    const dd = String(today.getDate()).padStart(2,"0");
    $("date").value = `${yyyy}-${mm}-${dd}`;
    $("platform").value = "telegram";
  }

  window.addEventListener("DOMContentLoaded", async () => {
    initDefaults();
    bindTabs();
    bindActions();
    try {
      await loadPlan();
    } catch (e) {
      toast("Load failed: " + e.message);
      statusLine("Error: " + e.message);
    }
  });
})();
'@

# -------------------------
# newsroom.css (FULL FILE)
# -------------------------
$newsroom_css = @'
:root{
  --bg:#0b1020;
  --panel:#0f1730;
  --panel2:#0b142a;
  --text:#e7ecff;
  --muted:#aeb7de;
  --pill:#131d3b;
  --pill2:#182652;
  --danger:#ff5b57;
  --primary:#6f7dff;
  --stroke:#22315c;
}

*{box-sizing:border-box}
body{
  margin:0;
  background:linear-gradient(180deg, var(--bg), #070a14);
  color:var(--text);
  font-family:system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

.topbar{
  display:flex;
  gap:10px;
  padding:14px;
  align-items:center;
  flex-wrap:wrap;
  border-bottom:1px solid var(--stroke);
}

.tabs{
  display:flex;
  gap:10px;
  padding:12px 14px;
  align-items:center;
  flex-wrap:wrap;
  border-bottom:1px solid var(--stroke);
}

.statusline{
  margin-left:auto;
  color:var(--muted);
  font-size:13px;
}

.grid{
  padding:14px;
  display:grid;
  grid-template-columns:repeat(3, minmax(260px, 1fr));
  gap:14px;
}

@media (max-width: 1050px){
  .grid{grid-template-columns:repeat(2, minmax(260px, 1fr));}
}
@media (max-width: 720px){
  .grid{grid-template-columns:1fr;}
}

.pill{
  border:1px solid var(--stroke);
  background:var(--pill);
  color:var(--text);
  border-radius:999px;
  padding:10px 14px;
  font-size:14px;
}

.input{
  outline:none;
}

.grow{ flex: 1 1 240px; }

.btn{
  cursor:pointer;
}
.btn:hover{
  background:var(--pill2);
}

.primary{
  background:rgba(111,125,255,.25);
  border-color:rgba(111,125,255,.6);
}
.danger{
  background:rgba(255,91,87,.18);
  border-color:rgba(255,91,87,.65);
}

.tab.active{
  background:rgba(111,125,255,.25);
  border-color:rgba(111,125,255,.6);
}

.card{
  background:linear-gradient(180deg, var(--panel), var(--panel2));
  border:1px solid var(--stroke);
  border-radius:18px;
  padding:14px;
  min-height:170px;
}

.cardTop{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
  margin-bottom:10px;
}

.pills{display:flex; gap:8px; flex-wrap:wrap;}
.actions{display:flex; gap:8px; flex-wrap:wrap;}

.mini{
  padding:6px 10px;
  font-size:12px;
  opacity:.95;
}

.title{
  font-size:18px;
  font-weight:700;
  margin:8px 0;
}

.snippet{
  color:var(--text);
  line-height:1.35;
  margin-bottom:10px;
}

.hashtags{
  color:var(--muted);
  line-height:1.35;
  white-space:pre-wrap;
}

.draft{ border-color:#3a4c8a; }
.approved{ border-color:#5b8fff; }
.sent{ border-color:#41d09a; }

.toast{
  position:fixed;
  right:18px;
  bottom:18px;
  background:#101b39;
  border:1px solid var(--stroke);
  color:var(--text);
  padding:12px 14px;
  border-radius:14px;
  max-width:520px;
  box-shadow: 0 10px 30px rgba(0,0,0,.35);
}
.hidden{ display:none; }
'@

Set-Content -Encoding UTF8 -Path $JOBS -Value $jobs_api
Set-Content -Encoding UTF8 -Path $HTML -Value $newsroom_html
Set-Content -Encoding UTF8 -Path $JS   -Value $newsroom_js
Set-Content -Encoding UTF8 -Path $CSS  -Value $newsroom_css

Write-Host "Overwritten:" -ForegroundColor Green
Write-Host "  $JOBS"
Write-Host "  $HTML"
Write-Host "  $JS"
Write-Host "  $CSS"
Write-Host ""
Write-Host "Now start server:" -ForegroundColor Green
Write-Host '$env:AUTH_TOKEN="mysupersecrettoken"'
Write-Host 'uvicorn satyagrah.web.jobs_api:app --host 127.0.0.1 --port 9000 --reload'
Write-Host ""
Write-Host "Open UI:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:9000/ui/newsroom"

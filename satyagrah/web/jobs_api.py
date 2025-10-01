from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Any, List, Dict
from pathlib import Path
import zipfile, os
from ..models.db import ensure_db, list_jobs, list_results
from ..services.worker import enqueue_export_job, run_worker_once
import datetime as _dt

# ---------------------------------------------------------
# paths
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "state.db"
EXPORTS = ROOT / "exports"
DATA = ROOT / "data"

# ---------------------------------------------------------
# app + static mounts
# ---------------------------------------------------------
app = FastAPI(title="AISatyagrah Jobs API")
app.mount("/exports", StaticFiles(directory=str(EXPORTS)), name="exports")
app.mount("/data", StaticFiles(directory=str(DATA)), name="data")

# ---------------------------------------------------------
# models
# ---------------------------------------------------------
class ExportReq(BaseModel):
    date: Optional[str] = None
    args: Optional[dict[str, Any]] = None

class DateReq(BaseModel):
    date: Optional[str] = None

class SelectedReq(BaseModel):
    date: Optional[str] = None
    files: List[str]
    args: Optional[dict[str, Any]] = None

# ---------------------------------------------------------
# helpers
# ---------------------------------------------------------
def _today() -> str:
    return _dt.date.today().isoformat()

def _href_to_path(href: str) -> Path:
    h = href.replace("\\", "/")
    if h.startswith("/data/") or h.startswith("/exports/"):
        return ROOT / h.lstrip("/")
    return ROOT / h

# --- OPTIONAL auth guard (enabled only if AUTH_TOKEN env var is set) ---
def auth_guard(x_auth: str | None = Header(default=None)):
    token = os.environ.get("AUTH_TOKEN")
    if not token:
        return True                     # open API in dev if no token configured
    if x_auth != token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# ---------------------------------------------------------
# api
# ---------------------------------------------------------
@app.get("/api/health")
def api_health():
    ensure_db(DB_PATH)
    q = len(list_jobs(DB_PATH, limit=1000, status="queued"))
    r = len(list_jobs(DB_PATH, limit=1000, status="running"))
    return {"ok": True, "queued": q, "running": r}

@app.get("/api/jobs")
def api_jobs(limit: int = 50, status: Optional[str] = None, date: Optional[str] = None):
    ensure_db(DB_PATH)
    return list_jobs(DB_PATH, limit=limit, status=status, date=date)

@app.get("/api/results")
def api_results(limit: int = 200, date: Optional[str] = None, job_id: Optional[int] = None):
    ensure_db(DB_PATH)
    rows = list_results(DB_PATH, limit=limit, date=date, job_id=job_id)
    for r in rows:
        p = Path(r["path"])
        r["size"] = p.stat().st_size if p.exists() else 0
        parts = str(p).replace("\\", "/").split("/exports/", 1)
        r["href"] = "/exports/" + parts[1] if len(parts) == 2 else ""
    return rows

@app.get("/api/images")
def api_images(date: Optional[str] = None, limit: int = 400) -> List[Dict[str, Any]]:
    date = date or _today()
    bases = [DATA / "runs" / date / "art", DATA / "runs" / date, EXPORTS / date]
    hits: List[Path] = []
    for base in bases:
        if base.exists():
            hits += sorted(
                p for p in base.rglob("*")
                if p.suffix.lower() in (".png", ".jpg", ".jpeg")
            )
    out: List[Dict[str, Any]] = []
    for p in hits[:limit]:
        p_str = str(p).replace("\\", "/")
        if "/data/" in p_str:
            href = "/data/" + p_str.split("/data/", 1)[1]
        elif "/exports/" in p_str:
            href = "/exports/" + p_str.split("/exports/", 1)[1]
        else:
            continue
        out.append({"path": p_str, "href": href, "name": p.name})
    return out

@app.post("/api/export/{kind}", dependencies=[Depends(auth_guard)])
def api_export(kind: str, body: ExportReq):
    ensure_db(DB_PATH)
    date = body.date or _today()
    jid = enqueue_export_job(DB_PATH, kind=kind, date=date, payload=(body.args or {}))
    return {"queued": jid, "kind": kind, "date": date}

@app.post("/api/export_selected/{kind}", dependencies=[Depends(auth_guard)])
def api_export_selected(kind: str, body: SelectedReq):
    ensure_db(DB_PATH)
    date = body.date or _today()
    files = [str(_href_to_path(h)) for h in (body.files or []) if h]
    payload: Dict[str, Any] = {"files": files}
    if body.args:
        payload.update(body.args)
    jid = enqueue_export_job(DB_PATH, kind=kind, date=date, payload=payload)
    return {"queued": jid, "kind": kind, "date": date, "count": len(files)}

@app.post("/api/queue/all", dependencies=[Depends(auth_guard)])
def api_queue_all(body: DateReq):
    ensure_db(DB_PATH)
    date = body.date or _today()
    ids = [enqueue_export_job(DB_PATH, kind=k, date=date, payload={})
           for k in ("pdf", "csv", "pptx", "gif", "mp4", "zip")]
    return {"ok": True, "date": date, "queued": ids}

@app.post("/api/jobs/retry_failed", dependencies=[Depends(auth_guard)])
def api_retry_failed(body: DateReq):
    ensure_db(DB_PATH)
    date = body.date
    failed = list_jobs(DB_PATH, limit=1000, status="failed", date=date)
    ids: List[int] = []
    for j in failed:
        kind = j["kind"].split(":", 1)[1]
        ids.append(enqueue_export_job(DB_PATH, kind=kind, date=j["date"], payload={}))
    return {"ok": True, "requeued": ids}

@app.post("/api/worker/tick", dependencies=[Depends(auth_guard)])
def api_worker_tick():
    ensure_db(DB_PATH)
    code = run_worker_once(DB_PATH, EXPORTS)
    return {"ok": (code == 0)}

@app.post("/api/worker/drain", dependencies=[Depends(auth_guard)])
def api_worker_drain(max_loops: int = 50):
    ensure_db(DB_PATH)
    iters = 0
    while iters < max_loops:
        q = list_jobs(DB_PATH, limit=1, status="queued")
        r = list_jobs(DB_PATH, limit=1, status="running")
        if not q and not r:
            break
        run_worker_once(DB_PATH, EXPORTS)
        iters += 1
    remaining = len(list_jobs(DB_PATH, limit=1000, status="queued"))
    return {"ok": True, "iterations": iters, "remaining": remaining}

@app.post("/api/sample", dependencies=[Depends(auth_guard)])
def api_sample(body: DateReq):
    ensure_db(DB_PATH)
    date = body.date or _today()
    artdir = ROOT / "data" / "runs" / date / "art"
    artdir.mkdir(parents=True, exist_ok=True)
    img = artdir / "sample.png"
    try:
        from PIL import Image, ImageDraw  # type: ignore
        im = Image.new("RGB", (1280, 720), (20, 20, 20))
        d = ImageDraw.Draw(im)
        d.text((40, 40), f"AISatyagrah sample — {date}", fill=(240, 240, 240))
        im.save(img)
    except Exception:
        img.write_bytes(b"")
    ids = [enqueue_export_job(DB_PATH, kind=k, date=date, payload={})
           for k in ("pdf", "csv", "pptx", "gif", "mp4", "zip")]
    return {"ok": True, "date": date, "image": str(img), "queued": ids}

@app.post("/api/results/zipday", dependencies=[Depends(auth_guard)])
def api_zipday(body: DateReq):
    ensure_db(DB_PATH)
    date = body.date or _today()
    rows = list_results(DB_PATH, limit=10000, date=date)
    outdir = EXPORTS / date
    outdir.mkdir(parents=True, exist_ok=True)
    zpath = outdir / "results_bundle.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for r in rows:
            p = Path(r["path"])
            if p.exists():
                z.write(p, arcname=p.name)
    href = "/exports/" + str(zpath).replace("\\", "/").split("/exports/", 1)[1]
    return {"ok": True, "path": str(zpath), "href": href}

# ---------------------------------------------------------
# ui
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return """<!doctype html>
<html lang='en'><meta charset='utf-8'/>
<title>AISatyagrah — Export Queue</title>
<style>
:root{color-scheme:dark light}
body{font:14px/1.45 system-ui,Segoe UI,Roboto,Arial;margin:24px;background:#111;color:#eee}
h1{font-size:20px;margin:0 0 12px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
input,button,select{padding:8px 10px;border-radius:10px;border:1px solid #333;background:#222;color:#eee}
button{cursor:pointer}
table{border-collapse:collapse;width:100%;margin-top:12px}
th,td{border-bottom:1px solid #333;padding:8px;text-align:left;font-variant-numeric:tabular-nums}
a{color:#7ecbff}
#toasts{position:fixed;right:16px;bottom:16px;display:flex;flex-direction:column;gap:8px}
.toast{background:#222;border:1px solid #333;border-radius:10px;padding:10px 12px;box-shadow:0 4px 12px rgb(0 0 0 / .4)}
.toast.ok{border-color:#2e7d32}
.toast.err{border-color:#c62828}
.section{margin-top:18px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
.badge{background:#222;border:1px solid #333;border-radius:999px;padding:4px 8px}
#gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin-top:12px}
.thumb{position:relative;border-radius:12px;border:1px solid #333;overflow:hidden;background:#000}
.thumb img{width:100%;height:120px;object-fit:cover;display:block}
.sel{position:absolute;top:6px;left:6px;background:#0008;border:1px solid #fff8;color:#fff;padding:2px 6px;border-radius:999px;font-size:12px}
.thumb.selected{outline:3px solid #59f}
#selPane{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px;margin-top:10px}
.selcard{position:relative;border:1px dashed #444;border-radius:10px;overflow:hidden;background:#000}
.selcard img{width:100%;height:90px;object-fit:cover;display:block}
.selidx{position:absolute;top:4px;left:4px;background:#0008;color:#fff;border:1px solid #fff4;border-radius:999px;font-size:11px;padding:1px 6px}
</style>
<body>
<h1>AISatyagrah — Export Queue</h1>
<div class="row">
  <label>Date <input id="date" type="date"></label>
  <button onclick="queue('pdf')">Queue PDF</button>
  <button onclick="queue('csv')">Queue CSV</button>
  <button onclick="queue('pptx')">Queue PPTX</button>
  <button onclick="queue('gif')">Queue GIF</button>
  <button onclick="queue('mp4')">Queue MP4</button>
  <button onclick="queue('zip')">Queue ZIP</button>
  <button onclick="queueAll()">Queue All</button>
  <button onclick="retryFailed()">Retry Failed</button>
  <button onclick="tick()">Worker Tick</button>
  <button onclick="drain()">Drain Queue</button>
  <button onclick="sample()">Make Sample Run</button>
  <label><input id="auto" type="checkbox" onchange="toggleAuto()"> Auto-tick</label>
  <button onclick="refresh()">Refresh Jobs</button>
  <button onclick="zipDay()">Download Results ZIP</button>
  <button onclick="setToken()">Set Token</button>
</div>

<div class="section">
  <h3>Jobs</h3>
  <table id="jobs"><thead><tr>
    <th>id</th><th>date</th><th>kind</th><th>status</th><th>created</th><th>finished</th><th>error</th>
  </tr></thead><tbody></tbody></table>
</div>

<div class="section">
  <h3>Results (today)</h3>
  <table id="results"><thead><tr>
    <th>id</th><th>job_id</th><th>kind</th><th>file</th><th>size</th><th>created</th>
  </tr></thead><tbody></tbody></table>
</div>

<div class="section">
  <h3>Gallery (today)</h3>
  <div class="toolbar">
    <span class="badge" id="selCount">0 selected</span>
    <button onclick="selectAll()">Select All</button>
    <button onclick="clearSel()">Clear</button>
    <span>| Export selected →</span>
    <label class="badge">MP4 fps <input id="mp4fps" type="number" min="0.2" step="0.2" value="1" style="width:70px"></label>
    <label class="badge">GIF ms/frame <input id="gifdur" type="number" min="20" step="10" value="100" style="width:90px"></label>
    <button onclick="queueSel('pdf')">PDF</button>
    <button onclick="queueSel('pptx')">PPTX</button>
    <button onclick="queueSel('gif')">GIF</button>
    <button onclick="queueSel('mp4')">MP4</button>
    <button onclick="queueSel('csv')">CSV</button>
    <button onclick="queueSel('zip')">ZIP</button>
  </div>
  <div id="gallery"></div>
</div>

<div class="section">
  <h3>Selection (drag to reorder)</h3>
  <div id="selPane"></div>
</div>

<div id="toasts"></div>

<script>
// attach x-auth automatically if saved
const RAW_FETCH = window.fetch;
window.fetch = (url, opts={})=>{
  const t = localStorage.getItem('xauth');
  const add = t ? {'x-auth': t} : {};
  opts.headers = Object.assign({}, opts.headers||{}, add);
  return RAW_FETCH(url, opts);
};
function setToken(){
  const cur = localStorage.getItem('xauth') || '';
  const t = prompt('Enter API token (x-auth). Leave blank to clear:', cur);
  if (t === null) return;
  if (t.trim()) localStorage.setItem('xauth', t.trim());
  else localStorage.removeItem('xauth');
  toast('Auth token saved');
}

const API = location.origin;
let autoTimer = null;

// selection state
const selected = new Set();
let selOrder = [];

// toast
function toast(msg, ok=true){
  const wrap = document.getElementById('toasts');
  const div = document.createElement('div');
  div.className = 'toast ' + (ok ? 'ok' : 'err');
  div.textContent = msg;
  wrap.appendChild(div);
  setTimeout(()=>div.remove(), 2200);
}
function setSelCount(){ document.getElementById('selCount').textContent = `${selOrder.length} selected`; }

// helpers
function todayStr(){ const d = new Date(), z = d.getTimezoneOffset()*60000; return (new Date(Date.now()-z)).toISOString().slice(0,10); }
function init(){ const di = document.getElementById('date'); if(!di.value) di.value = todayStr(); refresh(); }

async function queue(kind){
  const date = document.getElementById('date').value || todayStr();
  await fetch(`${API}/api/export/${kind}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({date})});
  toast(`Queued ${kind.toUpperCase()} for ${date}`); refresh();
}

async function queueSel(kind){
  if(!selOrder.length){ toast("Pick some images first", false); return; }
  const date = document.getElementById('date').value || todayStr();
  const args = {};
  if (kind === 'mp4')  { const v = parseFloat(document.getElementById('mp4fps').value); if (v>0) args.fps = v; }
  if (kind === 'gif')  { const v = parseInt(document.getElementById('gifdur').value);  if (v>0) args.duration_ms = v; }
  await fetch(`${API}/api/export_selected/${kind}`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({date, files: selOrder.slice(), args})
  });
  toast(`Queued ${kind.toUpperCase()} for ${selOrder.length} images`);
  refresh();
}

async function queueAll(){ const date = document.getElementById('date').value || todayStr(); await fetch(`${API}/api/queue/all`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({date})}); toast(`Queued ALL for ${date}`); refresh(); }
async function retryFailed(){ const date = document.getElementById('date').value || todayStr(); await fetch(`${API}/api/jobs/retry_failed`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({date})}); toast(`Requeued failed jobs`); refresh(); }
async function tick(){ const ok = (await (await fetch(`${API}/api/worker/tick`, {method:'POST'})).json()).ok; toast(ok?'Worker tick ok':'Worker tick error', ok); refresh(); }
async function drain(){ const r = await (await fetch(`${API}/api/worker/drain`, {method:'POST'})).json(); toast(`Drained: ${r.iterations} ticks, remaining ${r.remaining}`); refresh(); }
async function sample(){ const date = document.getElementById('date').value || todayStr(); await fetch(`${API}/api/sample`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({date})}); toast(`Sample created + all exports queued for ${date}`); await drain(); }
function toggleAuto(){ const on = document.getElementById('auto').checked; if(on){ autoTimer = setInterval(tick, 1200);} else { clearInterval(autoTimer); autoTimer=null; } }

function selectAll(){
  selOrder = [];
  document.querySelectorAll('#gallery .thumb').forEach(el=>{
    selected.add(el.dataset.href);
    selOrder.push(el.dataset.href);
    el.classList.add('selected');
  });
  setSelCount(); renderSelection();
}
function clearSel(){
  selected.clear(); selOrder = [];
  document.querySelectorAll('#gallery .thumb').forEach(el=>el.classList.remove('selected'));
  setSelCount(); renderSelection();
}

// selection pane
function renderSelection(){
  const pane = document.getElementById('selPane');
  pane.innerHTML = '';
  selOrder.forEach((href, idx)=>{
    const card = document.createElement('div');
    card.className = 'selcard'; card.draggable = true; card.dataset.idx = idx;
    card.addEventListener('dragstart', (e)=>{ e.dataTransfer.setData('text/plain', idx); });
    card.addEventListener('dragover', (e)=> e.preventDefault());
    card.addEventListener('drop', (e)=>{
      e.preventDefault();
      const src = parseInt(e.dataTransfer.getData('text/plain'));
      const dst = parseInt(card.dataset.idx);
      if (isNaN(src) || isNaN(dst) || src===dst) return;
      const item = selOrder.splice(src,1)[0];
      selOrder.splice(dst,0,item);
      renderSelection(); setSelCount();
    });
    const img = document.createElement('img'); img.src = href; img.alt = `#${idx+1}`;
    const badge = document.createElement('div'); badge.className='selidx'; badge.textContent = idx+1;
    card.appendChild(img); card.appendChild(badge);
    pane.appendChild(card);
  });
}

// refresh
async function refresh(){
  const date = document.getElementById('date').value || todayStr();

  const jobs = await (await fetch(`${API}/api/jobs?limit=50&date=${date}`)).json();
  const tb = document.querySelector('#jobs tbody'); tb.innerHTML='';
  for (const r of jobs){
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r.id}</td><td>${r.date||''}</td><td>${r.kind||''}</td><td>${r.status||''}</td>
      <td>${(r.created_at||'').slice(0,19)}</td><td>${(r.finished_at||'').slice(0,19)}</td><td>${r.error? 'err':''}</td>`;
    tb.appendChild(tr);
  }

  const res = await (await fetch(`${API}/api/results?date=${date}&limit=200`)).json();
  const rb = document.querySelector('#results tbody'); rb.innerHTML='';
  for (const r of res){
    const name = (r.href || r.path || '').split('/').pop();
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r.id}</td><td>${r.job_id}</td><td>${r.kind}</td>
      <td><a href="${r.href || '#'}" target="_blank">${name}</a></td>
      <td>${(r.size||0).toLocaleString()}</td>
      <td>${(r.created_at||'').slice(0,19)}</td>`;
    rb.appendChild(tr);
  }

  const imgs = await (await fetch(`${API}/api/images?date=${date}&limit=400`)).json();
  const g = document.getElementById('gallery'); g.innerHTML = '';
  const setHrefs = new Set(imgs.map(it=>it.href));
  selOrder = selOrder.filter(h=>setHrefs.has(h));
  selected.forEach(h=>{ if(!setHrefs.has(h)) selected.delete(h); });
  for (const it of imgs){
    const div = document.createElement('div'); div.className='thumb'; div.dataset.href = it.href;
    const img = document.createElement('img'); img.src = it.href; img.alt = it.name;
    const tag = document.createElement('div'); tag.className='sel'; tag.textContent='pick';
    div.appendChild(img); div.appendChild(tag);
    if (selected.has(it.href)) div.classList.add('selected');
    div.onclick = ()=>{
      if (selected.has(it.href)) {
        selected.delete(it.href);
        div.classList.remove('selected');
        selOrder = selOrder.filter(h=>h!==it.href);
      } else {
        selected.add(it.href);
        div.classList.add('selected');
        selOrder.push(it.href);
      }
      setSelCount(); renderSelection();
    };
    g.appendChild(div);
  }
  setSelCount(); renderSelection();
}

// bundle download
async function zipDay(){
  const date = document.getElementById('date').value || todayStr();
  const r = await (await fetch(`${API}/api/results/zipday`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({date})})).json();
  if (r.ok && r.href){ toast('Bundled results → downloading…'); window.open(r.href, '_blank'); } else { toast('Bundle failed', false); }
}

init();
</script>
</body></html>"""

# -*- coding: utf-8 -*-
import argparse, base64, json, time, sqlite3, threading, os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.server import BaseHTTPRequestHandler, HTTPServer
from .jobfmt import read_job_zip, write_result_zip

# ---------- Config & Status (shared across threads) ----------
CONFIG = {
    "sd_host": "http://127.0.0.1:7860",
    "max_per_day": 5,
    "share_percent": 50,          # 0..100; 100 = full speed, 50 = half-duty (sleep ~= work time)
    "paused": False,
    "inactivity_minutes": 120,    # nudge after this much idle time (no jobs processed)
}
CONFIG_MTIME = 0.0
STATUS = {
    "uptime_sec": 0,
    "processed_today": 0,
    "queue_len": 0,
    "last_job_id": "",
    "last_ok": None,
    "last_error": "",
    "share_percent": 50,
    "paused": False,
    "needs_attention": False,
    "since_last_job_sec": 0,
    "started_at": int(time.time()),
}

def _read_config(path: Path):
    global CONFIG, CONFIG_MTIME
    try:
        if path.exists():
            mt = path.stat().st_mtime
            if mt != CONFIG_MTIME:
                CONFIG.update(json.loads(path.read_text(encoding="utf-8")))
                CONFIG_MTIME = mt
    except Exception:
        pass

def _write_config(path: Path):
    global CONFIG
    try:
        path.write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")
    except Exception:
        pass

def _write_status(path: Path):
    try:
        path.write_text(json.dumps(STATUS, indent=2), encoding="utf-8")
    except Exception:
        pass

# ---------- Minimal usage DB ----------
def _db(path: Path):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY, count INTEGER NOT NULL)")
    return con

def _quota_ok(dbp: Path, limit: int) -> bool:
    if limit <= 0: return True
    day = time.strftime("%Y-%m-%d")
    con = _db(dbp); cur = con.cursor()
    row = cur.execute("SELECT count FROM usage WHERE day=?", (day,)).fetchone()
    c = row[0] if row else 0
    ok = c < limit
    if ok:
        cur.execute("INSERT INTO usage(day,count) VALUES(?,?) ON CONFLICT(day) DO UPDATE SET count=count+1", (day, c+1))
        con.commit()
    con.close()
    STATUS["processed_today"] = c + (1 if ok else 0)
    return ok

# ---------- SD call ----------
def _sd_txt2img(host: str, prompt: str, seed: int, steps: int, width: int, height: int, count: int):
    url = host.rstrip("/") + "/sdapi/v1/txt2img"
    body = json.dumps({"prompt": prompt, "seed": seed, "steps": steps, "width": width, "height": height, "n_iter": 1, "batch_size": count}).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type":"application/json","User-Agent":"Satyagrah-PeerAgent"})
    t0 = time.time()
    with urlopen(req, timeout=600) as r:
        j = json.loads(r.read().decode("utf-8"))
    dur = time.time() - t0
    imgs = []
    for i, b64 in enumerate(j.get("images", [])):
        imgs.append((f"img_{i+1}.png", base64.b64decode(b64)))
    return imgs, dur

# ---------- Panel (stdlib HTTP) ----------
class PanelHandler(BaseHTTPRequestHandler):
    def _send(self, code=200, ct="text/html; charset=utf-8", body=""):
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        root = self.server.root  # type: ignore
        if self.path.startswith("/status.json"):
            self._send(200, "application/json; charset=utf-8", STATUS)
            return
        if self.path.startswith("/"):
            self._send(200, "text/html; charset=utf-8", """<!doctype html>
<meta charset="utf-8">
<title>Peer Agent</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,sans-serif;margin:18px}}
.card{{max-width:880px;padding:16px;border:1px solid #e5e5e5;border-radius:12px;box-shadow:0 2px 12px #0001}}
.row{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
h2{{margin:0 0 8px 0}}
label span{{display:inline-block;min-width:160px}}
button,input[type=range]{{cursor:pointer}}
.badge{{display:inline-block;padding:2px 8px;border-radius:999px;background:#f3f3f3;border:1px solid #e3e3e3}}
.warn{{color:#c00}}
</style>
<div class="card">
  <h2>Peer GPU Agent</h2>
  <div class="row">
    <span class="badge">Queue: <b id="q">-</b></span>
    <span class="badge">Processed today: <b id="pt">-</b></span>
    <span class="badge">Share: <b id="sp">-</b>%</span>
    <span class="badge">Paused: <b id="pa">-</b></span>
    <span class="badge">Last job: <b id="lj">-</b></span>
  </div>
  <hr>
  <div>
    <label><span>GPU Share</span>
      <input id="share" type="range" min="0" max="100" step="5" value="50" oninput="S(this.value)">
      <b id="sv">50%</b></label>
  </div>
  <div>
    <label><span>Daily Limit</span>
      <input id="limit" type="number" min="0" value="5" style="width:6rem"> (0 = unlimited)
    </label>
  </div>
  <div>
    <label><span>Inactivity Nudge (min)</span>
      <input id="idle" type="number" min="15" value="120" style="width:6rem">
    </label>
  </div>
  <div class="row" style="margin-top:8px">
    <button onclick="setcfg()">Save settings</button>
    <button onclick="pause()">Pause</button>
    <button onclick="resume()">Resume</button>
    <button onclick="quitAgent()" style="border-color:#d33;color:#d33">Quit</button>
  </div>
  <p id="msg" class="warn"></p>
</div>
<script>
let ST={};
function S(v){document.getElementById('sv').textContent=v+'%'}
async function load(){
  const r=await fetch('/status.json'); ST=await r.json();
  document.getElementById('q').textContent=ST.queue_len;
  document.getElementById('pt').textContent=ST.processed_today;
  document.getElementById('sp').textContent=ST.share_percent;
  document.getElementById('pa').textContent=ST.paused?'yes':'no';
  document.getElementById('lj').textContent=ST.last_job_id||'-';
  document.getElementById('share').value=ST.share_percent; S(ST.share_percent);
  document.getElementById('limit').value=ST.max_per_day ?? 5;
  document.getElementById('idle').value=ST.inactivity_minutes ?? 120;
  if(ST.needs_attention){ document.getElementById('msg').textContent='No activity for a while. Pause or keep running?'; }
  setTimeout(load, 2000);
}
async function post(url, obj){ return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj||{})}); }
async function setcfg(){
  const body={share_percent:+share.value,max_per_day:+limit.value,inactivity_minutes:+idle.value};
  await post('/set', body); document.getElementById('msg').textContent='Saved.';
}
async function pause(){ await post('/pause',{}); }
async function resume(){ await post('/resume',{}); }
async function quitAgent(){ await post('/quit',{}); }
load();
</script>""")
            return
        self._send(404, body="Not found")

    def do_POST(self):
        root = self.server.root  # type: ignore
        n = int(self.headers.get("Content-Length","0") or "0")
        body = json.loads(self.rfile.read(n).decode("utf-8") or "{}") if n>0 else {}
        cfg_path = root / "agent_config.json"
        if self.path == "/set":
            changed = False
            for k in ("share_percent","max_per_day","inactivity_minutes"):
                if k in body:
                    CONFIG[k] = int(body[k])
                    changed = True
            if changed: _write_config(cfg_path)
            self._send(200, "application/json; charset=utf-8", {"ok": True})
            return
        if self.path == "/pause":
            CONFIG["paused"] = True; _write_config(cfg_path)
            self._send(200, "application/json; charset=utf-8", {"ok": True}); return
        if self.path == "/resume":
            CONFIG["paused"] = False; _write_config(cfg_path)
            self._send(200, "application/json; charset=utf-8", {"ok": True}); return
        if self.path == "/quit":
            (root / "quit.flag").write_text("1", encoding="utf-8")
            self._send(200, "application/json; charset=utf-8", {"ok": True}); return
        self._send(404, body="Not found")

def _start_panel(port: int, root: Path):
    srv = HTTPServer(("127.0.0.1", port), PanelHandler)
    srv.root = root  # type: ignore
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv

# ---------- Agent core ----------
def process_one(in_zip: Path, out_dir: Path, sd_host: str, db_path: Path):
    job = read_job_zip(in_zip)  # verifies signature & expiry
    if not _quota_ok(db_path, CONFIG.get("max_per_day", 5)):
        raise RuntimeError("Quota exceeded for today")
    images = []
    errors = []
    total_dur = 0.0
    for t in job.get("tasks", []):
        if t.get("type") != "txt2img":
            errors.append(f"Unsupported task: {t.get('type')}")
            continue
        try:
            imgs, dur = _sd_txt2img(sd_host, t["prompt"], int(t["seed"]), int(t["steps"]), int(t["width"]), int(t["height"]), int(t["count"]))
            images.extend(imgs)
            total_dur += float(dur)
        except Exception as e:
            errors.append(str(e))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / f"result_{job['id']}.zip"
    write_result_zip(job, images, out_zip, ok=(len(errors)==0), errors=errors)
    return out_zip, job["id"], (len(errors)==0), "; ".join(errors), total_dur

def main():
    ap = argparse.ArgumentParser(description="Peer GPU Agent")
    ap.add_argument("mode", choices=["once","run"], help="'once' processes a single zip; 'run' watches a folder")
    ap.add_argument("--inbox", default="jobs/inbox")
    ap.add_argument("--outbox", default="jobs/outbox_results")
    ap.add_argument("--sd-host", default=None)
    ap.add_argument("--state", default=None)
    ap.add_argument("--max-per-day", type=int, default=None)
    ap.add_argument("--interval", type=int, default=3, help="watch interval (seconds)")
    ap.add_argument("--panel-port", type=int, default=8090, help="0=disabled, otherwise serve control UI on this port")
    ap.add_argument("--config", default=None, help="path to agent_config.json")
    args = ap.parse_args()

    inbox = Path(args.inbox); outbox = Path(args.outbox)
    inbox.mkdir(parents=True, exist_ok=True); outbox.mkdir(parents=True, exist_ok=True)
    root = inbox.parent  # pack root (contains inbox/out)
    cfg_path = Path(args.config) if args.config else (root / "agent_config.json")
    st_path = root / "status.json"
    dbp = Path(args.state) if args.state else (root / "agent_state.db")

    # load/merge settings
    _read_config(cfg_path)
    if args.sd_host:      CONFIG["sd_host"] = args.sd_host
    if args.max_per_day is not None: CONFIG["max_per_day"] = args.max_per_day
    STATUS["share_percent"] = CONFIG["share_percent"]
    STATUS["paused"] = CONFIG["paused"]
    STATUS["inactivity_minutes"] = CONFIG["inactivity_minutes"]
    STATUS["max_per_day"] = CONFIG["max_per_day"]

    # start panel
    if args.panel_port and args.panel_port > 0:
        _start_panel(args.panel_port, root)
        print(f"[panel] http://127.0.0.1:{args.panel_port}")

    # modes
    if args.mode == "once":
        zips = sorted(inbox.glob("job_*.zip"))
        if not zips: raise SystemExit(f"No jobs found in {inbox}")
        out, jid, ok, err, dur = process_one(zips[0], outbox, CONFIG["sd_host"], dbp)
        print("Wrote:", out)
        return

    # run watcher loop
    seen = set()
    last_job_time = time.time()
    t_start = time.time()
    while True:
        # config hot-reload
        _read_config(cfg_path)
        STATUS["share_percent"] = CONFIG["share_percent"]
        STATUS["paused"] = CONFIG["paused"]
        STATUS["inactivity_minutes"] = CONFIG["inactivity_minutes"]
        STATUS["max_per_day"] = CONFIG["max_per_day"]
        STATUS["uptime_sec"] = int(time.time() - t_start)
        STATUS["since_last_job_sec"] = int(time.time() - last_job_time)
        STATUS["needs_attention"] = (not CONFIG["paused"]) and (STATUS["since_last_job_sec"] >= CONFIG["inactivity_minutes"] * 60)

        # graceful quit
        if (root / "quit.flag").exists():
            print("[agent] Quit flag detected. Exiting.")
            try: (root / "quit.flag").unlink()
            except Exception: pass
            break

        # queue
        pending = [z for z in sorted(inbox.glob("job_*.zip")) if z.name not in seen]
        STATUS["queue_len"] = len(pending)
        _write_status(st_path)

        if CONFIG["paused"] or not pending:
            time.sleep(args.interval)
            continue

        z = pending[0]
        try:
            out, jid, ok, err, dur = process_one(z, outbox, CONFIG["sd_host"], dbp)
            print("OK:" if ok else "ERR:", z.name, "â†’", out.name if ok else err)
            STATUS["last_job_id"] = jid
            STATUS["last_ok"] = ok
            STATUS["last_error"] = "" if ok else err
            last_job_time = time.time()
        except Exception as e:
            print("ERR:", z.name, e)
            STATUS["last_job_id"] = z.stem.replace("job_","")
            STATUS["last_ok"] = False
            STATUS["last_error"] = str(e)

        # duty-cycle sleep based on share_percent
        share = max(0, min(100, int(CONFIG.get("share_percent", 100))))
        if share <= 0:
            # sleep long if 0%
            time.sleep(max(5, args.interval))
        elif share < 100:
            # simple duty-cycle: sleep ~= work_time * (100-share)/share
            work = max(0.1, dur if 'dur' in locals() else 1.0)
            sleep_extra = work * (100.0 - share) / max(1.0, share)
            time.sleep(min(60.0, sleep_extra))

        seen.add(z.name)
        # small idle tick
        time.sleep(max(0.2, args.interval * 0.2))

if __name__ == "__main__":
    main()


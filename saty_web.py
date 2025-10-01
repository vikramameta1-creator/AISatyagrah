#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Satyagrah Local Web UI â€” FastAPI or Stdlib Fallback (+ Offline Mode)

- Tries FastAPI + Uvicorn first
- Falls back to stdlib HTTP server if FastAPI not available
- Can write an offline HTML page if binding a socket is not permitted

Buttons in the UI call CLI commands like:  python -m satyagrah <args>
"""

from __future__ import annotations

import argparse
import asyncio
import errno
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import AsyncIterator, List, Optional, Tuple

APP_TITLE = "Satyagrah â€“ Local Web UI"
ROOT = Path(os.environ.get("SATY_ROOT") or os.getcwd())


# ---------------------------- helpers ----------------------------

def which_python() -> str:
    return sys.executable or "python"


async def stream_process_async(args: List[str]) -> AsyncIterator[bytes]:
    """Spawn `python -m satyagrah <args>` and stream combined stdout/stderr as bytes (async)."""
    py = which_python()
    cmd = [py, "-m", "satyagrah", *args]
    banner = "$ " + " ".join(cmd) + "\n"
    yield banner.encode("utf-8")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            limit=1 << 20,
        )
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line
        rc = await proc.wait()
        yield f"\n[exit {rc}]\n".encode("utf-8")
    except FileNotFoundError:
        yield b"ERROR: Could not spawn process. Is your venv active and satyagrah importable?\n"
    except Exception as e:
        yield f"ERROR: {e}\n".encode("utf-8")


def run_process_blocking(args: List[str]) -> Tuple[int, str]:
    """Run the CLI synchronously; return (rc, combined_output). Used by the fallback server."""
    import subprocess
    py = which_python()
    cmd = [py, "-m", "satyagrah", *args]
    try:
        p = subprocess.Popen(
            cmd, cwd=str(ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        assert p.stdout is not None
        out = ["$ " + " ".join(cmd) + "\n"]
        for line in p.stdout:
            out.append(line)
        rc = p.wait()
        out.append(f"\n[exit {rc}]\n")
        return rc, "".join(out)
    except FileNotFoundError:
        return 127, "$ " + " ".join(cmd) + "\nERROR: Could not spawn process. Is venv active?\n"
    except Exception as e:
        return 1, f"$ {' '.join(cmd)}\nERROR: {e}\n"


# ---------------------------- HTML builders (no f-strings) ----------------------------

def _home_html(title: str) -> str:
    html = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>__TITLE__</title>
<style>
  :root { --bg:#0b0e14; --fg:#ebedf0; --muted:#a0a8b0; --card:#121622; --accent:#6ea8fe; }
  html,body { margin:0; height:100%; background:var(--bg); color:var(--fg); font-family: ui-sans-serif,system-ui,Segoe UI,Roboto,Arial; }
  .wrap { display:flex; flex-direction:column; height:100%; }
  header { padding:12px 16px; background:var(--card); border-bottom:1px solid #222738; }
  header h1 { margin:0; font-size:18px; letter-spacing:.3px; }
  main { display:grid; grid-template-columns: 340px 1fr; gap:12px; padding:12px; height:100%; box-sizing:border-box; }
  .panel { background:var(--card); border:1px solid #222738; border-radius:12px; padding:12px; }
  .grp { margin-bottom:14px; }
  .grp h3 { margin:0 0 8px 0; font-size:14px; color:var(--muted); font-weight:600; }
  label { display:inline-block; width:90px; color:var(--muted); font-size:12px; }
  input,select { background:#0f1422; color:var(--fg); border:1px solid #2a3147; border-radius:8px; padding:6px 8px; margin:2px 0; font-size:13px; }
  .btn { background:#11182a; color:var(--fg); border:1px solid #2a3147; border-radius:10px; padding:8px 10px; margin:4px 4px 4px 0; font-size:13px; cursor:pointer; }
  .btn.primary { background:#1a2540; border-color:#38518a; }
  .btn:disabled { opacity:.6; cursor:not-allowed; }
  #log { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:#0a0d16; border:1px solid #222738; height:calc(100vh - 170px); border-radius:12px; padding:10px; overflow:auto; white-space:pre-wrap; }
  .row { display:flex; align-items:center; gap:8px; margin:4px 0; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>__TITLE__</h1>
  </header>
  <main>
    <section class="panel">
      <div class="grp"><h3>Parameters</h3>
        <div class="row"><label>Date</label><input id="date" value="latest"/></div>
        <div class="row"><label>Idx</label><input id="idx" type="number" value="1"/></div>
        <div class="row"><label>Top</label><input id="top" type="number" value="3"/></div>
        <div class="row"><label>Indices</label><input id="indices" placeholder="e.g. 1,3,5"/></div>
        <div class="row"><label>ID</label><input id="topic_id" value="auto"/></div>
        <div class="row"><label>Seed</label><input id="seed" type="number" value="12345"/></div>
        <div class="row"><label>Lang</label><input id="lang" value="en,hi"/></div>
        <div class="row"><label>Aspect</label>
          <select id="aspect">
            <option value="all" selected>all</option>
            <option value="4x5">4x5</option>
            <option value="1x1">1x1</option>
            <option value="9x16">9x16</option>
          </select>
        </div>
        <div class="row"><label>Image</label>
          <select id="image">
            <option value="">(auto)</option>
            <option value="4x5">4x5</option>
            <option value="1x1">1x1</option>
            <option value="9x16">9x16</option>
          </select>
        </div>
        <div class="row"><label>Platform</label>
          <select id="platform">
            <option value="">(none)</option>
            <option>instagram</option>
            <option>instagram-stories</option>
            <option>shorts</option>
            <option>x</option>
            <option>twitter</option>
            <option>linkedin</option>
            <option>facebook</option>
          </select>
        </div>
        <div class="row"><label></label>
          <label><input type="checkbox" id="skip_image"/> skip image</label>
          <label><input type="checkbox" id="package"/> package</label>
          <label><input type="checkbox" id="saveas" checked/> saveas</label>
          <label><input type="checkbox" id="csv" checked/> csv</label>
          <label><input type="checkbox" id="open"/> open</label>
        </div>
      </div>

      <div class="grp"><h3>Pipeline</h3>
        <button class="btn" onclick="run(['doctor','--strict'])">Doctor</button>
        <button class="btn" onclick="run(['research','--date', val('date')])">Research</button>
        <button class="btn" onclick="run(['triage','--date', val('date')])">Triage</button>
        <button class="btn" onclick="quick()">Quick</button>
        <button class="btn" onclick="batch()">Batch</button>
        <button class="btn" onclick="layout()">Layout</button>
        <button class="btn" onclick="run(['thumbs','--date', val('date')])">Thumbs</button>
        <button class="btn" onclick="run(['socialcsv','--date', val('date')])">SocialCSV</button>
        <button class="btn" onclick="run(['seeds','--date', val('date')])">Seeds</button>
        <button class="btn" onclick="busy=false; append('\n[info] Busy reset.\n');">Reset busy</button>
      </div>

      <div class="grp"><h3>Publish</h3>
        <button class="btn primary" onclick="publishNow()">Publish</button>
        <button class="btn" onclick="run(['open','--what','exports','--date', val('date')])">Open exports</button>
        <button class="btn" onclick="run(['open','--what','runs','--date', val('date')])">Open runs</button>
        <button class="btn" onclick="zipOutbox()">Zip outbox</button>
        <button class="btn" onclick="openOutbox()">Open outbox (resolved)</button>
      </div>

      <div class="grp"><h3>Feeds</h3>
        <button class="btn" onclick="run(['feeds','list'])">List</button>
        <div class="row"><label>New feed</label><input id="feedurl" placeholder="https://.../feed" style="width:200px"/> <button class="btn" onclick="addFeed()">Add</button></div>
        <div class="row"><label>Remove #</label><input id="rmindex" type="number" min="1" style="width:100px"/> <button class="btn" onclick="removeFeed()">Remove</button></div>
        <button class="btn" onclick="run(['feeds','reset'])">Reset (backup/defaults)</button>
      </div>
    </section>

    <section class="panel">
      <div class="grp"><h3>Output</h3>
        <pre id="log"></pre>
      </div>
    </section>
  </main>
</div>
<script>
  let busy = false;
  function setBusy(v){ busy = v; }
  const logEl = document.getElementById('log');
  function val(id){ return document.getElementById(id).value; }
  function checked(id){ return document.getElementById(id).checked; }
  function append(txt){ logEl.textContent += txt; logEl.scrollTop = logEl.scrollHeight; }

  async function run(args){
    if(busy){ append("\n[busy] Wait for current task to finish...\n"); return; }
    setBusy(true);
    try{
      append("\n$ python -m satyagrah " + args.join(' ') + "\n");
      const res = await fetch('/api/run', {
        method: 'POST',
        headers:{'content-type':'application/json'},
        body: JSON.stringify({args})
      });

      // Support both streaming (FastAPI) and full-buffered (fallback server)
      if(!res.body || !res.body.getReader){
        append(await res.text());
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while(true){
        const {done, value} = await reader.read();
        if(done) break;
        append(decoder.decode(value));
      }
    } catch(e){
      append("\n[error] " + (e && e.message ? e.message : String(e)) + "\n");
    } finally{
      setBusy(false);
    }
  }

  function quick(){
    const a = ['quick','--date', val('date'),'--idx', String(val('idx')),'--seed', String(val('seed'))];
    const lang = val('lang'); if(lang) a.push('--lang', lang);
    const aspect = val('aspect'); if(aspect && aspect !== 'all') a.push('--aspect', aspect);
    if(checked('skip_image')) a.push('--skip_image');
    if(checked('package')) a.push('--package');
    if(checked('saveas')) a.push('--saveas');
    const tid = val('topic_id'); if(tid && tid !== 'auto') a.push('--id', tid);
    run(a);
  }
  function batch(){
    const a = ['batch','--date', val('date'),'--seed', String(val('seed'))];
    const raw = val('indices').trim();
    if(raw){ a.push('--indices', raw); } else { a.push('--top', String(val('top'))); }
    const lang = val('lang'); if(lang) a.push('--lang', lang);
    const aspect = val('aspect'); if(aspect && aspect !== 'all') a.push('--aspect', aspect);
    if(checked('skip_image')) a.push('--skip_image');
    if(checked('package')) a.push('--package');
    if(checked('saveas')) a.push('--saveas');
    run(a);
  }
  function layout(){
    const a = ['layout','--date', val('date'),'--id', val('topic_id')||'auto'];
    const aspect = val('aspect'); if(aspect && aspect !== 'all') a.push('--aspect', aspect);
    run(a);
  }
  function publishNow(){
    const a = ['publish','--date', val('date'),'--id', val('topic_id')||'auto','--lang', (val('lang')||'en')];
    const img = val('image'); if(img) a.push('--image', img);
    const plat = val('platform'); if(plat) a.push('--platform', plat);
    if(checked('csv')) a.push('--csv');
    if(checked('open')) a.push('--open');
    run(a);
  }
  function addFeed(){
    const u = val('feedurl').trim(); if(!u){ append('\n[warn] Enter a feed URL first.\n'); return; }
    run(['feeds','add', u]);
  }
  function removeFeed(){
    const i = val('rmindex'); if(!i){ append('\n[warn] Enter a 1-based index.\n'); return; }
    run(['feeds','remove','--index', String(i)]);
  }

  async function zipOutbox(){
    if(busy){ append("\n[busy] Wait for current task to finish...\n"); return; }
    setBusy(true);
    try{
      append("\n$ zip outbox\n");
      const res = await fetch("/api/zip_outbox", {
        method:"POST", headers:{"content-type":"application/json"},
        body: JSON.stringify({date: val("date")})
      });
      append(await res.text());
    }catch(e){
      append("\n[error] " + (e?.message || e) + "\n");
    }finally{
      setBusy(false);
    }
  }
  async function openOutbox(){
    try{
      const res = await fetch("/api/open_outbox", {
        method:"POST", headers:{"content-type":"application/json"},
        body: JSON.stringify({date: val("date")})
      });
      append(await res.text());
    }catch(e){
      append("\n[error] " + (e?.message || e) + "\n");
    }
  }
</script>
</body>
</html>
"""
    return html.replace("__TITLE__", title)


def _offline_html(title: str) -> str:
    h = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>__TITLE__ (Offline)</title>
<style>
  :root { --bg:#0b0e14; --fg:#ebedf0; --muted:#a0a8b0; --card:#121622; --accent:#6ea8fe; }
  html,body { margin:0; height:100%; background:var(--bg); color:var(--fg); font-family: ui-sans-serif,system-ui,Segoe UI,Roboto,Arial; }
  .wrap { display:flex; flex-direction:column; height:100%; }
  header { padding:12px 16px; background:var(--card); border-bottom:1px solid #222738; }
  header h1 { margin:0; font-size:18px; letter-spacing:.3px; }
  main { display:grid; grid-template-columns: 340px 1fr; gap:12px; padding:12px; height:100%; box-sizing:border-box; }
  .panel { background:var(--card); border:1px solid #222738; border-radius:12px; padding:12px; }
  .grp { margin-bottom:14px; }
  .grp h3 { margin:0 0 8px 0; font-size:14px; color:var(--muted); font-weight:600; }
  label { display:inline-block; width:90px; color:var(--muted); font-size:12px; }
  input,select { background:#0f1422; color:var(--fg); border:1px solid #2a3147; border-radius:8px; padding:6px 8px; margin:2px 0; font-size:13px; }
  .btn { background:#11182a; color:var(--fg); border:1px solid #2a3147; border-radius:10px; padding:8px 10px; margin:4px 4px 4px 0; font-size:13px; cursor:pointer; }
  #log { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:#0a0d16; border:1px solid #222738; height:calc(100vh - 170px); border-radius:12px; padding:10px; overflow:auto; white-space:pre-wrap; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>__TITLE__ â€” Offline Mode</h1>
    <div style="color:var(--muted); font-size:12px; margin-top:4px;">Networking is disabled. Use the CLI shown by each action.</div>
  </header>
  <main>
    <section class="panel">
      <div class="grp"><h3>Output</h3>
        <pre id="log">Offline mode: this environment does not allow starting a webserver.</pre>
      </div>
    </section>
  </main>
</div>
</body>
</html>
"""
    return h.replace("__TITLE__", title)


# ---------------------------- outbox helpers ----------------------------

def resolve_run_date(date_param: Optional[str], root: Path) -> str:
    if date_param and date_param != "latest":
        return date_param
    exports = root / "exports"
    try:
        if exports.exists():
            dates = [
                p.name for p in exports.iterdir()
                if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name[7] == "-"
            ]
            dates.sort(reverse=True)
            for d in dates:
                if (exports / d / "outbox").exists():
                    return d
    except Exception:
        pass
    from datetime import date as _date
    return _date.today().isoformat()


def get_outbox_path(root: Path, run_date: str) -> Path:
    return root / "exports" / run_date / "outbox"


def zip_outbox(root: Path, run_date: str) -> Path:
    import zipfile
    outbox = get_outbox_path(root, run_date)
    zip_path = root / "exports" / run_date / f"outbox_{run_date}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        if outbox.exists():
            for p in outbox.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(outbox))
    return zip_path


def open_folder(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            import subprocess; subprocess.run(["open", str(path)], check=False)
        else:
            import subprocess; subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass


# ---------------------------- FastAPI app factory (lazy import) ----------------------------

def create_fastapi_app():
    """
    Try to import FastAPI & build the app. Return (app, error) where error is None on success.
    On environments without `ssl`, importing FastAPI may raise ModuleNotFoundError('ssl').
    """
    try:
        from fastapi import FastAPI, Body
        from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, PlainTextResponse
    except Exception as e:  # ImportError, ModuleNotFoundError('ssl'), etc.
        return None, e

    app = FastAPI(title=APP_TITLE)

    @app.get("/", response_class=HTMLResponse)
    async def home():
        return _home_html(APP_TITLE)

    @app.post("/api/run")
    async def api_run(payload: dict = Body(default={})):
        import shlex
        data = payload or {}
        args = data.get("args") or data.get("cmd") or data.get("command") or []
        if isinstance(args, str):
            args = shlex.split(args)
        if not isinstance(args, list) or not args:
            return JSONResponse({"ok": False, "error": "missing 'cmd' (list) or 'command' (string)"}, status_code=400)
        return StreamingResponse(stream_process_async(args), media_type="text/plain; charset=utf-8")

    @app.get("/api/doctorjson")
    async def api_doctor_json():
        py = which_python()
        cmd = [py, "-m", "satyagrah", "doctor", "--json"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, cwd=str(ROOT),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            out, err = await proc.communicate()
            if proc.returncode not in (0, 2):
                return PlainTextResponse((err or out or b"error").decode("utf-8", errors="ignore"), status_code=500)
            data = json.loads(out.decode("utf-8", errors="ignore") or "[]")
            return JSONResponse(data)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/api/zip_outbox")
    async def api_zip_outbox(payload: dict = Body(default={})):
        date = (payload.get("date") or "latest")
        rd = resolve_run_date(date, ROOT)
        outbox = get_outbox_path(ROOT, rd)
        if not outbox.exists():
            return PlainTextResponse(f"[warn] Outbox not found for date {rd}\n", status_code=404)
        z = zip_outbox(ROOT, rd)
        return PlainTextResponse(f"ZIP -> {z}\n", status_code=200)

    @app.post("/api/open_outbox")
    async def api_open_outbox(payload: dict = Body(default={})):
        date = (payload.get("date") or "latest")
        rd = resolve_run_date(date, ROOT)
        outbox = get_outbox_path(ROOT, rd)
        if not outbox.exists():
            return PlainTextResponse(f"[warn] Outbox not found for date {rd}\n", status_code=404)
        open_folder(outbox)
        return PlainTextResponse(f"Opened -> {outbox}\n", status_code=200)

    return app, None


# ---------------------------- Fallback server (stdlib only) ----------------------------

class _Handler(BaseHTTPRequestHandler):
    server_version = "SatyFallback/1.2"

    def _send(self, code: int, ctype: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/" or self.path.startswith("/index.html"):
            html = _home_html(APP_TITLE).encode("utf-8")
            self._send(200, "text/html; charset=utf-8", html)
            return

        if self.path == "/api/doctorjson":
            rc, out = run_process_blocking(["doctor", "--json"])  # doctor may exit 0/2
            try:
                data = json.loads(out)
                body = json.dumps(data).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", body)
            except Exception:
                self._send(200 if rc in (0, 2) else 500, "text/plain; charset=utf-8", out.encode("utf-8"))
            return

        self._send(404, "text/plain; charset=utf-8", b"Not found")

    def do_POST(self):  # noqa: N802
        n = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n) if n > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}

        if self.path == "/api/run":
            args = payload.get("args") or []
            if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
                self._send(400, "application/json; charset=utf-8", b'{"error":"args must be a list of strings"}')
                return
            rc, out = run_process_blocking(args)
            self._send(200, "text/plain; charset=utf-8", out.encode("utf-8"))
            return

        if self.path == "/api/zip_outbox":
            date = (payload.get("date") if isinstance(payload, dict) else None) or "latest"
            rd = resolve_run_date(date, ROOT)
            outbox = get_outbox_path(ROOT, rd)
            if not outbox.exists():
                self._send(404, "text/plain; charset=utf-8", f"[warn] Outbox not found for date {rd}\n".encode("utf-8"))
                return
            z = zip_outbox(ROOT, rd)
            self._send(200, "text/plain; charset=utf-8", f"ZIP -> {z}\n".encode("utf-8"))
            return

        if self.path == "/api/open_outbox":
            date = (payload.get("date") if isinstance(payload, dict) else None) or "latest"
            rd = resolve_run_date(date, ROOT)
            outbox = get_outbox_path(ROOT, rd)
            if not outbox.exists():
                self._send(404, "text/plain; charset=utf-8", f"[warn] Outbox not found for date {rd}\n".encode("utf-8"))
                return
            open_folder(outbox)
            self._send(200, "text/plain; charset=utf-8", f"Opened -> {outbox}\n".encode("utf-8"))
            return

        self._send(404, "text/plain; charset=utf-8", b"Not found")


def run_fallback_server(host: str, port: int) -> None:
    """Run stdlib HTTP server. If binding is not supported, raise OSError to allow offline mode."""
    try:
        httpd = ThreadingHTTPServer((host, port), _Handler)
    except OSError as e:
        raise e
    sa = httpd.socket.getsockname()
    print(f"Fallback server on http://{sa[0]}:{sa[1]}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


# ---------------------------- Offline writer ----------------------------

def write_offline_page(out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = _offline_html(APP_TITLE)
    out_path.write_text(html, encoding="utf-8")
    return out_path


# ---------------------------- tests ----------------------------

def _selftest() -> int:
    import unittest
    import tempfile

    class Tests(unittest.TestCase):
        def test_home_contains_title(self):
            html = _home_html(APP_TITLE)
            self.assertIn(APP_TITLE, html)
            self.assertIn("function val(id)", html)
            self.assertIn("<title", html)

        def test_which_python(self):
            self.assertTrue(which_python())

        def test_offline_writer(self):
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "offline.html"
                out = write_offline_page(p)
                self.assertTrue(out.exists())
                t = out.read_text(encoding="utf-8")
                self.assertIn("Offline", t)
                self.assertIn(APP_TITLE, t)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


# ---------------------------- CLI entry ----------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes (FastAPI only)")
    parser.add_argument("--selftest", action="store_true", help="Run built-in tests and exit")
    parser.add_argument("--force-fallback", action="store_true", help="Force stdlib server (ignore FastAPI)")
    parser.add_argument("--offline", action="store_true", help="Write offline HTML and exit (no server)")
    parser.add_argument("--offline-out", default="saty_offline.html", help="Offline HTML path")
    args = parser.parse_args(argv if argv is not None else None)

    if args.selftest:
        return _selftest()

    if args.offline:
        out = write_offline_page(Path(args.offline_out))
        print(f"Offline page written -> {out}")
        return 0

    # Try FastAPI first unless forced fallback
    if not args.force_fallback:
        app, err = create_fastapi_app()
        if app is not None:
            try:
                import uvicorn  # type: ignore
                print(f"Root: {ROOT}")
                uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
                return 0
            except Exception as e:
                print(f"FastAPI/Uvicorn unavailable or failed ({e}); trying fallback server...")
        else:
            print(f"FastAPI unavailable ({err}); trying fallback server...")

    # Fallback server; if bind fails, write offline page
    try:
        run_fallback_server(args.host, args.port)
        return 0
    except OSError as e:
        if getattr(e, 'errno', None) in {138, errno.EPERM, errno.EACCES} or 'Not supported' in str(e):
            out = write_offline_page(Path(args.offline_out))
            print(f"Networking not permitted here ({e}). Offline page -> {out}")
            return 0
        raise


def _safe_exit(code) -> None:
    """Exit semantics that avoid raising SystemExit on success."""
    try:
        icode = 0 if code is None else int(code)
    except Exception:
        icode = 1
    if icode != 0:
        raise SystemExit(icode)
    print("Done.")


if __name__ == "__main__":
    _safe_exit(main())


# add_outbox_buttons_fix.ps1
$ErrorActionPreference = "Stop"
$web = "D:\AISatyagrah\saty_web.py"
if (-not (Test-Path $web)) { throw "Not found: $web" }

# Backup
Copy-Item $web "$web.bak_$(Get-Date -Format yyyyMMdd_HHmmss)" -Force

# Load
$t = Get-Content -Raw -Encoding UTF8 $web

# --- 1) Ensure Body is imported with FastAPI ---
$t = $t -replace 'from fastapi import FastAPI, Request, Response\b',
                 'from fastapi import FastAPI, Request, Response, Body'

# --- 2) Inject helpers (only once) before "tests" header ---
if ($t -notmatch 'def resolve_run_date\(') {
$helpers = @'
# ---------------------------- outbox helpers ----------------------------
def resolve_run_date(date_param: Optional[str], root: Path) -> str:
    if date_param and date_param != "latest":
        return date_param
    exports = root / "exports"
    try:
        if exports.exists():
            dates = [p.name for p in exports.iterdir() if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name[7] == "-"]
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
'@
  $marker = '# ---------------------------- tests ----------------------------'
  $pos = $t.IndexOf($marker)
  if ($pos -ge 0) {
    $t = $t.Insert($pos, $helpers + "`r`n")
  } else {
    # fallback: append
    $t = $t + "`r`n" + $helpers + "`r`n"
  }
}

# --- 3) Add FastAPI endpoints (only once) before "return app, None" ---
if ($t -notmatch '/api/zip_outbox') {
$apiBlock = @'
    @app.post("/api/zip_outbox")
    async def api_zip_outbox(payload: dict = Body(default={})):
        date = (payload.get("date") or "latest")
        rd = resolve_run_date(date, ROOT)
        outbox = get_outbox_path(ROOT, rd)
        from fastapi.responses import PlainTextResponse
        if not outbox.exists():
            return PlainTextResponse(f"[warn] Outbox not found for date {rd}\n", status_code=404)
        z = zip_outbox(ROOT, rd)
        return PlainTextResponse(f"ZIP -> {z}\n", status_code=200)

    @app.post("/api/open_outbox")
    async def api_open_outbox(payload: dict = Body(default={})):
        date = (payload.get("date") or "latest")
        rd = resolve_run_date(date, ROOT)
        outbox = get_outbox_path(ROOT, rd)
        from fastapi.responses import PlainTextResponse
        if not outbox.exists():
            return PlainTextResponse(f"[warn] Outbox not found for date {rd}\n", status_code=404)
        open_folder(outbox)
        return PlainTextResponse(f"Opened -> {outbox}\n", status_code=200)

'@
  $ret = "return app, None"
  $retPos = $t.IndexOf($ret)
  if ($retPos -ge 0) {
    $t = $t.Insert($retPos, $apiBlock)
  }
}

# --- 4) Add fallback server routes (only once) in do_POST before 404 ---
if ($t -notmatch 'path == "/api/zip_outbox"') {
$fallback = @'
        elif self.path == "/api/zip_outbox":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(n) if n > 0 else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                self._send(400, "application/json; charset=utf-8", b'{"error":"invalid json"}')
                return
            date = (payload.get("date") if isinstance(payload, dict) else None) or "latest"
            rd = resolve_run_date(date, ROOT)
            outbox = get_outbox_path(ROOT, rd)
            if not outbox.exists():
                self._send(404, "text/plain; charset=utf-8", f"[warn] Outbox not found for date {rd}\n".encode("utf-8"))
                return
            z = zip_outbox(ROOT, rd)
            self._send(200, "text/plain; charset=utf-8", f"ZIP -> {z}\n".encode("utf-8"))
            return
        elif self.path == "/api/open_outbox":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(n) if n > 0 else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                self._send(400, "application/json; charset=utf-8", b'{"error":"invalid json"}')
                return
            date = (payload.get("date") if isinstance(payload, dict) else None) or "latest"
            rd = resolve_run_date(date, ROOT)
            outbox = get_outbox_path(ROOT, rd)
            if not outbox.exists():
                self._send(404, "text/plain; charset=utf-8", f"[warn] Outbox not found for date {rd}\n".encode("utf-8"))
                return
            open_folder(outbox)
            self._send(200, "text/plain; charset=utf-8", f"Opened -> {outbox}\n".encode("utf-8"))
            return
'@
  $notFound = 'self._send(404, "text/plain; charset=utf-8", b"Not found")'
  $nfPos = $t.IndexOf($notFound)
  if ($nfPos -ge 0) {
    $t = $t.Insert($nfPos, $fallback)
  }
}

# --- 5) Add two buttons after the "Open runs" button in the home HTML ---
$anchorRuns = @'<button class="btn" onclick="run([\'open\',\'--what\',\'runs\',\'--date\', val(\'date\')])">Open runs</button>'@
$btnInsert = @'
        <button class="btn" onclick="zipOutbox()">Zip outbox</button>
        <button class="btn" onclick="openOutbox()">Open outbox (resolved)</button>
'@
if ($t.Contains($anchorRuns) -and -not $t.Contains('Zip outbox')) {
  $idx = $t.IndexOf($anchorRuns)
  if ($idx -ge 0) {
    $t = $t.Insert($idx + $anchorRuns.Length, "`r`n" + $btnInsert)
  }
}

# --- 6) Add JS functions just before the first </script> in the file (home page script) ---
if ($t -notmatch 'function zipOutbox\(') {
$js = @'
  async function zipOutbox(){
    if(busy){ append("\n[busy] Wait for current task to finish...\n"); return; }
    busy = true;
    append("\n$ zip outbox\n");
    const res = await fetch("/api/zip_outbox", {
      method:"POST", headers:{"content-type":"application/json"},
      body: JSON.stringify({date: val("date")})
    });
    append(await res.text());
    busy = false;
  }
  async function openOutbox(){
    const res = await fetch("/api/open_outbox", {
      method:"POST", headers:{"content-type":"application/json"},
      body: JSON.stringify({date: val("date")})
    });
    append(await res.text());
  }
'@
  $closeScript = '</script>'
  $first = $t.IndexOf($closeScript)
  if ($first -ge 0) {
    $t = $t.Insert($first, "`r`n" + $js + "`r`n")
  }
}

# --- Write back ---
Set-Content -Encoding UTF8 $web $t
Write-Host "Patched $web"

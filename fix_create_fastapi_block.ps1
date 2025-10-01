# fix_create_fastapi_block.ps1
$ErrorActionPreference = "Stop"
$web = "D:\AISatyagrah\saty_web.py"
if (-not (Test-Path $web)) { throw "Not found: $web" }

# backup
Copy-Item $web "$web.bak_$(Get-Date -Format yyyyMMdd_HHmmss)" -Force

# load
$t = Get-Content -Raw -Encoding UTF8 $web

# Replace the whole create_fastapi_app() block
$pattern = '(?s)def create_fastapi_app\(\):.*?return app, None'
$replacement = @"
def create_fastapi_app():
    \"\"\"Try to import FastAPI & build the app. Return (app, error) where error is None on success.\"\"\"
    try:
        from fastapi import FastAPI, Request, Response, Body
        from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, PlainTextResponse
    except Exception as e:  # ImportError, ModuleNotFoundError('ssl'), etc.
        return None, e

    app = FastAPI(title=APP_TITLE)

    @app.get("/", response_class=HTMLResponse)
    async def home() -> str:
        return _home_html(APP_TITLE)

    @app.post("/api/run")
    async def api_run(payload: dict = Body(default={})):
        # Accept {"args":[...]}, {"cmd":[...]}, or {"command":"string"}
        args = payload.get("args") or payload.get("cmd") or payload.get("command") or []
        if isinstance(args, str):
            from shlex import split as _split
            args = _split(args)
        if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
            return JSONResponse({"error": "args must be a list of strings"}, status_code=400)
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
"@

$new = [regex]::Replace($t, $pattern, $replacement)
if ($new -eq $t) { Write-Warning "Pattern not found — file may already be fixed." } else { $t = $new }

# Ensure the helper functions exist (we added them earlier; keep as-is if present)
# No-op here: we assume resolve_run_date/get_outbox_path/zip_outbox/open_folder already exist.

# write back
Set-Content -Encoding UTF8 $web $t
Write-Host "Rewrote create_fastapi_app() in $web"

# force_fix_web.ps1
$web = 'D:\AISatyagrah\saty_web.py'
if (-not (Test-Path $web)) { Write-Error "Not found: $web"; exit 1 }

# Backup
$bak = "$web.bak_$(Get-Date -f yyyyMMdd_HHmmss)"
Copy-Item $web $bak -Force
Write-Host "Backup -> $bak"

# Load file
$code = Get-Content -Raw $web

# New, known-good create_fastapi_app()
$func = @"
def create_fastapi_app():
    \"\"\"Try to import FastAPI & build the app. Return (app, error) where error is None on success.
    On environments without `ssl`, importing FastAPI may raise ModuleNotFoundError('ssl').
    \"\"\"
    try:
        from fastapi import FastAPI, Request, Body
        from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, PlainTextResponse
    except Exception as e:  # ImportError, ModuleNotFoundError('ssl'), etc.
        return None, e

    app = FastAPI(title=APP_TITLE)

    @app.get("/", response_class=HTMLResponse)
    async def home():
        return _home_html(APP_TITLE)

    @app.post("/api/run")
    async def api_run(payload: dict = Body(default={})):
        \"\"\"
        Accept JSON like:
          {\"args\": [\"doctor\",\"--strict\"]}
          {\"cmd\": [\"doctor\",\"--strict\"]}
          {\"command\": \"doctor --strict\"}
        Streams the CLI output as text/plain.
        \"\"\"
        import shlex
        data = payload or {}
        args = data.get(\"args\") or data.get(\"cmd\") or data.get(\"command\") or []
        if isinstance(args, str):
            args = shlex.split(args)
        if not isinstance(args, list) or not args:
            return JSONResponse({\"ok\": False, \"error\": \"missing 'cmd' (list) or 'command' (string)\"}, status_code=400)
        return StreamingResponse(stream_process_async(args), media_type=\"text/plain; charset=utf-8\")

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
            return JSONResponse({\"error\": str(e)}, status_code=500)

    return app, None
"@

# Replace the whole function body, regardless of current indentation
$pattern = '(?ms)^def\s+create_fastapi_app\(\):\s*.*?^\s*return\s+app,\s*None\s*$'
$patched = [regex]::Replace($code, $pattern, $func)

if ($patched -eq $code) {
  Write-Host "Could not find existing create_fastapi_app(); inserting a fresh copy..." -ForegroundColor Yellow
  $patched = $code + "`r`n`r`n" + $func + "`r`n"
}

Set-Content -Encoding UTF8 $web $patched
Write-Host "Wrote $web"

# Compile sanity check
& python -m py_compile $web

# Show key lines
Select-String -Path $web -Pattern 'def create_fastapi_app|@app.post\("/api/run"|async def api_run|@app.get\("/api/doctorjson"|async def api_doctor_json' -Context 0,1

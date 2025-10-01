# --- config ---
$web = 'D:\AISatyagrah\saty_web.py'

# --- backup ---
if (Test-Path $web) {
  Copy-Item $web "$web.bak_$(Get-Date -f yyyyMMdd_HHmmss)"
} else {
  Write-Error "File not found: $web"; exit 1
}

# --- load ---
$code = Get-Content -Raw $web

# --- ensure FastAPI Request is imported in the lazy-import block ---
# from fastapi import FastAPI, Request, Response
$code = $code -replace 'from fastapi import FastAPI(?:\s*,\s*Response)?', 'from fastapi import FastAPI, Request, Response'

# --- replace the /api/run route with a robust version that reads JSON and streams output ---
$apiRun = @'
@app.post("/api/run")
async def api_run(request: Request):
    """
    Accept JSON like {"cmd": ["doctor","--strict"]} or {"args": [...]} or {"command": "doctor --strict"}.
    Returns plain text of the CLI output.
    """
    import shlex
    # read JSON safely (don't 422 on empty body)
    try:
        data = await request.json()
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    # accept multiple shapes
    args = data.get("args") or data.get("cmd") or data.get("command") or []
    if isinstance(args, str):
        args = shlex.split(args)

    if not isinstance(args, list) or not args:
        return JSONResponse({"ok": False, "error": "missing 'cmd' (list) or 'command' (string)"}, status_code=400)

    # stream CLI output back to the browser
    return StreamingResponse(stream_process_async(args), media_type="text/plain; charset=utf-8")
'@

# Replace whatever api_run exists inside create_fastapi_app()
$pattern = '(?ms)@app\.post\("/api/run"\)\s*async\s+def\s+api_run\([^\)]*\):.*?(?=^\s*@app\.|^\s*return app, None|^\s*\Z)'
$code = [regex]::Replace($code, $pattern, $apiRun + "`r`n")

# --- normalize /api/doctorjson signature (no return-type/params that confuse FastAPI) ---
$code = [regex]::Replace(
  $code,
  '(?ms)@app\.get\("/api/doctorjson"\)\s*async\s+def\s+api_doctor_json\([^\)]*\)\s*->\s*["\w\.\[\]]+:',
  '@app.get("/api/doctorjson")' + "`r`n" + 'async def api_doctor_json():'
)

# --- save ---
Set-Content -Encoding UTF8 $web $code

# --- quick compile sanity ---
python -m py_compile $web

# --- show the two function headers to confirm patch ---
Select-String -Path $web -Pattern 'async def api_run|async def api_doctor_json' -Context 0,2
Write-Host "`nPatched saty_web.py. Restart the server to apply changes." -ForegroundColor Green

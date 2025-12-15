# D:\AISatyagrah\scripts\jwt_and_export_test.ps1
$ErrorActionPreference = "Stop"

# ==== CONFIG ====
$base   = "http://127.0.0.1:9000"
$token  = $env:AUTH_TOKEN            # must match what the API was started with
$useJwt = $false
if ($env:JWT_SECRET -and $env:JWT_SECRET.Trim() -ne "") { $useJwt = $true }

Write-Host "API base: $base"
Write-Host "AUTH_TOKEN(length): " ($token | ForEach-Object { $_.Length })
Write-Host "JWT enabled? $useJwt"
Write-Host ""

# ==== Build headers ====
$headers = @{}
if ($token) { $headers["x-auth"] = $token }

$jwt = ""
if ($useJwt) {
  Write-Host "Generating JWT with env:JWT_SECRET..." -ForegroundColor Cyan
  $jwt = python - <<'PY'
import os, time, sys
try:
    import jwt
except Exception:
    print("")
    sys.exit(0)
secret = os.getenv("JWT_SECRET") or ""
if not secret:
    print("")
    sys.exit(0)
claims = {"sub":"dev","iat":int(time.time()),"exp":int(time.time())+3600}
print(jwt.encode(claims, secret, algorithm="HS256"))
PY
  if ($jwt) { $headers["Authorization"] = "Bearer $jwt" }
}

# ==== Tool/library checks ====
function Test-PythonImport([string]$mod) {
  $out = python - <<PY
import importlib, sys
try:
    importlib.import_module("$mod")
    print("OK")
except Exception as e:
    print("ERR:", e.__class__.__name__)
PY
  return $out.Trim()
}

$haveFfmpeg = $null -ne (Get-Command ffmpeg -ErrorAction SilentlyContinue)
Write-Host ("ffmpeg in PATH? " + ($haveFfmpeg ? "YES" : "NO"))

@(
  @{name="reportlab"; label="ReportLab" }
  @{name="PIL";       label="Pillow"    }
  @{name="pptx";      label="python-pptx"}
) | ForEach-Object {
  $r = Test-PythonImport $_.name
  Write-Host ("{0}: {1}" -f $_.label, $r)
}

# ==== Helper: GET with 3 auth modes ====
function Invoke-WithAuth($url) {
  try {
    return Invoke-RestMethod $url -Headers $headers -ErrorAction Stop
  } catch {
    try {
      if ($token) {
        return Invoke-RestMethod ($url + "?token=$token") -ErrorAction Stop
      } else { throw }
    } catch {
      throw
    }
  }
}

# ==== Ping API ====
Write-Host "`n== Health ==" -ForegroundColor Cyan
Invoke-RestMethod "$base/api/health" | Out-Host

Write-Host "`n== Version ==" -ForegroundColor Cyan
Invoke-WithAuth "$base/api/version" | Out-Host

Write-Host "`n== Config ==" -ForegroundColor Cyan
Invoke-WithAuth "$base/api/config" | ConvertTo-Json -Depth 6 | Out-Host

Write-Host "`n== Files (paged) ==" -ForegroundColor Cyan
Invoke-WithAuth "$base/api/files?limit=5&offset=0" | ConvertTo-Json -Depth 6 | Out-Host

Write-Host "`n== Start export job (memory) ==" -ForegroundColor Cyan
$body = @{ kind = "all"; use_redis = $false; retries = 2; backoff_sec = 2 } | ConvertTo-Json
$job  = Invoke-WithAuth "$base/api/jobs" -Method Post -ContentType 'application/json' -Body $body
$jid  = $job.id
$jid  | Out-Host

Start-Sleep -Seconds 1
Write-Host "`n== Poll job ==" -ForegroundColor Cyan
Invoke-WithAuth "$base/api/jobs/$jid" | ConvertTo-Json -Depth 6 | Out-Host

Write-Host "`n== Metrics (first lines) ==" -ForegroundColor Cyan
(Invoke-RestMethod "$base/metrics") -split "`n" | Select-Object -First 20 | ForEach-Object { $_ }

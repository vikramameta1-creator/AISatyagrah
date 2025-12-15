param(
  [string]$Api = "http://127.0.0.1:9000",
  [string]$Date = (Get-Date).ToString("yyyy-MM-dd"),
  [string]$Platform = "telegram",
  [string]$Token = $env:AUTH_TOKEN
)

$ErrorActionPreference = "Stop"

$headers = @{}
if ($Token) { $headers["x-auth"] = $Token }

Write-Host "Smoke: $Api  date=$Date platform=$Platform auth=" -NoNewline
if ($Token) { Write-Host "ON" -ForegroundColor Green } else { Write-Host "OFF" -ForegroundColor Yellow }

Write-Host "`nGET /api/health" -ForegroundColor Cyan
Invoke-RestMethod "$Api/api/health" -Headers $headers | ConvertTo-Json -Depth 6

Write-Host "`nGET /api/auth/enabled (if present)" -ForegroundColor Cyan
try {
  Invoke-RestMethod "$Api/api/auth/enabled" -Headers $headers | ConvertTo-Json -Depth 6
} catch {
  Write-Host "  (endpoint not present yet — OK for now)" -ForegroundColor Yellow
}

Write-Host "`nGET /api/newsroom/plan" -ForegroundColor Cyan
Invoke-RestMethod "$Api/api/newsroom/plan?date=$Date&platform=$Platform" -Headers $headers | ConvertTo-Json -Depth 6

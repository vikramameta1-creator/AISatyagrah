param(
  [int]$Port = 8010,
  [string]$SDHost = "http://127.0.0.1:7860",
  [string]$PeerInbox = "",           # e.g. "D:\AISatyagrah\dist\peer_agent_exe\inbox"
  [string]$PeerResults = "",         # e.g. "D:\AISatyagrah\jobs\peer_out"
  [switch]$CreateShortcuts = $true
)

$ErrorActionPreference = 'Stop'

# --- robust path detection (works when run as a .ps1 file or from different hosts) ---
$here = $PSScriptRoot
if (-not $here) {
  if ($PSCommandPath) { $here = Split-Path -Parent $PSCommandPath }
  else { $here = (Get-Location).Path }
}
$proj = (Resolve-Path (Join-Path $here '..')).Path

Write-Host "== AISatyagrah installer =="
Write-Host "Script folder: $here"
Write-Host "Project root : $proj"

# 0) Ensure scripts folder exists (if someone ran from a temp copy)
New-Item -ItemType Directory -Force -Path (Join-Path $proj 'scripts') | Out-Null

# 1) Python / venv
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python not found on PATH. Install Python 3.10+ and re-run."
}
if (-not (Test-Path "$proj\.venv\Scripts\python.exe")) {
  Write-Host "Creating venv..."
  python -m venv "$proj\.venv"
}
& "$proj\.venv\Scripts\python.exe" -m pip install -U pip wheel
& "$proj\.venv\Scripts\python.exe" -m pip install fastapi uvicorn python-multipart pillow

# 2) Folders
@(
  "$proj\data", "$proj\data\runs", "$proj\exports", "$proj\templates",
  "$proj\jobs\outbox", "$proj\jobs\peer_in", "$proj\jobs\peer_out"
) | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }

# 3) Env vars (User scope)
[Environment]::SetEnvironmentVariable("SATYAGRAH_SD_HOST",     $SDHost,             "User")
[Environment]::SetEnvironmentVariable("SATYAGRAH_PEER_OUTBOX", "$proj\jobs\outbox", "User")
if ($PeerInbox)   { [Environment]::SetEnvironmentVariable("SATYAGRAH_PEER_INBOX",   $PeerInbox,   "User") }
if ($PeerResults) { [Environment]::SetEnvironmentVariable("SATYAGRAH_PEER_RESULTS", $PeerResults, "User") }

# 4) Launch helpers
@"
`$env:SATYAGRAH_SD_HOST      = '$SDHost'
`$env:SATYAGRAH_PEER_OUTBOX  = '$proj\jobs\outbox'
`$env:SATYAGRAH_PEER_INBOX   = '$PeerInbox'
`$env:SATYAGRAH_PEER_RESULTS = '$PeerResults'
& '$proj\.venv\Scripts\python.exe' -m satyagrah.webui --port $Port
"@ | Set-Content -Encoding UTF8 "$proj\scripts\start_webui.ps1"

@"
# Optional: set SATYAGRAH_SECRET in env, or drop secret.txt next to PeerAgent.exe
& '$proj\.venv\Scripts\python.exe' -m satyagrah.peer.agent_app
"@ | Set-Content -Encoding UTF8 "$proj\scripts\start_peer_agent.ps1"

# 5) Desktop shortcuts (optional)
if ($CreateShortcuts) {
  $shell = New-Object -ComObject WScript.Shell
  $desk  = [Environment]::GetFolderPath("Desktop")

  $lnk1 = $shell.CreateShortcut("$desk\AISatyagrah WebUI.lnk")
  $lnk1.TargetPath = "powershell.exe"
  $lnk1.Arguments  = "-NoProfile -ExecutionPolicy Bypass -File `"$proj\scripts\start_webui.ps1`""
  $lnk1.WorkingDirectory = "$proj"
  $lnk1.Save()

  $lnk2 = $shell.CreateShortcut("$desk\AISatyagrah PeerAgent.lnk")
  $lnk2.TargetPath = "powershell.exe"
  $lnk2.Arguments  = "-NoProfile -ExecutionPolicy Bypass -File `"$proj\scripts\start_peer_agent.ps1`""
  $lnk2.WorkingDirectory = "$proj"
  $lnk2.Save()
}

# 6) Doctor
Write-Host "Running doctor..."
& "$proj\.venv\Scripts\python.exe" -m satyagrah.doctor --fix

Write-Host ""
Write-Host "Done ✅"
Write-Host "Start WebUI      : $proj\scripts\start_webui.ps1 (port $Port)"
Write-Host "Open in browser  : http://127.0.0.1:$Port"
Write-Host "PeerAgent launcher: $proj\scripts\start_peer_agent.ps1"
Write-Host "If you set new env vars, restart your terminal to pick them up."

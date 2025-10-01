# ========= CONFIG: set the actual commands you use to start each service =========
# Option A (direct): put the real commands here, e.g. your uvicorn/FastAPI or python -m entrypoints.
# Example guesses (change if different in your repo):
$SdCmd  = 'python -m satyagrah.image.mock_sd --host 127.0.0.1 --port 7860'   # <— edit or leave ""
$WebCmd = 'python -m satyagrah.webui --port 8000'                            # <— edit or leave ""

# Option B (batch): leave the two above as "" and point to your .bat files instead.
$SdBat  = 'D:\AISatyagrah\scripts\start_sd_mock.bat'     # used only if file exists AND $SdCmd is ""
$WebBat = 'D:\AISatyagrah\scripts\start_webui.bat'       # used only if file exists AND $WebCmd is ""

# ========= SCRIPT STARTS HERE — no edits needed below =========
$ErrorActionPreference = 'SilentlyContinue'
Set-Location 'D:\AISatyagrah'

# Kill anything blocking ports 7860/8000
$ports = 7860,8000
Get-NetTCPConnection -LocalPort $ports -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { try { Stop-Process -Id $_ -Force -ErrorAction Stop } catch {} }

function Start-Cmd([string]$cmdLine){
  if([string]::IsNullOrWhiteSpace($cmdLine)){ return $false }
  Write-Host "Starting: $cmdLine"
  Start-Process -WindowStyle Minimized "cmd.exe" -ArgumentList "/c $cmdLine"
  return $true
}

# Start SD (prefer direct command; else .bat if present)
$sdStarted = $false
if(-not [string]::IsNullOrWhiteSpace($SdCmd)){ $sdStarted = Start-Cmd $SdCmd }
elseif(Test-Path $SdBat){ $sdStarted = Start-Process -WindowStyle Minimized $SdBat; $sdStarted = $true }
else{ Write-Warning "SD start not configured. Edit $PSCommandPath to set `$SdCmd or create $SdBat" }

Start-Sleep -Seconds 2

# Start Web UI (prefer direct command; else .bat if present)
$webStarted = $false
if(-not [string]::IsNullOrWhiteSpace($WebCmd)){ $webStarted = Start-Cmd $WebCmd }
elseif(Test-Path $WebBat){ $webStarted = Start-Process -WindowStyle Minimized $WebBat; $webStarted = $true }
else{ Write-Warning "Web UI start not configured. Edit $PSCommandPath to set `$WebCmd or create $WebBat" }

# Wait for SD (7860)
for($i=0;$i -lt 30;$i++){
  try{ if((Invoke-WebRequest http://127.0.0.1:7860 -UseBasicParsing).StatusCode -ge 200){break} }catch{}
  Start-Sleep 1
}
# Wait for Web UI (8000)
for($i=0;$i -lt 30;$i++){
  try{ if((Invoke-WebRequest http://127.0.0.1:8000 -UseBasicParsing).StatusCode -ge 200){break} }catch{}
  Start-Sleep 1
}

# Open browser if up
try{ Start-Process "http://127.0.0.1:8000" }catch{}

# Final health check
python -m satyagrah.doctor --strict

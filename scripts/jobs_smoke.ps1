param(
  [string]$Base      = "http://127.0.0.1:9000",
  [string]$Token     = $env:AUTH_TOKEN,
  [ValidateSet("all","zip","pdf","pptx","csv","gif","mp4")]
  [string]$Kind      = "all",
  [string]$Date      = "",
  [switch]$UseRedis,
  [int]$Retries      = 2,
  [int]$BackoffSec   = 2,
  [int]$PollMs       = 700,
  [int]$TimeoutSec   = 90,
  [switch]$Bearer    # if set, send Authorization: Bearer instead of x-auth
)

if ([string]::IsNullOrWhiteSpace($Token)) {
  Write-Warning "AUTH_TOKEN not set in this shell. Using fallback 'mysupersecrettoken'."
  $Token = "mysupersecrettoken"
}

function New-AuthHeaders {
  param([string]$t,[switch]$bearer)
  if ($bearer) { return @{ "Authorization" = "Bearer $t" } }
  else         { return @{ "x-auth" = $t } }
}

$hdr = New-AuthHeaders -t $Token -bearer:$Bearer
$ct  = 'application/json'

Write-Host "== Health (public) =="
Invoke-RestMethod "$Base/api/health"

Write-Host "`n== Enqueue export job =="
$body = @{
  kind        = $Kind
  use_redis   = [bool]$UseRedis
  retries     = $Retries
  backoff_sec = $BackoffSec
}
if ($Date) { $body.date = $Date }
$jobResp = Invoke-RestMethod "$Base/api/jobs" -Method POST -Headers $hdr -ContentType $ct -Body ($body | ConvertTo-Json -Depth 4)
$jobResp | ConvertTo-Json -Depth 6
$jid = $jobResp.id
if ([string]::IsNullOrWhiteSpace($jid)) { throw "Job was not created (jid empty)." }

Write-Host "`n== Poll status =="
$sw = [Diagnostics.Stopwatch]::StartNew()
$doneStates = "done","failed","canceled","error"
$status = ""
while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
  try {
    $st = Invoke-RestMethod "$Base/api/jobs/$jid" -Headers $hdr
    $status = $st.status
    Write-Host ("{0:n1}s  status={1}  progress={2}%" -f $sw.Elapsed.TotalSeconds, $st.status, [int]($st.progress))
    if ($doneStates -contains $status) { break }
  } catch {
    Write-Warning $_.Exception.Message
  }
  Start-Sleep -Milliseconds $PollMs
}
$sw.Stop()
Write-Host "Final status: $status"
if ($status -ne "done") { Write-Warning "Job did not finish successfully."; }

Write-Host "`n== If done, show results =="
try {
  $st = Invoke-RestMethod "$Base/api/jobs/$jid" -Headers $hdr
  $st.result | ConvertTo-Json -Depth 6
} catch { Write-Warning $_.Exception.Message }

Write-Host "`n== Files (recent 5) =="
try {
  Invoke-RestMethod "$Base/api/files?limit=5&offset=0" -Headers $hdr | ConvertTo-Json -Depth 6
} catch { Write-Warning $_.Exception.Message }

Write-Host "`n== Metrics =="
try {
  Invoke-RestMethod "$Base/metrics" | Select-Object -First 20 | ForEach-Object { $_ }
} catch { Write-Warning $_.Exception.Message }

Write-Host "`nTip:"
Write-Host " - Server tab must be running uvicorn with the SAME AUTH_TOKEN:"
Write-Host "     `$env:AUTH_TOKEN = '$Token' ; uvicorn satyagrah.web.jobs_api:app --host 127.0.0.1 --port 9000 --reload"
Write-Host " - Start an RQ worker if UseRedis is set:"
Write-Host "     `$env:REDIS_URL = 'redis://127.0.0.1:6379/0' ; `$env:RQ_WORKER_CLASS = 'rq.SimpleWorker' ; python -m rq.cli worker exports --url `$env:REDIS_URL"

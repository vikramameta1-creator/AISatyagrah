param(
  [string]$Api = "http://127.0.0.1:9000",
  [string]$Token = $env:AUTH_TOKEN,     # set this in your shell if auth is on
  [string]$Date = ""                    # blank = latest run
)

# --- helpers ---
$H = if ($Token) { @{ "x-auth" = $Token } } else { @{} }
function J($o){ $o | ConvertTo-Json -Depth 8 }

Write-Host "== Version / Doctor =="
Invoke-RestMethod -Uri "$Api/api/version"
Invoke-RestMethod -Uri "$Api/api/newsroom/doctor"

Write-Host "`n== Plan (get or build fallback) =="
$plan = Invoke-RestMethod -Uri "$Api/api/newsroom/plan?date=$Date" -Headers $H
$resolved = $plan.date
"Using date: $resolved, items: $($plan.items.Count)"

# ---------- 1) Send Now (per-id) ----------
$ids = @()
$plan.items | Where-Object { $_.platform -eq 'telegram' -and $_.status -eq 'approved' } | Select-Object -First 2 | ForEach-Object { $ids += ($_.id, $_.topic_id | Where-Object { $_ })[0] }
if ($ids.Count -gt 0) {
  Write-Host "`n== Send Now (dry-run) for ids: $($ids -join ',') =="
  $body = @{ date=$resolved; platform='telegram'; ids=$ids; dry_run=$true }
  Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/send_now" -Headers $H -Body ($body|J) -ContentType "application/json"
} else {
  Write-Host "No approved telegram items to send now (dry-run)."
}

# ---------- 2) Approve by filter ----------
Write-Host "`n== Approve-Filter (query='stampede') on telegram (dry pack) =="
$body = @{ date=$resolved; platform='telegram'; query='stampede' }
Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/approve_filter" -Headers $H -Body ($body|J) -ContentType "application/json"

# ---------- 3) Import CSV (demo) ----------
Write-Host "`n== Import CSV =="
$tmp = Join-Path $env:TEMP "newsroom_import.csv"
@'
title,snippet,hashtags,id
Demo title A,Short snippet A,#india #indiapolitics,ia
Demo title B,Short snippet B,#delhi #mumbai,ib
'@ | Set-Content -Encoding UTF8 $tmp
# PowerShell 7+ multipart form:
$form = @{
  date = $resolved
  platform = 'telegram'
  file = Get-Item $tmp
}
Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/import_csv" -Headers $H -Form $form

# ---------- 4) Hashtag presets CRUD ----------
Write-Host "`n== Presets add/apply/list/delete =="
$pres = @{ name='base_in'; platform='telegram'; hashtags='#india #indiapolitics #delhi #mumbai' }
Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/presets" -Headers $H -Body ($pres|J) -ContentType "application/json"
Invoke-RestMethod -Uri "$Api/api/newsroom/presets"
Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/presets/apply?date=$resolved&platform=telegram&name=base_in" -Headers $H
Invoke-RestMethod -Method DELETE -Uri "$Api/api/newsroom/presets?name=base_in&platform=telegram" -Headers $H

# ---------- 5) Split-run (platform specific) ----------
Write-Host "`n== Run split (telegram, DRY-RUN) =="
$split = @{ date=$resolved; target='telegram'; dry_run=$true; confirm=$false }
Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/run_split" -Headers $H -Body ($split|J) -ContentType "application/json"

# ---------- 6) Images report ----------
Write-Host "`n== Image attach report (telegram) =="
Invoke-RestMethod -Uri "$Api/api/newsroom/images?date=$resolved&platform=telegram" -Headers $H

# ---------- 7) Undo (flip status for a single id) ----------
Write-Host "`n== Undo/flip status of first telegram row (if exists) =="
$firstT = $plan.items | Where-Object { $_.platform -eq 'telegram' } | Select-Object -First 1
if ($firstT) {
  $undo = @{ date=$resolved; id= ($firstT.id, $firstT.topic_id | Where-Object { $_ })[0] }
  Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/undo" -Headers $H -Body ($undo|J) -ContentType "application/json"
}

# ---------- 8) Test-mode toggle ----------
Write-Host "`n== Test mode toggle on/off =="
Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/test_mode" -Headers $H -Body (@{enabled=$true}|J) -ContentType "application/json"
Invoke-RestMethod -Uri "$Api/api/newsroom/test_mode"
Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/test_mode" -Headers $H -Body (@{enabled=$false}|J) -ContentType "application/json"

# ---------- 9) Roles map (token -> role) ----------
if ($Token) {
  Write-Host "`n== Set role for current token (editor) and read roles =="
  Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/roles" -Headers $H -Body (@{token=$Token; role='editor'}|J) -ContentType "application/json"
  Invoke-RestMethod -Uri "$Api/api/newsroom/roles" -Headers $H
} else {
  Write-Host "No token set; skipping roles demo."
}

# ---------- 10) Core pipeline + metrics + logs (still DRY-RUN) ----------
Write-Host "`n== Auto-approve preview =="
Invoke-RestMethod -Uri "$Api/api/newsroom/auto_approve/preview?date=$resolved" -Headers $H

Write-Host "`n== Auto-approve apply =="
Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/auto_approve?date=$resolved" -Headers $H

Write-Host "`n== Run pipeline (DRY-RUN guarded) =="
$run = @{ date=$resolved; platform='telegram'; dry_run=$true; skip_instagram=$false; rebuild=$false; confirm=$false }
Invoke-RestMethod -Method POST -Uri "$Api/api/newsroom/run" -Headers $H -Body ($run|J) -ContentType "application/json"

Write-Host "`n== Metrics & Logs =="
Invoke-RestMethod -Uri "$Api/api/newsroom/metrics?days=7" -Headers $H
Invoke-RestMethod -Uri "$Api/api/newsroom/logs?date=$resolved&limit=50" -Headers $H

Write-Host "`n== IG captions & CSV (download to exports) =="
$igTxt = "D:\AISatyagrah\exports\instagram_captions_$resolved.txt"
$igCsv = "D:\AISatyagrah\exports\instagram_posts_$resolved.csv"
try { Invoke-WebRequest -Uri "$Api/api/newsroom/ig_captions?date=$resolved" -Headers $H -OutFile $igTxt } catch { "No captions yet." }
try { Invoke-WebRequest -Uri "$Api/api/newsroom/ig_csv?date=$resolved" -Headers $H -OutFile $igCsv } catch { "No IG CSV yet." }

Write-Host "`nAll calls done."

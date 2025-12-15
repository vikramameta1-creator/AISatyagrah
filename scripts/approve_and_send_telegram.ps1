param(
  [string]$Date = "",
  [switch]$ConfirmSend  # require explicit switch to actually publish
)
$API = "http://127.0.0.1:9000"
$H = @{}; if ($env:AUTH_TOKEN) { $H["x-auth"] = $env:AUTH_TOKEN }
$resolved = if ($Date) { $Date } else { (Invoke-RestMethod -Uri "$API/api/newsroom/plan" -Headers $H).date }
$plan = Invoke-RestMethod -Uri "$API/api/newsroom/plan?date=$resolved" -Headers $H

$drafts = $plan.items | Where-Object { $_.platform -eq "telegram" -and (($_.status) -as [string]).ToLower() -eq "draft" }
foreach ($d in $drafts) {
  $ident = if ($d.id) { "$($d.id)" } elseif ($d.topic_id) { "$($d.topic_id)" } else { "" }
  if (-not $ident) { continue }
  $body = @{ date=$resolved; id=$ident; topic_id=$ident; status="approved" } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri "$API/api/newsroom/status" -Headers ($H + @{ "Content-Type"="application/json" }) -Body $body | Out-Null
}

# Dry-run first
$body = @{ date=$resolved; platform="telegram"; dry_run=$true; skip_instagram=$true; rebuild=$false } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$API/api/newsroom/run" -Headers ($H + @{ "Content-Type"="application/json" }) -Body $body

if ($ConfirmSend) {
  $body = @{ date=$resolved; platform="telegram"; dry_run=$false; skip_instagram=$true; rebuild=$false; confirm=$true } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri "$API/api/newsroom/run" -Headers ($H + @{ "Content-Type"="application/json" }) -Body $body
} else {
  Write-Host "Publish skipped (no -ConfirmSend)."
}

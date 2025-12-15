param([string]$Date = "")
$API = "http://127.0.0.1:9000"
$H = @{}; if ($env:AUTH_TOKEN) { $H["x-auth"] = $env:AUTH_TOKEN }
$resolved = if ($Date) { $Date } else { (Invoke-RestMethod -Uri "$API/api/newsroom/plan" -Headers $H).date }
$plan = Invoke-RestMethod -Uri "$API/api/newsroom/plan?date=$resolved" -Headers $H

$drafts = $plan.items | Where-Object { $_.platform -eq "instagram" -and (($_.status) -as [string]).ToLower() -eq "draft" }
foreach ($d in $drafts) {
  $ident = if ($d.id) { "$($d.id)" } elseif ($d.topic_id) { "$($d.topic_id)" } else { "" }
  if (-not $ident) { continue }
  $body = @{ date=$resolved; id=$ident; topic_id=$ident; status="approved" } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri "$API/api/newsroom/status" -Headers ($H + @{ "Content-Type"="application/json" }) -Body $body | Out-Null
}

# Build captions (no publish)
$body = @{ date=$resolved; platform="instagram"; dry_run=$true; skip_instagram=$false; rebuild=$false } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$API/api/newsroom/run" -Headers ($H + @{ "Content-Type"="application/json" }) -Body $body | Out-Null

# Download captions + CSV
$dstCap = "D:\AISatyagrah\exports\instagram_captions_$resolved.txt"
$null = New-Item -ItemType Directory -Force -Path (Split-Path $dstCap)
Invoke-WebRequest -Uri "$API/api/newsroom/ig_captions?date=$resolved" -Headers $H -OutFile $dstCap

$dstCsv = "D:\AISatyagrah\exports\instagram_posts_$resolved.csv"
Invoke-WebRequest -Uri "$API/api/newsroom/ig_csv?date=$resolved" -Headers $H -OutFile $dstCsv
Write-Host "IG outputs -> $dstCap , $dstCsv"

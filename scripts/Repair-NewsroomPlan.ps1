param(
  [string]$Root = "D:\AISatyagrah",
  [string]$Date = "2025-12-12",
  [string]$Platform = "telegram"
)

$runDir = Join-Path $Root "data\runs\$Date"
$plan   = Join-Path $runDir "newsroom_plan.jsonl"
if (-not (Test-Path $plan)) { throw "Plan not found: $plan" }

# --- backup first
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$bak   = Join-Path $Root "exports\archive\plan_${Date}_backup_${stamp}.jsonl"
New-Item -ItemType Directory -Force (Split-Path $bak) | Out-Null
Copy-Item $plan $bak -Force
Write-Host "Backup -> $bak"

# --- read lines (PS5-safe)
$lines = Get-Content -Path $plan -Encoding UTF8

$out      = New-Object System.Collections.Generic.List[string]
$changed  = 0
$nl       = [Environment]::NewLine

foreach($line in $lines){
  if (-not $line -or -not $line.Trim()) { continue }
  $obj = $line | ConvertFrom-Json

  # Fix rows where id is missing but hashtags looks like "t<number>"
  if ((-not $obj.id) -and ($obj.hashtags -match '^t\d+$')) {
    $obj.id       = $obj.hashtags
    $obj.topic_id = $obj.hashtags

    # Rebuild hashtags from snippet (#words only)
    $tags = @()
    if ($obj.snippet) {
      $tags = ($obj.snippet -split '\s+') | Where-Object { $_ -match '^#' }
    }
    $obj.hashtags = ($tags -join ' ').Trim()
    $changed++
  }

  $out.Add(($obj | ConvertTo-Json -Compress))
}

# --- write back
($out -join $nl) | Set-Content -Encoding UTF8 -Path $plan
Write-Host "Repaired: $changed row(s) -> $plan"

# --- quick summary
$items = Get-Content -Path $plan | ForEach-Object { $_ | ConvertFrom-Json }
$ids   = ($items | Select-Object -ExpandProperty id)
Write-Host "IDs now: $($ids -join ', ')"

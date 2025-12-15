# --- BEGIN newsroom_tools.ps1 ------------------------------------------------
param()

$API = "http://127.0.0.1:9000"
$Headers = @{}
if ($env:AUTH_TOKEN -and $env:AUTH_TOKEN.Trim()) { $Headers["x-auth"] = $env:AUTH_TOKEN.Trim() }

function Invoke-ApiJson {
  param([string]$Method="GET",[string]$Path,[hashtable]$Headers,[object]$Body)
  if ($Body -is [string]) { $json = $Body }
  elseif ($null -ne $Body) { $json = ($Body | ConvertTo-Json -Depth 8) }
  $params = @{ Method=$Method; Uri=("$API$Path"); Headers=$Headers }
  if ($json) { $params.ContentType="application/json"; $params.Body=$json }
  Invoke-RestMethod @params
}

# PS5 multipart upload
function PS5-MultipartUpload {
  param([string]$Uri, [string]$FilePath, [hashtable]$Headers)
  $boundary = [System.Guid]::NewGuid().ToString()
  $nl = "`r`n"
  $content = "--$boundary$nl" +
    'Content-Disposition: form-data; name="file"; filename="' + [System.IO.Path]::GetFileName($FilePath) + '"' + $nl +
    "Content-Type: text/csv$nl$nl" +
    [System.IO.File]::ReadAllText($FilePath) + $nl +
    "--$boundary--$nl"
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
  $hc = New-Object System.Net.Http.HttpClient
  foreach($k in $Headers.Keys){ $hc.DefaultRequestHeaders.Add($k, [string]$Headers[$k]) }
  $ct = New-Object System.Net.Http.ByteArrayContent($bytes)
  $ct.Headers.ContentType = New-Object System.Net.Http.Headers.MediaTypeHeaderValue("multipart/form-data")
  $ct.Headers.ContentType.Parameters.Add((New-Object System.Net.Http.Headers.NameValueHeaderValue("boundary",$boundary)))
  $resp = $hc.PostAsync($Uri, $ct).Result
  if (-not $resp.IsSuccessStatusCode) { throw ($resp.Content.ReadAsStringAsync().Result) }
  ($resp.Content.ReadAsStringAsync().Result | ConvertFrom-Json)
}

# 1) Load plan (utility)
function Get-Plan { param([string]$Date,[string]$Platform="telegram")
  Invoke-RestMethod "$API/api/newsroom/plan?date=$Date&platform=$Platform" -Headers $Headers
}

# 2) Approve all
function Approve-All { param([string]$Date,[string]$Platform="telegram")
  Invoke-ApiJson -Method POST -Path "/api/newsroom/approve_all?date=$Date&platform=$Platform" -Headers $Headers
}

# 3) Approve filter (contains)
function Approve-Filter { param([string]$Date,[string]$Platform="telegram",[string]$Contains)
  Invoke-ApiJson -Method POST -Path "/api/newsroom/approve_filter?date=$Date&platform=$Platform&contains=$([uri]::EscapeDataString($Contains))" -Headers $Headers
}

# 4) Dry run
function Run-Dry { param([string]$Date,[string]$Platform="telegram")
  Invoke-ApiJson -Method POST -Path "/api/newsroom/run" -Headers $Headers `
    -Body @{ date=$Date; platform=$Platform; dry_run=$true; confirm=$false }
}

# 5) Publish (confirm)
function Publish-Confirm { param([string]$Date,[string]$Platform="telegram")
  Invoke-ApiJson -Method POST -Path "/api/newsroom/run" -Headers $Headers `
    -Body @{ date=$Date; platform=$Platform; dry_run=$false; confirm=$true }
}

# 6) Import CSV (multipart)
function Import-CSV { param([string]$Date,[string]$Platform="telegram",[string]$CsvPath)
  if (-not (Test-Path $CsvPath)) { throw "CSV not found: $CsvPath" }
  PS5-MultipartUpload -Uri "$API/api/newsroom/import_csv?date=$Date&platform=$Platform" -FilePath $CsvPath -Headers $Headers
}

# 7) Download IG captions
function Get-IGCaptions { param([string]$Date)
  $out = "D:\AISatyagrah\exports\instagram_captions_$Date.txt"
  Invoke-WebRequest "$API/api/newsroom/ig_captions?date=$Date" -Headers $Headers -OutFile $out
  $out
}

# 8) Metrics
function Get-Metrics { param([int]$Days=7)
  Invoke-RestMethod "$API/api/newsroom/metrics?days=$Days" -Headers $Headers
}

# 9) Logs
function Get-Logs { param([string]$Date,[int]$Limit=100)
  Invoke-RestMethod "$API/api/newsroom/logs?date=$Date&limit=$Limit" -Headers $Headers
}

# 10) Undo item to draft
function Undo-Item { param([string]$Date,[string]$Id)
  Invoke-ApiJson -Method POST -Path "/api/newsroom/undo" -Headers $Headers -Body @{ date=$Date; id=$Id }
}

Write-Host "Loaded newsroom_tools.ps1 helpers."
# --- END newsroom_tools.ps1 --------------------------------------------------

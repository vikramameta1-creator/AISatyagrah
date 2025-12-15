#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# ---- config ----
$ROOT      = "D:\AISatyagrah"
$UI        = Join-Path $ROOT "ui"
$WEBPY     = Join-Path $ROOT "satyagrah\web\jobs_api.py"
$RUNS      = Join-Path $ROOT "data\runs"
$EXPORT    = Join-Path $ROOT "exports"
$ARCH      = Join-Path $EXPORT "archive"
$HOST      = "127.0.0.1"
$PORT      = 9000
$API       = "http://$HOST:$PORT"
$HARDRESET = $false   # true => archive old runs (keep today) + clear exports\latest

# Prefer venv Python so uvicorn loads properly
$VENV_PY   = Join-Path $ROOT ".venv\Scripts\python.exe"
$PY        = (Test-Path $VENV_PY) ? $VENV_PY : "python"

# ---- helpers ----
function Stop-Uvicorn {
  Get-Process -ErrorAction SilentlyContinue `
    | Where-Object {
        ($_.Name -match 'python|uvicorn') -and
        ($_.Path  -and ($_.Path -like "*AISatyagrah*"))
      } `
    | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep 1
}

function Start-Uvicorn {
  Push-Location $ROOT
  $args = @(
    "-m","uvicorn",
    "satyagrah.web.jobs_api:create_app",
    "--factory","--host",$HOST,"--port",$PORT,"--reload"
  )
  Start-Process -WindowStyle Minimized -FilePath $PY -ArgumentList $args -WorkingDirectory $ROOT
  Pop-Location
  Start-Sleep 2
}

function PS5-MultipartUpload($Uri, [string]$FilePath, $Headers=@{}) {
  Add-Type -AssemblyName System.Net.Http
  $hc = [System.Net.Http.HttpClient]::new()
  foreach ($k in $Headers.Keys) { $hc.DefaultRequestHeaders.Remove($k) | Out-Null; $hc.DefaultRequestHeaders.Add($k,[string]$Headers[$k]) }
  $mp = [System.Net.Http.MultipartFormDataContent]::new()
  $fs = [System.IO.File]::OpenRead($FilePath)
  try {
    $sc = [System.Net.Http.StreamContent]::new($fs)
    $cd = [System.Net.Http.Headers.ContentDispositionHeaderValue]::new("form-data")
    $cd.Name='"file"'; $cd.FileName='"'+[IO.Path]::GetFileName($FilePath)+'"'
    $sc.Headers.ContentDisposition = $cd
    $mp.Add($sc)

    try {
      $resp = $hc.PostAsync($Uri,$mp).Result
    } catch {
      return @{ ok=$false; error="Connect failed: $($_.Exception.Message)"; uri=$Uri }
    }
    if ($null -eq $resp) { return @{ ok=$false; error="No response (server offline?)"; uri=$Uri } }
    $txt  = $resp.Content.ReadAsStringAsync().Result
    return @{ ok=$resp.IsSuccessStatusCode; status=[int]$resp.StatusCode; body=$txt }
  } finally {
    $fs.Dispose(); $mp.Dispose(); $hc.Dispose()
  }
}

function Backup-Now {
  New-Item -ItemType Directory -Force -Path $ARCH | Out-Null
  $ts  = Get-Date -Format "yyyyMMdd_HHmmss"
  $tmp = Join-Path $env:TEMP ("ais_backup_"+$ts)   # << OUTSIDE exports to avoid recursion
  New-Item -ItemType Directory -Force -Path $tmp | Out-Null

  if (Test-Path $WEBPY) { Copy-Item $WEBPY $tmp -Force }
  if (Test-Path $UI   ) { Copy-Item $UI   (Join-Path $tmp "ui")    -Recurse -Force }
  if (Test-Path $RUNS ) { Copy-Item $RUNS (Join-Path $tmp "runs")  -Recurse -Force }
  if (Test-Path $EXPORT) {
    New-Item -ItemType Directory -Force -Path (Join-Path $tmp "exports") | Out-Null
    Get-ChildItem $EXPORT | Where-Object { $_.Name -ne "archive" } `
      | Copy-Item -Destination (Join-Path $tmp "exports") -Recurse -Force
  }

  $zip = Join-Path $ARCH ("backup_"+$ts+".zip")
  if (Test-Path $zip) { Remove-Item $zip -Force }
  Compress-Archive -Path (Join-Path $tmp "*") -DestinationPath $zip -Force
  Remove-Item $tmp -Recurse -Force
  Write-Host "Backup written: $zip"
}

function Clean-UI {
  $extras = @(
    "quickpanel.html","quickpanel.js","quickpanel.css","quickpanel_embed.js",
    "newsroom_more.js","newsroom_more.css","favicon.svg","favicon.ico"
  )
  foreach ($f in $extras) {
    $p = Join-Path $UI $f
    if (Test-Path $p) { Remove-Item $p -Force }
  }
}

function Write-Minimal-UI {
  New-Item -ItemType Directory -Force -Path $UI | Out-Null

  $HTML = @'
<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<title>AISatyagrah — Newsroom</title><meta name="viewport" content="width=device-width,initial-scale=1"/>
<link rel="stylesheet" href="/ui-static/newsroom.css"></head><body>
<header id="toolbar">
  <input id="tb-token" placeholder="Toolbar token"/>
  <select id="tb-platform"><option value="telegram" selected>telegram</option><option value="instagram">instagram</option></select>
  <button id="tb-approve">Approve All</button><button id="tb-dryrun">Dry-Run</button>
  <button id="tb-publish">Publish (confirm)</button><button id="tb-metrics">Metrics</button><button id="tb-logs">Logs</button>
  <input id="tb-search" placeholder="search…"/><button id="tb-search-btn">Search</button>
</header>
<main class="container">
  <h1>AISatyagrah — Newsroom</h1>
  <div class="row">
    <label>Date <input id="date" placeholder="dd / mm / yyyy"/></label>
    <div class="nav"><button id="prev">⟨⟨</button><button id="next">⟩⟩</button></div>
    <label>Platform <select id="platform"><option value="telegram" selected>telegram</option><option value="instagram">instagram</option></select></label>
    <button id="load">Load plan</button><button id="latest">Latest telegram</button><button id="fromcsv">⇢ Generate from CSV</button>
  </div>
  <div class="row toggles">
    <label><input type="checkbox" id="dryrun" checked/> Dry run (don’t send Telegram)</label>
    <label><input type="checkbox" id="skipig"/> Skip Instagram captions</label>
    <button id="run">Run pipeline</button><button id="ig">✨ IG captions</button>
  </div>
  <div id="tabs"><button data-tab="all">All (0)</button><button data-tab="draft">Draft (0)</button><button data-tab="approved">Approved (0)</button><button data-tab="sent">Sent (0)</button></div>
  <section id="list"></section>
  <section><label>x-auth token (optional) <input id="auth"/></label><button id="save">Save</button></section>
</main>
<script src="/ui-static/newsroom_toolbar.js"></script><script src="/ui-static/newsroom.js"></script>
</body></html>
'@

  $CSS = @'
:root{--bg:#0b0f1a;--ink:#e6e8f2;--mut:#a7aed3;--chip:#6f6bff;--chip2:#2e3354;--ok:#34d399;--warn:#f59e0b}
*{box-sizing:border-box} html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:system-ui,Segoe UI,Inter,Arial}
.container{max-width:1200px;margin:24px auto;padding:0 16px}
#toolbar{display:flex;gap:8px;align-items:center;padding:10px;background:#0d1327;border-bottom:1px solid #232a49;position:sticky;top:0;z-index:10}
#toolbar input,select,button{background:#0e1224;color:var(--ink);border:1px solid #2a3250;border-radius:10px;padding:8px 12px}
#toolbar button{background:var(--chip);border:none}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0}
#tabs{display:flex;gap:10px;margin:16px 0}
#tabs button{background:#151a2b;color:var(--ink);border:1px solid #2a3250;border-radius:999px;padding:6px 12px}
.card{background:#0e1326;border:1px solid #232a49;border-radius:18px;padding:14px 16px;margin:12px 0}
.badge{background:#16203a;border:1px solid #2a3250;border-radius:999px;padding:4px 8px;margin-right:8px}
.badge.ok{background:rgba(52,211,153,.2);border-color:rgba(52,211,153,.45)}
.badge.warn{background:rgba(245,158,11,.2);border-color:rgba(245,158,11,.45)}
.mono{font-family:ui-monospace,Consolas,monospace}
'@

  $TB = @'
(function(){
  const $=(s)=>document.querySelector(s);
  function tok(){return localStorage.getItem("xauth")||""}
  function setTok(){localStorage.setItem("xauth",$("#tb-token").value.trim());$("#auth").value=$("#tb-token").value.trim()}
  function api(p,o){const h=o?.headers||{};const t=tok();if(t)h["x-auth"]=t;return fetch(p,{...o,headers:h})}
  async function run(url){const r=await api(url); const t=await r.text(); alert(t)}
  $("#tb-approve").onclick=()=>run(`/api/newsroom/approve_all?date=${encodeURIComponent($("#date").value)}&platform=${$("#tb-platform").value}`);
  $("#tb-dryrun").onclick =()=>run(`/api/newsroom/run?date=${encodeURIComponent($("#date").value)}&platform=${$("#tb-platform").value}&dry_run=true`);
  $("#tb-publish").onclick=()=>{ if(confirm("Really publish?")) run(`/api/newsroom/run?date=${encodeURIComponent($("#date").value)}&platform=${$("#tb-platform").value}&dry_run=false`) };
  $("#tb-metrics").onclick=async()=>{const r=await api("/api/newsroom/metrics?days=7");alert(await r.text())}
  $("#tb-logs").onclick   =async()=>{const r=await api(`/api/newsroom/logs?date=${encodeURIComponent($("#date").value)}&limit=100`);alert(await r.text())}
  $("#tb-search-btn").onclick=()=>alert("Use list filters; baseline UI keeps search simple.");
  $("#tb-token").addEventListener("change",setTok); const t=tok(); $("#tb-token").value=t; $("#auth").value=t;
})();
'@

  $JS = @'
(function(){
  const $=(s)=>document.querySelector(s);
  function tok(){return localStorage.getItem("xauth")||""}
  function api(p){return fetch(p,{headers:tok()?{"x-auth":tok()}:undefined})}
  function render(items){
    const root=$("#list"); root.innerHTML="";
    for(const it of items){
      const c=document.createElement("div"); c.className="card";
      c.innerHTML=`<div class="row">
        <span class="badge ${it.status==='approved'?'ok':it.status==='draft'?'warn':''}">${(it.status||'').toUpperCase()}</span>
        <span class="badge">${it.platform}</span></div>
        <h3>${it.title||"(no title)"} <small class="mono">${it.id||it.topic_id||""}</small></h3>
        <p>${it.snippet||""}</p><div class="mono">${(it.hashtags||"").replaceAll("#","#<wbr>")}</div>`;
      root.appendChild(c);
    }
  }
  async function load(){
    const d=$("#date").value.trim(), p=$("#platform").value;
    const r=await api(`/api/newsroom/plan?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}`); const j=await r.json();
    render(j.items||[]);
    const all=(j.items||[]).length, draft=(j.items||[]).filter(x=>x.status==="draft").length,
          appr=(j.items||[]).filter(x=>x.status==="approved").length, sent=(j.items||[]).filter(x=>x.status==="sent").length;
    document.querySelector("#tabs [data-tab='all']").textContent=`All (${all})`;
    document.querySelector("#tabs [data-tab='draft']").textContent=`Draft (${draft})`;
    document.querySelector("#tabs [data-tab='approved']").textContent=`Approved (${appr})`;
    document.querySelector("#tabs [data-tab='sent']").textContent=`Sent (${sent})`;
  }
  $("#load").onclick = load;
  $("#latest").onclick=()=>{ $("#date").value=""; load(); };
  $("#fromcsv").onclick=()=>alert("Use reset_newsroom_v2.ps1 PS5-MultipartUpload helper to POST a CSV.");
  $("#run").onclick = async ()=>{
    const d=$("#date").value.trim(),p=$("#platform").value, dry=$("#dryrun").checked, skip=$("#skipig").checked;
    const r=await api(`/api/newsroom/run?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}&dry_run=${dry}&skip_instagram=${skip}`);
    alert(await r.text()); load();
  };
  $("#ig").onclick= async ()=>{
    const d=$("#date").value.trim(); const r=await api(`/api/newsroom/ig_captions?date=${encodeURIComponent(d)}&download=1`);
    if(r.status===204){alert("No captions.");return;}
    const b=await r.blob(); const a=document.createElement("a"); a.href=URL.createObjectURL(b); a.download="instagram_captions.txt"; a.click();
  };
  load();
})();
'@

  Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom.html") -Value $HTML
  Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom.css")  -Value $CSS
  Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom_toolbar.js") -Value $TB
  Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom.js")        -Value $JS
}

# ---- run flow ----
Write-Host "Stopping Uvicorn…" -ForegroundColor Yellow
Stop-Uvicorn

Write-Host "Backup current state…" -ForegroundColor Yellow
Backup-Now

if ($HARDRESET -and (Test-Path $RUNS)) {
  Write-Host "Hard reset enabled: archiving old runs (keep today) + clearing exports\latest" -ForegroundColor Yellow
  $today = Get-Date -Format "yyyy-MM-dd"
  Get-ChildItem $RUNS -Directory | Where-Object { $_.Name -ne $today } | ForEach-Object {
    $z = Join-Path $ARCH ("run_"+$_.Name+".zip")
    if (Test-Path $z) { Remove-Item $z -Force }
    Compress-Archive -Path (Join-Path $_.FullName "*") -DestinationPath $z -Force
    Remove-Item $_.FullName -Recurse -Force
  }
  $latest = Join-Path $EXPORT "latest"
  if (Test-Path $latest) { Remove-Item $latest -Recurse -Force }
}

Write-Host "Removing experimental UI…" -ForegroundColor Yellow
Clean-UI

Write-Host "Writing minimal UI…" -ForegroundColor Yellow
Write-Minimal-UI

Write-Host "Starting Uvicorn via $PY…" -ForegroundColor Yellow
Start-Uvicorn

# smoke test
try {
  $j = Invoke-RestMethod -Uri "$API/api/newsroom/plan" -TimeoutSec 10
  Write-Host "API OK – items:" ($j.items | Measure-Object | % Count) -ForegroundColor Green
} catch {
  Write-Warning "Smoke test failed: $($_.Exception.Message)  (If venv is required, ensure $VENV_PY exists.)"
}

Write-Host "`nCSV upload helper usage (PowerShell 5.x safe):" -ForegroundColor Cyan
@"
`$csv = 'D:\AISatyagrah\imports\newsroom.csv'
`$hdr = @{ 'x-auth' = '$($env:AUTH_TOKEN)' }
`$uri = '$API/api/newsroom/import_csv?date=&platform=telegram'  # blank date = latest
PS5-MultipartUpload -Uri `$uri -FilePath `$csv -Headers `$hdr
"@ | Write-Host

Write-Host "`nOpen UI: $API/ui/newsroom" -ForegroundColor Green

#Requires -Version 5.1
<#
Nuke & Rebuild to a clean baseline UI + helpers (safe for PS5.1).
- Kills Uvicorn
- Backs up UI and data
- Removes quickpanel/newsroom_more/embed/extra icons
- Writes minimal UI files (newsroom.html/.css/.js + toolbar)
- Restarts Uvicorn and smoke-tests
- Gives PS5-safe CSV upload + basic pipeline calls

Edit toggles below to taste.
#>

$ErrorActionPreference = "Stop"

# --- toggles ---
$HardReset   = $false              # $true => archive old runs (except today) and clear /exports/latest
$HostPort    = 9000
$Token       = $env:AUTH_TOKEN     # leave as-is; UI still shows a token box
$Date        = ""                  # blank = latest
$Platform    = "telegram"

# --- paths ---
$ROOT   = "D:\AISatyagrah"
$UI     = Join-Path $ROOT "ui"
$WEBPY  = Join-Path $ROOT "satyagrah\web\jobs_api.py"
$RUNS   = Join-Path $ROOT "data\runs"
$EXPORT = Join-Path $ROOT "exports"
$ARCH   = Join-Path $EXPORT "archive"
$BIN    = Join-Path $ROOT "scripts"

New-Item -ItemType Directory -Force -Path $BIN,$ARCH | Out-Null

# --- helpers ---
function Stop-Uvicorn {
  Get-Process -Name "python","uvicorn" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like "*AISatyagrah*" } |
    Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep 1
}

function Start-Uvicorn {
  Push-Location $ROOT
  $env:PYTHONUTF8="1"
  $cmd = "uvicorn satyagrah.web.jobs_api:create_app --factory --host 127.0.0.1 --port $HostPort --reload"
  Start-Process -WindowStyle Minimized -FilePath "powershell.exe" -ArgumentList "-NoLogo -NoProfile -Command `$env:PYTHONUTF8='1'; $cmd" -WorkingDirectory $ROOT
  Pop-Location
  Start-Sleep 2
}

function Zip-Dir($dir, $zipPath) {
  if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
  Compress-Archive -Path (Join-Path $dir "*") -DestinationPath $zipPath -Force
}

function Backup-Now {
  $ts = Get-Date -Format "yyyyMMdd_HHmmss"
  $bk = Join-Path $ARCH "backup_$ts.zip"
  $tmp = Join-Path $ARCH "tmp_$ts"
  New-Item -ItemType Directory -Force -Path $tmp | Out-Null
  Copy-Item $WEBPY $tmp -Force
  if (Test-Path $UI) { Copy-Item $UI $tmp -Recurse -Force }
  if (Test-Path $RUNS) { Copy-Item $RUNS $tmp -Recurse -Force }
  if (Test-Path $EXPORT) { Copy-Item $EXPORT $tmp -Recurse -Force }
  if (Test-Path $bk) { Remove-Item $bk -Force }
  Compress-Archive -Path (Join-Path $tmp "*") -DestinationPath $bk -Force
  Remove-Item $tmp -Recurse -Force
  Write-Host "Backup written to $bk"
}

function Clean-UI-Addons {
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

  # --- HTML ---
  $HTML = @'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>AISatyagrah — Newsroom</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <link rel="stylesheet" href="/ui-static/newsroom.css">
</head>
<body>
  <header id="toolbar">
    <input id="tb-token" placeholder="Toolbar token" />
    <select id="tb-platform">
      <option value="telegram" selected>telegram</option>
      <option value="instagram">instagram</option>
    </select>
    <button id="tb-approve">Approve All</button>
    <button id="tb-dryrun">Dry-Run</button>
    <button id="tb-publish">Publish (confirm)</button>
    <button id="tb-metrics">Metrics</button>
    <button id="tb-logs">Logs</button>
    <input id="tb-search" placeholder="search…" />
    <button id="tb-search-btn">Search</button>
  </header>

  <main class="container">
    <h1>AISatyagrah — Newsroom</h1>
    <div class="row">
      <label>Date <input id="date" placeholder="dd / mm / yyyy" /></label>
      <div class="nav">
        <button id="prev">⟨⟨</button>
        <button id="next">⟩⟩</button>
      </div>
      <label>Platform
        <select id="platform">
          <option value="telegram" selected>telegram</option>
          <option value="instagram">instagram</option>
        </select>
      </label>
      <button id="load">Load plan</button>
      <button id="latest">Latest telegram</button>
      <button id="fromcsv">⇢ Generate from CSV</button>
    </div>

    <div class="row toggles">
      <label><input type="checkbox" id="dryrun" checked /> Dry run (don’t send Telegram)</label>
      <label><input type="checkbox" id="skipig" /> Skip Instagram captions</label>
      <button id="run">Run pipeline</button>
      <button id="ig">✨ IG captions</button>
    </div>

    <div id="tabs">
      <button data-tab="all">All (0)</button>
      <button data-tab="draft">Draft (0)</button>
      <button data-tab="approved">Approved (0)</button>
      <button data-tab="sent">Sent (0)</button>
    </div>

    <section id="list"></section>
    <section>
      <label>x-auth token (optional) <input id="auth" /></label>
      <button id="save">Save</button>
    </section>
  </main>

  <script src="/ui-static/newsroom_toolbar.js"></script>
  <script src="/ui-static/newsroom.js"></script>
</body>
</html>
'@

  # --- CSS (minimal dark) ---
  $CSS = @'
:root{--bg:#0b0f1a;--ink:#e6e8f2;--mut:#a7aed3;--chip:#6f6bff;--chip2:#2e3354;--ok:#34d399;--warn:#f59e0b}
*{box-sizing:border-box} html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial}
.container{max-width:1200px;margin:24px auto;padding:0 16px}
header#toolbar{display:flex;gap:8px;align-items:center;padding:10px 12px;background:#0d1327;border-bottom:1px solid #232a49;position:sticky;top:0;z-index:10}
header input,select,button{background:#0e1224;color:var(--ink);border:1px solid #2a3250;border-radius:10px;padding:8px 12px}
header button{background:var(--chip);border:none}
h1{font-weight:700;letter-spacing:.5px}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0}
#tabs{display:flex;gap:10px;margin:16px 0}
#tabs button{background:#151a2b;color:var(--ink);border:1px solid #2a3250;border-radius:999px;padding:6px 12px}
.card{background:#0e1326;border:1px solid #232a49;border-radius:18px;padding:14px 16px;margin:12px 0;box-shadow:0 1px 0 rgba(0,0,0,.35)}
.badge{background:#16203a;border:1px solid #2a3250;border-radius:999px;padding:4px 8px;margin-right:8px;font-size:.85rem}
.badge.ok{background:rgba(52,211,153,.2);border-color:rgba(52,211,153,.45)}
.badge.warn{background:rgba(245,158,11,.2);border-color:rgba(245,158,11,.45)}
.mono{font-family:ui-monospace,Menlo,Monaco,Consolas,monospace}
'@

  # --- minimal toolbar JS (no experimental hooks) ---
  $TB = @'
(function(){
  const $ = (s)=>document.querySelector(s);
  function saveToken(){
    const t = $("#tb-token").value.trim();
    localStorage.setItem("xauth", t);
    $("#auth").value = t;
  }
  function loadToken(){
    const t = localStorage.getItem("xauth") || "";
    $("#tb-token").value = t; $("#auth").value = t;
  }
  function api(path, opts){
    const h = opts?.headers || {};
    const tok = localStorage.getItem("xauth")||"";
    if(tok) h["x-auth"]=tok;
    return fetch(path,{...opts,headers:h});
  }
  async function approveAll(){
    const d = $("#date").value.trim(); const p = $("#tb-platform").value;
    const r = await api(`/api/newsroom/approve_all?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}`,{method:"POST"});
    const j = await r.json(); alert(JSON.stringify(j));
  }
  async function dryRun(){
    const d = $("#date").value.trim(); const p = $("#tb-platform").value;
    const r = await api(`/api/newsroom/run?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}&dry_run=true`);
    const j = await r.json(); alert(JSON.stringify(j));
  }
  async function publishConfirm(){
    if(!confirm("Really publish (send)?")) return;
    const d = $("#date").value.trim(); const p = $("#tb-platform").value;
    const r = await api(`/api/newsroom/run?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}&dry_run=false`);
    const j = await r.json(); alert(JSON.stringify(j));
  }
  async function metrics(){ const r = await api("/api/newsroom/metrics?days=7"); const j = await r.json(); alert(JSON.stringify(j)); }
  async function logs(){
    const d = $("#date").value.trim();
    const r = await api(`/api/newsroom/logs?date=${encodeURIComponent(d)}&limit=100`);
    const j = await r.json(); alert(JSON.stringify(j));
  }

  $("#tb-approve").onclick = approveAll;
  $("#tb-dryrun").onclick = dryRun;
  $("#tb-publish").onclick = publishConfirm;
  $("#tb-metrics").onclick = metrics;
  $("#tb-logs").onclick = logs;
  $("#tb-search-btn").onclick = ()=>alert("Search is minimal in baseline; use the list filters.");

  $("#tb-token").addEventListener("change", saveToken);
  loadToken();
})();
'@

  # --- page JS (minimal list loader) ---
  $JS = @'
(function(){
  const $ = (s)=>document.querySelector(s);
  function tok(){ return localStorage.getItem("xauth")||""; }
  function api(p){ return fetch(p,{headers: tok()?{"x-auth":tok()}:undefined}); }

  async function loadPlan(){
    const d = $("#date").value.trim(); const p = $("#platform").value;
    const r = await api(`/api/newsroom/plan?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}`);
    const j = await r.json();
    renderList(j.items||[]);
    // update tabs
    $("#tabs [data-tab='all']").textContent = `All (${(j.items||[]).length})`;
    const draft = (j.items||[]).filter(x=>x.status==="draft").length;
    const appr  = (j.items||[]).filter(x=>x.status==="approved").length;
    const sent  = (j.items||[]).filter(x=>x.status==="sent").length;
    document.querySelector("#tabs [data-tab='draft']").textContent = `Draft (${draft})`;
    document.querySelector("#tabs [data-tab='approved']").textContent = `Approved (${appr})`;
    document.querySelector("#tabs [data-tab='sent']").textContent = `Sent (${sent})`;
  }

  function renderList(items){
    const root = $("#list"); root.innerHTML = "";
    for(const [i,it] of items.entries()){
      const card = document.createElement("div"); card.className="card";
      card.innerHTML = `
        <div class="row"><span class="badge ${it.status==='approved'?'ok':it.status==='draft'?'warn':''}">${it.status.toUpperCase()}</span>
        <span class="badge">${it.platform}</span></div>
        <h3>${it.title||"(no title)"} <small class="mono">${it.id||it.topic_id||""}</small></h3>
        <p>${it.snippet||""}</p>
        <div class="mono">${(it.hashtags||"").replaceAll("#","#<wbr>")}</div>
      `;
      root.appendChild(card);
    }
  }

  $("#load").onclick = loadPlan;
  $("#latest").onclick = ()=>{ $("#date").value=""; loadPlan(); };
  $("#fromcsv").onclick = ()=>alert("Use the PS helper to import CSV on Windows PowerShell 5.");

  $("#run").onclick = async ()=>{
    const d = $("#date").value.trim(); const p = $("#platform").value;
    const dry = $("#dryrun").checked; const skip = $("#skipig").checked;
    const q = `/api/newsroom/run?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}&dry_run=${dry}&skip_instagram=${skip}`;
    const r = await api(q); alert(await r.text()); loadPlan();
  };

  $("#ig").onclick = async ()=>{
    const d = $("#date").value.trim();
    const r = await api(`/api/newsroom/ig_captions?date=${encodeURIComponent(d)}&download=1`);
    if (r.status===204){ alert("No captions available."); return; }
    const blob = await r.blob();
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "instagram_captions.txt"; a.click();
  };

  // initial
  loadPlan();
})();
'@

  Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom.html") -Value $HTML
  Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom.css")  -Value $CSS
  Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom_toolbar.js") -Value $TB
  Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom.js")        -Value $JS
}

function PS5-MultipartUpload($Uri, [string]$FilePath, $Headers=@{}) {
  Add-Type -AssemblyName System.Net.Http
  $hc = [System.Net.Http.HttpClient]::new()
  foreach ($k in $Headers.Keys) { $hc.DefaultRequestHeaders.Add($k, [string]$Headers[$k]) }
  $mp = [System.Net.Http.MultipartFormDataContent]::new()
  $fs = [System.IO.File]::OpenRead($FilePath)
  $sc = [System.Net.Http.StreamContent]::new($fs)
  $cd = [System.Net.Http.Headers.ContentDispositionHeaderValue]::new("form-data")
  $cd.Name     = '"file"'
  $cd.FileName = '"' + [IO.Path]::GetFileName($FilePath) + '"'
  $sc.Headers.ContentDisposition = $cd
  $mp.Add($sc)
  $resp = $hc.PostAsync($Uri, $mp).Result
  $txt  = $resp.Content.ReadAsStringAsync().Result
  $fs.Dispose(); $mp.Dispose(); $hc.Dispose()
  return $txt
}

# ----------------- Execute -----------------
Write-Host "Stopping Uvicorn…" -ForegroundColor Yellow
Stop-Uvicorn

Write-Host "Backup current state…" -ForegroundColor Yellow
Backup-Now

if ($HardReset) {
  Write-Host "Hard reset: archiving old runs (keep today) + clearing exports\latest…" -ForegroundColor Yellow
  $today = (Get-Date -Format "yyyy-MM-dd")
  Get-ChildItem $RUNS -Directory | Where-Object { $_.Name -ne $today } | ForEach-Object {
    $zip = Join-Path $ARCH ("run_"+$_.Name+".zip")
    Zip-Dir $_.FullName $zip
    Remove-Item $_.FullName -Recurse -Force
  }
  $latest = Join-Path $EXPORT "latest"
  if (Test-Path $latest) { Remove-Item $latest -Recurse -Force }
}

Write-Host "Removing experimental UI add-ons…" -ForegroundColor Yellow
Clean-UI-Addons

Write-Host "Writing minimal UI…" -ForegroundColor Yellow
Write-Minimal-UI

Write-Host "Starting Uvicorn…" -ForegroundColor Yellow
Start-Uvicorn

# simple smoke
$API = "http://127.0.0.1:$HostPort"
Start-Sleep 1
try {
  $plan = Invoke-RestMethod -Uri "$API/api/newsroom/plan" -ErrorAction Stop
  Write-Host "API OK • items:" ($plan.items | Measure-Object | % Count)
} catch {
  Write-Warning "Smoke test failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "CSV upload helper (PS5-safe) usage example:" -ForegroundColor Cyan
@"
`$csv = 'D:\AISatyagrah\imports\newsroom.csv'
`$uri = '$API/api/newsroom/import_csv?date=$Date&platform=$Platform'
`$txt = PS5-MultipartUpload -Uri `$uri -FilePath `$csv -Headers @{ 'x-auth' = '$Token' }
`$txt
"@ | Write-Host

Write-Host ""
Write-Host "Open UI: http://127.0.0.1:$HostPort/ui/newsroom" -ForegroundColor Green

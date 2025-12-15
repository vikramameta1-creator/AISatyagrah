$ErrorActionPreference = "Stop"
$UI = "D:\AISatyagrah\ui"
New-Item -ItemType Directory -Force -Path $UI | Out-Null

# --- FULL CSS ---
$css = @'
/* --- More drawer / toolbar (AISatyagrah) --- */
#more-toolbar{display:flex;gap:.5rem;align-items:center;margin:.25rem 0 .5rem 0}
#more-btn{background:#6a63ff;color:#fff;border:0;border-radius:12px;padding:.55rem .9rem;font-weight:600;cursor:pointer}
#more-btn:hover{filter:brightness(1.1)}
#more-drawer{position:relative;background:#0e1224;border:1px solid #2a3250;border-radius:12px;padding:.9rem;display:none;margin:.5rem 0}
#more-drawer.open{display:block}
#more-drawer h4{margin:.25rem 0 .35rem 0;font-weight:700;color:#e6e8f2}
#more-drawer .row{display:grid;grid-template-columns:180px 1fr auto;gap:.5rem;align-items:center;margin:.3rem 0}
#more-drawer .row.small{grid-template-columns:180px auto auto auto}
#more-drawer input[type="text"],
#more-drawer input[type="search"],
#more-drawer input[type="file"],
#more-drawer select,
#more-drawer textarea{background:#0b0f1e;color:#e6e8f2;border:1px solid #2a3250;border-radius:10px;padding:.5rem}
#more-drawer textarea{min-height:60px}
#more-drawer .pill{background:#756bff;color:#fff;border:0;border-radius:10px;padding:.45rem .8rem;cursor:pointer}
#more-drawer .pill.warn{background:#ff6565}
#more-drawer .pill.ghost{background:#293152}
#more-drawer .right{justify-self:end}
#more-drawer .muted{opacity:.7}
#more-drawer pre{background:#0b0f1e;border:1px solid #2a3250;border-radius:10px;padding:.6rem;max-height:280px;overflow:auto;color:#c9cdf3}
#more-drawer .hint{font-size:.85rem;opacity:.8}
.badge{display:inline-block;background:#293152;color:#cfd3ff;border-radius:999px;padding:.1rem .6rem;margin-left:.3rem}
'@
Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom_more.css") -Value $css

# --- FULL JS (NO <script> WRAPPER) ---
$js = @'
(() => {
  const $ = (sel, el=document) => el.querySelector(sel);
  const API = "/api/newsroom";
  const ui = {
    tokenInput: () => document.querySelector('input[name="x-auth"]') || $("#token") || $('[placeholder="x-auth token (optional)"]'),
    dateInput : () => document.querySelector('input[type="date"]') || $("#date") || $('[aria-label="date"]'),
    platform  : () => document.querySelector('select#platform, select[name=platform]') || $("#platform"),
    toast(msg){ console.log("[newsroom_more]", msg); const el = document.createElement("div"); el.textContent = msg; el.style.cssText="position:fixed;right:12px;bottom:12px;background:#293152;color:#fff;padding:.6rem .8rem;border-radius:10px;z-index:9999"; document.body.appendChild(el); setTimeout(()=>el.remove(),1800); }
  };
  const authHeader = () => { const t = ui.tokenInput()?.value?.trim(); return t ? {"x-auth":t} : {}; };
  const pickDate   = () => (ui.dateInput()?.value || "").trim();
  const pickPlat   = () => (ui.platform()?.value || "telegram");

  async function api(path, {method="GET", json, form, blob} = {}) {
    const headers = {...authHeader()};
    let body;
    if (json!==undefined) { headers["Content-Type"]="application/json"; body = JSON.stringify(json); }
    if (form!==undefined) { body = form; }
    const res = await fetch(`${API}${path}`, {method, headers, body});
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return blob ? res.blob() : res.json();
  }
  function dlBlob(blob, name){ const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href), 5000); }

  function injectUI(){
    const header = document.querySelector("h1, .page-title, header") || document.body.firstElementChild;
    const bar = document.createElement("div");
    bar.id = "more-toolbar";
    bar.innerHTML = `<button id="more-btn">More ▾</button><span class="muted">Quick actions<span class="badge">10</span></span>`;
    header?.insertAdjacentElement("afterend", bar);

    const drawer = document.createElement("div");
    drawer.id = "more-drawer";
    drawer.innerHTML = `
      <div class="row small"><h4>Bulk actions</h4>
        <span class="hint">Date defaults to latest run • Platform uses current dropdown</span>
        <button class="pill right" id="btn-refresh">Refresh plan</button>
      </div>
      <div class="row">
        <label>Approve by search</label>
        <input id="approve-query" type="search" placeholder="title/snippet/hashtags contains…">
        <button class="pill right" id="btn-approve-filter">Approve</button>
      </div>
      <div class="row">
        <label>Send now (IDs)</label>
        <input id="send-ids" type="text" placeholder="t1,t2,t5">
        <div class="right"><label class="muted"><input type="checkbox" id="send-dry" checked> dry-run</label><button class="pill" id="btn-send-now">Send</button></div>
      </div>
      <div class="row">
        <label>Split-run</label>
        <div>
          <select id="split-target"><option value="telegram">telegram only</option><option value="instagram">instagram only</option></select>
          <label class="muted"><input type="checkbox" id="split-dry" checked> dry-run</label>
        </div>
        <button class="pill right" id="btn-split-run">Run</button>
      </div>
      <div class="row">
        <label>Undo status</label>
        <input id="undo-id" type="text" placeholder="id (e.g., t3)">
        <button class="pill ghost right" id="btn-undo">Undo</button>
      </div>
      <div class="row">
        <label>Import CSV</label>
        <input id="csv-file" type="file" accept=".csv">
        <button class="pill right" id="btn-import">Upload</button>
      </div>
      <div class="row">
        <label>Presets</label>
        <div>
          <input id="preset-name" type="text" placeholder="name (baseline)">
          <textarea id="preset-tags" placeholder="#india #delhi … (optional when applying)"></textarea>
          <div class="hint">Add: name + hashtags • Apply/Delete: name only</div>
        </div>
        <div class="right">
          <button class="pill" id="btn-preset-add">Add</button>
          <button class="pill" id="btn-preset-apply">Apply</button>
          <button class="pill ghost" id="btn-preset-del">Delete</button>
        </div>
      </div>
      <div class="row small">
        <label>Images audit</label>
        <button class="pill" id="btn-images">Check</button>
        <button class="pill" id="btn-ig">Download IG captions</button>
      </div>
      <div class="row small">
        <label>Test mode</label>
        <label class="muted"><input type="checkbox" id="test-mode"> enabled</label>
        <button class="pill warn" id="btn-testmode-save">Save</button>
      </div>
      <div class="row"><label>Output</label><pre id="more-out" class="span"></pre></div>
    `;
    bar.insertAdjacentElement("afterend", drawer);
    $("#more-btn").onclick = ()=> drawer.classList.toggle("open");
    return { out: $("#more-out") };
  }

  const { out } = injectUI();
  const show = (obj)=>{ out.textContent = (typeof obj==="string") ? obj : JSON.stringify(obj,null,2); };

  async function plan(){ return api(`/plan?date=${encodeURIComponent(pickDate())}`); }
  $("#btn-refresh").onclick = async ()=>{ show(await plan()); };

  $("#btn-approve-filter").onclick = async ()=>{
    const q = $("#approve-query").value.trim();
    show(await api("/approve_filter",{method:"POST", json:{date:pickDate(), platform:pickPlat(), query:q}}));
  };

  $("#btn-send-now").onclick = async ()=>{
    const ids = $("#send-ids").value.split(",").map(s=>s.trim()).filter(Boolean);
    show(await api("/send_now",{method:"POST", json:{date:pickDate(), platform:pickPlat(), ids, dry_run: $("#send-dry").checked}}));
  };

  $("#btn-split-run").onclick = async ()=>{
    show(await api("/run_split",{method:"POST", json:{date:pickDate(), target:$("#split-target").value, dry_run: $("#split-dry").checked, confirm:false}}));
  };

  $("#btn-undo").onclick = async ()=>{
    const id = $("#undo-id").value.trim();
    show(await api("/undo",{method:"POST", json:{date:pickDate(), id}}));
  };

  $("#btn-import").onclick = async ()=>{
    const f = $("#csv-file").files[0]; if(!f){ show("Pick a CSV"); return; }
    const fd = new FormData(); fd.append("file", f); fd.append("date", pickDate()); fd.append("platform", pickPlat());
    const res = await fetch(`${API}/import_csv`, {method:"POST", headers: authHeader(), body: fd});
    show(await res.json());
  };

  $("#btn-preset-add").onclick = async ()=>{
    show(await api("/presets",{method:"POST", json:{name:$("#preset-name").value.trim(), platform:pickPlat(), hashtags:$("#preset-tags").value.trim()}}));
  };
  $("#btn-preset-apply").onclick = async ()=>{
    const name = encodeURIComponent($("#preset-name").value.trim());
    const d = encodeURIComponent(pickDate()); const p = encodeURIComponent(pickPlat());
    const r = await fetch(`${API}/presets/apply?date=${d}&platform=${p}&name=${name}`, {method:"POST", headers: authHeader()});
    show(await r.json());
  };
  $("#btn-preset-del").onclick = async ()=>{
    const name = encodeURIComponent($("#preset-name").value.trim());
    const p = encodeURIComponent(pickPlat());
    const r = await fetch(`${API}/presets?name=${name}&platform=${p}`, {method:"DELETE", headers: authHeader()});
    show(await r.json());
  };

  $("#btn-images").onclick = async ()=>{
    const d = encodeURIComponent(pickDate()); const p = encodeURIComponent(pickPlat());
    show(await api(`/images?date=${d}&platform=${p}`));
  };

  $("#btn-ig").onclick = async ()=>{
    const d = encodeURIComponent(pickDate());
    const blob = await api(`/ig_captions?date=${d}`, {blob:true});
    dlBlob(blob, `instagram_captions_${pickDate()||"latest"}.txt`);
  };

  $("#btn-testmode-save").onclick = async ()=>{
    show(await api("/test_mode",{method:"POST", json:{enabled: $("#test-mode").checked}}));
  };
})();
'@
Set-Content -Encoding UTF8 -Path (Join-Path $UI "newsroom_more.js") -Value $js

# --- Favicon (SVG + copy to .ico to stop 404s) ---
$svg = @'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0e1224"/><circle cx="32" cy="32" r="14" fill="#756bff"/></svg>'@
Set-Content -Encoding UTF8 -Path (Join-Path $UI "favicon.svg") -Value $svg
Copy-Item -Path (Join-Path $UI "favicon.svg") -Destination (Join-Path $UI "favicon.ico") -Force

# --- Verify files ---
Get-ChildItem -Path (Join-Path $UI '*') -Include 'newsroom_more.css','newsroom_more.js','favicon.svg','favicon.ico' -File |
  Format-Table Name,Length

# --- Inject tags into newsroom.html (safe insert, no -replace) ---
$htmlPath = Join-Path $UI 'newsroom.html'
if (Test-Path $htmlPath) {
  $html = Get-Content $htmlPath -Raw
  $needCss = ($html -notmatch 'newsroom_more\.css')
  $needJs  = ($html -notmatch 'newsroom_more\.js')
  $needFav = ($html -notmatch 'favicon\.(ico|svg)')

  if ($needCss -or $needJs -or $needFav) {
    $inserts = @()
    if ($needFav) { $inserts += '<link rel="icon" href="/ui-static/favicon.svg" />' }
    if ($needCss) { $inserts += '<link rel="stylesheet" href="/ui-static/newsroom_more.css" />' }
    if ($needJs)  { $inserts += '<script defer src="/ui-static/newsroom_more.js"></script>' }
    $needle = '</body>'
    $idx = [cultureinfo]::InvariantCulture.CompareInfo.LastIndexOf($html, $needle, [System.Globalization.CompareOptions]::IgnoreCase)
    if ($idx -ge 0) {
      $patched = $html.Substring(0,$idx) + ($inserts -join "`r`n") + "`r`n" + $html.Substring($idx)
      Set-Content -Path $htmlPath -Encoding UTF8 -Value $patched
      Write-Host "Injected assets into newsroom.html"
    } else {
      Write-Warning "Could not find </body>; skipping inline injection. You can add the three tags manually."
    }
  } else {
    Write-Host "newsroom.html already references the More UI assets."
  }
} else {
  Write-Warning "newsroom.html not found; UI will still work if you add the three tags to your template."
}

Write-Host "Done. Press Ctrl+F5 on /ui/newsroom."

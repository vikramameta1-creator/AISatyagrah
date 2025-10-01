$web = "D:\AISatyagrah\saty_web.py"
if (-not (Test-Path $web)) { throw "Not found: $web" }

# Backup
Copy-Item $web "$web.bak_$(Get-Date -Format yyyyMMdd_HHmmss)" -Force
$t = Get-Content -Raw -Encoding UTF8 $web

# --- A) Add keyframes once (before the FIRST </style>) ---
if ($t -notmatch 'keyframes\s+pulse') {
  $parts = $t -split '</style>', 2
  if ($parts.Count -eq 2) {
    $anim = @"
  @keyframes pulse { 0%{opacity:.2} 50%{opacity:1} 100%{opacity:.2} }
"@
    $t = $parts[0] + $anim + "</style>" + $parts[1]
  }
}

# --- B) Add the "Running..." badge after the title in HOME html (id=busyBadge) ---
if ($t -notmatch 'id="busyBadge"') {
  $badge = @'
$1
    <div id="busyBadge" style="display:none; font-size:12px; color:#a0a8b0; margin-top:4px;">
      <span class="dot" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#6ea8fe;margin-right:6px;animation:pulse 1s infinite;"></span>
      Running...
    </div>
'@
  $rx = New-Object System.Text.RegularExpressions.Regex '<h1>__TITLE__</h1>'
  $t = $rx.Replace($t, $badge, 1)
}

# --- C) Ensure we have setBusy() and it toggles the badge + disables buttons ---
$setBusyDesired = @'
function setBusy(v){
  busy = v;
  try { _allBtns().forEach(b => b.disabled = v); } catch(e){}
  try {
    var bb = document.getElementById("busyBadge");
    if(bb){ bb.style.display = v ? "block" : "none"; }
  } catch(e){}
  document.body.classList.toggle("busy", v);
}
'@

if ($t -match 'function\s+setBusy\(') {
  $pattern = '(?s)function\s+setBusy\([^\)]*\)\s*\{.*?\}'
  $t = [System.Text.RegularExpressions.Regex]::Replace($t, $pattern, $setBusyDesired)
} else {
  # Insert helper near the UI script top (just after the first 'let busy = false;')
  if ($t -match 'let busy = false;') {
    $inject = @'
let busy = false;
  const _allBtns = () => Array.from(document.querySelectorAll("button.btn"));
'@ + "`r`n" + $setBusyDesired
    $t = $t -replace 'let busy = false;', [System.Text.RegularExpressions.Regex]::Escape('let busy = false;')
    $t = $t -replace [System.Text.RegularExpressions.Regex]::Escape('let busy = false;'), $inject
  }
}

# --- D) Make existing calls use setBusy(true/false) (idempotent) ---
$t = [regex]::Replace($t, '\bbusy\s*=\s*true;',  'setBusy(true);')
$t = [regex]::Replace($t, '\bbusy\s*=\s*false;', 'setBusy(false);')

# Save
Set-Content -Path $web -Value $t -Encoding UTF8
Write-Host "Patched $web. Restart the web UI to load changes."

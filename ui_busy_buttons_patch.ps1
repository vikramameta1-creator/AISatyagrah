$web = "D:\AISatyagrah\saty_web.py"
if (-not (Test-Path $web)) { throw "Not found: $web" }

# Backup
Copy-Item $web "$web.bak_$(Get-Date -Format yyyyMMdd_HHmmss)" -Force
$t = Get-Content -Raw -Encoding UTF8 $web

# Inject setBusy() helper right after 'let busy = false;' (only if not already present)
if ($t -notmatch 'function setBusy\(') {
  $inject = @"
let busy = false;
  const _allBtns = () => Array.from(document.querySelectorAll("button.btn"));
  function setBusy(v){
    busy = v;
    try { _allBtns().forEach(b => b.disabled = v); } catch(e){}
    document.body.classList.toggle("busy", v);
  }
"@
  $t = $t -replace 'let busy = false;', [System.Text.RegularExpressions.Regex]::Escape('let busy = false;')
  $t = $t -replace [System.Text.RegularExpressions.Regex]::Escape('let busy = false;'), $inject
}

# Turn all 'busy = true/false;' into setBusy(true/false);
$t = [regex]::Replace($t, '\bbusy\s*=\s*true;',  'setBusy(true);')
$t = [regex]::Replace($t, '\bbusy\s*=\s*false;', 'setBusy(false);')

# Save
Set-Content -Path $web -Value $t -Encoding UTF8
Write-Host "Patched $web. Restart the web UI to load changes."

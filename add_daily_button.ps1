param(
  [string]$Web = "D:\AISatyagrah\saty_web.py"
)

if (-not (Test-Path $Web)) { throw "Not found: $Web" }

# Backup
Copy-Item $Web "$Web.bak_$(Get-Date -Format yyyyMMdd_HHmmss)"

# Load file
$t = Get-Content $Web -Raw

# --- 1) Insert the "Daily" button before the Quick button (if not present) ---
if ($t -notmatch 'onclick="dailyRun\(\)"') {
  $replacement = "        <button class=""btn primary"" onclick=""dailyRun()"">Daily</button>`r`n" + '$1'
  $t = [regex]::Replace(
    $t,
    '(?m)^\s*(<button class="btn" onclick="quick\(\)">Quick</button>\s*)$',
    $replacement
  )
}

# --- 2) Append the dailyRun() function before </script> (if not present) ---
if ($t -notmatch 'function dailyRun\(\)') {
$dailyJs = @'
  async function dailyRun(){
    if(busy){ append("\n[busy] Wait for current task to finish...\n"); return; }
    try{
      busy = true;
      append("\n=== Daily run ===\n");
      await run(['doctor','--strict']);
      await run(['research','--date', val('date')]);
      await run(['triage','--date', val('date')]);

      const b = ['batch','--date', val('date'),'--seed', String(val('seed'))];
      const raw = (val('indices')||'').trim();
      if(raw){ b.push('--indices', raw); } else { b.push('--top', String(val('top')||'3')); }
      const lang = val('lang'); if(lang) b.push('--lang', lang);
      const aspect = val('aspect'); if(aspect && aspect !== 'all') b.push('--aspect', aspect);
      if(checked('skip_image')) b.push('--skip_image');
      if(checked('package')) b.push('--package');
      if(checked('saveas')) b.push('--saveas');
      await run(b);

      const platforms=['instagram','instagram-stories','x','shorts','youtube','whatsapp','telegram'];
      const aspectMap={instagram:'1x1','instagram-stories':'9x16',x:'4x5',shorts:'9x16',youtube:'1x1',whatsapp:'1x1',telegram:'1x1'};
      const top = Number(String(val('top')||'3'));
      const lang2 = (val('lang')||'en');

      for(let i=1;i<=top;i++){
        const tid = 't'+i;
        for(const p of platforms){
          const img = aspectMap[p] || '';
          const a = ['publish','--date', val('date'),'--id', tid,'--lang', lang2];
          if(img) a.push('--image', img);
          a.push('--platform', p, '--csv');
          await run(a);
        }
      }

      append("\n$ zip outbox\n");
      try{
        const res = await fetch("/api/zip_outbox", {
          method:"POST", headers:{"content-type":"application/json"},
          body: JSON.stringify({date: val("date")})
        });
        append(await res.text());
      } catch(e){ append("\n[warn] zip_outbox failed: " + e + "\n"); }

      await openOutbox();
    } finally {
      busy = false;
    }
  }
'@

  $t = [regex]::Replace(
    $t,
    '</script>\s*</body>\s*</html>\s*$',
    [regex]::Escape($dailyJs) + "`r`n</script>`r`n</body>`r`n</html>"
  )
}

# Save
Set-Content -Encoding UTF8 $Web $t
Write-Host "Patched $Web"

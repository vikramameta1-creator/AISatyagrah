# -*- coding: utf-8 -*-
import re, pathlib
p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8").replace("`r`n", "\r\n")

m = re.search(r'^(?P<indent>\s*)if getattr\(\s*args,\s*"dry_run",\s*False\)\s*:\s*$', s, flags=re.M)
if not m:
    print("dry_run block not found; no changes."); exit()

indent = m.group("indent")
snippet = (
    f"{indent}if getattr(args, \"dry_run\", False):\n"
    f"{indent}    preview = (caption[:60]).replace(\"\\n\", \" / \")\n"
    f"{indent}    print(f\"[DRY] sendPhoto chat={{chat_id}} file={{img}} caption={{preview}}...\")\n"
    f"{indent}    sent += 1\n"
    f"{indent}    count += 1\n"
    f"{indent}    continue\n"
)

pattern = re.compile(
    rf'^{re.escape(indent)}if getattr\(\s*args,\s*"dry_run",\s*False\)\s*:\s*\n'
    r'(?:.*\n)*?'
    rf'^{re.escape(indent)}\s*continue\s*$', re.M)

s2, n = pattern.subn(snippet, s, count=1)
if n == 0:
    # fallback: just ensure the preview line is correct
    s2 = re.sub(r'preview\s*=\s*\(caption\[:60\]\)\.replace\([^\n]*',
                f'{indent}preview = (caption[:60]).replace("\\n", " / ")', s, count=1)

p.write_text(s2, encoding="utf-8")
print("telegram DRY block normalized.")

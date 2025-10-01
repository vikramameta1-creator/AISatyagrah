# -*- coding: utf-8 -*-
import re, pathlib
p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")

def fix_line(text):
    out = []
    changed = False
    for line in text.splitlines(True):
        m = re.match(r'^(\s*)rows\s*=\s*doctor_run\(', line)
        if m:
            indent = m.group(1)
            out.append(f'{indent}rows = doctor_run(host, fix=getattr(args, "fix", False))\n')
            changed = True
        else:
            out.append(line)
    return ''.join(out), changed

s, changed = fix_line(s)
p.write_text(s, encoding="utf-8")
print("Patched rows=doctor_run(...) line." if changed else "No change needed.")

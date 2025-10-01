# -*- coding: utf-8 -*-
import re, pathlib
p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")

# normalize any literal `r`n artifacts just in case
s = s.replace("`r`n", "\r\n")

# fix the exact doctor_run call with an extra ')'
s = re.sub(
    r'doctor_run\(\s*host\s*,\s*fix=getattr\(\s*args\s*,\s*"fix"\s*,\s*False\s*\)\)\)',
    r'doctor_run(host, fix=getattr(args, "fix", False))',
    s
)

# safety: if somehow "rows = doctor_run(host...))" exists, drop one ')'
s = re.sub(r'(rows\s*=\s*doctor_run\([^\)]*\))\)', r'\1', s)

p.write_text(s, encoding="utf-8")
print("Fixed unmatched parenthesis in doctor_run call.")

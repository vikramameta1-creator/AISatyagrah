# -*- coding: utf-8 -*-
import re, pathlib

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")

# normalize any literal `r`n artifacts
s = s.replace("`r`n", "\r\n")

# limit edits to cmd_batch body
m = re.search(r'^def\s+cmd_batch\(\s*args\s*\):', s, flags=re.M)
if m:
    start = m.end()
    nxt = re.search(r'^\s*def\s+\w+\(', s[start:], flags=re.M)
    end = start + (nxt.start() if nxt else len(s) - start)
    body = s[start:end]

    # insert a newline before cmd_socialcsv(ns) if it was glued to the closing ')'
    body2 = re.sub(r'\)\s*cmd_socialcsv\(ns\)', ')\n            cmd_socialcsv(ns)', body)
    if body2 != body:
        s = s[:start] + body2 + s[end:]

p.write_text(s, encoding="utf-8")
print("Fixed newline before cmd_socialcsv(ns) inside cmd_batch.")

# -*- coding: utf-8 -*-
import re, pathlib
p = pathlib.Path(r"satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# A) add --fix flag to the doctor subparser (right after --host or before set_defaults)
s = re.sub(
    r'(d\s*=\s*sub\.add_parser\("doctor"[^)]*\)\s*\n(?:.*?\n)*?\s*d\.add_argument\("--host"[^)]*\)\s*\n)',
    r'\1    d.add_argument("--strict", action="store_true")\n    d.add_argument("--fix", action="store_true")\n',
    s,
    flags=re.S,
)

# B) pass fix into doctor_run(host, fix=...)
s = re.sub(
    r'rows\s*=\s*doctor_run\(\s*host\s*\)',
    r'rows = doctor_run(host, fix=getattr(args, "fix", False))',
    s,
)

if s != orig:
    p.write_text(s, encoding="utf-8")
    print("cli.py doctor patched.")
else:
    print("cli.py did not need changes.")

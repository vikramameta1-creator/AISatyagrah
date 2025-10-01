# -*- coding: utf-8 -*-
import re, pathlib
p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# A) normalize any literal `r`n into real CRLF
s = s.replace("`r`n", "\r\n")

# B) nuke ALL prior strict/fix lines (dedupe)
s = re.sub(r"^\s*d\.add_argument\(\"--strict\"[^\n]*\)\s*\r?\n", "", s, flags=re.M)
s = re.sub(r"^\s*d\.add_argument\(\"--fix\"[^\n]*\)\s*\r?\n", "", s, flags=re.M)

# C) ensure we pass fix into doctor_run(...)
s = re.sub(
    r"rows\s*=\s*doctor_run\(\s*host\s*(?:,\s*fix\s*=\s*[^)]*)?\)",
    r"rows = doctor_run(host, fix=getattr(args, \"fix\", False))",
    s,
    count=1
)

# D) insert the clean flags exactly once right after the doctor --host line
s = re.sub(
    r"(d\.add_argument\(\"--host\"[^\n]*\)\s*\r?\n)",
    r"\1    d.add_argument(\"--strict\", action=\"store_true\")\r\n    d.add_argument(\"--fix\", action=\"store_true\")\r\n",
    s,
    count=1
)

if s != orig:
    p.write_text(s, encoding="utf-8")
    print("cli.py doctor block cleaned.")
else:
    print("cli.py did not need changes.")

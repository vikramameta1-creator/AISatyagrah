# -*- coding: utf-8 -*-
import re, pathlib

p = pathlib.Path(r"satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# A) normalize literal `r`n -> real newlines
s = s.replace("`r`n", "\r\n")

# B) ensure import is present
if "from .doctor import run as doctor_run" not in s:
    s = re.sub(
        r"(^\s*from\s+\.\s*config\s+import[^\n]*\n)",
        r"\1from .doctor import run as doctor_run\n",
        s,
        count=1,
        flags=re.M
    )

# C) remove any prior doctor --strict/--fix lines to avoid duplicates
s = re.sub(r"^\s*d\.add_argument\([\"']--strict[\"'][^\n]*\)\s*\r?\n", "", s, flags=re.M)
s = re.sub(r"^\s*d\.add_argument\([\"']--fix[\"'][^\n]*\)\s*\r?\n", "", s, flags=re.M)

# D) insert clean flags once, right after doctor --host
s = re.sub(
    r"(d\.add_argument\([\"']--host[\"'][^\n]*\)\s*\r?\n)",
    r"\1    d.add_argument(\"--strict\", action=\"store_true\")\r\n"
    r"    d.add_argument(\"--fix\", action=\"store_true\")\r\n",
    s,
    count=1
)

# E) make sure the call passes fix=... exactly once
s = re.sub(
    r"rows\s*=\s*doctor_run\(\s*host\s*(?:,\s*fix\s*=\s*[^)]*)?\)",
    r"rows = doctor_run(host, fix=getattr(args, \"fix\", False))",
    s,
    count=1
)

# F) unescape any accidental backslash-escaped quotes on the two add_argument lines
s = s.replace('d.add_argument(\\"--strict\\"', 'd.add_argument("--strict"')
s = s.replace('d.add_argument(\\"--fix\\"', 'd.add_argument("--fix"')

if s != orig:
    p.write_text(s, encoding="utf-8")
    print("cli.py doctor block cleaned.")
else:
    print("cli.py did not need changes.")

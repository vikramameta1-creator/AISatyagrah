# -*- coding: utf-8 -*-
import re, pathlib
p = pathlib.Path(r"satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# A) turn literal `r`n into real CRLF
s = s.replace("`r`n", "\r\n")

# B) unglue the specific init -> research line if stuck
s = s.replace(
    "initp.set_defaults(func=cmd_init)r = sub.add_parser(",
    "initp.set_defaults(func=cmd_init)\r\n\r\n    r = sub.add_parser("
)

# C) unglue the doctor strict line if stuck
s = re.sub(
    r'd\.add_argument\("--strict", action="store_true"\)\s*d\.set_defaults\(func=cmd_doctor\)',
    'd.add_argument("--strict", action="store_true")\r\n    d.set_defaults(func=cmd_doctor)',
    s
)

# D) generic safety: split any other glued ")\n<var> = sub.add_parser("
s = re.sub(
    r'\)\s*([A-Za-z_]\w*)\s*=\s*sub\.add_parser\(',
    r')\r\n\r\n    \1 = sub.add_parser(',
    s
)

if s != orig:
    p.write_text(s, encoding="utf-8", newline="")
    print("cli.py patched.")
else:
    print("cli.py did not need patching.")

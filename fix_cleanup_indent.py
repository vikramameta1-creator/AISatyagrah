# -*- coding: utf-8 -*-
import re, pathlib

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8").replace("`r`n", "\r\n")
orig = s

# determine the standard indent used for subparsers (e.g., '    ')
m_std = re.search(r'^(\s*)\w+\s*=\s*sub\.add_parser\(', s, flags=re.M)
std = m_std.group(1) if m_std else "    "

# find existing cleanup block
m = re.search(r'^(\s*)(\w+)\s*=\s*sub\.add_parser\(\s*["\']cleanup["\'][^\n]*\)\s*[\s\S]*?^\s*\2\.set_defaults\(\s*func=cmd_cleanup\s*\)',
              s, flags=re.M)
clean = (
    f'{std}cl = sub.add_parser("cleanup", help="Delete old runs/exports, keep last N")\r\n'
    f'{std}cl.add_argument("--keep", type=int, default=14)\r\n'
    f'{std}cl.set_defaults(func=cmd_cleanup)'
)

if m:
    # replace the whole block with canonical indentation
    s = s[:m.start()] + clean + s[m.end():]
else:
    # insert before the extras end marker, or after socialcsv/publish if needed
    inserted = False
    s2 = re.sub(r"(\#\s*----\s*end extras\s*----)", clean + "\r\n\r\n" + r"\1", s, count=1, flags=re.S)
    if s2 != s:
        s = s2; inserted = True
    if not inserted and 'add_parser("socialcsv"' in s:
        s = re.sub(r'(sc\.set_defaults\(func=cmd_socialcsv\)\s*)', r'\1' + "\r\n" + clean + "\r\n", s, count=1, flags=re.S)
    if not inserted and 'add_parser("publish"' in s:
        s = re.sub(r'(pb\.set_defaults\(func=cmd_publish\)\s*)', r'\1' + "\r\n" + clean + "\r\n", s, count=1, flags=re.S)

if s != orig:
    p.write_text(s, encoding="utf-8")
    print("cleanup subparser normalized.")
else:
    print("No changes needed.")

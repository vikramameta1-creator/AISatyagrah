# -*- coding: utf-8 -*-
import re, pathlib

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# Normalize any literal `r`n from past patches
s = s.replace("`r`n", "\r\n")

# Remove any stray duplicated doctor flags anywhere (safe: other subparsers don't use variable "d")
s = re.sub(r'^\s*d\.add_argument\("--(?:strict|fix|hint)".*?\)\s*\r?\n', "", s, flags=re.M)

# Find the doctor subparser block:  <indent><var>=sub.add_parser("doctor"... ) ... <indent><var>.set_defaults(func=cmd_doctor)
m = re.search(
    r'^(\s*)(\w+)\s*=\s*sub\.add_parser\(\s*["\']doctor["\'][^\n]*\)\s*[\s\S]*?^\s*\2\.set_defaults\(\s*func=cmd_doctor\s*\)',
    s, flags=re.M
)
if not m:
    print("ERROR: doctor subparser block not found."); raise SystemExit(1)

indent, var = m.group(1), m.group(2)

# Build a clean, correctly-indented block
clean = (
    f'{indent}{var} = sub.add_parser("doctor", help="Environment checks")\r\n'
    f'{indent}{var}.add_argument("--host", default=None, help="SD API host (overrides settings)")\r\n'
    f'{indent}{var}.add_argument("--strict", action="store_true", help="Exit 2 on any failed check")\r\n'
    f'{indent}{var}.add_argument("--fix", action="store_true", help="Auto-create/migrate common issues")\r\n'
    f'{indent}{var}.add_argument("--hint", action="store_true", help="Print mock server command if SD is down")\r\n'
    f'{indent}{var}.set_defaults(func=cmd_doctor)'
)

# Replace the whole original doctor block with the clean one
s = s[:m.start()] + clean + s[m.end():]

# Ensure the call passes fix= once
s = re.sub(
    r'rows\s*=\s*doctor_run\(\s*host[^\)]*\)',
    'rows = doctor_run(host, fix=getattr(args, "fix", False))',
    s
)

p.write_text(s, encoding="utf-8")
print("doctor subparser reset.")

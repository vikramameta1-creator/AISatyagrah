# -*- coding: utf-8 -*-
import re, pathlib

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")

# find the doctor subparser block:  d = sub.add_parser("doctor" ... ) ... d.set_defaults(func=cmd_doctor)
m = re.search(r'^(\s*)(\w+)\s*=\s*sub\.add_parser\(["\']doctor["\'][^\n]*\)\s*[\s\S]*?^\s*\2\.set_defaults\(func=cmd_doctor\)',
              s, flags=re.M)
if not m:
    print("doctor block not found"); raise SystemExit(1)

indent, var = m.group(1), m.group(2)
block = s[m.start():m.end()]

# remove ANY prior --strict/--fix/--hint lines inside the block
block = re.sub(r'^\s*'+re.escape(var)+r'\.add_argument\(["\']--(?:strict|fix|hint)["\'][^\n]*\)\s*\r?\n',
               '', block, flags=re.M)

# insert clean flags exactly once right AFTER the --host line if present; else after the first add_argument
host = re.search(r'^\s*'+re.escape(var)+r'\.add_argument\(["\']--host["\'][^\n]*\)\s*\r?\n', block, flags=re.M)
if host:
    ins = host.end()
else:
    first = re.search(r'^\s*'+re.escape(var)+r'\.add_argument\(', block, flags=re.M)
    ins = first.end() if first else block.find('\n')+1

flags_txt = (f'{indent}    {var}.add_argument("--strict", action="store_true")\n'
             f'{indent}    {var}.add_argument("--fix", action="store_true")\n'
             f'{indent}    {var}.add_argument("--hint", action="store_true")\n')
block = block[:ins] + flags_txt + block[ins:]

# normalize the call to pass fix= once
block = re.sub(r'rows\s*=\s*doctor_run\(\s*host[^\)]*\)',
               'rows = doctor_run(host, fix=getattr(args, "fix", False))',
               block)

# write back
s = s[:m.start()] + block + s[m.end():]
p.write_text(s, encoding="utf-8")
print("doctor flags deduped inside block.")

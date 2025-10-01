# -*- coding: utf-8 -*-
import pathlib, re, sys

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8").replace("`r`n", "\r\n")

# 1) locate cmd_telegram function body
m_fun = re.search(r'^def\s+cmd_telegram\s*\(\s*args\s*\)\s*:\s*$', s, flags=re.M)
if not m_fun:
    print("cmd_telegram not found"); sys.exit(1)
fs = m_fun.end()
m_next = re.search(r'^\s*def\s+\w+\s*\(', s[fs:], flags=re.M)
fe = fs + (m_next.start() if m_next else len(s) - fs)
body = s[fs:fe]

# 2) find the "if getattr(args, \"dry_run\", False):" line
m_dry = re.search(r'^(\s*)if\s+getattr\(\s*args,\s*"dry_run",\s*False\)\s*:\s*$', body, flags=re.M)
if not m_dry:
    print("dry_run block start not found"); sys.exit(1)
indent = m_dry.group(1)
start = m_dry.start()

# 3) find end of that indented block: first line whose indent <= parent indent (or end)
lines = body.splitlines(True)
# compute line index of start
pos = 0
idx = 0
while idx < len(lines) and pos + len(lines[idx]) <= start:
    pos += len(lines[idx]); idx += 1

# consume the "if ..." line itself
block_start_idx = idx
idx += 1

def leading_ws(t): 
    return re.match(r'^\s*', t).group(0)

parent_len = len(indent)
while idx < len(lines):
    cur = lines[idx]
    if cur.strip() == "":
        idx += 1
        continue
    if len(leading_ws(cur)) <= parent_len:
        break
    idx += 1

block_end_idx = idx  # slice end (not inclusive)

# 4) build clean DRY block
snippet = (
    f"{indent}if getattr(args, \"dry_run\", False):\n"
    f"{indent}    txt = caption.replace(\"\\r\\n\", \"\\n\").replace(\"\\r\", \"\\n\")\n"
    f"{indent}    preview = \" / \".join(txt.split(\"\\n\"))[:60]\n"
    f"{indent}    print(f\"[DRY] sendPhoto chat={{chat_id}} file={{img}} caption={{preview}}...\")\n"
    f"{indent}    sent += 1\n"
    f"{indent}    count += 1\n"
    f"{indent}    continue\n"
)

# 5) replace and write back
new_body = "".join(lines[:block_start_idx]) + snippet + "".join(lines[block_end_idx:])
s_fixed = s[:fs] + new_body + s[fe:]
p.write_text(s_fixed, encoding="utf-8")
print("cmd_telegram DRY block replaced.")

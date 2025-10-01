# -*- coding: utf-8 -*-
import re, pathlib

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8").replace("`r`n", "\r\n")

# 1) Find cmd_telegram
m_fun = re.search(r'^def\s+cmd_telegram\s*\(\s*args\s*\)\s*:\s*$', s, flags=re.M)
if not m_fun:
    print("cmd_telegram not found; aborting.")
    raise SystemExit(1)

fun_start = m_fun.end()
# Find next def to mark function end
m_next = re.search(r'^\s*def\s+\w+\s*\(', s[fun_start:], flags=re.M)
fun_end = fun_start + (m_next.start() if m_next else len(s) - fun_start)
body = s[fun_start:fun_end]

# 2) Locate the dry_run 'if' line and its indentation
m_dry = re.search(r'^(\s*)if\s+getattr\(\s*args,\s*"dry_run",\s*False\)\s*:\s*$', body, flags=re.M)
if not m_dry:
    print("dry_run block not found; aborting.")
    raise SystemExit(1)

indent = m_dry.group(1)
dry_start = m_dry.start()

# 3) Find the matching 'continue' that ends the DRY block (first 'continue' after the if)
m_cont = re.search(rf'^{re.escape(indent)}\s*continue\s*$', body[m_dry.end():], flags=re.M)
if not m_cont:
    print("No 'continue' after dry_run; aborting.")
    raise SystemExit(1)
dry_end = m_dry.end() + m_cont.end()

# 4) Build a clean replacement block (no tricky backslashes inside f-string exprs)
snippet = (
    f"{indent}if getattr(args, \"dry_run\", False):\n"
    f"{indent}    txt = caption.replace(\"\\r\\n\", \"\\n\").replace(\"\\r\", \"\\n\")\n"
    f"{indent}    preview = \" / \".join(txt.split(\"\\n\"))[:60]\n"
    f"{indent}    print(f\"[DRY] sendPhoto chat={{chat_id}} file={{img}} caption={{preview}}...\")\n"
    f"{indent}    sent += 1\n"
    f"{indent}    count += 1\n"
    f"{indent}    continue\n"
)

# 5) Replace and write back
new_body = body[:dry_start] + snippet + body[dry_end:]
s_fixed = s[:fun_start] + new_body + s[fun_end:]
p.write_text(s_fixed, encoding="utf-8")
print("cmd_telegram dry-run block replaced cleanly.")

# -*- coding: utf-8 -*-
import pathlib, re, sys

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8").replace("`r`n", "\r\n")

# 1) Locate def cmd_telegram(...) function body
m_fun = re.search(r'^def\s+cmd_telegram\s*\(\s*args\s*\)\s*:\s*$', s, flags=re.M)
if not m_fun:
    print("ERROR: cmd_telegram not found"); sys.exit(1)

fun_start = m_fun.end()
m_next = re.search(r'^\s*def\s+\w+\s*\(', s[fun_start:], flags=re.M)
fun_end = fun_start + (m_next.start() if m_next else len(s) - fun_start)
body = s[fun_start:fun_end]

# 2) Find the dry-run IF line and its indent inside the function
m_dry = re.search(r'^(\s*)if\s+getattr\(\s*args,\s*"dry_run",\s*False\)\s*:\s*$', body, flags=re.M)
if not m_dry:
    print("ERROR: dry_run IF not found in cmd_telegram"); sys.exit(1)

indent = m_dry.group(1)
dry_if_start = m_dry.start()

# 3) Find the end of the dry-run block.
# Prefer the first "continue" at the same indent. If missing (file was corrupted),
# fall back to first URL or sending block start at same indent.
m_continue = re.search(rf'^{re.escape(indent)}continue\s*$', body[m_dry.end():], flags=re.M)
if m_continue:
    dry_end = m_dry.end() + m_continue.end()
else:
    # fallback markers (url/name/files lines at same indent)
    m_url   = re.search(rf'^{re.escape(indent)}url\s*=\s*f?["\']https?://', body[m_dry.end():], flags=re.M)
    m_name  = re.search(rf'^{re.escape(indent)}name\s*=\s*pathlib\.Path\(', body[m_dry.end():], flags=re.M)
    m_files = re.search(rf'^{re.escape(indent)}files\s*=\s*\{{', body[m_dry.end():], flags=re.M)
    cand = [m for m in (m_url, m_name, m_files) if m]
    if not cand:
        # Last fallback: end of function body
        dry_end = len(body)
    else:
        dry_end = m_dry.end() + min(m.start() for m in cand)

# 4) Clean replacement: compute preview safely, no backslashes inside f-string exprs
snippet = (
    f"{indent}if getattr(args, \"dry_run\", False):\n"
    f"{indent}    txt = caption.replace(\"\\r\\n\", \"\\n\").replace(\"\\r\", \"\\n\")\n"
    f"{indent}    preview = \" / \".join(txt.split(\"\\n\"))[:60]\n"
    f"{indent}    print(f\"[DRY] sendPhoto chat={{chat_id}} file={{img}} caption={{preview}}...\")\n"
    f"{indent}    sent += 1\n"
    f"{indent}    count += 1\n"
    f"{indent}    continue\n"
)

new_body = body[:dry_if_start] + snippet + body[dry_end:]
s_fixed = s[:fun_start] + new_body + s[fun_end:]

p.write_text(s_fixed, encoding="utf-8")
print("cmd_telegram dry-run block replaced.")

# -*- coding: utf-8 -*-
import pathlib, re

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")

# Normalize any literal `r`n from previous patches
s = s.replace("`r`n", "\r\n")

# Replace the DRY print that has .replace('\n', ...) inside an f-string
lines = s.splitlines(True)
out, changed = [], False
for i, line in enumerate(lines):
    if "[DRY] sendPhoto" in line and "caption=" in line and "replace(" in line:
        indent = re.match(r"^(\s*)", line).group(1)
        # Insert a preview line first
        out.append(indent + "preview = (caption[:60]).replace(\"\\n\", \" / \")\n")
        # Then print with the precomputed preview
        out.append(indent + "print(f\"[DRY] sendPhoto chat={chat_id} file={img} caption={preview}...\")\n")
        changed = True
    else:
        out.append(line)

if changed:
    p.write_text("".join(out), encoding="utf-8")
    print("Patched DRY print to avoid backslashes in f-string expressions.")
else:
    print("No change needed (pattern not found).")

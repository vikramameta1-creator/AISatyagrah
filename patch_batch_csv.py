# -*- coding: utf-8 -*-
import re, pathlib, argparse

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# 1) Add --csv and --lang to the batch subparser (dedupe first)
s = re.sub(r'^\s*b\.add_argument\(["\']--csv["\'][^\n]*\)\s*\r?\n', "", s, flags=re.M)
s = re.sub(r'^\s*b\.add_argument\(["\']--lang["\'][^\n]*\)\s*\r?\n', "", s, flags=re.M)
s = re.sub(
    r'(b\.set_defaults\(\s*func=cmd_batch\s*\))',
    'b.add_argument("--csv", action="store_true", help="Write social.csv after batch")\n'
    '    b.add_argument("--lang", default="en,hi", help="Languages for CSV (e.g., en or en,hi)")\n'
    r'    \1',
    s,
    count=1
)

# 2) Inject CSV write at the end of cmd_batch(args)
m = re.search(r'^def\s+cmd_batch\(\s*args\s*\):', s, flags=re.M)
if m:
    start = m.end()
    nxt = re.search(r'^\s*def\s+\w+\(', s[start:], flags=re.M)
    end = start + (nxt.start() if nxt else len(s) - start)

    body = s[start:end]
    if "cmd_socialcsv(ns)" not in body:
        # append snippet before the function ends, respecting 4-space indent
        snippet = (
            "\n"
            "    # write social.csv if requested\n"
            "    if getattr(args, \"csv\", False):\n"
            "        try:\n"
            "            ns = argparse.Namespace(\n"
            "                date=date,\n"
            "                aspect=getattr(args, \"aspect\", \"all\") or \"all\",\n"
            "                lang=getattr(args, \"lang\", \"en,hi\"),\n"
            "                out=str((ROOT / \"exports\" / date) / \"social.csv\"),\n"
            "            )\n"
            "            cmd_socialcsv(ns)\n"
            "        except SystemExit:\n"
            "            pass\n"
        )
        body = body.rstrip() + snippet + "\n"
        s = s[:start] + body + s[end:]

p.write_text(s, encoding="utf-8")
print("batch --csv installed.")

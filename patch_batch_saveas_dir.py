# -*- coding: utf-8 -*-
import re, pathlib, argparse, os, textwrap

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# 1) Add --saveas-dir to the batch subparser (dedupe first)
s = re.sub(r'^\s*b\.add_argument\(["\']--saveas-dir["\'][^\n]*\)\s*\r?\n', "", s, flags=re.M)
s = re.sub(
    r'(b\.add_argument\(["\']--lang["\'][^\n]*\)\s*\r?\n\s*b\.set_defaults\(func=cmd_batch\))',
    r'b.add_argument("--saveas-dir", default=None, help="Subfolder under exports/<date> for saved copies (e.g., outbox)")'+"\n"+r'    \1',
    s, count=1
)

# 2) Inject copy-to-outdir code inside cmd_batch, after each quick run
m = re.search(r'^def\s+cmd_batch\(\s*args\s*\):', s, flags=re.M)
if m:
    start = m.end()
    nxt = re.search(r'^\s*def\s+\w+\(', s[start:], flags=re.M)
    end = start + (nxt.start() if nxt else len(s) - start)
    body = s[start:end]

    if "## _batch_saveas_outdir_copy" not in body:
        snippet = """
    ## _batch_saveas_outdir_copy
    # If a save-as dir was requested, copy per-topic outputs there
    if getattr(args, "saveas", False) and getattr(args, "saveas_dir", None):
        outdir = (ROOT / "exports" / date / args.saveas_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        exp = ROOT / "exports" / date
        aspects = ["4x5","1x1","9x16"] if (getattr(args, "aspect", "all") or "all").lower()=="all" else [args.aspect]
        copied = []
        # images
        for a in aspects:
            for ext in ("png","jpg"):
                src = exp / f"onepager_{a}.{ext}"
                if src.exists():
                    dst = outdir / f"{topic_id}_{a}.{ext}"
                    dst.write_bytes(src.read_bytes()); copied.append(dst)
        # captions
        langs = [x.strip() for x in (getattr(args, "lang", "en,hi") or "en,hi").split(",") if x.strip()]
        for lg in langs:
            src = exp / f"caption_{lg}.txt"
            if src.exists():
                dst = outdir / f"{topic_id}_caption_{lg}.txt"
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8"); copied.append(dst)
        if copied:
            print(f"Saved copies for {topic_id} in {outdir}")
"""
        # append snippet near the end of the per-item loop by placing it before the function end
        body = body.rstrip() + snippet + "\n"
        s = s[:start] + body + s[end:]

# 3) If CSV is requested, and a saveas-dir exists, also write CSV into that folder (keeps things together)
s = re.sub(
    r'ns\s*=\s*argparse\.Namespace\(\s*date=date,\s*aspect=getattr\(args,\s*"aspect",\s*"all"\)[\s\S]*?out=str\(\(ROOT\s*/\s*"exports"\s*/\s*date\)\s*/\s*"social\.csv"\)\s*,\s*\)\s*',
    r'ns = argparse.Namespace(date=date, aspect=getattr(args, "aspect", "all") or "all", '
    r'lang=getattr(args, "lang", "en,hi"), '
    r'out=str(((ROOT / "exports" / date / args.saveas_dir) if getattr(args,"saveas_dir",None) else (ROOT / "exports" / date)) / "social.csv"), '
    r')',
    s, count=1
)

if s != orig:
    p.write_text(s, encoding="utf-8")
    print("batch --saveas-dir installed.")
else:
    print("No changes needed.")

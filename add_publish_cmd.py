# -*- coding: utf-8 -*-
import pathlib, argparse, re

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# 1) append cmd_publish if missing
if "def cmd_publish(" not in s:
    s += r"""

def cmd_publish(args):
    date = _resolve_date(getattr(args, "date", None))
    topic_id = getattr(args, "id", "auto")
    try:
        topic_id = resolve_topic_id(date, topic_id)
    except Exception:
        if topic_id == "auto":
            topic_id = "t1"

    exp = ROOT / "exports" / date
    outdir = pathlib.Path(getattr(args, "to", "") or (exp / "outbox"))
    outdir.mkdir(parents=True, exist_ok=True)

    # choose aspects
    aspects = ["4x5","1x1","9x16"] if (getattr(args, "aspect", "all") or "all").lower()=="all" else [args.aspect]

    copied = []
    # images -> <topic_id>_<aspect>.<ext>
    for a in aspects:
        for ext in ("png","jpg"):
            src = exp / f"onepager_{a}.{ext}"
            if src.exists():
                dst = outdir / f"{topic_id}_{a}.{ext}"
                dst.write_bytes(src.read_bytes()); copied.append(dst)

    # captions -> <topic_id>_caption_<lang>.txt
    langs = [x.strip() for x in (getattr(args, "lang", "en") or "en").split(",") if x.strip()]
    for lg in langs:
        src = exp / f"caption_{lg}.txt"
        if src.exists():
            dst = outdir / f"{topic_id}_caption_{lg}.txt"
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8"); copied.append(dst)

    # optional CSV alongside
    if getattr(args, "csv", False):
        try:
            ns = argparse.Namespace(date=date, aspect=getattr(args,"aspect","all") or "all",
                                    lang=",".join(langs), out=str(outdir/"social.csv"))
            cmd_socialcsv(ns)
        except SystemExit:
            pass

    if copied:
        print("Publish -> " + " | ".join(str(p) for p in copied))
    print(f"Ready in -> {outdir}")
"""

# 2) register the subcommand under the "extras" block
if 'add_parser("publish"' not in s:
    s = re.sub(
        r"(\#\s*----\s*end extras\s*----)",
        r"""
    # publish
    pb = sub.add_parser("publish", help="Copy exports to an outbox with stable names")
    pb.add_argument("--id", default="auto")
    pb.add_argument("--date", default=None, help="YYYY-MM-DD or 'latest'")
    pb.add_argument("--aspect", default="all", help="4x5|1x1|9x16|all")
    pb.add_argument("--lang", default="en", help="e.g., en or en,hi")
    pb.add_argument("--to", default=None, help="Destination folder (defaults to exports/<date>/outbox)")
    pb.add_argument("--csv", action="store_true", help="Also write social.csv next to files")
    pb.set_defaults(func=cmd_publish)

\g<1>""",
        s, count=1, flags=re.S
    )

if s != orig:
    p.write_text(s, encoding="utf-8")
    print("publish command installed.")
else:
    print("No changes needed.")

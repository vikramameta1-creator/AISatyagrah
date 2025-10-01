# -*- coding: utf-8 -*-
import re, pathlib

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# A) Append the telegram command if missing
if "def cmd_telegram(" not in s:
    s += r"""

def cmd_telegram(args):
    import os, csv, time, requests, argparse, pathlib
    date = _resolve_date(getattr(args, "date", None))
    exp  = ROOT / "exports" / date
    csv_path = exp / "social.csv"
    # auto-create CSV if missing
    if not csv_path.exists():
        try:
            ns = argparse.Namespace(date=date,
                                    aspect=getattr(args, "aspect", "all") or "all",
                                    lang=getattr(args, "lang", "en,hi"),
                                    out=str(csv_path))
            cmd_socialcsv(ns)
        except SystemExit:
            pass

    if not csv_path.exists():
        print(f"No social.csv found at {csv_path}. Run socialcsv or batch --csv."); return 2

    token = os.environ.get("SATYAGRAH_TELEGRAM_BOT")
    if not token:
        print("Missing env SATYAGRAH_TELEGRAM_BOT"); return 2
    chat_id = getattr(args, "chat", None)
    if not chat_id:
        print("Provide --chat <CHAT_ID>"); return 2

    # language preference
    langs = [x.strip() for x in (getattr(args, "lang", "en,hi") or "en,hi").split(",") if x.strip()]

    sent = 0; skipped = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            img = row.get("jpg_path") or row.get("png_path") or ""
            if not img or not pathlib.Path(img).exists():
                skipped += 1; continue
            # pick caption by preferred lang
            caption = ""
            for lg in langs:
                key = f"caption_{lg}"
                if row.get(key):
                    caption = row[key]
                    break
            if not caption:
                caption = row.get("caption_en","") or ""

            if getattr(args, "dry_run", False):
                print(f"[DRY] sendPhoto chat={chat_id} file={img} caption={caption[:60].replace('\\n',' / ')}...")
                sent += 1
                continue

            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(img, "rb") as fh:
                files = {"photo": (pathlib.Path(img).name, fh, "image/jpeg")}
                data = {"chat_id": chat_id, "caption": caption}
                try:
                    resp = requests.post(url, data=data, files=files, timeout=30)
                    if resp.ok:
                        sent += 1
                        print(f"Sent -> {img}")
                        time.sleep(1.0)  # gentle rate limit
                    else:
                        print(f"[ERR] {resp.status_code} {resp.text[:120]}")
                except Exception as e:
                    print(f"[ERR] {e}")
    print(f"Done. sent={sent}, skipped={skipped}")
"""

# B) Register the subparser (under extras) if missing
if 'add_parser("telegram"' not in s:
    s = re.sub(
        r"(\#\s*----\s*end extras\s*----)",
        r"""
    # telegram
    tg = sub.add_parser("telegram", help="Send social.csv images+captions to Telegram")
    tg.add_argument("--date", default=None, help="YYYY-MM-DD or 'latest'")
    tg.add_argument("--aspect", default="all", help="4x5|1x1|9x16|all (for CSV auto-gen)")
    tg.add_argument("--lang", default="en,hi", help="Caption language preference, e.g., en or en,hi")
    tg.add_argument("--chat", default=None, help="Telegram chat_id to send to")
    tg.add_argument("--dry-run", action="store_true", help="Print what would be sent")
    tg.set_defaults(func=cmd_telegram)

\g<1>""",
        s, count=1, flags=re.S
    )

if s != orig:
    p.write_text(s, encoding="utf-8")
    print("telegram command installed.")
else:
    print("No changes needed.")

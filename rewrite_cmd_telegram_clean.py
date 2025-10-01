# -*- coding: utf-8 -*-
import re, pathlib

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8").replace("`r`n", "\r\n")

# find start of def cmd_telegram(...):
m = re.search(r'(?m)^([ \t]*)def\s+cmd_telegram\s*\(.*?\):', s)
if not m:
    print("cmd_telegram start not found; aborting."); raise SystemExit(1)

indent = m.group(1)
start = m.start()

# find the end of the function = next top-level def
m2 = re.search(r'(?m)^([ \t]*)def\s+\w+\s*\(', s[m.end():])
end = m.end() + (m2.start() if m2 else len(s)-m.end())

# clean replacement function (robust DRY preview, MIME, aspect, limit, delay)
func = """def cmd_telegram(args):
    import os, csv, time, requests, argparse, pathlib
    date = _resolve_date(getattr(args, "date", None))
    exp  = ROOT / "exports" / date
    csv_path = exp / "social.csv"
    # auto-create CSV if missing
    if not csv_path.exists():
        try:
            ns = argparse.Namespace(
                date=date,
                aspect=(getattr(args, "aspect", "all") or "all"),
                lang=getattr(args, "lang", "en,hi"),
                out=str(csv_path),
            )
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

    langs = [x.strip() for x in (getattr(args, "lang", "en,hi") or "en,hi").split(",") if x.strip()]

    # read CSV and optionally filter aspect
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    aspect = (getattr(args, "aspect", "all") or "all").lower()
    if aspect != "all":
        rows = [row for row in rows if row.get("aspect","").lower() == aspect]

    limit = getattr(args, "limit", None)
    try:
        limit = int(limit) if limit is not None else None
    except Exception:
        limit = None

    delay = float(getattr(args, "delay", 1.0) or 1.0)

    sent = 0; skipped = 0; count = 0
    for row in rows:
        if limit is not None and count >= limit:
            break

        img = row.get("jpg_path") or row.get("png_path") or ""
        if not img or not pathlib.Path(img).exists():
            skipped += 1; continue

        # pick caption by preferred lang
        caption = ""
        for lg in langs:
            key = f"caption_{lg}"
            if row.get(key):
                caption = row[key]; break
        if not caption:
            caption = row.get("caption_en","") or ""

        if getattr(args, "dry_run", False):
            # precompute preview safely (no backslashes in f-string expression)
            txt = caption.replace("\\r\\n","\\n").replace("\\r","\\n")
            preview = " / ".join(txt.split("\\n"))[:60]
            print(f"[DRY] sendPhoto chat={chat_id} file={img} caption={preview}...")
            sent += 1; count += 1
            continue

        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        name = pathlib.Path(img).name
        lower = name.lower()
        mime = "image/jpeg" if lower.endswith((".jpg",".jpeg")) else "image/png"

        try:
            with open(img, "rb") as fh:
                files = {"photo": (name, fh, mime)}
                data = {"chat_id": chat_id, "caption": caption}
                resp = requests.post(url, data=data, files=files, timeout=30)
            if resp.ok:
                sent += 1; count += 1
                print(f"Sent -> {img}")
                time.sleep(delay)
            else:
                print(f"[ERR] {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            print(f"[ERR] {e}")

    print(f"Done. sent={sent}, skipped={skipped}")
"""

# re-indent the function to match original indent
func_indented = "".join((indent + ln) if ln.strip() else ln for ln in func.splitlines(True))

# stitch back
s2 = s[:start] + func_indented + s[end:]
p.write_text(s2, encoding="utf-8")
print("cmd_telegram replaced cleanly.")

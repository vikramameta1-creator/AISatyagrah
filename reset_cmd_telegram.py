# -*- coding: utf-8 -*-
import re, pathlib

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8").replace("`r`n", "\r\n")
orig = s

# -----------------------------
# A) Replace the whole cmd_telegram() with a clean version
# -----------------------------
func_lines = [
"def cmd_telegram(args):",
"    import os, csv, time, requests, argparse, pathlib",
"    date = _resolve_date(getattr(args, \"date\", None))",
"    exp  = ROOT / \"exports\" / date",
"    csv_path = exp / \"social.csv\"",
"    # auto-create CSV if missing",
"    if not csv_path.exists():",
"        try:",
"            ns = argparse.Namespace(",
"                date=date,",
"                aspect=(getattr(args, \"aspect\", \"all\") or \"all\"),",
"                lang=getattr(args, \"lang\", \"en,hi\"),",
"                out=str(csv_path),",
"            )",
"            cmd_socialcsv(ns)",
"        except SystemExit:",
"            pass",
"    if not csv_path.exists():",
"        print(f\"No social.csv found at {csv_path}. Run socialcsv or batch --csv.\"); return 2",
"    token = os.environ.get(\"SATYAGRAH_TELEGRAM_BOT\")",
"    if not token:",
"        print(\"Missing env SATYAGRAH_TELEGRAM_BOT\"); return 2",
"    chat_id = getattr(args, \"chat\", None)",
"    if not chat_id:",
"        print(\"Provide --chat <CHAT_ID>\"); return 2",
"    langs = [x.strip() for x in (getattr(args, \"lang\", \"en,hi\") or \"en,hi\").split(\",\") if x.strip()]",
"",
"    # read CSV and optionally filter aspect",
"    with open(csv_path, newline=\"\", encoding=\"utf-8\") as f:",
"        rows = list(csv.DictReader(f))",
"    aspect = (getattr(args, \"aspect\", \"all\") or \"all\").lower()",
"    if aspect != \"all\":",
"        rows = [row for row in rows if row.get(\"aspect\", \"\").lower() == aspect]",
"    limit = getattr(args, \"limit\", None)",
"    try:",
"        limit = int(limit) if limit is not None else None",
"    except Exception:",
"        limit = None",
"    delay = float(getattr(args, \"delay\", 1.0) or 1.0)",
"",
"    sent = 0; skipped = 0; count = 0",
"    for row in rows:",
"        if limit is not None and count >= limit:",
"            break",
"        img = row.get(\"jpg_path\") or row.get(\"png_path\") or \"\"",
"        if not img or not pathlib.Path(img).exists():",
"            skipped += 1; continue",
"        # pick caption",
"        caption = \"\"",
"        for lg in langs:",
"            key = f\"caption_{lg}\"",
"            if row.get(key):",
"                caption = row[key]; break",
"        if not caption:",
"            caption = row.get(\"caption_en\", \"\") or \"\"",
"",
"        if getattr(args, \"dry_run\", False):",
"            # precompute preview safely (no backslashes in f-string expr)",
"            txt = caption.replace(\"\\r\\n\", \"\\n\").replace(\"\\r\", \"\\n\")",
"            preview = \" / \".join(txt.split(\"\\n\"))[:60]",
"            print(f\"[DRY] sendPhoto chat={chat_id} file={img} caption={preview}...\")",
"            sent += 1; count += 1",
"            continue",
"",
"        url = f\"https://api.telegram.org/bot{token}/sendPhoto\"",
"        name = pathlib.Path(img).name",
"        lower = name.lower()",
"        mime = \"image/jpeg\" if lower.endswith((\".jpg\", \".jpeg\")) else \"image/png\"",
"        try:",
"            with open(img, \"rb\") as fh:",
"                files = {\"photo\": (name, fh, mime)}",
"                data = {\"chat_id\": chat_id, \"caption\": caption}",
"                resp = requests.post(url, data=data, files=files, timeout=30)",
"            if resp.ok:",
"                sent += 1; count += 1",
"                print(f\"Sent -> {img}\")",
"                time.sleep(delay)",
"            else:",
"                print(f\"[ERR] {resp.status_code} {resp.text[:200]}\")",
"        except Exception as e:",
"            print(f\"[ERR] {e}\")",
"    print(f\"Done. sent={sent}, skipped={skipped}\")",
]
func = \"\\r\\n\".join(func_lines) + \"\\r\\n\"

# remove existing cmd_telegram (if any)
s = re.sub(r'^def\\s+cmd_telegram\\s*\\(.*?^def\\s+\\w+\\s*\\(', '<<TELEGRAM_FUNC>>\\r\\n', s, flags=re.M|re.S)
if '<<TELEGRAM_FUNC>>' in s:
    # find where marker landed; we need to reinsert function before the next def
    s = s.replace('<<TELEGRAM_FUNC>>\\r\\n', func)
else:
    # append at end if not found
    if not s.endswith(\"\\r\\n\"): s += \"\\r\\n\"
    s += func

# -----------------------------
# B) Ensure telegram subparser exists with all flags
# -----------------------------
# Remove any existing telegram subparser block (best effort)
s = re.sub(r'(?ms)^\\s*\\w+\\s*=\\s*sub\\.add_parser\\(\\s*[\"\\']telegram[\"\\'][^\\n]*\\)\\s*.*?^\\s*\\w+\\.set_defaults\\(\\s*func=cmd_telegram\\s*\\)\\s*', '', s)

sub_block = [
"    # telegram",
"    tg = sub.add_parser(\"telegram\", help=\"Send social.csv images+captions to Telegram\")",
"    tg.add_argument(\"--date\", default=None, help=\"YYYY-MM-DD or 'latest'\")",
"    tg.add_argument(\"--aspect\", default=\"all\", help=\"4x5|1x1|9x16|all (filter and CSV auto-gen)\")",
"    tg.add_argument(\"--lang\", default=\"en,hi\", help=\"Caption language preference, e.g., en or en,hi\")",
"    tg.add_argument(\"--chat\", default=None, help=\"Telegram chat_id to send to\")",
"    tg.add_argument(\"--dry-run\", action=\"store_true\", help=\"Print what would be sent\")",
"    tg.add_argument(\"--limit\", type=int, default=None, help=\"Send only the first N rows\")",
"    tg.add_argument(\"--delay\", type=float, default=1.0, help=\"Seconds to sleep between sends\")",
"    tg.set_defaults(func=cmd_telegram)",
]
sub_txt = \"\\r\\n\".join(sub_block) + \"\\r\\n\"

# Insert before extras end marker if present, else after publish block, else at end of parser setup
if re.search(r'\\#\\s*----\\s*end extras\\s*----', s):
    s = re.sub(r'(\\#\\s*----\\s*end extras\\s*----)', sub_txt + '\\r\\n' + r\"\\1\", s, count=1, flags=re.S)
elif 'add_parser(\"publish\"' in s:
    s = re.sub(r'(pb\\.set_defaults\\(func=cmd_publish\\)\\s*)', r\"\\1\" + sub_txt, s, count=1, flags=re.S)
else:
    # last resort: add near other subparsers
    s = re.sub(r'(sub\\s*=\\s*parser\\.add_subparsers\\([^\\)]*\\)[^\\n]*\\n)', r\"\\1\" + sub_txt, s, count=1, flags=re.S)

if s != orig:
    p.write_text(s, encoding=\"utf-8\")
    print(\"cmd_telegram replaced and subparser ensured.\")
else:
    print(\"No changes applied (already clean).\")

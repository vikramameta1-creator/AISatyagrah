# -*- coding: utf-8 -*-
import pathlib, re

p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8").replace("`r`n", "\r\n")
orig = s

# A) Add --limit and --delay to the telegram subparser (idempotent)
s = re.sub(r'^\s*tg\.add_argument\(["\']--limit["\'][^\n]*\)\s*\r?\n', "", s, flags=re.M)
s = re.sub(r'^\s*tg\.add_argument\(["\']--delay["\'][^\n]*\)\s*\r?\n', "", s, flags=re.M)
s = re.sub(
    r'(tg\.add_argument\(["\']--dry-run["\'][^\n]*\)\s*\r?\n\s*tg\.set_defaults\(func=cmd_telegram\))',
    'tg.add_argument("--limit", type=int, default=None, help="Send only the first N rows")\n'
    '    tg.add_argument("--delay", type=float, default=1.0, help="Seconds to sleep between sends")\n'
    r'    \1',
    s, count=1
)

# B) Enhance cmd_telegram logic (idempotent transforms)
if "def cmd_telegram(" in s:
    # 1) Filter rows by aspect if requested (beyond CSV auto-gen)
    s = re.sub(
        r'with open\(csv_path[^\)]*\) as f:\s*\r?\n\s*r\s*=\s*csv\.DictReader\(f\)\s*\r?\n\s*for row in r:',
        'with open(csv_path, newline="", encoding="utf-8") as f:\n'
        '        r = list(csv.DictReader(f))\n'
        '        # optional aspect filter (in case CSV has multiple aspects)\n'
        '        aspect = (getattr(args, "aspect", "all") or "all").lower()\n'
        '        if aspect != "all":\n'
        '            r = [row for row in r if row.get("aspect","").lower()==aspect]\n'
        '        count = 0\n'
        '        for row in r:',
        s, count=1
    )

    # 2) Respect --limit
    s = re.sub(
        r'for row in r:\s*\r?\n',
        'for row in r:\n'
        '            if getattr(args, "limit", None) is not None and count >= int(args.limit):\n'
        '                break\n',
        s, count=1
    )

    # 3) Choose MIME by extension and use configurable delay
    s = re.sub(
        r'files\s*=\s*\{"photo":\s*\(pathlib\.Path\(img\)\.name,\s*fh,\s*"image/jpeg"\)\s*\)\}',
        'name = pathlib.Path(img).name\n'
        '                    lower = name.lower()\n'
        '                    mime = "image/jpeg" if lower.endswith((".jpg",".jpeg")) else "image/png"\n'
        '                    files = {"photo": (name, fh, mime)}',
        s, count=1
    )
    s = re.sub(
        r'time\.sleep\(\s*1\.0\s*\)',
        'time.sleep(float(getattr(args, "delay", 1.0)))',
        s, count=1
    )

    # 4) Increment count when we actually send or dry-run
    s = re.sub(
        r'if getattr\(args,\s*"dry_run",\s*False\):\s*\r?\n\s*preview.*?\r?\n\s*print\(f"\[DRY\].*?"\)\s*\r?\n\s*sent \+= 1',
        'if getattr(args, "dry_run", False):\n'
        '                preview = (caption[:60]).replace("\\n", " / ")\n'
        '                print(f"[DRY] sendPhoto chat={chat_id} file={img} caption={preview}...")\n'
        '                sent += 1\n'
        '                count += 1',
        s, flags=re.S, count=1
    )
    s = re.sub(
        r'if resp\.ok:\s*\r?\n\s*sent \+= 1',
        'if resp.ok:\n'
        '                        sent += 1\n'
        '                        count += 1',
        s, count=1
    )

if s != orig:
    p.write_text(s, encoding="utf-8")
    print("telegram enhanced: MIME, aspect filter, --limit, --delay.")
else:
    print("No changes needed.")

	#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI: Post images + caption to Telegram from the outbox.
Reads token/chat_id from satyagrah creds store.

Usage examples:
  python -m satyagrah.adapters.telegram_post --date latest --id t13
  python -m satyagrah.adapters.telegram_post --date 2025-09-20 --id t13 --album --max 4
"""

from __future__ import annotations
import argparse, json, os, sys, re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

try:
    # shipped with your project
    from satyagrah.secrets import get_secret
except Exception:
    get_secret = None  # fallback later

ROOT = Path(os.environ.get("SATY_ROOT") or Path(__file__).resolve().parents[2])

# ---------------- helpers ----------------

def escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )

def trim_caption(s: str, limit: int = 1024) -> str:
    s = s.strip()
    if len(s) <= limit:
        return s
    return s[:limit-1] + "…"

def latest_date_with_outbox(root: Path) -> str:
    exports = root / "exports"
    if not exports.exists():
        return ""
    dates = [
        p.name for p in exports.iterdir()
        if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
    ]
    for d in sorted(dates, reverse=True):
        if (exports / d / "outbox").exists():
            return d
    return ""

def prefer_platform_files(outbox: Path, topic_id: str, platform: str = "telegram") -> List[Path]:
    """Prefer platform-specific files like t13_telegram_*.png over generic t13_*.png."""
    exts = ("*.png", "*.jpg", "*.jpeg")
    picks: List[Path] = []
    # platform first
    for ext in exts:
        picks += sorted(outbox.glob(f"{topic_id}_{platform}_{ext}"))
    # then generic
    for ext in exts:
        picks += sorted(outbox.glob(f"{topic_id}_{ext}"))
    # de-dup by stem (if both png/jpg exist)
    seen = set()
    uniq: List[Path] = []
    for p in picks:
        stem = p.stem
        if stem not in seen:
            uniq.append(p)
            seen.add(stem)
    return uniq

def load_captions(outbox: Path, topic_id: str, platform: str = "telegram") -> Dict[str, str]:
    # prefer platform-specific
    caps = list(sorted(outbox.glob(f"{topic_id}_{platform}_caption_*.txt")))
    if not caps:
        caps = list(sorted(outbox.glob(f"{topic_id}_caption_*.txt")))
    out: Dict[str, str] = {}
    for p in caps:
        txt = p.read_text(encoding="utf-8", errors="ignore").strip()
        # extract lang: ..._caption_en.txt
        m = re.search(r"_caption_([a-z]{2})\.txt$", p.name, re.I)
        lang = (m.group(1).lower() if m else "en")
        out[lang] = txt
    return out

def compose_caption(captions: Dict[str, str], langs: List[str]) -> str:
    parts: List[str] = []
    for lang in langs:
        t = captions.get(lang)
        if t:
            parts.append(t)
    if not parts and captions:
        # fallback: any one caption
        parts = [next(iter(captions.values()))]
    cap = "\n\n".join(parts).strip()
    cap = trim_caption(cap, 1024)  # Telegram photo/doc caption limit
    cap = escape_html(cap)
    return cap

def get_creds() -> Tuple[str, str]:
    # Prefer native secrets module
    if get_secret:
        token = (get_secret("telegram", "bot_token") or "").strip()
        chat  = (get_secret("telegram", "chat_id") or "").strip()
    else:
        # as a fallback, allow env vars
        token = os.environ.get("TG_BOT_TOKEN", "").strip()
        chat  = os.environ.get("TG_CHAT_ID", "").strip()
    return token, chat

def ensure_token_valid(token: str) -> None:
    if not token or not re.match(r"^\d+:[A-Za-z0-9_\-]{30,}$", token):
        raise SystemExit("[ERROR] telegram bot token missing/invalid. Set with: python -m satyagrah.creds_cli set --service telegram --key bot_token --value <TOKEN>")

def ensure_chat_valid(chat: str) -> None:
    if not chat:
        raise SystemExit("[ERROR] telegram chat_id missing. Set with: python -m satyagrah.creds_cli set --service telegram --key chat_id --value <ID_OR_@username>")

# ---------------- telegram calls ----------------

def tg_send_photo(token: str, chat_id: str, image: Path, caption: str = "") -> dict:
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    files = {"photo": image.open("rb")}
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"
    r = requests.post(url, data=data, files=files, timeout=60)
    r.raise_for_status()
    return r.json()

def tg_send_media_group(token: str, chat_id: str, images: List[Path], caption: str) -> dict:
    """
    Up to 10 items in a single album. Only one item may carry the caption.
    """
    url = f"https://api.telegram.org/bot{token}/sendMediaGroup"
    media = []
    files = {}
    for i, p in enumerate(images):
        key = f"photo{i}"
        files[key] = p.open("rb")
        item = {"type": "photo", "media": f"attach://{key}"}
        if i == 0 and caption:
            item["caption"] = caption
            item["parse_mode"] = "HTML"
        media.append(item)
    data = {"chat_id": chat_id, "media": json.dumps(media, ensure_ascii=False)}
    r = requests.post(url, data=data, files=files, timeout=120)
    r.raise_for_status()
    return r.json()

# ---------------- main ----------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Post outbox files to Telegram")
    ap.add_argument("--date", default="latest", help="yyyy-mm-dd or 'latest'")
    ap.add_argument("--id", required=True, help="topic id, e.g. t13")
    ap.add_argument("--langs", default="en,hi", help="caption language order, comma separated")
    ap.add_argument("--album", action="store_true", help="send multiple images as a media group")
    ap.add_argument("--max", type=int, default=3, help="max images for album (<=10)")
    ap.add_argument("--dryrun", action="store_true", help="show what would be sent")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    run_date = args.date
    if run_date == "latest":
        rd = latest_date_with_outbox(ROOT)
        if not rd:
            print("[ERROR] No dated outbox found under exports/", file=sys.stderr)
            return 2
        run_date = rd

    outbox = ROOT / "exports" / run_date / "outbox"
    if not outbox.exists():
        print(f"[ERROR] Outbox not found: {outbox}", file=sys.stderr)
        return 2

    images = prefer_platform_files(outbox, args.id, "telegram")
    if not images:
        print(f"[ERROR] No images found for {args.id} in {outbox}", file=sys.stderr)
        return 2

    captions = load_captions(outbox, args.id, "telegram")
    caption = compose_caption(captions, [s.strip() for s in args.langs.split(",") if s.strip()])

    token, chat_id = get_creds()
    ensure_token_valid(token)
    ensure_chat_valid(chat_id)

    if args.album:
        images = images[: max(1, min(args.max, 10))]
    else:
        images = images[:1]

    print(f"Using outbox: {outbox}")
    print(f"Topic: {args.id}  |  date: {run_date}")
    print("Images:")
    for p in images:
        print("  -", p.name)
    print(f"Caption ({len(caption)} chars):", ("\n" + caption if args.verbose else " [hidden; use --verbose to show]"))

    if args.dryrun:
        print("\n[dryrun] Not sending to Telegram.")
        return 0

    try:
        if len(images) == 1:
            res = tg_send_photo(token, chat_id, images[0], caption)
        else:
            res = tg_send_media_group(token, chat_id, images, caption)
        ok = bool(res.get("ok", True))  # sendMediaGroup returns a list, not dict; requests.raise_for_status() already ran.
        print("Telegram: OK" if ok else f"Telegram: response = {res}")
        return 0 if ok else 1
    except requests.HTTPError as e:
        try:
            payload = e.response.json()
        except Exception:
            payload = e.response.text if e.response is not None else str(e)
        print("[HTTP ERROR]", payload, file=sys.stderr)
        return 1
    except Exception as e:
        print("[ERROR]", e, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

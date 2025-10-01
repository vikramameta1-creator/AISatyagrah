#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, re, sys
from pathlib import Path
from typing import Dict, List

from satyagrah.adapters.registry import get as get_adapter, names as adapter_names
# Reuse outbox helpers from your working telegram_post module
from satyagrah.adapters.telegram_post import (
    ROOT, latest_date_with_outbox, prefer_platform_files, load_captions, compose_caption
)

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Post outbox to one or more platforms")
    ap.add_argument("--date", default="latest")
    ap.add_argument("--id", required=True, help="topic id, e.g. t13")
    ap.add_argument("--platforms", default="telegram", help="csv, e.g. telegram,x,instagram")
    ap.add_argument("--album", action="store_true")
    ap.add_argument("--max", type=int, default=3)
    ap.add_argument("--dryrun", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    run_date = args.date
    if run_date == "latest":
        rd = latest_date_with_outbox(ROOT)
        if not rd:
            print("[ERROR] no dated outbox found under exports/", file=sys.stderr)
            return 2
        run_date = rd

    outbox = ROOT / "exports" / run_date / "outbox"
    if not outbox.exists():
        print(f"[ERROR] outbox not found: {outbox}", file=sys.stderr); return 2

    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    print("Adapters available:", ", ".join(adapter_names()))
    print(f"Posting {args.id} from {outbox} to {platforms}")

    # common selection & captions
    images_all = prefer_platform_files(outbox, args.id, "telegram")  # generic pick still fine
    if not images_all:
        print(f"[ERROR] no images found for {args.id}", file=sys.stderr); return 2
    images = images_all[: (max(1, min(args.max, 10)) if args.album else 1)]
    captions = load_captions(outbox, args.id, "telegram")
    caption = compose_caption(captions, ["en","hi"])

    if args.verbose:
        print("Images:", [p.name for p in images])
        print("Caption:", caption)

    if args.dryrun:
        print("[dryrun] not sending"); return 0

    rc = 0
    for platform in platforms:
        adapter = get_adapter(platform)
        if not adapter:
            print(f"[skip] adapter '{platform}' not implemented yet", file=sys.stderr)
            rc = max(rc, 1); continue
        res = adapter.publish(images, {"en":caption})  # adapter composes internally if needed
        print(f"[{platform}] {'OK' if res.ok else 'FAIL'}: {res.message}")
        if not res.ok:
            rc = max(rc, 1)
    return rc

if __name__ == "__main__":
    sys.exit(main())

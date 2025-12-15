from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .plan_builder import RUNS_DIR, PLAN_NAME, DATE_RE, _find_run_dir
from .formatting import format_instagram


def _log(msg: str) -> None:
    print(f"[newsroom-ig] {msg}")


def _load_plan(run_dir: Path, platform: Optional[str]) -> List[Dict[str, Any]]:
    """
    Load newsroom_plan.jsonl and optionally filter by platform.
    """
    plan_path = run_dir / PLAN_NAME
    if not plan_path.is_file():
        raise SystemExit(f"Plan file not found: {plan_path}")

    items: List[Dict[str, Any]] = []
    with plan_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if platform and obj.get("platform") != platform:
                continue
            items.append(obj)

    _log(f"Loaded {len(items)} item(s) from {plan_path}")
    return items


def _write_captions(run_dir: Path, items: List[Dict[str, Any]]) -> Path:
    """
    Write Instagram captions to a .txt file, one block per item.
    """
    out_path = run_dir / "instagram_captions.txt"
    with out_path.open("w", encoding="utf-8") as f:
        for idx, item in enumerate(items, start=1):
            caption = format_instagram(item)
            ident = item.get("id") or item.get("topic_id") or f"post-{idx}"
            f.write(f"# {ident}\n")
            f.write(caption)
            f.write("\n\n---\n\n")
    _log(f"Wrote {len(items)} caption block(s) to {out_path}")
    return out_path


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m satyagrah.newsroom.export_instagram_captions",
        description="Export Instagram captions from newsroom_plan.jsonl",
    )
    parser.add_argument(
        "--date",
        help="Run date YYYY-MM-DD (default: latest run with plan)",
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Platform filter, e.g. telegram / instagram (default: any)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of items to include",
    )

    args = parser.parse_args(argv)

    _log(f"Runs dir: {RUNS_DIR}")

    # Find run directory by date (or latest)
    if args.date:
        if not DATE_RE.match(args.date):
            raise SystemExit(f"Invalid date: {args.date!r}, expected YYYY-MM-DD")
        date = args.date
        run_dir = RUNS_DIR / date
        if not run_dir.is_dir():
            raise SystemExit(f"Run directory not found: {run_dir}")
    else:
        date, run_dir = _find_run_dir(args.platform)

    _log(f"Using run date: {date}")
    _log(f"Run dir: {run_dir}")

    items = _load_plan(run_dir, args.platform)

    if args.limit is not None:
        items = items[: args.limit]

    if not items:
        _log("No items to export.")
        return

    _write_captions(run_dir, items)


if __name__ == "__main__":
    main()

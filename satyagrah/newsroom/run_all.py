"""
satyagrah.newsroom.run_all

Orchestrate the newsroom pipeline for a single date + platform:

1. Build / refresh newsroom_plan.jsonl from satyagraph_social.csv
2. (Optionally) send Telegram posts from the plan
3. (Optionally) generate Instagram captions from the plan
"""

from __future__ import annotations

import argparse
from typing import List, Optional

from . import plan_builder
from . import send_telegram_from_plan
from . import instagram_captions


def _build_common_args(date: Optional[str], platform: str) -> List[str]:
    """Helper to build ['--date', ..., '--platform', ...] style argv."""
    args: List[str] = []
    if date:
        args += ["--date", date]
    if platform:
        args += ["--platform", platform]
    return args


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m satyagrah.newsroom.run_all",
        description=(
            "Run the newsroom pipeline for a given run date and platform.\n\n"
            "Steps:\n"
            "  1) plan_builder  → build / refresh newsroom_plan.jsonl\n"
            "  2) send_telegram_from_plan (optional)\n"
            "  3) instagram_captions (optional)\n"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--date",
        help=(
            "Run date in YYYY-MM-DD. If omitted, each step will use its own "
            "default / 'latest run' logic."
        ),
    )
    parser.add_argument(
        "--platform",
        default="telegram",
        help="Logical platform name (telegram / instagram / youtube / etc.).",
    )

    parser.add_argument(
        "--skip-plan",
        action="store_true",
        help="Skip rebuilding newsroom_plan.jsonl (reuse existing file).",
    )
    parser.add_argument(
        "--skip-telegram",
        action="store_true",
        help="Skip the Telegram sending step.",
    )
    parser.add_argument(
        "--skip-instagram",
        action="store_true",
        help="Skip the Instagram captions step.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Telegram only: format and log messages but do NOT send to Telegram.",
    )

    args = parser.parse_args(argv)

    # -------------------------------
    # Step 1 – Build / refresh plan
    # -------------------------------
    if not args.skip_plan:
        pb_args = _build_common_args(args.date, args.platform)
        print(f"[run_all] Step 1: plan_builder {pb_args}")
        plan_builder.main(pb_args)
    else:
        print("[run_all] Step 1: plan_builder SKIPPED (--skip-plan)")

    # -------------------------------
    # Step 2 – Telegram sending
    # -------------------------------
    if not args.skip_telegram:
        tg_args = _build_common_args(args.date, args.platform)
        if args.dry_run:
            tg_args.append("--dry-run")
        print(f"[run_all] Step 2: send_telegram_from_plan {tg_args}")
        send_telegram_from_plan.main(tg_args)
    else:
        print("[run_all] Step 2: send_telegram_from_plan SKIPPED (--skip-telegram)")

    # -------------------------------
    # Step 3 – Instagram captions
    # -------------------------------
    if not args.skip_instagram:
        ig_args = _build_common_args(args.date, args.platform)
        print(f"[run_all] Step 3: instagram_captions {ig_args}")
        instagram_captions.main(ig_args)
    else:
        print("[run_all] Step 3: instagram_captions SKIPPED (--skip-instagram)")

    print("[run_all] Done.")


if __name__ == "__main__":
    main()

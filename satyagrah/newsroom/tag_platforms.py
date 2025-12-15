from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Iterable

from .plan_builder import RUNS_DIR, _find_run_dir  # reuse existing helpers


def _log(msg: str) -> None:
    print(f"[platforms] {msg}")


def _update_platforms(
    rows: List[dict],
    ids: Iterable[str],
    platforms_value: str,
    all_rows: bool,
) -> int:
    """
    Update the 'platforms' column for matching rows.

    ids         = list of topic ids (t1, t2, …) to update
    platforms_value = string like 'telegram' or 'telegram,youtube'
    all_rows    = if True, ignore ids and update every row
    """
    ids_set = {i.strip() for i in ids} if ids else set()
    changed = 0

    for row in rows:
        if all_rows:
            matched = True
        else:
            topic_id = (row.get("topic_id") or row.get("id") or "").strip()
            matched = topic_id in ids_set

        if matched:
            row["platforms"] = platforms_value
            changed += 1

        # make sure the column exists even if not matched
        row.setdefault("platforms", row.get("platforms", ""))

    return changed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m satyagrah.newsroom.tag_platforms",
        description="Tag which platforms each topic should go to.",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Run date (YYYY-MM-DD) or 'latest'.",
    )
    parser.add_argument(
        "--platforms",
        required=True,
        help="Comma-separated platforms, e.g. 'telegram' or 'telegram,youtube'.",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--ids",
        nargs="+",
        help="Topic ids to tag, e.g. t1 t3 t4.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Tag all rows in this run.",
    )

    args = parser.parse_args(argv)

    run_dir = _find_run_dir(args.date)
    if run_dir is None:
        raise SystemExit(f"No run dir found for date '{args.date}' under {RUNS_DIR}")

    csv_path = Path(run_dir) / "satyagraph_social.csv"
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    _log(f"Run dir: {run_dir}")
    _log(f"CSV: {csv_path}")

    # Read all rows
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if "platforms" not in fieldnames:
        fieldnames.append("platforms")
        _log("CSV has no 'platforms' column; adding it.")

    changed = _update_platforms(
        rows=rows,
        ids=args.ids or [],
        platforms_value=args.platforms.strip(),
        all_rows=bool(args.all),
    )

    if changed == 0:
        _log("No matching rows were updated.")
        return

    # Write back
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    _log(f"Updated platforms='{args.platforms}' for {changed} row(s).")


if __name__ == "__main__":
    main()

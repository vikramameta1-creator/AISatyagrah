# D:\AISatyagrah\satyagrah\newsroom\add_platforms_column.py

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List


def _get_root() -> Path:
    # Same style as the other newsroom tools
    return Path(__file__).resolve().parents[2]


def _get_runs_dir() -> Path:
    root = _get_root()
    runs_dir = root / "data" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir


def _pick_date(runs_dir: Path, date: str | None) -> str:
    if date:
        return date

    # Fallback to latest run dir name (YYYY-MM-DD)
    dates: List[str] = [
        p.name for p in runs_dir.iterdir()
        if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name[7] == "-"
    ]
    if not dates:
        raise SystemExit("[platforms] No run directories found in data/runs")

    latest = sorted(dates)[-1]
    print(f"[platforms] No --date given, using latest run date: {latest}")
    return latest


def add_platforms_column(
    run_dir: Path,
    default_platform: str = "telegram",
) -> None:
    csv_path = run_dir / "satyagraph_social.csv"
    if not csv_path.exists():
        print(f"[platforms] No satyagraph_social.csv in {run_dir}, skipping")
        return

    print(f"[platforms] Patching {csv_path}")

    with csv_path.open("r", newline="", encoding="utf-8") as f_in:
        reader = list(csv.DictReader(f_in))

    if not reader:
        print("[platforms] CSV has 0 rows, nothing to do")
        return

    fieldnames = list(reader[0].keys())
    if "platform" in fieldnames or "platforms" in fieldnames:
        print("[platforms] CSV already has a platform/platforms column, leaving as-is")
        return

    new_fieldnames = fieldnames + ["platforms"]
    tmp_path = csv_path.with_suffix(".tmp")

    with tmp_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=new_fieldnames)
        writer.writeheader()
        for row in reader:
            row["platforms"] = default_platform
            writer.writerow(row)

    tmp_path.replace(csv_path)
    print(f"[platforms] Added 'platforms' column "
          f"with value '{default_platform}' for {len(reader)} row(s)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m satyagrah.newsroom.add_platforms_column",
        description="Add a 'platforms' column to satyagraph_social.csv "
                    "for a given run date (default: telegram).",
    )
    parser.add_argument(
        "--date",
        help="Run date in YYYY-MM-DD (default: latest run in data/runs)",
    )
    parser.add_argument(
        "--default-platform",
        default="telegram",
        help="Value to put into the new 'platforms' column (default: telegram)",
    )

    args = parser.parse_args(argv)

    runs_dir = _get_runs_dir()
    date = _pick_date(runs_dir, args.date)
    run_dir = runs_dir / date

    if not run_dir.exists():
        raise SystemExit(f"[platforms] Run dir does not exist: {run_dir}")

    add_platforms_column(run_dir, default_platform=args.default_platform)


if __name__ == "__main__":
    main()

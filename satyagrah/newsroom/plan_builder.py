from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT_DIR / "data" / "runs"
PLAN_NAME = "newsroom_plan.jsonl"

def _list_run_dates(runs_dir: Path) -> List[str]:
    if not runs_dir.exists():
        return []
    dates: List[str] = []
    for p in runs_dir.iterdir():
        if p.is_dir():
            n = p.name
            if len(n) == 10 and n[4] == "-" and n[7] == "-":
                dates.append(n)
    return sorted(dates)

def _resolve_date(date: Optional[str], runs_dir: Path) -> str:
    if date:
        return date
    dates = _list_run_dates(runs_dir)
    if not dates:
        raise FileNotFoundError("No runs found in data/runs")
    return dates[-1]

def _find_social_csv(run_dir: Path) -> Path:
    for c in [run_dir/"satyagraph_social.csv", run_dir/"social.csv", run_dir/"newsroom_social.csv"]:
        if c.exists():
            return c
    raise FileNotFoundError(f"No social CSV in {run_dir}")

def build_plan(
    date: Optional[str] = None,
    runs_dir: Path = RUNS_DIR,
    platform: Optional[str] = None,
    dry_run: bool = False,
) -> Path:
    resolved = _resolve_date(date, runs_dir)
    run_dir = runs_dir / resolved
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = _find_social_csv(run_dir)

    items: List[Dict] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            platforms_field = row.get("platforms") or row.get("platform") or "telegram"
            platforms = [p.strip().lower() for p in platforms_field.split(",") if p.strip()]
            for plat in platforms:
                if platform and plat != platform:
                    continue
                item = dict(row)
                item["id"] = str(row.get("id") or row.get("topic_id") or row.get("post_id") or f"row{idx}")
                item["platform"] = plat
                item.setdefault("status", "draft")
                items.append(item)

    plan_path = run_dir / PLAN_NAME
    with plan_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    return plan_path

def main(argv: Optional[Iterable[str]] = None) -> Path:
    parser = argparse.ArgumentParser(description="Build newsroom_plan.jsonl")
    parser.add_argument("--date", default=None)
    parser.add_argument("--runs-dir", default=str(RUNS_DIR))
    parser.add_argument("--platform", default=None)
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args(list(argv) if argv is not None else None)
    path = build_plan(date=args.date, runs_dir=Path(args.runs_dir), platform=args.platform, dry_run=args.dry_run)
    print(f"[newsroom.plan_builder] Plan written to: {path}")
    return path

if __name__ == "__main__":
    main()

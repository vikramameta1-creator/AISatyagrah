# -*- coding: utf-8 -*-
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]

def latest_run_date() -> str | None:
    runs_dir = ROOT / "data" / "runs"
    if not runs_dir.exists():
        return None
    dates = [p.name for p in runs_dir.iterdir() if p.is_dir() and p.name[:4].isdigit()]
    return max(dates) if dates else None

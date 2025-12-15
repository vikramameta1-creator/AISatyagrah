# -*- coding: utf-8 -*-
"""
Satyagraph LoRA jokes batch generator.

- Reads topic rows via facts_satire.build_topic_rows(date)
- Uses LoRA inference harness to generate a short Hinglish joke per topic
- Writes JSONL to data/runs/<date>/satyagraph_jokes.jsonl
- Optional: updates satire.json with a "lora_joke" field per topic

Usage examples:

  # Basic: write jokes JSONL
  python -m satyagrah.analysis.satyagraph_jokes --date 2025-09-18

  # Custom output path
  python -m satyagrah.analysis.satyagraph_jokes --date 2025-09-18 --out custom_jokes.jsonl

  # Limit to first 2 topics (for quick testing)
  python -m satyagrah.analysis.satyagraph_jokes --date 2025-09-18 --limit 2

  # Also update satire.json with lora_joke
  python -m satyagrah.analysis.satyagraph_jokes --date 2025-09-18 --update-satire
"""

from __future__ import annotations

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..analysis.facts_satire import build_topic_rows

try:
    # Real LoRA inference harness
    from ..infer.satyagraph_lora_infer import generate_lora_joke_for_row
except Exception as e:  # pragma: no cover
    raise SystemExit(
        f"[satyagraph_jokes] ERROR: Could not import LoRA inference harness: {e}\n"
        "Make sure satyagrah/infer/satyagraph_lora_infer.py exists and its dependencies (torch, transformers, peft) are installed."
    )


def _root_default() -> Path:
    d = Path(r"D:\AISatyagrah")
    return d if d.exists() else Path.cwd()


ROOT: Path = Path(os.environ.get("AISATYAGRAH_ROOT") or _root_default()).resolve()
DATA: Path = ROOT / "data"
RUNS: Path = DATA / "runs"


def _ensure_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise SystemExit(f"[satyagraph_jokes] Invalid date {date_str!r}: {e}")
    return dt.date().isoformat()


def _default_out_path(day: str) -> Path:
    return RUNS / day / "satyagraph_jokes.jsonl"


def _load_satire(day: str) -> Dict[str, Any]:
    """
    Load satire.json for the day, or return {} if missing.
    """
    p = RUNS / day / "satire.json"
    if not p.exists():
        return {}
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_satire(day: str, satire: Dict[str, Any]) -> None:
    p = RUNS / day / "satire.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(satire, f, ensure_ascii=False, indent=2)


def _make_jsonl_record(day: str, row: Dict[str, Any], joke: str) -> Dict[str, Any]:
    return {
        "date": day,
        "topic_id": row.get("topic_id"),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "one_liner": row.get("one_liner"),
        "actors": row.get("actors"),
        "category": row.get("category"),
        "source": row.get("source"),
        "published": row.get("published"),
        "joke": joke,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="satyagraph_jokes",
        description="Batch-generate LoRA jokes for Satyagraph topics.",
    )
    ap.add_argument(
        "--date",
        required=True,
        help="Run date (YYYY-MM-DD), e.g. 2025-09-18",
    )
    ap.add_argument(
        "--out",
        help="Override output JSONL path (default: data/runs/<date>/satyagraph_jokes.jsonl)",
    )
    ap.add_argument(
        "--append",
        action="store_true",
        help="Append to existing JSONL instead of overwriting",
    )
    ap.add_argument(
        "--limit",
        type=int,
        help="Optional max number of topics to process (for quick tests)",
    )
    ap.add_argument(
        "--update-satire",
        action="store_true",
        help="Also write lora_joke into satire.json for each topic.",
    )
    args = ap.parse_args(argv)

    day = _ensure_date(args.date)
    run_dir = RUNS / day
    if not run_dir.exists():
        raise SystemExit(f"[satyagraph_jokes] Run directory not found: {run_dir}")

    # 1) Load topic rows
    try:
        rows = build_topic_rows(day)
    except Exception as e:
        raise SystemExit(f"[satyagraph_jokes] Error building topic rows for {day}: {e}")

    if not rows:
        print(f"[satyagraph_jokes] No topics found for {day} (facts.json/satire.json empty?).")
        return 0

    if args.limit is not None and args.limit >= 0:
        rows = rows[: args.limit]

    # 2) Prepare output path
    out_path = Path(args.out) if args.out else _default_out_path(day)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if args.append else "w"
    written = 0

    # 3) Optionally load satire.json to update lora_joke
    satire: Dict[str, Any] = {}
    if args.update_satire:
        satire = _load_satire(day)

    print(
        f"[satyagraph_jokes] Using models under: {ROOT / 'models'}\n"
        f"[satyagraph_jokes] Generating jokes for {len(rows)} topics on {day} -> {out_path}"
    )

    with out_path.open(mode, encoding="utf-8") as f:
        for row in rows:
            tid = str(row.get("topic_id") or "")
            try:
                joke = generate_lora_joke_for_row(row, day)
            except Exception as e:
                joke = f"[LoRA error: {e}]"

            rec = _make_jsonl_record(day, row, joke)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1

            print(f"[satyagraph_jokes] topic {tid}: {joke[:80]!r}")

            # Update satire.json in-memory
            if args.update_satire:
                entry = satire.get(tid) or {}
                entry["lora_joke"] = joke
                satire[tid] = entry

    if args.update_satire:
        _save_satire(day, satire)
        print(
            f"[satyagraph_jokes] Updated satire.json with lora_joke for {len(rows)} topics."
        )

    print(f"[satyagraph_jokes] Wrote {written} jokes to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

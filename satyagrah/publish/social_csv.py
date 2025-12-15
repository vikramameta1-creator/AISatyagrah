# -*- coding: utf-8 -*-
"""
satyagrah.publish.social_csv

Builds a simple CSV of social-media-ready snippets from your
facts/satire data for a given date.

Usage (from project root):
    python -m satyagrah.publish.social_csv --date 2025-09-18

This will write:
    data/runs/2025-09-18/satyagraph_social.csv
"""

from __future__ import annotations

import os
import csv
from pathlib import Path
from typing import Any, Dict, List

from ..analysis.facts_satire import build_topic_rows


# --------------------------- ROOT / CONSTANTS -----------------------------

def _root_default() -> Path:
    d = Path(r"D:\AISatyagrah")
    return d if d.exists() else Path.cwd()


ROOT: Path = Path(os.environ.get("AISATYAGRAH_ROOT") or _root_default()).resolve()
RUNS: Path = ROOT / "data" / "runs"

# Baseline hashtags – matches our earlier decision
DEFAULT_HASHTAGS = "#india #indiapolitics #delhi #mumbai #newdelhi"


# --------------------------- CORE LOGIC -----------------------------------

def _choose_joke(row: Dict[str, Any]) -> str:
    """
    Prefer LoRA joke, then one_liner, then summary/title.
    """
    for key in ("lora_joke", "one_liner", "summary", "title"):
        val = (row.get(key) or "").strip()
        if val:
            return val
    return ""


def write_social_csv(date: str, out_path: Path, hashtags: str = DEFAULT_HASHTAGS) -> int:
    """
    Build a CSV of social snippets for the given date.

    Each row roughly:
      - topic_id, title, category, summary, actors, joke, snippet, hashtags, source, published, date
    """
    rows: List[Dict[str, Any]] = build_topic_rows(date)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "topic_id",
        "title",
        "category",
        "summary",
        "actors",
        "joke",
        "snippet",
        "hashtags",
        "source",
        "published",
        "date",
    ]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in rows:
            topic_id = r.get("topic_id")
            title = (r.get("title") or "").strip()
            summary = (r.get("summary") or "").strip()
            actors = r.get("actors") or ""
            category = r.get("category") or ""
            source = r.get("source") or ""
            published = r.get("published") or ""

            joke = _choose_joke(r)

            if title and joke:
                snippet_core = f"{title} — {joke}"
            elif joke:
                snippet_core = joke
            else:
                snippet_core = summary or title

            snippet = (snippet_core + "  " + hashtags).strip()

            writer.writerow(
                {
                    "topic_id": topic_id,
                    "title": title,
                    "category": category,
                    "summary": summary,
                    "actors": actors,
                    "joke": joke,
                    "snippet": snippet,
                    "hashtags": hashtags,
                    "source": source,
                    "published": published,
                    "date": date,
                }
            )

    print(f"[social_csv] Wrote {len(rows)} rows to {out_path}")
    return len(rows)


# --------------------------- CLI ENTRYPOINT -------------------------------

def main(argv: List[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build social-media-ready CSV for Satyagraph topics."
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Run date (YYYY-MM-DD) under data/runs/DATE",
    )
    parser.add_argument(
        "--outfile",
        help="Optional override output path (default: data/runs/DATE/satyagraph_social.csv)",
    )
    parser.add_argument(
        "--hashtags",
        default=DEFAULT_HASHTAGS,
        help=f"Hashtags to append (default: {DEFAULT_HASHTAGS!r})",
    )

    args = parser.parse_args(argv)

    date = args.date
    if args.outfile:
        out_path = Path(args.outfile)
    else:
        out_path = RUNS / date / "satyagraph_social.csv"

    count = write_social_csv(date, out_path, hashtags=args.hashtags)
    return 0 if count >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

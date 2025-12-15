# satyagrah/analysis/satyagraph_jsonl.py
"""
Build a Satyagraph JSONL dataset from facts+satire.

Usage (from project root):
    python -m satyagrah.analysis.satyagraph_jsonl --date 2025-09-18

This will create:
    data/runs/2025-09-18/satyagraph_train.jsonl

Each line is a JSON object roughly like:

    {
      "id": "2025-09-18_t1",
      "topic_id": "t1",
      "run_date": "2025-09-18",
      "title": "...",
      "actors": ["..."],
      "claims": ["[accusation] X: ..."],
      "neutral_summary": "...",
      "satire_one_liner": "...",
      "input": "<instruction-style input text>",
      "output": "<satirical one-liner>"
    }
"""

from __future__ import annotations

import argparse
import json
import datetime
from pathlib import Path
from typing import Any, Dict, List

from .facts_satire import build_topic_rows, _date_or_today, _run_dir  # reuse internals


def _claims_to_list(claims_text: str) -> List[str]:
    """
    Split the compact 'claims' field from CSV into a list.
    Claims are separated by ' || '.
    """
    if not claims_text:
        return []
    parts = [c.strip() for c in claims_text.split("||")]
    return [p for p in parts if p]


def build_jsonl_rows(date: str | None = None) -> List[Dict[str, Any]]:
    """
    Build a list of JSONL-ready dicts for a given run date.
    """
    date_str = _date_or_today(date)
    rows = build_topic_rows(date_str)
    out: List[Dict[str, Any]] = []

    for r in rows:
        topic_id = str(r.get("topic_id", "") or "")
        if not topic_id:
            continue

        title = (r.get("title") or "").strip()
        summary = (r.get("summary") or "").strip()
        one_liner = (r.get("one_liner") or "").strip()

        # If we have neither summary nor one_liner, skip
        if not summary and not one_liner:
            continue

        # Actors / claims as lists
        actors_text = (r.get("actors") or "").strip()
        actors = [a.strip() for a in actors_text.split(",") if a.strip()]
        claims_list = _claims_to_list((r.get("claims") or "").strip())

        category = (r.get("category") or "").strip()
        url = (r.get("url") or "").strip()
        source = (r.get("source") or "").strip()
        published = (r.get("published") or "").strip()
        language = (r.get("language") or "").strip()
        metaphor = (r.get("metaphor") or "").strip()

        # Build an instruction-style "input" text
        pieces: List[str] = []
        if title:
            pieces.append(f"Title: {title}")
        if category:
            pieces.append(f"Category: {category}")
        if actors:
            pieces.append("Actors: " + ", ".join(actors))
        if claims_list:
            pieces.append("Claims:\n" + "\n".join(f"- {c}" for c in claims_list))
        if summary:
            pieces.append("Neutral summary: " + summary)
        if metaphor:
            pieces.append(f"Visual metaphor: {metaphor}")

        instruction = (
            "Based on the following factual description of a political/news event, "
            "write one short satirical one-liner in English. The joke should be sharp "
            "but avoid hate or calls for violence.\n\n"
        )
        input_text = instruction + "\n\n".join(pieces)

        # Output is the satire one-liner (if we have it)
        output_text = one_liner or ""

        obj: Dict[str, Any] = {
            "id": f"{date_str}_{topic_id}",
            "topic_id": topic_id,
            "run_date": date_str,
            "title": title,
            "category": category,
            "actors": actors,
            "claims": claims_list,
            "neutral_summary": summary,
            "satire_one_liner": one_liner,
            "url": url,
            "source": source,
            "published": published,
            "language": language,
            "metaphor": metaphor,
            "input": input_text,
            "output": output_text,
        }
        out.append(obj)

    return out


def write_jsonl_for_date(date: str | None = None, out_path: Path | None = None) -> Path:
    """
    Build JSONL rows and write to data/runs/<date>/satyagraph_train.jsonl.
    """
    date_str = _date_or_today(date)
    run_dir = _run_dir(date_str)

    if out_path is None:
        out_path = run_dir / "satyagraph_train.jsonl"

    rows = build_jsonl_rows(date_str)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for obj in rows:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"[satyagraph_jsonl] Wrote {len(rows)} examples to {out_path}")
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m satyagrah.analysis.satyagraph_jsonl",
        description="Build a JSONL dataset from Satyagraph facts+satire.",
    )
    parser.add_argument(
        "--date",
        help="run date YYYY-MM-DD (default: today)",
    )

    args = parser.parse_args(argv)
    date_str = _date_or_today(args.date)
    write_jsonl_for_date(date_str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

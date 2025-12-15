# satyagrah/analysis/facts_satire.py
"""
Facts + Satire table builder for Satyagraph.

Usage (from project root):
    python -m satyagrah.analysis.facts_satire --date 2025-09-18 --write-csv

This will create:
    data/runs/2025-09-18/facts_satire.csv

Each row combines:
    - topics.json  (title, url, source, published, category ...)
    - facts.json   (summary, actors, claims, risk_flags, meta ...)
    - satire.json  (one_liner, metaphor, style, risk ...)
"""

import argparse
import csv
import datetime
import json
from pathlib import Path
from typing import Any, Dict, List


# project root is TWO levels up (…\AISatyagrah), because this file is in satyagrah/analysis/
ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "data" / "runs"



def _date_or_today(d: str | None) -> str:
    return d or datetime.date.today().isoformat()


def _run_dir(date: str | None) -> Path:
    d = _date_or_today(date)
    return RUNS_DIR / d


def _load_json(path: Path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[facts_satire] Warning: could not parse {path}: {e}")
            return {}
    return {}


def _normalize_topics(raw: Any) -> Dict[str, Dict[str, Any]]:
    """
    Normalize topics.json into {topic_id: item}.
    Supports both list-of-items and dict forms.
    """
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, dict):
        # Could be {id: item} OR {somekey: {..., 'id': 't1'}}
        for key, val in raw.items():
            if isinstance(val, dict) and "id" in val:
                out[val["id"]] = val
            elif isinstance(val, dict):
                # fallback: key is id
                v = dict(val)
                v.setdefault("id", key)
                out[key] = v
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            tid = item.get("id")
            if not tid:
                continue
            out[tid] = item
    return out


def build_topic_rows(date: str | None = None) -> List[Dict[str, Any]]:
    """
    Merge topics.json + facts.json + satire.json for a given date
    into a list of flat dict rows, one per topic_id.
    """
    run_dir = _run_dir(date)
    date_str = _date_or_today(date)

    topics_path = run_dir / "topics.json"
    facts_path = run_dir / "facts.json"
    satire_path = run_dir / "satire.json"

    topics_raw = _load_json(topics_path)
    facts = _load_json(facts_path)
    satire = _load_json(satire_path)

    if not facts:
        print(f"[facts_satire] No facts found in {facts_path}.")
        return []

    topics = _normalize_topics(topics_raw)

    rows: List[Dict[str, Any]] = []

    for topic_id, f_entry in sorted(facts.items()):
        t_entry = topics.get(topic_id, {})
        s_entry = satire.get(topic_id, {})

        # Claims -> single text field, separated by " || "
        claims = f_entry.get("claims", [])
        claims_text = " || ".join(
            f"[{c.get('stance','')}] {c.get('actor','?')}: {c.get('text','')}"
            for c in claims
            if isinstance(c, dict)
        )

        actors = f_entry.get("actors", [])
        actors_text = ", ".join(str(a) for a in actors)

        risk_flags = f_entry.get("risk_flags", [])
        risk_flags_text = ", ".join(str(r) for r in risk_flags)

        meta = f_entry.get("meta", {}) or {}
        url = meta.get("url") or t_entry.get("url", "")
        source = meta.get("source") or t_entry.get("source", "")
        published = meta.get("published") or t_entry.get("published", "")
        language = meta.get("language") or t_entry.get("language", "")

        row: Dict[str, Any] = {
            "run_date": date_str,
            "topic_id": topic_id,
            "title": t_entry.get("title", ""),
            "category": f_entry.get("category", "") or t_entry.get("category", ""),
            "summary": f_entry.get("summary", ""),
            "actors": actors_text,
            "claims": claims_text,
            "risk_flags": risk_flags_text,
            "one_liner": s_entry.get("one_liner", ""),
            "metaphor": s_entry.get("metaphor", ""),
            "style": s_entry.get("style", ""),
            "satire_risk": s_entry.get("risk", ""),
            "url": url,
            "source": source,
            "published": published,
            "language": language,
        }

        rows.append(row)

    return rows


def write_csv_for_date(date: str | None = None, out_path: Path | None = None) -> Path:
    """
    Build rows and write CSV for a given date.
    Returns the CSV path.
    """
    run_dir = _run_dir(date)
    date_str = _date_or_today(date)

    if out_path is None:
        out_path = run_dir / "facts_satire.csv"

    rows = build_topic_rows(date)
    if not rows:
        print("[facts_satire] No rows to write.")
        return out_path

    fieldnames = [
        "run_date",
        "topic_id",
        "title",
        "category",
        "summary",
        "actors",
        "claims",
        "risk_flags",
        "one_liner",
        "metaphor",
        "style",
        "satire_risk",
        "url",
        "source",
        "published",
        "language",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[facts_satire] Wrote {len(rows)} rows to {out_path}")
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m satyagrah.analysis.facts_satire",
        description="Build a facts+satire table/CSV for a run date.",
    )
    parser.add_argument(
        "--date",
        help="run date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--write-csv",
        action="store_true",
        help="write facts_satire.csv into the run directory",
    )

    args = parser.parse_args(argv)
    date = _date_or_today(args.date)

    if args.write_csv:
        write_csv_for_date(date)
    else:
        rows = build_topic_rows(date)
        print(f"[facts_satire] {len(rows)} rows for {date}")
        # Show a quick preview of first few
        for row in rows[:3]:
            print(
                f"- {row['topic_id']}: {row['title']!r} | "
                f"actors={row['actors']} | one_liner={row['one_liner']!r}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

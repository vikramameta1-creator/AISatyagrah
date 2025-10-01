# -*- coding: utf-8 -*-
import json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[2]  # D:\AISatyagrah

def _date_or_today(d=None):
    return d or datetime.date.today().isoformat()

def facts_path(date: str | None = None) -> pathlib.Path:
    date = _date_or_today(date)
    return ROOT / "data" / "runs" / date / "facts.json"

def write_facts_stub(topic_id: str, date: str | None, summary: str, bullets: list[str]) -> pathlib.Path:
    """Create or update a minimal facts.json with a single topic."""
    date = _date_or_today(date)
    run_dir = ROOT / "data" / "runs" / date
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "facts.json"
    data = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    data[topic_id] = {"summary": summary, "bullets": bullets}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

def read_facts(date: str | None) -> dict:
    p = facts_path(date)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

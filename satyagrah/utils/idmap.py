# -*- coding: utf-8 -*-
import json, pathlib, datetime, re
ROOT = pathlib.Path(__file__).resolve().parents[2]

def _date_or_today(d=None):
    return d or datetime.date.today().isoformat()

def _map_path(date):
    return ROOT / "data" / "runs" / date / "idmap.json"

def load_idmap(date: str) -> dict:
    p = _map_path(date)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def friendly_ids(date: str) -> list[str]:
    m = load_idmap(date)
    # values are like "t1","t2"... sort by numeric tail
    def key_fn(v: str):
        m = re.match(r"t(\d+)$", v)
        return int(m.group(1)) if m else 999999
    return sorted(set(m.values()), key=key_fn)

def ensure_friendly_id(date: str, raw_id: str, preferred_index: int | None = None) -> str:
    """Map a raw feed id → tN (stable per date)."""
    p = _map_path(date)
    m = load_idmap(date)
    if raw_id in m:
        return m[raw_id]
    existing = set(m.values())
    cand = f"t{preferred_index}" if preferred_index else None
    if not cand or cand in existing:
        n = 1
        while f"t{n}" in existing:
            n += 1
        cand = f"t{n}"
    m[raw_id] = cand
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    return cand

def resolve_topic_id(date: str, requested: str) -> str:
    """
    Resolve what to use on disk:
      - 'auto'  → first friendly id (e.g., t1) if available
      - 'tN'    → use as-is
      - other   → use as given (e.g., a raw hash used earlier)
    """
    if not requested or requested.lower() == "auto":
        ids = friendly_ids(date)
        if not ids:
            raise FileNotFoundError("No friendly IDs yet for this date. Run 'quick' first, or pass --id t1/t2/…")
        return ids[0]  # pick the first (t1)
    return requested

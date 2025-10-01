# -*- coding: utf-8 -*-
import json, pathlib, datetime
from dateutil import parser as dtp
from rapidfuzz import fuzz

ROOT = pathlib.Path(__file__).resolve().parents[2]

KEYWORDS = [
    "court","judge","judicial","hearing","order","summon","verdict","gavel",
    "raid","cbi","ed","probe","arrest",
    "budget","gst","price","inflation","policy","ordinance",
    "protest","rally","farm","media","anchor","debate"
]

def _date_or_today(d=None):
    return d or datetime.date.today().isoformat()

def _parse_dt(s):
    try:
        return dtp.parse(s)
    except Exception:
        return None

def _recency_score(published_iso, today=None):
    t0 = _parse_dt(published_iso)
    if not t0:
        return 0.4
    today = today or datetime.datetime.now(t0.tzinfo)
    days = max(0.0, (today - t0).total_seconds() / 86400.0)
    return max(0.0, 1.0 - min(days, 7.0)/7.0)

def _visual_hook_score(title):
    t = (title or "").lower()
    hits = sum(1 for k in KEYWORDS if k in t)
    return min(1.0, hits / 2.0)

def _risk_inverse(title):
    t = (title or "").lower()
    if "alleg" in t or "defam" in t:
        return 0.6
    return 1.0

def _score(item):
    r = _recency_score(item.get("published"))
    v = _visual_hook_score(item.get("title",""))
    k = _risk_inverse(item.get("title",""))
    return round(0.6*r + 0.3*v + 0.1*k, 4)

def _dedupe(items, threshold=92):
    items_sorted = sorted(items, key=lambda x: (x.get("published") or ""), reverse=True)
    kept = []
    for it in items_sorted:
        title = it.get("title","")
        if not title:
            continue
        if any(fuzz.ratio(title, k.get("title","")) >= threshold for k in kept):
            continue
        kept.append(it)
    return kept

def load_topics(date=None):
    date = _date_or_today(date)
    p = ROOT / "data" / "runs" / date / "topics.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

def write_shortlist(date, items):
    date = _date_or_today(date)
    out_dir = ROOT / "data" / "runs" / date
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "shortlist.json"
    payload = {"date": date, "items": items}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

def shortlist(date=None, top=6, dedupe_threshold=92):
    topics = load_topics(date)
    if not topics:
        raise FileNotFoundError("No topics.json for this date. Run: python -m satyagrah research")
    pool = _dedupe(topics, threshold=dedupe_threshold)
    scored = [{**t, "score": _score(t)} for t in pool]
    scored.sort(key=lambda x: x["score"], reverse=True)
    picks = scored[:top]
    return write_shortlist(date, picks)

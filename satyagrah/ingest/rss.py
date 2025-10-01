# -*- coding: utf-8 -*-
import hashlib, json, pathlib, datetime
import feedparser
from dateutil import parser as dtp

ROOT = pathlib.Path(__file__).resolve().parents[2]

def _date_or_today(d=None):
    return d or datetime.date.today().isoformat()

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

def _norm_entry(e: dict, source: str) -> dict:
    url = e.get("link") or e.get("id") or ""
    title = (e.get("title") or "").strip()
    published = None
    for key in ("published", "updated"):
        if e.get(key):
            try:
                published = dtp.parse(e[key]).isoformat()
                break
            except Exception:
                pass
    return {
        "id": _sha1(url or title),
        "title": title,
        "url": url,
        "published": published,
        "source": source,
        "category": "politics",
        "raw_text": "",
        "language": "en",
        "risk_flags": [],
        "meta": {}
    }

def fetch_from_feeds(urls: list[str]) -> list[dict]:
    out = []
    for u in urls:
        fp = feedparser.parse(u)
        for e in fp.entries[:30]:
            out.append(_norm_entry(e, source=u))
    return out

def write_topics(date: str | None, items: list[dict]) -> pathlib.Path:
    date = _date_or_today(date)
    run_dir = ROOT / "data" / "runs" / date
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "topics.json"
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

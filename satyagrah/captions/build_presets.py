# -*- coding: utf-8 -*-
"""
Build platform-specific captions for one topic id (or many).
Usage:
  python -m satyagrah.captions.build_presets --id t1 --date latest --platforms instagram x
  python -m satyagrah.captions.build_presets --date latest --from-shortlist --top 3
Writes:
  exports/<date>/<id>/caption_<platform>.txt
  exports/<date>/social_<platform>.csv (append)
"""
import argparse, csv, datetime, json
from pathlib import Path
from typing import List
from .build import build_for, latest_run_date
from .presets import PRESETS

def _read_facts(proj: Path):
    p = proj / "data" / "facts" / "facts.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"topics":[]}

def _topic_for_id(facts, tid):
    return next((t for t in facts.get("topics", []) if t.get("id")==tid), None)

def _trim_to(s: str, n: int):
    return s if len(s) <= n else (s[:max(0, n-1)] + "…")

def _utm(url: str, date: str, tid: str):
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}utm_source=aisatyagrah&utm_medium=social&utm_campaign={date}_{tid}"

def _merge_tags(base, extra):
    out=[]; seen=set()
    for t in list(base or []) + list(extra or []):
        t=str(t).lower().replace(" ", "")
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out

def build_one(proj: Path, tid: str, date: str, platforms: List[str]):
    facts = _read_facts(proj)
    topic = _topic_for_id(facts, tid)
    if not topic:
        # ensure a minimal caption so pipeline never blocks
        info = build_for(tid, date, "india")  # also writes generic caption.txt + social.csv
        topic = {"id": tid, "title": info["title"], "summary": info["caption"], "tags": []}
    title   = (topic.get("title") or "").strip()
    summary = (topic.get("summary") or "").strip()
    tags    = topic.get("tags", [])
    sources = topic.get("sources", [])

    exports = proj / "exports" / date
    outdir  = exports / tid
    outdir.mkdir(parents=True, exist_ok=True)

    results = []
    for p in platforms:
        preset = PRESETS[p]
        merged = _merge_tags(preset.base_tags, tags)
        hashline = " " + " ".join(f"#{t}" for t in merged) if merged else ""

        links = ""
        if preset.include_sources and sources:
            # limit to first 2 to keep things tidy
            u = [_utm(str(s), date, tid) for s in list(sources)[:2]]
            links = "\n\nSources: " + " | ".join(u)

        # build caption, then trim softly by reducing summary first
        body = f"{title} — {summary}".strip()
        cap  = (body + ("\n\n" + hashline if hashline else "") + (links or "")).strip()
        if len(cap) > preset.max_len:
            spare = preset.max_len - len(cap) + len(summary)
            new_summary = _trim_to(summary, max(0, spare))
            body = f"{title} — {new_summary}".strip(" —")
            cap  = (body + ("\n\n" + hashline if hashline else "") + (links or "")).strip()
            cap  = _trim_to(cap, preset.max_len)

        out_txt = outdir / f"caption_{p}.txt"
        out_txt.write_text(cap, encoding="utf-8")

        csv_path = exports / f"social_{p}.csv"
        new = not csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new: w.writerow(["id","title","platform","caption"])
            w.writerow([tid, title, p, cap])

        results.append((p, str(out_txt)))
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="single topic id")
    ap.add_argument("--date", default="latest")
    ap.add_argument("--platforms", nargs="*", default=["instagram","tiktok","x"])
    ap.add_argument("--from-shortlist", action="store_true", help="build for all ids in runs/<date>/shortlist.json")
    ap.add_argument("--top", type=int, default=0, help="limit when using --from-shortlist")
    args = ap.parse_args()

    proj = Path(__file__).resolve().parents[2]
    runs = proj / "data" / "runs"
    date = args.date
    if date.lower() == "latest":
        date = latest_run_date(runs)

    ids = []
    if args.from_shortlist:
        sl = runs / date / "shortlist.json"
        if not sl.exists():
            raise SystemExit(f"shortlist not found: {sl}")
        data = json.loads(sl.read_text(encoding="utf-8"))
        if isinstance(data, list):
            ids = [x if isinstance(x, str) else (x.get("id") or x.get("topic_id") or x.get("slug")) for x in data]
        else:
            seq = data.get("items") or data.get("topics") or data.get("ids") or []
            ids = [x if isinstance(x, str) else (x.get("id") or x.get("topic_id") or x.get("slug")) for x in seq]
        ids = [i for i in ids if i]
        if args.top and args.top>0: ids = ids[:args.top]
    elif args.id:
        ids = [args.id]
    else:
        raise SystemExit("Provide --id or --from-shortlist")

    print(f"Building {len(ids)} item(s) — date={date} — platforms={args.platforms}")
    for tid in ids:
        paths = build_one(proj, tid, date, args.platforms)
        for p, path in paths:
            print(f" - {tid} [{p}] → {path}")

if __name__ == "__main__":
    main()

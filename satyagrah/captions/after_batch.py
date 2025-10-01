# -*- coding: utf-8 -*-
"""
Run after a batch to build captions for processed items.
Usage:
  python -m satyagrah.captions.after_batch --date latest --top 3 --region india
"""
import argparse, json, datetime, re
from pathlib import Path
from .build import build_for, latest_run_date

def _safe_read_text(p: Path):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def _safe_read_json(p: Path):
    try:
        return json.loads(_safe_read_text(p)) if p.exists() else None
    except Exception:
        return None

def _first_sentence(s: str, max_len=140):
    s = (s or "").strip()
    if not s: return ""
    # take first sentence-ish or first line, cap length
    s = re.split(r'[\r\n\.!?]+', s, maxsplit=1)[0].strip() or s
    return (s[:max_len] + "…") if len(s) > max_len else s

def _derive_topic_fields(run_dir: Path, topic_id: str):
    """
    Try a few common files to get title/summary/tags.
    """
    # candidates
    title_txt   = run_dir / "title.txt"
    summary_txt = run_dir / "summary.txt"
    prompt_txt  = run_dir / "prompt.txt"
    tags_txt    = run_dir / "tags.txt"
    topic_json  = run_dir / "topic.json"
    meta_json   = run_dir / "meta.json"
    prompt_json = run_dir / "prompt.json"

    title = ""
    summary = ""
    tags = []

    # JSON sources first (richer)
    for jp in [topic_json, meta_json, prompt_json]:
        j = _safe_read_json(jp)
        if j:
            title   = title   or str(j.get("title")   or "")
            summary = summary or str(j.get("summary") or j.get("caption") or j.get("desc") or "")
            # tags might be list or comma string
            jt = j.get("tags") or j.get("hashtags") or []
            if isinstance(jt, str):
                tags += [t.strip().lower() for t in re.split(r'[, ]+', jt) if t.strip()]
            elif isinstance(jt, list):
                tags += [str(t).strip().lower() for t in jt if str(t).strip()]
            # fallback: prompt field can seed title/summary
            if not title and isinstance(j.get("prompt"), str):
                title = _first_sentence(j["prompt"], 80)

    # Plain text sources
    if not title and title_txt.exists():
        title = _first_sentence(_safe_read_text(title_txt), 80)
    if not summary and summary_txt.exists():
        summary = _safe_read_text(summary_txt).strip()
    if not title and prompt_txt.exists():
        title = _first_sentence(_safe_read_text(prompt_txt), 80)
    if not summary and prompt_txt.exists():
        # next lines of prompt as summary
        lines = _safe_read_text(prompt_txt).splitlines()
        summary = " ".join(lines[1:]).strip()[:240]

    if (not title) and (not summary):
        title = f"Topic {topic_id}"

    # tags.txt (comma/space/newline separated)
    if tags_txt.exists():
        ts = [t.strip().lower() for t in re.split(r'[, \r\n]+', _safe_read_text(tags_txt)) if t.strip()]
        tags.extend(ts)

    # de-dupe while preserving order
    seen = set(); tags_clean = []
    for t in tags:
        t = t.replace(" ", "")
        if t and t not in seen:
            seen.add(t); tags_clean.append(t)

    return title.strip(), summary.strip(), tags_clean

def _ensure_topic_in_facts(facts_path: Path, runs_root: Path, date: str, topic_id: str) -> bool:
    """
    Ensure an entry with id=topic_id exists in facts.json; if missing, create it
    using best-effort fields from runs/<date>/<topic_id>/.
    Returns True if facts.json changed.
    """
    facts = _safe_read_json(facts_path) or {"topics": []}
    topics = facts.get("topics", [])
    if any((t.get("id") == topic_id) for t in topics):
        return False  # already present

    run_dir = runs_root / date / topic_id
    title, summary, tags = _derive_topic_fields(run_dir, topic_id)
    topics.append({
        "id": topic_id,
        "title": title or f"Topic {topic_id}",
        "summary": summary or "Auto-added from shortlist.",
        "tags": tags or []
    })
    facts["topics"] = topics
    facts_path.parent.mkdir(parents=True, exist_ok=True)
    facts_path.write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")
    return True

def _read_ids(shortlist_path: Path):
    data = _safe_read_json(shortlist_path)
    ids = []
    if isinstance(data, list):
        for x in data:
            if isinstance(x, str):
                ids.append(x)
            elif isinstance(x, dict):
                ids.append(x.get("id") or x.get("topic_id") or x.get("slug"))
    elif isinstance(data, dict):
        seq = data.get("items") or data.get("topics") or data.get("ids") or []
        for x in seq:
            if isinstance(x, str):
                ids.append(x)
            elif isinstance(x, dict):
                ids.append(x.get("id") or x.get("topic_id") or x.get("slug"))
    return [i for i in ids if i]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="latest")
    ap.add_argument("--top", type=int, default=0, help="limit to first N; 0=all")
    ap.add_argument("--region", default="india")
    args = ap.parse_args()

    proj = Path(__file__).resolve().parents[2]
    runs_root = proj / "data" / "runs"
    date = args.date
    if date.lower() == "latest":
        date = latest_run_date(runs_root)

    shortlist = runs_root / date / "shortlist.json"
    if not shortlist.exists():
        raise SystemExit(f"shortlist not found: {shortlist}")

    facts_path = proj / "data" / "facts" / "facts.json"

    ids = _read_ids(shortlist)
    if args.top and args.top > 0:
        ids = ids[:args.top]

    print(f"Captions for {len(ids)} item(s) — date={date}")
    added = 0
    for tid in ids:
        try:
            # Ensure facts has an entry for this id; auto-hydrate from run dir if needed
            if _ensure_topic_in_facts(facts_path, runs_root, date, tid):
                added += 1
            info = build_for(tid, date, args.region)
            print(" -", tid, "→", info["caption_path"])
        except Exception as e:
            print(" !", tid, "ERROR:", e)

    if added:
        print(f"(auto-added {added} topic(s) to facts.json)")

if __name__ == "__main__":
    main()

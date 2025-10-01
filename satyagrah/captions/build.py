# -*- coding: utf-8 -*-
"""
Usage:
  python -m satyagrah.captions.build --id t1 --date latest --region india
Writes:
  exports/<date>/<id>/caption.txt
  exports/<date>/social.csv (append)
Also exposes build_for(id, date='latest', region='india') for programmatic use.
"""
import argparse, csv, datetime, json
from pathlib import Path

def latest_run_date(runs_dir: Path) -> str:
    dates = []
    for p in runs_dir.iterdir():
        if p.is_dir():
            try:
                datetime.date.fromisoformat(p.name)
                dates.append(p.name)
            except Exception:
                pass
    return max(dates) if dates else datetime.date.today().isoformat()

def _merge_tags(base_tags, topic_tags):
    merged = [*(t.lower().replace(" ", "") for t in base_tags or [])]
    for t in (topic_tags or []):
        t = str(t).lower().replace(" ", "")
        if t and t not in merged:
            merged.append(t)
    return merged

def build_for(topic_id: str, date: str = "latest", region: str = "india"):
    proj = Path(__file__).resolve().parents[2]  # D:\AISatyagrah
    data = proj / "data"
    facts_path = data / "facts" / "facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8")) if facts_path.exists() else {"topics":[]}

    topic = next((t for t in facts.get("topics", []) if t.get("id") == topic_id), None)
    if not topic:
        raise RuntimeError(f"Topic id not found in facts.json: {topic_id}")

    if date.lower() == "latest":
        date = latest_run_date(data / "runs")

    exports = proj / "exports"
    outdir = exports / date / topic_id
    outdir.mkdir(parents=True, exist_ok=True)

    base_tags = ["india","indiapolitics","delhi","mumbai","newdelhi"] if region.lower()=="india" else []
    tags = _merge_tags(base_tags, topic.get("tags"))

    title = (topic.get("title") or "").strip()
    summary = (topic.get("summary") or "").strip()
    hashline = (" " + " ".join(f"#{t}" for t in tags)).strip() if tags else ""
    caption = f"{title} — {summary}\n\n{hashline}".strip()

    cap_path = outdir / "caption.txt"
    cap_path.write_text(caption, encoding="utf-8")

    csv_path = exports / date / "social.csv"
    new = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["id","title","caption"])
        w.writerow([topic_id, title, caption])

    return {
        "id": topic_id,
        "date": date,
        "caption_path": str(cap_path),
        "csv_path": str(csv_path),
        "title": title,
        "caption": caption,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--date", default="latest")
    ap.add_argument("--region", default="india")
    args = ap.parse_args()
    info = build_for(args.id, args.date, args.region)
    print(f"Wrote: {info['caption_path']}")
    print(f"Appended: {info['csv_path']}")

if __name__ == "__main__":
    main()

# satyagrah/topics.py
"""
Satyagraph topics/facts helper (Milestone 5.1+).

Usage (from project root):
    python -m satyagrah.topics new t1 --date 2025-09-18 --summary "Short neutral summary"
    python -m satyagrah.topics wizard t1 --date 2025-09-18
    python -m satyagrah.topics satire t1 --date 2025-09-18 --one-liner "Punchy one-liner"
    python -m satyagrah.topics auto-satire --date 2025-09-18
"""
import argparse
import datetime
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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
            print(f"[topics] Warning: could not parse {path}: {e}")
            return {}
    return {}


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# cmd: new  → create/overwrite a facts.json entry
# ---------------------------------------------------------------------------

def cmd_new(args) -> int:
    date = _date_or_today(args.date)
    run_dir = _run_dir(date)
    run_dir.mkdir(parents=True, exist_ok=True)

    facts_path = run_dir / "facts.json"
    facts = _load_json(facts_path)

    topic_id = args.id
    if topic_id in facts and not args.force:
        print(f"[topics] Topic {topic_id!r} already exists in {facts_path}. Use --force to overwrite.")
        return 1

    # Try to pull metadata from topics.json if present
    topics_path = run_dir / "topics.json"
    meta = {}
    if topics_path.exists():
        try:
            items = json.loads(topics_path.read_text(encoding="utf-8"))
            if isinstance(items, dict):
                for item in items.values():
                    if item.get("id") == topic_id:
                        meta = item
                        break
            elif isinstance(items, list):
                for item in items:
                    if item.get("id") == topic_id:
                        meta = item
                        break
        except Exception as e:
            print(f"[topics] Warning: could not read topics.json: {e}")

    meta_block = {
        "url": meta.get("url", ""),
        "source": meta.get("source", ""),
        "published": meta.get("published", ""),
        "language": meta.get("language", ""),
    }
    category = meta.get("category", "")
    risk_flags = meta.get("risk_flags", [])
    title = meta.get("title", "")

    summary = args.summary or title or ""
    entry = {
        "summary": summary,
        "bullets": [],
        "category": category,
        "actors": [],
        "claims": [],
        "risk_flags": risk_flags,
        "meta": meta_block,
    }

    facts[topic_id] = entry
    _save_json(facts_path, facts)
    print(f"[topics] Wrote/updated {facts_path} for topic {topic_id!r}.")
    return 0


# ---------------------------------------------------------------------------
# cmd: wizard  → interactive editor for a single topic facts entry
# ---------------------------------------------------------------------------

def _print_facts_snapshot(topic_id: str, entry: dict) -> None:
    print("\n---------------- CURRENT FACTS ----------------")
    print(f"Topic id : {topic_id}")
    print(f"Summary  : {entry.get('summary', '')}")
    print(f"Category : {entry.get('category', '')}")
    print(f"Actors   : {', '.join(entry.get('actors', [])) or '(none)'}")
    print("Bullets  :")
    for i, b in enumerate(entry.get("bullets", []), start=1):
        print(f"  {i}. {b}")
    print("Claims   :")
    for i, c in enumerate(entry.get("claims", []), start=1):
        print(f"  {i}. [{c.get('stance','')}] {c.get('actor','?')}: {c.get('text','')}")
    print("Meta     :")
    m = entry.get("meta", {})
    print(f"  url       : {m.get('url','')}")
    print(f"  source    : {m.get('source','')}")
    print(f"  published : {m.get('published','')}")
    print(f"  language  : {m.get('language','')}")
    print("------------------------------------------------\n")


def cmd_wizard(args) -> int:
    date = _date_or_today(args.date)
    run_dir = _run_dir(date)
    run_dir.mkdir(parents=True, exist_ok=True)

    facts_path = run_dir / "facts.json"
    facts = _load_json(facts_path)

    topic_id = args.id
    if topic_id not in facts:
        print(f"[wizard] Topic {topic_id!r} not found in {facts_path}.")
        print("         Run 'python -m satyagrah.topics new ...' first.")
        return 1

    entry = facts[topic_id]

    while True:
        _print_facts_snapshot(topic_id, entry)
        print("Wizard menu:")
        print("  1) Edit summary")
        print("  2) Add bullet point")
        print("  3) Add actor")
        print("  4) Add claim")
        print("  5) Remove claim")
        print("  6) Show again")
        print("  0) Save & exit")
        choice = input("Select option: ").strip()

        if choice == "1":
            new_summary = input("New summary (blank = keep current): ").strip()
            if new_summary:
                entry["summary"] = new_summary

        elif choice == "2":
            bullet = input("New bullet text: ").strip()
            if bullet:
                entry.setdefault("bullets", []).append(bullet)

        elif choice == "3":
            actor = input("Actor name (e.g. 'Election Commission'): ").strip()
            if actor and actor not in entry.setdefault("actors", []):
                entry["actors"].append(actor)

        elif choice == "4":
            if not entry.get("actors"):
                print("[wizard] No actors yet. Add at least one actor first.")
                continue

            print("Available actors:")
            for i, a in enumerate(entry["actors"], start=1):
                print(f"  {i}) {a}")
            idx = input("Choose actor by number (or 0 to type a new one): ").strip()
            actor_name = ""
            try:
                n = int(idx)
                if n == 0:
                    actor_name = input("Actor name: ").strip()
                elif 1 <= n <= len(entry["actors"]):
                    actor_name = entry["actors"][n - 1]
                else:
                    print("[wizard] Invalid selection.")
                    continue
            except ValueError:
                print("[wizard] Invalid selection.")
                continue

            if actor_name and actor_name not in entry["actors"]:
                entry["actors"].append(actor_name)

            text = input("Claim text: ").strip()
            stance = input("Stance (accusation/defence/announcement/other) [other]: ").strip() or "other"
            if text:
                claim = {
                    "actor": actor_name or "unknown",
                    "text": text,
                    "stance": stance,
                }
                entry.setdefault("claims", []).append(claim)

        elif choice == "5":
            claims = entry.get("claims", [])
            if not claims:
                print("[wizard] No claims to remove.")
                continue
            for i, c in enumerate(claims, start=1):
                print(f"  {i}. [{c.get('stance','')}] {c.get('actor','?')}: {c.get('text','')}")
            idx = input("Remove which claim number (or 0 to cancel): ").strip()
            try:
                n = int(idx)
                if n == 0:
                    continue
                if 1 <= n <= len(claims):
                    removed = claims.pop(n - 1)
                    print(f"[wizard] Removed claim: {removed.get('text','')}")
                else:
                    print("[wizard] Invalid selection.")
            except ValueError:
                print("[wizard] Invalid selection.")

        elif choice == "6":
            continue

        elif choice == "0":
            facts[topic_id] = entry
            _save_json(facts_path, facts)
            print(f"[wizard] Saved {facts_path}. Bye.")
            return 0

        else:
            print("[wizard] Unknown option.")

        facts[topic_id] = entry
        _save_json(facts_path, facts)


# ---------------------------------------------------------------------------
# cmd: satire  → create/overwrite a single satire.json entry
# ---------------------------------------------------------------------------

def cmd_satire(args) -> int:
    date = _date_or_today(args.date)
    run_dir = _run_dir(date)
    run_dir.mkdir(parents=True, exist_ok=True)

    facts_path = run_dir / "facts.json"
    satire_path = run_dir / "satire.json"

    facts = _load_json(facts_path)
    if args.id not in facts:
        print(f"[satire] Topic {args.id!r} not found in {facts_path}. Run 'topics new' first.")
        return 1

    topic = facts[args.id]
    satire = _load_json(satire_path)

    one_liner = args.one_liner or topic.get("summary", "") or "Satire"
    neutral_summary_en = topic.get("summary", "")

    satire_entry = {
        "one_liner": one_liner,
        "neutral_summary_en": neutral_summary_en,
        "neutral_summary_hi": "",
        "metaphor": args.metaphor or "mask",
        "style": args.style or "rk_lineart",
        "risk": args.risk or "low",
        "hashtags_en": "",
        "hashtags_hi": "",
    }

    satire[args.id] = satire_entry
    _save_json(satire_path, satire)
    print(f"[satire] Wrote/updated {satire_path} for topic {args.id!r}.")
    return 0


# ---------------------------------------------------------------------------
# cmd: auto-satire  → build satire.json entries for all topics of a date
# ---------------------------------------------------------------------------

def _guess_metaphor(category: str, summary: str) -> str:
    cat = (category or "").lower()
    text = (summary or "").lower()
    if "election" in cat or "poll" in text or "vote" in text:
        return "election_stage"
    if "court" in text or "hc " in text or "high court" in text or "supreme court" in text:
        return "courtroom"
    if "parliament" in text or "lok sabha" in text or "rajya sabha" in text:
        return "parliament"
    if "budget" in text or "economy" in text or "inflation" in text:
        return "finance_circus"
    return "newsroom"


def cmd_auto_satire(args) -> int:
    date = _date_or_today(args.date)
    run_dir = _run_dir(date)
    run_dir.mkdir(parents=True, exist_ok=True)

    facts_path = run_dir / "facts.json"
    satire_path = run_dir / "satire.json"

    facts = _load_json(facts_path)
    if not facts:
        print(f"[auto-satire] No facts found in {facts_path}. Run 'topics new' or your ingest pipeline first.")
        return 1

    satire = _load_json(satire_path)
    created = 0
    skipped = 0

    for topic_id, entry in sorted(facts.items()):
        if topic_id in satire and not args.force:
            skipped += 1
            continue

        summary = entry.get("summary", "") or f"Topic {topic_id}"
        category = entry.get("category", "")
        risk_flags = entry.get("risk_flags", [])

        one_liner = summary
        if len(one_liner) > 120:
            one_liner = one_liner[:117].rstrip() + "..."

        metaphor = _guess_metaphor(category, summary)
        risk_level = "med" if risk_flags else "low"

        satire_entry = {
            "one_liner": one_liner,
            "neutral_summary_en": summary,
            "neutral_summary_hi": "",
            "metaphor": metaphor,
            "style": "rk_lineart",
            "risk": risk_level,
            "hashtags_en": "",
            "hashtags_hi": "",
        }

        satire[topic_id] = satire_entry
        created += 1

    _save_json(satire_path, satire)
    print(f"[auto-satire] Wrote/updated {satire_path}.")
    print(f"[auto-satire] Topics: created={created}, skipped={skipped} (use --force to overwrite).")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m satyagrah.topics",
        description="Satyagraph topics/facts & satire helpers",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="Create/extend facts.json entry for a topic id")
    p_new.add_argument("id", help="topic id (e.g. 't1' or '9464…')")
    p_new.add_argument("--date", help="run date YYYY-MM-DD (default: today)")
    p_new.add_argument("--summary", help="short neutral summary text")
    p_new.add_argument("--force", action="store_true", help="overwrite if topic already exists in facts.json")
    p_new.set_defaults(func=cmd_new)

    p_wiz = sub.add_parser("wizard", help="Interactive CLI to edit a topic's facts (actors, claims, bullets)")
    p_wiz.add_argument("id", help="topic id (must exist in facts.json)")
    p_wiz.add_argument("--date", help="run date YYYY-MM-DD (default: today)")
    p_wiz.set_defaults(func=cmd_wizard)

    p_sat = sub.add_parser("satire", help="Create/extend satire.json entry for a topic id")
    p_sat.add_argument("id", help="topic id (must exist in facts.json)")
    p_sat.add_argument("--date", help="run date YYYY-MM-DD (default: today)")
    p_sat.add_argument("--one-liner", dest="one_liner", help="short satirical headline / hook")
    p_sat.add_argument("--metaphor", help="visual metaphor (courtroom, circus, puppet, mic, etc.)")
    p_sat.add_argument("--style", help="art style key (rk_lineart, stencil, etc.)")
    p_sat.add_argument("--risk", help="low|med|high; just a tag for now")
    p_sat.set_defaults(func=cmd_satire)

    p_auto = sub.add_parser("auto-satire", help="Generate satire.json entries for all topics of a date")
    p_auto.add_argument("--date", help="run date YYYY-MM-DD (default: today)")
    p_auto.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing satire entries for this date",
    )
    p_auto.set_defaults(func=cmd_auto_satire)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

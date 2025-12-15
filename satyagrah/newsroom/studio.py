import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

# Root is two levels up from this file: satyagrah/newsroom/studio.py
ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "data" / "runs"


@dataclass
class NewsroomItem:
    topic_id: str
    title: str
    snippet: str
    joke: str
    hashtags: str
    platform: str
    image_prompt: str
    video_prompt: str


def load_rows(date: str, platform_filter: Optional[str], limit: Optional[int]) -> List[NewsroomItem]:
    run_dir = RUNS_DIR / date
    csv_path = run_dir / "satyagraph_social.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"satyagraph_social.csv not found for date {date} at {csv_path}")

    items: List[NewsroomItem] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            platform = (raw.get("platform") or "").strip()
            if platform_filter:
                # simple contains check, case-insensitive
                if platform_filter.lower() not in platform.lower():
                    continue

            topic_id = (raw.get("topic_id") or "").strip()
            title = (raw.get("title") or "").strip()
            snippet = (raw.get("snippet") or "").strip()
            joke = (raw.get("joke") or "").strip()
            hashtags = (raw.get("hashtags") or "").strip()

            image_prompt = build_image_prompt(title, snippet, hashtags)
            video_prompt = build_video_prompt(title, snippet, joke)

            items.append(
                NewsroomItem(
                    topic_id=topic_id,
                    title=title,
                    snippet=snippet,
                    joke=joke,
                    hashtags=hashtags,
                    platform=platform,
                    image_prompt=image_prompt,
                    video_prompt=video_prompt,
                )
            )

            if limit is not None and len(items) >= limit:
                break

    return items


def build_image_prompt(title: str, snippet: str, hashtags: str) -> str:
    """
    Build a simple text-to-image prompt for Stable Diffusion / image bots.
    You can tune this later to match your art style.
    """
    base = f"satirical news illustration about: {title}. "
    if snippet:
        base += f"Context: {snippet}. "
    if hashtags:
        base += f"Include visual hints for: {hashtags}. "

    style = (
        "high quality, cinematic lighting, detailed, expressive characters, "
        "stylized political cartoon, Indian newsroom vibe"
    )
    return base + style


def build_video_prompt(title: str, snippet: str, joke: str) -> str:
    """
    Build a short script-style prompt for a 30-60s video.
    This is text only; your video tool will consume it later.
    """
    parts = [f"Headline: {title}."]
    if snippet:
        parts.append(f"Summary: {snippet}.")
    if joke:
        parts.append(f"Satire angle: {joke}.")

    parts.append(
        "Write a 30-45 second satirical news monologue in Hinglish, "
        "with one anchor in a virtual studio, sharp punchlines but no defamation. "
        "Keep it fast-paced and visually descriptive for video generation."
    )
    return " ".join(parts)


def write_plan(date: str, items: List[NewsroomItem]) -> Path:
    run_dir = RUNS_DIR / date
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "newsroom_plan.jsonl"

    with out_path.open("w", encoding="utf-8") as f:
        for item in items:
            json.dump(asdict(item), f, ensure_ascii=False)
            f.write("\n")

    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate newsroom image/video prompts from satyagraph_social.csv")
    parser.add_argument("--date", required=True, help="Run date in YYYY-MM-DD (must match data/runs/<date>)")
    parser.add_argument(
        "--platform",
        default=None,
        help="Filter by platform column (e.g. 'telegram', 'instagram'). If omitted, include all.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of posts to include in the plan",
    )

    args = parser.parse_args()

    items = load_rows(args.date, args.platform, args.limit)
    out_path = write_plan(args.date, items)

    print(f"[newsroom] Root: {ROOT}")
    print(f"[newsroom] Runs dir: {RUNS_DIR}")
    print(f"[newsroom] Date: {args.date}")
    print(f"[newsroom] Platform filter: {args.platform or '(none)'}")
    print(f"[newsroom] Items in plan: {len(items)}")
    print(f"[newsroom] Plan written to: {out_path}")


if __name__ == "__main__":
    main()

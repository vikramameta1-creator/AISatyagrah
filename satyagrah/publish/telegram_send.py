"""
telegram_send.py

Send AISatyagrah posts to Telegram from satyagraph_social.csv.

Usage examples (from D:\AISatyagrah):

    # Dry-run using the latest run folder that actually has satyagraph_social.csv
    python -m satyagrah.publish.telegram_send --dry-run

    # Send real messages for a specific date
    $env:SATYAGRAH_TELEGRAM_BOT = "<your_bot_token>"
    python -m satyagrah.publish.telegram_send --date 2025-09-29 --chat <chat_id>

    # Limit to first 3 posts
    python -m satyagrah.publish.telegram_send --date 2025-09-29 --chat <chat_id> --limit 3

Environment:

    SATYAGRAH_RUNS_ROOT
        Optional. Root folder containing dated run dirs.
        Default: "<current_working_dir>/data/runs"

    SATYAGRAH_TELEGRAM_BOT
        Required (unless --dry-run). Telegram bot token.

CSV expectations:

    Run folder:  data/runs/YYYY-MM-DD/
    File name:   satyagraph_social.csv

    Your CSV columns currently are:
        topic_id, title, category, summary, actors,
        joke, snippet, hashtags, source, published, date

    This script builds each Telegram message as:

        snippet

        joke

        hashtags

    If a 'platform' column exists, rows are only sent if platform is empty
    or contains "telegram" (case-insensitive). If no platform column, all rows
    are considered.
"""

from __future__ import annotations

import argparse
import sys
import csv
import os
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, List, Optional, Dict, Any

import json
import urllib.request
import urllib.parse
import urllib.error


# ---------------------------------------------------------------------------
# Paths & run directory helpers
# ---------------------------------------------------------------------------

CSV_FILENAME = "satyagraph_social.csv"
# Prefer 'snippet' from your CSV, then fall back to other possible names
TEXT_COLUMNS_CANDIDATES = ["snippet", "text", "message", "caption", "post", "content"]
HASHTAG_COLUMNS_CANDIDATES = ["hashtags", "tags", "hash", "hash_tags"]
PLATFORM_COLUMN_NAME = "platform"


def safe_print(text: str) -> None:
    """
    Print text safely even on Windows consoles with limited encodings.

    Uses sys.stdout.buffer + encode(errors="replace") so characters like
    zero-width spaces won't crash the script.
    """
    encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
    if not isinstance(text, str):
        text = str(text)
    sys.stdout.buffer.write((text + "\n").encode(encoding, errors="replace"))


def get_runs_root() -> Path:
    """
    Determine where data/runs lives.

    Priority:
      1. SATYAGRAH_RUNS_ROOT env var
      2. ./data/runs relative to the current working directory
    """
    env_root = os.getenv("SATYAGRAH_RUNS_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return (Path.cwd() / "data" / "runs").resolve()


def _is_yyyymmdd(name: str) -> bool:
    try:
        datetime.strptime(name, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def find_latest_run_dir_with_csv(root: Path, csv_name: str) -> Path:
    """
    Pick the latest YYYY-MM-DD directory that actually contains `csv_name`.
    """
    candidates: List[Path] = []

    if not root.exists():
        raise FileNotFoundError(f"Runs root does not exist: {root}")

    for child in root.iterdir():
        if child.is_dir() and _is_yyyymmdd(child.name):
            if (child / csv_name).is_file():
                candidates.append(child)

    if not candidates:
        raise FileNotFoundError(
            f"No dated run directories containing {csv_name!r} found in {root}. "
            "Run the cli5 pipeline first so that the CSV is created."
        )

    # names are YYYY-MM-DD so lexical max is also chronological max
    return max(candidates, key=lambda p: p.name)


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

@dataclass
class SocialPost:
    text: str
    raw_row: Dict[str, Any]


def load_social_posts(csv_path: Path, platform_filter: str = "telegram") -> List[SocialPost]:
    """
    Load posts from CSV and optionally filter by platform.

    For your current CSV layout, the message is built as:

        snippet
        (blank line)
        joke
        (blank line)
        hashtags
    """
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    posts: List[SocialPost] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip() for fn in (reader.fieldnames or [])]

        # Map candidates to actual column names (case-insensitive)
        def find_column(candidates: Iterable[str]) -> Optional[str]:
            lower_map = {fn.lower(): fn for fn in fieldnames}
            for cand in candidates:
                if cand.lower() in lower_map:
                    return lower_map[cand.lower()]
            return None

        text_col = find_column(TEXT_COLUMNS_CANDIDATES)
        hashtags_col = find_column(HASHTAG_COLUMNS_CANDIDATES)

        # always try to include 'joke' if present
        joke_col = None
        for fn in fieldnames:
            if fn.lower() == "joke":
                joke_col = fn
                break

        platform_col = None
        for fn in fieldnames:
            if fn.lower() == PLATFORM_COLUMN_NAME:
                platform_col = fn
                break

        if text_col is None:
            raise ValueError(
                f"Could not find any text column in {csv_path}. "
                f"Tried: {', '.join(TEXT_COLUMNS_CANDIDATES)}. "
                f"Available columns: {', '.join(fieldnames)}"
            )

        for row in reader:
            # Platform filtering
            if platform_col:
                platform_val = (row.get(platform_col) or "").strip().lower()
                if platform_val and platform_filter.lower() not in platform_val:
                    continue  # skip rows not meant for this platform

            # 1) base text from snippet/text/etc.
            text = (row.get(text_col) or "").strip()

            # 2) add joke if present
            if joke_col:
                joke_val = (row.get(joke_col) or "").strip()
                if joke_val:
                    if text:
                        text = text + "\n\n" + joke_val
                    else:
                        text = joke_val

            if not text:
                continue  # nothing to send

            # 3) add hashtags at the end
            if hashtags_col:
                tags_val = (row.get(hashtags_col) or "").strip()
                if tags_val:
                    if not text.endswith("\n"):
                        text += "\n"
                    text += "\n" + tags_val

            # Telegram hard limit is 4096 characters
            if len(text) > 4096:
                text = text[:4000].rstrip() + "\n\n[… trimmed …]"

            posts.append(SocialPost(text=text, raw_row=row))

    return posts


# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------

class TelegramError(RuntimeError):
    pass


def send_telegram_text(bot_token: str, chat_id: str, text: str) -> dict:
    """
    Send a text message to Telegram using only the stdlib.
    Returns the parsed JSON response.
    """
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",           # change to "MarkdownV2" if you prefer
        "disable_web_page_preview": "true",
    }

    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(api_url, data=encoded)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                raise TelegramError(f"Non-JSON response from Telegram: {body!r}")

            if not payload.get("ok", False):
                raise TelegramError(f"Telegram error: {payload}")
            return payload

    except urllib.error.HTTPError as e:
        raise TelegramError(f"HTTP error from Telegram: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise TelegramError(f"Network error talking to Telegram: {e}") from e


# ---------------------------------------------------------------------------
# CLI + run-dir resolution
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send AISatyagrah Telegram posts from satyagraph_social.csv"
    )

    parser.add_argument(
        "--date",
        help=(
            "Run date in YYYY-MM-DD. "
            "If omitted, uses the latest dated run directory that already has satyagraph_social.csv."
        ),
    )
    parser.add_argument(
        "--chat",
        help="Telegram chat id (required unless --dry-run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not send anything to Telegram, just print what would be sent.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of posts to process.",
    )
    parser.add_argument(
        "--platform",
        default="telegram",
        help="Platform filter value to match against 'platform' column (default: telegram).",
    )

    return parser.parse_args(argv)


def resolve_run_dir_and_csv(args: argparse.Namespace) -> tuple[Path, Path]:
    """
    Decide which run directory and CSV file we’ll use.

    If --date is provided:
        - Require that the folder exists.
        - Require that satyagraph_social.csv exists inside it.

    If --date is omitted:
        - Pick the latest dated folder that already has satyagraph_social.csv.
    """
    root = get_runs_root()
    print(f"[telegram_send] Runs root: {root}")

    if args.date:
        try:
            run_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            raise SystemExit(f"Invalid --date format, expected YYYY-MM-DD, got: {args.date!r}")

        run_dir = root / run_date.strftime("%Y-%m-%d")
        if not run_dir.is_dir():
            raise SystemExit(
                f"Run directory not found: {run_dir}\n"
                "Make sure you have run the cli5 pipeline for that date "
                "and that the folder name matches YYYY-MM-DD."
            )

        csv_path = run_dir / CSV_FILENAME
        if not csv_path.is_file():
            contents = ", ".join(sorted(p.name for p in run_dir.iterdir()))
            raise SystemExit(
                f"Expected CSV not found at: {csv_path}\n"
                f"Folder contents: {contents}\n"
                "Either run the cli5 pipeline for that date or adjust telegram_send.py "
                "to use the correct CSV filename."
            )

        return run_dir, csv_path

    # No --date: pick latest run with CSV
    run_dir = find_latest_run_dir_with_csv(root, CSV_FILENAME)
    csv_path = run_dir / CSV_FILENAME
    return run_dir, csv_path


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    run_dir, csv_path = resolve_run_dir_and_csv(args)
    print(f"[telegram_send] Using run directory: {run_dir}")
    print(f"[telegram_send] CSV path: {csv_path}")

    posts = load_social_posts(csv_path, platform_filter=args.platform)
    if not posts:
        print("[telegram_send] No posts found for Telegram in CSV.")
        return

    if args.limit is not None and args.limit >= 0:
        posts = posts[: args.limit]

    bot_token = os.getenv("SATYAGRAH_TELEGRAM_BOT")
    chat_id = args.chat

    if not args.dry_run:
        if not bot_token:
            raise SystemExit(
                "SATYAGRAH_TELEGRAM_BOT is not set and --dry-run was not given. "
                "Set your Telegram bot token or use --dry-run."
            )
        if not chat_id:
            raise SystemExit(
                "--chat is required when not using --dry-run. "
                "Provide your Telegram chat id."
            )

    print(f"[telegram_send] Loaded {len(posts)} post(s).")
    if args.dry_run:
        print("[telegram_send] DRY-RUN mode: nothing will be sent to Telegram.")
        if not chat_id:
            chat_id = "<no-chat-id>"

    for idx, post in enumerate(posts, 1):
        header = f"\n--- Post {idx}/{len(posts)} ---"
        print(header)
        safe_print(post.text)
        safe_print("-----------------")

        if args.dry_run:
            continue

        try:
            resp = send_telegram_text(bot_token, chat_id, post.text)
            msg_id = resp.get("result", {}).get("message_id")
            print(f"[telegram_send] Sent message_id={msg_id}")
        except TelegramError as e:
            print(f"[telegram_send] ERROR sending post {idx}: {e}")

    print("[telegram_send] Done.")


if __name__ == "__main__":
    main()

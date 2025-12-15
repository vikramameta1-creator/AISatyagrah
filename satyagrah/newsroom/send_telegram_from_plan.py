from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT_DIR / "data" / "runs"
PLAN_NAME = "newsroom_plan.jsonl"

try:
    import requests  # type: ignore
except Exception:
    requests = None

def _list_run_dates(runs_dir: Path) -> List[str]:
    if not runs_dir.exists():
        return []
    dates: List[str] = []
    for p in runs_dir.iterdir():
        if p.is_dir():
            n = p.name
            if len(n) == 10 and n[4] == "-" and n[7] == "-":
                dates.append(n)
    return sorted(dates)

def _resolve_date(date: Optional[str], runs_dir: Path) -> str:
    if date:
        return date
    dates = _list_run_dates(runs_dir)
    if not dates:
        raise FileNotFoundError("No runs found in data/runs")
    return dates[-1]

def _plan_path(date: str, runs_dir: Path) -> Path:
    return runs_dir / date / PLAN_NAME

def _load_plan(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"{PLAN_NAME} not found: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items

def _save_plan(path: Path, items: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

def _send_telegram_message(token: str, chat_id: str, text: str) -> Optional[int]:
    if requests is None:
        print("[newsroom.send_telegram] requests not installed; dry-run only")
        return None
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": text})
    resp.raise_for_status()
    data = resp.json()
    return int(data.get("result", {}).get("message_id")) if "result" in data else None

def send_from_plan(
    date: Optional[str] = None,
    runs_dir: Path = RUNS_DIR,
    platform: str = "telegram",
    dry_run: bool = False,
    limit: Optional[int] = None,
    chat_id: Optional[str] = None,
) -> Dict[str, Any]:
    resolved = _resolve_date(date, runs_dir)
    path = _plan_path(resolved, runs_dir)
    items = _load_plan(path)

    token = os.environ.get("SATYAGRAH_TELEGRAM_BOT") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("SATYAGRAH_TELEGRAM_CHAT") or os.environ.get("TELEGRAM_CHAT_ID") or ""

    now_iso = datetime.now(timezone.utc).isoformat()
    sent = 0
    candidates = 0
    new_items: List[Dict[str, Any]] = []

    for it in items:
        if (it.get("platform") or "").lower() != platform.lower():
            new_items.append(it); continue
        status = (it.get("status") or "draft").lower()
        if status == "sent":
            new_items.append(it); continue
        if status != "approved":  # only approved are candidates
            new_items.append(it); continue

        candidates += 1
        title = it.get("title") or it.get("summary") or ""
        snippet = it.get("snippet") or ""
        hashtags = it.get("hashtags") or ""
        text = "\n".join([t for t in (title, snippet, hashtags) if t]).strip()
        if not text:
            new_items.append(it); continue

        print(f"[newsroom.send_telegram] ({platform}) {text!r}")

        if dry_run or not token or not chat_id:
            new_items.append(it)
        else:
            msg_id = _send_telegram_message(token=token, chat_id=chat_id, text=text)
            it["status"] = "sent"
            it["sent_at"] = now_iso
            if msg_id is not None:
                it["message_id"] = msg_id
            new_items.append(it)
            sent += 1

        if limit is not None and sent >= limit:
            # append remaining untouched
            new_items.extend(items[len(new_items):])
            break

    if not dry_run:
        _save_plan(path, new_items)

    return {
        "date": resolved,
        "plan_path": str(path),
        "sent": sent,
        "candidates": candidates,
        "dry_run": dry_run,
        "platform": platform,
        "token_present": bool(token),
        "chat_id": chat_id or None,
    }

def main(argv: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(description="Send Telegram posts from plan")
    parser.add_argument("--date", default=None)
    parser.add_argument("--runs-dir", default=str(RUNS_DIR))
    parser.add_argument("--platform", default="telegram")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--chat-id", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    s = send_from_plan(
        date=args.date, runs_dir=Path(args.runs_dir),
        platform=args.platform, dry_run=args.dry_run,
        limit=args.limit, chat_id=args.chat_id,
    )
    print("[newsroom.send_telegram] Summary:", s)
    return s

if __name__ == "__main__":
    main()

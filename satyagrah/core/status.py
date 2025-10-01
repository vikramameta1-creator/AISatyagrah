# satyagrah/core/status.py
from __future__ import annotations
import os
import socket
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from .config import RUNS, EXPORTS, SD_HOST, SECRET, ensure_dirs

ensure_dirs()

def _fmt_dt(ts: float | int | None) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return None

def _latest_dir_info(base: Path) -> tuple[str | None, float | None]:
    """
    Return (name, mtime) of newest directory (or file) inside base.
    If nothing exists, returns (None, None).
    """
    try:
        items = [p for p in base.iterdir() if p.exists()]
        if not items:
            return (None, None)
        newest = max(items, key=lambda p: p.stat().st_mtime)
        return (newest.name, newest.stat().st_mtime)
    except Exception:
        return (None, None)

def _count_exports_for_hint(hint: str | None) -> int:
    """
    Best-effort count of exports associated with the latest run.
    If we have a latest item name, count anything in EXPORTS that contains that
    as a substring; otherwise return total file count.
    """
    try:
        if hint:
            return sum(1 for p in EXPORTS.rglob("*") if p.is_file() and hint in p.name)
        return sum(1 for p in EXPORTS.rglob("*") if p.is_file())
    except Exception:
        return 0

def _check_host_reachable(url: str, timeout: float = 1.5) -> bool:
    """
    Lightweight reachability check using stdlib (no requests dependency).
    We try a HEAD/GET to the root of SD_HOST. Any response (even 403) counts
    as reachable; only connection failures are 'down'.
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            return False
        # Some SD servers don't like HEAD on root; fall back to GET.
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            return resp.status > 0
    except (HTTPError, URLError, socket.timeout, ValueError):
        return False
    except Exception:
        return False

def get_status() -> dict:
    """Produce a status snapshot used by /dash and /api/status."""
    # Reachability and secret
    sd_host = SD_HOST
    sd_reachable = _check_host_reachable(sd_host)
    secret_set = bool(SECRET)

    # Telegram configured?
    tg_token = os.getenv("SATYAGRAH_TELEGRAM_TOKEN", "")
    tg_chat  = os.getenv("SATYAGRAH_TELEGRAM_CHAT", "")
    telegram_configured = bool(tg_token and tg_chat)

    # Latest run info + export count
    latest_name, latest_mtime = _latest_dir_info(RUNS)
    latest_run_date = _fmt_dt(latest_mtime)
    exports_count_for_latest = _count_exports_for_hint(latest_name)

    return {
        "sd_host": sd_host,
        "sd_reachable": sd_reachable,
        "secret_set": secret_set,
        "telegram_configured": telegram_configured,
        "latest_run_date": latest_run_date,
        "exports_count_for_latest": exports_count_for_latest,
    }

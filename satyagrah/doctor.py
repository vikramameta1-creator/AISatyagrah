# -*- coding: utf-8 -*-
"""
AISatyagrah Doctor — quick environment check & optional auto-fix.
Run as:  python -m satyagrah.doctor [--strict] [--fix] [--host http://127.0.0.1:7860]
"""
import argparse, os, sys, json, datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from pathlib import Path

def p(s): print(s, flush=True)

def tg(msg: str):
    """Best-effort Telegram notify (won't crash if not configured)."""
    try:
        from .notify.telegram import send as _send
        _send(msg)
    except Exception:
        pass

def check_dir(path: Path, create: bool=False):
    try:
        if not path.exists():
            if create:
                path.mkdir(parents=True, exist_ok=True)
            return False
        return True
    except Exception:
        return False

def touch_testfile(path: Path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")
        return True
    except Exception:
        return False

def http_ok(url: str, timeout=3.0):
    try:
        req = Request(url, headers={"User-Agent": "AISatyagrah-Doctor"})
        with urlopen(req, timeout=timeout) as r:
            return 200 <= getattr(r, "status", 200) < 500
    except (URLError, HTTPError, TimeoutError, OSError, NameError):
        return False

def ensure_sample_facts(facts_path: Path):
    if facts_path.exists(): return True
    sample = {
        "topics": [
            {
                "id": "t1",
                "title": "Sample Topic",
                "summary": "Short neutral summary for testing.",
                "sources": ["https://example.org/source1"],
                "tags": ["india", "politics", "satire"]
            }
        ]
    }
    try:
        facts_path.parent.mkdir(parents=True, exist_ok=True)
        facts_path.write_text(json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False

def _run(strict=False, fix=False, host=None):
    here = Path(__file__).resolve()
    proj = here.parent.parent  # D:\AISatyagrah
    data = proj / "data"
    runs = data / "runs"
    facts = data / "facts" / "facts.json"
    exports = proj / "exports"
    templates = proj / "templates"

    failures = []

    # 1) folders
    p("• Checking folders…")
    for folder in [data, runs, exports, templates]:
        ok = check_dir(folder, create=fix)
        p(f"  - {folder} : {'OK' if ok else 'MISSING'}")
        if not ok: failures.append(f"missing:{folder}")

    # 2) write test
    today = datetime.date.today().isoformat()
    testfile = exports / today / "_doctor.txt"
    can_write = touch_testfile(testfile) if fix or exports.exists() else False
    p(f"• Write test to {testfile} : {'OK' if can_write else 'FAILED'}")
    if not can_write: failures.append("write:exports")

    # 3) SD host
    host = (host or os.getenv("SATYAGRAH_SD_HOST", "http://127.0.0.1:7860")).rstrip("/")
    p(f"• Checking SD host: {host}")
    sd_ok = http_ok(host) or http_ok(host + "/docs") or http_ok(host + "/sdapi/v1/sd-models")
    p(f"  - reachable: {'YES' if sd_ok else 'NO'}")
    if not sd_ok: failures.append("sd:unreachable")

    # 4) sample facts
    facts_ok = ensure_sample_facts(facts) if fix else facts.exists()
    p(f"• Facts file: {facts} : {'OK' if facts_ok else 'MISSING'}")
    if not facts_ok: failures.append("facts:missing")

    # Summary + Telegram notify
    p("\nSummary:")
    if failures:
        for f in failures:
            p(f"  - {f}")
        tg("AISatyagrah Doctor ❌ Issues: " + ", ".join(failures) + f" | host={host}")
        if strict:
            p("\nStrict mode: FAIL")
            return 1
        p("\nNon-strict mode: WARN (continuing)")
        return 0
    else:
        p("  All checks passed.")
        tg(f"AISatyagrah Doctor ✅ All checks passed | host={host}")
        return 0

# Importable entrypoint
def run(strict=False, fix=False, host=None):
    """Programmatic entrypoint used by other modules (returns exit code int)."""
    return _run(strict=strict, fix=fix, host=host)

# CLI entrypoint
def main():
    parser = argparse.ArgumentParser(description="AISatyagrah environment doctor")
    parser.add_argument("--strict", action="store_true", help="Return nonzero exit code if any check fails")
    parser.add_argument("--fix", action="store_true", help="Create missing folders & sample data where safe")
    parser.add_argument("--host", default=os.getenv("SATYAGRAH_SD_HOST", "http://127.0.0.1:7860"),
                        help="Stable Diffusion host (mock or real)")
    args = parser.parse_args()
    return _run(strict=args.strict, fix=args.fix, host=args.host)

if __name__ == "__main__":
    sys.exit(main())

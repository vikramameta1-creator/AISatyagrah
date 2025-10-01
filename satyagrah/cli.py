# satyagrah/cli.py
import argparse, datetime as _dt, json, sys, inspect
from pathlib import Path

# Resolve project root dynamically (works in D:\AISatyagrah_coding3 or original)
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORTS = ROOT / "exports"
DEFAULT_DB = ROOT / "state.db"

def _today_str():
    return _dt.date.today().isoformat()

def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(prog="satyagrah")

    # Global options
    parser.add_argument("--date", help="YYYY-MM-DD; defaults to today or latest-run fallback")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--host", default="http://127.0.0.1:7860", help="Image API host")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings")
    parser.add_argument("--saveas", help="Copy outputs to a name or folder")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to sqlite DB")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # doctor
    p_doctor = sub.add_parser("doctor", help="Environment checks and fixes")
    p_doctor.add_argument("--fix", action="store_true")

    # prompt (compatible with old flags)
    p_prompt = sub.add_parser("prompt", help="Build prompt for a topic")
    p_prompt.add_argument("--id", required=True)
    p_prompt.add_argument("--one_liner")
    p_prompt.add_argument("--metaphor")
    p_prompt.add_argument("--style")
    p_prompt.add_argument("--risk")

    # image
    p_image = sub.add_parser("image", help="Generate image for topic id")
    p_image.add_argument("--id", required=True)

    # export jobs
    for kind in ("csv", "pdf", "pptx", "gif", "mp4", "zip"):
        sp = sub.add_parser(f"export:{kind}", help=f"Queue an {kind.upper()} export job")
        sp.add_argument("--date", help="Override date for this job")
        sp.add_argument("--args", help="JSON payload overrides")

    # worker
    sub.add_parser("worker", help="Run one worker tick (cron-friendly)")

    # telegram publish
    p_tg = sub.add_parser("telegram", help="Publish social.csv to Telegram")
    p_tg.add_argument("--chat", required=True)
    p_tg.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    # ensure DB and helpers
    from .models.db import ensure_db, insert_run
    from .storage.index import resolve_latest_date
    from .services.worker import enqueue_export_job, run_worker_once

    exports_root = Path(DEFAULT_EXPORTS)
    date = args.date or resolve_latest_date(exports_root) or _today_str()

    db_path = Path(args.db)
    ensure_db(db_path)
    _ = insert_run(db_path, date=date, cmd=args.cmd, seed=args.seed)

    if args.cmd == "doctor":
        from .doctor import run as doctor_run
        return doctor_run(strict=args.strict, fix=getattr(args, "fix", False))

    if args.cmd == "prompt":
        from .image import build_prompt
        # pass only the kwargs that build_prompt actually accepts
        sig = inspect.signature(build_prompt)
        kwargs = {}
        if "id" in sig.parameters: kwargs["id"] = args.id
        if "topic_id" in sig.parameters: kwargs["topic_id"] = args.id
        if "date" in sig.parameters: kwargs["date"] = date
        for k in ("one_liner","metaphor","style","risk"):
            if k in sig.parameters and getattr(args, k) is not None:
                kwargs[k] = getattr(args, k)
        try:
            out = build_prompt(**kwargs)
        except TypeError:
            # last-ditch: (id, date)
            out = build_prompt(args.id, date)
        print(out)
        return 0

    if args.cmd == "image":
        from .image import generate_image_for_id
        out = generate_image_for_id(args.id, date, host=args.host)
        print(out)
        return 0

    if args.cmd.startswith("export:"):
        kind = args.cmd.split(":", 1)[1]
        payload = {}
        if getattr(args, "args", None):
            payload.update(json.loads(args.args))
        job_id = enqueue_export_job(db_path, kind=kind, date=date, payload=payload)
        print(f"Queued job {job_id} for {kind} ({date})")
        return 0

    if args.cmd == "worker":
        return run_worker_once(db_path, exports_root)

    if args.cmd == "telegram":
        try:
            from .notify.telegram import publish_csv
        except Exception:
            from .publish.telegram import publish_csv  # fallback if you have this layout
        return publish_csv(date=date, chat=args.chat, dry_run=args.dry_run)

    parser.error("Unknown command")

if __name__ == "__main__":
    raise SystemExit(main())

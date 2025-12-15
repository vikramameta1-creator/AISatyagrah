import argparse, datetime as _dt, json, sys, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORTS = ROOT / "exports"
DEFAULT_DB = ROOT / "state.db"


def _today_str() -> str:
    return _dt.date.today().isoformat()


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(prog="satyagrah")

    parser.add_argument("--date", help="YYYY-MM-DD; default latest/today")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--host", default="http://127.0.0.1:7860")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--saveas")
    parser.add_argument("--db", default=str(DEFAULT_DB))

    sub = parser.add_subparsers(dest="cmd", required=True)

    # doctor
    p_doctor = sub.add_parser("doctor", help="Environment checks")
    p_doctor.add_argument("--fix", action="store_true")

    # prompt
    p_prompt = sub.add_parser("prompt", help="Build prompt for a topic")
    p_prompt.add_argument("--id", required=True)
    p_prompt.add_argument("--one_liner")
    p_prompt.add_argument("--metaphor")
    p_prompt.add_argument("--style")
    p_prompt.add_argument("--risk")

    # image
    p_image = sub.add_parser("image", help="Generate image for topic id")
    p_image.add_argument("--id", required=True)

    # exports
    for kind in ("csv", "pdf", "pptx", "gif", "mp4", "zip"):
        sp = sub.add_parser(f"export:{kind}", help=f"Queue {kind.upper()} export")
        sp.add_argument("--date")
        sp.add_argument("--args")

    # worker
    sub.add_parser("worker", help="Run one worker tick")

    # telegram
    p_tg = sub.add_parser("telegram", help="Publish to Telegram")
    p_tg.add_argument("--chat", required=True)
    p_tg.add_argument("--dry-run", action="store_true")
    p_tg.add_argument(
        "--from-plan",
        action="store_true",
        help="Send from newsroom_plan.jsonl instead of social CSV",
    )

    # newsroom
    p_newsroom = sub.add_parser("newsroom", help="Build newsroom_plan.jsonl")
    p_newsroom.add_argument("--date")
    p_newsroom.add_argument("--platform")
    p_newsroom.add_argument("--limit", type=int)
    p_newsroom.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    from .models.db import ensure_db, insert_run
    from .storage.index import resolve_latest_date
    from .services.worker import enqueue_export_job, run_worker_once

    exports_root = Path(DEFAULT_EXPORTS)
    date = args.date or resolve_latest_date(exports_root) or _today_str()

    db_path = Path(args.db)
    ensure_db(db_path)
    insert_run(db_path, date=date, cmd=args.cmd, seed=getattr(args, "seed", None))

    if args.cmd == "doctor":
        from .doctor import run as doctor_run
        return doctor_run(strict=args.strict, fix=getattr(args, "fix", False))

    if args.cmd == "prompt":
        from .image import build_prompt
        sig = inspect.signature(build_prompt)
        kwargs = {}
        if "id" in sig.parameters:
            kwargs["id"] = args.id
        if "topic_id" in sig.parameters:
            kwargs["topic_id"] = args.id
        if "date" in sig.parameters:
            kwargs["date"] = date
        for k in ("one_liner", "metaphor", "style", "risk"):
            if k in sig.parameters and getattr(args, k) is not None:
                kwargs[k] = getattr(args, k)
        out = build_prompt(**kwargs)
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
        # If --from-plan: delegate to newsroom sender
        if getattr(args, "from_plan", False):
            from .newsroom.send_telegram_from_plan import main as send_from_plan
            forward = ["--platform", "telegram"]
            if args.date:
                forward += ["--date", args.date]
            if args.chat:
                forward += ["--chat", args.chat]
            if args.dry_run:
                forward += ["--dry-run"]
            return send_from_plan(forward)
        else:
            # Legacy path: from social CSV
            try:
                from .notify.telegram import publish_csv
            except Exception:
                from .publish.telegram import publish_csv
            return publish_csv(date=date, chat=args.chat, dry_run=args.dry_run)

    if args.cmd == "newsroom":
        from .newsroom.plan_builder import main as newsroom_main
        forward = []
        if args.date:
            forward += ["--date", args.date]
        if args.platform:
            forward += ["--platform", args.platform]
        if args.limit is not None:
            forward += ["--limit", str(args.limit)]
        if args.dry_run:
            forward += ["--dry-run"]
        return newsroom_main(forward)

    parser.error("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())

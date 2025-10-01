import argparse, datetime as _dt, json, sys
from pathlib import Path
from .models.db import ensure_db, insert_run, list_jobs
from .storage.index import resolve_latest_date
from .services.worker import enqueue_export_job, run_worker_once

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORTS = ROOT / "exports"
DEFAULT_DB = ROOT / "state.db"

def _today() -> str:
    return _dt.date.today().isoformat()

def _auto_date(arg_date: str | None, exports_root: Path) -> str:
    if arg_date:
        return arg_date
    today = _today()
    latest = resolve_latest_date(exports_root)
    if latest is None or latest < today:
        return today
    return latest

def _normalize_globals(argv: list[str]) -> list[str]:
    globals_with_vals = ("--date", "--db", "--seed")
    front, rest = [], []
    i = 0
    while i < len(argv):
        a = argv[i]; matched = False
        for g in globals_with_vals:
            if a == g:
                front.append(a)
                if i + 1 < len(argv) and not argv[i+1].startswith("-"):
                    front.append(argv[i+1]); i += 2
                else:
                    i += 1
                matched = True; break
            if a.startswith(g + "="):
                front.append(a); i += 1; matched = True; break
        if not matched:
            rest.append(a); i += 1
    return front + rest

def _print_jobs(rows):
    if not rows:
        print("No jobs."); return
    print(f"{'id':>4}  {'date':10}  {'kind':12}  {'status':8}  {'created_at':19}  {'finished_at':19}  {'err?'}")
    for r in rows:
        print(f"{r['id']:>4}  {r['date']:10}  {r['kind'][:12]:12}  {r['status'][:8]:8}  "
              f"{(r['created_at'] or '')[:19]:19}  {(r.get('finished_at') or '')[:19]:19}  "
              f"{'Y' if r.get('error') else ''}")

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    argv = _normalize_globals(argv)

    p = argparse.ArgumentParser(prog="satyagrah.cli3", description="Export queue + worker + jobs")
    p.add_argument("--date", help="YYYY-MM-DD; default prefers today")
    p.add_argument("--seed", type=int, help="Optional seed")
    p.add_argument("--db", default=str(DEFAULT_DB), help="Path to sqlite DB")

    sub = p.add_subparsers(dest="cmd", required=True)

    # exports
    for kind in ("csv","pdf","pptx","gif","mp4","zip"):
        sp = sub.add_parser(f"export:{kind}", help=f"Queue {kind.upper()} export")
        sp.add_argument("--args", help="JSON payload")

    # worker
    sub.add_parser("worker", help="Run one worker tick")

    # jobs list/tail
    p_list = sub.add_parser("jobs:list", help="List recent jobs")
    p_list.add_argument("--status", choices=["queued","running","done","failed"])
    p_list.add_argument("--limit", type=int, default=30)

    p_tail = sub.add_parser("jobs:tail", help="Tail the last N jobs (alias)")
    p_tail.add_argument("--limit", type=int, default=20)

    args = p.parse_args(argv)
    date = _auto_date(getattr(args, "date", None), DEFAULT_EXPORTS)
    dbp = Path(args.db); ensure_db(dbp)
    insert_run(dbp, date=date, cmd=args.cmd, seed=getattr(args, "seed", None))

    if args.cmd.startswith("export:"):
        kind = args.cmd.split(":", 1)[1]
        payload = json.loads(args.args) if getattr(args, "args", None) else {}
        jid = enqueue_export_job(dbp, kind=kind, date=date, payload=payload)
        print(f"Queued job {jid} for {kind} ({date})")
        return 0

    if args.cmd == "worker":
        return run_worker_once(dbp, DEFAULT_EXPORTS)

    if args.cmd == "jobs:list":
        rows = list_jobs(dbp, limit=args.limit, status=args.status, date=date if not args.status else None)
        _print_jobs(rows); return 0

    if args.cmd == "jobs:tail":
        rows = list_jobs(dbp, limit=args.limit)
        _print_jobs(rows); return 0

    p.error("Unknown command")

if __name__ == "__main__":
    raise SystemExit(main())

# satyagrah/services/worker_loop.py
from __future__ import annotations
import time, argparse, datetime as _dt
from pathlib import Path
from ..models.db import ensure_db
from .worker import run_worker_once

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "state.db"
EXPORTS = ROOT / "exports"
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
LOGFILE = LOGS / "worker.log"

def tick() -> bool:
    ensure_db(DB_PATH)
    code = run_worker_once(DB_PATH, EXPORTS)
    ok = (code == 0)
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOGFILE.open("a", encoding="utf-8") as f:
        f.write(f"{now}  tick -> {'ok' if ok else 'err'}\n")
    return ok

def main():
    ap = argparse.ArgumentParser(description="AISatyagrah worker loop")
    ap.add_argument("--interval", type=float, default=1.2, help="seconds between ticks")
    args = ap.parse_args()
    print(f"[worker_loop] using DB={DB_PATH}  exports={EXPORTS}  every {args.interval}s")
    while True:
        try:
            tick()
        except KeyboardInterrupt:
            print("\n[worker_loop] stopped by user")
            break
        except Exception as e:
            now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with LOGFILE.open("a", encoding="utf-8") as f:
                f.write(f"{now}  EXC {e}\n")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()

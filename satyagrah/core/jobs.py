# -*- coding: utf-8 -*-
import subprocess, time, uuid
from pathlib import Path
from .config import ROOT, LOGS, LOCKS, ensure_dirs
from .logutil import get_logger

logger = get_logger("jobs")

def _lock_path(name: str) -> Path:
    return LOCKS / f"{name}.lock"

def acquire_lock(name: str, ttl_sec=3600) -> bool:
    ensure_dirs()
    p = _lock_path(name)
    if p.exists():
        # stale lock? allow overwrite after ttl
        if time.time() - p.stat().st_mtime < ttl_sec:
            return False
    p.write_text(str(time.time()), encoding="utf-8")
    return True

def release_lock(name: str):
    p = _lock_path(name)
    try: p.unlink()
    except FileNotFoundError: pass

def start_job(cmd: list[str], name: str = "job"):
    """
    Starts a background job, writes stdout/stderr to logs/job-<id>.log, and
    protects against concurrent runs of the same job name via a lock file.
    Returns (job_id:str, started:bool)
    """
    ensure_dirs()
    if not acquire_lock(name):
        logger.warning("Lock busy for %s; skipping launch", name)
        return ("", False)

    jid = f"{name}-{uuid.uuid4().hex[:8]}"
    logfile = LOGS / f"{jid}.log"
    logger.info("Starting %s: %s", jid, " ".join(cmd))
    with open(logfile, "w", encoding="utf-8") as f:
        # shell=False; inherit env; cwd=ROOT
        subprocess.Popen(cmd, cwd=str(ROOT), stdout=f, stderr=subprocess.STDOUT)
    return (jid, True)

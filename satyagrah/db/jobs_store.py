# satyagrah/db/jobs_store.py
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DDL = """
CREATE TABLE IF NOT EXISTS jobs (
  id         TEXT PRIMARY KEY,
  backend    TEXT,
  kind       TEXT,
  date       TEXT,
  status     TEXT,
  progress   REAL,
  message    TEXT,
  result     TEXT,         -- JSON as text
  created_at REAL,
  updated_at REAL
);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    cx = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
    cx.execute("PRAGMA journal_mode=WAL;")
    cx.execute("PRAGMA synchronous=NORMAL;")
    cx.execute("PRAGMA foreign_keys=ON;")
    return cx


class JobsStore:
    """Tiny SQLite-backed job store with upsert/get/list helpers."""

    def __init__(self, root: Path, filename: str = "jobs.db") -> None:
        self.root = Path(root)
        self.db_path = self.root / "data" / filename
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cx = _connect(self.db_path)
        self._init()

    def _init(self) -> None:
        cur = self.cx.cursor()
        for stmt in DDL.strip().split(";"):
            s = stmt.strip()
            if s:
                cur.execute(s)
        cur.close()

    @staticmethod
    def _norm(job: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure JSON serialisable fields
        job = dict(job)
        if isinstance(job.get("result"), (dict, list)):
            job["result"] = json.dumps(job["result"], ensure_ascii=False)
        return job

    def upsert(self, job: Dict[str, Any]) -> None:
        job = self._norm(job)
        now = time.time()
        job.setdefault("created_at", now)
        job["updated_at"] = now

        cols = ["id","backend","kind","date","status","progress","message","result","created_at","updated_at"]
        vals = [job.get(k) for k in cols]
        placeholders = ",".join(["?"] * len(cols))
        sets = ",".join([f"{c}=excluded.{c}" for c in cols[1:]])  # keep id
        sql = f"INSERT INTO jobs ({','.join(cols)}) VALUES ({placeholders}) " \
              f"ON CONFLICT(id) DO UPDATE SET {sets};"
        self.cx.execute(sql, vals)

    def patch(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        if "result" in fields and isinstance(fields["result"], (dict, list)):
            fields["result"] = json.dumps(fields["result"], ensure_ascii=False)
        fields["updated_at"] = time.time()
        sets = ",".join([f"{k}=?" for k in fields.keys()])
        vals = list(fields.values()) + [job_id]
        self.cx.execute(f"UPDATE jobs SET {sets} WHERE id=?", vals)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        row = self.cx.execute(
            "SELECT id,backend,kind,date,status,progress,message,result,created_at,updated_at "
            "FROM jobs WHERE id=?", (job_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(zip(
            ["id","backend","kind","date","status","progress","message","result","created_at","updated_at"],
            row
        ))
        # Try to parse JSON result
        try:
            d["result"] = json.loads(d["result"]) if d["result"] else None
        except Exception:
            pass
        d["ok"] = True
        return d

    def list(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        rows = self.cx.execute(
            "SELECT id,backend,kind,date,status,progress,message,result,created_at,updated_at "
            "FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (int(limit), int(offset))
        ).fetchall()
        items: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(zip(
                ["id","backend","kind","date","status","progress","message","result","created_at","updated_at"],
                r
            ))
            try:
                d["result"] = json.loads(d["result"]) if d["result"] else None
            except Exception:
                pass
            d["ok"] = True
            items.append(d)
        return items

    def close(self) -> None:
        try:
            self.cx.close()
        except Exception:
            pass

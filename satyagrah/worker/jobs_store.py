from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs_history (
  id TEXT PRIMARY KEY,
  backend TEXT,
  kind TEXT,
  status TEXT,
  progress REAL,
  message TEXT,
  result_json TEXT,
  created_at REAL,
  updated_at REAL
);
CREATE INDEX IF NOT EXISTS idx_jobs_history_created ON jobs_history(created_at DESC);
"""

class JobsStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # ensure DB exists and schema is present
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path.as_posix(), timeout=10)
        con.row_factory = sqlite3.Row
        return con

    def _ensure_schema(self) -> None:
        with self._connect() as con:
            con.executescript(SCHEMA)

    def upsert_job(self, job: Dict) -> None:
        """
        Insert or replace a job snapshot.
        Expected keys: id, backend, kind, status, progress, message, result (dict), created_at, updated_at
        """
        res = job.get("result")
        result_json = json.dumps(res, ensure_ascii=False) if res is not None else None
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO jobs_history (id, backend, kind, status, progress, message, result_json, created_at, updated_at)
                VALUES (:id, :backend, :kind, :status, :progress, :message, :result_json, :created_at, :updated_at)
                ON CONFLICT(id) DO UPDATE SET
                  backend=excluded.backend,
                  kind=excluded.kind,
                  status=excluded.status,
                  progress=excluded.progress,
                  message=excluded.message,
                  result_json=excluded.result_json,
                  created_at=excluded.created_at,
                  updated_at=excluded.updated_at
                """,
                {
                    "id": job.get("id"),
                    "backend": job.get("backend"),
                    "kind": job.get("kind"),
                    "status": job.get("status"),
                    "progress": float(job.get("progress") or 0.0),
                    "message": job.get("message"),
                    "result_json": result_json,
                    "created_at": float(job.get("created_at") or 0.0),
                    "updated_at": float(job.get("updated_at") or 0.0),
                },
            )

    def get_history(self, limit: int = 20, offset: int = 0) -> Tuple[List[Dict], int]:
        """
        Returns (items, total)
        items sorted by created_at DESC with pagination.
        """
        if limit < 1:
            limit = 1
        if limit > 200:
            limit = 200
        if offset < 0:
            offset = 0

        with self._connect() as con:
            # total
            cur = con.execute("SELECT COUNT(*) AS c FROM jobs_history")
            total = int(cur.fetchone()["c"])

            # page
            cur = con.execute(
                """
                SELECT id, backend, kind, status, progress, message, result_json, created_at, updated_at
                FROM jobs_history
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            items = []
            for row in cur.fetchall():
                res = None
                if row["result_json"]:
                    try:
                        res = json.loads(row["result_json"])
                    except Exception:
                        res = None
                items.append(
                    {
                        "id": row["id"],
                        "backend": row["backend"],
                        "kind": row["kind"],
                        "status": row["status"],
                        "progress": row["progress"],
                        "message": row["message"],
                        "result": res,
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )
            return items, total

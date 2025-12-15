# satyagrah/jobs_store.py
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DIR = Path.cwd() / "data"
DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB = DEFAULT_DIR / "jobs.db"


@dataclass
class JobRow:
    id: str
    backend: str           # "memory" or "redis"
    kind: str              # "all", etc.
    date: Optional[str]    # export date (YYYY-MM-DD) or None
    status: str            # queued|running|done|failed
    progress: float        # 0..100
    message: str
    result_json: Optional[str]  # JSON string of result dict
    created_at: float
    updated_at: float


class JobStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ---- public API -------------------------------------------------

    def start(self, job_id: str, backend: str, kind: str, date: Optional[str]) -> None:
        now = time.time()
        row = JobRow(
            id=job_id, backend=backend, kind=kind, date=date,
            status="queued", progress=0.0, message="queued",
            result_json=None, created_at=now, updated_at=now
        )
        self._upsert(row)

    def update(self, job_id: str, **fields: Any) -> None:
        row = self.get(job_id)
        if not row:
            # create a minimal record if missing
            self.start(job_id, fields.get("backend", "memory"), fields.get("kind", "all"), fields.get("date"))
            row = self.get(job_id)
        assert row is not None
        for k, v in fields.items():
            if k == "result" and v is not None:
                row["result_json"] = json.dumps(v, ensure_ascii=False)
            elif k in row:
                row[k] = v
        row["updated_at"] = time.time()
        self._upsert(_dict_to_row(row))

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._con() as con:
            cur = con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            r = cur.fetchone()
            return _row_to_dict(r) if r else None

    def list(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        with self._con() as con:
            cur = con.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (int(limit), int(offset)),
            )
            return [_row_to_dict(r) for r in cur.fetchall()]

    def cleanup(self, keep_last: int = 1000) -> None:
        """Trim table to last N rows by created_at (optional)."""
        with self._con() as con:
            cur = con.execute("SELECT id FROM jobs ORDER BY created_at DESC LIMIT -1 OFFSET ?", (int(keep_last),))
            old_ids = [r[0] for r in cur.fetchall()]
            if old_ids:
                con.executemany("DELETE FROM jobs WHERE id = ?", [(i,) for i in old_ids])

    # ---- internals --------------------------------------------------

    def _init_db(self) -> None:
        with self._con() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=NORMAL")
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY,
                  backend TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  date TEXT,
                  status TEXT NOT NULL,
                  progress REAL NOT NULL,
                  message TEXT NOT NULL,
                  result_json TEXT,
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)")

    def _upsert(self, row: JobRow) -> None:
        with self._con() as con:
            con.execute(
                """
                INSERT INTO jobs (id, backend, kind, date, status, progress, message, result_json, created_at, updated_at)
                VALUES (:id, :backend, :kind, :date, :status, :progress, :message, :result_json, :created_at, :updated_at)
                ON CONFLICT(id) DO UPDATE SET
                  backend=excluded.backend,
                  kind=excluded.kind,
                  date=excluded.date,
                  status=excluded.status,
                  progress=excluded.progress,
                  message=excluded.message,
                  result_json=excluded.result_json,
                  updated_at=excluded.updated_at
                """,
                asdict(row),
            )

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES, isolation_level=None)
        con.row_factory = sqlite3.Row
        return con


# ---- helpers --------------------------------------------------------

def _row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    d = dict(r)
    if d.get("result_json"):
        try:
            d["result"] = json.loads(d["result_json"])
        except Exception:
            d["result"] = None
    else:
        d["result"] = None
    d.pop("result_json", None)
    return d

def _dict_to_row(d: Dict[str, Any]) -> JobRow:
    return JobRow(
        id=d["id"],
        backend=d.get("backend", "memory"),
        kind=d.get("kind", "all"),
        date=d.get("date"),
        status=d.get("status", "queued"),
        progress=float(d.get("progress", 0.0)),
        message=d.get("message", ""),
        result_json=json.dumps(d.get("result")) if d.get("result") is not None else None,
        created_at=float(d.get("created_at", time.time())),
        updated_at=float(d.get("updated_at", time.time())),
    )

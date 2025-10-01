import sqlite3, json, datetime as _dt
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  cmd TEXT NOT NULL,
  seed INTEGER,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  date TEXT NOT NULL,
  payload TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  error TEXT
);
CREATE TABLE IF NOT EXISTS results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id INTEGER,
  path TEXT NOT NULL,
  kind TEXT NOT NULL,
  meta TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

def ensure_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as cx:
        cx.executescript(SCHEMA)

def insert_run(db_path: Path, *, date: str, cmd: str, seed: int | None):
    with sqlite3.connect(db_path) as cx:
        cur = cx.execute(
            'INSERT INTO runs(date, cmd, seed, created_at) VALUES (?,?,?,?)',
            (date, cmd, seed, _dt.datetime.now().isoformat()),
        )
        return cur.lastrowid

def enqueue_job(db_path: Path, *, kind: str, date: str, payload: dict) -> int:
    with sqlite3.connect(db_path) as cx:
        cur = cx.execute(
            'INSERT INTO jobs(kind, date, payload, status, created_at) VALUES (?,?,?,?,?)',
            (kind, date, json.dumps(payload), 'queued', _dt.datetime.now().isoformat()),
        )
        return cur.lastrowid

def fetch_next_job(db_path: Path):
    with sqlite3.connect(db_path) as cx:
        cx.row_factory = sqlite3.Row
        row = cx.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
        if not row:
            return None
        cx.execute("UPDATE jobs SET status='running', started_at=? WHERE id=?",
                   (_dt.datetime.now().isoformat(), row['id']))
        return dict(row)

def complete_job(db_path: Path, job_id: int, *, ok: bool, error: str | None, artifacts: list[tuple[str, str, dict]]):
    with sqlite3.connect(db_path) as cx:
        cx.execute(
            "UPDATE jobs SET status=?, finished_at=?, error=? WHERE id=?",
            ('done' if ok else 'failed', _dt.datetime.now().isoformat(), error, job_id),
        )
        for path, kind, meta in artifacts:
            cx.execute(
                'INSERT INTO results(job_id, path, kind, meta, created_at) VALUES (?,?,?,?,?)',
                (job_id, path, kind, json.dumps(meta or {}), _dt.datetime.now().isoformat()),
            )

def list_jobs(db_path: Path, *, limit: int = 50, status: str | None = None, date: str | None = None, order: str = "DESC"):
    with sqlite3.connect(db_path) as cx:
        cx.row_factory = sqlite3.Row
        q = "SELECT id, kind, date, status, created_at, started_at, finished_at, error FROM jobs"
        where, params = [], []
        if status: where.append("status=?"); params.append(status)
        if date:   where.append("date=?");   params.append(date)
        if where: q += " WHERE " + " AND ".join(where)
        q += f" ORDER BY id {order} LIMIT ?"; params.append(limit)
        return [dict(r) for r in cx.execute(q, params).fetchall()]

def list_results(db_path: Path, *, date: str | None = None, job_id: int | None = None, limit: int = 100):
    with sqlite3.connect(db_path) as cx:
        cx.row_factory = sqlite3.Row
        q = """SELECT r.id, r.job_id, r.path, r.kind, r.meta, r.created_at,
                      j.date AS job_date, j.kind AS job_kind
               FROM results r LEFT JOIN jobs j ON j.id=r.job_id"""
        where, params = [], []
        if job_id is not None: where.append("r.job_id=?"); params.append(job_id)
        if date is not None:   where.append("j.date=?");   params.append(date)
        if where: q += " WHERE " + " AND ".join(where)
        q += " ORDER BY r.id DESC LIMIT ?"; params.append(limit)
        return [dict(r) for r in cx.execute(q, params).fetchall()]

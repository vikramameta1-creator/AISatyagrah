from __future__ import annotations
import os, sqlite3, json, time, hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class JobRow:
    id: str
    kind: str
    status: str
    created_at: float
    updated_at: float
    meta: Dict[str, Any]
    result: Dict[str, Any]

def _now() -> float:
    return time.time()

def _dict(x):
    return x if isinstance(x, dict) else {}

def _row_to_obj(r) -> Dict[str, Any]:
    return {
        "id": r[0],
        "kind": r[1],
        "status": r[2],
        "created_at": r[3],
        "updated_at": r[4],
        "meta": json.loads(r[5] or "{}"),
        "result": json.loads(r[6] or "{}"),
    }

class JobsStore:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.db_path, isolation_level=None)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        con.row_factory = sqlite3.Row
        return con

    def _init(self):
        con = self._connect()
        with con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS jobs(
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    meta   TEXT,
                    result TEXT
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status  ON jobs(status)")
        con.close()

    # --- basic ops ----------------------------------------------------------
    def add(self, job_id: str, kind: str, status: str="queued",
            meta: Optional[Dict[str, Any]]=None, result: Optional[Dict[str, Any]]=None):
        ts = _now()
        con = self._connect()
        with con:
            con.execute(
                "INSERT OR REPLACE INTO jobs(id,kind,status,created_at,updated_at,meta,result) VALUES (?,?,?,?,?,?,?)",
                (job_id, kind, status, ts, ts, json.dumps(_dict(meta)), json.dumps(_dict(result)))
            )
        con.close()
        return job_id

    def update(self, job_id: str, status: Optional[str]=None,
               meta: Optional[Dict[str, Any]]=None, result: Optional[Dict[str, Any]]=None):
        con = self._connect()
        with con:
            cur = con.execute("SELECT id, meta, result FROM jobs WHERE id=?", (job_id,))
            row = cur.fetchone()
            if not row:
                con.close()
                return False
            new_meta = _dict(meta) or json.loads(row["meta"] or "{}")
            new_result = _dict(result) or json.loads(row["result"] or "{}")
            con.execute(
                "UPDATE jobs SET status=COALESCE(?,status), updated_at=?, meta=?, result=? WHERE id=?",
                (status, _now(), json.dumps(new_meta), json.dumps(new_result), job_id)
            )
        con.close()
        return True

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        con = self._connect()
        cur = con.execute("SELECT id,kind,status,created_at,updated_at,meta,result FROM jobs WHERE id=?", (job_id,))
        row = cur.fetchone()
        con.close()
        return _row_to_obj(row) if row else None

    def list(self, limit: int=50, offset: int=0, status: Optional[str]=None) -> Dict[str, Any]:
        con = self._connect()
        if status:
            cur = con.execute("""
                SELECT id,kind,status,created_at,updated_at,meta,result
                FROM jobs WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (status, limit, offset))
            tcur = con.execute("SELECT COUNT(*) FROM jobs WHERE status=?", (status,))
        else:
            cur = con.execute("""
                SELECT id,kind,status,created_at,updated_at,meta,result
                FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            tcur = con.execute("SELECT COUNT(*) FROM jobs")
        items = [_row_to_obj(r) for r in cur.fetchall()]
        total = int(tcur.fetchone()[0])
        con.close()
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    # --- backfill from exports directory -----------------------------------
    def backfill_from_exports(self, exports_root: str) -> int:
        """
        Scan exports_root recursively for files named like export_*.{zip,pdf,pptx,csv,gif,mp4}
        and add a 'succeeded' job per logical export group (basename without extension).
        """
        exts = {".zip", ".pdf", ".pptx", ".csv", ".gif", ".mp4"}
        added = 0
        for root, dirs, files in os.walk(exports_root):
            groups = {}
            for f in files:
                name, ext = os.path.splitext(f)
                if ext.lower() not in exts: 
                    continue
                groups.setdefault(name, []).append(os.path.join(root, f))
            for base, paths in groups.items():
                # stable id from base path
                h = hashlib.sha1((root + "|" + base).encode("utf-8")).hexdigest()
                # mtime = newest file mtime in the group
                mt = max(os.path.getmtime(p) for p in paths)
                meta = {"exports": paths}
                # Insert if absent
                if not self.get(h):
                    con = self._connect()
                    with con:
                        con.execute(
                            "INSERT INTO jobs(id,kind,status,created_at,updated_at,meta,result) VALUES (?,?,?,?,?,?,?)",
                            (h, "all", "succeeded", mt, mt, json.dumps(meta), json.dumps({"backfill": True}))
                        )
                    con.close()
                    added += 1
        return added

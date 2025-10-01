# satyagrah/services/worker.py
from pathlib import Path
from ..models.db import enqueue_job, fetch_next_job, complete_job

def enqueue_export_job(db_path: Path, *, kind: str, date: str, payload: dict) -> int:
    # kind is one of: csv, pdf, pptx, gif, mp4, zip
    return enqueue_job(db_path, kind=f"export:{kind}", date=date, payload=payload)

def _run_job(kind: str, date: str, exports_root: Path):
    if kind == "export:csv":
        from ..exports.csv_export import run as run_csv
        p = run_csv(date=date, exports_root=exports_root)
        return [(str(p), "csv", {})]
    elif kind == "export:pdf":
        from ..exports.pdf_export import run as run_pdf
        p = run_pdf(date=date, exports_root=exports_root)
        return [(str(p), "pdf", {})]
    elif kind == "export:pptx":
        from ..exports.pptx_export import run as run_pptx
        p = run_pptx(date=date, exports_root=exports_root)
        return [(str(p), "pptx", {})]
    elif kind == "export:gif":
        from ..exports.gif_export import run as run_gif
        p = run_gif(date=date, exports_root=exports_root)
        return [(str(p), "gif", {})]
    elif kind == "export:mp4":
        from ..exports.mp4_export import run as run_mp4
        p = run_mp4(date=date, exports_root=exports_root)
        return [(str(p), "mp4", {})]
    elif kind == "export:zip":
        from ..exports.zip_export import run as run_zip
        p = run_zip(date=date, exports_root=exports_root)
        return [(str(p), "zip", {})]
    else:
        raise RuntimeError(f"Unknown job kind: {kind}")

def run_worker_once(db_path: Path, exports_root: Path) -> int:
    job = fetch_next_job(db_path)
    if not job:
        print("No jobs.")
        return 0

    jid = job["id"]
    kind = job["kind"]

    try:
        artifacts = _run_job(kind, job["date"], exports_root)
        complete_job(db_path, jid, ok=True, error=None, artifacts=artifacts)
        print(f"Job {jid} done: {kind}")
        return 0
    except Exception as e:
        complete_job(db_path, jid, ok=False, error=str(e), artifacts=[])
        print(f"Job {jid} failed: {e}")
        return 1

# D:\AISatyagrah\satyagrah\worker\tasks.py
from __future__ import annotations
from typing import Optional, Dict, Any
from rq import get_current_job

from satyagrah.web.jobs_api import (
    _root_dir, _today, _gather_sources, _rel_to_root,
    export_zip_from_sources, export_csv_from_sources, export_pdf_from_sources,
    export_pptx_from_sources, export_gif_from_sources, export_mp4_from_sources,
)

# NEW: persist progress/results
from satyagrah.db import jobs_store as store

def _progress(p: float, msg: str) -> None:
    job = get_current_job()
    if job:
        job.meta["progress"] = float(p)
        job.meta["message"]  = msg
        job.save_meta()
        store.update_job(job.id, progress=float(p), message=msg)

def run_export_job(kind: str = "all", date: Optional[str] = None, base_url: str = "http://127.0.0.1:9000") -> Dict[str, Any]:
    job = get_current_job()
    if job:
        job.meta.update({"progress": 5.0, "message": "started"})
        job.save_meta()
        store.update_job(job.id, status="started", progress=5.0, message="started")

    root = _root_dir()
    date = date or _today()
    sources = _gather_sources(root, date)
    if not sources:
        if job:
            store.update_job(job.id, status="error", progress=100.0, message="nothing_to_export")
        return {"error": "nothing_to_export"}

    res: Dict[str, Any] = {}
    if kind in ("zip","all"):  res["zip"]  = _rel_to_root(export_zip_from_sources(root, date, sources, progress=_progress))
    if kind in ("csv","all"):  res["csv"]  = _rel_to_root(export_csv_from_sources(root, date, sources))
    if kind in ("pdf","all"):  res["pdf"]  = _rel_to_root(export_pdf_from_sources(root, date, base_url, sources))
    if kind in ("pptx","all"): res["pptx"] = _rel_to_root(export_pptx_from_sources(root, date, base_url, sources))
    if any(s.suffix.lower() in (".png",".jpg",".jpeg",".webp",".bmp") for s in sources):
        try:
            if kind in ("gif","all"):  res["gif"] = _rel_to_root(export_gif_from_sources(root, date, sources, progress=_progress))
        except Exception as e:
            res["gif_error"] = str(e)
        try:
            if kind in ("mp4","all"):  res["mp4"] = _rel_to_root(export_mp4_from_sources(root, date, sources, progress=_progress))
        except Exception as e:
            res["mp4_error"] = str(e)

    if job:
        job.meta.update({"progress": 100.0, "message": "complete"})
        job.save_meta()
        store.update_job(job.id, status="done", progress=100.0, message="complete", result=res)

    return res

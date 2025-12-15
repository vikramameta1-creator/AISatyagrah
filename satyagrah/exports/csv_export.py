# satyagrah/exports/csv_export.py
from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
DATAROOT = ROOT / "data"
EXPORTS = ROOT / "exports"

def _today() -> str:
    import datetime as _dt
    return _dt.date.today().isoformat()

def _images_for_date(date: str) -> List[Path]:
    art = DATAROOT / "runs" / date / "art"
    if not art.is_dir():
        return []
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    return sorted([p for p in art.iterdir() if p.suffix.lower() in exts and p.is_file()])

def _load_captions(date: str) -> Dict[str, Dict[str, Any]]:
    p = DATAROOT / "runs" / date / "captions.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def run(date: str, outdir: Path, payload: Dict[str, Any]) -> Path:
    """
    Worker calls this: run(date, EXPORTS/<date>, payload)
    payload may contain:
      - files: list of /data/... web paths in the desired order (from UI)
    Output: social.csv in exports/<date>/
    """
    date = date or _today()
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "social.csv"

    # selection from UI (web paths like /data/runs/<date>/art/xxx.png)
    files_web = payload.get("files") or []
    if files_web:
        files = [ (DATAROOT / Path(w.replace("/data/", "")).as_posix()).resolve() for w in files_web ]
    else:
        files = _images_for_date(date)

    caps = _load_captions(date)

    # write CSV
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "caption", "hashtags", "date"])
        for p in files:
            # compute web path for lookup
            try:
                rel = p.relative_to(DATAROOT).as_posix()
                web = f"/data/{rel}"
            except Exception:
                web = p.name
            rec = caps.get(web, {})
            caption = rec.get("caption", "")
            tags = rec.get("hashtags", [])
            w.writerow([p.name, caption, " ".join(tags), date])

    return out

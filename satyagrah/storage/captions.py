from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import json

def _file_for_date(root: Path, date: str) -> Path:
    d = root / "data" / "runs" / date
    d.mkdir(parents=True, exist_ok=True)
    return d / "captions.json"

def load(root: Path, date: str) -> Dict[str, Any]:
    p = _file_for_date(root, date)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save(root: Path, date: str, data: Dict[str, Any]) -> None:
    p = _file_for_date(root, date)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

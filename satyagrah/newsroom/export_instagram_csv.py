# D:\AISatyagrah\satyagrah\newsroom\export_instagram_csv.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
import csv, json
from satyagrah.paths import RUNS_DIR

def _plan_path(date: str) -> Path:
    return RUNS_DIR / date / "newsroom_plan.jsonl"

def _load_plan(date: str) -> List[Dict[str, Any]]:
    p = _plan_path(date)
    items: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            try: items.append(json.loads(s))
            except: pass
    return items

def export_instagram_csv(date: str, out_path: str) -> Path:
    items = _load_plan(date)
    approved_ig = [
        it for it in items
        if str(it.get("platform")) == "instagram"
        and (str(it.get("status") or "draft").lower() == "approved")
    ]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        # Common columns most schedulers accept / can be mapped
        w.writerow(["caption", "image", "alt_text"])
        for it in approved_ig:
            title = (it.get("title") or "").strip()
            snippet = (it.get("snippet") or it.get("joke") or "").strip()
            hashtags = (it.get("hashtags") or "").strip()
            base = (snippet or title).strip()
            cap = (base + (" " + hashtags if hashtags else "")).strip()
            w.writerow([cap, it.get("image") or "", it.get("alt") or ""])
    return out

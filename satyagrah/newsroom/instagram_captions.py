# D:\AISatyagrah\satyagrah\newsroom\instagram_captions.py
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT_DIR / "data" / "runs"
PLAN_NAME = "newsroom_plan.jsonl"

def _list_run_dates(rd: Path) -> List[str]:
    if not rd.exists(): return []
    out=[]
    for p in rd.iterdir():
        n=p.name
        if p.is_dir() and len(n)==10 and n[4]=="-" and n[7]=="-": out.append(n)
    return sorted(out)

def _resolve_date(date: Optional[str], rd: Path) -> str:
    return date or (_list_run_dates(rd)[-1] if _list_run_dates(rd) else (_ for _ in ()).throw(FileNotFoundError("No runs found")))

def _plan_path(date: str, rd: Path) -> Path:
    return rd / date / PLAN_NAME

def _load_plan(path: Path) -> List[Dict[str, Any]]:
    if not path.exists(): raise FileNotFoundError(f"{PLAN_NAME} not found: {path}")
    items=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if not line: continue
        try: items.append(json.loads(line))
        except json.JSONDecodeError: pass
    return items

def export_captions_from_plan(date: Optional[str]=None, runs_dir: Path=RUNS_DIR, platform: str="instagram") -> Path:
    resolved=_resolve_date(date, runs_dir)
    items=_load_plan(_plan_path(resolved, runs_dir))
    captions=[]
    for it in items:
        if it.get("platform")!=platform: continue
        if (it.get("status") or "").lower()!="approved": continue  # Step 3
        title = it.get("title") or it.get("summary") or ""
        snippet = it.get("snippet") or ""
        hashtags = it.get("hashtags") or ""
        txt="\n".join([x for x in (title, snippet, hashtags) if x]).strip()
        if txt: captions.append(txt)
    out = runs_dir / resolved / "instagram_captions.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for i,cap in enumerate(captions):
            if i>0: f.write("\n\n")
            f.write(cap)
    print(f"[newsroom.instagram_captions] Captions written to: {out}")
    return out

def main(argv: Optional[Iterable[str]]=None) -> Path:
    p=argparse.ArgumentParser()
    p.add_argument("--date", default=None)
    p.add_argument("--runs-dir", default=str(RUNS_DIR))
    p.add_argument("--platform", default="instagram")
    a=p.parse_args(list(argv) if argv is not None else None)
    return export_captions_from_plan(date=a.date, runs_dir=Path(a.runs_dir), platform=a.platform)

if __name__=="__main__":
    main()

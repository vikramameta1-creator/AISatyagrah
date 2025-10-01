from pathlib import Path

def resolve_latest_date(exports_root: Path) -> str | None:
    if not exports_root.exists():
        return None
    dates = [p.name for p in exports_root.iterdir()
             if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name[7] == "-"]
    return max(dates) if dates else None

from pathlib import Path
from typing import List, Optional
from PIL import Image


def _find_images(date: str, root: Path) -> List[Path]:
    hits: List[Path] = []
    for base in [root / "exports" / date, root / "data" / "runs" / date, root / "data" / "runs" / date / "art"]:
        if base.exists():
            hits += sorted(p for p in base.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    return hits[:120]


def run(*, date: str, exports_root: Path, files: Optional[List[str]] = None, duration_ms: Optional[int] = None, **_) -> Path:
    root = exports_root.parent
    outdir = exports_root / date
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "export.gif"

    imgs = [Path(f) for f in (files or []) if Path(f).exists()] or _find_images(date, root)
    if not imgs:
        raise RuntimeError("No images found for GIF export")

    frames = [Image.open(p).convert("RGB") for p in imgs]
    try:
        frames[0].save(path, save_all=True, append_images=frames[1:], optimize=True,
                       duration=int(duration_ms or 100), loop=0, format="GIF")
    finally:
        for fr in frames:
            try: fr.close()
            except Exception: pass
    return path

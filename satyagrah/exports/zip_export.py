from pathlib import Path
from typing import List, Optional
import zipfile


def _find_images(date: str, root: Path) -> List[Path]:
    hits: List[Path] = []
    for base in [
        root / "exports" / date,
        root / "data" / "runs" / date,
        root / "data" / "runs" / date / "art",
    ]:
        if base.exists():
            hits += sorted(
                p for p in base.rglob("*")
                if p.suffix.lower() in (".png", ".jpg", ".jpeg")
            )
    return hits


def run(
    *,
    date: str,
    exports_root: Path,
    files: Optional[List[str]] = None,
    **_,
) -> Path:
    """Zip all images (or selected ones)."""
    root = exports_root.parent
    outdir = exports_root / date
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "images.zip"

    imgs = [Path(f) for f in (files or []) if Path(f).exists()] or _find_images(date, root)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in imgs:
            arc = p.relative_to(root).as_posix()
            z.write(p, arcname=arc)
    return path

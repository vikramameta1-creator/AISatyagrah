from pathlib import Path
from typing import List, Optional
from PIL import Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from ..storage import captions as capstore

def _find_images(date: str, root: Path) -> List[Path]:
    hits: List[Path] = []
    for base in [root / "exports" / date, root / "data" / "runs" / date, root / "data" / "runs" / date / "art"]:
        if base.exists():
            hits += sorted(p for p in base.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    return hits[:120]

def run(*, date: str, exports_root: Path, files: Optional[List[str]] = None, **_) -> Path:
    root = exports_root.parent
    outdir = exports_root / date
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "contact_sheet.pdf"

    imgs = [Path(f) for f in (files or []) if Path(f).exists()] or _find_images(date, root)
    caps = capstore.load(root, date)

    c = canvas.Canvas(str(out), pagesize=landscape(A4))
    W, H = landscape(A4)

    def header():
        c.setFont("Helvetica-Bold", 16)
        c.drawString(36, H - 30, f"AISatyagrah — Contact Sheet — {date}")

    header()

    if not imgs:
        c.setFont("Helvetica", 12)
        c.drawString(36, H - 60, "No images found. (data/runs/<date>/art)")
        c.showPage()
        c.save()
        return out

    cols, rows = 3, 2
    margin, gutter = 36, 16
    cell_w = (W - 2 * margin - (cols - 1) * gutter) / cols
    cell_h = (H - 2 * margin - (rows - 1) * gutter - 32) / rows

    def draw_cell(px: int, py: int, p: Path):
        with Image.open(p) as im:
            iw, ih = im.size
        scale = min(cell_w / iw, (cell_h - 26) / ih)
        tw, th = iw * scale, ih * scale
        x = margin + px * (cell_w + gutter) + (cell_w - tw) / 2
        y = H - margin - (py + 1) * (cell_h + gutter) + (cell_h - th)
        c.drawImage(ImageReader(str(p)), x, y, tw, th, preserveAspectRatio=True, mask="auto")
        rel = p.relative_to(root).as_posix()
        meta = caps.get(rel, {})
        # filename line
        c.setFont("Helvetica", 9); c.setFillGray(0.9)
        c.drawString(margin + px * (cell_w + gutter) + 2, y - 12, p.name[:70])
        # caption line
        txt = (meta.get("caption") or "").strip()
        tags = (meta.get("hashtags") or "").strip()
        c.setFont("Helvetica", 10); c.setFillGray(1.0)
        line = (txt + (" " + tags if tags else "")).strip()[:110]
        if line:
            c.drawString(margin + px * (cell_w + gutter) + 2, y - 26, line)

    x = y = 0
    for p in imgs:
        draw_cell(x, y, p)
        x += 1
        if x == cols:
            x = 0
            y += 1
            if y == rows:
                c.showPage(); header(); y = 0
    c.showPage(); c.save()
    return out

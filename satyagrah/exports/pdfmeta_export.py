from pathlib import Path
from typing import Optional, List
from ..exporter_meta import write_pdf_for_topics


def run(*, date: str, exports_root: Path, files: Optional[List[str]] = None, **_) -> Path:
    """Generate Satyagraph topics PDF into exports/<date>/.

    This is similar to pdf_export.run but uses facts+satire topics instead
    of image contact sheets.
    """
    # exports_root is usually ROOT / "exports"
    outdir = exports_root / date
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "satyagraph_meta.pdf"
    write_pdf_for_topics(str(out), date)
    return out

from pathlib import Path
from typing import Optional, List
from ..exporter_meta import write_pptx_for_topics


def run(*, date: str, exports_root: Path, files: Optional[List[str]] = None, **_) -> Path:
    """Generate Satyagraph topics PPTX into exports/<date>/.

    This is similar to pptx_export.run but uses facts+satire topics.
    """
    outdir = exports_root / date
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "satyagraph_meta.pptx"
    write_pptx_for_topics(str(out), date)
    return out

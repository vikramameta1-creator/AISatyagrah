from pathlib import Path
from typing import List, Optional
import os


def _find_images(date: str, root: Path) -> List[Path]:
    hits: List[Path] = []
    for base in [root / "exports" / date, root / "data" / "runs" / date, root / "data" / "runs" / date / "art"]:
        if base.exists():
            hits += sorted(p for p in base.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    return hits[:120]


def _get_ImageSequenceClip():
    try:
        from moviepy.editor import ImageSequenceClip  # moviepy 1.x
        return ImageSequenceClip
    except Exception:
        pass
    try:
        from moviepy import ImageSequenceClip  # moviepy 2.x
        return ImageSequenceClip
    except Exception:
        pass
    from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
    return ImageSequenceClip


def run(*, date: str, exports_root: Path, files: Optional[List[str]] = None, fps: Optional[float] = None, **_) -> Path:
    root = exports_root.parent
    outdir = exports_root / date
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "export.mp4"

    try:
        import imageio_ffmpeg  # type: ignore
        os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    imgs = [Path(f) for f in (files or []) if Path(f).exists()] or _find_images(date, root)
    if not imgs:
        raise RuntimeError("No images found for MP4 export")

    ImageSequenceClip = _get_ImageSequenceClip()
    clip = ImageSequenceClip([str(p) for p in imgs], fps=fps or 1)
    clip.write_videofile(str(path), codec="libx264", audio=False, ffmpeg_params=["-pix_fmt", "yuv420p"])
    return path

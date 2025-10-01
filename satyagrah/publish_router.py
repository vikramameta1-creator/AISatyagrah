# satyagrah/publish_router.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
from .adapters import get_adapter
from .adapters.base import PublishResult

def _gather_files(outbox: Path, topic_id: str, platform: str) -> Tuple[List[Path], Dict[str, str]]:
    """
    Collect images and captions for a topic_id, preferring platform-specific
    assets: t<ID>_<platform>_* before generic t<ID>_*.
    """
    images: List[Path] = []
    captions: Dict[str, str] = {}

    # ---- images ----
    # 1) platform-specific
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        images.extend(sorted(outbox.glob(f"{topic_id}_{platform}_*{ext}")))
    # 2) generic fallback
    if not images:
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            images.extend(sorted(outbox.glob(f"{topic_id}_*{ext}")))

    # ---- captions ----
    # platform-specific: t<ID>_<platform>_caption_<lang>.txt
    for capfile in outbox.glob(f"{topic_id}_{platform}_caption_*.txt"):
        # e.g. t13_telegram_caption_en.txt -> en
        try:
            lang = capfile.stem.split("_caption_")[1]
        except Exception:
            lang = "en"
        captions[lang] = capfile.read_text(encoding="utf-8", errors="ignore").strip()

    # generic: t<ID>_caption_<lang>.txt (only fill missing langs)
    for capfile in outbox.glob(f"{topic_id}_caption_*.txt"):
        try:
            lang = capfile.stem.split("_caption_")[1]
        except Exception:
            lang = "en"
        if lang not in captions:
            captions[lang] = capfile.read_text(encoding="utf-8", errors="ignore").strip()

    return images, captions

def publish_to_platform(outbox: Path, topic_id: str, platform: str) -> PublishResult:
    adapter_cls = get_adapter(platform)
    if not adapter_cls:
        return PublishResult(False, f"Unknown platform '{platform}'")

    images, captions = _gather_files(outbox, topic_id, platform)
    if not images and not captions:
        return PublishResult(False, f"No images or captions found for {topic_id} in {outbox}")

    adapter = adapter_cls()
    return adapter.publish(images, captions)

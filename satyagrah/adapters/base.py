# satyagrah/adapters/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

class PublishResult:
    def __init__(self, ok: bool, message: str = "", meta: Optional[dict] = None):
        self.ok = ok
        self.message = message
        self.meta = meta or {}

    def __repr__(self) -> str:
        return f"PublishResult(ok={self.ok}, message={self.message!r})"

class SocialAdapter(ABC):
    """Base for all social adapters."""
    name: str  # e.g. "telegram"

    # Capability flags (extend as needed)
    supports_images: bool = True
    supports_albums: bool = False
    supports_video: bool = False
    max_caption_chars: int = 4096  # platform-specific; Telegram text is 4096, photo caption ~1024

    @abstractmethod
    def validate(self) -> bool:
        """Return True if required credentials present/valid."""
        raise NotImplementedError

    @abstractmethod
    def publish(self, images: List[Path], captions: Dict[str, str]) -> PublishResult:
        """
        images: list of image file paths to post
        captions: {"en": "...", "hi": "..."} or any langs you generate
        Return PublishResult.
        """
        raise NotImplementedError

# -*- coding: utf-8 -*-
# Platform presets: hashtag baselines, soft length caps, link formatting
from dataclasses import dataclass
from typing import List

@dataclass
class Preset:
    name: str
    base_tags: List[str]
    max_len: int  # soft cap; we'll trim summary first
    include_sources: bool

PRESETS = {
    "instagram": Preset(
        name="instagram",
        base_tags=["india","indiapolitics","delhi","mumbai","newdelhi"],
        max_len=2200,
        include_sources=True,
    ),
    "tiktok": Preset(
        name="tiktok",
        base_tags=["india","politics","satire"],
        max_len=2200,
        include_sources=False,
    ),
    "x": Preset(
        name="x",
        base_tags=["india","politics","satire"],
        max_len=270,  # leave room for hashtags
        include_sources=True,
    ),
    "youtube": Preset(
        name="youtube",
        base_tags=["india","politics","satire"],
        max_len=5000,
        include_sources=True,
    ),
}

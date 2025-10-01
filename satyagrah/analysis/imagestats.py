from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image

def _rgb_hex(rgb: Tuple[float, float, float]) -> str:
    r, g, b = [int(max(0, min(255, round(c)))) for c in rgb]
    return f"#{r:02x}{g:02x}{b:02x}"

def _brightness(rgb_arr: np.ndarray) -> float:
    # perceptual luminance, 0..1
    r, g, b = rgb_arr[..., 0], rgb_arr[..., 1], rgb_arr[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return float(y.mean())

def _dominant(rgb_arr: np.ndarray) -> Tuple[int, int, int]:
    # quantize to 16-level buckets per channel, pick the mode
    q = (rgb_arr / 16).astype(np.uint8)
    flat = q.reshape(-1, 3)
    # map (r<<8 | g<<4 | b)
    keys = (flat[:, 0] << 8) | (flat[:, 1] << 4) | flat[:, 2]
    key = int(np.bincount(keys).argmax())
    r = (key >> 8) & 0xF
    g = (key >> 4) & 0xF
    b = key & 0xF
    # dequantize back to 0..255 center
    return int(r * 16 + 8), int(g * 16 + 8), int(b * 16 + 8)

def analyze_image(path: Path) -> Dict[str, Any]:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    # speed: scale longest side to 256 px max
    scale = 256 / max(w, h)
    if scale < 1:
        im = im.resize((int(w * scale), int(h * scale)), Image.BILINEAR)
    arr = np.asarray(im, dtype=np.float32)
    avg = tuple(arr.reshape(-1, 3).mean(axis=0))
    dom = _dominant(arr)
    bright = _brightness(arr / 255.0)  # 0..1

    orient = "square"
    if w > h * 1.05: orient = "landscape"
    elif h > w * 1.05: orient = "portrait"

    meta = {
        "width": w, "height": h, "orientation": orient,
        "avg_hex": _rgb_hex(avg), "dom_hex": _rgb_hex(dom),
        "brightness": round(bright, 3),
    }
    meta["suggested_caption"], meta["suggested_tags"] = suggest(meta)
    return meta

def suggest(meta: Dict[str, Any]) -> Tuple[str, str]:
    mood = "moody" if meta["brightness"] < 0.35 else ("soft" if meta["brightness"] < 0.6 else "bright")
    orient = meta["orientation"]
    dom = meta["dom_hex"]
    cap = f"{mood} {orient} frame • tone {dom}"
    tags = " ".join([
        "#art", "#design", "#AISatyagrah",
        "#portrait" if orient == "portrait" else "#landscape" if orient == "landscape" else "#square",
        "#moody" if mood == "moody" else "#soft" if mood == "soft" else "#bright",
    ])
    return cap, tags

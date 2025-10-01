# -*- coding: utf-8 -*-
from PIL import Image
import pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[2]

def _date_or_today(d=None):
    return d or datetime.date.today().isoformat()

def make_thumbs(date: str | None = None):
    date = _date_or_today(date)
    exp = ROOT / "exports" / date
    exp.mkdir(parents=True, exist_ok=True)
    outs = []
    for stem in ["onepager_4x5", "onepager_1x1", "onepager_9x16"]:
        png = exp / f"{stem}.png"
        jpg = exp / f"{stem}.jpg"
        if png.exists():
            img = Image.open(png).convert("RGB")
            img.save(jpg, format="JPEG", quality=88, optimize=True, progressive=True)
            outs.append(jpg)
    return outs

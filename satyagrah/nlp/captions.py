# -*- coding: utf-8 -*-
import pathlib, datetime
from .i18n import make_caption_lines

ROOT = pathlib.Path(__file__).resolve().parents[2]

def _date_or_today(d=None):
    return d or datetime.date.today().isoformat()

def build_caption(one_liner: str, summary: str, lang: str = "en") -> str:
    lines = make_caption_lines(one_liner, summary, lang=lang)
    return "\n".join(lines)

def write_caption(date: str | None, text: str, lang: str = "en") -> pathlib.Path:
    date = _date_or_today(date)
    out_dir = ROOT / "exports" / date
    out_dir.mkdir(parents=True, exist_ok=True)
    # caption_en.txt, caption_hi.txt, etc.
    out = out_dir / f"caption_{lang.lower()}.txt"
    out.write_text(text, encoding="utf-8")
    return out

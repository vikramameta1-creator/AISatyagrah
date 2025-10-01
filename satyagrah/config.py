# -*- coding: utf-8 -*-
import pathlib
try:
    import yaml
except Exception:
    yaml = None  # graceful fallback if PyYAML missing

ROOT = pathlib.Path(__file__).resolve().parents[1]

def _read_yaml(path: pathlib.Path) -> dict:
    if not path.exists() or yaml is None:
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def load_feeds_yaml() -> dict:
    """Return {'rss': [...]} from configs/feeds.yaml (if present)."""
    cfg = _read_yaml(ROOT / "configs" / "feeds.yaml")
    rss = cfg.get("rss") or cfg.get("feeds") or []
    if isinstance(rss, str):
        rss = [rss]
    return {"rss": rss}

def load_settings() -> dict:
    """
    Return {'defaults': {...}} from configs/settings.yaml.
    Accepts either:
      defaults: { aspect: "4x5", watermark: "off", ... }
    or a flat map: { aspect: "4x5", watermark: "off", ... }
    """
    raw = _read_yaml(ROOT / "configs" / "settings.yaml")
    if not raw:
        return {"defaults": {}}
    if "defaults" in raw and isinstance(raw["defaults"], dict):
        return {"defaults": raw["defaults"]}
    return {"defaults": raw}

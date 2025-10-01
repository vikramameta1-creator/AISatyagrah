# -*- coding: utf-8 -*-
import base64, io, json, time, pathlib, requests
from PIL import Image
from ..config import load_settings

# project root: D:\AISatyagrah\satyagrah
ROOT = pathlib.Path(__file__).resolve().parents[2]

def _normalize_host(host: str) -> str:
    host = host or "http://127.0.0.1:7860"
    return host[:-1] if host.endswith("/") else host

def _prompt_path(date: str, topic_id: str) -> pathlib.Path:
    return ROOT / "data" / "runs" / date / "prompts" / f"{topic_id}.prompt.json"

def _art_dir(date: str) -> pathlib.Path:
    p = ROOT / "data" / "runs" / date / "art"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _sd_defaults() -> dict:
    s = (load_settings() or {}).get("defaults", {})
    return {
        "sd_timeout": int(s.get("sd_timeout", 60)),
        "sd_retries": int(s.get("sd_retries", 3)),
        "sampler_name": (s.get("sampler_name") or "").strip() or None,
    }

def _load_prompt(date: str, topic_id: str) -> dict:
    p = _prompt_path(date, topic_id)
    if not p.exists():
        # Fallback minimal prompt if missing (pipeline normally writes this before calling us)
        return {
            "positive": f"High-contrast political satire poster about {topic_id}",
            "negative": "",
            "width": 768,
            "height": 960,
            "steps": 30,
            "cfg_scale": 7.0,
            "sampler_name": "DPM++ 2M Karras",
        }
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def _payload_from_prompt(pr: dict, seed=None) -> dict:
    positive = pr.get("positive", "")
    negative = pr.get("negative", "")
    width    = int(pr.get("width", 768))
    height   = int(pr.get("height", 960))
    steps    = int(pr.get("steps", 30))
    cfg      = float(pr.get("cfg_scale", 7.0))
    sampler  = pr.get("sampler_name", "DPM++ 2M Karras")

    payload = {
        "prompt": positive,
        "negative_prompt": negative,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg,
        "sampler_name": sampler,
        # -1 → random; specific int → reproducible
        "seed": int(seed) if seed is not None else -1,
    }
    if seed is not None:
        payload["subseed_strength"] = 0
    # settings override for sampler (optional)
    sd = _sd_defaults()
    if sd.get("sampler_name"):
        payload["sampler_name"] = sd["sampler_name"]
    return payload

def _save_png_atomic(b64png: str, out_path: pathlib.Path) -> pathlib.Path:
    raw = base64.b64decode(b64png)
    img = Image.open(io.BytesIO(raw))
    tmp = out_path.with_suffix(out_path.suffix + ".part")
    img.save(tmp, format="PNG")
    tmp.replace(out_path)
    return out_path

def generate_image_for_id(topic_id: str, date: str, host: str = "http://127.0.0.1:7860", seed=None) -> pathlib.Path:
    """
    Create hero PNG at data/runs/<date>/art/<topic_id>_hero.png using AUTOMATIC1111 /sdapi/v1/txt2img.
    Also copies the prompt JSON next to the hero as data/runs/<date>/art/<topic_id>.prompt.json.
    Returns the hero path.
    """
    host = _normalize_host(host)
    pr = _load_prompt(date, topic_id)
    payload = _payload_from_prompt(pr, seed=seed)

    url = f"{host}/sdapi/v1/txt2img"
    sd = _sd_defaults()
    timeout = int(sd["sd_timeout"])
    retries = int(sd["sd_retries"])
    last_err = None

    for attempt in range(1, retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            images = data.get("images") or []
            if not images:
                raise RuntimeError("No images returned from SD API")

            art_dir = _art_dir(date)
            hero = art_dir / f"{topic_id}_hero.png"
            _save_png_atomic(images[0], hero)

            # Keep a copy of the prompt JSON alongside the hero
            (art_dir / f"{topic_id}.prompt.json").write_text(
                json.dumps(pr, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return hero
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.2)
            else:
                raise RuntimeError(f"Image generation failed after {retries} attempts: {last_err}") from last_err


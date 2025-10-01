from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import json, os, re, requests

from .base import SocialAdapter, PublishResult
from .registry import register
from ..secrets import get_secret

def _compose_caption(captions: Dict[str,str], order=("en","hi")) -> str:
    def esc(s:str)->str: return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    for lang in order:
        if lang in captions and captions[lang].strip():
            return esc(captions[lang].strip())[:1024]
    if captions:
        return esc(next(iter(captions.values())).strip())[:1024]
    return ""

@register
class TelegramAdapter(SocialAdapter):
    name = "telegram"

    def __init__(self):
        self.token = (get_secret("telegram","bot_token") or os.getenv("TG_BOT_TOKEN","")).strip()
        self.chat_id = (get_secret("telegram","chat_id") or os.getenv("TG_CHAT_ID","")).strip()

    def validate(self) -> bool:
        return bool(self.token and self.chat_id and re.match(r"^\d+:[A-Za-z0-9_\-]{30,}$", self.token))

    def _send_photo(self, image: Path, caption: str) -> dict:
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        files = {"photo": image.open("rb")}
        data = {"chat_id": self.chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        r = requests.post(url, data=data, files=files, timeout=60)
        r.raise_for_status()
        return r.json()

    def _send_media_group(self, images: List[Path], caption: str) -> dict:
        url = f"https://api.telegram.org/bot{self.token}/sendMediaGroup"
        media, files = [], {}
        for i, p in enumerate(images):
            k = f"photo{i}"
            files[k] = p.open("rb")
            item = {"type":"photo", "media": f"attach://{k}"}
            if i == 0 and caption:
                item["caption"] = caption
                item["parse_mode"] = "HTML"
            media.append(item)
        data = {"chat_id": self.chat_id, "media": json.dumps(media, ensure_ascii=False)}
        r = requests.post(url, data=data, files=files, timeout=120)
        r.raise_for_status()
        return r.json()

    def publish(self, images: List[Path], captions: Dict[str, str]) -> PublishResult:
        if not self.validate():
            return PublishResult(False, "Telegram credentials missing/invalid")
        if not images:
            return PublishResult(False, "No images to send")
        cap = _compose_caption(captions, ("en","hi"))
        try:
            if len(images) == 1:
                res = self._send_photo(images[0], cap)
            else:
                res = self._send_media_group(images[:10], cap)
            return PublishResult(True, "sent", {"response": res})
        except requests.HTTPError as e:
            try:
                payload = e.response.json()
            except Exception:
                payload = e.response.text if e.response is not None else str(e)
            return PublishResult(False, f"HTTP error: {payload}")
        except Exception as e:
            return PublishResult(False, f"Error: {e}")

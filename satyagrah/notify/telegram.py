# -*- coding: utf-8 -*-
import os, json, urllib.request

def send(text: str) -> bool:
    token = os.getenv("SATYAGRAH_TELEGRAM_BOT_TOKEN")
    chat  = os.getenv("SATYAGRAH_TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return 200 <= getattr(r, "status", 200) < 300

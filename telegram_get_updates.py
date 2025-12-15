import os
import json
import requests

token = os.environ.get("SATYAGRAH_TELEGRAM_BOT", "").strip()
if not token:
    raise SystemExit("SATYAGRAH_TELEGRAM_BOT is not set")

url = f"https://api.telegram.org/bot{token}/getUpdates"
print("URL:", url)

r = requests.get(url, timeout=15)
print("Status:", r.status_code)
try:
    data = r.json()
except Exception as e:
    print("Error decoding JSON:", e)
    print("Raw text:", r.text[:500])
    raise

print(json.dumps(data, indent=2, ensure_ascii=False))

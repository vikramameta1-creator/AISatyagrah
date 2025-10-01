import requests

def get_status(base="http://127.0.0.1:7861") -> dict:
    return requests.get(f"{base}/api/status", timeout=3).json()

def set_share(base, pct: int) -> dict:
    return requests.post(f"{base}/api/share", json={"pct": pct}, timeout=3).json()

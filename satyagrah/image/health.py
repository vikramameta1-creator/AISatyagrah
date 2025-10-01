# -*- coding: utf-8 -*-
import requests

def sdapi_ping(host: str, timeout_s: int = 3) -> bool:
    try:
        r = requests.get(host.rstrip("/") + "/sdapi/v1/progress", timeout=timeout_s)
        return r.ok
    except Exception:
        return False

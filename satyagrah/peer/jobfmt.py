# -*- coding: utf-8 -*-
import base64, hashlib, hmac, json, time, zipfile, io, os, datetime
from pathlib import Path

def _secret() -> bytes:
    s = os.getenv("SATYAGRAH_SECRET")
    if not s: raise RuntimeError("SATYAGRAH_SECRET not set")
    return s.encode("utf-8")

def _canon(obj) -> bytes:
    return json.dumps(obj, separators=(",",":"), sort_keys=True, ensure_ascii=False).encode("utf-8")

def sign_payload(payload: dict) -> str:
    mac = hmac.new(_secret(), _canon(payload), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode("utf-8").rstrip("=")

def verify_payload(payload: dict, sig: str) -> bool:
    try:
        mac = base64.urlsafe_b64decode(sig + "==")
        exp = hmac.new(_secret(), _canon(payload), hashlib.sha256).digest()
        return hmac.compare_digest(mac, exp)
    except Exception:
        return False

def make_job_dict(job_id: str, requester: str, tasks: list, ttl_hours=24):
    now = int(time.time())
    return {
        "id": job_id,
        "requester": requester,
        "created": now,
        "expires": now + ttl_hours*3600,
        "version": 1,
        "tasks": tasks,  # e.g. [{"type":"txt2img","prompt":"...","seed":123,"steps":28,"width":768,"height":1024,"count":1}]
    }

def write_job_zip(job: dict, out_zip: Path):
    payload = {"job": job}
    payload["sig"] = sign_payload(payload)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("job.json", json.dumps(payload, indent=2, ensure_ascii=False))

def read_job_zip(in_zip: Path) -> dict:
    with zipfile.ZipFile(in_zip, "r") as z:
        jobj = json.loads(z.read("job.json").decode("utf-8"))
    payload = {"job": jobj.get("job")}
    sig = jobj.get("sig","")
    if not verify_payload(payload, sig): raise RuntimeError("Invalid job signature")
    if int(time.time()) > int(payload["job"]["expires"]): raise RuntimeError("Job expired")
    return payload["job"]

def write_result_zip(job: dict, images: list[tuple[str, bytes]], out_zip: Path, ok=True, errors=None):
    result = {
        "job_id": job["id"],
        "ok": bool(ok),
        "errors": errors or [],
        "images": [name for name,_ in images],
        "created": int(time.time()),
        "version": 1
    }
    payload = {"result": result}
    payload["sig"] = sign_payload(payload)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("result.json", json.dumps(payload, indent=2, ensure_ascii=False))
        for name, data in images:
            z.writestr(name, data)

def read_result_zip(in_zip: Path) -> dict:
    with zipfile.ZipFile(in_zip, "r") as z:
        robj = json.loads(z.read("result.json").decode("utf-8"))
    payload = {"result": robj.get("result")}
    sig = robj.get("sig","")
    if not verify_payload(payload, sig): raise RuntimeError("Invalid result signature")
    return payload["result"]

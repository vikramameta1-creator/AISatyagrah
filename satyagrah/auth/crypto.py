# -*- coding: utf-8 -*-
import base64, hashlib, hmac, os, secrets, time

def hash_password(password: str, *, salt: bytes=None) -> str:
    salt = salt or secrets.token_bytes(16)
    key  = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return base64.b64encode(salt + key).decode("utf-8")

def verify_password(password: str, encoded: str) -> bool:
    raw  = base64.b64decode(encoded.encode("utf-8"))
    salt, key = raw[:16], raw[16:]
    new = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(new, key)

def get_secret() -> bytes:
    s = os.getenv("SATYAGRAH_SECRET")
    if not s:
        raise RuntimeError("SATYAGRAH_SECRET not set")
    return s.encode("utf-8")

def new_token() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(24)).decode("utf-8").rstrip("=")

def sign_session(token: str) -> str:
    mac = hmac.new(get_secret(), token.encode("utf-8"), hashlib.sha256).digest()
    return f"{token}.{base64.urlsafe_b64encode(mac).decode('utf-8').rstrip('=')}"

def verify_session(signed: str) -> str | None:
    try:
        token, mac_b64 = signed.rsplit(".", 1)
        mac = base64.urlsafe_b64decode(mac_b64 + "==")
        exp = hmac.new(get_secret(), token.encode("utf-8"), hashlib.sha256).digest()
        return token if hmac.compare_digest(mac, exp) else None
    except Exception:
        return None

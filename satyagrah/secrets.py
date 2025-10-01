# satyagrah/secrets.py
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Dict, List, Optional

try:
    import keyring  # Uses Windows Credential Manager on Windows
    HAVE_KEYRING = True
except Exception:
    keyring = None
    HAVE_KEYRING = False

NAMESPACE = "AISatyagrah"
ROOT = Path(os.environ.get("SATY_ROOT") or Path(__file__).resolve().parents[1])
INDEX_PATH = ROOT / "configs" / "creds_index.json"  # stores key *names* only (not values)

def _svc(service: str) -> str:
    return f"{NAMESPACE}:{service.strip().lower()}"

def _load_index() -> Dict[str, List[str]]:
    try:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        if INDEX_PATH.exists():
            return json.loads(INDEX_PATH.read_text(encoding="utf-8") or "{}")
    except Exception:
        pass
    return {}

def _save_index(idx: Dict[str, List[str]]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")

def list_keys(service: str) -> List[str]:
    idx = _load_index()
    return list(dict.fromkeys(idx.get(service.lower(), [])))  # unique, keep order

def set_secret(service: str, key: str, value: str) -> None:
    if not HAVE_KEYRING:
        raise RuntimeError("keyring not available. Install with: pip install keyring")
    keyring.set_password(_svc(service), key, value)
    idx = _load_index()
    items = idx.get(service.lower(), [])
    if key not in items:
        items.append(key)
        idx[service.lower()] = items
        _save_index(idx)

def get_secret(service: str, key: str) -> Optional[str]:
    if not HAVE_KEYRING:
        raise RuntimeError("keyring not available. Install with: pip install keyring")
    return keyring.get_password(_svc(service), key)

def delete_secret(service: str, key: str) -> bool:
    if not HAVE_KEYRING:
        raise RuntimeError("keyring not available. Install with: pip install keyring")
    from keyring.errors import PasswordDeleteError
    try:
        keyring.delete_password(_svc(service), key)
        idx = _load_index()
        items = [k for k in idx.get(service.lower(), []) if k != key]
        idx[service.lower()] = items
        _save_index(idx)
        return True
    except PasswordDeleteError:
        return False

def clear_service(service: str) -> int:
    """Remove all keys for a service (best-effort)."""
    keys = list_keys(service)
    n = 0
    for k in keys:
        if delete_secret(service, k):
            n += 1
    return n

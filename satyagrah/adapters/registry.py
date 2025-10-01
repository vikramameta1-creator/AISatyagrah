from __future__ import annotations
from typing import Dict, Type, Optional
from .base import SocialAdapter

_REG: Dict[str, Type[SocialAdapter]] = {}

def register(adapter_cls: Type[SocialAdapter]):
    name = getattr(adapter_cls, "name", None)
    if not name:
        raise ValueError("Adapter class missing .name")
    _REG[name] = adapter_cls
    return adapter_cls

def get(name: str) -> Optional[SocialAdapter]:
    cls = _REG.get(name)
    return cls() if cls else None

def names():
    return sorted(_REG.keys())

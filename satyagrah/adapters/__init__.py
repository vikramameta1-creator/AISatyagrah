# satyagrah/adapters/__init__.py
from __future__ import annotations
from typing import Dict, Type, Optional
from .base import SocialAdapter

_REGISTRY: Dict[str, Type[SocialAdapter]] = {}

def register_adapter(cls: Type[SocialAdapter]) -> Type[SocialAdapter]:
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError("Adapter must define class attribute 'name'")
    _REGISTRY[name.lower()] = cls
    return cls

def get_adapter(name: str) -> Optional[Type[SocialAdapter]]:
    return _REGISTRY.get(name.lower())

def available_adapters():
    return sorted(_REGISTRY.keys())

from typing import Callable, Dict
from pathlib import Path

Handler = Callable[[Path, dict], bytes]  # input: result_zip, options -> bytes

class ExportRegistry:
    def __init__(self):
        self._h: Dict[str, Handler] = {}
    def register(self, name: str, fn: Handler): self._h[name] = fn
    def get(self, name: str) -> Handler: return self._h[name]

registry = ExportRegistry()

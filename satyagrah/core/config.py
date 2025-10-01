# satyagrah/core/config.py
from __future__ import annotations
import os
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parents[1]   # .../satyagrah
PROJ = ROOT.parent                            # project root (e.g., D:\AISatyagrah)

# Base data dirs (overridable via env)
RUNS    = Path(os.getenv("SATYAGRAH_RUNS",    str(PROJ / "runs")))
EXPORTS = Path(os.getenv("SATYAGRAH_EXPORTS", str(PROJ / "exports")))
LOGS    = Path(os.getenv("SATYAGRAH_LOGS",    str(PROJ / "logs")))
LOCKS   = Path(os.getenv("SATYAGRAH_LOCKS",   str(PROJ / "locks")))

# External service & secret
SD_HOST = os.getenv("SATYAGRAH_SD_HOST", "http://127.0.0.1:7860")
SECRET  = os.getenv("SATYAGRAH_SECRET", "")

def ensure_dirs() -> None:
    """Ensure all expected directories exist."""
    for p in (RUNS, EXPORTS, LOGS, LOCKS):
        p.mkdir(parents=True, exist_ok=True)

# D:\AISatyagrah\satyagrah\paths.py

from __future__ import annotations

from pathlib import Path

# Root of the project, e.g. D:\AISatyagrah
ROOT_DIR = Path(__file__).resolve().parent.parent

# Data directory: D:\AISatyagrah\data
DATA_DIR = ROOT_DIR / "data"

# Runs directory: D:\AISatyagrah\data\runs
RUNS_DIR = DATA_DIR / "runs"

# UI directory for HTML/JS/CSS: D:\AISatyagrah\ui
UI_DIR = ROOT_DIR / "ui"

# Exports directory for generated outputs: D:\AISatyagrah\exports
EXPORTS_DIR = ROOT_DIR / "exports"

# Make sure key directories exist (no error if they already exist)
for p in (DATA_DIR, RUNS_DIR, EXPORTS_DIR):
    p.mkdir(parents=True, exist_ok=True)

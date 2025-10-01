# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
from .config import LOGS, ensure_dirs

def get_logger(name="satyagrah"):
    ensure_dirs()
    logger = logging.getLogger(name)
    if logger.handlers:  # avoid double handlers if called twice
        return logger
    logger.setLevel(logging.INFO)
    fh = RotatingFileHandler(LOGS / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    ch = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh.setFormatter(fmt); ch.setFormatter(fmt)
    logger.addHandler(fh); logger.addHandler(ch)
    return logger

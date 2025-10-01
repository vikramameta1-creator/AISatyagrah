# -*- coding: utf-8 -*-
"""
PeerAgent — single-file volunteer app wrapper.
- Uses inbox/ and out/ folders next to the EXE
- Serves the control panel at http://127.0.0.1:8090
- If SATYAGRAH_SECRET is missing, reads ./secret.txt (one line)
- Writes crash logs to peer_agent_error.log next to the EXE
"""
import os, sys, json, webbrowser, traceback, importlib
from pathlib import Path

def _basedir() -> Path:
    if getattr(sys, "frozen", False):  # PyInstaller
        return Path(os.path.dirname(sys.executable)).resolve()
    return Path(__file__).resolve().parent

def _log_error(base: Path, exc: Exception):
    try:
        (base / "peer_agent_error.log").write_text(
            "=== PeerAgent crash ===\n" + "".join(traceback.format_exception(exc)),
            encoding="utf-8"
        )
    except Exception:
        pass

def _ensure_secret(base: Path):
    if os.getenv("SATYAGRAH_SECRET"):
        return True
    sec_file = base / "secret.txt"
    if sec_file.exists():
        os.environ["SATYAGRAH_SECRET"] = sec_file.read_text(encoding="utf-8").strip()
        return True
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "Please set SATYAGRAH_SECRET or put it in a file named 'secret.txt' here.\n\n"
            "The agent will run, but it won't process jobs until the secret is set.",
            "AISatyagrah Peer Agent",
            0x40
        )
    except Exception:
        pass
    return False

def main():
    base = _basedir()
    os.chdir(base)  # keep all files next to the EXE
    inbox  = base / "inbox"
    outbox = base / "out"
    state  = base / "agent_state.db"
    cfg    = base / "agent_config.json"
    inbox.mkdir(exist_ok=True); outbox.mkdir(exist_ok=True)

    if not cfg.exists():
        cfg.write_text(json.dumps({
            "sd_host": "http://127.0.0.1:7860",
            "max_per_day": 5,
            "share_percent": 50,
            "paused": False,
            "inactivity_minutes": 120
        }, indent=2), encoding="utf-8")

    _ensure_secret(base)

    try:
        webbrowser.open("http://127.0.0.1:8090")
    except Exception:
        pass

    # Import the bundled agent submodule explicitly (works in PyInstaller)
    try:
        agent_mod = importlib.import_module("satyagrah.peer.agent")
    except Exception as e:
        _log_error(base, e)
        raise

    # call the real agent
    sys.argv = [
        "peer-agent", "run",
        "--inbox", str(inbox),
        "--outbox", str(outbox),
        "--state", str(state),
        "--config", str(cfg),
        "--panel-port", "8090"
    ]
    agent_mod.main()

if __name__ == "__main__":
    try:
        main()
    except Exception as _e:
        _log_error(_basedir(), _e)
        raise

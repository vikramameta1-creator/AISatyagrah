# -*- coding: utf-8 -*-
import argparse, os
from pathlib import Path

TEMPLATE_README = """\
AISatyagrah Peer GPU Agent (Volunteer)
======================================

This folder lets you help render images securely for AISatyagrah.

Prereqs:
- Python 3.10+ installed
- Stable Diffusion API at: {sd_host} (AUTOMATIC1111 or compatible)
- A shared secret from the coordinator

First-time setup:
1) Open a terminal here.
2) Set your secret:
   Windows (PowerShell):  $env:SATYAGRAH_SECRET = "{secret_here}"
   macOS/Linux (bash):    export SATYAGRAH_SECRET="{secret_here}"
3) (Optional) change settings in agent_config.json

Run:
- Windows: double-click  run_agent_windows.bat
- macOS/Linux:            ./run_agent_unix.sh

Control Panel:
- After starting, open http://127.0.0.1:8090 for:
  • GPU Share meter (0–100%)
  • Daily limit
  • Pause/Resume
  • Quit
  • Live status (queue, last job, processed today)
"""

RUN_WIN = r"""@echo off
setlocal
REM --- Paths (relative to this folder) ---
set ROOT=%~dp0
set INBOX=%ROOT%inbox
set OUTBOX=%ROOT%out
set STATE=%ROOT%agent_state.db
set CFG=%ROOT%agent_config.json
set SDHOST=

if "%SATYAGRAH_SECRET%"=="" (
  echo [ERROR] SATYAGRAH_SECRET is not set. See README.txt
  pause
  exit /b 1
)

REM ensure folders
if not exist "%INBOX%" mkdir "%INBOX%"
if not exist "%OUTBOX%" mkdir "%OUTBOX%"

python -m satyagrah.peer.agent run --inbox "%INBOX%" --outbox "%OUTBOX%" --state "%STATE%" --config "%CFG%" --panel-port 8090 %SDHOST%
pause
"""

RUN_UNIX = """#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
INBOX="$ROOT/inbox"
OUTBOX="$ROOT/out"
STATE="$ROOT/agent_state.db"
CFG="$ROOT/agent_config.json"
SDHOST=""

if [[ -z "${SATYAGRAH_SECRET:-}" ]]; then
  echo "[ERROR] SATYAGRAH_SECRET is not set. See README.txt" >&2
  exit 1
fi

mkdir -p "$INBOX" "$OUTBOX"
python -m satyagrah.peer.agent run --inbox "$INBOX" --outbox "$OUTBOX" --state "$STATE" --config "$CFG" --panel-port 8090 $SDHOST
"""

DEFAULT_CONFIG = {
    "sd_host": "http://127.0.0.1:7860",
    "max_per_day": 5,
    "share_percent": 50,
    "paused": False,
    "inactivity_minutes": 120
}

def main():
    ap = argparse.ArgumentParser(description="Build volunteer peer agent pack")
    ap.add_argument("--out", required=True, help="output folder for the volunteer pack")
    ap.add_argument("--sd-host", default="http://127.0.0.1:7860")
    ap.add_argument("--secret-placeholder", default="<ask-coordinator>")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "inbox").mkdir(parents=True, exist_ok=True)
    (out / "out").mkdir(parents=True, exist_ok=True)

    # scripts
    (out / "run_agent_windows.bat").write_text(RUN_WIN, encoding="utf-8")
    (out / "run_agent_unix.sh").write_text(RUN_UNIX, encoding="utf-8")
    os.chmod(out / "run_agent_unix.sh", 0o755)

    # config + readme
    cfg = dict(DEFAULT_CONFIG); cfg["sd_host"] = args.sd_host
    (out / "agent_config.json").write_text(json_dump(cfg), encoding="utf-8")
    (out / "README.txt").write_text(TEMPLATE_README.format(sd_host=args.sd_host, secret_here=args.secret_placeholder), encoding="utf-8")

    print("Volunteer pack written to:", out)

def json_dump(obj):  # tiny helper to avoid importing json at module top
    import json
    return json.dumps(obj, indent=2)

if __name__ == "__main__":
    main()

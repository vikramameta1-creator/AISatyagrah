AISatyagrah Peer GPU Agent (Volunteer)
======================================

This folder lets you help render images securely for AISatyagrah.

Prereqs:
- Python 3.10+ installed
- Stable Diffusion API at: http://127.0.0.1:7860 (AUTOMATIC1111 or compatible)
- A shared secret from the coordinator

First-time setup:
1) Open a terminal here.
2) Set your secret:
   Windows (PowerShell):  $env:SATYAGRAH_SECRET = "<ask-coordinator>"
   macOS/Linux (bash):    export SATYAGRAH_SECRET="<ask-coordinator>"
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

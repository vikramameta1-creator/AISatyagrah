$env:SATYAGRAH_NO_AUTH = "1"        # dev mode; remove later to enable login
cd D:\AISatyagrah
.\.venv\Scripts\uvicorn.exe satyagrah.webui:app --host 127.0.0.1 --port 8010

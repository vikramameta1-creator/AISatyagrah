$env:SATYAGRAH_SD_HOST      = 'http://127.0.0.1:7860'
$env:SATYAGRAH_PEER_OUTBOX  = 'D:\AISatyagrah\jobs\outbox'
$env:SATYAGRAH_PEER_INBOX   = 'D:\AISatyagrah\dist\peer_agent_exe\inbox'
$env:SATYAGRAH_PEER_RESULTS = 'D:\AISatyagrah\jobs\peer_out'
& 'D:\AISatyagrah\.venv\Scripts\python.exe' -m satyagrah.webui --port 8010

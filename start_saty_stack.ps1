# D:\AISatyagrah\start_saty_stack.ps1
# Minimal, reliable launcher that starts SD mock (7860) and Web UI (8000)
# in separate console windows using your existing .bat files.

param()  # no params for now (keeps it simple & robust)

$Project = "D:\AISatyagrah"
$env:SATY_ROOT = $Project

# Start SD mock API (port 7860) in its own window
Start-Process -FilePath "$Project\start_sd_mock.bat" -WorkingDirectory $Project -WindowStyle Normal -Verb Open

# Small delay so SD mock gets a head start
Start-Sleep -Seconds 2

# Start Web UI (port 8000) in its own window
Start-Process -FilePath "$Project\start_saty_web.bat" -WorkingDirectory $Project -WindowStyle Normal -Verb Open

. "$PSScriptRoot\patch.ps1"
Set-JsonField "D:\AISatyagrah\config\renderers.json" "active" "automatic1111"
Set-JsonField "D:\AISatyagrah\config\renderers.json" "automatic1111.host" "http://127.0.0.1:7860"
Set-JsonField "D:\AISatyagrah\config\renderers.json" "automatic1111.timeout_sec" 180
Write-Host "Renderer set to AUTOMATIC1111 at 127.0.0.1:7860"

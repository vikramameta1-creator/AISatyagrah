. "$PSScriptRoot\patch.ps1"
Set-JsonField "D:\AISatyagrah\config\storage.json" "paths.hot"  "D:\\AISatyagrah\\data\\hot"
Set-JsonField "D:\AISatyagrah\config\storage.json" "paths.warm" "D:\\AISatyagrah\\data\\warm"
Set-JsonField "D:\AISatyagrah\config\storage.json" "paths.cold" "D:\\AISatyagrah\\archive"
Set-JsonField "D:\AISatyagrah\config\storage.json" "cache.prompt_images_mb" 15360
Set-JsonField "D:\AISatyagrah\config\storage.json" "cache.upscales_mb" 10240
Write-Host "Storage paths & cache caps updated."

. "$PSScriptRoot\patch.ps1"
Set-JsonField "D:\AISatyagrah\config\settings.json" "features.bilingual_captions.enabled" $true
Set-JsonField "D:\AISatyagrah\config\settings.json" "locale.default_primary" "en-IN"
Set-JsonField "D:\AISatyagrah\config\settings.json" "locale.secondary" "hi-IN"
Write-Host "Bilingual captions enabled (EN primary, HI secondary)."

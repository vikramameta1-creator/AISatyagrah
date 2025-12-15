Start-Process pwsh -ArgumentList "-NoLogo -NoExit -ExecutionPolicy Bypass -File `"$PSScriptRoot\run_api.ps1`""
Start-Process pwsh -ArgumentList "-NoLogo -NoExit -ExecutionPolicy Bypass -File `"$PSScriptRoot\run_worker.ps1`""

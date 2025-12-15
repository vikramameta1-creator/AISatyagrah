[CmdletBinding()]
param(
  [Parameter(Mandatory)] [string]$File,
  [Parameter(Mandatory)] [string]$Key,
  [Parameter(Mandatory)] [string]$Value
)

if (-not (Test-Path $File)) {
  throw "File not found: $File"
}

# Append a stamped comment safely (fixes $key: $value ':' issue)
$stamp = "`r`n# PATCH $(Get-Date -Format 'u')`r`n# $($Key): $Value`r`n"
Add-Content -Path $File -Value $stamp -Encoding UTF8
Write-Host "Patched $File with: $($Key): $Value"

#Requires -Version 5.1
<#
.SYNOPSIS
  Removes PowerPilot's registration from Power BI Desktop's External Tools folder.

.DESCRIPTION
  Deletes only PowerPilot.pbitool.json. Measures PowerPilot already added to a report stay: they are
  ordinary measures in the PowerPilot display folder, and Power BI owns them.
#>
[CmdletBinding()]
param(
    [string]$TargetDir = (Join-Path ${env:CommonProgramFiles(x86)} 'Microsoft Shared\Power BI Desktop\External Tools')
)

$ErrorActionPreference = 'Stop'
$target = Join-Path $TargetDir 'PowerPilot.pbitool.json'

if (-not (Test-Path $target)) {
    Write-Host "PowerPilot is not registered (nothing at $target)."
    exit 0
}

try {
    Remove-Item -LiteralPath $target -Confirm:$false
}
catch [System.UnauthorizedAccessException] {
    Write-Host "`nWindows denied access to $TargetDir`nRun this script from an administrator PowerShell.`n" -ForegroundColor Red
    exit 1
}

Write-Host "Removed $target. Restart Power BI Desktop to clear the ribbon button."

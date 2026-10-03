#Requires -Version 5.1
<#
.SYNOPSIS
  Registers PowerPilot with Power BI Desktop so it appears on the External Tools ribbon.

.DESCRIPTION
  Power BI Desktop loads every *.pbitool.json it finds in
    C:\Program Files (x86)\Common Files\Microsoft Shared\Power BI Desktop\External Tools
  at startup. That folder is machine-wide, so writing to it needs an elevated PowerShell.
  This script fills in the absolute paths (Desktop needs a fully qualified executable path) and
  writes PowerPilot.pbitool.json there.

.PARAMETER Python
  The pythonw.exe that has PowerPilot's requirements (including requirements-powerbi.txt).
  Defaults to backend\.venv\Scripts\pythonw.exe in this repository.

.PARAMETER TargetDir
  Where to write the registration file. Defaults to Desktop's External Tools folder; override it to
  preview the result without administrator rights.
#>
[CmdletBinding()]
param(
    [string]$Python,
    [string]$TargetDir = (Join-Path ${env:CommonProgramFiles(x86)} 'Microsoft Shared\Power BI Desktop\External Tools')
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$launcher = Join-Path $PSScriptRoot 'launcher.py'
$template = Join-Path $PSScriptRoot 'powerpilot.pbitool.json'
if (-not $Python) { $Python = Join-Path $repo 'backend\.venv\Scripts\pythonw.exe' }

function Stop-With([string]$Message) { Write-Host "`n$Message`n" -ForegroundColor Red; exit 1 }

if (-not (Test-Path $Python)) {
    Stop-With "Could not find $Python`nCreate the backend environment first (see docs\powerbi-external-tool.md), or pass -Python <path to pythonw.exe>."
}
if (-not (Test-Path (Join-Path $repo 'frontend\dist\index.html'))) {
    Stop-With "PowerPilot's interface has not been built.`nRun:  cd `"$repo\frontend`"; npm install; npm run build"
}

# The libraries pythonnet loads come with Power BI Desktop, but pythonnet itself must be installed.
$console = Join-Path (Split-Path $Python) 'python.exe'
& $console -c "import clr" 2>$null
if ($LASTEXITCODE -ne 0) {
    Stop-With "pythonnet is not installed for $console`nRun:  `"$console`" -m pip install -r `"$repo\backend\requirements-powerbi.txt`""
}

# JSON strings need backslashes doubled; do it once, here, rather than trusting hand-escaped paths.
function Escape-Json([string]$Text) { $Text.Replace('\', '\\') }
$json = (Get-Content $template -Raw).Replace('__PYTHONW__', (Escape-Json $Python)).Replace('__LAUNCHER__', (Escape-Json $launcher))
$null = $json | ConvertFrom-Json   # refuse to write something Desktop would silently ignore

try {
    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    $target = Join-Path $TargetDir 'PowerPilot.pbitool.json'
    Set-Content -Path $target -Value $json -Encoding UTF8
}
catch [System.UnauthorizedAccessException] {
    Stop-With "Windows denied access to:`n  $TargetDir`nRight-click PowerShell, choose 'Run as administrator', and run this script again."
}

Write-Host "`nRegistered PowerPilot:" -ForegroundColor Green
Write-Host "  $target"
Write-Host "`nRestart Power BI Desktop, open a report, and look for PowerPilot on the External Tools ribbon.`n"

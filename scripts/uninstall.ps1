# Remove the worldcanon sidecar from Windows.
# Usage:  .\uninstall.ps1 [-KeepFiles]

param(
    [switch]$KeepFiles
)

$ErrorActionPreference = "Stop"
$TaskName = "WorldbuilderCanonSidecar"
$InstallDir = Join-Path $env:LOCALAPPDATA "WorldbuilderCanon"

# Stop + unregister the task
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task: $TaskName"
} else {
    Write-Host "No scheduled task found."
}

# Kill any lingering process
Get-Process -Name "worldcanon-sidecar" -ErrorAction SilentlyContinue | Stop-Process -Force

if (-not $KeepFiles) {
    if (Test-Path $InstallDir) {
        Remove-Item $InstallDir -Recurse -Force
        Write-Host "Removed install folder: $InstallDir"
    }
} else {
    Write-Host "Kept install folder: $InstallDir"
}

Write-Host ""
Write-Host "Uninstall complete."

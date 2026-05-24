# Remove the worldcanon sidecar from Windows.
#
# Double-click uninstall.cmd, or run from PowerShell:
#   .\uninstall.ps1 [-KeepFiles]

param(
    [switch]$KeepFiles
)

$ErrorActionPreference = "Stop"
$TaskName = "WorldbuilderCanonSidecar"
$InstallDir = Join-Path $env:LOCALAPPDATA "WorldbuilderCanon"

try {
    Write-Host ""
    Write-Host "Worldbuilder Canon uninstaller" -ForegroundColor Cyan
    Write-Host ""

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed scheduled task: $TaskName"
    } else {
        Write-Host "No scheduled task found."
    }

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
    Write-Host "Uninstall complete." -ForegroundColor Green
    Write-Host ""
    Write-Host "The plugin in your Obsidian vault is NOT removed -- to remove that,"
    Write-Host "open Obsidian, Settings -> Community plugins, click the trash icon"
    Write-Host "next to Worldbuilder Canon."
}
catch {
    Write-Host ""
    Write-Host "Uninstall hit an error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}
finally {
    Write-Host ""
    Read-Host "Press Enter to close this window"
}

# Install the worldcanon sidecar on Windows.
#
# Easiest way to run this: double-click install.cmd in this folder.
# Manual: open PowerShell, cd into this folder, run:
#   .\install.ps1 -VaultPath "C:\path\to\your\vault"
#
# If you don't pass -VaultPath, the script will ask you for it.

param(
    [string]$VaultPath,
    [int]$Port = 7777
)

$ErrorActionPreference = "Stop"

function Write-Banner($msg) {
    Write-Host ""
    Write-Host "=====================================================" -ForegroundColor Cyan
    Write-Host " $msg" -ForegroundColor Cyan
    Write-Host "=====================================================" -ForegroundColor Cyan
    Write-Host ""
}

try {
    Write-Banner "Worldbuilder Canon sidecar installer"

    if (-not $VaultPath) {
        Write-Host "Where is your Obsidian vault folder?"
        Write-Host "Example: C:\Users\$env:USERNAME\Documents\WorldVault"
        Write-Host ""
        $VaultPath = Read-Host "Vault path"
        if (-not $VaultPath) {
            throw "No vault path entered. Run install.cmd again."
        }
    }

    $VaultPath = $VaultPath.Trim('"').Trim()

    if (-not (Test-Path $VaultPath -PathType Container)) {
        throw "Vault folder not found: $VaultPath`n`nMake sure you typed the full path, with no quotes. " +
              "If the folder doesn't exist yet, create it first or copy the starter-vault folder there."
    }

    $Here = $PSScriptRoot
    $SidecarSrc = Join-Path $Here "worldcanon-sidecar"
    if (-not (Test-Path $SidecarSrc -PathType Container)) {
        throw "worldcanon-sidecar folder not found next to install.ps1.`n`nDid you extract the full release zip? " +
              "install.ps1, worldcanon-sidecar\, and worldcanon-import.exe should all be in the same folder."
    }

    $InstallDir = Join-Path $env:LOCALAPPDATA "WorldbuilderCanon"
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

    Write-Host "Installing to: $InstallDir"
    Write-Host ""

    $SidecarDest = Join-Path $InstallDir "worldcanon-sidecar"
    if (Test-Path $SidecarDest) { Remove-Item $SidecarDest -Recurse -Force }
    Copy-Item $SidecarSrc $SidecarDest -Recurse
    Write-Host "  Copied sidecar binary"

    $ImporterSrc = Join-Path $Here "worldcanon-import.exe"
    if (Test-Path $ImporterSrc) {
        Copy-Item $ImporterSrc (Join-Path $InstallDir "worldcanon-import.exe") -Force
        Write-Host "  Copied importer binary"
    }

    $DiagnoseSrc = Join-Path $Here "diagnose.ps1"
    if (Test-Path $DiagnoseSrc) {
        Copy-Item $DiagnoseSrc (Join-Path $InstallDir "diagnose.ps1") -Force
    }
    $DiagnoseCmdSrc = Join-Path $Here "diagnose.cmd"
    if (Test-Path $DiagnoseCmdSrc) {
        Copy-Item $DiagnoseCmdSrc (Join-Path $InstallDir "diagnose.cmd") -Force
        Write-Host "  Copied diagnose script"
    }

    $VaultPath | Set-Content -Path (Join-Path $InstallDir "vault-path.txt") -Encoding UTF8

    $SidecarExe = Join-Path $SidecarDest "worldcanon-sidecar.exe"
    $Arguments = "--vault `"$VaultPath`" --port $Port --log-level info"

    $TaskName = "WorldbuilderCanonSidecar"
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | ForEach-Object {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    $Action = New-ScheduledTaskAction `
        -Execute $SidecarExe `
        -Argument $Arguments `
        -WorkingDirectory $InstallDir
    $Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Worldbuilder Canon sidecar (watches vault, serves HTTP on localhost)" `
        -RunLevel Limited | Out-Null
    Write-Host "  Registered scheduled task (auto-starts at login)"

    Start-ScheduledTask -TaskName $TaskName
    Write-Host "  Started sidecar"

    Write-Banner "Sidecar installed and started"
    Write-Host "Vault:    $VaultPath"
    Write-Host "Logs:     $InstallDir\sidecar.log"
    Write-Host "Verify:   open http://127.0.0.1:$Port/stats in a browser"
    Write-Host ""
    Write-Host "Next: install the plugin (worldcanon-plugin.zip -> install.cmd)."
    Write-Host "If anything stops working later, run diagnose.cmd in this folder"
    Write-Host "and send the resulting Desktop zip to Adam."
}
catch {
    Write-Host ""
    Write-Host "=====================================================" -ForegroundColor Red
    Write-Host " Install failed" -ForegroundColor Red
    Write-Host "=====================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    Write-Host ""
    Write-Host "If you don't understand this error, take a screenshot of the whole window"
    Write-Host "(including the lines above) and send it to Adam."
}
finally {
    Write-Host ""
    Read-Host "Press Enter to close this window"
}

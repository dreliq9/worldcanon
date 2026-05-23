# Install the worldcanon sidecar on Windows.
# Run from the extracted release folder (containing worldcanon-sidecar\ and worldcanon-import.exe).
# Usage:  .\install.ps1 -VaultPath "C:\Users\<name>\Documents\WorldVault"

param(
    [Parameter(Mandatory = $true)]
    [string]$VaultPath,

    [int]$Port = 7777
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $VaultPath -PathType Container)) {
    Write-Error "Vault folder not found: $VaultPath"
}

$Here = $PSScriptRoot
$SidecarSrc = Join-Path $Here "worldcanon-sidecar"
if (-not (Test-Path $SidecarSrc -PathType Container)) {
    Write-Error "worldcanon-sidecar folder not found next to install.ps1. Did you extract the full release zip?"
}

$InstallDir = Join-Path $env:LOCALAPPDATA "WorldbuilderCanon"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

Write-Host "Installing to $InstallDir"

# Copy artifacts
$SidecarDest = Join-Path $InstallDir "worldcanon-sidecar"
if (Test-Path $SidecarDest) { Remove-Item $SidecarDest -Recurse -Force }
Copy-Item $SidecarSrc $SidecarDest -Recurse

$ImporterSrc = Join-Path $Here "worldcanon-import.exe"
if (Test-Path $ImporterSrc) {
    Copy-Item $ImporterSrc (Join-Path $InstallDir "worldcanon-import.exe") -Force
}

# Persist the vault path so the task can reference it
$VaultPath | Set-Content -Path (Join-Path $InstallDir "vault-path.txt") -Encoding UTF8

# Build the command line the task will run
$SidecarExe = Join-Path $SidecarDest "worldcanon-sidecar.exe"
$Arguments = "--vault `"$VaultPath`" --port $Port --log-level info"

# Register the scheduled task
$TaskName = "WorldbuilderCanonSidecar"

# Remove any existing task
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

# Kick it off now
Start-ScheduledTask -TaskName $TaskName

Write-Host ""
Write-Host "Sidecar installed and started."
Write-Host "Vault: $VaultPath"
Write-Host "Logs:  $InstallDir\sidecar.log"
Write-Host ""
Write-Host "Verify by visiting http://127.0.0.1:$Port/stats in a browser."
Write-Host ""
Write-Host "The sidecar will auto-start at login. To stop it temporarily:"
Write-Host "  Stop-ScheduledTask -TaskName $TaskName"
Write-Host "To remove entirely, run uninstall.ps1."

# Worldbuilder Canon diagnostic script.
#
# Captures sidecar logs, /stats output, Ollama state, vault info, and
# system specs into a zip on your Desktop. Send that zip to Adam if
# something isn't working.
#
# This script is READ-ONLY. It does not change any settings, restart
# services, or touch your story content.
#
# Usage: right-click diagnose.ps1 -> Run with PowerShell.

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

Write-Host ""
Write-Host "Worldbuilder Canon diagnostic" -ForegroundColor Cyan
Write-Host "Capturing sidecar state, Ollama state, vault info, and system specs..."
Write-Host "(This is read-only. Nothing on your computer is being changed.)"
Write-Host ""

$Now = Get-Date -Format "yyyy-MM-dd-HHmm"
$WorkDir = Join-Path $env:TEMP "worldcanon-diagnose-$Now"
$ZipPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "worldcanon-diagnose-$Now.zip"
New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null

$SidecarRoot = Join-Path $env:LOCALAPPDATA "WorldbuilderCanon"
$SummaryPath = Join-Path $WorkDir "summary.txt"

function Add-Summary($msg) {
    Add-Content -Path $SummaryPath -Value $msg -Encoding utf8
}

Add-Summary "Worldbuilder Canon diagnostic report"
Add-Summary "Generated: $(Get-Date -Format 'u')"
Add-Summary "Computer:  $env:COMPUTERNAME"
Add-Summary "User:      $env:USERNAME"
Add-Summary ""

# --- Sidecar /stats endpoint ---
Add-Summary "=== Sidecar /stats ==="
try {
    $stats = Invoke-WebRequest -Uri "http://127.0.0.1:7777/stats" -TimeoutSec 5 -UseBasicParsing
    $stats.Content | Out-File (Join-Path $WorkDir "sidecar-stats.json") -Encoding utf8
    Add-Summary "Sidecar reachable on 127.0.0.1:7777"
    Add-Summary $stats.Content
} catch {
    Add-Summary "Sidecar UNREACHABLE on 127.0.0.1:7777"
    Add-Summary "Error: $($_.Exception.Message)"
}
Add-Summary ""

# --- Sidecar log (last 200 lines) ---
Add-Summary "=== Sidecar log ==="
$LogPath = Join-Path $SidecarRoot "sidecar.log"
if (Test-Path $LogPath) {
    $size = [math]::Round((Get-Item $LogPath).Length / 1KB, 1)
    Add-Summary "Log file: $LogPath ($size KB)"
    Add-Summary "Saved last 200 lines to sidecar.log"
    Get-Content -Path $LogPath -Tail 200 -ErrorAction SilentlyContinue |
        Out-File (Join-Path $WorkDir "sidecar.log") -Encoding utf8
} else {
    Add-Summary "No sidecar.log at $LogPath"
    Add-Summary "(Either the sidecar has never started, or it can't write here.)"
}
Add-Summary ""

# --- Task Scheduler entry ---
Add-Summary "=== Task Scheduler ==="
try {
    $task = Get-ScheduledTask -TaskName "WorldbuilderCanonSidecar" -ErrorAction Stop
    $info = Get-ScheduledTaskInfo -TaskName "WorldbuilderCanonSidecar"
    Add-Summary "Task registered."
    Add-Summary "State:          $($task.State)"
    Add-Summary "LastRunTime:    $($info.LastRunTime)"
    Add-Summary "LastTaskResult: 0x$('{0:X8}' -f $info.LastTaskResult)"
    Add-Summary "NextRunTime:    $($info.NextRunTime)"
} catch {
    Add-Summary "WorldbuilderCanonSidecar task NOT REGISTERED."
    Add-Summary "(install.ps1 may not have run, or the task was removed.)"
}
Add-Summary ""

# --- Ollama state ---
Add-Summary "=== Ollama ==="
$ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollamaProc) {
    Add-Summary "Ollama process: RUNNING (PID $($ollamaProc.Id))"
} else {
    Add-Summary "Ollama process: NOT RUNNING"
    Add-Summary "(Canon: Ask about my world will fail until Ollama starts.)"
}
$ollamaListPath = Join-Path $WorkDir "ollama-list.txt"
try {
    $models = & ollama list 2>&1
    if ($LASTEXITCODE -eq 0) {
        $models | Out-File $ollamaListPath -Encoding utf8
        Add-Summary "Installed models:"
        ($models | Out-String).TrimEnd() -split "`n" | ForEach-Object { Add-Summary "  $_" }
    } else {
        Add-Summary "ollama CLI returned non-zero exit code: $LASTEXITCODE"
        $models | Out-File $ollamaListPath -Encoding utf8
    }
} catch {
    Add-Summary "ollama CLI not found on PATH."
    Add-Summary "(Either Ollama isn't installed, or its directory isn't in PATH.)"
}
Add-Summary ""

# --- Env vars worldcanon cares about ---
Add-Summary "=== Environment ==="
$envModel = $null
foreach ($scope in @("Process", "User", "Machine")) {
    $val = [Environment]::GetEnvironmentVariable("WORLDCANON_LLM_MODEL", $scope)
    if ($val) { $envModel = "$val (scope: $scope)"; break }
}
if (-not $envModel) { $envModel = "(not set; sidecar defaults to gemma3:4b)" }
Add-Summary "WORLDCANON_LLM_MODEL = $envModel"
Add-Summary ""

# --- Vault sanity ---
Add-Summary "=== Vault ==="
$VaultPathFile = Join-Path $SidecarRoot "vault-path.txt"
if (Test-Path $VaultPathFile) {
    $vault = (Get-Content $VaultPathFile -Raw).Trim()
    Add-Summary "Vault path (from vault-path.txt): $vault"
    if (Test-Path $vault) {
        Add-Summary "Vault folder exists."
        foreach ($folder in @("canon", "drafts", "entities", "systems", "naming", "brainstorm", "research")) {
            $p = Join-Path $vault $folder
            if (Test-Path $p) {
                $count = (Get-ChildItem -Path $p -Recurse -File -Filter "*.md" -ErrorAction SilentlyContinue).Count
                Add-Summary "  $folder/ : $count markdown files"
            } else {
                Add-Summary "  $folder/ : MISSING"
            }
        }
        $pluginDir = Join-Path $vault ".obsidian\plugins\worldcanon-canon"
        if (Test-Path $pluginDir) {
            Add-Summary "Plugin installed at: $pluginDir"
            $manifest = Join-Path $pluginDir "manifest.json"
            if (Test-Path $manifest) {
                try {
                    $mf = Get-Content $manifest -Raw | ConvertFrom-Json
                    Add-Summary "Plugin version: $($mf.version)"
                } catch {
                    Add-Summary "manifest.json present but unparseable."
                }
            }
            $mainJs = Join-Path $pluginDir "main.js"
            if (Test-Path $mainJs) {
                $jsSize = [math]::Round((Get-Item $mainJs).Length / 1KB, 1)
                $jsTime = (Get-Item $mainJs).LastWriteTime
                Add-Summary "main.js: $jsSize KB, last modified $jsTime"
            }
        } else {
            Add-Summary "Plugin NOT INSTALLED in vault (no .obsidian/plugins/worldcanon-canon/)."
        }
        $cpFile = Join-Path $vault ".obsidian\community-plugins.json"
        if (Test-Path $cpFile) {
            $enabled = (Get-Content $cpFile -Raw).Trim()
            Add-Summary "community-plugins.json: $enabled"
        }
    } else {
        Add-Summary "Vault folder DOES NOT EXIST on disk!"
        Add-Summary "(The path in vault-path.txt points nowhere. Did the vault get moved or deleted?)"
    }
} else {
    Add-Summary "No vault-path.txt at $VaultPathFile"
    Add-Summary "(install.ps1 has not been run, or someone deleted the file.)"
}
Add-Summary ""

# --- Index sqlite info ---
Add-Summary "=== Index database ==="
$Idx = Join-Path $SidecarRoot "index.sqlite"
if (Test-Path $Idx) {
    $f = Get-Item $Idx
    Add-Summary "index.sqlite size: $([math]::Round($f.Length/1MB, 2)) MB"
    Add-Summary "Last modified:     $($f.LastWriteTime)"
} else {
    Add-Summary "No index.sqlite at $Idx"
    Add-Summary "(Sidecar has never indexed. Probably never started successfully.)"
}
Add-Summary ""

# --- System specs ---
Add-Summary "=== System ==="
try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    Add-Summary "OS:           $($os.Caption) (build $($os.BuildNumber))"
    Add-Summary "Architecture: $($os.OSArchitecture)"
} catch {
    Add-Summary "Could not read OS info: $($_.Exception.Message)"
}
try {
    $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
    $ramGB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
    Add-Summary "RAM:          $ramGB GB"
} catch {
    Add-Summary "Could not read RAM info."
}
try {
    $cDrive = Get-PSDrive -Name C -ErrorAction Stop
    $freeGB = [math]::Round($cDrive.Free / 1GB, 1)
    $totalGB = [math]::Round(($cDrive.Used + $cDrive.Free) / 1GB, 1)
    Add-Summary "C: drive:     $freeGB GB free of $totalGB GB"
} catch {
    Add-Summary "Could not read drive info."
}
Add-Summary "PowerShell:   $($PSVersionTable.PSVersion)"

# --- Bundle ---
try {
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    Compress-Archive -Path "$WorkDir\*" -DestinationPath $ZipPath -Force
    Remove-Item -Path $WorkDir -Recurse -Force
} catch {
    Write-Host ""
    Write-Host "Could not create zip: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Diagnostic files left in: $WorkDir" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " Diagnostic bundle ready" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Saved to:" -ForegroundColor Green
Write-Host "  $ZipPath" -ForegroundColor White
Write-Host ""
Write-Host "What to do now:"
Write-Host "  1. Email or message the zip file to Adam."
Write-Host "  2. Tell him what you were trying to do when it broke."
Write-Host ""
Write-Host "What's in the zip:"
Write-Host "  - summary.txt        : high-signal status of every component"
Write-Host "  - sidecar.log        : last 200 lines of the sidecar log"
Write-Host "  - sidecar-stats.json : the /stats endpoint output (if reachable)"
Write-Host "  - ollama-list.txt    : which models you have installed"
Write-Host ""
Write-Host "What's NOT in the zip:"
Write-Host "  - Any of your story content. The vault content stays on your machine." -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to close"

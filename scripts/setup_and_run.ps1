param(
    [ValidateSet("standard", "premium")]
    [string]$Mode = "standard",
    [switch]$InstallRuntime,
    [switch]$InstallFfmpeg,
    [switch]$SkipLaunch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $RepoRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

function New-ProjectVenv {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.11 -m venv $VenvPath
        return
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $VenvPath
        return
    }
    throw "Python 3.11+ non trovato. Installa Python e rilancia lo script."
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating virtual environment in $VenvPath" -ForegroundColor Cyan
    New-ProjectVenv
}

Write-Host "Installing project dependencies" -ForegroundColor Cyan
& $PythonExe -m pip install -U pip setuptools wheel
& $PythonExe -m pip install -e $RepoRoot

if ($InstallRuntime) {
    Write-Host "Installing vLLM + vLLM-Omni for local Voxtral runtime" -ForegroundColor Cyan
    & $PythonExe -m pip install -U vllm
    & $PythonExe -m pip install "git+https://github.com/vllm-project/vllm-omni.git" --upgrade
}

if ($InstallFfmpeg) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Installing ffmpeg through winget" -ForegroundColor Cyan
        winget install --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
    }
    else {
        Write-Warning "winget non disponibile. Installa ffmpeg manualmente e assicurati che sia nel PATH."
    }
}

if ($SkipLaunch) {
    Write-Host "Setup completato. Avvio saltato su richiesta." -ForegroundColor Green
    exit 0
}

$TargetScript = if ($Mode -eq "premium") {
    Join-Path $RepoRoot "PREMIUM\premium_app.py"
}
else {
    Join-Path $RepoRoot "app.py"
}

Write-Host "Launching $Mode UI" -ForegroundColor Green
& $PythonExe $TargetScript

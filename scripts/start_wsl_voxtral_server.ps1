param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$RepoPathInWsl = "/mnt/h/MistralTTS",
    [string]$ModelId = "mistralai/Voxtral-4B-TTS-2603",
    [int]$Port = 8000,
    [string]$ExtraArgs = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$bashCommand = @"
set -euo pipefail
cd '$RepoPathInWsl'
export MODEL_ID='$ModelId'
export VOXTRAL_PORT='$Port'
export VOXTRAL_EXTRA_ARGS='$ExtraArgs'
mkdir -p \$HOME/voxtral-wsl/logs
nohup ./wsl/start_voxtral_server.sh > \$HOME/voxtral-wsl/logs/voxtral-server-launcher.log 2>&1 &
sleep 3
ps -ef | grep -i '[v]llm.*Voxtral-4B-TTS-2603' || true
"@

Write-Host "Starting Voxtral server in WSL distro $Distro" -ForegroundColor Cyan
wsl.exe -d $Distro -- bash -lc $bashCommand
Write-Host "If startup succeeded, the Windows UI can connect to http://127.0.0.1:$Port" -ForegroundColor Green

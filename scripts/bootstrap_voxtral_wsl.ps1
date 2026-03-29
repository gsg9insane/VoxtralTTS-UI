param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$RepoPathInWsl = "/mnt/h/MistralTTS",
    [string]$HfToken = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$bashCommand = @"
set -euo pipefail
cd '$RepoPathInWsl'
chmod +x wsl/bootstrap_voxtral.sh wsl/start_voxtral_server.sh wsl/stop_voxtral_server.sh
export HF_TOKEN='$HfToken'
./wsl/bootstrap_voxtral.sh
"@

Write-Host "Bootstrapping Voxtral runtime in WSL distro $Distro" -ForegroundColor Cyan
wsl.exe -d $Distro -- bash -lc $bashCommand


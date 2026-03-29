param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$RepoPathInWsl = "/mnt/h/MistralTTS"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$bashCommand = @"
set -euo pipefail
cd '$RepoPathInWsl'
./wsl/stop_voxtral_server.sh
"@

Write-Host "Stopping Voxtral server in WSL distro $Distro" -ForegroundColor Cyan
wsl.exe -d $Distro -- bash -lc $bashCommand


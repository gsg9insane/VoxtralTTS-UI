param(
    [string]$Distro = "Ubuntu-24.04",
    [int]$Port = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "WSL distro status" -ForegroundColor Cyan
wsl.exe -l -v

Write-Host "`nVoxtral process status inside $Distro" -ForegroundColor Cyan
wsl.exe -d $Distro -- bash -lc "ps -ef | grep -i '[v]llm.*Voxtral-4B-TTS-2603' || true"

Write-Host "`nWindows health probe" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/health" -TimeoutSec 3
    Write-Host "HTTP $($response.StatusCode) on /health" -ForegroundColor Green
}
catch {
    Write-Warning $_.Exception.Message
}


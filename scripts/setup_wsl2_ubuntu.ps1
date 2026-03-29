param(
    [string]$Distro = "Ubuntu-24.04"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    throw "Esegui questo script in PowerShell come Administrator. `wsl --install` richiede privilegi elevati."
}

Write-Host "Installing WSL2 with distro $Distro" -ForegroundColor Cyan
wsl --install -d $Distro
wsl --set-default-version 2

Write-Host "WSL installation command completed." -ForegroundColor Green
Write-Host "If Windows asks for a reboot, restart the machine and then continue with scripts\\bootstrap_voxtral_wsl.ps1" -ForegroundColor Yellow


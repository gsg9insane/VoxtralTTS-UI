param(
    [ValidateSet("standard", "premium", "both")]
    [string]$Mode = "both",
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $RepoRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Virtual environment non trovato. Esegui prima scripts\\setup_and_run.ps1 -SkipLaunch"
}

Write-Host "Installing packaging dependencies" -ForegroundColor Cyan
& $PythonExe -m pip install -U pip setuptools wheel
& $PythonExe -m pip install -e $RepoRoot
& $PythonExe -m pip install pyinstaller

$SpecFiles = switch ($Mode) {
    "standard" { @("packaging\voxtral_studio.spec") }
    "premium" { @("packaging\voxtral_studio_premium.spec") }
    default { @("packaging\voxtral_studio.spec", "packaging\voxtral_studio_premium.spec") }
}

foreach ($Spec in $SpecFiles) {
    $Args = @("-m", "PyInstaller", "--noconfirm")
    if ($Clean) {
        $Args += "--clean"
    }
    $Args += (Join-Path $RepoRoot $Spec)
    Write-Host "Building $Spec" -ForegroundColor Cyan
    & $PythonExe @Args
}

Write-Host "Build completata. Controlla la cartella dist\\" -ForegroundColor Green


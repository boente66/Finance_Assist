$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PyInstaller = Join-Path $ProjectRoot ".venv\Scripts\pyinstaller.exe"
$Executable = Join-Path $ProjectRoot "dist\FinanceAssist-test.exe"
$ReleaseDir = Join-Path $ProjectRoot "dist\release"

if (-not (Test-Path $Python) -or -not (Test-Path $PyInstaller)) {
    throw "Ambiente de build ausente em $ProjectRoot\.venv"
}

Push-Location $ProjectRoot
try {
    & $PyInstaller --noconfirm --clean "ControleFinanceiro-teste.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou." }
    if (-not (Test-Path $Executable)) {
        throw "Executável de teste não foi gerado: $Executable"
    }

    $Version = & $Python -c "from core.version import APP_VERSION; print(APP_VERSION)"
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível obter a versão." }
    New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
    $Archive = Join-Path $ReleaseDir "finance-assist_${Version}_windows-x64.zip"
    if (Test-Path $Archive) { Remove-Item -Force $Archive }
    Compress-Archive -Path @($Executable, "README.md", "LICENSE") -DestinationPath $Archive
    $Hash = (Get-FileHash -Algorithm SHA256 $Archive).Hash.ToLowerInvariant()
    "$Hash  $(Split-Path -Leaf $Archive)" | Set-Content -Encoding ascii "$Archive.sha256"
    Write-Output "Pacote criado: $Archive"
    Write-Output "Checksum: $Archive.sha256"
}
finally {
    Pop-Location
}

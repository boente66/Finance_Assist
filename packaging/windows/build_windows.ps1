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
    # Qt wheels can carry an older CRT than ONNX requires. Use the complete
    # redistributable supplied by Visual Studio, including nested DLL copies.
    $VsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $VsWhere)) { throw "Visual Studio C++ Redistributable não localizado." }
    $VsRoot = & $VsWhere -latest -products '*' -property installationPath
    $Runtime = Get-ChildItem "$VsRoot\VC\Redist\MSVC\*\x64\Microsoft.VC143.CRT" -Directory |
        Sort-Object { [version]$_.Parent.Parent.Name } -Descending | Select-Object -First 1
    if (-not $Runtime) { throw "Runtime MSVC x64 redistribuível ausente." }
    $env:FINANCE_ASSIST_MSVC_REDIST = $Runtime.FullName
    Get-ChildItem "$Runtime\*.dll" | ForEach-Object { Write-Output "$($_.Name): $($_.VersionInfo.FileVersion)" }
    & $PyInstaller --noconfirm --clean "ControleFinanceiro-teste.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou." }
    if (-not (Test-Path $Executable)) {
        throw "Executável de teste não foi gerado: $Executable"
    }

    & $Python packaging/verify_archive.py $Executable
    if ($LASTEXITCODE -ne 0) { throw "Inventário de views incompleto." }
    $Report = Join-Path $ProjectRoot "dist\views-windows.json"
    $Probe = Start-Process -FilePath $Executable -ArgumentList @("--self-test-views", "--self-test-report", "`"$Report`"") -RedirectStandardOutput "$Report.stdout.log" -RedirectStandardError "$Report.stderr.log" -Wait -PassThru
    if ($Probe.ExitCode -ne 0) {
        if (Test-Path $Report) { Get-Content -Raw $Report | Write-Output }
        Get-Content -Raw "$Report.stderr.log" | Write-Output
        throw "Falha na verificação das views (código $($Probe.ExitCode)): $Report"
    }
    if (-not (Get-Content -Raw $Report | ConvertFrom-Json).ok) { throw "Relatório de views reprovado." }

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

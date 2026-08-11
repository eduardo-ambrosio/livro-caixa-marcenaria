$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$buildPython = Join-Path $projectRoot ".venv-build\Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"
$entryPoint = Join-Path $projectRoot "app.py"
$assetsPath = Join-Path $projectRoot "assets"
$iconPath = Join-Path $assetsPath "livro-caixa.ico"
$hooksPath = Join-Path $projectRoot "packaging\hooks"
$distPath = Join-Path $projectRoot "dist"
$workPath = Join-Path $projectRoot "build"

if (-not (Test-Path -LiteralPath $buildPython)) {
    throw "Ambiente de build ausente. Crie .venv-build e instale o PyInstaller."
}
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Arquivo .env ausente. Configure o Project URL e a Publishable key antes do build."
}
if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Icone do aplicativo ausente: $iconPath"
}

$envContent = Get-Content -LiteralPath $envFile -Raw
if ($envContent -notmatch "SUPABASE_PUBLISHABLE_KEY=sb_publishable_") {
    throw "A Publishable key não foi encontrada no arquivo .env."
}
if ($envContent -match "sb_secret_|service_role|SUPABASE_DB_URL|postgresql://") {
    throw "O .env contém uma credencial que não pode ser distribuída. Build cancelado."
}

$version = & $buildPython -c "from livro_caixa import __version__; print(__version__)"
if ($LASTEXITCODE -ne 0 -or -not $version) {
    throw "Não foi possível identificar a versão do aplicativo."
}

$pythonBase = & $buildPython -c "import sys; print(sys.base_prefix)"
$tclData = Join-Path $pythonBase "tcl\tcl8.6"
$tkData = Join-Path $pythonBase "tcl\tk8.6"
$tclModules = Join-Path $pythonBase "tcl\tcl8"
$tkinterExtension = Join-Path $pythonBase "DLLs\_tkinter.pyd"
$tclDll = Join-Path $pythonBase "DLLs\tcl86t.dll"
$tkDll = Join-Path $pythonBase "DLLs\tk86t.dll"

foreach ($requiredPath in @($tclData, $tkData, $tclModules, $tkinterExtension, $tclDll, $tkDll)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Dependência gráfica ausente no runtime de build: $requiredPath"
    }
}

Push-Location $projectRoot
try {
    & $buildPython -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --onedir `
        --name LivroCaixa `
        --icon $iconPath `
        --distpath $distPath `
        --workpath $workPath `
        --specpath $workPath `
        --additional-hooks-dir $hooksPath `
        --hidden-import tkinter.font `
        --add-data "$assetsPath;assets" `
        --add-data "$tclData;_tcl_data" `
        --add-data "$tkData;_tk_data" `
        --add-data "$tclModules;tcl8" `
        --add-binary "$tkinterExtension;." `
        --add-binary "$tclDll;." `
        --add-binary "$tkDll;." `
        $entryPoint

    if ($LASTEXITCODE -ne 0) {
        throw "O PyInstaller não conseguiu gerar o aplicativo."
    }

    $applicationFolder = Join-Path $distPath "LivroCaixa"
    Copy-Item -LiteralPath $envFile -Destination (Join-Path $applicationFolder ".env") -Force
    Set-Content `
        -LiteralPath (Join-Path $applicationFolder "VERSAO.txt") `
        -Value $version `
        -Encoding ascii

    Write-Output "BUILD_OK"
    Write-Output "VERSAO=$version"
    Write-Output "PASTA=$applicationFolder"
} finally {
    Pop-Location
}

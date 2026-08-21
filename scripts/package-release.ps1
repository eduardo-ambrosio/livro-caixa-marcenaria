$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$buildPython = Join-Path $projectRoot ".venv-build\Scripts\python.exe"
$applicationFolder = Join-Path $projectRoot "dist\LivroCaixa"
$installerFolder = Join-Path $projectRoot "installer"
$releaseRoot = Join-Path $projectRoot "release"

if (-not (Test-Path -LiteralPath (Join-Path $applicationFolder "LivroCaixa.exe"))) {
    throw "Execute scripts\build-windows.ps1 antes de montar o pacote."
}

$version = & $buildPython -c "from livro_caixa import __version__; print(__version__)"
if ($LASTEXITCODE -ne 0 -or -not $version) {
    throw "Nao foi possivel identificar a versao do aplicativo."
}

$builtVersionFile = Join-Path $applicationFolder "VERSAO.txt"
if (-not (Test-Path -LiteralPath $builtVersionFile)) {
    throw "O build nao possui VERSAO.txt. Execute scripts\build-windows.ps1 novamente."
}

$builtVersion = (Get-Content -LiteralPath $builtVersionFile -Raw).Trim()
if ($builtVersion -ne $version) {
    throw "O build e o codigo-fonte possuem versoes diferentes ($builtVersion e $version). Execute scripts\build-windows.ps1 novamente."
}

$packageName = "LivroCaixa-v$version-Windows81-x64"
$packageFolder = Join-Path $releaseRoot $packageName
$packageAppFolder = Join-Path $packageFolder "app"
$zipPath = Join-Path $releaseRoot "$packageName.zip"

New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
if (Test-Path -LiteralPath $packageFolder) {
    Remove-Item -LiteralPath $packageFolder -Recurse -Force
}
New-Item -ItemType Directory -Path $packageAppFolder -Force | Out-Null

Copy-Item -Path (Join-Path $applicationFolder "*") -Destination $packageAppFolder -Recurse -Force
Copy-Item -LiteralPath (Join-Path $installerFolder "install.ps1") -Destination $packageFolder
Copy-Item -LiteralPath (Join-Path $installerFolder "Instalar Livro Caixa.cmd") -Destination $packageFolder

$packagedEnv = Get-Content -LiteralPath (Join-Path $packageAppFolder ".env") -Raw
if ($packagedEnv -match "sb_secret_|service_role|SUPABASE_DB_URL|postgresql://") {
    throw "O pacote contem uma credencial proibida. Publicacao cancelada."
}

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path $packageFolder -DestinationPath $zipPath -CompressionLevel Optimal
$hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash

Write-Output "PACOTE_OK"
Write-Output "VERSAO=$version"
Write-Output "SISTEMA=Windows 8.1 x64"
Write-Output "ZIP=$zipPath"
Write-Output "SHA256=$hash"

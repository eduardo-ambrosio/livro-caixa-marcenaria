param(
    [string]$InstallFolder = (Join-Path $env:LOCALAPPDATA "Programs\LivroCaixa"),
    [switch]$SkipShortcuts,
    [switch]$DoNotLaunch,
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

$sourceFolder = Join-Path $PSScriptRoot "app"
$executable = Join-Path $InstallFolder "LivroCaixa.exe"

if (-not (Test-Path -LiteralPath (Join-Path $sourceFolder "LivroCaixa.exe"))) {
    throw "Os arquivos do Livro Caixa nao foram encontrados. Extraia o ZIP inteiro antes de instalar."
}

$running = Get-Process -Name "LivroCaixa" -ErrorAction SilentlyContinue
if ($running) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Feche o Livro Caixa antes de instalar esta versao.",
        "Livro Caixa",
        "OK",
        "Warning"
    ) | Out-Null
    exit 1
}

if (Test-Path -LiteralPath $InstallFolder) {
    Remove-Item -LiteralPath $InstallFolder -Recurse -Force
}

New-Item -ItemType Directory -Path $InstallFolder -Force | Out-Null
Copy-Item -Path (Join-Path $sourceFolder "*") -Destination $InstallFolder -Recurse -Force

if (-not $SkipShortcuts) {
    $shell = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath("Desktop")
    $startMenu = [Environment]::GetFolderPath("Programs")

    foreach ($shortcutPath in @(
        (Join-Path $desktop "Livro Caixa.lnk"),
        (Join-Path $startMenu "Livro Caixa.lnk")
    )) {
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $executable
        $shortcut.WorkingDirectory = $InstallFolder
        $shortcut.Description = "Livro Caixa da Marcenaria"
        $shortcut.Save()
    }
}

if (-not $DoNotLaunch) {
    Start-Process -FilePath $executable -WorkingDirectory $InstallFolder
}

if (-not $Silent) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Livro Caixa instalado com sucesso. Um atalho foi criado na Area de Trabalho.",
        "Instalacao concluida",
        "OK",
        "Information"
    ) | Out-Null
}

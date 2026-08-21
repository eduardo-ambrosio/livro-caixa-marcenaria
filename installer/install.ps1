param(
    [string]$InstallFolder = (Join-Path $env:LOCALAPPDATA "Programs\LivroCaixa"),
    [switch]$SkipShortcuts,
    [switch]$DoNotLaunch,
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

$sourceFolder = Join-Path $PSScriptRoot "app"
$executable = Join-Path $InstallFolder "LivroCaixa.exe"

# Pacote oficial Microsoft KB2999226 para Windows 8.1 x64.
$ucrtUrl = "https://download.microsoft.com/download/9/6/F/96FD0525-3DDF-423D-8845-5F92F4A6883E/Windows8.1-KB2999226-x64.msu"
$ucrtSha256 = "9F707096C7D279ED4BC2A40BA695EFAC69C20406E0CA97E2B3E08443C6381D15"
$requiredUcrtFiles = @(
    "ucrtbase.dll",
    "api-ms-win-crt-conio-l1-1-0.dll",
    "api-ms-win-crt-convert-l1-1-0.dll",
    "api-ms-win-crt-environment-l1-1-0.dll",
    "api-ms-win-crt-filesystem-l1-1-0.dll",
    "api-ms-win-crt-heap-l1-1-0.dll",
    "api-ms-win-crt-locale-l1-1-0.dll",
    "api-ms-win-crt-math-l1-1-0.dll",
    "api-ms-win-crt-process-l1-1-0.dll",
    "api-ms-win-crt-runtime-l1-1-0.dll",
    "api-ms-win-crt-stdio-l1-1-0.dll",
    "api-ms-win-crt-string-l1-1-0.dll",
    "api-ms-win-crt-time-l1-1-0.dll",
    "api-ms-win-crt-utility-l1-1-0.dll"
)

function Show-InstallerMessage {
    param(
        [string]$Message,
        [string]$Title = "Livro Caixa",
        [ValidateSet("Information", "Warning", "Error")]
        [string]$Icon = "Information"
    )

    if ($Silent) { return }

    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Message, $Title, "OK", $Icon) | Out-Null
}

function Get-RealWindowsVersion {
    $detectedVersion = [Environment]::OSVersion.Version
    try {
        $windowsInfo = Get-ItemProperty `
            -LiteralPath "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion" `
            -ErrorAction Stop

        # Evita [Version]::new(), indisponivel no PowerShell 4 do Windows 8.1.
        if ($null -ne $windowsInfo.CurrentMajorVersionNumber) {
            $versionText = "{0}.{1}.{2}" -f `
                [int]$windowsInfo.CurrentMajorVersionNumber, `
                [int]$windowsInfo.CurrentMinorVersionNumber, `
                [int]$windowsInfo.CurrentBuildNumber
            return [Version]$versionText
        }
        if ($windowsInfo.CurrentVersion) {
            return [Version]$windowsInfo.CurrentVersion
        }
    } catch {
        # Usa a versao informada pelo .NET se o Registro nao estiver acessivel.
    }
    return $detectedVersion
}

function Get-Sha256 {
    param([string]$Path)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = $null
    try {
        $stream = [System.IO.File]::OpenRead($Path)
        $hashBytes = $sha.ComputeHash($stream)
        return ([BitConverter]::ToString($hashBytes)).Replace("-", "")
    } finally {
        if ($stream) { $stream.Dispose() }
        if ($sha) { $sha.Dispose() }
    }
}

function Download-OfficialUcrtPackage {
    param([string]$Destination)

    try {
        [System.Net.ServicePointManager]::SecurityProtocol = `
            [System.Net.ServicePointManager]::SecurityProtocol -bor `
            [System.Net.SecurityProtocolType]::Tls12
    } catch {
        # Continua com a configuracao padrao da plataforma.
    }

    $webClient = $null
    try {
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers["User-Agent"] = "LivroCaixa-Windows81-Installer"
        $webClient.DownloadFile($ucrtUrl, $Destination)
        return
    } catch {
        try {
            Import-Module BitsTransfer -ErrorAction Stop
            Start-BitsTransfer -Source $ucrtUrl -Destination $Destination -ErrorAction Stop
            return
        } catch {
            throw @"
Nao foi possivel baixar automaticamente o componente de compatibilidade da Microsoft.

Verifique a conexao com a Internet e execute o instalador novamente.

Se este computador bloquear downloads HTTPS antigos, baixe manualmente o arquivo
Windows8.1-KB2999226-x64.msu no site oficial da Microsoft e coloque-o na mesma
pasta deste instalador. Depois execute novamente "Instalar Livro Caixa.cmd".
"@
        }
    } finally {
        if ($webClient) { $webClient.Dispose() }
    }
}

function Get-UcrtSourcePackage {
    param([string]$TempFolder)

    $manualPackage = Join-Path $PSScriptRoot "Windows8.1-KB2999226-x64.msu"
    $downloadedPackage = Join-Path $TempFolder "Windows8.1-KB2999226-x64.msu"

    if (Test-Path -LiteralPath $manualPackage) {
        Copy-Item -LiteralPath $manualPackage -Destination $downloadedPackage -Force
    } else {
        Download-OfficialUcrtPackage -Destination $downloadedPackage
    }

    $actualHash = (Get-Sha256 -Path $downloadedPackage).ToUpperInvariant()
    if ($actualHash -ne $ucrtSha256) {
        throw @"
A verificacao de seguranca do componente Microsoft falhou.

O arquivo baixado nao corresponde ao KB2999226 oficial esperado.
Apague Windows8.1-KB2999226-x64.msu (se voce o colocou manualmente) e tente novamente.
"@
    }
    return $downloadedPackage
}

function Expand-Cabinet {
    param(
        [string]$Cabinet,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Destination)) {
        New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    }

    $expandExe = Join-Path $env:SystemRoot "System32\expand.exe"
    & $expandExe "-F:*" $Cabinet $Destination | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao extrair o componente Microsoft (codigo $LASTEXITCODE)."
    }
}

function Test-UcrtFilesInFolder {
    param([string]$Folder)

    foreach ($name in $requiredUcrtFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $Folder $name))) {
            return $false
        }
    }
    return $true
}

function Test-SystemUcrtAvailable {
    $systemDirectory = [Environment]::SystemDirectory
    if ([Environment]::Is64BitOperatingSystem -and -not [Environment]::Is64BitProcess) {
        $systemDirectory = Join-Path $env:windir "Sysnative"
    }
    return (Test-UcrtFilesInFolder -Folder $systemDirectory)
}

function Install-AppLocalUcrt {
    param([string]$TargetFolder)

    $windowsVersion = Get-RealWindowsVersion
    if ($windowsVersion.Major -ge 10) { return }
    if (($windowsVersion.Major -ne 6) -or ($windowsVersion.Minor -ne 3)) {
        throw "Esta edicao especial do Livro Caixa foi preparada para Windows 8.1 x64 (versao 6.3)."
    }
    if (Test-SystemUcrtAvailable) { return }

    Show-InstallerMessage `
        -Message "Preparando compatibilidade com Windows 8.1. O instalador vai baixar cerca de 1 MB do servidor oficial da Microsoft e usar o componente somente dentro do Livro Caixa. O Windows nao sera atualizado." `
        -Title "Compatibilidade com Windows 8.1" `
        -Icon "Information"

    $tempFolder = Join-Path ([System.IO.Path]::GetTempPath()) ("LivroCaixa-UCRT-" + [Guid]::NewGuid().ToString("N"))
    $msuFolder = Join-Path $tempFolder "msu"
    $cabFolder = Join-Path $tempFolder "cab"
    New-Item -ItemType Directory -Path $tempFolder -Force | Out-Null

    try {
        $msuPackage = Get-UcrtSourcePackage -TempFolder $tempFolder
        Expand-Cabinet -Cabinet $msuPackage -Destination $msuFolder

        $innerCab = Get-ChildItem -Path $msuFolder -Recurse | Where-Object {
            (-not $_.PSIsContainer) -and
            ($_.Name -like "*KB2999226*x64*.cab") -and
            ($_.Name -notlike "*WSUSSCAN*")
        } | Select-Object -First 1
        if (-not $innerCab) {
            throw "Nao foi possivel localizar o pacote interno do KB2999226."
        }

        Expand-Cabinet -Cabinet $innerCab.FullName -Destination $cabFolder

        $foundFiles = @{}
        Get-ChildItem -Path $cabFolder -Recurse | Where-Object {
            (-not $_.PSIsContainer) -and
            (($_.Name -ieq "ucrtbase.dll") -or ($_.Name -like "api-ms-win-crt-*.dll"))
        } | ForEach-Object {
            $key = $_.Name.ToLowerInvariant()
            if (-not $foundFiles.ContainsKey($key)) {
                $foundFiles[$key] = $_.FullName
            }
        }

        foreach ($name in $requiredUcrtFiles) {
            if (-not $foundFiles.ContainsKey($name.ToLowerInvariant())) {
                throw "O componente Microsoft extraido nao contem $name."
            }
        }

        $targetInternal = Join-Path $TargetFolder "_internal"
        if (-not (Test-Path -LiteralPath $targetInternal)) {
            throw "A pasta interna do Livro Caixa nao foi encontrada apos a copia dos arquivos."
        }

        foreach ($entry in $foundFiles.GetEnumerator()) {
            $fileName = [System.IO.Path]::GetFileName($entry.Value)
            Copy-Item -LiteralPath $entry.Value -Destination (Join-Path $TargetFolder $fileName) -Force
            Copy-Item -LiteralPath $entry.Value -Destination (Join-Path $targetInternal $fileName) -Force
        }

        if (-not (Test-UcrtFilesInFolder -Folder $TargetFolder)) {
            throw "A preparacao local do Universal C Runtime nao foi concluida corretamente."
        }
    } finally {
        if (Test-Path -LiteralPath $tempFolder) {
            Remove-Item -LiteralPath $tempFolder -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

trap {
    Show-InstallerMessage `
        -Message $_.Exception.Message `
        -Title "Nao foi possivel instalar o Livro Caixa" `
        -Icon "Error"
    exit 1
}

if (-not [Environment]::Is64BitOperatingSystem) {
    throw "Este pacote do Livro Caixa requer Windows de 64 bits."
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceFolder "LivroCaixa.exe"))) {
    throw "Os arquivos do Livro Caixa nao foram encontrados. Extraia o ZIP inteiro antes de instalar."
}

$running = Get-Process -Name "LivroCaixa" -ErrorAction SilentlyContinue
if ($running) {
    Show-InstallerMessage `
        -Message "Feche o Livro Caixa antes de instalar esta versao." `
        -Title "Livro Caixa" `
        -Icon "Warning"
    exit 1
}

if (Test-Path -LiteralPath $InstallFolder) {
    Remove-Item -LiteralPath $InstallFolder -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallFolder -Force | Out-Null
Copy-Item -Path (Join-Path $sourceFolder "*") -Destination $InstallFolder -Recurse -Force

Install-AppLocalUcrt -TargetFolder $InstallFolder

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

Show-InstallerMessage `
    -Message "Livro Caixa instalado com sucesso. Um atalho foi criado na Area de Trabalho." `
    -Title "Instalacao concluida" `
    -Icon "Information"

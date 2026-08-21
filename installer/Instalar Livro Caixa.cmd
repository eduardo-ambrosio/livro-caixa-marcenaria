@echo off
setlocal
cd /d "%~dp0"

echo Instalando Livro Caixa para Windows 8.1 x64...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
    echo.
    echo Nao foi possivel instalar o Livro Caixa.
    echo Se apareceu uma mensagem de erro, tire uma foto e envie para suporte.
    pause
    exit /b 1
)
exit /b 0

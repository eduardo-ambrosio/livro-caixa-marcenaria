@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
    echo.
    echo Nao foi possivel instalar o Livro Caixa.
    pause
    exit /b 1
)
exit /b 0

@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1"
if errorlevel 1 (
    echo.
    echo Nao foi possivel gerar o programa.
    pause
    exit /b 1
)
echo.
echo Programa gerado com sucesso na pasta dist\LivroCaixa.
pause

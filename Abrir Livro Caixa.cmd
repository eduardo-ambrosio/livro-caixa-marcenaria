@echo off
set "PYTHONW=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"

if not exist "%PYTHONW%" (
    echo Nao foi possivel encontrar o interpretador Python.
    echo Configure o Python no PyCharm ou instale o Python antes de continuar.
    pause
    exit /b 1
)

start "Livro Caixa da Marcenaria" "%PYTHONW%" "%~dp0app.py"

@echo off
cd /d "%~dp0"

if not exist .env (
    echo.
    echo ========================================================
    echo  ERRO: arquivo .env nao encontrado.
    echo  Copie ".env.example" para ".env" e preencha com as
    echo  credenciais reais antes de continuar.
    echo ========================================================
    echo.
    pause
    exit /b 1
)

if not exist .venv (
    echo Primeira vez rodando aqui — preparando o programa, aguarde...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
)

echo Abrindo o sistema no navegador...
".venv\Scripts\python.exe" -m streamlit run app.py

pause

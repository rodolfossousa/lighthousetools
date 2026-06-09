@echo off
title Lighthouse Tools
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado nesta maquina.
    echo Instale em: https://www.python.org/downloads/
    echo Marque a opcao "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo Primeira execucao — criando ambiente virtual...
    echo Isso pode demorar cerca de 1 minuto.
    echo.
    python -m venv .venv
    call ".venv\Scripts\activate.bat"
    echo Instalando dependencias...
    pip install -r app\requirements.txt
    pip install -e Lighthouse
    echo.
    echo Ambiente criado com sucesso!
    echo.
) else (
    call ".venv\Scripts\activate.bat"
)

cd app
start "" http://localhost:8501
streamlit run main.py --server.headless=true
pause

@echo off
chcp 65001 >nul 2>&1
echo ===========================================
echo   Lighthouse Tools - Setup Inicial
echo ===========================================
echo.

REM ── Verificar Python ──────────────────────────
echo [1/5] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale em https://www.python.org/downloads/
    echo        Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo        Python %%v encontrado.
echo.

REM ── Verificar Node.js ─────────────────────────
echo [2/5] Verificando Node.js e npm...
set "PATH=C:\Program Files\nodejs;%PATH%"
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado. Instale em https://nodejs.org/
    pause
    exit /b 1
)
for /f %%v in ('node --version 2^>^&1') do echo        Node.js %%v encontrado.
for /f %%v in ('npm --version 2^>^&1') do echo        npm %%v encontrado.
echo.

REM ── Instalar biblioteca Lighthouse ────────────
echo [3/5] Instalando biblioteca Lighthouse (pip install -e)...
if not exist "%~dp0Lighthouse\setup.py" (
    if not exist "%~dp0Lighthouse\pyproject.toml" (
        echo [ERRO] Pasta Lighthouse/ nao encontrada.
        pause
        exit /b 1
    )
)
pip install -e "%~dp0Lighthouse" --quiet
if errorlevel 1 (
    echo [ERRO] Falha ao instalar biblioteca Lighthouse.
    pause
    exit /b 1
)
echo        Lighthouse instalado com sucesso.
echo.

REM ── Instalar dependencias do backend ──────────
echo [4/5] Instalando dependencias do backend (pip install -r)...
pip install -r "%~dp0backend\requirements.txt" --quiet
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias do backend.
    pause
    exit /b 1
)
echo        Dependencias do backend instaladas.
echo.

REM ── Instalar dependencias do frontend ─────────
echo [5/5] Instalando dependencias do frontend (npm install)...
cd /d "%~dp0frontend"
npm install
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias do frontend.
    pause
    exit /b 1
)
echo        Dependencias do frontend instaladas.
echo.

REM ── Verificar clients.json ────────────────────
cd /d "%~dp0"
if not exist "%~dp0clients.json" (
    echo ===========================================
    echo   ATENCAO: clients.json nao encontrado!
    echo ===========================================
    echo   1. Copie clients.example.json para clients.json
    echo   2. Preencha com as api_key e workspace_id reais
    echo   3. Consulte um colega para obter as credenciais
    echo ===========================================
    echo.
)

echo ===========================================
echo   Setup concluido com sucesso!
echo ===========================================
echo.
echo   Para iniciar o sistema, execute:
echo     start-dev.bat
echo.
pause

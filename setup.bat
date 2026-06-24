@echo off
chcp 65001 >nul 2>&1
echo ===========================================
echo   Lighthouse Tools - Setup Inicial
echo ===========================================
echo.

REM ── Verificar Python ──────────────────────────
echo [1/6] Verificando Python...
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
echo [2/6] Verificando Node.js e npm...
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

REM ── Criar ambiente virtual ────────────────────
echo [3/6] Criando ambiente virtual (.venv)...
if not exist "%~dp0.venv\Scripts\activate.bat" (
    python -m venv "%~dp0.venv"
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
    echo        Ambiente virtual criado.
) else (
    echo        Ambiente virtual ja existe.
)
call "%~dp0.venv\Scripts\activate.bat"
echo.

REM ── Instalar dependencias Python ──────────────
echo [4/6] Instalando dependencias Python...
pip install -e "%~dp0Lighthouse" --quiet
if errorlevel 1 (
    echo [ERRO] Falha ao instalar biblioteca Lighthouse.
    pause
    exit /b 1
)
echo        Lighthouse instalado.
pip install -r "%~dp0backend\requirements.txt" --quiet
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias do backend.
    pause
    exit /b 1
)
echo        Dependencias do backend instaladas.
echo.

REM ── Instalar dependencias do frontend ─────────
echo [5/6] Instalando dependencias do frontend (npm install)...
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
echo [6/6] Verificando clients.json...
if not exist "%~dp0clients.json" (
    echo.
    echo ===========================================
    echo   ATENCAO: clients.json nao encontrado!
    echo ===========================================
    echo   1. Copie clients.example.json para clients.json:
    echo      copy clients.example.json clients.json
    echo   2. Preencha com as api_key e workspace_id reais
    echo   3. Consulte um colega para obter as credenciais
    echo ===========================================
    echo.
) else (
    echo        clients.json encontrado.
    echo.
)

echo ===========================================
echo   Setup concluido com sucesso!
echo ===========================================
echo.
echo   Para iniciar o sistema, execute:
echo     start-dev.bat
echo.
echo   Backend: http://localhost:8001/docs
echo   Frontend: http://localhost:3000
echo.
pause

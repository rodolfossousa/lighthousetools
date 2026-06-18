@echo off
echo ===========================================
echo   Lighthouse Tools - Development Server
echo ===========================================
echo.

REM Garante que Node.js e Python estejam no PATH
set "PATH=C:\Program Files\nodejs;%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%PATH%"

echo Limpando cache do Next.js (.next)...
if exist "%~dp0frontend\.next" rmdir /s /q "%~dp0frontend\.next"

echo Iniciando Backend (FastAPI) na porta 8001...
start "Backend - FastAPI" cmd /k "set PATH=C:\Program Files\nodejs;%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%PATH% && cd /d %~dp0backend && python -m uvicorn main:app --reload --port 8001"

timeout /t 3 /nobreak > nul

echo Iniciando Frontend (Next.js) na porta 3000...
start "Frontend - Next.js" cmd /k "set PATH=C:\Program Files\nodejs;%PATH% && cd /d %~dp0frontend && npm run dev"

echo.
echo Backend: http://localhost:8001/docs
echo Frontend: http://localhost:3000
echo.
pause

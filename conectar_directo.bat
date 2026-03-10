@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title DeepSeek Client - Menu Principal

if exist "venv\Scripts\activate.bat" (
    echo [*] Entorno virtual detectado. Activando...
    call venv\Scripts\activate.bat
)

set PYTHONPATH=%PYTHONPATH%;%CD%

:: Variables de estado inicial
set THINK=OFF
set SEARCH=OFF

:MENU
cls
echo ========================================================
echo          DEEPSEEK CLIENT - MENU PRINCIPAL
echo ========================================================
echo.
echo Modos Actuales:
echo  [3] DeepThink (R1) : !THINK!
echo  [4] Busqueda Web   : !SEARCH!
echo.
echo Opciones de Arranque:
echo  [1] Chat Interactivo  (Modo Visible)
echo  [2] Chat Interactivo  (Modo Oculto / Headless)
echo  [5] Servidor API      (Puerto 8000 - compatible OpenAI)
echo  [6] Stack Claude Code (Navegador Visible)
echo  [7] Stack Claude Code (Navegador Oculto / Headless)
echo  [8] Dashboard Analitico Web
echo  [9] Salir
echo.
set /p opcion="Seleccione una opcion [1-9]: "

if "%opcion%"=="1" goto CHAT
if "%opcion%"=="2" goto CHAT_HEADLESS
if "%opcion%"=="3" goto TOGGLE_THINK
if "%opcion%"=="4" goto TOGGLE_SEARCH
if "%opcion%"=="5" goto API_SERVER
if "%opcion%"=="6" goto CLAUDE_STACK
if "%opcion%"=="7" goto CLAUDE_STACK_HEADLESS
if "%opcion%"=="8" goto DASHBOARD
if "%opcion%"=="9" exit

goto MENU

:TOGGLE_THINK
if "!THINK!"=="OFF" (set THINK=ON) else (set THINK=OFF)
goto MENU

:TOGGLE_SEARCH
if "!SEARCH!"=="OFF" (set SEARCH=ON) else (set SEARCH=OFF)
goto MENU

:BUILD_ARGS
set PY_ARGS=
if "!THINK!"=="ON" set PY_ARGS=!PY_ARGS! --think
if "!SEARCH!"=="ON" set PY_ARGS=!PY_ARGS! --search
goto :eof

:CHAT
echo [*] Iniciando Chat Interactivo...
call :BUILD_ARGS
where wt >nul 2>&1
if %errorlevel%==0 (
    wt --title "DeepSeek Chat" cmd /k "cd /d %CD% && python app\interactive_chat.py !PY_ARGS!"
) else (
    python app\interactive_chat.py !PY_ARGS!
    pause
)
goto MENU

:CHAT_HEADLESS
echo [*] Iniciando Chat Headless...
call :BUILD_ARGS
where wt >nul 2>&1
if %errorlevel%==0 (
    wt --title "DeepSeek Chat (Headless)" cmd /k "cd /d %CD% && python app\interactive_chat.py --headless !PY_ARGS!"
) else (
    python app\interactive_chat.py --headless !PY_ARGS!
    pause
)
goto MENU

:API_SERVER
echo [*] Iniciando Servidor API DeepSeek en Puerto 8000...
echo [*] Endpoint: http://localhost:8000/v1/chat/completions
where wt >nul 2>&1
if %errorlevel%==0 (
    wt --title "DeepSeek API Server" cmd /k "cd /d %CD% && python app\server.py"
) else (
    start "DEEPSEEK_API" cmd /k "cd /d %CD% && python app\server.py"
)
timeout /t 2 /nobreak > nul
goto MENU

:CLAUDE_STACK
echo [*] Iniciando Stack Claude Code (Navegador Visible)...
echo.
echo  PASO 1: Arrancando servidor DeepSeek (Puerto 8000)...
start "DEEPSEEK_API" cmd /k "cd /d %CD% && python app\server.py"
echo [*] Esperando a que DeepSeek cargue (15s)...
timeout /t 15 /nobreak > nul

echo  PASO 2: Arrancando proxy Anthropic (Puerto 4000)...
start "ANTHROPIC_PROXY" cmd /k "cd /d %CD% && python app\anthropic_proxy.py --port 4000"
timeout /t 3 /nobreak > nul

echo  PASO 3: Lanzando Claude Code...
where wt >nul 2>&1
if %errorlevel%==0 (
    wt --title "Claude Code - DeepSeek (Visible)" cmd /k "claude"
) else (
    start "CLAUDE_CODE" cmd /k "claude"
)
goto MENU

:CLAUDE_STACK_HEADLESS
echo [*] Iniciando Stack Claude Code (Modo Headless / Oculto)...
echo.
echo  PASO 1: Arrancando servidor DeepSeek en modo HEADLESS (Puerto 8000)...
start "DEEPSEEK_API" cmd /k "cd /d %CD% && set HEADLESS=true && python app\server.py"
echo [*] Esperando a que el servidor arranque (10s)...
timeout /t 10 /nobreak > nul

echo  PASO 2: Arrancando proxy Anthropic (Puerto 4000)...
start "ANTHROPIC_PROXY" cmd /k "cd /d %CD% && python app\anthropic_proxy.py --port 4000"
timeout /t 3 /nobreak > nul

echo  PASO 3: Lanzando Claude Code...
where wt >nul 2>&1
if %errorlevel%==0 (
    wt --title "Claude Code - DeepSeek (Headless)" cmd /k "claude"
) else (
    start "CLAUDE_CODE" cmd /k "claude"
)
goto MENU

:DASHBOARD
echo [*] Iniciando Dashboard Analitico...
start "DEEPSEEK_DASHBOARD" cmd /c "python app\dashboard.py"
timeout /t 2 /nobreak > nul
start http://localhost:5000
goto MENU

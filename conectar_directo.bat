@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title DeepSeek GLM - Menu Principal

REM En GLM el venv suele estar en el root o no existir
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
echo  [1] Iniciar Chat Interactivo (Modo Visible)
echo  [2] Iniciar Chat Interactivo (Modo Oculto / Headless)
echo  [5] Escanear Interfaz DeepSeek (Diagnostico proxy)
echo  [6] Salir
echo.
set /p opcion="Seleccione una opcion [1-6]: "

if "%opcion%"=="1" goto CHAT
if "%opcion%"=="2" goto CHAT_HEADLESS
if "%opcion%"=="3" goto TOGGLE_THINK
if "%opcion%"=="4" goto TOGGLE_SEARCH
if "%opcion%"=="5" goto ESCANER
if "%opcion%"=="6" exit

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
echo [*] Iniciando Interfaz de Chat...
call :BUILD_ARGS
python app\interactive_chat.py !PY_ARGS!
pause
goto MENU

:CHAT_HEADLESS
echo [*] Iniciando Interfaz de Chat (Headless)...
call :BUILD_ARGS
python app\interactive_chat.py --headless !PY_ARGS!
pause
goto MENU

:ESCANER
echo [*] Iniciando Escaner de Interfaz DeepSeek...
if not exist captures mkdir captures
start "PROXY_DEEPSEEK" mitmdump -s tools\ui_scan_proxy.py
timeout /t 2 /nobreak > nul
python tools\run_ui_scan.py
echo [*] Cerrando Proxy...
taskkill /FI "WINDOWTITLE eq PROXY_DEEPSEEK*" /F > nul
pause
goto MENU

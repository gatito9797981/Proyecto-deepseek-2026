@echo off
setlocal
cd /d "%~dp0"
title DeepSeek GLM - Modo Directo
echo ==========================================
echo Cargando sesion guardada de DeepSeek GLM...
echo ==========================================

REM En GLM el venv suele estar en el root o no existir
if exist "venv\Scripts\activate.bat" (
    echo [OK] Entorno virtual detectado. Activando...
    call venv\Scripts\activate.bat
)

echo Iniciando chat interactivo...
echo.
python app\interactive_chat.py

echo.
echo ==========================================
echo El proceso ha terminado. 
echo Si el navegador se cerro, revisa los errores arriba.
pause

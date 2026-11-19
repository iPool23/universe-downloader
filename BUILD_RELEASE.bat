@echo off
chcp 65001 >nul
rem Compila la app de escritorio y arma el instalador (carpeta dist)
powershell -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
if %errorlevel% neq 0 (
    echo.
    echo Error en la compilacion
    pause
    exit /b 1
)
echo.
echo Presiona cualquier tecla para salir...
pause >nul

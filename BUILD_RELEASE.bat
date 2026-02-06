@echo off
chcp 65001 >nul
echo ============================================================
echo   UNIVERSE DOWNLOADER - BUILD COMPLETO
echo ============================================================
echo.

echo [1/2] Compilando ejecutable...
python scripts\build.py
if %errorlevel% neq 0 (
    echo.
    echo ✗ Error en la compilación
    pause
    exit /b 1
)

echo.
echo [2/2] Creando paquete de distribución...
python scripts\create_release.py
if %errorlevel% neq 0 (
    echo.
    echo ✗ Error creando el paquete
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ BUILD COMPLETADO
echo ============================================================
echo.
echo 📦 Archivo listo: UniverseDownloader_v2.2.0_Windows.zip
echo.
echo Presiona cualquier tecla para salir...
pause >nul

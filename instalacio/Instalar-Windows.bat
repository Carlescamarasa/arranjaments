@echo off
rem Alternativa a "Instalar Arranjaments" (l'instalador amb finestra de la carpeta principal), per si no s'obri.
rem Doble clic en este fitxer: instala tot el que cal en una finestra negra i posa la icona "Arranjaments" a l'Escriptori.
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-windows.ps1" %*
set CODI=%ERRORLEVEL%
if /I "%~1"=="-SensePreguntes" exit /b %CODI%
echo.
pause
exit /b %CODI%

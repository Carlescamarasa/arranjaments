@echo off
rem Doble clic en este fitxer per a instalar tot el que cal i posar la icona "Arranjaments" a l'Escriptori.
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalacio\instalar-windows.ps1" %*
set CODI=%ERRORLEVEL%
if /I "%~1"=="-SensePreguntes" exit /b %CODI%
echo.
pause
exit /b %CODI%

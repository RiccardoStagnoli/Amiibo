@echo off
chcp 65001 >nul
cd /d "%~dp0whatsapp"
title Installazione segreteria WhatsApp
where npm >nul 2>nul || (echo ERRORE: Node.js non installato. Segui la GUIDA, Fase 7. & pause & exit /b 1)
echo Installo la segreteria WhatsApp (scarica anche un browser Chrome interno, circa 200 MB)...
call npm install
if errorlevel 1 (echo. & echo ERRORE: installazione non riuscita.) else (echo. & echo Installazione completata. Ora avvia avvia_segreteria_whatsapp.bat)
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
title JARVIS - avvio
echo Avvio dei servizi di Jarvis (si aprono 4 finestre: non chiuderle)...
start "JARVIS - WhatsApp" /min cmd /c "%~dp0servizio_loop.bat" whatsapp
timeout /t 3 >nul
start "JARVIS - Pannello" /min cmd /c "%~dp0servizio_loop.bat" pannello
timeout /t 5 >nul
start "JARVIS - Ascolto" /min cmd /c "%~dp0servizio_loop.bat" ascolto
timeout /t 2 >nul
start "JARVIS - Alexa" /min cmd /c "%~dp0servizio_loop.bat" alexa
echo.
echo Fatto. Di' "Jarvis attivazione" oppure apri http://localhost:8080
timeout /t 8 >nul

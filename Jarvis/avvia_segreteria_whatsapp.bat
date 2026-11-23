@echo off
chcp 65001 >nul
cd /d "%~dp0whatsapp"
title JARVIS - Segreteria WhatsApp (non chiudere)
:riavvia
node segreteria_whatsapp.js
echo.
echo La segreteria si e' fermata. Riavvio tra 15 secondi (chiudi la finestra per fermarla)...
timeout /t 15 >nul
goto riavvia

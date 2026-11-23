@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PY=py
where py >nul 2>nul || set PY=python
:ciclo
if "%1"=="whatsapp" (cd /d "%~dp0whatsapp" & node servizio_whatsapp.js)
if "%1"=="pannello" (cd /d "%~dp0" & %PY% server.py)
if "%1"=="ascolto"  (cd /d "%~dp0" & %PY% ascolto.py)
echo Servizio %1 fermo. Riavvio tra 15 secondi...
timeout /t 15 >nul
goto ciclo

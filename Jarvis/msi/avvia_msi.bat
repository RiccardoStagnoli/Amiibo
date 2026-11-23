@echo off
chcp 65001 >nul
cd /d "%~dp0"
title JARVIS - Agente Msi (non chiudere)
set PYTHONUTF8=1
set PY=py
where py >nul 2>nul || set PY=python
:ciclo
%PY% msi_agente.py
echo Agente fermo. Riavvio tra 15 secondi...
timeout /t 15 >nul
goto ciclo

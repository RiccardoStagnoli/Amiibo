@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Installazione agente Msi
set PY=py
where py >nul 2>nul || set PY=python
%PY% -m pip install -r requirements_msi.txt
if errorlevel 1 (echo. & echo ERRORE: installa prima Python sul PC Msi.) else (echo. & echo Fatto. Ora modifica msi_agente.py ^(SERVER e TOKEN^) e avvia avvia_msi.bat)
pause

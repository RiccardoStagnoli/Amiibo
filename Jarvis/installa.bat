@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Installazione JARVIS
set PY=py
where py >nul 2>nul || set PY=python
echo Installo le librerie di Jarvis...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERRORE: installazione non riuscita. Controlla di aver installato Python ^(GUIDA, Fase 1^).
) else (
  echo.
  echo Installazione completata. Ora fai doppio clic su avvia_jarvis.bat
)
pause

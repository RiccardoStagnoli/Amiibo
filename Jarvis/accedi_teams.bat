@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Accesso a Teams
set PYTHONUTF8=1
set PY=py
where py >nul 2>nul || set PY=python
%PY% teams_reader.py

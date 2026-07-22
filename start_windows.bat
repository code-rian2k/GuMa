@echo off
title GuMa V26.7 by HB.
setlocal

cd /d "%~dp0"

if not exist "venv" (
    echo Ersteinrichtung von GuMa - bitte kurz warten...
    py -3 -m venv venv
    if errorlevel 1 (
        echo Konnte Python nicht finden. Bitte zuerst Python von https://www.python.org/downloads/ installieren
        echo und beim Setup unbedingt "Add Python to PATH" ankreuzen.
        pause
        exit /b 1
    )
)

echo Pruefe/installiere benoetigte Pakete...
venv\Scripts\pip install --upgrade pip >nul
venv\Scripts\pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Beim Installieren der Pakete ist ein Fehler aufgetreten - siehe Meldung oben.
    pause
    exit /b 1
)

venv\Scripts\python main.py

if errorlevel 1 (
    echo.
    echo GuMa wurde mit einem Fehler beendet - siehe Meldung oben.
    pause
)

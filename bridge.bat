@echo off
title LIVEMIND BRIDGE - lascia aperta questa finestra
cd /d "%~dp0"
echo Bridge attivo: il tuo agente IA comanda Ableton via bridge\inbox.jsonl
echo Lascia questa finestra aperta mentre lavori.
echo.
python -m livemind.app --no-brain --no-vision --no-voice --debug
pause

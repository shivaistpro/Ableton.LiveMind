@echo off
rem Avvia il Command Center (client desktop di LIVEMIND, richiede Claude Code CLI nel PATH).
cd /d "%~dp0"
python -m livemind_gui.main

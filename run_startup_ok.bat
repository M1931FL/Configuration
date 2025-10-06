@echo off
REM Запуск только со стартовым скриптом
python "%~dp0emulator.py" --startup "%~dp0scripts\startup_ok.txt"

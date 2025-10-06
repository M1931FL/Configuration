@echo off
REM Запуск с обоими параметрами; стартовый скрипт остановится на ошибке
python "%~dp0emulator.py" --vfs "%USERPROFILE%\VFS" --startup "%~dp0scripts\startup_error.txt"

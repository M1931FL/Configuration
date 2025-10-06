@echo off
REM Запуск только с указанием VFS
python "%~dp0emulator.py" --vfs "%USERPROFILE%\VFS"

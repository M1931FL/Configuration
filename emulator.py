# -*- coding: utf-8 -*-
"""
Эмулятор оболочки ОС — Этап 2: Конфигурация.
GUI на Tkinter. Заголовок: [username@hostname].
Параметры командной строки:
  --vfs PATH         путь к физическому корню VFS (пока используется только для отладочного вывода)
  --startup FILE     путь к стартовому скрипту с командами эмулятора (выполняется до первой ошибки)
Во время запуска печатается отладочный вывод параметров.
Переменные: %VARS% (например, %USERPROFILE%, %USERNAME%) и тильда ~.
Заглушки: ls, cd (печатают своё имя и аргументы). Реальные: echo, pwd, exit/quit.
"""

import os
import sys
import shlex
import socket
import getpass
import argparse
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


class CommandNotFound(Exception):
    def __init__(self, cmd: str):
        super().__init__(cmd)
        self.cmd = cmd


class ShellEmulatorApp(tk.Tk):
    def __init__(self, vfs_path: str | None = None, startup_script: str | None = None):
        super().__init__()

        self.username = (
            os.environ.get("USERNAME")
            or getpass.getuser()
            or "user"
        )
        self.hostname = socket.gethostname() or "host"
        self.cwd = os.getcwd()

        # Параметры запуска (могут быть None)
        self.vfs_path = os.path.abspath(vfs_path) if vfs_path else None
        self.startup_script = os.path.abspath(startup_script) if startup_script else None

        self.title(f"Эмулятор - [{self.username}@{self.hostname}]")
        self.geometry("900x540")
        self.minsize(640, 360)

        self._build_ui()
        self._history = []
        self._hist_idx = 0

        self._print_welcome()
        self._print_cli_debug()

        if self.startup_script:
            self.after(150, self.run_startup_script, self.startup_script)

    # ---------- UI ----------
    def _build_ui(self):
        self.output = ScrolledText(self, wrap=tk.WORD, font=("Consolas", 11), state=tk.DISABLED)
        self.output.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X, padx=8, pady=8)

        self.prompt_var = tk.StringVar()
        self._update_prompt()

        ttk.Label(bottom, textvariable=self.prompt_var, width=32, anchor="w").pack(side=tk.LEFT)
        self.entry = ttk.Entry(bottom)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.focus_set()

        ttk.Button(bottom, text="Выполнить", command=self.run_command).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(bottom, text="Очистить", command=self.clear_output).pack(side=tk.LEFT, padx=(8, 0))

        self.entry.bind("<Return>", self.run_command)
        self.entry.bind("<Up>", self._on_hist_up)
        self.entry.bind("<Down>", self._on_hist_down)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _update_prompt(self):
        shown_cwd = self.cwd if len(self.cwd) <= 60 else "…" + self.cwd[-59:]
        self.prompt_var.set(f"{self.username}@{self.hostname}:{shown_cwd}$")

    def _write(self, text: str):
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def _writeline(self, text: str = ""):
        self._write(text + "\n")

    def clear_output(self):
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.configure(state=tk.DISABLED)

    def _print_welcome(self):
        self._writeline("Прототип REPL (Windows). Этап 2: конфигурация.")
        self._writeline("Заглушки: ls, cd. Реальные: echo, pwd, exit/quit.")
        self._writeline("Поддерживается раскрытие %VARS% и ~.")
        self._writeline("Примеры:")
        self._writeline("  echo %USERNAME%")
        self._writeline("  echo %USERPROFILE%")
        self._writeline("  echo ~")
        self._writeline(r"  ls C:\Windows\System32")
        self._writeline(r"  cd \"%USERPROFILE%\\Documents\"")
        self._writeline("  неизвестная_команда")
        self._writeline()

    def _print_cli_debug(self):
        self._writeline("[Параметры запуска]")
        self._writeline(f"  VFS: {self.vfs_path if self.vfs_path else '(не задан)'}")
        if self.vfs_path:
            self._writeline(f"    существует: {'да' if os.path.isdir(self.vfs_path) else 'нет'}")
        self._writeline(f"  Стартовый скрипт: {self.startup_script if self.startup_script else '(не задан)'}")
        if self.startup_script:
            self._writeline(f"    существует: {'да' if os.path.isfile(self.startup_script) else 'нет'}")
        self._writeline()

    # ---------- History ----------
    def _on_hist_up(self, event=None):
        if not self._history:
            return "break"
        self._hist_idx = max(0, self._hist_idx - 1)
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self._history[self._hist_idx])
        return "break"

    def _on_hist_down(self, event=None):
        if not self._history:
            return "break"
        self._hist_idx = min(len(self._history), self._hist_idx + 1)
        self.entry.delete(0, tk.END)
        if self._hist_idx < len(self._history):
            self.entry.insert(0, self._history[self._hist_idx])
        return "break"

    # ---------- Command handling & scripting ----------
    def run_command(self, event=None):
        cmdline = self.entry.get().strip()
        if not cmdline:
            return "break"

        # Печать приглашения + команды
        self._writeline(f"{self.prompt_var.get()} {cmdline}")

        # История
        self._history.append(cmdline)
        self._hist_idx = len(self._history)
        self.entry.delete(0, tk.END)

        # Выполнение
        self._execute_line(cmdline)
        return "break"

    def _execute_line(self, line: str) -> bool:
        """Выполнить одну строку. Возвращает True при успехе, False при ошибке."""
        try:
            expanded = os.path.expandvars(line)
            tokens = shlex.split(expanded, posix=False)
            tokens = [os.path.expanduser(tok) for tok in tokens]
        except ValueError as e:
            self._writeline(f"Синтаксическая ошибка: {e}")
            return False

        return self._dispatch_tokens(tokens)

    def _dispatch_tokens(self, tokens: list[str]) -> bool:
        if not tokens:
            return True

        cmd, *args = tokens
        try:
            if cmd in ("exit", "quit"):
                self._writeline("Завершение работы эмулятора.")
                self.after(50, self.destroy)
                return True
            if cmd == "echo":
                self._cmd_echo(args)
            elif cmd == "pwd":
                self._writeline(self.cwd)
            elif cmd in ("ls", "cd"):
                self._cmd_stub(cmd, args)
            else:
                raise CommandNotFound(cmd)
            return True
        except CommandNotFound as e:
            self._writeline(f"Неизвестная команда: {e.cmd}")
            return False
        except Exception as e:
            self._writeline(f"Ошибка выполнения: {e}")
            return False

    def run_startup_script(self, script_path: str):
        """Выполнить скрипт команд. Остановиться при первой ошибке.
        Печатаем и ввод (как будто пользователь набрал), и вывод.
        """
        self._writeline(f"[SCRIPT] Запуск: {script_path}")
        if not os.path.isfile(script_path):
            self._writeline(f"[SCRIPT] Файл не найден: {script_path}")
            return

        try:
            with open(script_path, "r", encoding="utf-8-sig") as f:
                for lineno, raw in enumerate(f, 1):
                    line = raw.strip()
                    if not line or line.startswith("#") or line.startswith("//") or line.startswith(";"):
                        continue
                    self._writeline(f"{self.prompt_var.get()} {line}")
                    ok = self._execute_line(line)
                    if not ok:
                        self._writeline(f"[SCRIPT] Прервано из-за ошибки в строке {lineno}.")
                        break
        except Exception as e:
            self._writeline(f"[SCRIPT] Ошибка чтения скрипта: {e}")

    def _cmd_echo(self, args):
        self._writeline(" ".join(args))

    def _cmd_stub(self, cmd, args):
        rendered_args = " ".join(args) if args else "(без аргументов)"
        self._writeline(f"{cmd} {rendered_args}")
        if cmd == "cd" and args:
            target = args[0]
            self._writeline(f"(заглушка) Перейти в: {target}")

    def _on_close(self):
        self.destroy()


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="emulator.py",
        description="Эмулятор оболочки ОС (Этап 2, Windows). Поддержка параметров запуска и стартового скрипта.",
    )
    p.add_argument("--vfs", type=str, default=None, help="Путь к физическому корню VFS")
    p.add_argument("--startup", type=str, default=None, help="Путь к стартовому скрипту")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    app = ShellEmulatorApp(vfs_path=args.vfs, startup_script=args.startup)
    app.mainloop()

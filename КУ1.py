# -*- coding: utf-8 -*-
"""
Эмулятор оболочки ОС — Этап 1 (REPL).
GUI на Tkinter. Заголовок: [username@hostname].
Переменные: %USERPROFILE%, %USERNAME% и тильда ~.
Заглушки: ls, cd (печатают своё имя и аргументы). Реальные: echo, pwd, exit/quit.
"""

import os
import shlex
import socket
import getpass
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


class CommandNotFound(Exception):
    def __init__(self, cmd: str):
        super().__init__(cmd)
        self.cmd = cmd


class ShellEmulatorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.username = (
            os.environ.get("USERNAME")
            or getpass.getuser()
            or "user"
        )
        self.hostname = socket.gethostname() or "host"
        self.cwd = os.getcwd()

        self.title(f"Эмулятор - [{self.username}@{self.hostname}]")
        self.geometry("900x540")
        self.minsize(640, 360)

        self._build_ui()
        self._history = []
        self._hist_idx = 0
        self._print_welcome()

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
        self._writeline("Прототип REPL (Windows).")
        self._writeline("Заглушки: ls, cd. Реальные: echo, pwd, exit/quit.")
        self._writeline("Поддерживается раскрытие %VARS% и ~.")
        self._writeline("Примеры:")
        self._writeline("  echo %USERPROFILE%")
        self._writeline("  echo ~")
        self._writeline(r"  ls C:\Windows\System32")
        self._writeline(r"  cd \"%USERPROFILE%\\Documents\"")
        self._writeline("  неизвестная_команда")
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

    # ---------- Command handling ----------
    def run_command(self, event=None):
        cmdline = self.entry.get().strip()
        if not cmdline:
            return "break"

        self._writeline(f"{self.prompt_var.get()} {cmdline}")

        self._history.append(cmdline)
        self._hist_idx = len(self._history)
        self.entry.delete(0, tk.END)

        try:
            # Сначала раскрываем %VARS% и ~.
            expanded = os.path.expanduser(os.path.expandvars(cmdline))
            # posix=False, чтобы не ломать бэкслеши.
            tokens = shlex.split(expanded, posix=False)
            tokens = [os.path.expanduser(tok) for tok in tokens]
        except ValueError as e:
            self._writeline(f"Синтаксическая ошибка: {e}")
            return "break"

        if not tokens:
            return "break"

        cmd, *args = tokens

        try:
            if cmd in ("exit", "quit"):
                self._writeline("Завершение работы эмулятора.")
                self.after(50, self.destroy)
                return "break"
            if cmd == "echo":
                self._cmd_echo(args)
            elif cmd == "pwd":
                self._writeline(self.cwd)
            elif cmd in ("ls", "cd"):
                self._cmd_stub(cmd, args)
            else:
                raise CommandNotFound(cmd)
        except CommandNotFound as e:
            self._writeline(f"Неизвестная команда: {e.cmd}")
        except Exception as e:
            self._writeline(f"Ошибка выполнения: {e}")

        return "break"

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


if __name__ == "__main__":
    app = ShellEmulatorApp()
    app.mainloop()
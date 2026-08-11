from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

from .supabase_client import AuthSession, SupabaseError
from .theme import COLORS, FONTS, make_button


Authenticate = Callable[[str, str], AuthSession]


class LoginDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, authenticate: Authenticate) -> None:
        super().__init__(parent)
        self.authenticate = authenticate
        self.result: tuple[AuthSession, bool] | None = None
        self.title("Entrar no Livro Caixa")
        self.configure(background=COLORS["background"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        width, height = 540, 535
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(
            f"{width}x{height}+{max((screen_width - width) // 2, 0)}+"
            f"{max((screen_height - height) // 2, 0)}"
        )

        outer = tk.Frame(self, background=COLORS["background"])
        outer.pack(fill="both", expand=True, padx=48, pady=31)

        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo-cozinhas-formatec-v2.png"
        try:
            self.logo = tk.PhotoImage(file=str(logo_path))
            tk.Label(
                outer,
                image=self.logo,
                background=COLORS["background"],
                borderwidth=0,
            ).pack(pady=(0, 18))
        except tk.TclError:
            pass

        tk.Label(
            outer,
            text="Acessar o Livro Caixa",
            font=FONTS["heading"],
            foreground=COLORS["text"],
            background=COLORS["background"],
        ).pack()
        tk.Label(
            outer,
            text="Entre para carregar os dados da marcenaria.",
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["background"],
        ).pack(pady=(3, 23))

        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.remember_var = tk.BooleanVar(value=True)
        self.show_password_var = tk.BooleanVar(value=False)

        tk.Label(
            outer,
            text="E-mail",
            font=FONTS["body_bold"],
            foreground=COLORS["text"],
            background=COLORS["background"],
        ).pack(anchor="w")
        self.email_entry = ttk.Entry(
            outer,
            textvariable=self.email_var,
            style="Livro.TEntry",
            font=("Segoe UI", 14),
        )
        self.email_entry.pack(fill="x", ipady=5, pady=(5, 15))

        tk.Label(
            outer,
            text="Senha",
            font=FONTS["body_bold"],
            foreground=COLORS["text"],
            background=COLORS["background"],
        ).pack(anchor="w")
        self.password_entry = ttk.Entry(
            outer,
            textvariable=self.password_var,
            show="•",
            style="Livro.TEntry",
            font=("Segoe UI", 14),
        )
        self.password_entry.pack(fill="x", ipady=5, pady=(5, 8))

        options = tk.Frame(outer, background=COLORS["background"])
        options.pack(fill="x", pady=(0, 19))
        tk.Checkbutton(
            options,
            text="Manter conectado neste computador",
            variable=self.remember_var,
            font=FONTS["body"],
            foreground=COLORS["text"],
            background=COLORS["background"],
            activebackground=COLORS["background"],
            selectcolor=COLORS["surface"],
            borderwidth=0,
        ).pack(side="left")
        tk.Checkbutton(
            options,
            text="Mostrar senha",
            variable=self.show_password_var,
            command=self._toggle_password,
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["background"],
            activebackground=COLORS["background"],
            selectcolor=COLORS["surface"],
            borderwidth=0,
        ).pack(side="right")

        self.enter_button = make_button(
            outer,
            "Entrar",
            self._submit,
            primary=True,
            width=18,
        )
        self.enter_button.pack(ipady=4)

        self.bind("<Return>", lambda _event: self._submit())
        self.bind("<Escape>", lambda _event: self._cancel())
        self.after(100, self.email_entry.focus_set)
        self.grab_set()

    def _toggle_password(self) -> None:
        self.password_entry.configure(show="" if self.show_password_var.get() else "•")

    def _submit(self) -> None:
        email = self.email_var.get().strip()
        password = self.password_var.get()
        if not email or not password:
            messagebox.showwarning(
                "Preencha o acesso",
                "Informe o e-mail e a senha do Livro Caixa.",
                parent=self,
            )
            return

        self.enter_button.configure(state="disabled", text="Conectando...")
        self.update_idletasks()
        try:
            session = self.authenticate(email, password)
        except SupabaseError as error:
            self.enter_button.configure(state="normal", text="Entrar")
            messagebox.showerror("Não foi possível entrar", str(error), parent=self)
            self.password_entry.focus_set()
            self.password_entry.selection_range(0, "end")
            return

        self.result = (session, self.remember_var.get())
        self.grab_release()
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

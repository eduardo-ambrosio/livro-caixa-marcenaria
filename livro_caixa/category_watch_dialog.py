from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .supabase_client import CategoryRecord
from .theme import COLORS, FONTS, make_button


class CategoryWatchDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        categories: list[CategoryRecord],
        selected_ids: set[str],
    ) -> None:
        super().__init__(parent)
        self.title("Categorias para acompanhar")
        self.configure(background=COLORS["background"])
        self.geometry("560x610")
        self.minsize(500, 520)
        self.transient(parent)
        self.grab_set()

        self.categories = list(categories)
        self.variables = {
            category.id: tk.BooleanVar(value=category.id in selected_ids)
            for category in self.categories
        }
        self.result: set[str] | None = None

        outer = tk.Frame(self, background=COLORS["background"])
        outer.pack(fill="both", expand=True, padx=27, pady=23)
        tk.Label(
            outer,
            text="Categorias para acompanhar",
            font=FONTS["heading"],
            foreground=COLORS["text"],
            background=COLORS["background"],
        ).pack(anchor="w")
        tk.Label(
            outer,
            text="Marque uma ou várias categorias para deixá-las em destaque no Resumo.",
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["background"],
            wraplength=490,
            justify="left",
        ).pack(anchor="w", pady=(3, 14))

        selection_actions = tk.Frame(outer, background=COLORS["background"])
        selection_actions.pack(fill="x", pady=(0, 10))
        make_button(selection_actions, "Selecionar todas", self._select_all).pack(side="left")
        make_button(selection_actions, "Limpar seleção", self._clear_all).pack(side="left", padx=8)

        holder = tk.Frame(outer, background=COLORS["border"], padx=1, pady=1)
        holder.pack(fill="both", expand=True)
        canvas = tk.Canvas(
            holder,
            background=COLORS["surface"],
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        checklist = tk.Frame(canvas, background=COLORS["surface"])
        window_id = canvas.create_window((0, 0), window=checklist, anchor="nw")
        checklist.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window_id, width=event.width),
        )

        for category in self.categories:
            tk.Checkbutton(
                checklist,
                text=category.name,
                variable=self.variables[category.id],
                font=("Segoe UI", 14),
                foreground=COLORS["text"],
                background=COLORS["surface"],
                activeforeground=COLORS["text"],
                activebackground=COLORS["green_soft"],
                selectcolor=COLORS["surface"],
                anchor="w",
                cursor="hand2",
                padx=15,
                pady=8,
                takefocus=True,
            ).pack(fill="x")

        actions = tk.Frame(outer, background=COLORS["background"])
        actions.pack(fill="x", pady=(16, 0))
        make_button(actions, "Cancelar", self.destroy, width=10).pack(side="right", padx=(8, 0))
        make_button(actions, "Salvar seleção", self._save, primary=True, width=16).pack(side="right")
        self.bind("<Escape>", lambda _event: self.destroy())

    def _select_all(self) -> None:
        for variable in self.variables.values():
            variable.set(True)

    def _clear_all(self) -> None:
        for variable in self.variables.values():
            variable.set(False)

    def _save(self) -> None:
        self.result = {
            category_id
            for category_id, variable in self.variables.items()
            if variable.get()
        }
        self.destroy()

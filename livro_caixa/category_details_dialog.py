from __future__ import annotations

import tkinter as tk
from datetime import date
from decimal import Decimal
from tkinter import ttk

from .models import Entry
from .theme import COLORS, FONTS, make_button
from .widgets import format_brl


class CategoryDetailsDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        category_name: str,
        period_name: str,
        entries: list[Entry],
        detail_type: str = "expense",
    ) -> None:
        super().__init__(parent)
        is_income = detail_type == "income"
        self.title(
            f"Entradas — {period_name}"
            if is_income
            else f"Gastos — {category_name}"
        )
        self.configure(background=COLORS["background"])
        self.geometry("900x590")
        self.minsize(760, 500)
        self.transient(parent)
        self.grab_set()

        self.entries = sorted(entries, key=lambda entry: entry.date, reverse=True)
        total = sum((entry.value for entry in self.entries), Decimal("0"))

        outer = tk.Frame(self, background=COLORS["background"])
        outer.pack(fill="both", expand=True, padx=28, pady=23)

        heading = tk.Frame(outer, background=COLORS["background"])
        heading.pack(fill="x", pady=(0, 16))
        title_area = tk.Frame(heading, background=COLORS["background"])
        title_area.pack(side="left")
        tk.Label(
            title_area,
            text="Entradas do mês" if is_income else category_name,
            font=FONTS["heading"],
            foreground=COLORS["text"],
            background=COLORS["background"],
        ).pack(anchor="w")
        tk.Label(
            title_area,
            text=(
                f"Recebimentos de {period_name.lower()}"
                if is_income
                else f"Gastos de {period_name.lower()}"
            ),
            font=FONTS["body_bold"],
            foreground=COLORS["muted"],
            background=COLORS["background"],
        ).pack(anchor="w", pady=(3, 0))

        total_box = tk.Frame(
            heading,
            background=COLORS["green_soft"],
            padx=18,
            pady=10,
        )
        total_box.pack(side="right")
        tk.Label(
            total_box,
            text="TOTAL DE ENTRADAS" if is_income else "TOTAL DA CATEGORIA",
            font=("Segoe UI", 10, "bold"),
            foreground=COLORS["green"],
            background=COLORS["green_soft"],
        ).pack(anchor="e")
        tk.Label(
            total_box,
            text=format_brl(total),
            font=FONTS["metric"],
            foreground=COLORS["text"],
            background=COLORS["green_soft"],
        ).pack(anchor="e")

        table_holder = tk.Frame(outer, background=COLORS["border"], padx=1, pady=1)
        table_holder.pack(fill="both", expand=True)

        style = ttk.Style(self)
        style.configure(
            "CategoryDetails.Treeview",
            font=("Segoe UI", 13),
            rowheight=40,
            background=COLORS["surface"],
            fieldbackground=COLORS["surface"],
            foreground=COLORS["text"],
            borderwidth=0,
        )
        style.configure(
            "CategoryDetails.Treeview.Heading",
            font=("Segoe UI", 12, "bold"),
            background=COLORS["surface_soft"],
            foreground=COLORS["text"],
            padding=8,
        )
        style.map(
            "CategoryDetails.Treeview",
            background=[("selected", COLORS["row_active"])],
            foreground=[("selected", COLORS["text"])],
        )

        columns = ("date", "history", "category", "value")
        self.table = ttk.Treeview(
            table_holder,
            columns=columns,
            show="headings",
            style="CategoryDetails.Treeview",
            selectmode="browse",
        )
        scrollbar = ttk.Scrollbar(table_holder, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.table.pack(side="left", fill="both", expand=True)

        self.table.heading("date", text="DATA")
        self.table.heading("history", text="HISTÓRICO")
        self.table.heading("category", text="CATEGORIA")
        self.table.heading("value", text="VALOR")
        self.table.column("date", width=125, minwidth=110, anchor="center", stretch=False)
        self.table.column("history", width=365, minwidth=220, anchor="w")
        self.table.column("category", width=190, minwidth=140, anchor="w")
        self.table.column("value", width=150, minwidth=130, anchor="e", stretch=False)

        for index, entry in enumerate(self.entries):
            self.table.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    entry.date.strftime("%d/%m/%Y"),
                    entry.description,
                    entry.category,
                    format_brl(entry.value),
                ),
            )

        footer = tk.Frame(outer, background=COLORS["background"])
        footer.pack(fill="x", pady=(14, 0))
        count = len(self.entries)
        item_name = "entrada" if is_income else "lançamento"
        found_word = "encontrada" if is_income else "encontrado"
        tk.Label(
            footer,
            text=(
                f"{count} {item_name}{'s' if count != 1 else ''} "
                f"{found_word}{'s' if count != 1 else ''}."
            ),
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["background"],
        ).pack(side="left")
        make_button(footer, "Fechar", self.destroy, primary=True, width=10).pack(side="right")
        self.bind("<Escape>", lambda _event: self.destroy())

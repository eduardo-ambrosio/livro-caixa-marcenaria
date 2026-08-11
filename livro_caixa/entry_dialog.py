from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from .models import Entry
from .theme import COLORS, FONTS, make_button


class NewEntryDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        categories: list[str],
        initial_date: date | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Novo lançamento")
        self.configure(background=COLORS["background"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result: Entry | None = None

        width, height = 550, 535
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 2, 0)
        self.geometry(f"+{x}+{y}")

        outer = tk.Frame(self, background=COLORS["background"])
        outer.pack(fill="both", expand=True, padx=28, pady=24)

        tk.Label(
            outer,
            text="Novo lançamento",
            font=FONTS["heading"],
            foreground=COLORS["text"],
            background=COLORS["background"],
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(
            outer,
            text="Preencha as informações da entrada ou saída.",
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["background"],
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 22))

        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

        self.type_var = tk.StringVar(value="Saída")
        self.date_var = tk.StringVar(value=(initial_date or date.today()).strftime("%d/%m/%Y"))
        self.description_var = tk.StringVar()
        default_category = "Madeira" if "Madeira" in categories else categories[0]
        self.category_var = tk.StringVar(value=default_category)
        self.value_var = tk.StringVar()
        self.payment_var = tk.StringVar(value="Pix")

        type_box = ttk.Combobox(
            outer,
            textvariable=self.type_var,
            values=("Saída", "Entrada"),
            state="readonly",
            style="Livro.TCombobox",
        )
        date_entry = ttk.Entry(outer, textvariable=self.date_var, style="Livro.TEntry")
        description_entry = ttk.Entry(outer, textvariable=self.description_var, style="Livro.TEntry")
        category_box = ttk.Combobox(
            outer,
            textvariable=self.category_var,
            values=tuple(categories),
            state="readonly",
            style="Livro.TCombobox",
        )
        value_entry = ttk.Entry(outer, textvariable=self.value_var, style="Livro.TEntry")
        payment_box = ttk.Combobox(
            outer,
            textvariable=self.payment_var,
            values=("Pix", "Dinheiro", "Cartão", "Transferência", "Boleto"),
            state="readonly",
            style="Livro.TCombobox",
        )

        self._field(outer, "Tipo", type_box, 2, 0, padx=(0, 8))
        self._field(outer, "Data", date_entry, 2, 1, padx=(8, 0))
        self._field(outer, "Descrição", description_entry, 4, 0, columnspan=2)
        self._field(outer, "Categoria", category_box, 6, 0, padx=(0, 8))
        self._field(outer, "Valor (R$)", value_entry, 6, 1, padx=(8, 0))
        self._field(outer, "Forma de pagamento", payment_box, 8, 0, columnspan=2)

        actions = tk.Frame(outer, background=COLORS["background"])
        actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(29, 0))
        make_button(actions, "Cancelar", self.destroy, width=10).pack(side="left", padx=(0, 9))
        make_button(actions, "Salvar lançamento", self._save, primary=True, width=17).pack(side="left")

        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._save())
        description_entry.focus_set()

    @staticmethod
    def _field(
        parent: tk.Misc,
        text: str,
        widget: tk.Widget,
        row: int,
        column: int,
        *,
        columnspan: int = 1,
        padx: tuple[int, int] = (0, 0),
    ) -> None:
        tk.Label(
            parent,
            text=text,
            font=FONTS["small"],
            foreground=COLORS["muted"],
            background=COLORS["background"],
        ).grid(row=row, column=column, columnspan=columnspan, sticky="w", padx=padx)
        widget.grid(
            row=row + 1,
            column=column,
            columnspan=columnspan,
            sticky="ew",
            padx=padx,
            pady=(5, 16),
        )

    def _save(self) -> None:
        description = self.description_var.get().strip()
        raw_value = self.value_var.get().strip().replace("R$", "").replace(".", "").replace(",", ".")
        try:
            entry_date = datetime.strptime(self.date_var.get().strip(), "%d/%m/%Y").date()
            value = Decimal(raw_value)
        except (ValueError, InvalidOperation):
            messagebox.showwarning(
                "Revise o lançamento",
                "Use uma data no formato dd/mm/aaaa e informe um valor válido.",
                parent=self,
            )
            return

        if not description or value <= 0:
            messagebox.showwarning(
                "Revise o lançamento",
                "Informe uma descrição e um valor maior que zero.",
                parent=self,
            )
            return

        self.result = Entry(
            date=entry_date,
            description=description,
            category=self.category_var.get(),
            is_income=self.type_var.get() == "Entrada",
            value=value,
            payment_method=self.payment_var.get(),
        )
        self.destroy()

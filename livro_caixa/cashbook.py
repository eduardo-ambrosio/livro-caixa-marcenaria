from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk
from typing import Callable

from .models import Entry
from .theme import COLORS, FONTS, make_button
from .widgets import BorderedFrame, format_brl


LoadEntries = Callable[[date], list[Entry]]
SaveEntries = Callable[[date, list[Entry]], None]
DateChanged = Callable[[date], None]
ManageCategories = Callable[[], list[str]]


class CashBookRow:
    def __init__(self, default_category: str) -> None:
        self.description = tk.StringVar()
        self.category = tk.StringVar(value=default_category)
        self.income = tk.StringVar()
        self.expense = tk.StringVar()

    def is_empty(self) -> bool:
        return not any(
            value.get().strip()
            for value in (self.description, self.income, self.expense)
        )


class CashBookSheet(tk.Frame):
    COLUMN_WEIGHTS = (6, 3, 2, 2)
    COLUMN_TITLES = ("HISTÓRICO", "CATEGORIA", "ENTRADAS", "SAÍDAS")

    def __init__(
        self,
        parent: tk.Misc,
        load_entries: LoadEntries,
        save_entries: SaveEntries,
        categories: list[str],
        manage_categories: ManageCategories,
        initial_date: date | None = None,
        date_changed: DateChanged | None = None,
    ) -> None:
        super().__init__(parent, background=COLORS["background"])
        self.load_entries = load_entries
        self.save_entries = save_entries
        self.categories = list(categories)
        self.manage_categories = manage_categories
        self.date_changed = date_changed
        self.current_date = initial_date or date.today()
        self.rows: list[CashBookRow] = []
        self.cell_widgets: list[list[tk.Widget]] = []
        self.delete_buttons: list[tk.Button] = []
        self.active_row_index: int | None = None
        self.date_var = tk.StringVar(value=self.current_date.strftime("%d/%m/%Y"))
        self.page_var = tk.StringVar(value=f"Folha {self.current_date.day:02d}")
        self.income_total_var = tk.StringVar(value=format_brl(Decimal("0")))
        self.expense_total_var = tk.StringVar(value=format_brl(Decimal("0")))
        self.balance_var = tk.StringVar(value=format_brl(Decimal("0")))
        self.status_var = tk.StringVar(value="Preencha as células e pressione Enter para avançar.")

        self._build_header()
        self._build_sheet()
        self._load_current_page()

    def _build_header(self) -> None:
        header = BorderedFrame(self)
        header.pack(fill="x", pady=(0, 10))
        body = header.body

        top = tk.Frame(body, background=COLORS["surface"])
        top.pack(fill="x", padx=17, pady=(13, 7))
        tk.Label(
            top,
            text="MOVIMENTO DO CAIXA",
            font=("Segoe UI", 13, "bold"),
            foreground=COLORS["text"],
            background=COLORS["surface"],
        ).pack(side="left")
        tk.Label(
            top,
            textvariable=self.page_var,
            font=FONTS["body_bold"],
            foreground=COLORS["muted"],
            background=COLORS["surface"],
        ).pack(side="right")

        lower = tk.Frame(body, background=COLORS["surface"])
        lower.pack(fill="x", padx=17, pady=(0, 13))
        tk.Label(
            lower,
            text="Marcenaria",
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["surface"],
        ).pack(side="left")

        make_button(lower, "Dia seguinte  ›", lambda: self._change_day(1)).pack(side="right")
        self.date_entry = ttk.Entry(
            lower,
            textvariable=self.date_var,
            width=13,
            justify="center",
            style="LivroDate.TEntry",
            font=("Segoe UI", 17, "bold"),
        )
        self.date_entry.pack(side="right", padx=7)
        make_button(lower, "Abrir data", self._open_typed_date).pack(side="right")
        make_button(lower, "‹  Dia anterior", lambda: self._change_day(-1)).pack(side="right", padx=7)
        tk.Label(
            lower,
            text="Data:",
            font=FONTS["body_bold"],
            foreground=COLORS["text"],
            background=COLORS["surface"],
        ).pack(side="right", padx=(0, 2))

    def _build_sheet(self) -> None:
        panel = BorderedFrame(self)
        panel.pack(fill="both", expand=True)
        body = panel.body

        column_header = tk.Frame(body, background=COLORS["surface_soft"])
        column_header.pack(fill="x", padx=12, pady=(12, 0))
        for column, (title, weight) in enumerate(zip(self.COLUMN_TITLES, self.COLUMN_WEIGHTS)):
            column_header.columnconfigure(column, weight=weight, uniform="book-columns")
            label = tk.Label(
                column_header,
                text=title,
                font=("Segoe UI", 11, "bold"),
                foreground=COLORS["text"],
                background=COLORS["surface_soft"],
                pady=9,
                borderwidth=0,
                relief="flat",
            )
            label.grid(row=0, column=column, sticky="nsew")
        column_header.columnconfigure(4, minsize=30)
        tk.Label(
            column_header,
            text="",
            background=COLORS["surface_soft"],
            borderwidth=0,
            relief="flat",
        ).grid(row=0, column=4, sticky="nsew")

        grid_holder = tk.Frame(body, background=COLORS["surface"])
        grid_holder.pack(fill="both", expand=True, padx=12)
        self.canvas = tk.Canvas(
            grid_holder,
            background=COLORS["surface"],
            highlightthickness=0,
            height=310,
        )
        scrollbar = ttk.Scrollbar(grid_holder, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.rows_frame = tk.Frame(self.canvas, background=COLORS["surface"])
        self.canvas_window = self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.rows_frame.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_rows_frame)

        summary = tk.Frame(body, background=COLORS["surface_soft"])
        summary.pack(fill="x", padx=12)
        summary.columnconfigure(0, weight=1)
        self._summary_item(summary, "ENTRADAS DESTA PÁGINA", self.income_total_var, 1)
        self._summary_item(summary, "SAÍDAS DESTA PÁGINA", self.expense_total_var, 2)
        self._summary_item(summary, "SALDO DA PÁGINA", self.balance_var, 3)

        actions = tk.Frame(body, background=COLORS["surface"])
        actions.pack(fill="x", padx=14, pady=11)
        tk.Label(
            actions,
            textvariable=self.status_var,
            font=FONTS["small"],
            foreground=COLORS["muted"],
            background=COLORS["surface"],
        ).pack(side="left")
        make_button(actions, "Salvar página", self.save, primary=True).pack(side="right")
        make_button(actions, "+  Adicionar linhas", lambda: self._add_blank_rows(5)).pack(side="right", padx=(7, 0))
        make_button(actions, "Editar categorias", self._manage_categories).pack(side="right", padx=(7, 0))

    def _summary_item(self, parent: tk.Misc, label: str, variable: tk.StringVar, column: int) -> None:
        box = tk.Frame(parent, background=COLORS["surface_soft"], padx=14, pady=8)
        box.grid(row=0, column=column, sticky="e")
        tk.Label(
            box,
            text=label,
            font=("Segoe UI", 8, "bold"),
            foreground=COLORS["muted"],
            background=COLORS["surface_soft"],
        ).pack(anchor="e")
        tk.Label(
            box,
            textvariable=variable,
            font=FONTS["body_bold"],
            foreground=COLORS["text"],
            background=COLORS["surface_soft"],
        ).pack(anchor="e")

    def _update_scroll_region(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_rows_frame(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _load_current_page(self) -> None:
        if self.date_changed is not None:
            self.date_changed(self.current_date)
        self.date_var.set(self.current_date.strftime("%d/%m/%Y"))
        self.page_var.set(f"Folha {self.current_date.day:02d}")
        entries = self.load_entries(self.current_date)
        self._clear_rows()
        for entry in entries:
            self._add_row(entry)
        minimum_rows = max(15 - len(entries), 5)
        self._add_blank_rows(minimum_rows)
        self._update_totals()
        self.status_var.set("Preencha as células e pressione Enter para avançar.")

    def _clear_rows(self) -> None:
        for child in self.rows_frame.winfo_children():
            child.destroy()
        self.rows.clear()
        self.cell_widgets.clear()
        self.delete_buttons.clear()
        self.active_row_index = None

    def _add_blank_rows(self, count: int) -> None:
        for _ in range(count):
            self._add_row(None)
        self.after_idle(self._update_scroll_region)

    def _add_row(self, entry: Entry | None) -> None:
        row_number = len(self.rows)
        fallback_category = "Outros" if "Outros" in self.categories else self.categories[0]
        row = CashBookRow(fallback_category)
        if entry is not None:
            row.description.set(entry.description)
            row.category.set(entry.category)
            if entry.is_income:
                row.income.set(self._plain_money(entry.value))
            else:
                row.expense.set(self._plain_money(entry.value))
        self.rows.append(row)

        for column, weight in enumerate(self.COLUMN_WEIGHTS):
            self.rows_frame.columnconfigure(column, weight=weight, uniform="book-columns")
        self.rows_frame.columnconfigure(4, minsize=30)

        common = {
            "font": ("Segoe UI", 14),
            "foreground": COLORS["text"],
            "background": COLORS["white"],
            "insertbackground": COLORS["text"],
            "selectbackground": COLORS["green"],
            "selectforeground": COLORS["white"],
            "relief": "flat",
            "borderwidth": 0,
            "highlightthickness": 1,
            "highlightbackground": COLORS["border"],
            "highlightcolor": COLORS["green"],
        }
        description = tk.Entry(self.rows_frame, textvariable=row.description, **common)
        category = ttk.Combobox(
            self.rows_frame,
            textvariable=row.category,
            values=tuple(self.categories),
            state="readonly",
            style="Livro.TCombobox",
            font=("Segoe UI", 14),
        )
        category.bind("<MouseWheel>", self._block_category_mousewheel)
        category.bind("<Button-4>", self._block_category_mousewheel)
        category.bind("<Button-5>", self._block_category_mousewheel)
        category.bind("<<ComboboxSelected>>", self._clear_category_selection)
        category.bind("<FocusOut>", self._clear_category_selection, add="+")
        income = tk.Entry(self.rows_frame, textvariable=row.income, justify="right", **common)
        expense = tk.Entry(self.rows_frame, textvariable=row.expense, justify="right", **common)
        cells: list[tk.Widget] = [description, category, income, expense]

        for column, widget in enumerate(cells):
            widget.grid(row=row_number, column=column, sticky="nsew", ipady=9)
            widget.bind("<FocusIn>", lambda _event, r=row_number: self._activate_row(r))
            widget.bind("<Button-1>", lambda _event, r=row_number: self._activate_row(r), add="+")
            widget.bind("<Return>", lambda event, r=row_number, c=column: self._move_focus(r, c, 0, 1))
            widget.bind("<Down>", lambda event, r=row_number, c=column: self._move_focus(r, c, 1, 0))
            widget.bind("<Up>", lambda event, r=row_number, c=column: self._move_focus(r, c, -1, 0))
        self.cell_widgets.append(cells)

        delete_button = tk.Button(
            self.rows_frame,
            text="×",
            command=lambda selected=row: self._delete_row(selected),
            font=("Segoe UI", 12, "bold"),
            foreground=COLORS["muted"],
            background=COLORS["surface"],
            activebackground=COLORS["red_soft"],
            activeforeground=COLORS["red"],
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            cursor="hand2",
        )
        delete_button.grid(row=row_number, column=4, sticky="nsew")
        delete_button.bind("<Button-1>", lambda _event, r=row_number: self._activate_row(r), add="+")
        self.delete_buttons.append(delete_button)

        row.income.trace_add("write", lambda *_args: self._update_totals())
        row.expense.trace_add("write", lambda *_args: self._update_totals())

    @staticmethod
    def _block_category_mousewheel(_event=None):
        return "break"

    def _clear_category_selection(self, event) -> None:
        widget = event.widget
        self.after_idle(lambda: widget.selection_clear() if widget.winfo_exists() else None)

    def _activate_row(self, row_index: int) -> None:
        if row_index < 0 or row_index >= len(self.cell_widgets):
            return
        self.active_row_index = row_index
        for index, cells in enumerate(self.cell_widgets):
            active = index == row_index
            background = COLORS["row_active"] if active else COLORS["white"]
            border = COLORS["row_active_border"] if active else COLORS["border"]
            for widget in cells:
                if isinstance(widget, ttk.Combobox):
                    widget.configure(style="LivroActive.TCombobox" if active else "Livro.TCombobox")
                else:
                    widget.configure(
                        background=background,
                        highlightbackground=border,
                        highlightcolor=border if active else COLORS["green"],
                    )
            if index < len(self.delete_buttons):
                self.delete_buttons[index].configure(
                    background=COLORS["row_active"] if active else COLORS["surface"],
                    foreground=COLORS["red"] if active else COLORS["muted"],
                    highlightbackground=border,
                )
        self.status_var.set(f"Linha {row_index + 1} selecionada — pressione Enter para avançar.")

    def _delete_row(self, selected: CashBookRow) -> None:
        if len(self.rows) <= 1:
            return
        index = self.rows.index(selected)
        self.rows.pop(index)
        self._rebuild_rows()

    def _manage_categories(self) -> None:
        if not self.save(silent=True):
            return
        self.categories = self.manage_categories()
        self._load_current_page()
        self.status_var.set("Lista de categorias atualizada.")

    def _rebuild_rows(self) -> None:
        values = []
        for row in self.rows:
            values.append(
                (
                    row.description.get(),
                    row.category.get(),
                    row.income.get(),
                    row.expense.get(),
                )
            )
        self._clear_rows()
        for description, category, income, expense in values:
            self._add_row(None)
            row = self.rows[-1]
            row.description.set(description)
            row.category.set(category)
            row.income.set(income)
            row.expense.set(expense)
        self._update_totals()

    def _move_focus(self, row: int, column: int, row_delta: int, column_delta: int):
        target_row = row + row_delta
        target_column = column + column_delta
        if target_column >= len(self.COLUMN_TITLES):
            target_column = 0
            target_row = row + 1
        if target_column < 0:
            target_column = len(self.COLUMN_TITLES) - 1
            target_row = row - 1
        if target_row >= len(self.cell_widgets):
            self._add_blank_rows(1)
        target_row = max(0, min(target_row, len(self.cell_widgets) - 1))
        self.cell_widgets[target_row][target_column].focus_set()
        self.canvas.yview_moveto(target_row / max(len(self.cell_widgets), 1))
        return "break"

    def _change_day(self, days: int) -> None:
        if not self.save(silent=True):
            return
        self.current_date += timedelta(days=days)
        self._load_current_page()

    def _open_typed_date(self) -> None:
        try:
            selected_date = datetime.strptime(self.date_var.get().strip(), "%d/%m/%Y").date()
        except ValueError:
            messagebox.showwarning("Data inválida", "Informe a data no formato dd/mm/aaaa.", parent=self)
            return
        if not self.save(silent=True):
            return
        self.current_date = selected_date
        self._load_current_page()

    def save(self, silent: bool = False) -> bool:
        parsed: list[Entry] = []
        for index, row in enumerate(self.rows, start=1):
            if row.is_empty():
                continue
            income = self._parse_money(row.income.get())
            expense = self._parse_money(row.expense.get())
            description = row.description.get().strip()
            if income is None or expense is None:
                self._show_row_error(index, "Use apenas números nas colunas de entradas e saídas.")
                return False
            if not description:
                self._show_row_error(index, "Preencha o histórico do lançamento.")
                return False
            if (income > 0 and expense > 0) or (income <= 0 and expense <= 0):
                self._show_row_error(index, "Preencha somente a entrada ou somente a saída.")
                return False

            is_income = income > 0
            parsed.append(
                Entry(
                    date=self.current_date,
                    description=description,
                    category=row.category.get() or "Outros",
                    is_income=is_income,
                    value=income if is_income else expense,
                    payment_method="Não informado",
                    document="",
                )
            )

        try:
            self.save_entries(self.current_date, parsed)
        except Exception as error:
            self.status_var.set("Não foi possível sincronizar esta página.")
            messagebox.showerror(
                "A página não foi salva",
                str(error),
                parent=self,
            )
            return False

        self.status_var.set(f"Página de {self.current_date.strftime('%d/%m/%Y')} sincronizada.")
        if not silent:
            messagebox.showinfo(
                "Página salva",
                "Os lançamentos foram salvos no banco online.",
                parent=self,
            )
        return True

    def _show_row_error(self, row: int, message: str) -> None:
        self._activate_row(row - 1)
        messagebox.showwarning("Revise a linha", f"Linha {row}: {message}", parent=self)

    def _update_totals(self) -> None:
        income = Decimal("0")
        expense = Decimal("0")
        for row in self.rows:
            income_value = self._parse_money(row.income.get())
            expense_value = self._parse_money(row.expense.get())
            if income_value is not None:
                income += income_value
            if expense_value is not None:
                expense += expense_value
        self.income_total_var.set(format_brl(income))
        self.expense_total_var.set(format_brl(expense))
        self.balance_var.set(format_brl(income - expense))

    @staticmethod
    def _parse_money(raw: str) -> Decimal | None:
        text = raw.strip().replace("R$", "").replace(" ", "")
        if not text:
            return Decimal("0")
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            value = Decimal(text)
        except InvalidOperation:
            return None
        return value if value >= 0 else None

    @staticmethod
    def _plain_money(value: Decimal) -> str:
        formatted = f"{value:.2f}"
        return formatted.replace(".", ",")

from __future__ import annotations

import tkinter as tk
from datetime import date
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox, ttk

from .cashbook import CashBookSheet
from .category_dialog import CategoryManagerDialog
from .category_details_dialog import CategoryDetailsDialog
from .category_watch import calculate_category_watch_totals
from .category_watch_dialog import CategoryWatchDialog
from .config import ConfigurationError, load_supabase_config
from .entry_dialog import NewEntryDialog
from .login_dialog import LoginDialog
from .models import Entry
from .preferences_store import PreferencesStore
from .session_store import SessionStore
from .supabase_client import CategoryRecord, SupabaseClient, SupabaseError, SupabaseRepository
from .theme import COLORS, FONTS, configure_ttk, make_button
from .widgets import BorderedFrame, ExpenseChart, MetricCard, format_brl


class LivroCaixaApp(tk.Tk):
    MONTH_NAMES = (
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    )

    def __init__(self) -> None:
        super().__init__()
        self.title("Livro Caixa da Marcenaria")
        self._configure_window_icon()
        self.geometry("1220x760")
        self.minsize(1024, 680)
        self.configure(background=COLORS["background"])
        configure_ttk(self)
        self.withdraw()

        try:
            config = load_supabase_config()
        except ConfigurationError as error:
            messagebox.showerror("Configuração incompleta", str(error), parent=self)
            self.destroy()
            return

        self.client = SupabaseClient(config)
        self.repository = SupabaseRepository(self.client)
        self.session_store = SessionStore()
        self.remember_session = False
        self.client.on_session_updated = self._session_updated
        if not self._authenticate():
            self.destroy()
            return

        user_id = self.client.session.user_id if self.client.session is not None else "default"
        self.preferences_store = PreferencesStore(user_id)
        self.watched_category_ids = self.preferences_store.load_watched_category_ids()

        self.categories: list[str] = []
        self.category_records: list[CategoryRecord] = []
        self.entries: list[Entry] = []
        self.income = Decimal("0")
        self.expense = Decimal("0")
        self.expenses_by_category: dict[str, Decimal] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.active_page = "Resumo"
        self.expense_chart_mode = "bars"
        self.selected_month = date.today().replace(day=1)
        self.period_var = tk.StringVar(value=self._format_month(self.selected_month))
        self.month_selector_var = tk.StringVar(value=self._format_month(self.selected_month))
        self.month_options = self._build_month_options()
        self.month_lookup = {self._format_month(item): item for item in self.month_options}
        self.sync_status_var = tk.StringVar(value="●  Sincronizado")

        try:
            self.category_records = self.repository.load_categories()
            if not self.category_records:
                raise SupabaseError("Nenhuma categoria foi encontrada para este usuário.")
            self.categories = [category.name for category in self.category_records]
            self._reconcile_watched_categories()
            self._load_month_from_cloud(self.selected_month)
        except SupabaseError as error:
            messagebox.showerror(
                "Não foi possível carregar os dados",
                str(error),
                parent=self,
            )
            self.destroy()
            return

        self._build_titlebar()
        self._build_body()
        self._recalculate_totals()
        self.show_page("Resumo")
        self.deiconify()

    def _configure_window_icon(self) -> None:
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "livro-caixa-icon.png"
        try:
            self._window_icon = tk.PhotoImage(file=icon_path)
            self.iconphoto(True, self._window_icon)
        except tk.TclError:
            self._window_icon = None

    def _authenticate(self) -> bool:
        refresh_token = self.session_store.load()
        if refresh_token:
            self.remember_session = True
            try:
                self.client.restore_session(refresh_token)
                return True
            except SupabaseError:
                self.session_store.clear()
                self.remember_session = False

        dialog = LoginDialog(self, self.client.sign_in)
        self.wait_window(dialog)
        if dialog.result is None:
            return False

        session, self.remember_session = dialog.result
        if self.remember_session:
            try:
                self.session_store.save(session.refresh_token)
            except OSError:
                self.remember_session = False
        else:
            self.session_store.clear()
        return True

    def _session_updated(self, session) -> None:
        if self.remember_session:
            try:
                self.session_store.save(session.refresh_token)
            except OSError:
                self.remember_session = False

    def _build_titlebar(self) -> None:
        titlebar = tk.Frame(self, background=COLORS["surface"], height=84)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)

        brand_area = tk.Frame(titlebar, background=COLORS["surface"])
        brand_area.pack(side="left", padx=(16, 27))
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo-cozinhas-formatec-v2.png"
        try:
            self.brand_logo = tk.PhotoImage(file=str(logo_path))
            tk.Label(
                brand_area,
                image=self.brand_logo,
                background=COLORS["surface"],
                borderwidth=0,
            ).pack(side="left", pady=7)
        except tk.TclError:
            tk.Label(
                brand_area,
                text="Cozinhas Formatec",
                font=FONTS["brand"],
                foreground=COLORS["text"],
                background=COLORS["surface"],
            ).pack(side="left", pady=25)

        nav = tk.Frame(titlebar, background=COLORS["surface"])
        nav.pack(side="left", fill="y")
        for icon, page in (("▦", "Resumo"), ("↔", "Lançamentos")):
            button = tk.Button(
                nav,
                text=f"{icon}  {page}",
                command=lambda selected=page: self.show_page(selected),
                font=FONTS["body_bold"],
                foreground=COLORS["muted"],
                background=COLORS["surface"],
                activebackground=COLORS["surface_soft"],
                activeforeground=COLORS["green"],
                padx=18,
                pady=9,
                relief="flat",
                borderwidth=0,
                cursor="hand2",
            )
            button.pack(side="left", padx=(0, 6), pady=19)
            self.nav_buttons[page] = button

        status_area = tk.Frame(titlebar, background=COLORS["surface"])
        status_area.pack(side="right", padx=24)
        tk.Label(
            status_area,
            textvariable=self.period_var,
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["surface"],
        ).pack(anchor="e")
        sync_row = tk.Frame(status_area, background=COLORS["surface"])
        sync_row.pack(anchor="e", pady=(2, 0))
        tk.Label(
            sync_row,
            textvariable=self.sync_status_var,
            font=FONTS["small"],
            foreground=COLORS["green"],
            background=COLORS["surface"],
        ).pack(side="left", padx=(0, 9))
        tk.Button(
            sync_row,
            text="Atualizar dados",
            command=self._refresh_current_month,
            font=FONTS["small"],
            foreground=COLORS["green"],
            background=COLORS["surface"],
            activebackground=COLORS["surface_soft"],
            activeforeground=COLORS["green"],
            relief="flat",
            borderwidth=0,
            cursor="hand2",
        ).pack(side="left")
        tk.Frame(self, background=COLORS["border"], height=1).pack(fill="x")

    def _build_body(self) -> None:
        body = tk.Frame(self, background=COLORS["background"])
        body.pack(fill="both", expand=True)

        self.content = tk.Frame(body, background=COLORS["background"])
        self.content.pack(fill="both", expand=True, padx=27, pady=22)

    def show_page(self, page: str) -> None:
        self.active_page = page
        for name, button in self.nav_buttons.items():
            is_active = name == page
            button.configure(
                background=COLORS["surface_soft"] if is_active else COLORS["surface"],
                foreground=COLORS["green"] if is_active else COLORS["muted"],
            )

        for child in self.content.winfo_children():
            child.destroy()

        if page == "Resumo":
            self.content.pack_configure(pady=22)
            self._build_dashboard()
        elif page == "Lançamentos":
            self.content.pack_configure(pady=(10, 18))
            self._build_cashbook()
        else:
            self.content.pack_configure(pady=22)
            self._build_placeholder(page)

    def _build_cashbook(self) -> None:
        initial_date = self._initial_day_for_selected_month()
        sheet = CashBookSheet(
            self.content,
            self._entries_for_date,
            self._save_page_entries,
            self.categories,
            self._manage_categories,
            initial_date=initial_date,
            date_changed=self._cashbook_date_changed,
        )
        sheet.pack(fill="both", expand=True)

    def _build_header(self, title: str, subtitle: str, show_new_entry: bool) -> None:
        header = tk.Frame(self.content, background=COLORS["background"], height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        text = tk.Frame(header, background=COLORS["background"])
        text.pack(side="left", anchor="n")
        tk.Label(
            text,
            text=title,
            font=FONTS["heading"],
            foreground=COLORS["text"],
            background=COLORS["background"],
        ).pack(anchor="w")
        tk.Label(
            text,
            text=subtitle,
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["background"],
        ).pack(anchor="w", pady=(2, 0))

        if show_new_entry:
            make_button(header, "＋  Novo lançamento", self.open_new_entry, primary=True).pack(side="right", anchor="n")

    def _build_dashboard(self) -> None:
        self._build_header(
            "Resumo do mês",
            f"Movimentação de {self._format_month(self.selected_month).lower()}.",
            True,
        )

        period_bar = tk.Frame(self.content, background=COLORS["background"])
        period_bar.pack(fill="x", pady=(1, 13))
        tk.Label(
            period_bar,
            text="Mês exibido:",
            font=FONTS["body_bold"],
            foreground=COLORS["text"],
            background=COLORS["background"],
        ).pack(side="left", padx=(0, 8))
        make_button(period_bar, "‹", lambda: self._shift_month(-1), width=2).pack(side="left")
        month_selector = ttk.Combobox(
            period_bar,
            textvariable=self.month_selector_var,
            values=tuple(self._format_month(item) for item in self.month_options),
            state="readonly",
            width=21,
            style="Livro.TCombobox",
            font=("Segoe UI", 14, "bold"),
        )
        month_selector.pack(side="left", padx=7)
        month_selector.bind("<<ComboboxSelected>>", self._month_selected)
        make_button(period_bar, "›", lambda: self._shift_month(1), width=2).pack(side="left")
        make_button(period_bar, "Mês atual", self._go_to_current_month).pack(side="left", padx=(8, 0))

        metrics = tk.Frame(self.content, background=COLORS["background"])
        metrics.pack(fill="x", pady=(0, 15))
        for column in range(3):
            metrics.columnconfigure(column, weight=1, uniform="metrics")

        self.income_card = MetricCard(
            metrics,
            "Entradas",
            self.income,
            "↑ Clique para ver os recebimentos",
            COLORS["green"],
            command=self._show_income_details,
        )
        self.expense_card = MetricCard(metrics, "Saídas", self.expense, "↓ Pagamentos do mês", COLORS["red"])
        self.balance_card = MetricCard(metrics, "Saldo", self.income - self.expense, "✓ Resultado positivo", COLORS["brown"])
        self.income_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.expense_card.grid(row=0, column=1, sticky="nsew", padx=7)
        self.balance_card.grid(row=0, column=2, sticky="nsew", padx=(7, 0))

        lower = tk.Frame(self.content, background=COLORS["background"])
        lower.pack(fill="both", expand=True)
        lower.columnconfigure(0, weight=6)
        lower.columnconfigure(1, weight=5)
        lower.rowconfigure(0, weight=1)

        expenses_panel = BorderedFrame(lower)
        expenses_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        expenses_body = expenses_panel.body
        chart_header = tk.Frame(expenses_body, background=COLORS["surface"])
        chart_header.pack(fill="x", padx=20, pady=(15, 4))
        self.chart_title_var = tk.StringVar(value="Onde mais gastou")
        tk.Label(
            chart_header,
            textvariable=self.chart_title_var,
            font=FONTS["section"],
            foreground=COLORS["text"],
            background=COLORS["surface"],
        ).pack(side="left", anchor="center")
        self.chart_pie_button = make_button(
            chart_header,
            "Pizza (%)",
            lambda: self._set_expense_chart_mode("pie"),
        )
        self.chart_pie_button.pack(side="right")
        self.chart_bars_button = make_button(
            chart_header,
            "Linhas",
            lambda: self._set_expense_chart_mode("bars"),
        )
        self.chart_bars_button.pack(side="right", padx=(0, 7))
        self.show_all_expenses_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            chart_header,
            text="Todas as despesas",
            variable=self.show_all_expenses_var,
            command=self._toggle_all_expenses,
            font=("Segoe UI", 12, "bold"),
            foreground=COLORS["text"],
            background=COLORS["surface"],
            activeforeground=COLORS["text"],
            activebackground=COLORS["surface"],
            selectcolor=COLORS["surface"],
            cursor="hand2",
            takefocus=True,
            padx=7,
        ).pack(side="right", padx=(0, 9))
        chart_area = tk.Frame(expenses_body, background=COLORS["surface"])
        chart_area.pack(fill="both", expand=True, padx=20)
        chart_scrollbar = ttk.Scrollbar(chart_area, orient="vertical")
        chart_scrollbar.pack(side="right", fill="y")
        self.expense_chart = ExpenseChart(
            chart_area,
            self.expenses_by_category,
            mode=self.expense_chart_mode,
            show_all=self.show_all_expenses_var.get(),
            on_category_click=self._show_category_details,
        )
        self.expense_chart.configure(yscrollcommand=chart_scrollbar.set)
        chart_scrollbar.configure(command=self.expense_chart.yview)
        self.expense_chart.pack(side="left", fill="both", expand=True)
        self.expense_chart.after_idle(self.expense_chart.draw)
        self.chart_hint_var = tk.StringVar()
        tk.Label(
            expenses_body,
            textvariable=self.chart_hint_var,
            font=FONTS["small"],
            foreground=COLORS["muted"],
            background=COLORS["surface"],
        ).pack(anchor="w", padx=20, pady=(0, 16))
        self._update_chart_mode_controls()

        watch_panel = BorderedFrame(lower)
        watch_panel.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        watch_header = tk.Frame(watch_panel.body, background=COLORS["surface"])
        watch_header.pack(fill="x", padx=20, pady=(15, 3))
        tk.Label(
            watch_header,
            text="Categorias para acompanhar",
            font=FONTS["section"],
            foreground=COLORS["text"],
            background=COLORS["surface"],
        ).pack(side="left", anchor="center")
        make_button(
            watch_header,
            "Escolher categorias",
            self._choose_watched_categories,
        ).pack(side="right")
        tk.Label(
            watch_panel.body,
            text=f"Entradas e saídas de {self._format_month(self.selected_month).lower()}.",
            font=FONTS["small"],
            foreground=COLORS["muted"],
            background=COLORS["surface"],
        ).pack(anchor="w", padx=20, pady=(0, 10))
        self.watch_content = tk.Frame(watch_panel.body, background=COLORS["surface"])
        self.watch_content.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self._populate_category_watch()

    def _build_placeholder(self, page: str) -> None:
        self._build_header(page, "Esta tela será construída na próxima etapa do protótipo.", False)
        panel = BorderedFrame(self.content)
        panel.pack(fill="both", expand=True, pady=(7, 0))
        center = tk.Frame(panel.body, background=COLORS["surface"])
        center.place(relx=0.5, rely=0.44, anchor="center")
        tk.Label(
            center,
            text="Em construção",
            font=FONTS["section"],
            foreground=COLORS["text"],
            background=COLORS["surface"],
        ).pack(pady=(0, 8))
        tk.Label(
            center,
            text="A navegação já funciona. O conteúdo desta área será desenvolvido em seguida.",
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["surface"],
        ).pack(pady=(0, 18))
        make_button(center, "Voltar ao resumo", lambda: self.show_page("Resumo"), primary=True).pack()

    def _populate_category_watch(self) -> None:
        for child in self.watch_content.winfo_children():
            child.destroy()

        totals = calculate_category_watch_totals(
            self.category_records,
            self.watched_category_ids,
            self.entries,
            self.selected_month,
        )
        if not totals:
            tk.Label(
                self.watch_content,
                text=(
                    "Nenhuma categoria selecionada.\n\n"
                    "Clique em “Escolher categorias” para montar este acompanhamento."
                ),
                font=FONTS["body"],
                foreground=COLORS["muted"],
                background=COLORS["surface"],
                justify="center",
                wraplength=390,
            ).pack(expand=True, pady=35)
            return

        combined_income = sum((total.income for total in totals), Decimal("0"))
        combined_expense = sum((total.expense for total in totals), Decimal("0"))
        footer = tk.Frame(self.watch_content, background=COLORS["surface_soft"])
        footer.pack(side="bottom", fill="x", pady=(10, 0))
        self._watch_total(footer, "ENTRADAS SELECIONADAS", combined_income, COLORS["green"]).pack(
            side="left", fill="x", expand=True, padx=(12, 6), pady=9
        )
        self._watch_total(footer, "SAÍDAS SELECIONADAS", combined_expense, COLORS["red"]).pack(
            side="left", fill="x", expand=True, padx=(6, 12), pady=9
        )

        table_holder = tk.Frame(self.watch_content, background=COLORS["border"], padx=1, pady=1)
        table_holder.pack(fill="both", expand=True)
        style = ttk.Style(self)
        style.configure(
            "CategoryWatch.Treeview",
            font=("Segoe UI", 12),
            rowheight=38,
            background=COLORS["surface"],
            fieldbackground=COLORS["surface"],
            foreground=COLORS["text"],
            borderwidth=0,
        )
        style.configure(
            "CategoryWatch.Treeview.Heading",
            font=("Segoe UI", 11, "bold"),
            background=COLORS["surface_soft"],
            foreground=COLORS["text"],
            padding=7,
        )
        style.map(
            "CategoryWatch.Treeview",
            background=[("selected", COLORS["row_active"])],
            foreground=[("selected", COLORS["text"])],
        )

        columns = ("category", "income", "expense")
        table = ttk.Treeview(
            table_holder,
            columns=columns,
            show="headings",
            style="CategoryWatch.Treeview",
            selectmode="browse",
        )
        scrollbar = ttk.Scrollbar(table_holder, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        table.pack(side="left", fill="both", expand=True)
        table.heading("category", text="CATEGORIA")
        table.heading("income", text="ENTRADAS")
        table.heading("expense", text="SAÍDAS")
        table.column("category", width=190, minwidth=130, anchor="w")
        table.column("income", width=125, minwidth=105, anchor="e", stretch=False)
        table.column("expense", width=125, minwidth=105, anchor="e", stretch=False)

        for total in totals:
            table.insert(
                "",
                "end",
                values=(
                    total.name,
                    format_brl(total.income),
                    format_brl(total.expense),
                ),
            )

    def _watch_total(
        self,
        parent: tk.Misc,
        title: str,
        value: Decimal,
        color: str,
    ) -> tk.Frame:
        container = tk.Frame(parent, background=COLORS["surface_soft"])
        tk.Label(
            container,
            text=title,
            font=("Segoe UI", 10, "bold"),
            foreground=COLORS["muted"],
            background=COLORS["surface_soft"],
        ).pack(anchor="w")
        tk.Label(
            container,
            text=format_brl(value),
            font=FONTS["section"],
            foreground=color,
            background=COLORS["surface_soft"],
        ).pack(anchor="w", pady=(2, 0))
        return container

    def _choose_watched_categories(self) -> None:
        dialog = CategoryWatchDialog(
            self,
            self.category_records,
            self.watched_category_ids,
        )
        self.wait_window(dialog)
        if dialog.result is None:
            return
        self.watched_category_ids = set(dialog.result)
        try:
            self.preferences_store.save_watched_category_ids(self.watched_category_ids)
        except OSError:
            messagebox.showwarning(
                "Seleção não foi salva",
                "As categorias serão exibidas agora, mas talvez precisem ser escolhidas novamente ao abrir o programa.",
                parent=self,
            )
        self._populate_category_watch()

    def _reconcile_watched_categories(self) -> None:
        valid_ids = {category.id for category in self.category_records}
        filtered_ids = self.watched_category_ids & valid_ids
        if filtered_ids == self.watched_category_ids:
            return
        self.watched_category_ids = filtered_ids
        try:
            self.preferences_store.save_watched_category_ids(self.watched_category_ids)
        except OSError:
            pass

    def _set_expense_chart_mode(self, mode: str) -> None:
        self.expense_chart_mode = "pie" if mode == "pie" else "bars"
        self.expense_chart.set_mode(self.expense_chart_mode)
        self._update_chart_mode_controls()

    def _toggle_all_expenses(self) -> None:
        self.expense_chart.set_show_all(self.show_all_expenses_var.get())
        self._update_chart_mode_controls()

    def _update_chart_mode_controls(self) -> None:
        buttons = (
            (self.chart_bars_button, self.expense_chart_mode == "bars"),
            (self.chart_pie_button, self.expense_chart_mode == "pie"),
        )
        for button, active in buttons:
            button.configure(
                background=COLORS["green"] if active else COLORS["surface_soft"],
                foreground=COLORS["white"] if active else COLORS["text"],
                activebackground=COLORS["green_hover"] if active else COLORS["border"],
                activeforeground=COLORS["white"] if active else COLORS["text"],
            )
        self.chart_hint_var.set(
            (
                "Clique em uma fatia ou categoria para ver todos os lançamentos."
                if self.expense_chart_mode == "pie"
                else "Comparação dos valores gastos por categoria."
            )
            if self.show_all_expenses_var.get()
            else (
                "Clique em uma fatia ou categoria para ver os lançamentos das maiores despesas."
                if self.expense_chart_mode == "pie"
                else "As 5 categorias com maiores gastos no mês."
            )
        )
        self.chart_title_var.set(
            "Todas as despesas"
            if self.show_all_expenses_var.get()
            else "Onde mais gastou"
        )

    def _show_category_details(
        self,
        display_name: str,
        category_names: tuple[str, ...],
    ) -> None:
        selected = set(category_names)
        entries = [
            entry
            for entry in self.entries
            if not entry.is_income
            and entry.category in selected
            and entry.date.year == self.selected_month.year
            and entry.date.month == self.selected_month.month
        ]
        CategoryDetailsDialog(
            self,
            display_name,
            self._format_month(self.selected_month),
            entries,
        )

    def _show_income_details(self) -> None:
        entries = [
            entry
            for entry in self.entries
            if entry.is_income
            and entry.date.year == self.selected_month.year
            and entry.date.month == self.selected_month.month
        ]
        CategoryDetailsDialog(
            self,
            "Entradas",
            self._format_month(self.selected_month),
            entries,
            detail_type="income",
        )

    def open_new_entry(self) -> None:
        initial_date = self._initial_day_for_selected_month()
        dialog = NewEntryDialog(self, self.categories, initial_date=initial_date)
        self.wait_window(dialog)
        if dialog.result is None:
            return

        try:
            entry = self.repository.create_entry(dialog.result, self.category_records)
        except SupabaseError as error:
            self._show_sync_error("O lançamento não foi salvo", error)
            return

        self.entries.insert(0, entry)
        self.sync_status_var.set("●  Sincronizado")
        self._recalculate_totals()
        self.income_card.set_value(self.income)
        self.expense_card.set_value(self.expense)
        self.balance_card.set_value(self.income - self.expense)
        self.expense_chart.values = self.expenses_by_category
        self.expense_chart.draw()
        self._populate_category_watch()

    def _entries_for_date(self, selected_date: date) -> list[Entry]:
        return [entry for entry in self.entries if entry.date == selected_date]

    def _save_page_entries(self, selected_date: date, page_entries: list[Entry]) -> None:
        try:
            saved_entries = self.repository.replace_day_entries(
                selected_date,
                page_entries,
                self.category_records,
            )
        except SupabaseError:
            self.sync_status_var.set("●  Sem sincronização")
            raise
        other_dates = [entry for entry in self.entries if entry.date != selected_date]
        self.entries = saved_entries + other_dates
        self.sync_status_var.set("●  Sincronizado")
        self._recalculate_totals()

    def _load_month_from_cloud(self, month: date) -> None:
        cloud_entries = self.repository.load_month_entries(month, self.category_records)
        other_months = [
            entry
            for entry in self.entries
            if entry.date.year != month.year or entry.date.month != month.month
        ]
        self.entries = cloud_entries + other_months

    def _refresh_current_month(self) -> None:
        try:
            updated_categories = self.repository.load_categories()
            if not updated_categories:
                raise SupabaseError("Nenhuma categoria foi encontrada para este usuário.")
            cloud_entries = self.repository.load_month_entries(
                self.selected_month,
                updated_categories,
            )
        except SupabaseError as error:
            self._show_sync_error("Não foi possível atualizar", error)
            return

        self.category_records = updated_categories
        self.categories = [category.name for category in self.category_records]
        self._reconcile_watched_categories()
        other_months = [
            entry
            for entry in self.entries
            if entry.date.year != self.selected_month.year
            or entry.date.month != self.selected_month.month
        ]
        self.entries = cloud_entries + other_months
        self.sync_status_var.set("●  Sincronizado")
        self._recalculate_totals()
        self.show_page(self.active_page)

    def _recalculate_totals(self) -> None:
        month_entries = [
            entry
            for entry in self.entries
            if entry.date.year == self.selected_month.year
            and entry.date.month == self.selected_month.month
        ]
        self.income = sum(
            (entry.value for entry in month_entries if entry.is_income),
            Decimal("0"),
        )
        self.expense = sum(
            (entry.value for entry in month_entries if not entry.is_income),
            Decimal("0"),
        )
        categories: dict[str, Decimal] = {}
        for entry in month_entries:
            if entry.is_income:
                continue
            categories[entry.category] = categories.get(entry.category, Decimal("0")) + entry.value
        self.expenses_by_category = categories

    def _build_month_options(self) -> list[date]:
        current_year = date.today().year
        return [
            date(year, month, 1)
            for year in range(current_year - 5, current_year + 2)
            for month in range(1, 13)
        ]

    def _format_month(self, value: date) -> str:
        return f"{self.MONTH_NAMES[value.month - 1]} de {value.year}"

    @staticmethod
    def _add_months(value: date, amount: int) -> date:
        month_index = value.year * 12 + value.month - 1 + amount
        return date(month_index // 12, month_index % 12 + 1, 1)

    def _set_selected_month(self, value: date, rebuild: bool = True) -> None:
        selected_month = value.replace(day=1)
        try:
            self._load_month_from_cloud(selected_month)
        except SupabaseError as error:
            self._show_sync_error("Não foi possível abrir o mês", error)
            return

        self.selected_month = selected_month
        self.sync_status_var.set("●  Sincronizado")
        formatted = self._format_month(self.selected_month)
        self.period_var.set(formatted)
        self.month_selector_var.set(formatted)
        self._recalculate_totals()
        if rebuild and self.active_page == "Resumo":
            self.show_page("Resumo")

    def _shift_month(self, amount: int) -> None:
        self._set_selected_month(self._add_months(self.selected_month, amount))

    def _month_selected(self, _event=None) -> None:
        selected = self.month_lookup.get(self.month_selector_var.get())
        if selected is not None:
            self._set_selected_month(selected)

    def _go_to_current_month(self) -> None:
        self._set_selected_month(date.today().replace(day=1))

    def _initial_day_for_selected_month(self) -> date:
        today = date.today()
        if today.year == self.selected_month.year and today.month == self.selected_month.month:
            return today
        month_entries = [
            entry.date
            for entry in self.entries
            if entry.date.year == self.selected_month.year
            and entry.date.month == self.selected_month.month
        ]
        return max(month_entries) if month_entries else self.selected_month

    def _cashbook_date_changed(self, selected_date: date) -> None:
        month = selected_date.replace(day=1)
        if month != self.selected_month:
            self._set_selected_month(month, rebuild=False)

    def _manage_categories(self) -> list[str]:
        dialog = CategoryManagerDialog(self, self.categories)
        self.wait_window(dialog)
        if dialog.result is None:
            return list(self.categories)

        previous = list(self.categories)
        if not dialog.operations:
            return previous
        try:
            updated_categories = self.repository.manage_categories(dialog.operations)
            cloud_entries = self.repository.load_month_entries(
                self.selected_month,
                updated_categories,
            )
        except SupabaseError as error:
            self._show_sync_error("As categorias não puderam ser salvas", error)
            return previous

        self.category_records = updated_categories
        self.categories = [category.name for category in self.category_records]
        self._reconcile_watched_categories()
        other_months = [
            entry
            for entry in self.entries
            if entry.date.year != self.selected_month.year
            or entry.date.month != self.selected_month.month
        ]
        self.entries = cloud_entries + other_months
        self.sync_status_var.set("●  Sincronizado")
        self._recalculate_totals()
        return list(self.categories)

    def _show_sync_error(self, title: str, error: Exception) -> None:
        self.sync_status_var.set("●  Sem sincronização")
        messagebox.showerror(title, str(error), parent=self)

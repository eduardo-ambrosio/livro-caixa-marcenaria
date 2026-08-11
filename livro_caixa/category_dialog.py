from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .theme import COLORS, FONTS, make_button


class CategoryManagerDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, categories: list[str]) -> None:
        super().__init__(parent)
        self.title("Gerenciar categorias")
        self.configure(background=COLORS["background"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.categories = list(categories)
        self.result: list[str] | None = None
        self.operations: list[tuple[str, str, str | None]] = []

        width, height = 485, 520
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 2, 0)
        self.geometry(f"+{x}+{y}")

        outer = tk.Frame(self, background=COLORS["background"])
        outer.pack(fill="both", expand=True, padx=27, pady=23)
        tk.Label(
            outer,
            text="Categorias dos lançamentos",
            font=FONTS["heading"],
            foreground=COLORS["text"],
            background=COLORS["background"],
        ).pack(anchor="w")
        tk.Label(
            outer,
            text="Personalize a lista usada na coluna Categoria.",
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["background"],
        ).pack(anchor="w", pady=(2, 17))

        list_holder = tk.Frame(outer, background=COLORS["border"], padx=1, pady=1)
        list_holder.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_holder, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.listbox = tk.Listbox(
            list_holder,
            yscrollcommand=scrollbar.set,
            font=FONTS["body"],
            foreground=COLORS["text"],
            background=COLORS["surface"],
            selectbackground=COLORS["green_soft"],
            selectforeground=COLORS["green"],
            activestyle="none",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.listbox.yview)
        self.listbox.bind("<Double-Button-1>", lambda _event: self._rename())
        self._refresh_list()

        edit_actions = tk.Frame(outer, background=COLORS["background"])
        edit_actions.pack(fill="x", pady=(11, 19))
        make_button(edit_actions, "+ Adicionar", self._add).pack(side="left")
        make_button(edit_actions, "Renomear", self._rename).pack(side="left", padx=7)
        make_button(edit_actions, "Excluir", self._remove).pack(side="left")

        actions = tk.Frame(outer, background=COLORS["background"])
        actions.pack(fill="x")
        make_button(actions, "Cancelar", self.destroy, width=10).pack(side="right", padx=(8, 0))
        make_button(actions, "Salvar categorias", self._save, primary=True, width=17).pack(side="right")
        self.bind("<Escape>", lambda _event: self.destroy())

    def _refresh_list(self, selected_index: int | None = None) -> None:
        self.listbox.delete(0, "end")
        for category in self.categories:
            self.listbox.insert("end", category)
        if selected_index is not None and self.categories:
            index = min(selected_index, len(self.categories) - 1)
            self.listbox.selection_set(index)
            self.listbox.see(index)

    def _ask_name(self, title: str, prompt: str, initial: str = "") -> str | None:
        value = simpledialog.askstring(title, prompt, initialvalue=initial, parent=self)
        if value is None:
            return None
        name = " ".join(value.strip().split())
        if not name:
            messagebox.showwarning("Nome inválido", "Informe o nome da categoria.", parent=self)
            return None
        if len(name) > 40:
            messagebox.showwarning("Nome muito longo", "Use no máximo 40 caracteres.", parent=self)
            return None
        return name

    def _already_exists(self, name: str, ignored_index: int | None = None) -> bool:
        key = name.casefold()
        return any(
            category.casefold() == key and index != ignored_index
            for index, category in enumerate(self.categories)
        )

    def _add(self) -> None:
        name = self._ask_name("Adicionar categoria", "Nome da nova categoria:")
        if name is None:
            return
        if self._already_exists(name):
            messagebox.showwarning("Categoria existente", "Essa categoria já está na lista.", parent=self)
            return
        self.categories.append(name)
        self._refresh_list(len(self.categories) - 1)

    def _rename(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Selecione uma categoria", "Escolha a categoria que deseja renomear.", parent=self)
            return
        index = selection[0]
        old_name = self.categories[index]
        new_name = self._ask_name("Renomear categoria", "Novo nome:", old_name)
        if new_name is None or new_name == old_name:
            return
        if self._already_exists(new_name, ignored_index=index):
            messagebox.showwarning("Categoria existente", "Já existe uma categoria com esse nome.", parent=self)
            return
        self.categories[index] = new_name
        self.operations.append(("rename", old_name, new_name))
        self._refresh_list(index)

    def _remove(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Selecione uma categoria", "Escolha a categoria que deseja excluir.", parent=self)
            return
        if len(self.categories) == 1:
            messagebox.showwarning("Categoria necessária", "É necessário manter pelo menos uma categoria.", parent=self)
            return
        index = selection[0]
        name = self.categories[index]
        confirmed = messagebox.askyesno(
            "Excluir categoria",
            f"Excluir a categoria “{name}”?\n\nLançamentos antigos serão movidos para outra categoria.",
            parent=self,
        )
        if not confirmed:
            return
        self.categories.pop(index)
        self.operations.append(("delete", name, None))
        self._refresh_list(index)

    def _save(self) -> None:
        self.result = list(self.categories)
        self.destroy()

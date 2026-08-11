from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "background": "#F5F1EA",
    "surface": "#FFFDF9",
    "surface_soft": "#EFE7DA",
    "border": "#DED4C5",
    "text": "#2A251E",
    "muted": "#70675B",
    "green": "#356449",
    "green_hover": "#2C563E",
    "green_soft": "#E1EEE5",
    "brown": "#A96332",
    "red": "#B23B35",
    "red_soft": "#FAE7E4",
    "white": "#FFFFFF",
    "row_active": "#FFE6A6",
    "row_active_border": "#B76518",
}

FONTS = {
    "body": ("Segoe UI", 12),
    "body_bold": ("Segoe UI", 12, "bold"),
    "small": ("Segoe UI", 10),
    "heading": ("Segoe UI", 21, "bold"),
    "section": ("Segoe UI", 14, "bold"),
    "metric": ("Segoe UI", 19, "bold"),
    "brand": ("Segoe UI", 12, "bold"),
}


def configure_ttk(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "Livro.TCombobox",
        fieldbackground=COLORS["surface"],
        background=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=10,
        font=("Segoe UI", 14),
    )
    style.configure(
        "LivroActive.TCombobox",
        fieldbackground=COLORS["row_active"],
        background=COLORS["row_active"],
        foreground=COLORS["text"],
        bordercolor=COLORS["row_active_border"],
        lightcolor=COLORS["row_active_border"],
        darkcolor=COLORS["row_active_border"],
        padding=10,
        font=("Segoe UI", 14),
    )
    style.map(
        "LivroActive.TCombobox",
        fieldbackground=[("readonly", COLORS["row_active"])],
        foreground=[
            ("disabled", COLORS["muted"]),
            ("readonly", COLORS["text"]),
            ("!disabled", COLORS["text"]),
        ],
        selectbackground=[("readonly", COLORS["row_active"])],
        selectforeground=[("readonly", COLORS["text"])],
    )
    style.map(
        "Livro.TCombobox",
        fieldbackground=[("readonly", COLORS["surface"])],
        foreground=[
            ("disabled", COLORS["muted"]),
            ("readonly", COLORS["text"]),
            ("!disabled", COLORS["text"]),
        ],
        selectbackground=[("readonly", COLORS["surface"])],
        selectforeground=[("readonly", COLORS["text"])],
    )
    style.configure(
        "Livro.TEntry",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=10,
        font=FONTS["body"],
    )
    style.configure(
        "LivroDate.TEntry",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["green"],
        lightcolor=COLORS["green"],
        darkcolor=COLORS["green"],
        padding=10,
        font=("Segoe UI", 17, "bold"),
    )
    root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 14))
    return style


def make_button(
    parent: tk.Misc,
    text: str,
    command,
    *,
    primary: bool = False,
    width: int | None = None,
) -> tk.Button:
    background = COLORS["green"] if primary else COLORS["surface_soft"]
    foreground = COLORS["white"] if primary else COLORS["text"]
    active_background = COLORS["green_hover"] if primary else COLORS["border"]
    options = {
        "text": text,
        "command": command,
        "font": FONTS["body_bold"],
        "background": background,
        "foreground": foreground,
        "activebackground": active_background,
        "activeforeground": foreground,
        "relief": "flat",
        "borderwidth": 0,
        "cursor": "hand2",
        "padx": 15,
        "pady": 10,
    }
    if width is not None:
        options["width"] = width
    return tk.Button(parent, **options)

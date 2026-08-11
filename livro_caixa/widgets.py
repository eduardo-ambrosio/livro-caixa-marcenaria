from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from math import cos, radians, sin
from typing import Callable
from decimal import Decimal

from .theme import COLORS, FONTS


def format_brl(value: Decimal, decimals: bool = True) -> str:
    places = 2 if decimals else 0
    formatted = f"{value:,.{places}f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


class BorderedFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, **kwargs) -> None:
        kwargs.setdefault("background", COLORS["border"])
        kwargs.setdefault("padx", 1)
        kwargs.setdefault("pady", 1)
        super().__init__(parent, **kwargs)
        self.body = tk.Frame(self, background=COLORS["surface"])
        self.body.pack(fill="both", expand=True)


class MetricCard(BorderedFrame):
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        value: Decimal,
        detail: str,
        accent: str,
    ) -> None:
        super().__init__(parent, height=116)
        self.pack_propagate(False)

        accent_line = tk.Frame(self.body, height=4, background=accent)
        accent_line.pack(fill="x")

        content = tk.Frame(self.body, background=COLORS["surface"])
        content.pack(fill="both", expand=True, padx=17, pady=(11, 10))
        tk.Label(
            content,
            text=title,
            font=FONTS["body"],
            foreground=COLORS["muted"],
            background=COLORS["surface"],
        ).pack(anchor="w")
        self.value_label = tk.Label(
            content,
            text=format_brl(value),
            font=FONTS["metric"],
            foreground=COLORS["text"],
            background=COLORS["surface"],
        )
        self.value_label.pack(anchor="w", pady=(3, 1))
        tk.Label(
            content,
            text=detail,
            font=FONTS["small"],
            foreground=COLORS["muted"],
            background=COLORS["surface"],
        ).pack(anchor="w")

    def set_value(self, value: Decimal) -> None:
        self.value_label.configure(text=format_brl(value))


CategoryClick = Callable[[str, tuple[str, ...]], None]


class ExpenseChart(tk.Canvas):
    PIE_COLORS = (
        "#356449",
        "#B76518",
        "#2C6E91",
        "#B23B35",
        "#795692",
        "#C6922E",
    )

    def __init__(
        self,
        parent: tk.Misc,
        values: dict[str, Decimal],
        mode: str = "bars",
        on_category_click: CategoryClick | None = None,
    ) -> None:
        super().__init__(
            parent,
            background=COLORS["surface"],
            highlightthickness=0,
            height=330,
        )
        self.values = values
        self.mode = mode
        self.on_category_click = on_category_click
        self.bind("<Configure>", lambda _event: self.draw())

    def set_mode(self, mode: str) -> None:
        self.mode = "pie" if mode == "pie" else "bars"
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        if not self.values:
            self.create_text(
                max(self.winfo_width(), 300) / 2,
                max(self.winfo_height(), 160) / 2,
                text="Nenhuma saída registrada neste mês.",
                anchor="center",
                fill=COLORS["muted"],
                font=FONTS["body"],
            )
            return

        items = sorted(
            ((name, value) for name, value in self.values.items() if value > 0),
            key=lambda item: item[1],
            reverse=True,
        )
        if not items:
            return
        if self.mode == "pie":
            self._draw_pie(items)
        else:
            self._draw_bars(items[:5])

    def _draw_bars(self, items: list[tuple[str, Decimal]]) -> None:
        maximum = max(value for _, value in items) or Decimal("1")
        width = max(self.winfo_width(), 420)
        label_font = tkfont.Font(font=FONTS["body"])
        longest_label = max(label_font.measure(name) for name, _value in items)
        label_width = min(max(longest_label + 24, 120), int(width * 0.42))
        value_width = 92
        track_width = max(width - label_width - value_width - 22, 80)
        y = 23

        for name, value in items:
            available_label_width = label_width - 14
            display_name = self._fit_text(name, label_font, available_label_width)
            self.create_text(
                0,
                y,
                text=display_name,
                anchor="w",
                fill=COLORS["text"],
                font=FONTS["body"],
            )
            track_x = label_width
            track_y = y - 5
            self.create_rectangle(
                track_x,
                track_y,
                track_x + track_width,
                track_y + 10,
                fill=COLORS["surface_soft"],
                outline="",
            )
            filled = int(track_width * float(value / maximum))
            self.create_rectangle(
                track_x,
                track_y,
                track_x + filled,
                track_y + 10,
                fill=COLORS["brown"],
                outline="",
            )
            self.create_text(
                width - 4,
                y,
                text=format_brl(value, decimals=False),
                anchor="e",
                fill=COLORS["muted"],
                font=FONTS["body_bold"],
            )
            y += 43

    def _draw_pie(self, items: list[tuple[str, Decimal]]) -> None:
        pie_items: list[tuple[str, Decimal, tuple[str, ...]]] = [
            (name, value, (name,)) for name, value in items
        ]
        if len(pie_items) > 6:
            remaining = sum((value for _name, value, _categories in pie_items[5:]), Decimal("0"))
            remaining_categories = tuple(name for name, _value, _categories in pie_items[5:])
            pie_items = pie_items[:5] + [("Demais categorias", remaining, remaining_categories)]

        total = sum((value for _name, value, _categories in pie_items), Decimal("0"))
        if total <= 0:
            return

        width = max(self.winfo_width(), 420)
        height = max(self.winfo_height(), 220)
        pie_region_width = int(width * 0.52)
        diameter = min(height - 30, pie_region_width - 24, 315)
        left = max(12, (pie_region_width - diameter) // 2)
        top = max((height - diameter) // 2, 8)
        center_x = left + diameter / 2
        center_y = top + diameter / 2
        radius = diameter / 2
        start_angle = 90.0

        for index, (name, value, categories) in enumerate(pie_items):
            percentage = float(value / total)
            extent = percentage * 360.0
            color = self.PIE_COLORS[index % len(self.PIE_COLORS)]
            tag = f"pie-category-{index}"
            self.create_arc(
                left,
                top,
                left + diameter,
                top + diameter,
                start=start_angle,
                extent=-extent,
                fill=color,
                outline=COLORS["surface"],
                width=2,
                tags=(tag,),
            )
            if percentage >= 0.09:
                middle = start_angle - extent / 2
                label_x = center_x + cos(radians(middle)) * radius * 0.61
                label_y = center_y - sin(radians(middle)) * radius * 0.61
                self.create_text(
                    label_x,
                    label_y,
                    text=f"{percentage * 100:.0f}%",
                    fill=COLORS["white"],
                    font=FONTS["body_bold"],
                    tags=(tag,),
                )
            self._bind_category_click(tag, name, categories)
            start_angle -= extent

        legend_x = pie_region_width + 12
        legend_width = max(width - legend_x - 4, 120)
        legend_font = tkfont.Font(font=FONTS["body"])
        details_width = 145
        name_width = max(legend_width - details_width - 28, 45)
        row_height = min(35, max(28, (height - 20) // len(pie_items)))
        y = max(16, (height - row_height * len(pie_items)) // 2 + row_height // 2)

        for index, (name, value, categories) in enumerate(pie_items):
            percentage = float(value / total) * 100
            color = self.PIE_COLORS[index % len(self.PIE_COLORS)]
            tag = f"pie-category-{index}"
            self.create_rectangle(
                legend_x,
                y - 7,
                legend_x + 14,
                y + 7,
                fill=color,
                outline="",
                tags=(tag,),
            )
            self.create_text(
                legend_x + 22,
                y,
                text=self._fit_text(name, legend_font, name_width),
                anchor="w",
                fill=COLORS["text"],
                font=FONTS["body"],
                tags=(tag,),
            )
            self.create_text(
                width - 4,
                y,
                text=f"{percentage:.1f}%  ·  {format_brl(value, decimals=False)}",
                anchor="e",
                fill=COLORS["text"],
                font=FONTS["body_bold"],
                tags=(tag,),
            )
            self._bind_category_click(tag, name, categories)
            y += row_height

    def _bind_category_click(
        self,
        tag: str,
        display_name: str,
        categories: tuple[str, ...],
    ) -> None:
        self.tag_bind(
            tag,
            "<Button-1>",
            lambda _event, name=display_name, selected=categories: self._notify_category(name, selected),
        )
        self.tag_bind(tag, "<Enter>", lambda _event: self.configure(cursor="hand2"))
        self.tag_bind(tag, "<Leave>", lambda _event: self.configure(cursor=""))

    def _notify_category(self, display_name: str, categories: tuple[str, ...]) -> None:
        if self.on_category_click is not None:
            self.on_category_click(display_name, categories)

    @staticmethod
    def _fit_text(text: str, font: tkfont.Font, max_width: int) -> str:
        if font.measure(text) <= max_width:
            return text
        candidate = text
        while len(candidate) > 2 and font.measure(candidate + "…") > max_width:
            candidate = candidate[:-1].rstrip()
        return candidate + "…"

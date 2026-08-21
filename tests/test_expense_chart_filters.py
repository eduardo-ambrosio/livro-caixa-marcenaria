from __future__ import annotations

import unittest
from decimal import Decimal

from livro_caixa.widgets import ExpenseChart


class ExpenseChartFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.items = [
            (f"Categoria {index}", Decimal(str(100 - index)))
            for index in range(8)
        ]

    def test_lines_show_only_five_largest_by_default(self) -> None:
        visible = ExpenseChart._visible_bar_items(self.items, show_all=False)

        self.assertEqual(visible, self.items[:5])

    def test_lines_show_every_category_when_selected(self) -> None:
        visible = ExpenseChart._visible_bar_items(self.items, show_all=True)

        self.assertEqual(visible, self.items)

    def test_pie_groups_smaller_categories_by_default(self) -> None:
        visible = ExpenseChart._visible_pie_items(self.items, show_all=False)

        self.assertEqual(len(visible), 6)
        self.assertEqual(visible[-1][0], "Demais categorias")
        self.assertEqual(
            visible[-1][2],
            ("Categoria 5", "Categoria 6", "Categoria 7"),
        )

    def test_pie_keeps_every_category_when_selected(self) -> None:
        visible = ExpenseChart._visible_pie_items(self.items, show_all=True)

        self.assertEqual([name for name, _value, _categories in visible], [
            name for name, _value in self.items
        ])


if __name__ == "__main__":
    unittest.main()

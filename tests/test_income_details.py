from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

import livro_caixa.application as application_module
from livro_caixa.application import LivroCaixaApp
from livro_caixa.models import Entry


def make_entry(entry_date: date, *, is_income: bool, description: str) -> Entry:
    return Entry(
        date=entry_date,
        description=description,
        category="Venda" if is_income else "Material",
        is_income=is_income,
        value=Decimal("100.00"),
        payment_method="",
    )


class IncomeDetailsTests(unittest.TestCase):
    def test_dialog_receives_only_income_from_selected_month(self) -> None:
        selected_month = date(2026, 8, 1)
        expected = make_entry(date(2026, 8, 10), is_income=True, description="Armário")

        class AppStub:
            entries = [
                expected,
                make_entry(date(2026, 8, 11), is_income=False, description="MDF"),
                make_entry(date(2026, 7, 30), is_income=True, description="Venda anterior"),
            ]

            def __init__(self) -> None:
                self.selected_month = selected_month

            @staticmethod
            def _format_month(_value: date) -> str:
                return "Agosto de 2026"

        captured: dict[str, object] = {}

        def dialog_stub(parent, category_name, period_name, entries, detail_type="expense"):
            captured.update(
                parent=parent,
                category_name=category_name,
                period_name=period_name,
                entries=entries,
                detail_type=detail_type,
            )

        original_dialog = application_module.CategoryDetailsDialog
        application_module.CategoryDetailsDialog = dialog_stub
        try:
            app = AppStub()
            LivroCaixaApp._show_income_details(app)
        finally:
            application_module.CategoryDetailsDialog = original_dialog

        self.assertEqual(captured["entries"], [expected])
        self.assertEqual(captured["category_name"], "Entradas")
        self.assertEqual(captured["period_name"], "Agosto de 2026")
        self.assertEqual(captured["detail_type"], "income")


if __name__ == "__main__":
    unittest.main()

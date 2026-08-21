from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from livro_caixa.category_watch import calculate_category_watch_totals
from livro_caixa.models import Entry
from livro_caixa.preferences_store import PreferencesStore
from livro_caixa.supabase_client import CategoryRecord


def make_entry(
    entry_date: date,
    category: str,
    value: str,
    *,
    is_income: bool,
    category_id: str | None,
) -> Entry:
    return Entry(
        date=entry_date,
        description="Teste",
        category=category,
        is_income=is_income,
        value=Decimal(value),
        payment_method="",
        category_id=category_id,
    )


class CategoryWatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.categories = [
            CategoryRecord("venda-id", "Venda", True, 10),
            CategoryRecord("madeira-id", "Madeira", True, 20),
            CategoryRecord("outros-id", "Outros", True, 30),
        ]

    def test_totals_include_only_selected_categories_and_month(self) -> None:
        entries = [
            make_entry(date(2026, 8, 2), "Venda", "1500", is_income=True, category_id="venda-id"),
            make_entry(date(2026, 8, 3), "Venda", "100", is_income=False, category_id="venda-id"),
            make_entry(date(2026, 8, 4), "Madeira", "350", is_income=False, category_id="madeira-id"),
            make_entry(date(2026, 8, 5), "Outros", "90", is_income=False, category_id="outros-id"),
            make_entry(date(2026, 7, 31), "Venda", "800", is_income=True, category_id="venda-id"),
        ]

        totals = calculate_category_watch_totals(
            self.categories,
            {"venda-id", "madeira-id"},
            entries,
            date(2026, 8, 1),
        )

        self.assertEqual([total.name for total in totals], ["Venda", "Madeira"])
        self.assertEqual(totals[0].income, Decimal("1500"))
        self.assertEqual(totals[0].expense, Decimal("100"))
        self.assertEqual(totals[1].income, Decimal("0"))
        self.assertEqual(totals[1].expense, Decimal("350"))

    def test_category_name_is_used_when_old_entry_has_no_valid_id(self) -> None:
        entry = make_entry(
            date(2026, 8, 6),
            "Madeira",
            "75",
            is_income=False,
            category_id="id-antigo",
        )

        totals = calculate_category_watch_totals(
            self.categories,
            {"madeira-id"},
            [entry],
            date(2026, 8, 1),
        )

        self.assertEqual(totals[0].expense, Decimal("75"))


class PreferencesStoreTests(unittest.TestCase):
    def test_selection_is_saved_and_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preferences.json"
            store = PreferencesStore("usuario", path=path)

            store.save_watched_category_ids({"madeira-id", "venda-id"})

            self.assertEqual(
                store.load_watched_category_ids(),
                {"madeira-id", "venda-id"},
            )

    def test_invalid_file_returns_empty_selection(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preferences.json"
            path.write_text("{arquivo inválido", encoding="utf-8")

            self.assertEqual(
                PreferencesStore("usuario", path=path).load_watched_category_ids(),
                set(),
            )


if __name__ == "__main__":
    unittest.main()

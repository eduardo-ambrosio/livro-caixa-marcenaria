from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .models import Entry
from .supabase_client import CategoryRecord


@dataclass(frozen=True, slots=True)
class CategoryWatchTotal:
    category_id: str
    name: str
    income: Decimal
    expense: Decimal


def calculate_category_watch_totals(
    categories: list[CategoryRecord],
    selected_ids: set[str],
    entries: list[Entry],
    selected_month: date,
) -> list[CategoryWatchTotal]:
    selected_categories = [category for category in categories if category.id in selected_ids]
    totals = {
        category.id: {
            "income": Decimal("0"),
            "expense": Decimal("0"),
        }
        for category in selected_categories
    }
    category_id_by_name = {
        category.name.casefold(): category.id for category in selected_categories
    }

    for entry in entries:
        if (
            entry.date.year != selected_month.year
            or entry.date.month != selected_month.month
        ):
            continue
        category_id = entry.category_id
        if category_id not in totals:
            category_id = category_id_by_name.get(entry.category.casefold())
        if category_id not in totals:
            continue
        key = "income" if entry.is_income else "expense"
        totals[category_id][key] += entry.value

    return [
        CategoryWatchTotal(
            category_id=category.id,
            name=category.name,
            income=totals[category.id]["income"],
            expense=totals[category.id]["expense"],
        )
        for category in selected_categories
    ]

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class Entry:
    date: date
    description: str
    category: str
    is_income: bool
    value: Decimal
    payment_method: str
    document: str = ""


def sample_entries() -> list[Entry]:
    today = date.today()
    return [
        Entry(today, "Chapas de MDF", "Madeira", False, Decimal("1250"), "Pix"),
        Entry(today, "Armário planejado — Cliente exemplo", "Venda", True, Decimal("3800"), "Pix"),
        Entry(today, "Manutenção da serra", "Manutenção", False, Decimal("420"), "Dinheiro"),
    ]

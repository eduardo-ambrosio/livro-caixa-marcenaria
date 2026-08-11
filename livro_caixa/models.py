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
    id: str | None = None
    category_id: str | None = None

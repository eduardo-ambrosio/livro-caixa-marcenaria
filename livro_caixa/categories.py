from __future__ import annotations

import json
from pathlib import Path


class CategoryStore:
    DEFAULTS = [
        "Madeira",
        "Ferragens",
        "Funcionários",
        "Energia",
        "Manutenção",
        "Frete",
        "Venda",
        "Outros",
    ]

    def __init__(self, path: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parent.parent
        self.path = path or project_root / "data" / "categories.json"

    def load(self) -> list[str]:
        if not self.path.exists():
            return list(self.DEFAULTS)
        try:
            content = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return list(self.DEFAULTS)

        if not isinstance(content, list):
            return list(self.DEFAULTS)
        categories = self._clean(content)
        return categories or list(self.DEFAULTS)

    def save(self, categories: list[str]) -> None:
        cleaned = self._clean(categories)
        if not cleaned:
            raise ValueError("É necessário manter pelo menos uma categoria.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(cleaned, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _clean(values) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            name = " ".join(value.strip().split())
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            result.append(name)
        return result

from __future__ import annotations

import json
import os
from pathlib import Path


class PreferencesStore:
    """Guarda preferências visuais não sensíveis para cada usuário do aplicativo."""

    def __init__(self, user_id: str, path: Path | None = None) -> None:
        safe_user_id = "".join(
            character for character in user_id if character.isalnum() or character in "-_"
        ) or "default"
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        self.path = path or local_app_data / "LivroCaixa" / f"preferences-{safe_user_id}.json"

    def load_watched_category_ids(self) -> set[str]:
        if not self.path.exists():
            return set()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            values = payload.get("watched_category_ids", [])
            if not isinstance(values, list):
                return set()
            return {
                value
                for value in values
                if isinstance(value, str) and value.strip()
            }
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
            return set()

    def save_watched_category_ids(self, category_ids: set[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        payload = {
            "version": 1,
            "watched_category_ids": sorted(category_ids),
        }
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

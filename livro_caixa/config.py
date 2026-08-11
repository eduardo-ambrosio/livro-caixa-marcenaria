from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(ValueError):
    """Configuração ausente ou inválida para iniciar o aplicativo."""


@dataclass(frozen=True, slots=True)
class SupabaseConfig:
    url: str
    publishable_key: str


def _application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


def load_supabase_config() -> SupabaseConfig:
    file_values = _read_env_file(_application_root() / ".env")
    url = os.environ.get("SUPABASE_URL", file_values.get("SUPABASE_URL", "")).strip().rstrip("/")
    key = os.environ.get(
        "SUPABASE_PUBLISHABLE_KEY",
        file_values.get("SUPABASE_PUBLISHABLE_KEY", ""),
    ).strip()

    if not url.startswith("https://") or not url.endswith(".supabase.co"):
        raise ConfigurationError("O SUPABASE_URL não foi configurado corretamente no arquivo .env.")
    if not key.startswith("sb_publishable_"):
        raise ConfigurationError(
            "A SUPABASE_PUBLISHABLE_KEY não foi configurada corretamente no arquivo .env."
        )
    return SupabaseConfig(url=url, publishable_key=key)

"""Chargement de la configuration depuis le fichier .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _env(key: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(key, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"Variable d'environnement obligatoire manquante : {key}")
    return value  # type: ignore[return-value]


@dataclass(frozen=True)
class Settings:
    # Connexion Postgres
    pg_host: str
    pg_port: int
    pg_user: str
    pg_password: str
    pg_db_source: str
    pg_db_dwh: str

    # Paramètres ETL
    batch_size: int
    late_fee_per_day: float
    grace_days: int

    # Dashboard
    dash_host: str
    dash_port: int
    dash_debug: bool

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            pg_host=_env("PG_HOST", "localhost"),
            pg_port=int(_env("PG_PORT", "5432")),
            pg_user=_env("PG_USER", "postgres", required=True),
            pg_password=_env("PG_PASSWORD", required=True),
            pg_db_source=_env("PG_DB_SOURCE", "sakila"),
            pg_db_dwh=_env("PG_DB_DWH", "sakila_dwh"),
            batch_size=int(_env("ETL_BATCH_SIZE", "5000")),
            late_fee_per_day=float(_env("ETL_LATE_FEE_PER_DAY", "1.0")),
            grace_days=int(_env("ETL_GRACE_DAYS", "0")),
            dash_host=_env("DASH_HOST", "127.0.0.1"),
            dash_port=int(_env("DASH_PORT", "8050")),
            dash_debug=_env("DASH_DEBUG", "True").lower() in ("1", "true", "yes"),
        )


SETTINGS = Settings.load()

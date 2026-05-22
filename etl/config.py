"""Chargement de la configuration depuis le fichier .env (ou les variables
d'environnement injectées par la plateforme d'hébergement, ex: Render)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Sur Render / Railway / Fly.io, les variables sont déjà dans os.environ, et
# le .env n'existe pas. load_dotenv() ne pose alors aucun problème (no-op).
load_dotenv(PROJECT_ROOT / ".env")


def _env(key: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(key, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"Variable d'environnement obligatoire manquante : {key}")
    return value  # type: ignore[return-value]


@dataclass(frozen=True)
class Settings:
    # Connexions PostgreSQL (deux formes possibles)
    #   - via DATABASE_URL_*  : URL libpq complète (utilisée par Render/Railway)
    #   - via PG_*            : variables séparées (mode local / .env)
    source_url: str | None      # source Sakila/Pagila (peut être None si pas d'ETL en prod)
    dwh_url: str                # data warehouse (toujours requis pour le dashboard)

    # Paramètres ETL
    batch_size: int
    late_fee_per_day: float
    grace_days: int

    # Dashboard
    dash_host: str
    dash_port: int
    dash_debug: bool

    # ------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------
    @staticmethod
    def _resolve_url(url_key: str, *, db_default: tuple[str, str], optional: bool = False) -> str | None:
        """Retourne l'URL libpq voulue.

        Priorité :
          1. variable `<url_key>` (ex: `DATABASE_URL_DWH`)
          2. `DATABASE_URL` (fallback unique fourni par certaines plateformes)
          3. construction depuis PG_HOST/PG_PORT/PG_USER/PG_PASSWORD + db_default
        """
        url = os.getenv(url_key) or (os.getenv("DATABASE_URL") if url_key.endswith("_DWH") else None)
        if url:
            # Render fournit parfois "postgres://" — SQLAlchemy veut "postgresql://"
            if url.startswith("postgres://"):
                url = "postgresql://" + url[len("postgres://"):]
            # Forcer le driver psycopg2 pour SQLAlchemy
            if url.startswith("postgresql://"):
                url = "postgresql+psycopg2://" + url[len("postgresql://"):]
            return url

        # Construction depuis PG_*
        host = os.getenv("PG_HOST", "localhost")
        port = os.getenv("PG_PORT", "5432")
        user = os.getenv("PG_USER")
        password = os.getenv("PG_PASSWORD")
        database = os.getenv(db_default[0], db_default[1])

        if not user or not password:
            if optional:
                return None
            raise RuntimeError(
                f"Configuration Postgres manquante : ni {url_key} ni PG_USER/PG_PASSWORD ne sont définis."
            )
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            source_url=cls._resolve_url(
                "DATABASE_URL_SOURCE",
                db_default=("PG_DB_SOURCE", "sakila"),
                optional=True,
            ),
            dwh_url=cls._resolve_url(
                "DATABASE_URL_DWH",
                db_default=("PG_DB_DWH", "sakila_dwh"),
            ),
            batch_size=int(_env("ETL_BATCH_SIZE", "5000")),
            late_fee_per_day=float(_env("ETL_LATE_FEE_PER_DAY", "1.0")),
            grace_days=int(_env("ETL_GRACE_DAYS", "0")),
            dash_host=_env("DASH_HOST", "0.0.0.0"),
            dash_port=int(_env("PORT", _env("DASH_PORT", "8050"))),
            dash_debug=_env("DASH_DEBUG", "False").lower() in ("1", "true", "yes"),
        )


SETTINGS = Settings.load()

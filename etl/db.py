"""Fabriques de connexions SQLAlchemy pour la source et le DWH."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import SETTINGS


def get_source_engine() -> Engine:
    """Engine sur la base source (sakila / pagila).

    Lève RuntimeError si DATABASE_URL_SOURCE / PG_USER ne sont pas définis :
    en prod le dashboard n'a pas besoin de la source, seul l'ETL en a besoin.
    """
    if not SETTINGS.source_url:
        raise RuntimeError(
            "Aucune URL de connexion source définie. Configurez DATABASE_URL_SOURCE "
            "ou PG_HOST/PG_USER/PG_PASSWORD/PG_DB_SOURCE."
        )
    return create_engine(SETTINGS.source_url, future=True, pool_pre_ping=True)


def get_dwh_engine() -> Engine:
    """Engine sur la base data warehouse (sakila_dwh / Render Postgres)."""
    return create_engine(
        SETTINGS.dwh_url,
        future=True,
        pool_pre_ping=True,
        pool_recycle=300,   # recyclage agressif pour Render (idle disconnects fréquents)
    )

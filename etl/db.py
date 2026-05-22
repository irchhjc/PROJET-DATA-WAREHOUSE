"""Fabriques de connexions SQLAlchemy pour la source et le DWH."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import SETTINGS


def _build_url(database: str) -> str:
    return (
        f"postgresql+psycopg2://{SETTINGS.pg_user}:{SETTINGS.pg_password}"
        f"@{SETTINGS.pg_host}:{SETTINGS.pg_port}/{database}"
    )


def get_source_engine() -> Engine:
    """Engine sur la base source (sakila / pagila)."""
    return create_engine(_build_url(SETTINGS.pg_db_source), future=True, pool_pre_ping=True)


def get_dwh_engine() -> Engine:
    """Engine sur la base data warehouse (sakila_dwh)."""
    return create_engine(_build_url(SETTINGS.pg_db_dwh), future=True, pool_pre_ping=True)

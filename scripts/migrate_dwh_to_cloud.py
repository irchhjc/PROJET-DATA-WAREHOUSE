"""Migrer le contenu du DWH local (sakila_dwh) vers une base PostgreSQL cloud.

Cas d'usage :
    1. Tu as exécuté l'ETL en local, sakila_dwh est rempli.
    2. Tu as provisionné une base Postgres sur Render (ou Neon/Supabase).
    3. Tu lances ce script pour copier le schéma + les données vers le cloud.
    4. L'app Dash hébergée (lisant DATABASE_URL_DWH) voit les données.

Usage :
    # 1. Récupérer la "External Database URL" depuis Render → service sakila-dwh
    set CLOUD_DWH_URL=postgresql://sakila_app:xxx@dpg-xxx.frankfurt-postgres.render.com/sakila_dwh
    python -m scripts.migrate_dwh_to_cloud
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DDL_FILE = PROJECT_ROOT / "sql" / "01_create_dwh_schema.sql"
INDEX_FILE = PROJECT_ROOT / "sql" / "02_indexes.sql"


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def _local_url() -> str:
    host = os.getenv("PG_HOST", "localhost")
    port = os.getenv("PG_PORT", "5432")
    user = os.getenv("PG_USER", "postgres")
    pwd = os.getenv("PG_PASSWORD")
    db = os.getenv("PG_DB_DWH", "sakila_dwh")
    if not pwd:
        raise SystemExit("PG_PASSWORD doit être défini dans .env pour la base locale.")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"


def _cloud_url() -> str:
    url = os.getenv("CLOUD_DWH_URL") or os.getenv("DATABASE_URL_DWH")
    if not url:
        raise SystemExit(
            "Aucune URL cloud trouvée. Définir CLOUD_DWH_URL avec la 'External Database URL' "
            "fournie par Render (ou Neon/Supabase)."
        )
    # Render fournit souvent ?sslmode=require dans l'URL — on garde tel quel
    return _normalize_url(url)


TABLES_ORDER = [
    # Dimensions d'abord (la fact a des FK)
    "dim_date",
    "dim_film",
    "dim_store",
    "dim_customer",
    "fact_rental",
]


def main() -> None:
    src_url = _local_url()
    dst_url = _cloud_url()

    _log("--- Source (local DWH) ---")
    _log(f"  {src_url.split('@')[1]}")
    _log("--- Destination (cloud) ---")
    _log(f"  {dst_url.split('@')[1]}")

    src = create_engine(src_url, future=True)
    dst = create_engine(dst_url, future=True, pool_pre_ping=True)

    # 1. Appliquer le DDL sur la destination (idempotent : DROP + CREATE)
    _log("Application du DDL sur la base cloud…")
    ddl = DDL_FILE.read_text(encoding="utf-8")
    with dst.begin() as conn:
        conn.exec_driver_sql(ddl)
    _log("  → schéma `dwh` recréé sur le cloud")

    # 2. Copier les tables dans l'ordre des dépendances
    for table in TABLES_ORDER:
        t0 = time.time()
        df = pd.read_sql(f"SELECT * FROM dwh.{table}", src)
        if df.empty:
            _log(f"  ⚠ {table}: vide en source — ignoré")
            continue

        # Les colonnes générées (manager_full_name, full_name) ne doivent PAS être insérées
        df = df.drop(columns=[c for c in ("manager_full_name", "full_name") if c in df.columns])

        with dst.begin() as conn:
            conn.exec_driver_sql(f"TRUNCATE TABLE dwh.{table} RESTART IDENTITY CASCADE;")
            df.to_sql(table, conn, schema="dwh", if_exists="append",
                      index=False, method="multi", chunksize=1000)
        _log(f"  → {table}: {len(df):,} lignes en {time.time() - t0:.1f}s")

    # 3. Resynchroniser les séquences (puisqu'on a inséré avec les clés existantes)
    _log("Resynchronisation des séquences BIGSERIAL…")
    seq_resets = [
        "SELECT setval(pg_get_serial_sequence('dwh.dim_film',     'film_key'),     COALESCE(MAX(film_key),     1)) FROM dwh.dim_film;",
        "SELECT setval(pg_get_serial_sequence('dwh.dim_store',    'store_key'),    COALESCE(MAX(store_key),    1)) FROM dwh.dim_store;",
        "SELECT setval(pg_get_serial_sequence('dwh.dim_customer', 'customer_key'), COALESCE(MAX(customer_key), 1)) FROM dwh.dim_customer;",
    ]
    with dst.begin() as conn:
        for stmt in seq_resets:
            conn.exec_driver_sql(stmt)

    # 4. Indexes + ANALYZE
    _log("Création des index secondaires sur le cloud…")
    sql = INDEX_FILE.read_text(encoding="utf-8")
    with dst.begin() as conn:
        conn.exec_driver_sql(sql)

    # 4. Vérification rapide
    with dst.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM dwh.fact_rental")).scalar()
    _log(f"=== Migration OK — fact_rental contient {n:,} lignes côté cloud ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERREUR : {exc!r}", file=sys.stderr)
        sys.exit(1)

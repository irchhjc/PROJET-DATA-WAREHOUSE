"""Orchestrateur ETL : exécute extract → transform → load en séquence.

Usage :
    python -m etl.run_etl
"""

from __future__ import annotations

import io
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Force stdout/stderr en UTF-8 (Windows cp1252 ne gère pas tous les caractères)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")  # type: ignore[assignment]
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")  # type: ignore[assignment]

from sqlalchemy import text

from .config import SETTINGS
from .db import get_dwh_engine, get_source_engine
from .extract import (
    extract_customers,
    extract_films,
    extract_rentals,
    extract_stores,
)
from .load import (
    load_dim_customer,
    load_dim_film,
    load_dim_store,
    load_fact_rental,
)
from .populate_dim_date import populate as populate_dim_date
from .transform import (
    clean_customers,
    clean_films,
    clean_stores,
    segment_customers,
    transform_rentals,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_FILE = PROJECT_ROOT / "sql" / "01_create_dwh_schema.sql"
INDEX_FILE = PROJECT_ROOT / "sql" / "02_indexes.sql"


def _log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def ensure_schema(dwh_engine) -> None:
    """Exécute le DDL si la table fact_rental n'existe pas."""
    with dwh_engine.connect() as conn:
        exists = conn.execute(
            text(
                "SELECT to_regclass('dwh.fact_rental') IS NOT NULL AS ok"
            )
        ).scalar()

    if not exists:
        _log("Schéma DWH absent → exécution du DDL 01_create_dwh_schema.sql")
        ddl = DDL_FILE.read_text(encoding="utf-8")
        # psycopg2 sait exécuter plusieurs ordres SQL en un seul appel
        with dwh_engine.begin() as conn:
            conn.exec_driver_sql(ddl)
    else:
        _log("Schéma DWH déjà présent.")


def apply_indexes(dwh_engine) -> None:
    _log("Création des index secondaires…")
    sql = INDEX_FILE.read_text(encoding="utf-8")
    with dwh_engine.begin() as conn:
        conn.exec_driver_sql(sql)


def run() -> None:
    t0 = time.time()
    _log("=== ETL Sakila 360 — démarrage ===")
    _log(f"Source : {SETTINGS.pg_db_source}   |   Cible : {SETTINGS.pg_db_dwh}")

    src = get_source_engine()
    dwh = get_dwh_engine()

    ensure_schema(dwh)

    # ----------------- Extraction -----------------
    _log("Extraction des films…")
    films_raw = extract_films(src)
    _log(f"  → {len(films_raw):,} films")

    _log("Extraction des magasins…")
    stores_raw = extract_stores(src)
    _log(f"  → {len(stores_raw):,} magasins")

    _log("Extraction des clients…")
    customers_raw = extract_customers(src)
    _log(f"  → {len(customers_raw):,} clients")

    _log("Extraction des locations + paiements…")
    rentals_raw = extract_rentals(src)
    _log(f"  → {len(rentals_raw):,} locations")

    # ----------------- Transformation -----------------
    _log("Transformation : films, magasins, locations…")
    films = clean_films(films_raw)
    stores = clean_stores(stores_raw)
    rentals_clean = rentals_raw.dropna(subset=["rental_date", "customer_id", "film_id", "store_id"]).copy()
    rentals_tx, observation_date = transform_rentals(
        rentals_clean,
        late_fee_per_day=SETTINGS.late_fee_per_day,
        grace_days=SETTINGS.grace_days,
    )
    _log(f"  → date d'observation utilisée pour les locations ouvertes : {observation_date.date()}")

    _log("Segmentation client par CA total…")
    customers_clean = clean_customers(customers_raw)
    customers_seg = segment_customers(customers_clean, rentals_tx)
    seg_counts = customers_seg["segment"].value_counts().to_dict()
    _log(f"  → segments : {seg_counts}")

    # ----------------- dim_date -----------------
    rental_min = rentals_tx["rental_date"].min().date()
    rental_max_eff = max(
        rentals_tx["rental_date"].max().date(),
        rentals_tx["return_date"].dropna().max().date() if rentals_tx["return_date"].notna().any() else rentals_tx["rental_date"].max().date(),
    )
    # Petite marge : 30 jours avant/après pour fenêtres glissantes
    start = (rental_min - timedelta(days=30)).replace(day=1)
    end = rental_max_eff + timedelta(days=60)
    _log(f"Population dim_date du {start} au {end}…")
    n_dates = populate_dim_date(dwh, start, end)
    _log(f"  → {n_dates:,} lignes de calendrier insérées")

    # ----------------- Load dimensions -----------------
    _log("Chargement dim_film…")
    film_map = load_dim_film(dwh, films)
    _log(f"  → {len(film_map):,} films chargés")

    _log("Chargement dim_store…")
    store_map = load_dim_store(dwh, stores)
    _log(f"  → {len(store_map):,} magasins chargés")

    _log("Chargement dim_customer (SCD2 initialisation)…")
    customer_map = load_dim_customer(dwh, customers_seg)
    _log(f"  → {len(customer_map):,} clients chargés")

    # ----------------- Load fact -----------------
    _log("Chargement fact_rental…")
    n_fact = load_fact_rental(
        dwh, rentals_tx, film_map, customer_map, store_map,
        batch_size=SETTINGS.batch_size,
    )
    _log(f"  → {n_fact:,} faits chargés")

    # ----------------- Index + ANALYZE -----------------
    apply_indexes(dwh)

    elapsed = time.time() - t0
    _log(f"=== ETL terminé en {elapsed:.1f} s ===")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # pragma: no cover - point d'entrée
        print(f"ERREUR ETL : {exc!r}", file=sys.stderr)
        raise

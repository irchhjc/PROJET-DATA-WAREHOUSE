"""Chargement des DataFrames transformés dans le DWH.

Stratégie :
  - les dimensions sont TRUNCATE puis rechargées (full refresh),
  - les clés de substitution générées côté Postgres sont relues
    pour résoudre les FK de la fact.
  - SCD type 2 sur dim_customer : à la première charge, toutes les
    versions sont marquées is_current = TRUE / valid_to = 9999-12-31.
    La fonction `apply_scd2_customer_change` (voir doc) montre comment
    appliquer un changement d'adresse en mode incrémental.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------
def _truncate(conn, table: str) -> None:
    conn.exec_driver_sql(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")


# -----------------------------------------------------------
# Dimensions
# -----------------------------------------------------------
def load_dim_film(engine: Engine, films: pd.DataFrame) -> pd.DataFrame:
    """Charge dim_film et renvoie le mapping film_id → film_key."""
    cols = [
        "film_id", "title", "description", "category", "rating",
        "release_year", "language", "length_minutes",
        "rental_rate", "replacement_cost", "rental_duration_tgt",
    ]
    with engine.begin() as conn:
        _truncate(conn, "dwh.dim_film")
        films[cols].to_sql(
            "dim_film", conn, schema="dwh",
            if_exists="append", index=False,
            method="multi", chunksize=1000,
        )
        mapping = pd.read_sql("SELECT film_key, film_id FROM dwh.dim_film", conn)
    return mapping


def load_dim_store(engine: Engine, stores: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "store_id", "manager_first_name", "manager_last_name",
        "address", "district", "city", "country",
    ]
    with engine.begin() as conn:
        _truncate(conn, "dwh.dim_store")
        stores[cols].to_sql(
            "dim_store", conn, schema="dwh",
            if_exists="append", index=False,
            method="multi", chunksize=1000,
        )
        mapping = pd.read_sql("SELECT store_key, store_id FROM dwh.dim_store", conn)
    return mapping


def load_dim_customer(engine: Engine, customers: pd.DataFrame) -> pd.DataFrame:
    """Charge dim_customer (initialisation SCD2 : 1 version courante par client)."""
    cols = [
        "customer_id", "first_name", "last_name", "email",
        "address", "district", "city", "country",
        "segment", "is_active", "valid_from",
    ]
    df = customers[cols].copy()
    # Toutes les versions sont courantes à l'init
    df["valid_to"] = pd.Timestamp("9999-12-31").date()
    df["is_current"] = True

    with engine.begin() as conn:
        _truncate(conn, "dwh.dim_customer")
        df.to_sql(
            "dim_customer", conn, schema="dwh",
            if_exists="append", index=False,
            method="multi", chunksize=1000,
        )
        mapping = pd.read_sql(
            "SELECT customer_key, customer_id FROM dwh.dim_customer WHERE is_current",
            conn,
        )
    return mapping


# -----------------------------------------------------------
# Fact
# -----------------------------------------------------------
def load_fact_rental(
    engine: Engine,
    rentals: pd.DataFrame,
    film_map: pd.DataFrame,
    customer_map: pd.DataFrame,
    store_map: pd.DataFrame,
    *,
    batch_size: int = 5000,
) -> int:
    """Joint les mappings de clés et charge la table fact_rental."""
    fr = rentals.merge(film_map,     on="film_id",     how="inner") \
                .merge(customer_map, on="customer_id", how="inner") \
                .merge(store_map,    on="store_id",    how="inner")

    cols = [
        "rental_id", "date_key", "return_date_key",
        "film_key", "customer_key", "store_key",
        "rental_duration", "expected_duration",
        "days_late", "is_late", "is_returned",
        "amount", "late_fee", "count_rental",
    ]

    with engine.begin() as conn:
        _truncate(conn, "dwh.fact_rental")
        fr[cols].to_sql(
            "fact_rental", conn, schema="dwh",
            if_exists="append", index=False,
            method="multi", chunksize=batch_size,
        )
    return len(fr)


# -----------------------------------------------------------
# Démonstration SCD type 2 (non utilisé en full refresh)
# -----------------------------------------------------------
def apply_scd2_customer_change(
    engine: Engine,
    customer_id: int,
    new_attributes: dict,
    change_date,
) -> None:
    """Applique un changement SCD2 sur un client (changement d'adresse).

    Étapes :
      1. Clôt la version courante : valid_to = change_date - 1, is_current = FALSE.
      2. Insère une nouvelle version courante avec les nouveaux attributs.
    """
    sql_close = text("""
        UPDATE dwh.dim_customer
        SET    valid_to = :change_date - INTERVAL '1 day',
               is_current = FALSE
        WHERE  customer_id = :customer_id
          AND  is_current = TRUE;
    """)
    sql_insert = text("""
        INSERT INTO dwh.dim_customer
            (customer_id, first_name, last_name, email,
             address, district, city, country,
             segment, is_active, valid_from, valid_to, is_current)
        SELECT
            :customer_id, :first_name, :last_name, :email,
            :address, :district, :city, :country,
            :segment, :is_active, :change_date, DATE '9999-12-31', TRUE;
    """)
    with engine.begin() as conn:
        conn.execute(sql_close, {"customer_id": customer_id, "change_date": change_date})
        conn.execute(sql_insert, {"customer_id": customer_id, "change_date": change_date, **new_attributes})

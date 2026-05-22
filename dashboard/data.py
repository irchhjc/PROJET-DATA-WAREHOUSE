"""Couche d'accès aux données du DWH pour le dashboard.

Toutes les requêtes vont contre la base `sakila_dwh` / schéma `dwh`.
Un cache LRU léger limite le coût des requêtes répétées avec les
mêmes filtres ; il peut être vidé en appelant `clear_cache()`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Sequence

import pandas as pd
from sqlalchemy import text

from etl.db import get_dwh_engine

_ENGINE = get_dwh_engine()


def clear_cache() -> None:
    get_filter_options.cache_clear()


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------
def _in_clause(values: Optional[Sequence], cast: str = "") -> tuple[str, dict]:
    """Construit un fragment SQL `IN (:p0, :p1, ...)` paramétré."""
    if not values:
        return "", {}
    params = {f"p{i}": v for i, v in enumerate(values)}
    placeholders = ", ".join(f":{k}{cast}" for k in params)
    return f" IN ({placeholders}) ", params


def _filter_clauses(filters: dict) -> tuple[str, dict]:
    """Convertit le dict des filtres globaux en clause SQL + params."""
    where: list[str] = []
    params: dict = {}

    if filters.get("year"):
        where.append("d.year = :year")
        params["year"] = int(filters["year"])

    months = filters.get("months")
    if months:
        clause, p = _in_clause(months)
        if clause:
            where.append("d.month" + clause)
            params.update(p)

    countries = filters.get("countries")
    if countries:
        clause, p = _in_clause(countries)
        if clause:
            where.append("c.country" + clause)
            params.update({k: v for k, v in p.items()})

    stores = filters.get("stores")
    if stores:
        clause, p = _in_clause(stores)
        if clause:
            where.append("s.store_id" + clause)
            params.update({k: v for k, v in p.items()})

    categories = filters.get("categories")
    if categories:
        clause, p = _in_clause(categories)
        if clause:
            where.append("f.category" + clause)
            params.update({k: v for k, v in p.items()})

    ratings = filters.get("ratings")
    if ratings:
        clause, p = _in_clause(ratings)
        if clause:
            where.append("f.rating" + clause)
            params.update({k: v for k, v in p.items()})

    return (" AND ".join(where), params) if where else ("", {})


def _base_join() -> str:
    return """
        FROM       dwh.fact_rental fr
        INNER JOIN dwh.dim_date    d ON d.date_key     = fr.date_key
        INNER JOIN dwh.dim_film    f ON f.film_key     = fr.film_key
        INNER JOIN dwh.dim_customer c ON c.customer_key = fr.customer_key
        INNER JOIN dwh.dim_store   s ON s.store_key    = fr.store_key
    """


def _query(sql: str, params: Optional[dict] = None) -> pd.DataFrame:
    with _ENGINE.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


# -----------------------------------------------------------
# Options pour les filtres
# -----------------------------------------------------------
@lru_cache(maxsize=1)
def get_filter_options() -> dict:
    """Retourne les listes de valeurs distinctes pour alimenter les dropdowns."""
    years = _query(
        "SELECT DISTINCT d.year "
        "FROM dwh.dim_date d INNER JOIN dwh.fact_rental fr ON fr.date_key = d.date_key "
        "ORDER BY 1"
    )["year"].astype(int).tolist()
    countries = _query("SELECT DISTINCT country FROM dwh.dim_customer ORDER BY 1")["country"].tolist()
    stores = _query(
        "SELECT store_id, "
        "       store_id::text || ' — ' || COALESCE(city,'?') || ', ' || COALESCE(country,'?') AS label "
        "FROM dwh.dim_store ORDER BY store_id"
    )
    categories = _query("SELECT DISTINCT category FROM dwh.dim_film ORDER BY 1")["category"].tolist()
    ratings = _query("SELECT DISTINCT rating FROM dwh.dim_film WHERE rating IS NOT NULL ORDER BY 1")[
        "rating"
    ].tolist()
    months = [
        (1, "Janvier"), (2, "Février"), (3, "Mars"), (4, "Avril"),
        (5, "Mai"), (6, "Juin"), (7, "Juillet"), (8, "Août"),
        (9, "Septembre"), (10, "Octobre"), (11, "Novembre"), (12, "Décembre"),
    ]
    return {
        "years": years,
        "countries": countries,
        "stores": stores.to_dict("records"),
        "categories": categories,
        "ratings": ratings,
        "months": months,
    }


# -----------------------------------------------------------
# KPI globaux
# -----------------------------------------------------------
def get_kpis(filters: dict) -> dict:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    sql = f"""
        SELECT
            COALESCE(SUM(fr.amount), 0)                                   AS revenue,
            COUNT(*)                                                      AS nb_rentals,
            COALESCE(AVG(fr.amount), 0)                                   AS avg_basket,
            COALESCE(SUM(fr.late_fee), 0)                                 AS late_fees,
            COALESCE(SUM(CASE WHEN fr.is_late THEN 1 ELSE 0 END), 0)::float
                / NULLIF(COUNT(*), 0)                                     AS late_rate,
            COUNT(DISTINCT c.customer_id)                                 AS active_customers
        {_base_join()}
        {where_sql};
    """
    df = _query(sql, params)
    if df.empty:
        return {
            "revenue": 0, "nb_rentals": 0, "avg_basket": 0,
            "late_fees": 0, "late_rate": 0, "active_customers": 0,
        }
    return df.iloc[0].to_dict()


# -----------------------------------------------------------
# Séries pour graphiques
# -----------------------------------------------------------
def monthly_revenue(filters: dict) -> pd.DataFrame:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    sql = f"""
        SELECT  d.year, d.month, d.month_name,
                SUM(fr.amount) AS revenue,
                COUNT(*)       AS nb_rentals
        {_base_join()}
        {where_sql}
        GROUP BY d.year, d.month, d.month_name
        ORDER BY d.year, d.month;
    """
    return _query(sql, params)


def monthly_revenue_by_category(filters: dict) -> pd.DataFrame:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    sql = f"""
        SELECT  d.year, d.month, d.month_name, f.category,
                SUM(fr.amount) AS revenue
        {_base_join()}
        {where_sql}
        GROUP BY d.year, d.month, d.month_name, f.category
        ORDER BY d.year, d.month, revenue DESC;
    """
    return _query(sql, params)


def revenue_by_category(filters: dict) -> pd.DataFrame:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    sql = f"""
        SELECT  f.category,
                SUM(fr.amount) AS revenue,
                COUNT(*)       AS nb_rentals,
                ROUND(AVG(fr.amount)::numeric, 2) AS avg_basket
        {_base_join()}
        {where_sql}
        GROUP BY f.category
        ORDER BY revenue DESC;
    """
    return _query(sql, params)


def top_films_revenue(filters: dict, limit: int = 15) -> pd.DataFrame:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    params = {**params, "lim": limit}
    sql = f"""
        SELECT  f.film_id, f.title, f.category,
                SUM(fr.amount) AS revenue,
                COUNT(*)       AS nb_rentals
        {_base_join()}
        {where_sql}
        GROUP BY f.film_id, f.title, f.category
        ORDER BY revenue DESC
        LIMIT :lim;
    """
    return _query(sql, params)


def top_films_late(filters: dict, limit: int = 15) -> pd.DataFrame:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    params = {**params, "lim": limit}
    sql = f"""
        SELECT  f.film_id, f.title, f.category,
                SUM(fr.late_fee) AS late_fees,
                SUM(fr.days_late)::numeric(10,2) AS total_days_late,
                COUNT(*) FILTER (WHERE fr.is_late) AS nb_late
        {_base_join()}
        {where_sql}
        GROUP BY f.film_id, f.title, f.category
        HAVING SUM(fr.late_fee) > 0
        ORDER BY late_fees DESC
        LIMIT :lim;
    """
    return _query(sql, params)


def revenue_by_country(filters: dict) -> pd.DataFrame:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    sql = f"""
        SELECT  c.country,
                SUM(fr.amount)                  AS revenue,
                COUNT(*)                        AS nb_rentals,
                COUNT(DISTINCT c.customer_id)   AS nb_customers,
                COALESCE(AVG(fr.amount), 0)     AS avg_basket
        {_base_join()}
        {where_sql}
        GROUP BY c.country
        ORDER BY revenue DESC;
    """
    return _query(sql, params)


def country_category_heatmap(filters: dict, top_countries: int = 15) -> pd.DataFrame:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    params = {**params, "lim": top_countries}
    sql = f"""
        WITH top_c AS (
            SELECT c.country, SUM(fr.amount) AS rev
            {_base_join()}
            {where_sql}
            GROUP BY c.country
            ORDER BY rev DESC
            LIMIT :lim
        )
        SELECT  c.country, f.category,
                SUM(fr.amount) AS revenue,
                COUNT(*)       AS nb_rentals
        {_base_join()}
        INNER JOIN top_c tc ON tc.country = c.country
        {where_sql}
        GROUP BY c.country, f.category
        ORDER BY c.country, revenue DESC;
    """
    return _query(sql, params)


def store_performance(filters: dict) -> pd.DataFrame:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    sql = f"""
        SELECT  s.store_id, s.city, s.country, s.manager_full_name,
                SUM(fr.amount)                AS revenue,
                COUNT(*)                      AS nb_rentals,
                SUM(fr.late_fee)              AS late_fees,
                COUNT(DISTINCT c.customer_id) AS nb_customers,
                AVG(fr.amount)                AS avg_basket
        {_base_join()}
        {where_sql}
        GROUP BY s.store_id, s.city, s.country, s.manager_full_name
        ORDER BY revenue DESC;
    """
    return _query(sql, params)


def filtered_data(filters: dict, limit: int = 5000) -> pd.DataFrame:
    where, params = _filter_clauses(filters)
    where_sql = (" WHERE " + where) if where else ""
    params = {**params, "lim": limit}
    sql = f"""
        SELECT  fr.rental_id,
                d.full_date          AS rental_date,
                f.title              AS film,
                f.category,
                f.rating,
                c.full_name          AS customer,
                c.country            AS customer_country,
                c.segment            AS customer_segment,
                s.store_id           AS store_id,
                s.city               AS store_city,
                s.country            AS store_country,
                fr.rental_duration,
                fr.expected_duration,
                fr.days_late,
                fr.is_late,
                fr.amount,
                fr.late_fee
        {_base_join()}
        {where_sql}
        ORDER BY d.full_date DESC
        LIMIT :lim;
    """
    return _query(sql, params)

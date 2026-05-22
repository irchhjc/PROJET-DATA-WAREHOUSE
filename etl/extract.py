"""Extraction des données depuis la base source Sakila / Pagila.

Chaque fonction renvoie un DataFrame pandas prêt à être transformé.
Les requêtes dénormalisent à la source pour éviter les jointures
côté DWH au moment du chargement.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine

# -----------------------------------------------------------
# Films + catégories + langue
# -----------------------------------------------------------
FILM_SQL = """
-- Dans Pagila plusieurs films possèdent plusieurs catégories : on garde
-- la première par ordre alphabétique pour garantir l'unicité (DISTINCT ON).
SELECT DISTINCT ON (f.film_id)
    f.film_id,
    f.title,
    f.description,
    INITCAP(c.name)                       AS category,
    f.rating::text                        AS rating,
    f.release_year::int                   AS release_year,
    INITCAP(l.name)                       AS language,
    f.length                              AS length_minutes,
    f.rental_rate                         AS rental_rate,
    f.replacement_cost                    AS replacement_cost,
    f.rental_duration                     AS rental_duration_tgt
FROM       film f
INNER JOIN film_category fc ON fc.film_id     = f.film_id
INNER JOIN category      c  ON c.category_id  = fc.category_id
INNER JOIN language      l  ON l.language_id  = f.language_id
ORDER BY   f.film_id, c.name;
"""


def extract_films(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(FILM_SQL, engine)


# -----------------------------------------------------------
# Clients + adresse + ville + pays
# -----------------------------------------------------------
CUSTOMER_SQL = """
SELECT
    cu.customer_id,
    cu.first_name,
    cu.last_name,
    cu.email,
    a.address,
    a.district,
    ci.city,
    co.country,
    cu.active::int        AS active_flag,
    cu.create_date::date  AS create_date
FROM       customer cu
INNER JOIN address  a  ON a.address_id = cu.address_id
INNER JOIN city     ci ON ci.city_id   = a.city_id
INNER JOIN country  co ON co.country_id = ci.country_id
ORDER BY   cu.customer_id;
"""


def extract_customers(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(CUSTOMER_SQL, engine)


# -----------------------------------------------------------
# Magasins + adresse + manager
# -----------------------------------------------------------
STORE_SQL = """
SELECT
    s.store_id,
    st.first_name        AS manager_first_name,
    st.last_name         AS manager_last_name,
    a.address,
    a.district,
    ci.city,
    co.country
FROM       store   s
INNER JOIN staff   st ON st.staff_id = s.manager_staff_id
INNER JOIN address a  ON a.address_id = s.address_id
INNER JOIN city    ci ON ci.city_id   = a.city_id
INNER JOIN country co ON co.country_id = ci.country_id
ORDER BY   s.store_id;
"""


def extract_stores(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(STORE_SQL, engine)


# -----------------------------------------------------------
# Locations + paiements agrégés
# -----------------------------------------------------------
RENTAL_SQL = """
SELECT
    r.rental_id,
    r.rental_date,
    r.return_date,
    r.customer_id,
    i.film_id,
    i.store_id,
    f.rental_duration   AS expected_duration,
    COALESCE(p.total_paid, 0) AS amount
FROM       rental r
INNER JOIN inventory i  ON i.inventory_id = r.inventory_id
INNER JOIN film      f  ON f.film_id = i.film_id
LEFT  JOIN (
    SELECT rental_id, SUM(amount) AS total_paid
    FROM   payment
    GROUP BY rental_id
) p ON p.rental_id = r.rental_id;
"""


def extract_rentals(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(RENTAL_SQL, engine, parse_dates=["rental_date", "return_date"])

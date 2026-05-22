-- =================================================================
-- Sakila 360 - Requêtes OLAP obligatoires
-- Base : sakila_dwh, schéma : dwh
--
-- Les requêtes sont écrites pour PostgreSQL.
-- Remplacer la variable :target_year (psql) ou la constante 2022
-- pour adapter à l'année métier souhaitée.
-- =================================================================

SET search_path TO dwh, public;

-- ============================================================
-- Q1.  Évolution mensuelle du chiffre d'affaires par catégorie
--      pour une année cible (originalement 2005, ici 2022 selon
--      l'année réellement présente dans le dump Pagila).
-- ============================================================
SELECT
    d.year,
    d.month,
    d.month_name,
    f.category,
    SUM(fr.amount)            AS revenue,
    COUNT(*)                  AS nb_rentals,
    ROUND(AVG(fr.amount), 2)  AS avg_basket
FROM       dwh.fact_rental fr
INNER JOIN dwh.dim_date    d  ON d.date_key = fr.date_key
INNER JOIN dwh.dim_film    f  ON f.film_key = fr.film_key
WHERE      d.year = 2022                              -- :target_year
GROUP BY   d.year, d.month, d.month_name, f.category
ORDER BY   d.year, d.month, revenue DESC;


-- ============================================================
-- Q2.  Top 5 des films générant le plus de pénalités de retard
--      par magasin.
-- ============================================================
WITH film_store_late AS (
    SELECT
        s.store_id,
        s.city           AS store_city,
        s.country        AS store_country,
        f.film_id,
        f.title,
        f.category,
        SUM(fr.late_fee) AS total_late_fee,
        SUM(fr.days_late)::NUMERIC(10,2) AS total_days_late,
        COUNT(*) FILTER (WHERE fr.is_late) AS nb_late_rentals,
        COUNT(*) AS nb_rentals
    FROM       dwh.fact_rental fr
    INNER JOIN dwh.dim_film  f ON f.film_key  = fr.film_key
    INNER JOIN dwh.dim_store s ON s.store_key = fr.store_key
    WHERE      fr.late_fee > 0
    GROUP BY   s.store_id, s.city, s.country, f.film_id, f.title, f.category
),
ranked AS (
    SELECT *,
           RANK() OVER (PARTITION BY store_id ORDER BY total_late_fee DESC) AS rk
    FROM   film_store_late
)
SELECT *
FROM   ranked
WHERE  rk <= 5
ORDER BY store_id, rk;


-- ============================================================
-- Q3.  Pour chaque pays du client, identifier la catégorie de
--      film LA PLUS louée (en nombre de locations).
-- ============================================================
WITH country_cat AS (
    SELECT
        c.country,
        f.category,
        COUNT(*)        AS nb_rentals,
        SUM(fr.amount)  AS revenue
    FROM       dwh.fact_rental fr
    INNER JOIN dwh.dim_customer c ON c.customer_key = fr.customer_key
    INNER JOIN dwh.dim_film     f ON f.film_key     = fr.film_key
    GROUP BY   c.country, f.category
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY country ORDER BY nb_rentals DESC) AS rk
    FROM   country_cat
)
SELECT  country,
        category   AS top_category,
        nb_rentals,
        revenue
FROM    ranked
WHERE   rk = 1
ORDER BY nb_rentals DESC;


-- ============================================================
-- Q4.  Pourcentage de films de l'inventaire jamais loués durant
--      le dernier trimestre de la période observée.
--      (Trimestre déterminé dynamiquement à partir des données.)
-- ============================================================
WITH period AS (
    SELECT  EXTRACT(YEAR    FROM MAX(full_date))::INT AS y_max,
            EXTRACT(QUARTER FROM MAX(full_date))::INT AS q_max
    FROM    dwh.dim_date dd
    INNER JOIN dwh.fact_rental fr ON fr.date_key = dd.date_key
),
films_rented AS (
    SELECT DISTINCT fr.film_key
    FROM       dwh.fact_rental fr
    INNER JOIN dwh.dim_date    d ON d.date_key = fr.date_key
    CROSS JOIN period p
    WHERE      d.year = p.y_max
      AND      d.quarter = p.q_max
)
SELECT
    (SELECT y_max FROM period)                        AS year,
    (SELECT q_max FROM period)                        AS quarter,
    COUNT(DISTINCT f.film_key)                        AS total_films,
    COUNT(DISTINCT f.film_key) FILTER (WHERE fr.film_key IS NULL) AS never_rented,
    ROUND(100.0 * COUNT(DISTINCT f.film_key) FILTER (WHERE fr.film_key IS NULL)
                / NULLIF(COUNT(DISTINCT f.film_key), 0), 2)       AS pct_never_rented
FROM        dwh.dim_film  f
LEFT JOIN   films_rented  fr ON fr.film_key = f.film_key;


-- ============================================================
-- Q5.  Revenus mondiaux par pays et classement dynamique
--      des catégories (top 3) à l'intérieur de chaque pays.
-- ============================================================
WITH country_rev AS (
    SELECT
        c.country,
        SUM(fr.amount)              AS revenue,
        COUNT(*)                    AS nb_rentals,
        COUNT(DISTINCT c.customer_id) AS nb_customers
    FROM       dwh.fact_rental fr
    INNER JOIN dwh.dim_customer c ON c.customer_key = fr.customer_key
    GROUP BY   c.country
),
country_cat_rev AS (
    SELECT
        c.country,
        f.category,
        SUM(fr.amount)              AS cat_revenue,
        COUNT(*)                    AS cat_rentals,
        RANK() OVER (PARTITION BY c.country ORDER BY SUM(fr.amount) DESC) AS cat_rank
    FROM       dwh.fact_rental fr
    INNER JOIN dwh.dim_customer c ON c.customer_key = fr.customer_key
    INNER JOIN dwh.dim_film     f ON f.film_key     = fr.film_key
    GROUP BY   c.country, f.category
)
SELECT
    cr.country,
    cr.revenue,
    cr.nb_rentals,
    cr.nb_customers,
    ccr.category,
    ccr.cat_revenue,
    ccr.cat_rentals,
    ccr.cat_rank
FROM       country_rev    cr
INNER JOIN country_cat_rev ccr ON ccr.country = cr.country
WHERE      ccr.cat_rank <= 3
ORDER BY   cr.revenue DESC, cr.country, ccr.cat_rank;

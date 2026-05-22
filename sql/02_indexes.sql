-- =================================================================
-- Sakila 360 - Index secondaires pour le DWH
-- À exécuter APRÈS l'ETL (les index ralentiraient le chargement)
-- =================================================================

SET search_path TO dwh, public;

-- ---------- Fact ----------
CREATE INDEX IF NOT EXISTS ix_fact_rental_date_key       ON dwh.fact_rental(date_key);
CREATE INDEX IF NOT EXISTS ix_fact_rental_return_dt_key  ON dwh.fact_rental(return_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_rental_film_key       ON dwh.fact_rental(film_key);
CREATE INDEX IF NOT EXISTS ix_fact_rental_customer_key   ON dwh.fact_rental(customer_key);
CREATE INDEX IF NOT EXISTS ix_fact_rental_store_key      ON dwh.fact_rental(store_key);
CREATE INDEX IF NOT EXISTS ix_fact_rental_is_late        ON dwh.fact_rental(is_late) WHERE is_late = TRUE;

-- ---------- Dimensions ----------
CREATE INDEX IF NOT EXISTS ix_dim_date_year_month    ON dwh.dim_date(year, month);
CREATE INDEX IF NOT EXISTS ix_dim_film_category      ON dwh.dim_film(category);
CREATE INDEX IF NOT EXISTS ix_dim_film_rating        ON dwh.dim_film(rating);
CREATE INDEX IF NOT EXISTS ix_dim_customer_country   ON dwh.dim_customer(country);
CREATE INDEX IF NOT EXISTS ix_dim_customer_segment   ON dwh.dim_customer(segment);
CREATE INDEX IF NOT EXISTS ix_dim_store_country      ON dwh.dim_store(country);

ANALYZE dwh.dim_date;
ANALYZE dwh.dim_film;
ANALYZE dwh.dim_customer;
ANALYZE dwh.dim_store;
ANALYZE dwh.fact_rental;

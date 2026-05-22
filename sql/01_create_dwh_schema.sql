-- =================================================================
-- Sakila 360 - Data Warehouse - Schéma en étoile
-- Cible : base sakila_dwh, schéma "dwh"
--
-- Convention :
--   - clés primaires des dimensions = clés de substitution (surrogate)
--     identifiées par le suffixe "_key" (BIGSERIAL ou INT généré)
--   - clés métier (business key) conservées avec le suffixe "_id"
--   - dim_date utilise une clé naturelle au format YYYYMMDD (INTEGER)
--   - SCD type 2 sur dim_customer pour suivre les changements d'adresse
-- =================================================================

CREATE SCHEMA IF NOT EXISTS dwh;
SET search_path TO dwh, public;

-- -----------------------------------------------------------------
-- Suppression idempotente
-- -----------------------------------------------------------------
DROP TABLE IF EXISTS dwh.fact_rental   CASCADE;
DROP TABLE IF EXISTS dwh.dim_film      CASCADE;
DROP TABLE IF EXISTS dwh.dim_customer  CASCADE;
DROP TABLE IF EXISTS dwh.dim_store     CASCADE;
DROP TABLE IF EXISTS dwh.dim_date      CASCADE;

-- -----------------------------------------------------------------
-- Dimension Date
-- Clé : date_key = AAAAMMJJ (INT)
-- -----------------------------------------------------------------
CREATE TABLE dwh.dim_date (
    date_key        INTEGER     PRIMARY KEY,
    full_date       DATE        NOT NULL UNIQUE,
    day             SMALLINT    NOT NULL,
    month           SMALLINT    NOT NULL,
    month_name      VARCHAR(20) NOT NULL,
    quarter         SMALLINT    NOT NULL,
    year            SMALLINT    NOT NULL,
    day_of_week     SMALLINT    NOT NULL,           -- 1 = lundi ... 7 = dimanche
    day_name        VARCHAR(20) NOT NULL,
    week_of_year    SMALLINT    NOT NULL,
    is_weekend      BOOLEAN     NOT NULL DEFAULT FALSE,
    is_holiday      BOOLEAN     NOT NULL DEFAULT FALSE,
    holiday_label   VARCHAR(80)
);

COMMENT ON TABLE  dwh.dim_date IS 'Dimension calendrier ; granularité journalière.';
COMMENT ON COLUMN dwh.dim_date.date_key IS 'Clé de substitution AAAAMMJJ (ex: 20220515).';

-- -----------------------------------------------------------------
-- Dimension Film
-- -----------------------------------------------------------------
CREATE TABLE dwh.dim_film (
    film_key            BIGSERIAL    PRIMARY KEY,
    film_id             INTEGER      NOT NULL UNIQUE,        -- business key
    title               VARCHAR(255) NOT NULL,
    description         TEXT,
    category            VARCHAR(50)  NOT NULL,
    rating              VARCHAR(10),                          -- G, PG, PG-13, R, NC-17
    release_year        SMALLINT,
    language            VARCHAR(40),
    length_minutes      SMALLINT,
    rental_rate         NUMERIC(6,2),
    replacement_cost    NUMERIC(7,2),
    rental_duration_tgt SMALLINT,                              -- durée prévue contractuelle
    inserted_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dwh.dim_film IS 'Dimension Film conforme avec catégorie dénormalisée.';

-- -----------------------------------------------------------------
-- Dimension Store (magasin)
-- -----------------------------------------------------------------
CREATE TABLE dwh.dim_store (
    store_key            BIGSERIAL    PRIMARY KEY,
    store_id             INTEGER      NOT NULL UNIQUE,
    manager_first_name   VARCHAR(60),
    manager_last_name    VARCHAR(60),
    manager_full_name    VARCHAR(120) GENERATED ALWAYS AS (
                            COALESCE(manager_first_name,'') || ' ' || COALESCE(manager_last_name,'')
                         ) STORED,
    address              VARCHAR(255),
    district             VARCHAR(80),
    city                 VARCHAR(80),
    country              VARCHAR(80),
    inserted_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dwh.dim_store IS 'Dimension magasin (adresse + manager dénormalisés).';

-- -----------------------------------------------------------------
-- Dimension Customer (SCD type 2 sur l'adresse)
-- -----------------------------------------------------------------
CREATE TABLE dwh.dim_customer (
    customer_key   BIGSERIAL    PRIMARY KEY,
    customer_id    INTEGER      NOT NULL,                  -- business key (non unique : SCD2)
    first_name     VARCHAR(60)  NOT NULL,
    last_name      VARCHAR(60)  NOT NULL,
    full_name      VARCHAR(120) GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED,
    email          VARCHAR(120),
    address        VARCHAR(255),
    district       VARCHAR(80),
    city           VARCHAR(80),
    country        VARCHAR(80),
    segment        VARCHAR(20)  NOT NULL DEFAULT 'Standard', -- VIP / Premium / Standard / Inactif
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    -- Colonnes SCD type 2
    valid_from     DATE         NOT NULL DEFAULT CURRENT_DATE,
    valid_to       DATE         NOT NULL DEFAULT DATE '9999-12-31',
    is_current     BOOLEAN      NOT NULL DEFAULT TRUE,
    inserted_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX ux_dim_customer_current
    ON dwh.dim_customer (customer_id)
    WHERE is_current = TRUE;

COMMENT ON TABLE  dwh.dim_customer IS 'Dimension client en SCD type 2 (versions historisées sur l''adresse).';
COMMENT ON COLUMN dwh.dim_customer.valid_from IS 'Début de validité de la version.';
COMMENT ON COLUMN dwh.dim_customer.valid_to   IS 'Fin de validité (9999-12-31 si version active).';
COMMENT ON COLUMN dwh.dim_customer.is_current IS 'TRUE pour la dernière version de chaque customer_id.';

-- -----------------------------------------------------------------
-- Table de faits Rental
-- -----------------------------------------------------------------
CREATE TABLE dwh.fact_rental (
    rental_id          INTEGER     PRIMARY KEY,           -- business key
    date_key           INTEGER     NOT NULL REFERENCES dwh.dim_date(date_key),
    return_date_key    INTEGER              REFERENCES dwh.dim_date(date_key),
    film_key           BIGINT      NOT NULL REFERENCES dwh.dim_film(film_key),
    customer_key       BIGINT      NOT NULL REFERENCES dwh.dim_customer(customer_key),
    store_key          BIGINT      NOT NULL REFERENCES dwh.dim_store(store_key),

    -- Mesures
    rental_duration    NUMERIC(8,2),                       -- durée réelle en jours
    expected_duration  SMALLINT,                            -- durée contractuelle attendue
    days_late          NUMERIC(8,2) NOT NULL DEFAULT 0,    -- jours de retard
    is_late            BOOLEAN      NOT NULL DEFAULT FALSE,
    is_returned        BOOLEAN      NOT NULL DEFAULT FALSE,
    amount             NUMERIC(8,2) NOT NULL DEFAULT 0,    -- somme des paiements liés
    late_fee           NUMERIC(8,2) NOT NULL DEFAULT 0,    -- pénalité calculée
    count_rental       SMALLINT     NOT NULL DEFAULT 1
);

COMMENT ON TABLE  dwh.fact_rental IS 'Table de faits transactionnelle : 1 ligne = 1 location.';
COMMENT ON COLUMN dwh.fact_rental.rental_duration   IS 'Différence return_date - rental_date en jours.';
COMMENT ON COLUMN dwh.fact_rental.expected_duration IS 'Durée prévue au contrat (film.rental_duration).';
COMMENT ON COLUMN dwh.fact_rental.late_fee          IS 'Pénalité calculée : MAX(0, days_late) * tarif/jour.';
COMMENT ON COLUMN dwh.fact_rental.amount            IS 'Somme des paiements rattachés à la location.';

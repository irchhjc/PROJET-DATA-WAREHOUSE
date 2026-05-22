-- =================================================================
-- Sakila 360 - Nettoyage complet du DWH
-- ATTENTION : supprime toutes les tables du schéma dwh.
-- =================================================================

DROP TABLE IF EXISTS dwh.fact_rental   CASCADE;
DROP TABLE IF EXISTS dwh.dim_film      CASCADE;
DROP TABLE IF EXISTS dwh.dim_customer  CASCADE;
DROP TABLE IF EXISTS dwh.dim_store     CASCADE;
DROP TABLE IF EXISTS dwh.dim_date      CASCADE;
DROP SCHEMA IF EXISTS dwh CASCADE;

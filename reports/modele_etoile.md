# Modèle dimensionnel — Schéma en étoile Sakila 360

> Cible : base PostgreSQL `sakila_dwh`, schéma `dwh`.
> Tous les fichiers DDL sont versionnés dans `sql/`.

## 1. Diagramme synthétique

```
                              ┌─────────────────────┐
                              │      dim_date        │
                              │  date_key (PK INT)   │
                              │  full_date           │
                              │  day / month / quarter│
                              │  year / day_of_week  │
                              │  is_weekend / is_holiday │
                              └──────────┬──────────┘
                                         │
                                         │ date_key / return_date_key
                                         ▼
   ┌─────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────┐
   │      dim_film       │       │       fact_rental        │       │     dim_customer    │
   │  film_key (PK)      │◀──────│  rental_id (PK BIZ)      │──────▶│  customer_key (PK)  │
   │  film_id (BIZ)      │       │  date_key / return_dt    │       │  customer_id (BIZ)  │
   │  title, category    │       │  film_key                │       │  full_name, country │
   │  rating, language   │       │  customer_key            │       │  segment            │
   │  release_year       │       │  store_key               │       │  SCD 2 (valid_from, │
   │  rental_duration_tgt│       │  rental_duration         │       │   valid_to,         │
   │  rental_rate        │       │  expected_duration       │       │   is_current)       │
   │  replacement_cost   │       │  days_late, is_late      │       └──────────┬──────────┘
   └─────────────────────┘       │  is_returned             │                  │
                                 │  amount                  │                  │
                                 │  late_fee                │                  │
                                 │  count_rental            │                  │
                                 └──────────┬──────────────┘                  │
                                            │                                  │
                                            ▼                                  │
                                ┌─────────────────────┐                       │
                                │      dim_store      │                       │
                                │  store_key (PK)     │                       │
                                │  store_id (BIZ)     │                       │
                                │  manager_full_name  │                       │
                                │  city, country      │                       │
                                └─────────────────────┘                       │
                                                                              │
                                  (relation via customer_key, dim_customer)──┘
```

## 2. Description des tables

### dim_date
- **Granularité** : un jour.
- **Clé** : `date_key` au format `AAAAMMJJ` (`INTEGER`). Plus lisible et plus rapide que des dates en clés.
- **Attributs utiles** pour l'OLAP : `month`, `quarter`, `year`, `day_of_week` (1 = lundi), `is_weekend`, `is_holiday` (jours fériés US, configurable).

### dim_film
- **Granularité** : un film.
- **PK** : `film_key` (BIGSERIAL surrogate) ; **business key** : `film_id`.
- Catégorie dénormalisée. Pour les films ayant plusieurs catégories dans Pagila, on retient la première par ordre alphabétique (cf. `extract.py`).

### dim_customer (SCD type 2)
- **Granularité** : une version de client.
- **PK** : `customer_key` ; le couple (`customer_id`, `is_current`) est unique pour le client courant.
- Colonnes SCD2 : `valid_from`, `valid_to` (`9999-12-31` si version active), `is_current` (BOOLEAN).
- À l'initialisation de l'ETL, une seule version est créée par client. La fonction `apply_scd2_customer_change` dans `etl/load.py` montre comment clôturer la version courante et créer une nouvelle version à chaque changement d'adresse (mode incrémental).

### dim_store
- **Granularité** : un magasin (`store_id` business key).
- Adresse, ville, pays et nom du manager sont dénormalisés.

### fact_rental
- **Granularité** : une location.
- **Clés étrangères** : `date_key` (date de location), `return_date_key` (peut être NULL si non retourné), `film_key`, `customer_key`, `store_key`.
- **Mesures** :
  - `rental_duration` (numérique en jours) — durée réelle calculée par l'ETL.
  - `expected_duration` (smallint) — durée prévue copiée depuis `film.rental_duration`.
  - `days_late`, `is_late`, `is_returned`.
  - `amount` — somme des paiements liés (depuis la table `payment`).
  - `late_fee` — pénalité = `max(0, days_late) * ETL_LATE_FEE_PER_DAY`.
  - `count_rental` — toujours 1 (utile pour les agrégats COUNT(*)).

## 3. Stratégie SCD pour les changements d'adresse client

La table `dim_customer` est conçue en **SCD type 2** pour conserver l'historique des adresses :

| Étape | Action SQL |
|------|-----------|
| 1. Détecter un changement | Comparer les colonnes d'adresse de la source avec la version courante (`is_current = TRUE`) du DWH. |
| 2. Clôturer la version actuelle | `UPDATE dwh.dim_customer SET valid_to = change_date - 1, is_current = FALSE WHERE customer_id = ? AND is_current = TRUE` |
| 3. Insérer la nouvelle version | `INSERT INTO dwh.dim_customer (...) VALUES (..., valid_from=change_date, valid_to='9999-12-31', is_current=TRUE)` |
| 4. Maintenir la fact | Les nouvelles lignes de `fact_rental` pointent automatiquement vers la version courante via le mapping (`customer_id` → `customer_key`) reconstruit à chaque charge. |

L'implémentation est dans [etl/load.py](../etl/load.py) (`apply_scd2_customer_change`).

## 4. Choix techniques notables

- **PostgreSQL natif** pour la source ET le DWH — port officiel Pagila du dump Sakila.
- **Schéma `dwh` dédié** dans la base `sakila_dwh` (séparation logique).
- **Index secondaires** créés *après* le chargement pour ne pas pénaliser l'ETL ; voir `sql/02_indexes.sql`.
- **Pénalités configurables** via `.env` (`ETL_LATE_FEE_PER_DAY`, `ETL_GRACE_DAYS`).
- **Locations non retournées** : durée calculée jusqu'à une « date d'observation » = lendemain de la dernière location enregistrée.

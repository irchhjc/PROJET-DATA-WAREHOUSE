# Sakila 360 — Analyse de la Performance des Locations

> **Rapport projet — Business Intelligence / Data Warehouse**
> Auteur : projet académique sur la base de démonstration Sakila / Pagila
> Stack : PostgreSQL · Python (pandas, SQLAlchemy) · Dash · Plotly · ReportLab

---

## 1. Contexte business

Sakila est une chaîne fictive de vidéo-clubs internationaux dont la base relationnelle est largement utilisée pour des cas d'études BI. Le management cherche à dépasser le reporting opérationnel (vues sur les tables OLTP) pour obtenir une **vision décisionnelle consolidée** : rentabilité par film, performance des magasins, comportement des clients, tendances temporelles et géographiques.

Le port officiel PostgreSQL de Sakila — **Pagila** — embarque aujourd'hui 1 000 films, 599 clients, **500 magasins** (vs 2 dans le Sakila historique), 16 044 locations et 16 049 paiements sur la période **février — août 2022**.

## 2. Objectif du projet

Construire une **solution BI de bout en bout** :
1. Concevoir un **schéma en étoile** dédié au reporting.
2. Bâtir un **pipeline ETL** Python qui alimente cette cible depuis la base OLTP.
3. Implémenter les **5 analyses OLAP** demandées.
4. Livrer un **tableau de bord interactif Dash** (multi-pages, KPI, exports).
5. Produire un **rapport** et un **guide d'exécution**.

## 3. Architecture du Data Warehouse

```
   Source OLTP                  ETL Python              DWH cible
   ─────────────              ──────────────         ─────────────────
   PostgreSQL                  extract                PostgreSQL
   base sakila                 transform              base sakila_dwh
   (Pagila)                    load                   schéma dwh (étoile)
                                                       │
                                                       ▼
                                                  Dash + Plotly
                                              KPI · graphes · exports
```

- **Source** : base `sakila` (port Pagila officiel chargé dans PostgreSQL 18).
- **DWH** : base `sakila_dwh`, schéma `dwh`, 4 dimensions + 1 fact.
- **ETL** : Python 3.11 (pandas + SQLAlchemy), orchestré par `etl/run_etl.py`.
- **Dashboard** : Dash 2.17 + Dash Bootstrap Components, exposé sur `127.0.0.1:8050`.
- **Exports** : ReportLab (PDF), XlsxWriter (Excel multi-feuilles), CSV UTF-8.

## 4. Schéma en étoile

Voir le détail complet et le diagramme dans [`modele_etoile.md`](modele_etoile.md).

| Table | Type | Lignes après ETL | Clé primaire |
|------|------|------------------|--------------|
| `dwh.dim_date`      | dimension calendrier | 305  | `date_key` (AAAAMMJJ) |
| `dwh.dim_film`      | dimension film       | 1 000 | `film_key` (BIGSERIAL) |
| `dwh.dim_customer`  | dimension client (SCD2) | 599 | `customer_key` |
| `dwh.dim_store`     | dimension magasin    | 500   | `store_key` |
| `dwh.fact_rental`   | table de faits       | 16 044 | `rental_id` |

### Choix structurants

- **SCD type 2** sur `dim_customer` pour suivre les changements d'adresse ; à l'initialisation, une seule version par client (`is_current = TRUE`, `valid_to = 9999-12-31`).
- **Clé naturelle YYYYMMDD** pour `dim_date` — plus rapide et lisible que des clés synthétiques.
- **Mesures dérivées** stockées dans la fact (`days_late`, `is_late`, `is_returned`, `late_fee`) pour éviter les calculs en runtime.
- **Catégorie dénormalisée** dans `dim_film` — Pagila comporte des films multi-catégorisés ; on retient la première catégorie alphabétique pour garantir l'unicité.

## 5. Étapes ETL

Le pipeline `etl/run_etl.py` se déroule en six phases (durée < 15 s sur ce jeu de données) :

1. **Bootstrap du schéma** : exécution conditionnelle de `sql/01_create_dwh_schema.sql` si la fact n'existe pas.
2. **Extract** : requêtes SQL dénormalisées contre Sakila pour récupérer films, clients, magasins, locations + paiements agrégés.
3. **Transform** :
   - normalisation textuelle (`title`, `email`, casses) ;
   - calcul de la **durée réelle** = `return_date - rental_date` ;
   - gestion des `return_date NULL` via une **date d'observation** = `max(rental_date) + 1 jour` ;
   - calcul des **pénalités** = `max(0, durée_réelle − durée_prévue − grace_days) × tarif/jour` ;
   - **segmentation client** par CA : VIP (≥ Q75), Premium (≥ Q50), Standard, Inactif.
4. **Populate dim_date** : génération calendrier + indicateur jours fériés (US par défaut).
5. **Load dimensions** (TRUNCATE + INSERT) puis récupération des clés de substitution.
6. **Load fact** : jointures sur les mappings de clés, INSERT en batches de 5 000.
7. **ANALYZE + index** : `sql/02_indexes.sql` après chargement.

### Métriques créées

- `rental_duration` : durée réelle en jours.
- `expected_duration` : durée contractuelle du film.
- `days_late`, `is_late`, `is_returned`.
- `amount` : somme des paiements liés à la location.
- `late_fee` : pénalité calculée.
- `count_rental` : toujours 1 (compteur agrégeable).
- `segment` (dim_customer) : VIP / Premium / Standard / Inactif.

## 6. Résultats analytiques (cinq analyses OLAP)

### Q1 — Évolution mensuelle du chiffre d'affaires par catégorie (2022)

L'activité décolle en **juillet 2022** (CA mensuel = 28 511 $) avant de redescendre en août (23 938 $). Les catégories **Action**, **Animation** et **Classics** dominent le mix, ce qui se confirme dans les heatmaps pays × catégorie.

| Mois | CA total |
|------|---------|
| Février 2022 | 514 $ |
| Mai 2022 | 4 823 $ |
| Juin 2022 | 9 630 $ |
| Juillet 2022 | 28 511 $ |
| Août 2022 | 23 938 $ |
| **Total période** | **67 416 $** |

### Q2 — Top 5 films générant le plus de pénalités par magasin

Pour les magasins examinés, on observe que ce sont des films **Drama**, **Animation** et **Classics** qui creusent les pénalités. Exemples (extrait) :

| Magasin | Film | Catégorie | Pénalités $ | Locations en retard |
|---------|------|-----------|------------|---------------------|
| 1 | Creatures Shakespeare | Drama | 394.78 | 6 |
| 1 | Intentions Empire | Animation | 392.95 | 7 |
| 1 | Dances None | Animation | 392.94 | 9 |
| 1 | Gunfight Moon | Classics | 384.97 | 8 |
| 1 | Half Outfield | Action | 381.83 | 8 |
| 2 | Doors President | Animation | 388.14 | 10 |
| 2 | Ridgemont Submarine | Documentary | 236.85 | 16 |

> Lecture business : les films qui génèrent le plus de retards ne sont pas forcément les plus rentables. Le management peut considérer une politique de **caution renforcée** pour ces titres ou un **réajustement de la durée contractuelle**.

### Q3 — Pays du client × catégorie de film la plus louée

Les marchés majeurs (Inde, Chine, Japon, États-Unis, Mexique) plébiscitent **Action** ou **Animation**. Les marchés émergents (Russie, Nigeria) montrent une préférence pour la catégorie **Children**.

| Pays | Catégorie #1 | Locations |
|------|---------------|-----------|
| India | Action | 233 |
| China | Animation | 201 |
| Japan | Action | 134 |
| United States | Animation | 133 |
| Mexico | Action | 128 |
| Brazil | Action | 104 |
| Russian Federation | Children | 100 |
| Philippines | Animation | 82 |
| Turkey | Animation | 61 |
| Argentina | Animation | 58 |
| Nigeria | Children | 56 |

### Q4 — Pourcentage de films jamais loués durant le dernier trimestre

Sur le **T3 2022** (dernier trimestre observé), **42 films sur 1 000 (4,20 %)** n'ont jamais été loués. Le stock dormant est donc faible mais identifiable : il représente une opportunité de **promotion ciblée** ou de **destockage**.

### Q5 — Revenus mondiaux et classement dynamique des catégories

Top 10 pays par chiffre d'affaires :

| Pays | CA $ | Locations | Clients actifs |
|------|------|-----------|----------------|
| India | 6 628 | 1 572 | 60 |
| China | 5 799 | 1 426 | 53 |
| United States | 4 120 | 968 | 36 |
| Japan | 3 471 | 825 | 31 |
| Mexico | 3 307 | 796 | 30 |
| Brazil | 3 200 | 748 | 28 |
| Russian Federation | 3 046 | 713 | 28 |
| Philippines | 2 381 | 568 | 20 |
| Turkey | 1 662 | 388 | 15 |
| Nigeria | 1 511 | 352 | 13 |

Le classement dynamique des catégories est rendu dans le dashboard via la heatmap **Pays × Catégorie** et la table magasins.

## 7. Interprétations business

- **Saisonnalité forte** : 78 % du CA se concentre sur juillet–août. Les campagnes marketing doivent donc être préparées dès le printemps pour capter ce pic.
- **Mix produit cohérent** : Action, Animation et Classics représentent la majorité des locations dans la plupart des géographies.
- **Pénalités > Chiffre d'affaires** : `late_fee` total (53 986 $) dépasse le CA total (67 416 $). Cela indique que la durée contractuelle (`rental_duration_tgt`) est probablement trop courte au vu des usages réels, ou que la politique de pénalité serait trop sévère. Le management doit **revoir la durée par défaut** ou clarifier les rappels clients.
- **Segments clients équilibrés** : 25 % VIP, 25 % Premium, 50 % Standard. Aucun client inactif sur la période (chaque client a au moins une location).
- **Stock dormant** réduit (4,2 %), ce qui confirme une rotation efficace du catalogue.

## 8. Recommandations marketing & gestion de stock

1. **Optimisation de la durée contractuelle** par catégorie : passer à 5–7 jours pour Drama et Animation pour réduire les pénalités tout en maintenant la rotation.
2. **Campagne ciblée sur les VIP** : les 150 clients VIP représentent une part disproportionnée du CA — proposer un **abonnement annuel** ou des avant-premières.
3. **Adapter le catalogue géographiquement** : booster l'inventaire Animation en Chine et Action en Inde.
4. **Activer le stock dormant** : les 42 films jamais loués au T3 sont candidats à des **offres groupées** ou à du destockage promotionnel.
5. **Industrialiser la heatmap Pays × Catégorie** comme outil de pilotage des achats.
6. **Surveiller le taux de retard mensuel** comme KPI de fidélité opérationnelle (actuellement 51,7 %).

## 9. Limites du projet

- Le dump Pagila utilisé concerne **2022** ; les requêtes paramétrées sur 2005 (énoncé d'origine) ont été adaptées pour viser l'année effective des données.
- La **SCD type 2** est en place mais pas testée sur un flux incrémental : à la première charge, une seule version par client est créée. Le mécanisme `apply_scd2_customer_change` (`etl/load.py`) est prêt pour les charges futures.
- Pas de **table d'inventaire** dans le DWH — l'analyse Q4 utilise `dim_film` ; pour une vision « copies physiques », il faudrait ajouter une dimension `dim_inventory`.
- Tarif de pénalité **uniforme** (1 $/jour) — un tarif différencié par catégorie ou par film serait plus réaliste.
- **Jours fériés** calculés sur le calendrier US uniquement ; à étendre par pays pour des analyses internationales fines.

## 10. Pistes d'amélioration

- Ajouter une **dimension `dim_promotion`** pour mesurer l'efficacité des campagnes.
- Construire une **vue agrégée matérialisée** (`MATERIALIZED VIEW`) pour les KPI globaux et la rafraîchir post-ETL.
- Mettre en place une **planification (Airflow / cron)** pour exécuter l'ETL en mode incrémental.
- Étendre les **exports** : ajouter un export PNG vectoriel des graphiques (déjà supporté techniquement via Plotly + Kaleido).
- **Tests automatisés** : ajouter des tests pytest pour la couche `data.py` et les transformations.
- **Sécurité** : déplacer les secrets dans un gestionnaire (`vault`, `aws secrets manager`) et utiliser un utilisateur Postgres en lecture seule pour le dashboard.

---

## Annexe — Reproduire les résultats

```bash
# 1. Cloner et installer
git clone https://github.com/irchhjc/PROJET-DATA-WAREHOUSE.git
cd PROJET-DATA-WAREHOUSE
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # ajuster les credentials

# 2. Charger Pagila dans la base `sakila` (PostgreSQL)
#    (script ou commandes psql + dump officiel)

# 3. ETL
python -m etl.run_etl

# 4. Lancer le dashboard
python -m dashboard.app
# → http://127.0.0.1:8050
```

Les requêtes OLAP complètes sont dans [`sql/olap_queries.sql`](../sql/olap_queries.sql).

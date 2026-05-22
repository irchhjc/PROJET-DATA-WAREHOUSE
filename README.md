# Sakila 360 — Analyse de la Performance des Locations

Solution complète de Business Intelligence sur la base **Sakila / Pagila** :
modélisation décisionnelle en étoile, ETL Python vers un Data Warehouse PostgreSQL, et tableau de bord interactif **Python Dash**.

> Objectif : permettre au management de Sakila d'analyser la rentabilité des films, le comportement des clients, les performances par magasin et les tendances de location, et de produire des rapports exportables (PDF, Excel, CSV, PNG).

---

## Sommaire

1. [Architecture](#architecture)
2. [Arborescence du projet](#arborescence-du-projet)
3. [Installation rapide](#installation-rapide)
4. [Exécution du pipeline](#exécution-du-pipeline)
5. [Lancer le tableau de bord](#lancer-le-tableau-de-bord)
6. [Analyses OLAP fournies](#analyses-olap-fournies)
7. [Livrables](#livrables)

---

## Architecture

```
   ┌───────────────────┐      ETL Python       ┌────────────────────┐      Dash App
   │  PostgreSQL       │   (extract / clean    │  PostgreSQL        │   (Plotly + Bootstrap)
   │  base : sakila    │   transform / load)   │  base : sakila_dwh │   ┌─────────────────┐
   │  (schéma OLTP)    │  ─────────────────▶   │  (schéma étoile)   │ ▶ │ KPI / Charts /  │
   └───────────────────┘                       └────────────────────┘   │ Exports PDF/XLSX│
                                                                        └─────────────────┘
```

- **OLTP source** : base `sakila` (port PostgreSQL de Sakila = Pagila officiel).
- **DWH cible** : base `sakila_dwh`, schéma `dwh` en étoile, SCD type 2 sur l'adresse client.
- **ETL** : Python (pandas + SQLAlchemy), idempotent, paramétrable.
- **Dashboard** : Dash multi-pages + Plotly + Dash Bootstrap Components.
- **Exports** : ReportLab (PDF), XlsxWriter (Excel multi-feuilles), Kaleido (PNG).

## Arborescence du projet

```
PROJET-DATA-WAREHOUSE/
├── README.md
├── GUIDE_EXECUTION.md
├── requirements.txt
├── .env.example
├── sql/                      # scripts DDL et requêtes OLAP
│   ├── 01_create_dwh_schema.sql
│   ├── 02_indexes.sql
│   ├── 03_drop_dwh_objects.sql
│   └── olap_queries.sql
├── etl/                      # pipeline d'alimentation du DWH
│   ├── config.py
│   ├── db.py
│   ├── populate_dim_date.py
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   └── run_etl.py
├── dashboard/                # application Dash
│   ├── app.py
│   ├── data.py
│   ├── components/
│   ├── pages/
│   ├── callbacks/
│   └── utils/
├── reports/                  # rapport projet + modèle étoile
│   ├── RAPPORT_PROJET.md
│   └── modele_etoile.md
└── assets/                   # CSS personnalisé Dash
    └── custom.css
```

## Installation rapide

```bash
# 1. Cloner le projet
git clone https://github.com/irchhjc/PROJET-DATA-WAREHOUSE.git
cd PROJET-DATA-WAREHOUSE

# 2. Créer un environnement virtuel
python -m venv .venv
.venv\Scripts\activate          # PowerShell
# ou : source .venv/bin/activate  (Linux/Mac)

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer la connexion
copy .env.example .env          # puis éditer .env
```

## Exécution du pipeline

```bash
# Créer les bases si nécessaire (psql ou PgAdmin) :
#   CREATE DATABASE sakila ENCODING 'UTF8' TEMPLATE template0;
#   CREATE DATABASE sakila_dwh ENCODING 'UTF8' TEMPLATE template0;
# Et charger les dumps Pagila officiels dans la base sakila.

# 1. Créer le schéma étoile dans sakila_dwh
psql -h localhost -U postgres -d sakila_dwh -f sql/01_create_dwh_schema.sql

# 2. Lancer l'ETL complet
python -m etl.run_etl

# 3. (optionnel) Indexes après chargement
psql -h localhost -U postgres -d sakila_dwh -f sql/02_indexes.sql
```

## Lancer le tableau de bord

```bash
python -m dashboard.app
# Ouvrir http://127.0.0.1:8050
```

## Analyses OLAP fournies

1. **Évolution mensuelle du chiffre d'affaires par catégorie** sur une année cible.
2. **Top 5 des films générant le plus de pénalités** par magasin.
3. **Relation pays du client × catégorie la plus louée**.
4. **% de films de l'inventaire jamais loués** durant le dernier trimestre de la période.
5. **Revenus mondiaux par pays + classement dynamique des catégories**.

Les requêtes sont consultables dans [sql/olap_queries.sql](sql/olap_queries.sql).

## Déploiement en ligne (Render)

L'app est déployable d'un clic sur **Render** via le fichier [`render.yaml`](render.yaml) (Blueprint). Procédure complète : **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)**.

> Netlify ne convient pas à Dash (Netlify ne sert que du statique ou des fonctions serverless ; Dash est un serveur Flask qui doit tourner en continu). Render, Railway et Fly.io sont les alternatives standard. Ici Render est privilégié pour son Blueprint déclaratif et sa Postgres managée incluse.

Résumé express :
1. Pousser ce repo sur GitHub.
2. Sur https://dashboard.render.com → **New +** → **Blueprint** → sélectionner le repo.
3. Render provisionne la base Postgres et le service web.
4. Lancer `python -m scripts.migrate_dwh_to_cloud` localement avec `CLOUD_DWH_URL` pour copier le DWH.
5. L'URL publique est affichée dans Render.

## Livrables

- Scripts SQL (DDL + OLAP) — `sql/`
- Pipeline ETL Python — `etl/`
- Application Dash interactive — `dashboard/`
- Migration cloud — `scripts/migrate_dwh_to_cloud.py`
- Configuration Render — `render.yaml`, `Procfile`, `runtime.txt`
- Rapport projet complet — `reports/RAPPORT_PROJET.md`
- Guide d'exécution local — `GUIDE_EXECUTION.md`
- Guide de déploiement — `DEPLOY_RENDER.md`
- Exports PDF / Excel / CSV / PNG générés par l'app

---

**Auteur** : projet académique BI/Data Warehouse — base de démonstration Sakila/Pagila.

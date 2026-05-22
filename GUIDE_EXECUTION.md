# Guide d'exécution — Sakila 360

Ce guide reprend pas à pas l'installation et l'exécution du projet sur **Windows 10/11** (PowerShell) ou **Linux/Mac**.

---

## 1. Prérequis logiciels

| Outil | Version utilisée | Vérification |
|------|------------------|--------------|
| PostgreSQL | 14 ou plus récent (testé sur 18.3) | `psql --version` |
| Python | 3.11 (3.10 / 3.12 fonctionnent aussi) | `python --version` |
| Git | n'importe quelle version récente | `git --version` |
| Une base **Sakila / Pagila** chargée | dump officiel Pagila | `psql -d sakila -c "SELECT COUNT(*) FROM film"` |

> Si vous n'avez pas Pagila, téléchargez les deux scripts officiels depuis [github.com/devrimgunduz/pagila](https://github.com/devrimgunduz/pagila) :
> ```bash
> createdb -U postgres sakila
> psql -U postgres -d sakila -f pagila-schema.sql
> psql -U postgres -d sakila -f pagila-data.sql
> ```

## 2. Cloner le projet

```bash
git clone https://github.com/irchhjc/PROJET-DATA-WAREHOUSE.git
cd PROJET-DATA-WAREHOUSE
```

## 3. Créer l'environnement Python

### PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Bash (Linux/Mac/Git Bash)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Configurer la connexion Postgres

Copier le modèle puis adapter :

```powershell
Copy-Item .env.example .env
# éditer .env (Notepad / VS Code)
```

Variables minimales (les valeurs ci-dessous sont les défauts) :

```env
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=<votre_mot_de_passe>
PG_DB_SOURCE=sakila
PG_DB_DWH=sakila_dwh
ETL_LATE_FEE_PER_DAY=1.00
ETL_GRACE_DAYS=0
DASH_HOST=127.0.0.1
DASH_PORT=8050
DASH_DEBUG=True
```

## 5. Créer la base cible et le schéma DWH

```bash
psql -h localhost -U postgres -c "CREATE DATABASE sakila_dwh ENCODING 'UTF8' TEMPLATE template0;"
psql -h localhost -U postgres -d sakila_dwh -f sql/01_create_dwh_schema.sql
```

> Si vous préférez tout déléguer au script ETL, sautez cette étape : `run_etl.py` crée automatiquement le schéma s'il est absent.

## 6. Lancer l'ETL

```bash
# Important sur Windows : forcer UTF-8 en sortie console
$env:PYTHONIOENCODING="utf-8"     # PowerShell
# ou : export PYTHONIOENCODING=utf-8    (bash)

python -m etl.run_etl
```

Sortie attendue (ordre de grandeur) :

```
[12:32:41] === ETL Sakila 360 — démarrage ===
[12:32:41] Extraction des films… → 1 000 films
[12:32:41] Extraction des magasins… → 500 magasins
[12:32:41] Extraction des clients… → 599 clients
[12:32:42] Extraction des locations + paiements… → 16 044 locations
[12:32:42] Transformation : films, magasins, locations…
[12:32:42] Segmentation client par CA total… → {'Standard': 298, 'Premium': 151, 'VIP': 150}
[12:32:42] Population dim_date du 2022-01-01 au 2022-11-01… → 305 lignes
[12:32:43] Chargement dim_film… → 1 000 films chargés
[12:32:43] Chargement dim_store… → 500 magasins chargés
[12:32:43] Chargement dim_customer (SCD2 init)… → 599 clients
[12:32:51] Chargement fact_rental… → 16 044 faits
[12:32:51] Création des index secondaires…
[12:32:51] === ETL terminé en 10.3 s ===
```

## 7. Vérifier le DWH (optionnel)

```bash
psql -h localhost -U postgres -d sakila_dwh -c "
SELECT 'fact_rental'    AS t, COUNT(*) FROM dwh.fact_rental
UNION ALL SELECT 'dim_film',     COUNT(*) FROM dwh.dim_film
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dwh.dim_customer
UNION ALL SELECT 'dim_store',    COUNT(*) FROM dwh.dim_store
UNION ALL SELECT 'dim_date',     COUNT(*) FROM dwh.dim_date;"
```

Pour exécuter les analyses OLAP livrées :

```bash
psql -h localhost -U postgres -d sakila_dwh -f sql/olap_queries.sql
```

## 8. Lancer le tableau de bord Dash

```bash
python -m dashboard.app
```

Sortie attendue :

```
Dash is running on http://127.0.0.1:8050/
 * Serving Flask app 'app'
 * Debug mode: on
```

Ouvrir le navigateur sur **http://127.0.0.1:8050/**.

### Pages disponibles

| URL | Contenu |
|-----|---------|
| `/`         | Vue d'ensemble : KPI + carte mondiale + mix catégoriel |
| `/revenus`  | Évolution mensuelle par catégorie + heatmap pays × catégorie |
| `/films`    | Top films par CA et par pénalités |
| `/clients`  | Carte clients + segmentation |
| `/magasins` | Comparatif magasins (bar + DataTable) |
| `/donnees`  | Table dynamique des locations filtrées |

### Filtres globaux (panneau supérieur)

Année · Mois · Pays clients · Magasins · Catégorie · Rating.

### Exports

- **Rapport PDF** complet (page de garde + KPI + tableaux).
- **Excel multi-feuilles** : KPI, mensuel, catégories, top films CA, top films retards, pays, magasins, détail.
- **CSV** des locations filtrées (sépar. `;`, UTF-8 avec BOM).

## 9. Arrêter / re-lancer

- `Ctrl + C` dans le terminal arrête Dash.
- Pour rejouer l'ETL : `python -m etl.run_etl` (TRUNCATE + reload).
- Pour repartir d'une base vierge : `psql -d sakila_dwh -f sql/03_drop_dwh_objects.sql` puis relancer l'ETL.

## 10. Dépannage

| Symptôme | Cause probable | Correctif |
|---------|----------------|-----------|
| `UnicodeEncodeError: 'charmap'` au lancement de l'ETL | console Windows en cp1252 | Exécuter `$env:PYTHONIOENCODING="utf-8"` avant `python -m etl.run_etl`. |
| `psycopg2.OperationalError: connection refused` | service Postgres arrêté | Vérifier le service Windows `postgresql-x64-XX` ou `pg_ctl start`. |
| `relation "dwh.fact_rental" does not exist` | DDL non exécuté | Lancer `psql -d sakila_dwh -f sql/01_create_dwh_schema.sql` ou relancer `run_etl.py`. |
| Page Dash blanche avec erreur 500 | Connexion DWH KO | Vérifier `.env`, lancer `python -m etl.run_etl` au moins une fois. |
| Pas de données dans les graphiques | filtres trop restrictifs | Vider les filtres ou choisir l'année qui contient les données (2022 pour Pagila). |

## 11. Désinstallation propre

```bash
deactivate          # quitter l'environnement virtuel
rm -rf .venv        # ou Remove-Item -Recurse -Force .venv
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS sakila_dwh;"
```

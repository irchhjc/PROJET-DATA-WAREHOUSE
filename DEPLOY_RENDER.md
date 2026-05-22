# Déploiement Sakila 360 sur Render

> **Pourquoi Render** : Netlify ne sait pas exécuter une app Dash (Python/Flask en continu). Render est l'équivalent moderne pour ce type d'app — Blueprint déclaratif, support natif Python, base PostgreSQL managée incluse, free tier.
>
> **Coût** : 0 € au démarrage (Free Tier). La base Postgres free expire après 90 jours — il faudra alors la basculer en Starter ($7/mois) ou re-créer.

---

## 1. Prérequis

- Un compte **GitHub** avec ce repo pushé : https://github.com/irchhjc/PROJET-DATA-WAREHOUSE
- Un compte **Render** : https://render.com (gratuit, connexion via GitHub).
- Le DWH local **déjà rempli** (16 044 lignes dans `dwh.fact_rental`) — sinon, jouer `python -m etl.run_etl` d'abord.

## 2. Architecture cible

```
   GitHub  ──── déclenche déploiement ────▶   Render
   ──────                                     ──────
   render.yaml                                 ┌──────────────────────────┐
   dashboard/                                  │ Service web "sakila-360" │
   etl/                                        │   gunicorn + Dash         │
   sql/                                        │   $PORT (https public)    │
                                               └──────────┬───────────────┘
                                                          │ DATABASE_URL_DWH
                                                          ▼
                                               ┌──────────────────────────┐
                                               │ PostgreSQL "sakila-dwh"  │
                                               │   1 Go, free, SSL imposé │
                                               └──────────────────────────┘
                                                          ▲
                          (étape one-shot)                │
   ┌──────────────────┐    pg copy via                    │
   │ Postgres local   │ ─── scripts/migrate_dwh_to_cloud ─┘
   │ sakila_dwh       │
   └──────────────────┘
```

## 3. Procédure pas à pas

### Étape 1 — Créer le Blueprint

1. Aller sur https://dashboard.render.com → **New +** → **Blueprint**.
2. Connecter ton compte GitHub si pas déjà fait, et autoriser l'accès au repo `PROJET-DATA-WAREHOUSE`.
3. Render détecte automatiquement `render.yaml` à la racine et propose :
   - 1 **PostgreSQL Database** : `sakila-dwh` (free, 1 Go, région Frankfurt — modifiable)
   - 1 **Web Service** : `sakila-360` (Python, free)
4. Cliquer **Apply**. La base se provisionne en ~1–2 min, puis le service web se met à build.
5. Le premier build du service web va échouer (DB encore vide) — c'est normal. On l'alimente à l'étape suivante.

### Étape 2 — Récupérer l'URL de la base cloud

1. Dans Render → service `sakila-dwh` → onglet **Info**.
2. Copier la valeur **External Database URL** (format `postgresql://sakila_app:...@dpg-xxxxx.frankfurt-postgres.render.com/sakila_dwh`).
3. **Important** : cette URL contient `sslmode=require` implicite — psql et psycopg2 le gèrent automatiquement.

### Étape 3 — Migrer les données locales vers le cloud

Sur ta machine, dans le dossier du projet :

```powershell
# Activer l'environnement virtuel
.\.venv\Scripts\Activate.ps1

# Coller l'URL Render copiée ci-dessus
$env:CLOUD_DWH_URL = "postgresql://sakila_app:xxxxx@dpg-xxxxx.frankfurt-postgres.render.com/sakila_dwh"

# Lancer la migration (DDL + copie des 5 tables)
python -m scripts.migrate_dwh_to_cloud
```

Sortie attendue (~30s pour 16k lignes) :

```
[14:02:13] Application du DDL sur la base cloud…
[14:02:14]   → schéma `dwh` recréé sur le cloud
[14:02:14]   → dim_date: 305 lignes en 0.3s
[14:02:15]   → dim_film: 1 000 lignes en 0.6s
[14:02:16]   → dim_store: 500 lignes en 0.4s
[14:02:17]   → dim_customer: 599 lignes en 0.5s
[14:02:25]   → fact_rental: 16 044 lignes en 7.8s
[14:02:25] Resynchronisation des séquences BIGSERIAL…
[14:02:26] Création des index secondaires sur le cloud…
[14:02:27] === Migration OK — fact_rental contient 16 044 lignes côté cloud ===
```

### Étape 4 — Relancer le déploiement de l'app

1. Dans Render → service `sakila-360` → **Manual Deploy** → **Deploy latest commit**.
2. Suivre les logs (onglet **Logs**) : `pip install` puis `gunicorn dashboard.app:server`.
3. Quand tu vois `Listening at: http://0.0.0.0:10000`, l'app est en ligne.

### Étape 5 — Accéder au dashboard

L'URL publique apparaît en haut du service : `https://sakila-360.onrender.com` (ou un suffixe équivalent généré par Render).

Premier accès : ~30 s (l'app sortait de veille free tier). Ensuite ça répond instantanément tant qu'il y a du trafic.

## 4. Vérifications post-déploiement

### Côté base Postgres cloud

Depuis ta machine, en utilisant `CLOUD_DWH_URL` :

```powershell
$env:PGPASSWORD = "<le_password_dans_l_URL>"
psql "$env:CLOUD_DWH_URL" -c "SELECT COUNT(*) FROM dwh.fact_rental;"
# Attendu : 16044
```

### Côté app

- Ouvrir l'URL Render publique → la page d'accueil affiche les KPI (~67 416 $ de CA).
- Changer un filtre → la carte mondiale se met à jour (callback ↔ base cloud).
- Bouton **Rapport PDF** → téléchargement immédiat.

## 5. Mise à jour de l'app

Render redéploie **automatiquement à chaque push sur `main`** :

```bash
git add .
git commit -m "feat: improve XYZ"
git push origin main
# → Render reconstruit et redéploie le service web (~3 min)
```

Aucun redéploiement manuel nécessaire sauf changement de variables d'env.

## 6. Limitations du Free Tier Render

| Composant | Limite | Mitigation |
|----------|--------|------------|
| Service web | 512 Mo RAM, sleep après 15 min idle | Premier accès lent (~30 s). Pour éviter : passer en Starter ($7/mois) ou ping cron toutes les 10 min. |
| Postgres | 1 Go, expire 90 jours | Suivre l'alerte email Render, migrer en Starter ($7/mois) ou re-créer. |
| Build | 500 min/mois | Largement suffisant. |
| Bande passante | 100 Go/mois | Largement suffisant. |

## 7. Dépannage

| Symptôme | Cause | Correctif |
|---------|-------|----------|
| `502 Bad Gateway` | App en cours de wake-up | Attendre 30 s, recharger. |
| `relation "dwh.fact_rental" does not exist` dans les logs Render | DDL pas appliqué | Relancer `python -m scripts.migrate_dwh_to_cloud` localement. |
| `psycopg2.OperationalError: SSL connection has been closed unexpectedly` | Idle disconnect | Déjà géré par `pool_pre_ping=True` + `pool_recycle=300` dans `etl/db.py`. Si persiste, redémarrer le service. |
| Build échoue sur `kaleido` | Lib lourde non strictement nécessaire | Retirer `kaleido==0.2.1` de `requirements.txt` (PNG export en option, pas obligatoire pour le dashboard interactif). |
| App lance mais pages vides | `DATABASE_URL_DWH` non liée à la base | Dans le service web → **Environment** → vérifier la variable, sinon supprimer/recréer le Blueprint. |

## 8. Désactiver / nettoyer

- **Suspendre le coût** : Service web → **Settings** → **Suspend**.
- **Supprimer définitivement** : pour chaque service → **Settings** → **Delete** (taper le nom pour confirmer).
- **Tout supprimer d'un coup** : depuis le Blueprint → **Delete Blueprint**.

---

**Liens utiles**

- Render docs Python : https://render.com/docs/deploy-flask
- Render Blueprints (`render.yaml` spec) : https://render.com/docs/blueprint-spec
- Gunicorn Dash : https://dash.plotly.com/deployment

"""Transformations métier appliquées entre l'extract et le load.

- nettoyage textuel,
- calcul de la durée réelle de location et des pénalités,
- segmentation client à partir du chiffre d'affaires,
- gestion des return_date NULL via une date d'observation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd


# -----------------------------------------------------------
# Films
# -----------------------------------------------------------
def clean_films(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["title"] = out["title"].astype(str).str.strip().str.title()
    out["category"] = out["category"].astype(str).str.strip()
    out["rating"] = out["rating"].fillna("Unrated")
    out["language"] = out["language"].astype(str).str.strip()
    out["release_year"] = out["release_year"].astype("Int64")
    return out


# -----------------------------------------------------------
# Magasins
# -----------------------------------------------------------
def clean_stores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("address", "district", "city", "country", "manager_first_name", "manager_last_name"):
        if col in out:
            out[col] = out[col].astype(str).str.strip()
    return out


# -----------------------------------------------------------
# Clients
# -----------------------------------------------------------
def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("first_name", "last_name", "email", "address", "district", "city", "country"):
        out[col] = out[col].astype(str).str.strip()
    out["first_name"] = out["first_name"].str.title()
    out["last_name"] = out["last_name"].str.title()
    out["email"] = out["email"].str.lower()
    out["is_active"] = out["active_flag"].astype(int).astype(bool)
    out["valid_from"] = pd.to_datetime(out["create_date"]).dt.date
    return out


def segment_customers(customers: pd.DataFrame, rentals: pd.DataFrame) -> pd.DataFrame:
    """Ajoute la colonne `segment` en se basant sur le CA total par client.

    Segments :
      - VIP        : > 75ᵉ percentile du CA
      - Premium    : > 50ᵉ percentile
      - Standard   : autres clients ayant au moins une location
      - Inactif    : aucune location
    """
    revenue_per_cust = (
        rentals.groupby("customer_id", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "total_revenue"})
    )

    out = customers.merge(revenue_per_cust, on="customer_id", how="left")
    out["total_revenue"] = out["total_revenue"].fillna(0.0)

    active_rev = out.loc[out["total_revenue"] > 0, "total_revenue"]
    if active_rev.empty:
        out["segment"] = "Inactif"
        return out

    q75 = active_rev.quantile(0.75)
    q50 = active_rev.quantile(0.50)

    def _label(r: float) -> str:
        if r <= 0:
            return "Inactif"
        if r >= q75:
            return "VIP"
        if r >= q50:
            return "Premium"
        return "Standard"

    out["segment"] = out["total_revenue"].apply(_label)
    return out


# -----------------------------------------------------------
# Locations : durée réelle + pénalités
# -----------------------------------------------------------
def transform_rentals(
    rentals: pd.DataFrame,
    *,
    late_fee_per_day: float,
    grace_days: int = 0,
) -> Tuple[pd.DataFrame, datetime]:
    """Calcule durée, retard et pénalité.

    - return_date NULL → considérée comme location ouverte à la date d'observation
      (= max(rental_date) du dataset + 1 jour). Cette date est aussi renvoyée
      pour générer la dim_date sur une fenêtre complète.
    - days_late = max(0, durée_réelle - durée_prévue - grace_days)
    - late_fee  = days_late * late_fee_per_day
    """
    out = rentals.copy()

    # Date d'observation = lendemain de la dernière location enregistrée
    observation_date = (out["rental_date"].max() + pd.Timedelta(days=1)).normalize()

    out["is_returned"] = out["return_date"].notna()
    effective_return = out["return_date"].fillna(observation_date)

    duration = (effective_return - out["rental_date"]).dt.total_seconds() / 86400.0
    out["rental_duration"] = duration.round(2)

    out["expected_duration"] = out["expected_duration"].astype(int)
    days_late = (out["rental_duration"] - out["expected_duration"] - grace_days).clip(lower=0)
    out["days_late"] = days_late.round(2)
    out["is_late"] = out["days_late"] > 0
    out["late_fee"] = (out["days_late"] * late_fee_per_day).round(2)
    out["count_rental"] = 1

    # Clés de date format AAAAMMJJ
    out["date_key"] = out["rental_date"].dt.strftime("%Y%m%d").astype(int)
    out["return_date_key"] = (
        out["return_date"].dt.strftime("%Y%m%d").astype("Int64")  # Int64 pour tolérer NaN
    )

    out["amount"] = out["amount"].astype(float).round(2)
    return out, observation_date.to_pydatetime()

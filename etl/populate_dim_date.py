"""Génération de la dimension date couvrant la période des locations.

La table dim_date est alimentée par produit cartésien : 1 ligne par jour,
clé naturelle YYYYMMDD. Jours fériés détectés via la bibliothèque `holidays`
(par défaut sur les US, pays d'origine Sakila ; configurable).
"""

from __future__ import annotations

from datetime import date, timedelta

import holidays
import pandas as pd
from sqlalchemy.engine import Engine

FRENCH_MONTHS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}
FRENCH_DAYS = {
    0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi",
    4: "Vendredi", 5: "Samedi", 6: "Dimanche",
}


def build_dim_date(start: date, end: date, country_iso: str = "US") -> pd.DataFrame:
    """Construit un DataFrame dim_date entre `start` et `end` (inclus)."""
    if end < start:
        raise ValueError("end doit être >= start")

    holiday_cal = holidays.country_holidays(country_iso, years=range(start.year, end.year + 1))

    rows = []
    current = start
    one_day = timedelta(days=1)
    while current <= end:
        is_hol = current in holiday_cal
        rows.append(
            {
                "date_key": int(current.strftime("%Y%m%d")),
                "full_date": current,
                "day": current.day,
                "month": current.month,
                "month_name": FRENCH_MONTHS[current.month],
                "quarter": (current.month - 1) // 3 + 1,
                "year": current.year,
                # 1 = lundi ... 7 = dimanche pour rester en ISO
                "day_of_week": current.weekday() + 1,
                "day_name": FRENCH_DAYS[current.weekday()],
                "week_of_year": int(current.strftime("%V")),
                "is_weekend": current.weekday() >= 5,
                "is_holiday": is_hol,
                "holiday_label": holiday_cal.get(current) if is_hol else None,
            }
        )
        current += one_day

    return pd.DataFrame(rows)


def populate(engine: Engine, start: date, end: date, country_iso: str = "US") -> int:
    """Insère le DataFrame généré dans dwh.dim_date (table vidée auparavant)."""
    df = build_dim_date(start, end, country_iso=country_iso)
    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE TABLE dwh.dim_date CASCADE;")
        df.to_sql(
            "dim_date",
            con=conn,
            schema="dwh",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=2000,
        )
    return len(df)

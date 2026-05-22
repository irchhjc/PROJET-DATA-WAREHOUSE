"""Génération des exports Excel et CSV à partir des données du DWH."""

from __future__ import annotations

import io

import pandas as pd

from dashboard import data as dwh_data


def build_excel(filters: dict) -> bytes:
    """Construit un classeur Excel multi-feuilles (KPI, temps, films, clients, magasins)."""
    kpis = dwh_data.get_kpis(filters)
    kpi_df = pd.DataFrame(
        [
            ("Chiffre d'affaires",     round(kpis["revenue"], 2)),
            ("Nombre de locations",    int(kpis["nb_rentals"])),
            ("Panier moyen",           round(kpis["avg_basket"], 2)),
            ("Pénalités totales",      round(kpis["late_fees"], 2)),
            ("Taux de retard",         f"{(kpis['late_rate'] or 0) * 100:.2f} %"),
            ("Clients actifs",         int(kpis["active_customers"])),
        ],
        columns=["Indicateur", "Valeur"],
    )

    monthly      = dwh_data.monthly_revenue(filters)
    by_category  = dwh_data.revenue_by_category(filters)
    top_revenue  = dwh_data.top_films_revenue(filters, limit=25)
    top_late     = dwh_data.top_films_late(filters, limit=25)
    by_country   = dwh_data.revenue_by_country(filters)
    by_store     = dwh_data.store_performance(filters)
    detail       = dwh_data.filtered_data(filters, limit=10000)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        kpi_df.to_excel(writer,      sheet_name="KPI",            index=False)
        monthly.to_excel(writer,     sheet_name="Mensuel",        index=False)
        by_category.to_excel(writer, sheet_name="Catégories",     index=False)
        top_revenue.to_excel(writer, sheet_name="Top films CA",   index=False)
        top_late.to_excel(writer,    sheet_name="Top films retards", index=False)
        by_country.to_excel(writer,  sheet_name="Pays",           index=False)
        by_store.to_excel(writer,    sheet_name="Magasins",       index=False)
        detail.to_excel(writer,      sheet_name="Détail",         index=False)

        # Mise en forme simple : largeurs auto + bordure d'en-tête
        wb = writer.book
        header_fmt = wb.add_format({"bold": True, "bg_color": "#1f2937", "color": "white", "border": 1})
        for sheet_name, frame in {
            "KPI": kpi_df, "Mensuel": monthly, "Catégories": by_category,
            "Top films CA": top_revenue, "Top films retards": top_late,
            "Pays": by_country, "Magasins": by_store, "Détail": detail,
        }.items():
            ws = writer.sheets[sheet_name]
            for i, col in enumerate(frame.columns):
                ws.write(0, i, col, header_fmt)
                width = min(40, max(12, frame[col].astype(str).map(len).max() if not frame.empty else 12))
                ws.set_column(i, i, width)
    return buf.getvalue()


def build_csv(filters: dict) -> bytes:
    """Export CSV des locations filtrées."""
    df = dwh_data.filtered_data(filters, limit=50000)
    buf = io.StringIO()
    df.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
    return buf.getvalue().encode("utf-8-sig")

"""Callbacks centralisés : KPI cards et graphiques, dépendants des filtres.

Toutes les sorties sont enregistrées avec `allow_duplicate=True` parce que
plusieurs pages peuvent posséder un id identique (par exemple `kpi-row`).
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, callback, dash_table, html, no_update

from dashboard import data as dwh_data
from dashboard.components import kpi_cards


# -------- Palette & template Plotly --------
_TEMPLATE = "plotly_white"
_SEQ = px.colors.qualitative.Bold


def _empty_fig(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template=_TEMPLATE,
        title=title,
        annotations=[
            dict(
                text="Aucune donnée pour les filtres sélectionnés",
                xref="paper", yref="paper",
                showarrow=False, font=dict(size=14, color="#6b7280"),
            )
        ],
    )
    return fig


# -----------------------------------------------------------
# Filtres globaux → dict
# -----------------------------------------------------------
def _collect(year, months, countries, stores, categories, ratings) -> dict:
    return {
        "year": year,
        "months": months or [],
        "countries": countries or [],
        "stores": stores or [],
        "categories": categories or [],
        "ratings": ratings or [],
    }


_FILTER_INPUTS = [
    Input("f-year", "value"),
    Input("f-months", "value"),
    Input("f-countries", "value"),
    Input("f-stores", "value"),
    Input("f-categories", "value"),
    Input("f-ratings", "value"),
]


# -----------------------------------------------------------
# KPI Row
# -----------------------------------------------------------
@callback(Output("kpi-row", "children"), *_FILTER_INPUTS)
def update_kpis(year, months, countries, stores, categories, ratings):
    try:
        filters = _collect(year, months, countries, stores, categories, ratings)
        kpis = dwh_data.get_kpis(filters)
        return kpi_cards.render_row(kpis)
    except Exception as exc:
        return dbc.Alert(f"Erreur KPI : {exc!s}", color="danger")


# -----------------------------------------------------------
# Page Accueil
# -----------------------------------------------------------
@callback(Output("g-monthly-revenue", "figure"), *_FILTER_INPUTS)
def update_monthly_revenue(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.monthly_revenue(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return _empty_fig("Évolution mensuelle du chiffre d'affaires")
        df["period"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
        fig = px.area(df, x="period", y="revenue", template=_TEMPLATE,
                      labels={"period": "Mois", "revenue": "Chiffre d'affaires ($)"},
                      title="Évolution mensuelle du chiffre d'affaires")
        fig.update_traces(line_color="#1f2937", fillcolor="rgba(245, 158, 11, 0.3)")
        fig.update_layout(hovermode="x unified", margin=dict(t=50, l=10, r=10, b=10))
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


@callback(Output("g-revenue-by-category", "figure"), *_FILTER_INPUTS)
def update_revenue_by_category(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.revenue_by_category(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return _empty_fig("Revenus par catégorie")
        fig = px.pie(df, names="category", values="revenue", template=_TEMPLATE,
                     hole=0.55, title="Mix CA par catégorie",
                     color_discrete_sequence=_SEQ)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=50, l=10, r=10, b=10), showlegend=False)
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


@callback(Output("g-revenue-map", "figure"), *_FILTER_INPUTS)
def update_revenue_map(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.revenue_by_country(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return _empty_fig("Carte mondiale des revenus")
        fig = px.choropleth(
            df, locations="country", locationmode="country names",
            color="revenue", hover_data=["nb_rentals", "nb_customers"],
            template=_TEMPLATE,
            color_continuous_scale="YlOrRd",
            title="Carte mondiale des revenus par pays",
        )
        fig.update_layout(margin=dict(t=50, l=10, r=10, b=10),
                          geo=dict(showframe=False, showcoastlines=True))
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


# -----------------------------------------------------------
# Page Revenus
# -----------------------------------------------------------
@callback(Output("g-monthly-revenue-cat", "figure"), *_FILTER_INPUTS)
def update_monthly_cat(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.monthly_revenue_by_category(
            _collect(year, months, countries, stores, categories, ratings)
        )
        if df.empty:
            return _empty_fig("Évolution mensuelle par catégorie")
        df["period"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
        fig = px.line(
            df, x="period", y="revenue", color="category",
            template=_TEMPLATE,
            title="Évolution mensuelle du CA par catégorie",
            labels={"period": "Mois", "revenue": "CA ($)", "category": "Catégorie"},
            color_discrete_sequence=_SEQ,
        )
        fig.update_layout(margin=dict(t=50, l=10, r=10, b=10), hovermode="x unified")
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


@callback(Output("g-revenue-by-category-bar", "figure"), *_FILTER_INPUTS)
def update_cat_bar(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.revenue_by_category(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return _empty_fig("Catégories les plus rentables")
        fig = px.bar(
            df, x="revenue", y="category", orientation="h",
            template=_TEMPLATE,
            title="Catégories les plus rentables",
            color="revenue", color_continuous_scale="Oranges",
            labels={"revenue": "CA ($)", "category": "Catégorie"},
        )
        fig.update_layout(yaxis=dict(categoryorder="total ascending"),
                          margin=dict(t=50, l=10, r=10, b=10), coloraxis_showscale=False)
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


@callback(Output("g-country-heatmap", "figure"), *_FILTER_INPUTS)
def update_heatmap(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.country_category_heatmap(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return _empty_fig("Pays × Catégorie")
        pivot = df.pivot_table(index="country", columns="category", values="revenue", fill_value=0)
        fig = px.imshow(
            pivot, color_continuous_scale="YlOrRd", template=_TEMPLATE,
            title="Heatmap CA — Pays × Catégorie", aspect="auto",
            labels=dict(x="Catégorie", y="Pays", color="CA ($)"),
        )
        fig.update_layout(margin=dict(t=50, l=10, r=10, b=10))
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


# -----------------------------------------------------------
# Page Films
# -----------------------------------------------------------
@callback(Output("g-top-films-revenue", "figure"), *_FILTER_INPUTS)
def update_top_revenue(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.top_films_revenue(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return _empty_fig("Top films par CA")
        fig = px.bar(
            df, x="revenue", y="title", color="category", orientation="h",
            template=_TEMPLATE, title="Top 15 films par chiffre d'affaires",
            labels={"revenue": "CA ($)", "title": "Film", "category": "Catégorie"},
            color_discrete_sequence=_SEQ,
        )
        fig.update_layout(yaxis=dict(categoryorder="total ascending"),
                          margin=dict(t=50, l=10, r=10, b=10))
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


@callback(Output("g-top-films-late", "figure"), *_FILTER_INPUTS)
def update_top_late(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.top_films_late(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return _empty_fig("Top films par pénalités")
        fig = px.bar(
            df, x="late_fees", y="title", color="category", orientation="h",
            template=_TEMPLATE, title="Top 15 films par pénalités de retard",
            labels={"late_fees": "Pénalités ($)", "title": "Film", "category": "Catégorie"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(yaxis=dict(categoryorder="total ascending"),
                          margin=dict(t=50, l=10, r=10, b=10))
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


# -----------------------------------------------------------
# Page Clients
# -----------------------------------------------------------
@callback(Output("g-clients-map", "figure"), *_FILTER_INPUTS)
def update_clients_map(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.revenue_by_country(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return _empty_fig("Clients par pays")
        fig = px.scatter_geo(
            df, locations="country", locationmode="country names",
            size="nb_customers", color="revenue",
            template=_TEMPLATE, color_continuous_scale="Viridis",
            title="Clients actifs et revenus par pays",
            hover_data=["nb_rentals"],
        )
        fig.update_layout(margin=dict(t=50, l=10, r=10, b=10),
                          geo=dict(showframe=False, showcoastlines=True))
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


@callback(Output("g-clients-segments", "figure"), *_FILTER_INPUTS)
def update_segments(year, months, countries, stores, categories, ratings):
    try:
        # Pour la segmentation, on requête dim_customer directement
        from sqlalchemy import text
        from etl.db import get_dwh_engine
        with get_dwh_engine().connect() as conn:
            df = pd.read_sql(
                text(
                    "SELECT segment, COUNT(*) AS nb FROM dwh.dim_customer "
                    "WHERE is_current GROUP BY segment ORDER BY nb DESC"
                ),
                conn,
            )
        if df.empty:
            return _empty_fig("Segments clients")
        fig = px.pie(df, names="segment", values="nb", hole=0.5,
                     template=_TEMPLATE, title="Répartition des clients par segment",
                     color_discrete_sequence=_SEQ)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=50, l=10, r=10, b=10), showlegend=False)
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


@callback(Output("g-top-countries", "figure"), *_FILTER_INPUTS)
def update_top_countries(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.revenue_by_country(
            _collect(year, months, countries, stores, categories, ratings)
        ).head(20)
        if df.empty:
            return _empty_fig("Top pays par CA")
        fig = px.bar(
            df, x="country", y="revenue", color="nb_rentals",
            template=_TEMPLATE, color_continuous_scale="Oranges",
            title="Top 20 pays par chiffre d'affaires",
            labels={"country": "Pays", "revenue": "CA ($)", "nb_rentals": "Locations"},
        )
        fig.update_layout(margin=dict(t=50, l=10, r=10, b=10))
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


# -----------------------------------------------------------
# Page Magasins
# -----------------------------------------------------------
@callback(Output("g-store-revenue", "figure"), *_FILTER_INPUTS)
def update_store_revenue(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.store_performance(
            _collect(year, months, countries, stores, categories, ratings)
        ).head(30)
        if df.empty:
            return _empty_fig("Performance magasins")
        df["store_label"] = df["store_id"].astype(str) + " — " + df["city"].fillna("")
        fig = px.bar(
            df, x="store_label", y="revenue", color="late_fees",
            template=_TEMPLATE, color_continuous_scale="Reds",
            title="Top 30 magasins par chiffre d'affaires",
            labels={"store_label": "Magasin", "revenue": "CA ($)", "late_fees": "Pénalités ($)"},
        )
        fig.update_layout(margin=dict(t=50, l=10, r=10, b=10), xaxis_tickangle=-45)
        return fig
    except Exception as exc:
        return _empty_fig(f"Erreur : {exc!s}")


@callback(
    Output("t-stores", "data"),
    Output("t-stores", "columns"),
    *_FILTER_INPUTS,
)
def update_store_table(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.store_performance(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return [], []
        df = df.copy()
        for col in ("revenue", "late_fees", "avg_basket"):
            df[col] = df[col].round(2)
        cols = [{"name": c.replace("_", " ").title(), "id": c} for c in df.columns]
        return df.to_dict("records"), cols
    except Exception:
        return [], []


# -----------------------------------------------------------
# Page Données — table dynamique
# -----------------------------------------------------------
@callback(
    Output("t-rentals", "data"),
    Output("t-rentals", "columns"),
    *_FILTER_INPUTS,
)
def update_rental_table(year, months, countries, stores, categories, ratings):
    try:
        df = dwh_data.filtered_data(_collect(year, months, countries, stores, categories, ratings))
        if df.empty:
            return [], []
        df = df.copy()
        if "rental_date" in df.columns:
            df["rental_date"] = pd.to_datetime(df["rental_date"]).dt.strftime("%Y-%m-%d")
        cols = [{"name": c.replace("_", " ").title(), "id": c} for c in df.columns]
        return df.to_dict("records"), cols
    except Exception:
        return [], []

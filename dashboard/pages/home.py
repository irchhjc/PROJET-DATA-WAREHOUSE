"""Page d'accueil : KPI globaux + vue synthétique du chiffre d'affaires."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def render() -> dbc.Container:
    return dbc.Container(
        [
            html.H2("Tableau de bord — Vue d'ensemble", className="mb-1"),
            html.P(
                "Synthèse de l'activité Sakila sur la période sélectionnée. "
                "Utilisez le panneau de filtres pour cibler une année, "
                "un mois, un pays, une catégorie ou un magasin.",
                className="text-muted",
            ),
            html.Div(id="kpi-row"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="g-monthly-revenue",   config={"displaylogo": False}), md=8),
                    dbc.Col(dcc.Graph(id="g-revenue-by-category", config={"displaylogo": False}), md=4),
                ],
                className="g-3 mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="g-revenue-map", config={"displaylogo": False}), md=12),
                ],
                className="g-3 mb-3",
            ),
        ],
        fluid=True,
    )

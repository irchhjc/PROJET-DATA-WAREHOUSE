"""Page Revenus : analyse temporelle et par catégorie."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def render() -> dbc.Container:
    return dbc.Container(
        [
            html.H2("Analyse des revenus", className="mb-1"),
            html.P("Évolution mensuelle, mix catégoriel et heatmap pays × catégorie.", className="text-muted"),
            html.Div(id="kpi-row"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="g-monthly-revenue-cat"), md=12),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="g-revenue-by-category-bar"), md=6),
                    dbc.Col(dcc.Graph(id="g-country-heatmap"), md=6),
                ],
                className="mb-3",
            ),
        ],
        fluid=True,
    )

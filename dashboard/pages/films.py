"""Page Films : top revenus, top pénalités, distribution catégories."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def render() -> dbc.Container:
    return dbc.Container(
        [
            html.H2("Analyse des films", className="mb-1"),
            html.P("Top films par chiffre d'affaires et par pénalités générées.", className="text-muted"),
            html.Div(id="kpi-row"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="g-top-films-revenue"), md=6),
                    dbc.Col(dcc.Graph(id="g-top-films-late"),    md=6),
                ],
                className="mb-3",
            ),
        ],
        fluid=True,
    )

"""Page Clients : géographie et segmentation."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def render() -> dbc.Container:
    return dbc.Container(
        [
            html.H2("Analyse des clients", className="mb-1"),
            html.P("Revenu, panier moyen, segmentation et répartition géographique.", className="text-muted"),
            html.Div(id="kpi-row"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="g-clients-map"),       md=8),
                    dbc.Col(dcc.Graph(id="g-clients-segments"),  md=4),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="g-top-countries"), md=12),
                ],
                className="mb-3",
            ),
        ],
        fluid=True,
    )

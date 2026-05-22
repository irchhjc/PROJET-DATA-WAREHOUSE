"""Page Magasins : comparatif des points de vente."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html


def render() -> dbc.Container:
    return dbc.Container(
        [
            html.H2("Performance des magasins", className="mb-1"),
            html.P("Comparatif CA / locations / pénalités / panier moyen.", className="text-muted"),
            html.Div(id="kpi-row"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="g-store-revenue"), md=12),
                ],
                className="mb-3",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H5("Détail magasins", className="card-title"),
                        dash_table.DataTable(
                            id="t-stores",
                            page_size=15,
                            sort_action="native",
                            filter_action="native",
                            style_cell={"fontFamily": "Inter, sans-serif", "fontSize": 13, "padding": "6px"},
                            style_header={"backgroundColor": "#1f2937", "color": "white", "fontWeight": "bold"},
                            style_data_conditional=[
                                {"if": {"row_index": "odd"}, "backgroundColor": "#f3f4f6"},
                            ],
                        ),
                    ]
                ),
                className="shadow-sm",
            ),
        ],
        fluid=True,
    )

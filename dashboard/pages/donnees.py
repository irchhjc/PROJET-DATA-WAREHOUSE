"""Page Données : table dynamique des locations filtrées."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dash_table, html


def render() -> dbc.Container:
    return dbc.Container(
        [
            html.H2("Détail des locations", className="mb-1"),
            html.P(
                "Tableau exportable filtré selon les sélections globales. "
                "Limité à 5 000 lignes pour préserver la fluidité.",
                className="text-muted",
            ),
            html.Div(id="kpi-row"),
            dbc.Card(
                dbc.CardBody(
                    [
                        dash_table.DataTable(
                            id="t-rentals",
                            page_size=20,
                            sort_action="native",
                            filter_action="native",
                            style_cell={"fontFamily": "Inter, sans-serif", "fontSize": 12, "padding": "5px"},
                            style_header={"backgroundColor": "#1f2937", "color": "white", "fontWeight": "bold"},
                            style_data_conditional=[
                                {"if": {"row_index": "odd"}, "backgroundColor": "#f9fafb"},
                                {
                                    "if": {"filter_query": "{is_late} eq true", "column_id": "is_late"},
                                    "color": "#b91c1c", "fontWeight": "bold",
                                },
                            ],
                        ),
                    ]
                ),
                className="shadow-sm",
            ),
        ],
        fluid=True,
    )

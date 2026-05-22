"""Rangée des boutons de téléchargement (PDF / Excel / CSV)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def render() -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.I(className="bi bi-download me-2 fs-5"),
                        html.Strong("Exports"),
                        html.Span(" — basés sur les filtres actuels", className="text-muted small ms-2"),
                    ],
                    className="mb-2",
                ),
                dbc.ButtonGroup(
                    [
                        dbc.Button("Rapport PDF", id="btn-export-pdf", color="danger",  outline=True),
                        dbc.Button("Excel multi-feuilles", id="btn-export-xlsx", color="success", outline=True),
                        dbc.Button("CSV (données filtrées)", id="btn-export-csv", color="primary", outline=True),
                    ],
                ),
                dcc.Download(id="dl-pdf"),
                dcc.Download(id="dl-xlsx"),
                dcc.Download(id="dl-csv"),
            ]
        ),
        className="mb-3 shadow-sm",
    )

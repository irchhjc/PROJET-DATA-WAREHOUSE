"""Panneau de filtres global, partagé par toutes les pages."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from dashboard.data import get_filter_options


def render() -> dbc.Card:
    opts = get_filter_options()
    years = opts["years"]
    default_year = years[-1] if years else None

    return dbc.Card(
        dbc.CardBody(
            [
                html.H5("Filtres", className="card-title mb-3"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Année", html_for="f-year"),
                                dcc.Dropdown(
                                    id="f-year",
                                    options=[{"label": str(y), "value": y} for y in years],
                                    value=default_year,
                                    clearable=False,
                                ),
                            ],
                            md=2,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Mois", html_for="f-months"),
                                dcc.Dropdown(
                                    id="f-months",
                                    options=[{"label": n, "value": m} for m, n in opts["months"]],
                                    multi=True,
                                    placeholder="Tous",
                                ),
                            ],
                            md=3,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Pays clients", html_for="f-countries"),
                                dcc.Dropdown(
                                    id="f-countries",
                                    options=[{"label": c, "value": c} for c in opts["countries"]],
                                    multi=True,
                                    placeholder="Tous",
                                ),
                            ],
                            md=3,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Catégorie", html_for="f-categories"),
                                dcc.Dropdown(
                                    id="f-categories",
                                    options=[{"label": c, "value": c} for c in opts["categories"]],
                                    multi=True,
                                    placeholder="Toutes",
                                ),
                            ],
                            md=2,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Rating", html_for="f-ratings"),
                                dcc.Dropdown(
                                    id="f-ratings",
                                    options=[{"label": r, "value": r} for r in opts["ratings"]],
                                    multi=True,
                                    placeholder="Tous",
                                ),
                            ],
                            md=2,
                        ),
                    ],
                    className="g-2",
                ),
                html.Div(
                    [
                        dbc.Label("Magasins", html_for="f-stores", className="mt-2"),
                        dcc.Dropdown(
                            id="f-stores",
                            options=[
                                {"label": s["label"], "value": s["store_id"]}
                                for s in opts["stores"][:200]   # limite par sécurité
                            ],
                            multi=True,
                            placeholder="Tous",
                        ),
                    ],
                ),
            ]
        ),
        className="mb-3 shadow-sm",
    )

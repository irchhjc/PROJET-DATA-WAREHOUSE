"""Point d'entrée de l'application Dash Sakila 360.

Lancer :
    python -m dashboard.app
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html

from etl.config import SETTINGS

from dashboard.components import downloads, filters, navbar
from dashboard.pages import clients, donnees, films, home, magasins, revenus
# Les imports ci-dessous enregistrent les callbacks via le décorateur @callback
from dashboard.callbacks import charts, downloads as dl_callbacks  # noqa: F401


# ---------------------------------------------------------------------
# Initialisation Dash
# ---------------------------------------------------------------------
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.FLATLY,
        dbc.icons.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap",
    ],
    suppress_callback_exceptions=True,
    title="Sakila 360 — Performance des locations",
    update_title="Calcul en cours…",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server  # exposé pour WSGI éventuel


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
def serve_layout() -> html.Div:
    return html.Div(
        [
            dcc.Location(id="url"),
            navbar.render(),
            dbc.Container(
                [
                    filters.render(),
                    downloads.render(),
                    html.Div(id="page-content"),
                    html.Hr(),
                    html.Footer(
                        [
                            html.Span("Sakila 360 — Projet académique BI/DW   ·   ",
                                      className="text-muted small"),
                            html.Span("Construit avec Dash + PostgreSQL.",
                                      className="text-muted small"),
                        ],
                        className="text-center py-3",
                    ),
                ],
                fluid=True,
            ),
        ]
    )


app.layout = serve_layout


# ---------------------------------------------------------------------
# Routing simple
# ---------------------------------------------------------------------
ROUTES = {
    "/":          home.render,
    "/revenus":   revenus.render,
    "/films":     films.render,
    "/clients":   clients.render,
    "/magasins":  magasins.render,
    "/donnees":   donnees.render,
}


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def route(pathname: str):
    return ROUTES.get(pathname or "/", home.render)()


# ---------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(
        host=SETTINGS.dash_host,
        port=SETTINGS.dash_port,
        debug=SETTINGS.dash_debug,
    )

"""Barre de navigation principale (Bootstrap)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

NAV_LINKS = [
    ("Accueil",  "/"),
    ("Revenus",  "/revenus"),
    ("Films",    "/films"),
    ("Clients",  "/clients"),
    ("Magasins", "/magasins"),
    ("Données",  "/donnees"),
]


def render(active: str = "/") -> dbc.Navbar:
    items = [
        dbc.NavItem(dbc.NavLink(label, href=href, active=(href == active)))
        for label, href in NAV_LINKS
    ]
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand(
                    [
                        html.Span("Sakila", className="fw-bold"),
                        html.Span(" 360", className="text-warning fw-bold"),
                    ],
                    href="/",
                    className="fs-4",
                ),
                dbc.Nav(items, className="ms-auto", navbar=True),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        sticky="top",
        className="mb-3 shadow-sm",
    )

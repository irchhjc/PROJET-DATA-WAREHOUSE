"""Rangée de cartes KPI homogènes (chiffre d'affaires, locations, etc.)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def _fmt_money(v: float) -> str:
    return f"{v:,.2f} $".replace(",", " ")


def _fmt_int(v: float) -> str:
    return f"{int(v):,}".replace(",", " ")


def _fmt_pct(v: float) -> str:
    return f"{(v or 0) * 100:.1f} %"


def _card(label: str, value: str, icon: str, color: str) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.I(className=f"bi {icon} fs-3 me-2"),
                        html.Span(label, className="text-muted small text-uppercase"),
                    ],
                    className="d-flex align-items-center mb-2",
                ),
                html.H3(value, className=f"fw-bold mb-0 text-{color}"),
            ]
        ),
        className="shadow-sm h-100",
    )


def render_row(kpis: dict) -> dbc.Row:
    revenue = kpis.get("revenue", 0) or 0
    nb_rentals = kpis.get("nb_rentals", 0) or 0
    avg_basket = kpis.get("avg_basket", 0) or 0
    late_fees = kpis.get("late_fees", 0) or 0
    late_rate = kpis.get("late_rate", 0) or 0
    customers = kpis.get("active_customers", 0) or 0

    cards = [
        _card("Chiffre d'affaires", _fmt_money(revenue),    "bi-cash-coin",         "success"),
        _card("Locations",          _fmt_int(nb_rentals),   "bi-film",              "primary"),
        _card("Panier moyen",       _fmt_money(avg_basket), "bi-bag-check",         "info"),
        _card("Pénalités totales",  _fmt_money(late_fees),  "bi-exclamation-octagon","danger"),
        _card("Taux de retard",     _fmt_pct(late_rate),    "bi-clock-history",     "warning"),
        _card("Clients actifs",     _fmt_int(customers),    "bi-people",            "secondary"),
    ]
    return dbc.Row(
        [dbc.Col(c, xs=12, sm=6, md=4, lg=2, className="mb-3") for c in cards],
        className="g-3",
    )

"""Callbacks des exports PDF / Excel / CSV."""

from __future__ import annotations

from datetime import datetime

from dash import Input, Output, State, callback, dcc, no_update

from dashboard.utils import exports, pdf_report


_FILTER_STATES = [
    State("f-year", "value"),
    State("f-months", "value"),
    State("f-countries", "value"),
    State("f-stores", "value"),
    State("f-categories", "value"),
    State("f-ratings", "value"),
]


def _filters(year, months, countries, stores, categories, ratings) -> dict:
    return {
        "year": year, "months": months or [], "countries": countries or [],
        "stores": stores or [], "categories": categories or [], "ratings": ratings or [],
    }


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@callback(
    Output("dl-pdf", "data"),
    Input("btn-export-pdf", "n_clicks"),
    *_FILTER_STATES,
    prevent_initial_call=True,
)
def export_pdf(n_clicks, year, months, countries, stores, categories, ratings):
    if not n_clicks:
        return no_update
    filters = _filters(year, months, countries, stores, categories, ratings)
    pdf_bytes = pdf_report.build_pdf(filters)
    return dcc.send_bytes(pdf_bytes, filename=f"sakila360_rapport_{_stamp()}.pdf")


@callback(
    Output("dl-xlsx", "data"),
    Input("btn-export-xlsx", "n_clicks"),
    *_FILTER_STATES,
    prevent_initial_call=True,
)
def export_xlsx(n_clicks, year, months, countries, stores, categories, ratings):
    if not n_clicks:
        return no_update
    filters = _filters(year, months, countries, stores, categories, ratings)
    xlsx_bytes = exports.build_excel(filters)
    return dcc.send_bytes(xlsx_bytes, filename=f"sakila360_export_{_stamp()}.xlsx")


@callback(
    Output("dl-csv", "data"),
    Input("btn-export-csv", "n_clicks"),
    *_FILTER_STATES,
    prevent_initial_call=True,
)
def export_csv(n_clicks, year, months, countries, stores, categories, ratings):
    if not n_clicks:
        return no_update
    filters = _filters(year, months, countries, stores, categories, ratings)
    csv_bytes = exports.build_csv(filters)
    return dcc.send_bytes(csv_bytes, filename=f"sakila360_donnees_{_stamp()}.csv")

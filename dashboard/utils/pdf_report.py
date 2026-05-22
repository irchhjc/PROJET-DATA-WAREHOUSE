"""Génération d'un rapport PDF synthétique avec ReportLab.

Le rapport contient :
    - une page de garde,
    - un bloc KPI,
    - un récapitulatif des analyses clés (top films, top catégories, pays),
    - les filtres ayant servi à la génération.
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from dashboard import data as dwh_data


_BRAND = colors.HexColor("#1f2937")
_ACCENT = colors.HexColor("#f59e0b")
_LIGHT = colors.HexColor("#f3f4f6")


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle("H0", parent=base["Title"], fontSize=24, textColor=_BRAND, leading=28))
    base.add(ParagraphStyle("H1Custom", parent=base["Heading1"], fontSize=15, textColor=_BRAND, spaceBefore=10))
    base.add(ParagraphStyle("Small", parent=base["BodyText"], fontSize=9, textColor=colors.grey))
    return base


def _fmt_money(v: float) -> str:
    return f"{(v or 0):,.2f} $".replace(",", " ")


def _table(df: pd.DataFrame, max_rows: int = 12) -> Table:
    df = df.head(max_rows).copy()
    data = [list(df.columns)] + df.astype(str).values.tolist()
    tbl = Table(data, hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",   (0, 0), (-1, -1), 8),
                ("GRID",       (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return tbl


def _filters_text(filters: dict) -> str:
    parts = []
    for label, key in (
        ("Année", "year"), ("Mois", "months"),
        ("Pays clients", "countries"), ("Magasins", "stores"),
        ("Catégories", "categories"), ("Ratings", "ratings"),
    ):
        v = filters.get(key)
        if v:
            if isinstance(v, list):
                parts.append(f"{label} : {', '.join(map(str, v))}")
            else:
                parts.append(f"{label} : {v}")
    return " · ".join(parts) if parts else "Aucun filtre (vue globale)"


def build_pdf(filters: dict) -> bytes:
    styles = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title="Rapport Sakila 360",
    )
    story: list = []

    # ----- Page de garde -----
    story.append(Paragraph("Sakila 360", styles["H0"]))
    story.append(Paragraph("Rapport d'Analyse de la Performance des Locations", styles["Heading2"]))
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph(
        f"<b>Date de génération :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles["BodyText"],
    ))
    story.append(Paragraph(f"<b>Périmètre :</b> {_filters_text(filters)}", styles["BodyText"]))
    story.append(Spacer(1, 1.0 * cm))
    story.append(Paragraph(
        "Ce rapport synthétise les principaux indicateurs de performance "
        "des locations Sakila pour les filtres sélectionnés. Il couvre la "
        "rentabilité par catégorie de films, le top des films par chiffre "
        "d'affaires et par pénalités de retard, ainsi qu'une analyse "
        "géographique et par magasin.",
        styles["BodyText"],
    ))
    story.append(PageBreak())

    # ----- KPI -----
    kpis = dwh_data.get_kpis(filters)
    story.append(Paragraph("1. Indicateurs clés", styles["H1Custom"]))
    kpi_table = [
        ["Chiffre d'affaires",   _fmt_money(kpis.get("revenue", 0))],
        ["Nombre de locations",  f"{int(kpis.get('nb_rentals', 0)):,}".replace(",", " ")],
        ["Panier moyen",         _fmt_money(kpis.get("avg_basket", 0))],
        ["Pénalités totales",    _fmt_money(kpis.get("late_fees", 0))],
        ["Taux de retard",       f"{(kpis.get('late_rate') or 0) * 100:.1f} %"],
        ["Clients actifs",       f"{int(kpis.get('active_customers', 0)):,}".replace(",", " ")],
    ]
    tbl = Table(kpi_table, colWidths=[7 * cm, 5 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _LIGHT]),
                ("BOX", (0, 0), (-1, -1), 0.5, _BRAND),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("TEXTCOLOR", (0, 0), (0, -1), _BRAND),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    story.append(tbl)

    # ----- Top catégories -----
    story.append(Paragraph("2. Catégories les plus rentables", styles["H1Custom"]))
    by_cat = dwh_data.revenue_by_category(filters)
    if not by_cat.empty:
        by_cat_disp = by_cat.copy()
        by_cat_disp["revenue"] = by_cat_disp["revenue"].apply(_fmt_money)
        by_cat_disp["avg_basket"] = by_cat_disp["avg_basket"].apply(_fmt_money)
        story.append(_table(by_cat_disp, max_rows=10))
    else:
        story.append(Paragraph("Aucune donnée pour le périmètre choisi.", styles["BodyText"]))

    # ----- Top films CA -----
    story.append(Paragraph("3. Top films par chiffre d'affaires", styles["H1Custom"]))
    top_rev = dwh_data.top_films_revenue(filters, limit=10)
    if not top_rev.empty:
        top_rev_disp = top_rev.copy()
        top_rev_disp["revenue"] = top_rev_disp["revenue"].apply(_fmt_money)
        story.append(_table(top_rev_disp, max_rows=10))
    else:
        story.append(Paragraph("Aucune donnée.", styles["BodyText"]))

    # ----- Top films pénalités -----
    story.append(Paragraph("4. Top films par pénalités de retard", styles["H1Custom"]))
    top_late = dwh_data.top_films_late(filters, limit=10)
    if not top_late.empty:
        top_late_disp = top_late.copy()
        top_late_disp["late_fees"] = top_late_disp["late_fees"].apply(_fmt_money)
        story.append(_table(top_late_disp, max_rows=10))
    else:
        story.append(Paragraph("Aucune pénalité enregistrée sur le périmètre.", styles["BodyText"]))

    story.append(PageBreak())

    # ----- Revenus par pays -----
    story.append(Paragraph("5. Revenus par pays (top 15)", styles["H1Custom"]))
    by_country = dwh_data.revenue_by_country(filters).head(15)
    if not by_country.empty:
        by_country_disp = by_country.copy()
        by_country_disp["revenue"] = by_country_disp["revenue"].apply(_fmt_money)
        by_country_disp["avg_basket"] = by_country_disp["avg_basket"].apply(_fmt_money)
        story.append(_table(by_country_disp, max_rows=15))

    # ----- Performance magasins -----
    story.append(Paragraph("6. Performance des magasins (top 15)", styles["H1Custom"]))
    by_store = dwh_data.store_performance(filters).head(15)
    if not by_store.empty:
        by_store_disp = by_store.copy()
        by_store_disp["revenue"] = by_store_disp["revenue"].apply(_fmt_money)
        by_store_disp["late_fees"] = by_store_disp["late_fees"].apply(_fmt_money)
        by_store_disp["avg_basket"] = by_store_disp["avg_basket"].apply(_fmt_money)
        story.append(_table(by_store_disp, max_rows=15))

    story.append(Spacer(1, 1.0 * cm))
    story.append(Paragraph(
        "— Rapport généré automatiquement par l'application Sakila 360. —",
        styles["Small"],
    ))

    doc.build(story)
    return buf.getvalue()

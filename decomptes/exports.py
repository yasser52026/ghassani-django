import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

ENTETE_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
ENTETE_FONT = Font(color="FFFFFF", bold=True)


def exporter_decomptes_excel(service, annee, mois, decomptes):
    wb = Workbook()
    ws = wb.active
    ws.title = "Décompte"
    ws.merge_cells("A1:I1")
    ws["A1"] = f"Décompte des heures supplémentaires — {service.nom} — {MOIS_FR[mois]} {annee}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = Alignment(horizontal="center")

    entetes = ["Matricule", "Nom", "Prénom", "Ouvrable", "Vendredi", "Ramadan", "Week-end/férié", "Nuit", "Total"]
    ws.append([])
    ws.append(entetes)
    for col_idx, _ in enumerate(entetes, start=1):
        c = ws.cell(row=3, column=col_idx)
        c.fill = ENTETE_FILL
        c.font = ENTETE_FONT
        c.alignment = Alignment(horizontal="center")

    total = 0.0
    for d in decomptes:
        ws.append([
            d.agent.matricule, d.agent.nom, d.agent.prenom,
            d.heures_ouvrable, d.heures_vendredi, d.heures_ramadan,
            d.heures_weekend_ferie, d.heures_nuit, d.total_heures,
        ])
        total += d.total_heures

    ligne = ws.max_row + 1
    ws.cell(row=ligne, column=3, value="TOTAL").font = Font(bold=True)
    ws.cell(row=ligne, column=9, value=total).font = Font(bold=True)
    for idx, largeur in enumerate([14, 16, 16, 12, 12, 12, 16, 10, 12], start=1):
        ws.column_dimensions[get_column_letter(idx)].width = largeur

    tampon = io.BytesIO()
    wb.save(tampon)
    tampon.seek(0)
    return tampon


def exporter_decomptes_pdf(service, annee, mois, decomptes):
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(tampon, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle("Titre", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=14)
    style_sous = ParagraphStyle("Sous", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10)

    elements = [
        Paragraph("CHR de Fès — Hôpital Al Ghassani", style_sous),
        Paragraph(f"Bordereau des heures supplémentaires — {service.nom}<br/>{MOIS_FR[mois]} {annee}", style_titre),
        Spacer(1, 0.8*cm),
    ]

    donnees = [["Matricule", "Nom et prénom", "Ouvrable", "Vendredi", "Ramadan", "W-E/férié", "Nuit", "Total"]]
    total = 0.0
    for d in decomptes:
        donnees.append([
            d.agent.matricule, d.agent.nom_complet,
            f"{d.heures_ouvrable:g}", f"{d.heures_vendredi:g}", f"{d.heures_ramadan:g}",
            f"{d.heures_weekend_ferie:g}", f"{d.heures_nuit:g}", f"{d.total_heures:g}",
        ])
        total += d.total_heures
    donnees.append(["", "TOTAL", "", "", "", "", "", f"{total:g}"])

    table = Table(donnees, repeatRows=1, colWidths=[2.3*cm, 4.5*cm, 2*cm, 2*cm, 2*cm, 2.2*cm, 1.8*cm, 2*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(table)
    doc.build(elements)
    tampon.seek(0)
    return tampon

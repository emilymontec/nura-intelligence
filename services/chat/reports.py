"""
Módulo 4 - Visualización y Reportes.

Antes de este cambio, el botón "exportar_reporte_pdf()" del frontend era
texto estático sin ningún handler, y no existía ninguna librería de
generación de PDF instalada ni ninguna vista que lo produjera. Este módulo
genera reportes reales (PDF, DOCX, PPTX) a partir del `dataset_context` ya
calculado por el motor de analítica, con 3 variantes por audiencia:

- "executive"  — resumen breve, salud del dato, KPIs principales, hallazgos
                 en lenguaje de negocio. Pensado para alguien que lee 2 minutos.
- "technical"  — todo el detalle: resumen completo, KPIs, alertas de fraude,
                 anomalías (lista extendida), correlaciones, hallazgos.
- "financial"  — foco en columnas e indicadores monetarios: KPIs y
                 correlaciones filtrados a lo financiero, salud y hallazgos
                 orientados a impacto económico.
"""
import io
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)


PALETTE = {
    "purple": colors.HexColor("#7C3AED"),
    "dark": colors.HexColor("#1F2937"),
    "gray": colors.HexColor("#6B7280"),
    "red": colors.HexColor("#DC2626"),
    "green": colors.HexColor("#16A34A"),
    "yellow": colors.HexColor("#CA8A04"),
    "light_bg": colors.HexColor("#F3F4F6"),
}

AUDIENCE_TITLES = {
    "executive": "Reporte Ejecutivo Nura",
    "technical": "Reporte Técnico Nura",
    "financial": "Reporte Financiero Nura",
}

AUDIENCE_LABELS = {
    "executive": "Ejecutivo",
    "technical": "Técnico",
    "financial": "Financiero",
}

_FINANCIAL_KEYWORDS = (
    "total", "monto", "amount", "revenue", "ventas", "sales", "profit",
    "ganancia", "price", "precio", "cost", "costo", "ingreso", "income",
    "margen", "margin", "pago", "payment", "factura", "invoice",
)


def _is_financial_column(name: str) -> bool:
    name_lower = (name or "").lower()
    return any(kw in name_lower for kw in _FINANCIAL_KEYWORDS)


def _resolve_audience(audience: str) -> str:
    audience = (audience or "executive").strip().lower()
    return audience if audience in AUDIENCE_TITLES else "executive"


def _audience_config(audience: str) -> dict:
    """
    Define, por audiencia, cuánto y qué detalle incluir. Mantiene toda la
    lógica de diferenciación en un solo lugar para que PDF/DOCX/PPTX se
    comporten igual.
    """
    if audience == "technical":
        return {
            "kpi_limit": 20,
            "anomaly_limit": 15,
            "correlation_limit": 15,
            "insight_limit": 20,
            "include_fraud": True,
            "include_full_summary": True,
            "financial_only": False,
        }
    if audience == "financial":
        return {
            "kpi_limit": 15,
            "anomaly_limit": 5,
            "correlation_limit": 10,
            "insight_limit": 12,
            "include_fraud": True,
            "include_full_summary": True,
            "financial_only": True,
        }
    # executive (default)
    return {
        "kpi_limit": 6,
        "anomaly_limit": 3,
        "correlation_limit": 5,
        "insight_limit": 8,
        "include_fraud": False,
        "include_full_summary": False,
        "financial_only": False,
    }


def _extract_sections(context: dict, audience: str):
    """Extrae y filtra del dataset_context las secciones según la audiencia."""
    cfg = _audience_config(audience)

    file_name = context.get("file_name", "dataset")
    industry = context.get("industry", "General / Negocios")
    summary = context.get("summary", {})
    health = context.get("health", {})
    kpis = list(context.get("kpis", []))
    insights = list(context.get("insights", []))
    anomalies = list(context.get("anomalies", []))
    correlations = list(context.get("correlations", []))
    fraud_signals = list(context.get("fraud_signals", [])) if cfg["include_fraud"] else []

    if cfg["financial_only"]:
        financial_kpis = [k for k in kpis if _is_financial_column(k.get("label", ""))]
        kpis = financial_kpis or kpis  # si no hay KPIs financieros, no dejamos el reporte vacío
        correlations = [
            c for c in correlations
            if _is_financial_column(c.get("col1", "")) or _is_financial_column(c.get("col2", ""))
        ] or correlations

    kpis = kpis[: cfg["kpi_limit"]]
    anomalies = anomalies[: cfg["anomaly_limit"]]
    correlations = correlations[: cfg["correlation_limit"]]
    insights = insights[: cfg["insight_limit"]]

    return {
        "file_name": file_name,
        "industry": industry,
        "summary": summary,
        "health": health,
        "kpis": kpis,
        "insights": insights,
        "anomalies": anomalies,
        "correlations": correlations,
        "fraud_signals": fraud_signals,
        "cfg": cfg,
    }


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(name="NuraTitle", fontSize=22, leading=26, textColor=PALETTE["dark"], spaceAfter=4))
    base.add(ParagraphStyle(name="NuraSubtitle", fontSize=11, textColor=PALETTE["gray"], spaceAfter=20))
    base.add(ParagraphStyle(name="NuraH2", fontSize=14, textColor=PALETTE["purple"], spaceBefore=16, spaceAfter=8))
    base.add(ParagraphStyle(name="NuraBody", fontSize=10, leading=15, textColor=PALETTE["dark"]))
    base.add(ParagraphStyle(name="NuraBullet", fontSize=10, leading=15, textColor=PALETTE["dark"], leftIndent=12))
    return base


def _score_color(score: float):
    if score >= 80:
        return PALETTE["green"]
    if score >= 50:
        return PALETTE["yellow"]
    return PALETTE["red"]


def generate_pdf_report(context: dict, generated_for: str = "", audience: str = "executive") -> bytes:
    """
    Genera un reporte en PDF a partir de un dataset_context ya calculado (el
    mismo dict que produce services/analytics/analyzer.py). `audience`
    controla qué tan detallado es y qué secciones incluye (ver AUDIENCE_TITLES).
    Devuelve los bytes del PDF; no toca el sistema de archivos.
    """
    if not context or not context.get("file_name"):
        raise ValueError("No hay un dataset analizado en esta sesión para generar un reporte.")

    audience = _resolve_audience(audience)
    data = _extract_sections(context, audience)

    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    story = []

    # Portada / encabezado
    story.append(Paragraph(AUDIENCE_TITLES[audience], styles["NuraTitle"]))
    subtitle = (
        f"Archivo: {data['file_name']} · Sector: {data['industry']} · "
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    if generated_for:
        subtitle += f" · Para: {generated_for}"
    story.append(Paragraph(subtitle, styles["NuraSubtitle"]))

    # Resumen del dataset
    if data["cfg"]["include_full_summary"]:
        story.append(Paragraph("Resumen de la información", styles["NuraH2"]))
        summary = data["summary"]
        resumen_data = [
            ["Filas analizadas", str(summary.get("rows", "—"))],
            ["Columnas", str(summary.get("columns", "—"))],
            ["Celdas vacías", str(summary.get("total_missing", "—"))],
            ["Filas duplicadas", str(summary.get("duplicate_rows", "—"))],
        ]
        resumen_table = Table(resumen_data, colWidths=[7 * cm, 7 * cm])
        resumen_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), PALETTE["light_bg"]),
            ("TEXTCOLOR", (0, 0), (-1, -1), PALETTE["dark"]),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
        ]))
        story.append(resumen_table)

    # Salud de los datos
    health = data["health"]
    score = health.get("health_score", 0)
    risk = health.get("risk_level", "desconocido")
    story.append(Paragraph("Salud de los datos", styles["NuraH2"]))
    score_style = ParagraphStyle(name="ScoreStyle", parent=styles["NuraBody"], textColor=_score_color(score), fontSize=13)
    story.append(Paragraph(f"Puntuación: {score}/100 — Riesgo {risk}", score_style))
    story.append(Spacer(1, 8))

    # KPIs
    if data["kpis"]:
        kpi_title = "Indicadores financieros clave" if audience == "financial" else "Indicadores clave (KPIs)"
        story.append(Paragraph(kpi_title, styles["NuraH2"]))
        kpi_rows = [["Indicador", "Valor"]] + [[k.get("label", "—"), str(k.get("value", "—"))] for k in data["kpis"]]
        kpi_table = Table(kpi_rows, colWidths=[9 * cm, 5 * cm])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PALETTE["purple"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALETTE["light_bg"]]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_table)

    # Alertas de fraude/errores (solo technical/financial)
    if data["fraud_signals"]:
        story.append(Paragraph("Alertas de fraude / error", styles["NuraH2"]))
        for s in data["fraud_signals"]:
            story.append(Paragraph(f"⚠ {s}", ParagraphStyle(name="Fraud", parent=styles["NuraBullet"], textColor=PALETTE["red"])))

    # Anomalías
    if data["anomalies"]:
        story.append(Paragraph("Anomalías detectadas", styles["NuraH2"]))
        story.append(Paragraph(
            f"Se detectaron {len(context.get('anomalies', []))} registros con comportamiento fuera de lo común "
            f"(mostrando hasta {len(data['anomalies'])} ejemplos):", styles["NuraBody"]
        ))
        for a in data["anomalies"]:
            story.append(Paragraph(f"• Fila {a.get('index')}: {a.get('reason', '')}", styles["NuraBullet"]))

    # Correlaciones
    if data["correlations"]:
        corr_title = "Relaciones financieras entre variables" if audience == "financial" else "Relaciones encontradas entre variables"
        story.append(Paragraph(corr_title, styles["NuraH2"]))
        for c in data["correlations"]:
            story.append(Paragraph(
                f"• {c.get('col1')} y {c.get('col2')}: relación {c.get('direction', '').lower()} "
                f"({c.get('strength', '')})", styles["NuraBullet"]
            ))

    # Hallazgos / insights en lenguaje natural
    if data["insights"]:
        story.append(PageBreak())
        story.append(Paragraph("Hallazgos y recomendaciones", styles["NuraH2"]))
        for i in data["insights"]:
            story.append(Paragraph(f"• {i}", styles["NuraBullet"]))
            story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def generate_docx_report(context: dict, generated_for: str = "", audience: str = "executive") -> bytes:
    """
    Genera el mismo reporte que generate_pdf_report(), pero en formato Word
    (.docx) editable, con la misma diferenciación por audiencia.
    """
    from docx import Document
    from docx.shared import Pt, RGBColor

    if not context or not context.get("file_name"):
        raise ValueError("No hay un dataset analizado en esta sesión para generar un reporte.")

    audience = _resolve_audience(audience)
    data = _extract_sections(context, audience)
    health = data["health"]
    score = health.get("health_score", 0)
    risk = health.get("risk_level", "desconocido")

    def _rgb(hex_color):
        h = hex_color.lstrip("#")
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    PURPLE = _rgb("7C3AED")
    DARK = _rgb("1F2937")
    GRAY = _rgb("6B7280")
    SCORE_COLOR = _rgb("16A34A") if score >= 80 else (_rgb("CA8A04") if score >= 50 else _rgb("DC2626"))
    RED = _rgb("DC2626")

    doc = Document()

    title = doc.add_heading(AUDIENCE_TITLES[audience], level=1)
    title.runs[0].font.color.rgb = DARK

    subtitle = doc.add_paragraph()
    subtitle_text = (
        f"Archivo: {data['file_name']} · Sector: {data['industry']} · "
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    if generated_for:
        subtitle_text += f" · Para: {generated_for}"
    run = subtitle.add_run(subtitle_text)
    run.font.size = Pt(9)
    run.font.color.rgb = GRAY

    if data["cfg"]["include_full_summary"]:
        doc.add_heading("Resumen de la información", level=2)
        summary = data["summary"]
        table = doc.add_table(rows=0, cols=2)
        table.style = "Light Grid Accent 5"
        for label, value in [
            ("Filas analizadas", summary.get("rows", "—")),
            ("Columnas", summary.get("columns", "—")),
            ("Celdas vacías", summary.get("total_missing", "—")),
            ("Filas duplicadas", summary.get("duplicate_rows", "—")),
        ]:
            row = table.add_row().cells
            row[0].text = str(label)
            row[1].text = str(value)

    doc.add_heading("Salud de los datos", level=2)
    p = doc.add_paragraph()
    r = p.add_run(f"Puntuación: {score}/100 — Riesgo {risk}")
    r.font.bold = True
    r.font.color.rgb = SCORE_COLOR

    if data["kpis"]:
        kpi_title = "Indicadores financieros clave" if audience == "financial" else "Indicadores clave (KPIs)"
        doc.add_heading(kpi_title, level=2)
        kpi_table = doc.add_table(rows=1, cols=2)
        kpi_table.style = "Light Grid Accent 5"
        hdr = kpi_table.rows[0].cells
        hdr[0].text = "Indicador"
        hdr[1].text = "Valor"
        for k in data["kpis"]:
            row = kpi_table.add_row().cells
            row[0].text = str(k.get("label", "—"))
            row[1].text = str(k.get("value", "—"))

    if data["fraud_signals"]:
        doc.add_heading("Alertas de fraude / error", level=2)
        for s in data["fraud_signals"]:
            p = doc.add_paragraph(style="List Bullet")
            r = p.add_run(f"⚠ {s}")
            r.font.color.rgb = RED

    if data["anomalies"]:
        doc.add_heading("Anomalías detectadas", level=2)
        doc.add_paragraph(
            f"Se detectaron {len(context.get('anomalies', []))} registros con comportamiento fuera de lo común "
            f"(mostrando hasta {len(data['anomalies'])} ejemplos):"
        )
        for a in data["anomalies"]:
            doc.add_paragraph(f"Fila {a.get('index')}: {a.get('reason', '')}", style="List Bullet")

    if data["correlations"]:
        corr_title = "Relaciones financieras entre variables" if audience == "financial" else "Relaciones encontradas entre variables"
        doc.add_heading(corr_title, level=2)
        for c in data["correlations"]:
            doc.add_paragraph(
                f"{c.get('col1')} y {c.get('col2')}: relación {c.get('direction', '').lower()} "
                f"({c.get('strength', '')})", style="List Bullet"
            )

    if data["insights"]:
        doc.add_page_break()
        doc.add_heading("Hallazgos y recomendaciones", level=2)
        for i in data["insights"]:
            doc.add_paragraph(i, style="List Bullet")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


def generate_pptx_report(context: dict, generated_for: str = "", audience: str = "executive") -> bytes:
    """
    Genera el mismo reporte en formato PowerPoint (.pptx), como una serie de
    diapositivas (portada, salud de datos, KPIs, hallazgos, y detalle técnico
    extra para la audiencia 'technical'). Usa python-pptx, que ya estaba en
    el roadmap para Módulo 4 pero sin ningún generador implementado.
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    if not context or not context.get("file_name"):
        raise ValueError("No hay un dataset analizado en esta sesión para generar un reporte.")

    audience = _resolve_audience(audience)
    data = _extract_sections(context, audience)
    health = data["health"]
    score = health.get("health_score", 0)
    risk = health.get("risk_level", "desconocido")

    PURPLE = RGBColor(0x7C, 0x3A, 0xED)
    DARK = RGBColor(0x1F, 0x29, 0x37)
    GRAY = RGBColor(0x6B, 0x72, 0x80)
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    SCORE_COLOR = RGBColor(0x16, 0xA3, 0x4A) if score >= 80 else (RGBColor(0xCA, 0x8A, 0x04) if score >= 50 else RGBColor(0xDC, 0x26, 0x26))

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def _add_slide():
        return prs.slides.add_slide(blank_layout)

    def _add_background(slide, color=RGBColor(0x0A, 0x0A, 0x0F)):
        bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        bg.shadow.inherit = False
        slide.shapes._spTree.remove(bg._element)
        slide.shapes._spTree.insert(2, bg._element)
        return bg

    def _add_title(slide, text, top=Inches(0.5), size=32, color=WHITE):
        box = slide.shapes.add_textbox(Inches(0.7), top, Inches(12), Inches(1))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = True
        run.font.color.rgb = color
        return box

    def _add_body_text(slide, text, top, size=16, color=RGBColor(0xCC, 0xCC, 0xCC), height=Inches(0.5)):
        box = slide.shapes.add_textbox(Inches(0.7), top, Inches(12), height)
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.color.rgb = color
        return box

    def _add_bullets(slide, items, top, size=14, color=RGBColor(0xE5, 0xE5, 0xE5)):
        box = slide.shapes.add_textbox(Inches(0.7), top, Inches(12), Inches(5.5))
        tf = box.text_frame
        tf.word_wrap = True
        for i, item in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            run = p.add_run()
            run.text = f"•  {item}"
            run.font.size = Pt(size)
            run.font.color.rgb = color
            p.space_after = Pt(8)
        return box

    # Slide 1 — Portada
    slide = _add_slide()
    _add_background(slide)
    _add_title(slide, AUDIENCE_TITLES[audience], top=Inches(2.6), size=40, color=WHITE)
    subtitle = f"Archivo: {data['file_name']}  ·  Sector: {data['industry']}"
    if generated_for:
        subtitle += f"  ·  Para: {generated_for}"
    _add_body_text(slide, subtitle, top=Inches(3.5), size=16, color=RGBColor(0xAA, 0xAA, 0xBB))
    _add_body_text(slide, datetime.now().strftime("%d/%m/%Y %H:%M"), top=Inches(4.0), size=12, color=GRAY)

    # Slide 2 — Salud de datos
    slide = _add_slide()
    _add_background(slide)
    _add_title(slide, "Salud de los datos", color=WHITE)
    _add_body_text(slide, f"Puntuación: {score}/100", top=Inches(1.8), size=28, color=SCORE_COLOR)
    _add_body_text(slide, f"Nivel de riesgo: {risk}", top=Inches(2.5), size=16)
    if data["cfg"]["include_full_summary"]:
        summary = data["summary"]
        lines = [
            f"Filas analizadas: {summary.get('rows', '—')}",
            f"Columnas: {summary.get('columns', '—')}",
            f"Celdas vacías: {summary.get('total_missing', '—')}",
            f"Filas duplicadas: {summary.get('duplicate_rows', '—')}",
        ]
        _add_bullets(slide, lines, top=Inches(3.3))

    # Slide 3 — KPIs
    if data["kpis"]:
        slide = _add_slide()
        _add_background(slide)
        kpi_title = "Indicadores financieros clave" if audience == "financial" else "Indicadores clave (KPIs)"
        _add_title(slide, kpi_title, color=WHITE)
        kpi_lines = [f"{k.get('label', '—')}: {k.get('value', '—')}" for k in data["kpis"]]
        _add_bullets(slide, kpi_lines, top=Inches(1.6))

    # Slide 4 — Alertas de fraude (technical/financial)
    if data["fraud_signals"]:
        slide = _add_slide()
        _add_background(slide)
        _add_title(slide, "Alertas de fraude / error", color=RGBColor(0xF8, 0x71, 0x71))
        _add_bullets(slide, [f"⚠ {s}" for s in data["fraud_signals"]], top=Inches(1.6), color=RGBColor(0xFC, 0xA5, 0xA5))

    # Slide 5 — Correlaciones
    if data["correlations"]:
        slide = _add_slide()
        _add_background(slide)
        corr_title = "Relaciones financieras entre variables" if audience == "financial" else "Relaciones entre variables"
        _add_title(slide, corr_title, color=WHITE)
        corr_lines = [
            f"{c.get('col1')} y {c.get('col2')}: relación {c.get('direction', '').lower()} ({c.get('strength', '')})"
            for c in data["correlations"]
        ]
        _add_bullets(slide, corr_lines, top=Inches(1.6))

    # Slide 6 — Anomalías (técnico sobre todo)
    if data["anomalies"]:
        slide = _add_slide()
        _add_background(slide)
        _add_title(slide, "Anomalías detectadas", color=WHITE)
        anomaly_lines = [f"Fila {a.get('index')}: {a.get('reason', '')}" for a in data["anomalies"]]
        _add_bullets(slide, anomaly_lines, top=Inches(1.6))

    # Slide final — Hallazgos y recomendaciones
    if data["insights"]:
        slide = _add_slide()
        _add_background(slide)
        _add_title(slide, "Hallazgos y recomendaciones", color=PURPLE)
        _add_bullets(slide, data["insights"], top=Inches(1.6))

    buffer = io.BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer.read()

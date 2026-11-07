"""PDF do território ativo, sem apropriar evidências da comunidade extensionista."""

from __future__ import annotations

from html import escape
from io import BytesIO
import re

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
from shapely.geometry import box, shape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from territorial_case import indicators
from territorial_science import mechanism_table, phase_severity, scientific_summary
from territorial_road_audit import SOURCE as ROAD_SOURCE, road_geojson


def _n(value, digits=0):
    if value is None or pd.isna(value):
        return "Não estimável"
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _segment_name(name: str) -> str:
    return re.sub(r"(?<=\d)\.(?=\d)", ",", str(name))


def _figure(data: pd.DataFrame, geometries: list, title: str, uf: str | None) -> BytesIO:
    fig, ax = plt.subplots(figsize=(7.0, 4.0), dpi=130)
    geo = data.dropna(subset=["latitude", "longitude"])
    geo = geo.loc[geo["latitude"].between(-34, 5.5) & geo["longitude"].between(-74, -32)].head(500)
    if not geo.empty:
        x0, x1 = float(geo.longitude.min()), float(geo.longitude.max())
        y0, y1 = float(geo.latitude.min()), float(geo.latitude.max())
        padx, pady = max((x1-x0)*.12, .025), max((y1-y0)*.12, .025)
        extent = box(x0-padx, y0-pady, x1+padx, y1+pady)
    else:
        extent = None
    if uf == "ES" and extent is not None:
        for feature in road_geojson()["features"]:
            road = shape(feature["geometry"]).intersection(extent)
            parts = road.geoms if hasattr(road, "geoms") else [road]
            for part in parts:
                if part.geom_type == "LineString" and not part.is_empty:
                    x, y = part.xy
                    ax.plot(x, y, color="#64748B", linewidth=.6, alpha=.7)
    for geom in geometries:
        if extent is not None:
            geom = geom.intersection(extent)
        parts = geom.geoms if hasattr(geom, "geoms") else [geom]
        for part in parts:
            if hasattr(part, "exterior"):
                x, y = part.exterior.xy
                ax.fill(x, y, facecolor="#DBEAFE", edgecolor="#1D4ED8", alpha=.7, linewidth=.7)
    if not geo.empty:
        ax.scatter(geo.longitude, geo.latitude, s=5, c="#F59E0B", alpha=.65, label="Ocorrências PRF")
        ax.legend(loc="best", fontsize=7)
        ax.set_xlim(extent.bounds[0], extent.bounds[2])
        ax.set_ylim(extent.bounds[1], extent.bounds[3])
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("Longitude WGS 84", fontsize=7)
    ax.set_ylabel("Latitude WGS 84", fontsize=7)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.2f}".replace(".", ",")))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.2f}".replace(".", ",")))
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _phase_figure(flags: pd.DataFrame) -> BytesIO:
    rates = phase_severity(flags)
    fig, ax = plt.subplots(figsize=(7, 2.4), dpi=130)
    palette = {"Plena Noite": "#1D4ED8", "Pleno dia": "#F59E0B", "Amanhecer": "#8B5CF6", "Anoitecer": "#64748B"}
    if not rates.empty and rates["Óbitos"].sum() > 0:
        ax.bar(rates["Fase"], rates["Óbitos por 100 acidentes"], color=[palette.get(name, "#64748B") for name in rates["Fase"]])
    else:
        ax.text(.5, .5, "Nenhum óbito registrado nas fases exibidas", ha="center", va="center", transform=ax.transAxes, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
    ax.set_ylabel("Óbitos por 100 acidentes", fontsize=8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}".replace(".", ",")))
    ax.tick_params(axis="x", labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def generate_selected_territory_report(
    data: pd.DataFrame, national: pd.DataFrame, meta: dict, flags: pd.DataFrame,
    ranking: pd.DataFrame, finance: dict, road_summary: dict | None = None,
    historical_summary: dict | None = None, selected_segments: pd.DataFrame | None = None,
) -> bytes:
    """Usa exclusivamente o recorte ativo para resultados e custos."""
    name, uf = meta["nome"], meta.get("uf")
    local, country = indicators(data), indicators(national)
    years = sorted(data["ano"].dropna().astype(int).unique()) if "ano" in data else []
    period = ", ".join(str(year) for year in years) or "não informado"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TerritoryTitle", parent=styles["Title"], fontSize=14, leading=18, spaceAfter=9,
                              textColor=colors.HexColor("#172554")))
    styles.add(ParagraphStyle(name="TerritoryHead", parent=styles["Heading2"], fontSize=10, leading=13,
                              spaceBefore=11, spaceAfter=4, textColor=colors.HexColor("#1D4ED8")))
    styles.add(ParagraphStyle(name="TerritoryBody", parent=styles["BodyText"], fontSize=8.4, leading=11.8, spaceAfter=5))
    story = [Paragraph("Iluminar para Proteger — Relatório do Território Selecionado", styles["TerritoryTitle"]),
             Paragraph(escape(f"Recorte: {name} | UF: {uf or 'Brasil'} | Código IBGE: {meta.get('codigo_ibge') or 'não aplicável'} | Anos: {period}"), styles["TerritoryBody"])]

    def section(title, *paragraphs):
        block = [Paragraph(title, styles["TerritoryHead"])]
        block.extend(Paragraph(escape(str(item)), styles["TerritoryBody"]) for item in paragraphs)
        story.append(KeepTogether(block))

    section("1. Identificação e fonte", f"{name}; microdados de acidentes da PRF carregados no dashboard. {meta.get('metodo', '')}.")
    section("2. Problema observado", f"{_n(local['acidentes'])} ocorrências únicas, {_n(local['obitos'])} óbitos e {_n(local['feridos_graves'])} feridos graves no recorte.")
    section("3. Metodologia", "Deduplicação por ID de ocorrência; causas relacionais como associações não exclusivas. Coordenadas municipais confrontadas com a Malha IBGE 2025 quando disponível.")
    road_text = "; ".join(f"{status}: {count}" for status, count in road_summary.items()) if road_summary else "não verificada neste recorte"
    historical_text = "; ".join(f"{status}: {count}" for status, count in historical_summary.items()) if historical_summary else "não realizada neste recorte"
    section("4. Auditoria geográfica", f"Método: {meta.get('metodo', 'não informado')}. Referência SNV 202507A: {road_text}. Confronto com versões históricas por mês de referência: {historical_text}. Datas exatas de publicação e abertura operacional não verificadas; proximidade não confirma pista.")
    section("5. Indicadores", f"Plena noite: {_n(local['noturnos'])}; pleno dia: {_n(local['diurnos'])}; acidentes fatais: {_n(local['acidentes_fatais'])}; feridos leves: {_n(local['feridos_leves'])}; óbitos por 100 acidentes: {_n(local['obitos_por_100'], 2)}.")
    if national["uf"].dropna().nunique() == 27:
        section("6. Referência nacional", f"Brasil na base carregada: {_n(country['acidentes'])} acidentes, {_n(country['obitos'])} óbitos. São dados contextuais, não resultados de {name}.")
    else:
        section("6. Referência nacional", "Indisponível: a base carregada não contém as 27 UFs.")
    section("7. Visibilidade, percepção e reação", scientific_summary(data, flags, name),
            "Faróis, contraste, velocidade, distância de percepção e frenagem, chuva, neblina e ofuscamento são mecanismos físicos possíveis; não foram medidos diretamente pela PRF neste estudo.")
    story.append(Image(_phase_figure(flags), width=15.5*cm, height=5.3*cm))
    rows = [["Fase", "Fator", "N", "Denom.", "%", "Óbitos"]]
    table_data = mechanism_table(flags)
    for item in table_data.itertuples(index=False):
        rows.append([str(item[0]), str(item[1]), str(item[2]), str(item[3]), _n(item[4], 1), str(item[6])])
    section("8. Fatores registrados por fase", "As linhas de causas podem se sobrepor; os denominadores são acidentes únicos de cada fase.")
    table = Table(rows, colWidths=[2.0*cm, 4.5*cm, 1.1*cm, 1.6*cm, 1.2*cm, 1.2*cm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 6.8),
                               ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#CBD5E1"))]))
    story.append(table)
    section("9. Mapa", "Pontos com coordenadas válidas; até 500 pontos são exibidos. O enquadramento acompanha as ocorrências e pode omitir partes distantes do território. O mapa não identifica locais de instalação.")
    story.append(Image(_figure(data, meta.get("geometrias", []), name, uf), width=15.5*cm, height=8.9*cm))
    br447_present = data["br"].astype(str).str.replace(r"\D", "", regex=True).eq("447").any() if "br" in data else False
    br447_caveat = " BR-447 exige triagem histórica: a malha SNV registra trechos com classificação física e quilometragem variáveis entre 2021 e 2025." if br447_present else ""
    section("10. Segmentos prioritários para investigação", f"{len(ranking)} segmentos identificados por BR/KM. Score heurístico sem denominador de tráfego; não atesta falta de iluminação.{br447_caveat}")
    if not ranking.empty:
        rows = [["Segmento", "Acidentes", "Noite", "Score", "SNV P/D/I"]]
        rows += [[_segment_name(item.trecho_id), str(item.n_acidentes_total), str(item.n_acidentes_noturnos),
                  _n(item.score_iluminacao_solar, 1), getattr(item, "triagem_snv", "n/d")]
                 for item in ranking.head(8).itertuples()]
        ranking_table = Table(rows, colWidths=[6.6*cm, 2.0*cm, 1.7*cm, 1.7*cm, 3.5*cm], repeatRows=1)
        ranking_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")),
                                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                           ("FONTSIZE", (0, 0), (-1, -1), 7),
                                           ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#CBD5E1"))]))
        story.append(ranking_table)
        section("10a. Legenda SNV", "P = correspondência espacial plausível, sem confirmação histórica; D = divergência identificada; I = informação insuficiente. Nenhum segmento foi certificado operacionalmente.")
    section("11. Custos condicionais", (f"{finance['segmentos']} segmentos, {_n(finance['extensao_km'],1)} km geométricos, {_n(finance['postes'])} postes hipotéticos, CAPEX R$ {_n(finance['capex'],2)}. Espaçamento longitudinal não substitui projeto luminotécnico." if finance else "Nenhum segmento selecionado para custo."))
    if finance and selected_segments is not None and not selected_segments.empty:
        section("11a. Segmentos incluídos no custo", "; ".join(_segment_name(item) for item in selected_segments["trecho_id"]))
    section("12. Limitações", "Sem lux, inventário de iluminação, volume de tráfego, residência das vítimas ou confirmação da situação histórica de cada pista. A análise é observacional e não demonstra causalidade.")
    section("13. Conclusão", f"O recorte {name} permite descrever os registros disponíveis e priorizar verificação técnica. Não se conclui que iluminação evitaria um número determinado de acidentes ou óbitos.")
    section("14. Referências", "PRF: https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf",
            "IBGE, Malha Municipal Digital 2025: https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html",
            f"SNV/DNIT, camada ES quando aplicável: {ROAD_SOURCE}",
            "SNV/DNIT histórico 2020–2025: https://servicos.dnit.gov.br/dnitcloud/index.php/s/oTpPRmYs5AAdiNr",
            "FHWA, Nighttime Visibility: https://highways.dot.gov/safety/other/visibility/nighttime-visibility-overview")
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.7*cm, rightMargin=1.7*cm, topMargin=1.7*cm, bottomMargin=1.7*cm)
    doc.build(story)
    return buffer.getvalue()

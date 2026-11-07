"""Relatório territorial independente do relatório científico nacional."""

from __future__ import annotations

from html import escape
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from territorial_case import BR447_SOURCE, MALHA_SOURCE, METRO_SOURCE, indicators, municipal_mesh, territorial_diagnostics


def _number(value: float | int | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "Não estimável"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _map_image(data: pd.DataFrame, audit: pd.DataFrame, scope: str):
    import geopandas as gpd
    import matplotlib.pyplot as plt

    geojson, geometries = municipal_mesh()
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    others = [geom for code, geom in geometries.items() if code != "3205200"]
    gpd.GeoSeries(others, crs="EPSG:4326").plot(ax=ax, facecolor="#E2E8F0", edgecolor="#64748B", linewidth=.5)
    gpd.GeoSeries([geometries["3205200"]], crs="EPSG:4326").plot(ax=ax, facecolor="#FDE68A", edgecolor="#B45309", linewidth=1.5)
    regional = data.loc[data.index.intersection(audit.index)]
    regional = regional.loc[audit.loc[regional.index, "dentro_metropole"] & audit.loc[regional.index, "coordenada_valida"]]
    shown = regional.sort_values("id").head(500)
    if not shown.empty:
        within = audit.loc[shown.index, "dentro_vila_velha"]
        ax.scatter(shown.loc[~within, "longitude"], shown.loc[~within, "latitude"], s=5, color="#38BDF8", alpha=.55, label="Outros municípios")
        ax.scatter(shown.loc[within, "longitude"], shown.loc[within, "latitude"], s=8, color="#B45309", alpha=.75, label="Vila Velha")
        ax.legend(loc="lower left", fontsize=6)
    if scope.startswith("Vila Velha"):
        ax.set_xlim(-40.60, -40.15)
        ax.set_ylim(-20.65, -20.17)
    else:
        ax.set_xlim(-40.74, -40.16)
        ax.set_ylim(-20.79, -19.83)
    ax.set_xlabel("Longitude (WGS 84)", fontsize=7)
    ax.set_ylabel("Latitude (WGS 84)", fontsize=7)
    ax.set_title("Vila Velha e Grande Vitória: limites IBGE 2025 e ocorrências", fontsize=8)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return buffer, len(shown), len(regional)


def generate_territorial_report(
    scope: str, data: pd.DataFrame, national_data: pd.DataFrame,
    causes: pd.DataFrame, ranking: pd.DataFrame, selected_segments: pd.DataFrame,
    finance: dict, audit: pd.DataFrame, evidence: dict | None = None,
) -> bytes:
    """Gera PDF local sem reutilizar números do relatório nacional como municipais."""
    evidence = evidence or {}
    local, national = indicators(data), indicators(national_data)
    years = sorted(int(year) for year in data["ano"].dropna().unique()) if "ano" in data else []
    period = f"{years[0]}-{years[-1]}" if years else "não informado"
    national_available = "uf" in national_data and national_data["uf"].dropna().nunique() == 27
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.7 * cm, rightMargin=1.7 * cm,
                            topMargin=1.7 * cm, bottomMargin=1.6 * cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CaseTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=14, leading=17, textColor=colors.HexColor("#1A2332"), spaceAfter=10))
    styles.add(ParagraphStyle(name="CaseHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
                              fontSize=10, leading=13, textColor=colors.HexColor("#1D4ED8"), spaceBefore=12, spaceAfter=5))
    styles.add(ParagraphStyle(name="CaseBody", parent=styles["BodyText"], fontName="Helvetica",
                              fontSize=8.5, leading=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="CaseSmall", parent=styles["BodyText"], fontName="Helvetica",
                              fontSize=7, leading=9, spaceAfter=5))
    story = [Paragraph("Iluminar para Proteger: Aplicação da Ciência de Dados à Segurança Viária de Vila Velha (ES) e seus Corredores Rodoviários", styles["CaseTitle"]),
             Paragraph("Estudo territorial observacional | Recorte: " + escape(scope) + " | Período disponível: " + period, styles["CaseBody"])]

    def section(title: str, paragraphs: list[str], keep: bool = False) -> None:
        items = [Paragraph(title, styles["CaseHeading"])]
        for text in paragraphs:
            items.append(Paragraph(escape(text), styles["CaseBody"]))
        story.append(KeepTogether(items) if keep else items[0])
        if not keep:
            story.extend(items[1:])

    section("1. Comunidade beneficiária", [
        "Vila Velha, Espírito Santo. A aplicação extensionista consiste em disponibilizar e apresentar o dashboard à comunidade; não houve implantação física de postes pelo projeto."
    ])
    section("2. Justificativa territorial", [
        "Deslocamentos metropolitanos e rodovias federais conectam Vila Velha a outros municípios. Ocorrências do entorno são apresentadas separadamente e não são atribuídas a moradores nem ao território municipal."
    ])
    section("3. Problema de pesquisa", [
        "Como se distribuem os acidentes noturnos e sua gravidade no recorte selecionado, e quais segmentos registrados justificam investigação exploratória de iluminação? A hipótese de visibilidade não equivale a prova causal."
    ])
    diag = territorial_diagnostics(audit)
    section("4. Metodologia", [
        f"Microdados PRF do período {period}, em nível de ocorrência única; pessoas e causas são tabelas relacionais separadas. Município e UF são normalizados. Coordenadas são confrontadas com a Malha Municipal Digital 2025 do IBGE, originalmente SIRGAS 2000 (EPSG:4674), transformada para WGS 84 (EPSG:4326).",
        f"Auditoria no ES: {diag['rotulo_vila']} registros rotulados Vila Velha; {diag['vila_confirmada']} pontos dentro da malha municipal ({diag['ponto_vila_rotulo_outro']} com rótulo de outro município); {diag['rotulo_vila_ponto_fora']} rótulos Vila Velha com ponto fora; {diag['vila_sem_coordenada']} registros municipais sem coordenada; {diag['divergencias']} divergências município/coordenada. Pontos fora do limite não são atribuídos ao município pelo rótulo. A malha de 2025 é referência retrospectiva para 2021-2025.",
    ])
    section("5. Resultados observados no recorte", [
        f"O recorte {scope} contém {_number(local['acidentes'])} ocorrências únicas, {_number(local['noturnos'])} em plena noite, {_number(local['diurnos'])} em pleno dia, {_number(local['obitos'])} óbitos, {_number(local['feridos_graves'])} feridos graves e {_number(local['feridos_leves'])} feridos leves.",
        f"Acidentes fatais: {_number(local['acidentes_fatais'])} ({_number(local['percentual_fatais'],2)}%). Óbitos por 100 acidentes: {_number(local['obitos_por_100'],2)}. Taxa noturna: {_number(local['taxa_noturna'],2)}; taxa diurna: {_number(local['taxa_diurna'],2)}.",
    ])
    national_lines = [
        f"A referência nacional, entre os dados carregados do período {period}, contém {_number(national['acidentes'])} ocorrências e {_number(national['obitos'])} óbitos. Seu indicador de óbitos por 100 acidentes é {_number(national['obitos_por_100'],2)}. Esses totais nacionais não são resultados de Vila Velha.",
        "Comparações descritivas dependem do tamanho amostral e da composição das vias. Não se inferem riscos individuais ou efeito da iluminação.",
    ] if national_available else [
        "Referência nacional indisponível: a base carregada não cobre as 27 UFs. Nenhum total da base parcial é apresentado como total do Brasil."
    ]
    section("6. Comparação contextual com o Brasil", national_lines)
    if local["acidentes"] < 200:
        story.append(Paragraph("A amostra territorial é pequena para projeção econômica local; taxas podem ser instáveis.", styles["CaseBody"]))
    cause_text = "; ".join(f"{name}: {_number(count)}" for name, count in causes.head(8).itertuples(index=False, name=None)) if not causes.empty else "Causas não disponíveis neste recorte."
    type_text = "; ".join(f"{name}: {_number(count)}" for name, count in data["tipo_acidente"].value_counts().loc[lambda counts: counts.gt(0)].head(8).items()) if "tipo_acidente" in data else "Tipos não disponíveis."
    section("7. Causas e gravidade", [
        "Causas associadas a ocorrências: " + cause_text,
        "Tipos de acidente: " + type_text,
        "Uma ocorrência pode ter múltiplas causas; contagens de causas não devem ser somadas como acidentes únicos."
    ])
    map_buffer, shown, regional = _map_image(data, audit, scope)
    story.append(KeepTogether([
        Paragraph("8. Mapa e segmentos elegíveis", styles["CaseHeading"]),
        Image(map_buffer, width=15.5 * cm, height=9.3 * cm),
        Paragraph(f"Mapa: {shown} de {regional} ocorrências metropolitanas com coordenadas válidas (limite visual de 500). Malha IBGE 2025. Pontos do entorno não são ocorrências municipais.", styles["CaseSmall"]),
    ]))
    if not ranking.empty:
        story.append(Paragraph(f"{len(ranking)} segmentos elegíveis por BR e KM no recorte. O score é heurístico, não valida risco causal, falta de iluminação ou prioridade de obra. Segmentos selecionados para custo: {len(selected_segments)}.", styles["CaseBody"]))
        rows = [["Segmento", "Acid. total", "Acid. not.", "Score"]]
        for row in ranking.head(8).itertuples():
            rows.append([str(row.trecho_id), str(row.n_acidentes_total), str(row.n_acidentes_noturnos), _number(row.score_iluminacao_solar, 1)])
        table = Table(rows, colWidths=[8.5 * cm, 2.5 * cm, 2.5 * cm, 2 * cm], repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")),
                                   ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("FONTSIZE", (0, 0), (-1, -1), 7),
                                   ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#CBD5E1")),
                                   ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(table)
    else:
        story.append(Paragraph("Sem segmentos elegíveis por BR e KM neste recorte.", styles["CaseBody"]))
    if "br" in data and {"latitude", "longitude"}.issubset(data):
        br447 = data.loc[data["br"].astype(str).str.replace(r"\D", "", regex=True).eq("447")]
        coordinates = len(br447[["latitude", "longitude"]].dropna().drop_duplicates())
        story.append(Paragraph(
            f"BR-447 no recorte: {len(br447)} ocorrências, {coordinates} pares distintos de coordenadas. "
            "A existência de registros permite descrição histórica, mas não valida risco em trechos novos ou modificados.",
            styles["CaseBody"],
        ))
    section("9. Proposta conceitual de iluminação solar", [
        "Protótipo: poste de 8 m, luminária LED de 40 W, painel de 240 Wp, bateria LiFePO4, telemetria e sensor de movimento. Autonomia e manutenção são simuladas. O espaçamento preliminar de 50 m não substitui projeto fotométrico."
    ])
    economic = ["Nenhum orçamento territorial foi produzido porque não há segmentos selecionados."]
    if finance:
        economic = [
            f"{finance['cenario']}: {finance['segmentos']} {'segmento hipotético' if finance.get('hipotetico') else 'segmentos selecionados'}, {_number(finance['extensao_km'],1)} km, {_number(finance['postes'])} postes estimados, custo unitário R$ {_number(finance['custo_unitario'],2)}, CAPEX R$ {_number(finance['capex'],2)}.",
            f"Manutenção anual hipotética: R$ {_number(finance['manutencao_anual'],2)}; reserva de duas reposições de bateria no horizonte de 15 anos: R$ {_number(finance['reserva_reposicoes_baterias_15_anos'],2)}. Taxa social de desconto de 8% ao ano é hipótese.",
        ]
        if finance["vpl_exploratorio_disponivel"]:
            economic.append("VPL social exploratório por redução hipotética de acidentes noturnos: " + "; ".join(f"{reduction:.0%}: R$ {_number(value,2)}" for reduction, value in finance["sensibilidade"].items()) + ". Benefícios representam custos sociais potencialmente evitados, não receita financeira; redução de óbitos pressupõe proporcionalidade adicional.")
        else:
            economic.append("A amostra/seleção não sustenta VPL local. Os custos acima são exemplos hipotéticos, não estimativa de economia para Vila Velha.")
    section("10. Viabilidade econômica condicional", economic)
    section("11. Limitações", [
        "A PRF não disponibiliza inventário completo de iluminação; fase do dia não mede lux; visibilidade não foi medida diretamente; não há residência das vítimas. Os resultados são observacionais e diferenças entre períodos não demonstram causalidade. A malha municipal de 2025 é usada retrospectivamente. BR-447 possui trechos em implantação; ausência de acidentes em trecho novo não prova segurança.",
        "A ABNT NBR 5101:2024 requer estudo fotométrico e validação de campo. Valores de vida estatística e custos de ferimentos do modelo permanecem provisórios quanto a fonte, ano-base e atualização monetária."
    ], keep=True)
    evidence_lines = []
    for key, label in (("video_demonstrativo", "Vídeo"), ("publicacao_linkedin", "LinkedIn"),
                       ("data_divulgacao", "Data"), ("participantes_registrados", "Participantes registrados"),
                       ("sintese_interacoes", "Interações"), ("resultados_apresentacao", "Resultados da apresentação")):
        value = evidence.get(key)
        if value is not None and value != "":
            evidence_lines.append(f"{label}: {value}")
    section("12. Aplicação extensionista", evidence_lines or [
        "O dashboard está disponível para divulgação comunitária. Não foram fornecidas evidências de apresentação pública ou participação; portanto não se afirma que tais atividades ocorreram."
    ])
    section("13. Conclusões e recomendações", [
        f"No recorte {scope}, os dados permitem descrever {_number(local['acidentes'])} ocorrências e identificar {len(ranking)} segmentos com BR/KM. A comparação noturno/diurno é descritiva, sem evidência causal sobre iluminação.",
        "Recomenda-se verificar em campo a localização, o inventário de iluminação, o volume de tráfego e as condições fotométricas antes de qualquer proposta física. ODS 11: acesso comunitário à informação e subsídios exploratórios para mobilidade mais segura, sem alegar melhora medida de indicador oficial."
    ])
    section("14. Referências", [
        "Polícia Rodoviária Federal. Microdados de acidentes carregados no sistema. https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf",
        "IBGE. Malha Municipal Digital 2025, ES_Municipios_2025.zip. " + MALHA_SOURCE,
        "Governo do Espírito Santo. COMDEVIT: sete municípios da Região Metropolitana da Grande Vitória. " + METRO_SOURCE,
        "DNIT. Obras da BR-447/ES e acesso ao Porto de Capuaba (2026). " + BR447_SOURCE,
        "ABNT. NBR 5101:2024, iluminação pública e rodoviária. Referência normativa; conformidade não demonstrada."
    ])

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(1.7 * cm, 1.0 * cm, "Iluminar para Proteger | Estudo de Caso Vila Velha (ES)")
        canvas.drawRightString(A4[0] - 1.7 * cm, 1.0 * cm, f"Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()

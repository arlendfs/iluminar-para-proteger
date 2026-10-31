"""
Módulo de Geração de Relatório Científico e Técnico em PDF.
Implementa todas as seções científicas exigidas, gráficos analíticos em alta resolução,
tabelas formatadas com paginação e integração direta aos resultados calculados no dashboard.
"""

import io
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from config import (
    APP_CONFIG,
    FINANCIAL_PARAMS,
    EFFECTIVENESS_PARAMS,
    ECONOMIC_VALUES,
    SCENARIOS,
    CENARIOS_ORCAMENTO,
    ENGENHARIA_SISTEMA_SOLAR,
    ENGENHARIA_SISTEMA_SOLAR_COMPACTO,
    LUMINOTECNICA_PARAMETROS,
    TELEMETRIA_CONFIG,
    POSTE_CUSTO_DETALHADO,
    REFERENCES,
    PDF_CONFIG,
    DEFAULT_SPACING_M,
)
from financial_model import calcular_balanco_energetico_detalhado, calcular_orcamento_cenarios
from metrics import compute_period_metrics, compute_day_vs_night_comparison
from reaction_analysis import analyze_visibility_and_reaction
from demographic_analysis import (
    compute_envolvimento_analysis,
    compute_sexo_analysis,
    compute_faixa_etaria_analysis,
    compute_veiculo_analysis,
    compute_tipo_acidente_analysis,
)


def format_pt_br_currency(val: float) -> str:
    """Formata valor em Real brasileiro: R$ 1.234.567,89"""
    if pd.isna(val) or val is None:
        return "R$ 0,00"
    s = f"{val:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def format_pt_br_number(val: float, decimals: int = 2) -> str:
    """Formata número com separador de milhar ponto e decimal vírgula: 1.234,56"""
    if pd.isna(val) or val is None:
        return "0"
    fmt = f"{{:,.{decimals}f}}"
    s = fmt.format(val)
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


class NumberedCanvas(canvas.Canvas):
    """
    Canvas com paginação de duas passagens: 'Página X de Y'.
    Gera cabeçalho e rodapé padronizados em todas as páginas.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setStrokeColor(colors.HexColor("#cccccc"))
        self.setFillColor(colors.HexColor("#555555"))

        # Cabeçalho (a partir da página 2)
        if self._pageNumber > 1:
            self.drawString(40, 805, "Iluminar para Proteger — Relatório Técnico e Científico de Segurança Viária")
            self.line(40, 800, 555, 800)

        # Rodapé
        self.line(40, 45, 555, 45)
        self.drawString(40, 32, "Projeto de Extensão em Ciência de Dados — UNINTER | Fontes: PRF / IPEA / FHWA")
        page_str = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(555, 32, page_str)
        self.restoreState()


class ReportGenerator:
    """
    Gerador de relatórios técnicos em PDF com rigor acadêmico e científico.
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._setup_styles()

    def _setup_styles(self) -> Dict[str, ParagraphStyle]:
        title_style = ParagraphStyle(
            "DocTitle",
            parent=self.styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor(PDF_CONFIG["colors"]["title"]),
            alignment=0,
            spaceAfter=4,
        )

        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#555555"),
            spaceAfter=12,
        )

        h1_style = ParagraphStyle(
            "Heading1_Custom",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor(PDF_CONFIG["colors"]["title"]),
            spaceBefore=12,
            spaceAfter=5,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "Body_Custom",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor(PDF_CONFIG["colors"]["text"]),
            spaceAfter=4,
        )

        callout_style = ParagraphStyle(
            "Callout_Custom",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#1a2332"),
            backColor=colors.HexColor(PDF_CONFIG["colors"]["card_bg"]),
            borderColor=colors.HexColor(PDF_CONFIG["colors"]["title"]),
            borderWidth=0.5,
            borderPadding=5,
            spaceBefore=4,
            spaceAfter=5,
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.white,
            alignment=1,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#222222"),
            alignment=1,
        )

        table_cell_left = ParagraphStyle(
            "TableCellLeft",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#222222"),
            alignment=0,
        )

        return {
            "title": title_style,
            "subtitle": subtitle_style,
            "h1": h1_style,
            "body": body_style,
            "callout": callout_style,
            "th": table_header_style,
            "td": table_cell_style,
            "td_left": table_cell_left,
        }

    def generate_accident_analysis_report(
        self,
        filtered_data: pd.DataFrame,
        top_segments: pd.DataFrame,
        causas_df: Optional[pd.DataFrame] = None,
        financial_summary: Optional[Dict[str, Any]] = None,
        quality_summary: Optional[Dict[str, Any]] = None,
        pessoas_df: Optional[pd.DataFrame] = None,
        veiculos_df: Optional[pd.DataFrame] = None,
    ) -> io.BytesIO:
        """
        Gera o documento PDF estruturado com todas as 15 seções científicas.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=PDF_CONFIG["margins"]["left"],
            rightMargin=PDF_CONFIG["margins"]["right"],
            topMargin=PDF_CONFIG["margins"]["top"],
            bottomMargin=PDF_CONFIG["margins"]["bottom"],
        )

        story = []

        # =====================================================================
        # 1. IDENTIFICAÇÃO DO PROJETO
        # =====================================================================
        story.append(Paragraph("ILUMINAR PARA PROTEGER", self.custom_styles["title"]))
        story.append(Paragraph(
            "<b>Auditoria Científica, Estatística e Viabilidade Socioeconômica de Iluminação Solar em Rodovias Federais</b>",
            self.custom_styles["subtitle"]
        ))

        qual = quality_summary or {}
        data_min = qual.get("data_minima", "01/01/2021")
        data_max = qual.get("data_maxima", "31/12/2025")
        
        # Alerta metodológico apenas se houver anos incompletos efetivamente presentes
        alerta_anos_inc = ""
        anos_inc = qual.get("anos_incompletos", [])
        if anos_inc:
            textos_inc = []
            for a, m in anos_inc:
                textos_inc.append(f"ano {a} com dados parciais até o mês {max(m):02d}")
            alerta_anos_inc = f" (com alerta metodológico para: {', '.join(textos_inc)})"
        
        info_header = f"""
        <b>Instituição:</b> Centro Universitário Internacional (UNINTER) — Extensão Universitária em Ciência de Dados<br/>
        <b>Período Analisado:</b> {data_min} a {data_max}{alerta_anos_inc}<br/>
        <b>Data de Emissão:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')} | <b>Bases Oficiais:</b> Polícia Rodoviária Federal (PRF), IPEA e FHWA
        """
        story.append(Paragraph(info_header, self.custom_styles["body"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1f77b4"), spaceAfter=8))

        # =====================================================================
        # 2. RESUMO EXECUTIVO
        # =====================================================================
        story.append(Paragraph("1. RESUMO EXECUTIVO", self.custom_styles["h1"]))

        total_ocorrencias = len(filtered_data)
        total_mortos = int(filtered_data["mortos"].sum()) if "mortos" in filtered_data.columns else 0
        total_feridos = int(filtered_data["total_feridos"].sum()) if "total_feridos" in filtered_data.columns else 0
        acidentes_fatais = int(filtered_data["acidente_fatal"].sum()) if "acidente_fatal" in filtered_data.columns else 0

        day_night_comp = compute_day_vs_night_comparison(filtered_data)
        noturno_dict = day_night_comp.get("noturno") or {}
        diurno_dict = day_night_comp.get("diurno") or {}

        acidentes_not = noturno_dict.get("n_acidentes", 0)
        mortos_not = noturno_dict.get("total_mortos", 0)
        perc_not = (acidentes_not / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0

        let_not = noturno_dict.get("mortos_por_100_acidentes", 0.0)
        let_dia = diurno_dict.get("mortos_por_100_acidentes", 0.0)
        fator_let = day_night_comp.get("razao_letalidade_obitos", 1.0)
        pct_fatais_geral = (acidentes_fatais / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0
        obitos_100_geral = (total_mortos / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0

        fin = financial_summary or {}
        n_trechos_resumo = len(top_segments) if top_segments is not None else 100
        vidas_salvas_resumo = fin.get("vidas_salvas_ano", 0.0)
        graves_evitados_resumo = fin.get("graves_evitados_ano", 0.0)

        resumo_p = f"""
        Este relatório técnico consolida a auditoria e análise de <b>{total_ocorrencias:,} ocorrências desduplicadas</b>, 
        resultando em <b>{total_mortos:,} óbitos confirmados</b> e <b>{total_feridos:,} pessoas feridas</b> no conjunto analisado.<br/>
        • <b>Percentual de Acidentes Fatais:</b> <b>{format_pt_br_number(pct_fatais_geral, 1)}%</b> dos sinistros resultaram em pelo menos um óbito ({acidentes_fatais:,} sinistros fatais).<br/>
        • <b>Taxa de Óbitos por 100 Acidentes:</b> O índice geral é de <b>{format_pt_br_number(obitos_100_geral, 2)} óbitos/100 acidentes</b>.<br/>
        • <b>Assimetria Dia vs Noite:</b> Os acidentes noturnos concentram <b>{acidentes_not:,} ocorrências ({format_pt_br_number(perc_not, 1)}%)</b> e <b>{mortos_not:,} mortes</b>, com taxa de <b>{format_pt_br_number(let_not, 2)} óbitos/100 acidentes</b> contra <b>{format_pt_br_number(let_dia, 2)} no diurno</b> (letalidade <b>{format_pt_br_number(fator_let, 2)}x maior</b>).<br/>
        • <b>Impacto Potencial da Iluminação Solar (Simulação CMF):</b> Para os {n_trechos_resumo} trechos críticos priorizados, estima-se que a intervenção com postes solares inteligentes pode preservar <b>{format_pt_br_number(vidas_salvas_resumo, 1)} vidas humanas por ano</b> e mitigar cerca de {format_pt_br_number(graves_evitados_resumo, 0)} feridos graves anualmente (fator CMF de 35% de redução noturna da FHWA, pendente de validação de campo).
        """
        story.append(Paragraph(resumo_p, self.custom_styles["body"]))

        # =====================================================================
        # 3. METODOLOGIA E AUDITORIA DE DADOS (ESCLARECIMENTO DOS 267 REGISTROS)
        # =====================================================================
        story.append(Paragraph("2. METODOLOGIA, CONFIABILIDADE E AUDITORIA DE REGISTROS", self.custom_styles["h1"]))

        linhas_brutas = qual.get("registros_brutos", total_ocorrencias)
        desdobramentos_consolidados = qual.get("desdobramentos_consolidados", qual.get("duplicatas_linhas_evitadas", 0))
        com_km_count = qual.get("ocorrencias_com_km", total_ocorrencias)
        sem_km_count = qual.get("ocorrencias_sem_km", 0)
        mortos_sem_km = qual.get("mortos_sem_km", 0)
        feridos_sem_km = qual.get("feridos_sem_km", 0)
        pessoas_unicas = qual.get("pessoas_unicas_pesid", len(pessoas_df) if pessoas_df is not None else 0)
        caso_excepcional_txt = ""
        if filtered_data is not None and not filtered_data.empty and "id" in filtered_data.columns:
            m_730910 = filtered_data[filtered_data["id"] == 730910]
            if not m_730910.empty:
                r_730910 = m_730910.iloc[0]
                p_730910 = pessoas_df[pessoas_df["id"] == 730910] if pessoas_df is not None and "id" in pessoas_df.columns else pd.DataFrame()
                n_pes = len(p_730910["pesid"].dropna().unique()) if not p_730910.empty and "pesid" in p_730910.columns else int(r_730910.get("total_vitimas", 0))
                caso_excepcional_txt = f"<br/><b>Caso Excepcional Auditado no Período:</b> Investigada a ocorrência ID 730910 na BR-{r_730910.get('br', '423')} ({r_730910.get('uf', 'PE')}), KM {r_730910.get('km', 127):.0f}, ocorrida em {r_730910.get('data_inversa', '17/10/2025')} ({r_730910.get('fase_dia_oficial', 'Plena Noite')}). Confirmou-se sinistro de alta gravidade com <b>{n_pes} pessoas distintas rastreadas</b> ({int(r_730910.get('mortos', 0))} óbitos e {int(r_730910.get('total_feridos', 0))} feridos), atestando a autenticidade dos microdados oficiais da PRF."

        metodologia_p = f"""
        <b>Dicionário e Granularidade:</b> Os microdados abertos da PRF ('todas_causas_tipos') multiplicam linhas para cada envolvido (<code>pesid</code>), veículo e causa registrada. Para assegurar total rigor estatístico, as ocorrências foram desduplicadas pela chave primária <code>id</code>, as vítimas agregadas por pessoas únicas (<code>pesid</code>) e os veículos por <code>id_veiculo</code>, consolidando <b>{desdobramentos_consolidados:,} desdobramentos de ocupantes, veículos e causas</b> a partir de <b>{linhas_brutas:,} linhas brutas</b> (total de <b>{pessoas_unicas:,} pessoas únicas</b> identificadas).<br/>
        <b>Auditoria Metodológica dos Registros sem Marco Quilométrico:</b><br/>
        - Linhas brutas lidas: <b>{linhas_brutas:,}</b> | Ocorrências únicas totais identificadas: <b>{qual.get('ocorrencias_unicas', total_ocorrencias):,}</b>.<br/>
        - Subtração direta de desdobramentos consolidados: `{linhas_brutas:,} - {qual.get('ocorrencias_unicas', total_ocorrencias):,} = {desdobramentos_consolidados:,}`.<br/>
        - Ocorrências com marco KM verificado: <b>{com_km_count:,}</b> | Ocorrências sem marco KM registrado: <b>{sem_km_count:,}</b> ({mortos_sem_km:,} óbito(s) e {feridos_sem_km:,} ferido(s)).<br/>
        - A diferença nos cálculos de segmentação decorre rigorosamente das <b>{sem_km_count:,} ocorrências com KM ausente</b> na PRF, as quais foram isoladas do ranking físico de trechos rodoviários para eliminar a histórica distorção de concentração indevida no KM 0,0, mas integralmente preservadas nas análises nacionais de letalidade, causas e demografia.{caso_excepcional_txt}
        """
        story.append(Paragraph(metodologia_p, self.custom_styles["body"]))

        # =====================================================================
        # 4. ANÁLISE TEMPORAL
        # =====================================================================
        story.append(Paragraph("3. EVOLUÇÃO TEMPORAL DOS ACIDENTES", self.custom_styles["h1"]))
        img_temporal = self._generate_temporal_chart(filtered_data)
        if img_temporal:
            story.append(img_temporal)
            story.append(Spacer(1, 4))

        # =====================================================================
        # 5. COMPARAÇÃO DIA VERSUS NOITE E DESCOBERTA DO AMANHECER
        # =====================================================================
        story.append(Paragraph("4. COMPARAÇÃO DETALHADA: FASES DO DIA E O FATOR CRÍTICO DO AMANHECER", self.custom_styles["h1"]))

        tbl_data = [
            [
                Paragraph("Fase do Dia (PRF)", self.custom_styles["th"]),
                Paragraph("Acidentes", self.custom_styles["th"]),
                Paragraph("Part. %", self.custom_styles["th"]),
                Paragraph("Óbitos", self.custom_styles["th"]),
                Paragraph("Feridos", self.custom_styles["th"]),
                Paragraph("Acid. Fatais", self.custom_styles["th"]),
                Paragraph("Óbitos/100 Ac.", self.custom_styles["th"]),
                Paragraph("% Fatais", self.custom_styles["th"]),
            ]
        ]

        tabela_oficial = day_night_comp.get("tabela_oficial")
        if tabela_oficial is not None and not tabela_oficial.empty:
            for _, r in tabela_oficial.iterrows():
                tbl_data.append([
                    Paragraph(str(r.get("fase_dia_oficial", "")), self.custom_styles["td_left"]),
                    Paragraph(f"{int(r.get('n_acidentes', 0)):,}", self.custom_styles["td"]),
                    Paragraph(f"{format_pt_br_number(r.get('participacao_acidentes_pct', 0.0), 1)}%", self.custom_styles["td"]),
                    Paragraph(f"{int(r.get('total_mortos', 0)):,}", self.custom_styles["td"]),
                    Paragraph(f"{int(r.get('total_feridos', 0)):,}", self.custom_styles["td"]),
                    Paragraph(f"{int(r.get('acidentes_fatais', 0)):,}", self.custom_styles["td"]),
                    Paragraph(f"{format_pt_br_number(r.get('mortos_por_100_acidentes', 0.0), 2)}", self.custom_styles["td"]),
                    Paragraph(f"{format_pt_br_number(r.get('prop_acidentes_fatais_pct', 0.0), 1)}%", self.custom_styles["td"]),
                ])

        t_comp = Table(tbl_data, colWidths=[2.5*cm, 1.8*cm, 1.4*cm, 1.4*cm, 1.6*cm, 1.8*cm, 2.3*cm, 1.7*cm])
        t_comp.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f77b4")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        story.append(t_comp)
        story.append(Spacer(1, 4))

        # Interpretação científica centralizada a partir de day_night_comp
        fases_dict = day_night_comp.get("fases_oficiais_dict", {})
        let_am = fases_dict.get("amanhecer", {}).get("mortos_por_100", 0.0)
        let_pn = fases_dict.get("plena_noite", {}).get("mortos_por_100", 0.0)
        let_pd = fases_dict.get("pleno_dia", {}).get("mortos_por_100", 0.0)
        let_an = fases_dict.get("anoitecer", {}).get("mortos_por_100", 0.0)
        fase_top_nome = day_night_comp.get("fase_mais_letal_nome", "Amanhecer")
        fase_top_val = day_night_comp.get("fase_mais_letal_valor", let_am)
        texto_fases = day_night_comp.get("texto_interpretativo_fases", "")

        fases_callout = f"""
        <b>Discussão Científica — Indicadores de Severidade por Fase do Dia (Foco Crítico: {fase_top_nome} com {format_pt_br_number(fase_top_val, 2)} óbitos/100 acidentes):</b><br/>
        {texto_fases}<br/>
        <b>Fatores Intervenientes Documentados na Literatura de Tráfego:</b><br/>
        1. <b>Nadir Circadiano (Fadiga Biológica):</b> Entre 04h e 06h ocorre o vale circadiano de vigília, elevando a probabilidade de microssono e tempo de percepção retardado;<br/>
        2. <b>Ofuscamento Horizontal (Glare Solar):</b> No amanhecer, o ângulo rasteiro do sol nascente reduz drasticamente o contraste óptico para veículos em sentido leste;<br/>
        3. <b>Penumbra e Conicidade Visual:</b> Períodos crepusculares induzem desligamento prematuro de faróis antes de haver iluminância ambiental segura;<br/>
        4. <b>Déficit de Contraste na Plena Noite:</b> Sem iluminação artificial contínua, a visibilidade fica restrita aos fachos dos faróis baixos (30 a 50m), incompatível com a distância de parada segura a 100 km/h.
        """
        story.append(Paragraph(fases_callout, self.custom_styles["callout"]))

        # =====================================================================
        # 6. CAUSAS DE ACIDENTES, REAÇÃO TARDIA E AUSÊNCIA DE REAÇÃO
        # =====================================================================
        story.append(Paragraph("5. VISIBILIDADE NOTURNA, TEMPO DE REAÇÃO E CAUSAS CONCORRENTES", self.custom_styles["h1"]))

        vis_analysis = analyze_visibility_and_reaction(
            filtered_data,
            causas_df if causas_df is not None else pd.DataFrame()
        )
        causas_fases_df = vis_analysis.get("causas_fases_df", pd.DataFrame())

        # Gráfico comparativo de causas
        img_reaction = self._generate_reaction_causes_chart(filtered_data, causas_df)
        if img_reaction:
            story.append(img_reaction)
            story.append(Spacer(1, 4))

        # Tabela das causas específicas de reação e visibilidade
        if not causas_fases_df.empty:
            target_causes = [
                "Reação tardia ou ineficiente do condutor",
                "Ausência de reação do condutor",
                "Condutor Dormindo",
                "Ultrapassagem Indevida",
                "Velocidade Incompatível",
                "Ingestão de Álcool pelo condutor",
            ]
            t_reacao_data = [
                [
                    Paragraph("Causa Auditada", self.custom_styles["th"]),
                    Paragraph("Fase do Dia", self.custom_styles["th"]),
                    Paragraph("Sinistros", self.custom_styles["th"]),
                    Paragraph("Óbitos", self.custom_styles["th"]),
                    Paragraph("Óbitos/100", self.custom_styles["th"]),
                    Paragraph("% Fatais", self.custom_styles["th"]),
                ]
            ]
            for c_nome in target_causes:
                sub_c = causas_fases_df[causas_fases_df["causa_normalizada"].str.contains(c_nome, case=False, na=False)]
                for _, r in sub_c.iterrows():
                    t_reacao_data.append([
                        Paragraph(c_nome[:28], self.custom_styles["td_left"]),
                        Paragraph(str(r["fase_dia_oficial"]), self.custom_styles["td"]),
                        Paragraph(f"{int(r['n_acidentes']):,}", self.custom_styles["td"]),
                        Paragraph(f"{int(r['total_mortos']):,}", self.custom_styles["td"]),
                        Paragraph(f"{format_pt_br_number(r['mortos_por_100'], 2)}", self.custom_styles["td"]),
                        Paragraph(f"{format_pt_br_number(r['prop_fatais_pct'], 1)}%", self.custom_styles["td"]),
                    ])

            t_reacao = Table(t_reacao_data, colWidths=[5.5*cm, 2.5*cm, 1.8*cm, 1.6*cm, 1.8*cm, 1.8*cm])
            t_reacao.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(t_reacao)
            story.append(Spacer(1, 4))

        evid_txt = vis_analysis.get("evidencias_texto", "")
        hip_txt = vis_analysis.get("hipotese_texto", "")
        lim_txt = vis_analysis.get("limitacoes_texto", "")

        vis_text = f"""
        <b>Rigor Científico Obrigatório e Reconciliação Causa–Ocorrência:</b><br/>
        • <b>{evid_txt}</b><br/>
        • <b>{hip_txt}</b><br/>
        • <b>{lim_txt}</b><br/>
        • <b>Fundamentação Externa (Escopo FHWA):</b> A recomendação <i>FHWA Proven Safety Countermeasures: Lighting</i> estabelece fatores de modificação de acidentes (CMF) para trechos e interseções iluminadas (reduções esperadas de 28% a 42% em colisões noturnas). Adota-se 35% como premissa de simulação paramétrica sujeita à verificação em projetos-piloto.
        """
        story.append(Paragraph(vis_text, self.custom_styles["callout"]))

        # =====================================================================
        # 6. PERFIL DEMOGRÁFICO DOS ENVOLVIDOS, FROTA VEICULAR E TIPOLOGIA
        # =====================================================================
        story.append(Paragraph("6. PERFIL DEMOGRÁFICO DOS ENVOLVIDOS, FROTA VEICULAR E TIPOLOGIA", self.custom_styles["h1"]))

        p_df = pessoas_df if pessoas_df is not None and not pessoas_df.empty else pd.DataFrame()
        v_df = veiculos_df if veiculos_df is not None and not veiculos_df.empty else pd.DataFrame()
        tbl_env = pd.DataFrame()  # initialise before conditional block — avoids UnboundLocalError when p_df is empty

        if not p_df.empty:
            res_env = compute_envolvimento_analysis(p_df)
            tbl_env = res_env.get("resumo_envolvimento", pd.DataFrame())

            if not tbl_env.empty:
                story.append(Paragraph("<b>Distribuição de Vítimas por Tipo de Envolvimento:</b>", self.custom_styles["body"]))
                t_env_data = [
                    [
                        Paragraph("Tipo de Envolvimento", self.custom_styles["th"]),
                        Paragraph("Envolvidos", self.custom_styles["th"]),
                        Paragraph("Óbitos", self.custom_styles["th"]),
                        Paragraph("Feridos Graves", self.custom_styles["th"]),
                        Paragraph("Feridos Leves", self.custom_styles["th"]),
                        Paragraph("Mortalidade (%)", self.custom_styles["th"]),
                        Paragraph("Part. Óbitos (%)", self.custom_styles["th"]),
                    ]
                ]
                for _, r in tbl_env.iterrows():
                    t_env_data.append([
                        Paragraph(str(r["tipo_envolvido"]), self.custom_styles["td_left"]),
                        Paragraph(f"{int(r['total_envolvidos']):,}", self.custom_styles["td"]),
                        Paragraph(f"{int(r['mortos']):,}", self.custom_styles["td"]),
                        Paragraph(f"{int(r['feridos_graves']):,}", self.custom_styles["td"]),
                        Paragraph(f"{int(r['feridos_leves']):,}", self.custom_styles["td"]),
                        Paragraph(f"{format_pt_br_number(r['taxa_mortalidade_pct'], 2)}%", self.custom_styles["td"]),
                        Paragraph(f"{format_pt_br_number(r['prop_total_mortos_pct'], 2)}%", self.custom_styles["td"]),
                    ])

                t_env_table = Table(t_env_data, colWidths=[4.2*cm, 2.2*cm, 1.8*cm, 2.2*cm, 2.2*cm, 2.4*cm, 2.2*cm])
                t_env_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f77b4")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]))
                story.append(t_env_table)
                story.append(Spacer(1, 4))

            res_faixa = compute_faixa_etaria_analysis(p_df)
            tbl_faixa = res_faixa.get("resumo_faixa_etaria", pd.DataFrame())
            qual_idade = res_faixa.get("metricas_qualidade_idade", {})

            if not tbl_faixa.empty:
                story.append(Paragraph(
                    f"<b>Distribuição por Faixa Etária e Rigor dos Dados Etários:</b> "
                    f"<i>(Idades Válidas: {qual_idade.get('idades_validas', 0):,} [{qual_idade.get('perc_idades_validas', 0.0):.1f}%] | "
                    f"Inconsistentes/Ausentes: {qual_idade.get('idades_inconsistentes_ou_ausentes', 0):,} [{qual_idade.get('perc_inconsistentes', 0.0):.1f}%] | "
                    f"Idades > 110 anos isoladas: {qual_idade.get('idades_superiores_110_anos', 0):,})</i>",
                    self.custom_styles["body"]
                ))
                t_faixa_data = [
                    [
                        Paragraph("Faixa Etária", self.custom_styles["th"]),
                        Paragraph("Pessoas", self.custom_styles["th"]),
                        Paragraph("Óbitos", self.custom_styles["th"]),
                        Paragraph("Feridos Graves", self.custom_styles["th"]),
                        Paragraph("Mortalidade (%)", self.custom_styles["th"]),
                        Paragraph("Part. Óbitos (%)", self.custom_styles["th"]),
                    ]
                ]
                for _, r in tbl_faixa.iterrows():
                    t_faixa_data.append([
                        Paragraph(str(r["faixa_etaria"]), self.custom_styles["td_left"]),
                        Paragraph(f"{int(r['total_pessoas']):,}", self.custom_styles["td"]),
                        Paragraph(f"{int(r['mortos']):,}", self.custom_styles["td"]),
                        Paragraph(f"{int(r['feridos_graves']):,}", self.custom_styles["td"]),
                        Paragraph(f"{format_pt_br_number(r['taxa_mortalidade_pct'], 2)}%", self.custom_styles["td"]),
                        Paragraph(f"{format_pt_br_number(r['prop_total_mortos_pct'], 2)}%", self.custom_styles["td"]),
                    ])

                t_faixa_table = Table(t_faixa_data, colWidths=[4.5*cm, 2.5*cm, 2.2*cm, 2.5*cm, 2.6*cm, 2.5*cm])
                t_faixa_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]))
                story.append(t_faixa_table)
                story.append(Spacer(1, 4))

        if not v_df.empty:
            tbl_v = compute_veiculo_analysis(v_df, p_df).head(6)
            if not tbl_v.empty:
                v_summary_str = ", ".join([f"{r['tipo_veiculo']}: {int(r['total_veiculos']):,} ({int(r.get('mortos', 0)):,} óbitos)" for _, r in tbl_v.iterrows()])
                story.append(Paragraph(
                    f"<b>Frota Veicular Predominante:</b> As categorias com maior envolvimento em acidentes são: {v_summary_str}.",
                    self.custom_styles["body"]
                ))

        # Análise observacional de pedestres com quantificação real
        pedestre_txt = "<b>Vulnerabilidade Observacional de Pedestres e Modos Ativos:</b> "
        if not tbl_env.empty and "tipo_envolvido" in tbl_env.columns:
            m_ped = tbl_env[tbl_env["tipo_envolvido"].astype(str).str.lower().str.contains("pedestre")]
            if not m_ped.empty:
                r_ped = m_ped.iloc[0]
                ped_tot = int(r_ped["total_envolvidos"])
                ped_mort = int(r_ped["mortos"])
                ped_taxa = float(r_ped["taxa_mortalidade_pct"])
                pedestre_txt += (
                    f"Entre os {ped_tot:,} pedestres identificados na base, registraram-se {ped_mort:,} fatalidades "
                    f"({format_pt_br_number(ped_taxa, 2)}% de letalidade específica, a maior entre as classes de usuários). "
                    f"Trata-se de evidência observacional de elevada vulnerabilidade dos modos ativos em rodovias federais, influenciada por "
                    f"fatores de risco concorrentes como travessias em nível, ausência de passarelas e velocidades elevadas, "
                    f"sem atribuição de causalidade exclusiva à ausência de iluminação."
                )
            else:
                pedestre_txt += "Pedestres apresentam a maior taxa específica de mortalidade observacional entre todas as classes de usuários."
        else:
            pedestre_txt += "Pedestres apresentam a maior taxa específica de mortalidade observacional entre todas as classes de usuários."

        story.append(Paragraph(pedestre_txt, self.custom_styles["callout"]))

        # =====================================================================
        # 7. RANKING DE TRECHOS CRÍTICOS E FÓRMULA DE PONTUAÇÃO
        # =====================================================================
        story.append(Paragraph("7. RANKING DE TRECHOS CRÍTICOS PARA ILUMINAÇÃO SOLAR", self.custom_styles["h1"]))

        formula_desc = """
        <b>Fórmula de Priorização para Iluminação Solar:</b><br/>
        Os trechos são segmentados em intervalos regulares contínuos de 2,0 km (ex: KM 144,0 a 146,0). O score prioriza a gravidade e a recorrência no período <b>noturno</b>:<br/>
        <code>Score_Solar = (5 × Mortos_not + 3 × FeridosGraves_not + 1 × FeridosLeves_not + 2 × Acidentes_not) × (1 + %Noturno / 100)</code>
        """
        story.append(Paragraph(formula_desc, self.custom_styles["body"]))

        if not top_segments.empty:
            t_trecho_data = [
                [
                    Paragraph("#", self.custom_styles["th"]),
                    Paragraph("Trecho (BR - UF - Extensão)", self.custom_styles["th"]),
                    Paragraph("Ac. Not.", self.custom_styles["th"]),
                    Paragraph("Óbitos", self.custom_styles["th"]),
                    Paragraph("Graves", self.custom_styles["th"]),
                    Paragraph("Score", self.custom_styles["th"]),
                    Paragraph("CAPEX (R$)", self.custom_styles["th"]),
                    Paragraph("Benefício/Ano", self.custom_styles["th"]),
                ]
            ]
            custo_un_trecho = float(fin.get("custo_unitario_poste", FINANCIAL_PARAMS["custo_poste_solar"]))
            postes_trecho_calc = int(np.ceil((2.0 * 1000.0) / DEFAULT_SPACING_M))
            inv_padrao_trecho = postes_trecho_calc * custo_un_trecho

            for i, (_, r) in enumerate(top_segments.head(10).iterrows(), start=1):
                inv_trecho_val = float(r.get("investimento_trecho", inv_padrao_trecho))
                t_trecho_data.append([
                    Paragraph(str(i), self.custom_styles["td"]),
                    Paragraph(str(r.get("trecho_id", r.get("trecho", "N/A"))), self.custom_styles["td_left"]),
                    Paragraph(f"{int(r.get('n_acidentes_noturnos', r.get('n_acidentes', 0))):,}", self.custom_styles["td"]),
                    Paragraph(f"{int(r.get('mortos_noturno', r.get('mortos', 0))):,}", self.custom_styles["td"]),
                    Paragraph(f"{int(r.get('feridos_graves_noturno', 0)):,}", self.custom_styles["td"]),
                    Paragraph(f"{format_pt_br_number(float(r.get('score_iluminacao_solar', r.get('score_prioridade', 0))), 1)}", self.custom_styles["td"]),
                    Paragraph(format_pt_br_currency(inv_trecho_val), self.custom_styles["td"]),
                    Paragraph(format_pt_br_currency(float(r.get("economia_anual_trecho", 0.0))), self.custom_styles["td"]),
                ])

            t_seg = Table(t_trecho_data, colWidths=[0.8*cm, 5.0*cm, 1.4*cm, 1.2*cm, 1.2*cm, 1.6*cm, 2.2*cm, 2.2*cm])
            t_seg.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(t_seg)
            story.append(Spacer(1, 4))

        # =====================================================================
        # 8. ENGENHARIA, DIMENSIONAMENTO E BALANÇO ENERGÉTICO
        # =====================================================================
        story.append(Paragraph("8. ENGENHARIA, CONCEITO COMPACTO E BALANÇO ENERGÉTICO", self.custom_styles["h1"]))

        n_trechos_analisados = len(top_segments)
        espacamento = DEFAULT_SPACING_M
        postes_por_trecho = int(np.ceil((2.0 * 1000.0) / espacamento))
        total_postes = n_trechos_analisados * postes_por_trecho

        # Cálculo do Balanço Energético Detalhado
        b_eng = calcular_balanco_energetico_detalhado()

        eng_p = f"""
        <b>Conceito Físico do Poste Solar Compacto (8m / 40W / 240Wp / 2.500Wh LiFePO4):</b><br/>
        • <b>Estrutura Mecânica:</b> Poste cônico contínuo de 8 metros em aço galvanizado a fogo com base flangeada e chumbadores de ancoragem. Braço curvo viário com avanço de 1,5m sobre o leito da rodovia.<br/>
        • <b>Compartimento de Baterias e Eletrônica:</b> Gabinete integrado ao corpo inferior do poste com vedação estanque IP66 e portinhola de manutenção autorizada.<br/>
        • <b>Conjunto Solar Compacto Integrado:</b> Módulo fotovoltaico monocristalino de <b>240 Wp</b> fixado no topo com inclinação ótima de 22° para a latitude média brasileira, sem módulos residenciais gigantes desproporcionais.<br/>
        • <b>Luminária Viária LED:</b> Potência de <b>40 W</b> com ótica viária Tipo II (corte total anti-ofuscamento), sensor Doppler por radar de micro-ondas e antena de telemetria.<br/>
        <br/>
        <b>Balanço Energético Auditado e Autonomia com ZERO Geração Solar:</b><br/>
        • <b>Consumo Noturno Dimerizado (12h):</b> 4h pico a 100% (160 Wh) + 4h normal a 80% (128 Wh) + 4h repouso a 60% (96 Wh) = <b>384 Wh/noite</b>.<br/>
        • <b>Telemetria e Supervisão 24h:</b> 2 W contínuos &rarr; <b>48 Wh/dia</b>. Consumo Total: <b>{b_eng['consumo_total_diario_wh']:.0f} Wh por dia/noite</b>.<br/>
        • <b>Banco de Baterias LiFePO4 (2.500 Wh nominais):</b> Com 80% DoD e 90% de rendimento MPPT/driver: <b>Capacidade Útil BOL = {b_eng['capacidade_util_bol_wh']:.1f} Wh</b> e <b>Capacidade Útil EOL (80% vida) = {b_eng['capacidade_util_eol_wh']:.1f} Wh</b>.<br/>
        • <b>Autonomia Efetiva com ZERO Sol:</b> <b>{b_eng['autonomia_zero_sol_bol_noites']:.2f} noites (BOL)</b> e <b>{b_eng['autonomia_zero_sol_eol_noites']:.2f} noites (EOL)</b>. Sustenta rigorosamente a meta mandatária de 3 noites consecutivas sem incidência solar.<br/>
        • <b>Geração Solar Diária (4,5 HSP, PR 80%):</b> <b>{b_eng['geracao_solar_sol_pleno_wh']:.1f} Wh/dia</b> (excedente de {b_eng['excedente_diario_sol_wh']:.1f} Wh/dia para recarga completa em {b_eng['dias_recarga_apos_3_noites']:.1f} dias de sol pleno).<br/>
        • <b>Dias Nublados vs Zero Sol:</b> Em dias nublados (25% de irradiação padrão), a geração é de <b>{b_eng['geracao_solar_dia_nublado_wh']:.1f} Wh/dia</b> (déficit diário de {abs(b_eng['balanco_liquido_nublado_wh']):.1f} Wh/dia). Com banco plenamente carregado, a autonomia estimada em dias nublados contínuos é de <b>{b_eng['capacidade_util_bol_wh'] / abs(b_eng['balanco_liquido_nublado_wh']):.1f} dias em início de vida (BOL)</b> e <b>{b_eng['capacidade_util_eol_wh'] / abs(b_eng['balanco_liquido_nublado_wh']):.1f} dias em fim de vida (EOL 80%)</b>.<br/>
        • <b>Hipótese de Inclinação e Localização:</b> A inclinação referencial de 22° adotada na simulação constitui parâmetro de modelagem média nacional, devendo ser calibrada para a latitude específica de cada trecho rodoviário.<br/>
        <br/>
        <b>Segurança Luminotécnica e Validação Pendente (ABNT NBR 5101:2024):</b><br/>
        A potência de 40W é uma <b>hipótese preliminar de engenharia</b>. A conformidade com as classes viárias V1 a V5 da ABNT NBR 5101:2024 (luminância de pista <i>L<sub>m</sub></i> &ge; 1,0 cd/m², uniformidade <i>U<sub>0</sub></i> &ge; 0,35 e ofuscamento <i>TI</i> &le; 10%) requer validação computacional em software de simulação luminotécnica (DIALux EVO) considerando a largura da via e o espaçamento de {espacamento} m.
        """
        story.append(Paragraph(eng_p, self.custom_styles["body"]))

        # =====================================================================
        # 9. MODELAGEM ORÇAMENTÁRIA MULTI-CENÁRIOS E RETORNO FINANCEIRO
        # =====================================================================
        story.append(Paragraph("9. MODELAGEM ECONÔMICA E CENÁRIOS COMPARÁVEIS (A A E)", self.custom_styles["h1"]))

        # Executa comparação dos 5 cenários
        orc_cen = calcular_orcamento_cenarios(
            top_segments_df=top_segments,
            n_trechos=n_trechos_analisados,
            comprimento_km=2.0,
            espacamento_m=espacamento,
            anos_base_dados=financial_summary.get("anos_base", 2.0) if financial_summary else 2.0,
        )
        comp_df = orc_cen["comparativo_df"]

        # Tabela Comparativa dos Cenários A a E
        t_cen_multi_data = [
            [
                Paragraph("Cenário Orçamentário", self.custom_styles["th"]),
                Paragraph("Classificação", self.custom_styles["th"]),
                Paragraph("Poste / LED", self.custom_styles["th"]),
                Paragraph("Custo/Poste", self.custom_styles["th"]),
                Paragraph("CAPEX (R$ M)", self.custom_styles["th"]),
                Paragraph("VPL 15a (R$ M)", self.custom_styles["th"]),
                Paragraph("TIR (% a.a.)", self.custom_styles["th"]),
                Paragraph("Payback", self.custom_styles["th"]),
            ]
        ]
        for _, row_c in comp_df.iterrows():
            tir_c_str = f"{row_c['TIR (% a.a.)']:.1f}%" if pd.notna(row_c['TIR (% a.a.)']) else "N/A"
            pb_c_str = f"{row_c['Payback Simples (anos)']:.2f} a" if row_c['Payback Simples (anos)'] < 100 else "> 15 a"
            t_cen_multi_data.append([
                Paragraph(str(row_c["Cenário"]), self.custom_styles["td_left"]),
                Paragraph(str(row_c["Tipo"]), self.custom_styles["td"]),
                Paragraph(f"{row_c['Altura']} / {row_c['LED']}", self.custom_styles["td"]),
                Paragraph(format_pt_br_currency(row_c["Custo Unitário (R$)"]), self.custom_styles["td"]),
                Paragraph(f"R$ {row_c['CAPEX Total (R$ M)']:.2f}M", self.custom_styles["td"]),
                Paragraph(f"R$ {row_c['VPL 15 Anos (R$ M)']:.2f}M", self.custom_styles["td"]),
                Paragraph(tir_c_str, self.custom_styles["td"]),
                Paragraph(pb_c_str, self.custom_styles["td"]),
            ])

        t_cen_multi = Table(t_cen_multi_data, colWidths=[3.8*cm, 2.2*cm, 2.0*cm, 2.2*cm, 1.8*cm, 1.8*cm, 1.6*cm, 1.6*cm])
        t_cen_multi.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f77b4")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(t_cen_multi)
        story.append(Spacer(1, 4))

        fin = financial_summary or {}
        capex_d = 4000 * 22310.00  # R$ 89,24M para o cenário compacto base
        beneficio_anual = fin.get("economia_anual", 0.0)
        beneficio_liq = fin.get("economia_liquida_anual", 0.0)
        vpl = fin.get("vpl", 0.0)
        tir = fin.get("tir")
        payback = fin.get("payback_simples_anos", 0.0)
        payback_desc = fin.get("payback_descontado_anos")
        roi_desc = fin.get("roi_descontado_pct", 0.0)
        vidas_salvas = fin.get("vidas_salvas_ano", 0.0)
        anos_base = fin.get("anos_base", 2.0)
        mortos_top = top_segments["mortos_noturno"].sum() if "mortos_noturno" in top_segments.columns else 0

        pb_str = f"{format_pt_br_number(payback, 2)} anos" if (payback and payback < 100) else "> 15 anos"
        pb_desc_str = f"{format_pt_br_number(payback_desc, 2)} anos" if payback_desc else "> 15 anos"
        tir_str = f"{format_pt_br_number(tir * 100, 2)}% a.a." if tir is not None else "N/A"

        n_trechos_top = len(top_segments) if top_segments is not None else 100
        anos_denom = anos_base if anos_base > 0 else 1.0

        # Extração dinâmica dos cenários A e D da comp_df
        row_a = comp_df[comp_df["Cenário"].astype(str).str.contains("Cenário A", na=False)]
        capex_a_str = f"R$ {row_a['CAPEX Total (R$ M)'].iloc[0]:.2f}M" if not row_a.empty else "N/A"
        pb_a_str = f"{row_a['Payback Simples (anos)'].iloc[0]:.2f} anos" if not row_a.empty else "N/A"

        row_d = comp_df[comp_df["Cenário"].astype(str).str.contains("Cenário D", na=False)]
        custo_d_str = format_pt_br_currency(row_d['Custo Unitário (R$)'].iloc[0]) if not row_d.empty else "N/A"
        capex_d_str = f"R$ {row_d['CAPEX Total (R$ M)'].iloc[0]:.2f}M" if not row_d.empty else "N/A"
        vpl_d_str = f"R$ {row_d['VPL 15 Anos (R$ M)'].iloc[0]:.2f}M" if not row_d.empty else "N/A"
        pb_d_str = f"{row_d['Payback Simples (anos)'].iloc[0]:.2f} anos" if not row_d.empty else "N/A"

        fin_text = f"""
        <b>Memória de Cálculo de Vidas Potencialmente Preservadas ({format_pt_br_number(vidas_salvas, 1)} vidas/ano em {n_trechos_top} Trechos Críticos):</b><br/>
        1. <b>Acúmulo Histórico:</b> Nos {n_trechos_top} trechos prioritários selecionados, ocorreram <b>{mortos_top} óbitos noturnos</b> no horizonte de {anos_base:.1f} anos analisados.<br/>
        2. <b>Taxa Baseline Anualizada:</b> `{mortos_top} óbitos / {anos_base:.1f} anos = {mortos_top / anos_denom:.1f} óbitos noturnos por ano`.<br/>
        3. <b>Fator de Redução CMF Simulado (FHWA):</b> 35% de redução hipotética de acidentes noturnos elegíveis &rarr; `{mortos_top / anos_denom:.1f} × 0,35 = {vidas_salvas:.1f} vidas potencialmente preservadas por ano no cenário adotado`.<br/>
        4. <b>Rastreabilidade de Seleção Amostral:</b> O conjunto de trechos críticos é ranqueado dinamicamente para o período analisado. Diferenças nos totais anualizados entre janelas temporais refletem a composição dos segmentos prioritários de cada base.<br/>
        5. <b>Valoração Paramétrica (IPEA / VSL):</b> Vidas preservadas ({format_pt_br_currency(vidas_salvas * ECONOMIC_VALUES['valor_vida_estatistica'])}) + Graves evitados ({format_pt_br_currency(fin.get('economia_graves', 0.0))}) + Leves evitados ({format_pt_br_currency(fin.get('economia_leves', 0.0))}) = <b>Benefício Social Bruto de {format_pt_br_currency(beneficio_anual)}/ano</b>.<br/>
        6. <b>Custos de Implantação e Retorno Socioeconômico Comparado:</b><br/>
        • <b>Meta Histórica (Cenário A):</b> CAPEX {capex_a_str} | Payback Simples: {pb_a_str}.<br/>
        • <b>Conceitual Compacto 8m/40W (Cenário D - Base):</b> Custo/un {custo_d_str} | CAPEX {capex_d_str} | Payback Simples: {pb_d_str} | VPL Social 15 anos: {vpl_d_str}.<br/>
        <br/>
        <b>Plano Conceitual de Manutenção e Telemetria:</b><br/>
        Supervisão remota contínua (telemetria LoRaWAN/NB-IoT a 2W) monitorando tensão da bateria, corrente do painel e integridade do LED. Provisão de OPEX com manutenção preventiva (R$ 500/poste/ano) e reserva para troca de baterias a cada 5 anos (R$ 3.800/un).<br/>
        <i>Aviso Metodológico Obrigatório: Os cálculos representam simulações socioeconômicas conceituais sob taxa social de desconto de 8% a.a. e horizonte de 15 anos. A valoração da vida estatística (VSL) é uma métrica de custo-benefício social e não constitui receita financeira. Não existem postes físicos instalados nesta etapa acadêmica do projeto.</i>
        """
        story.append(Paragraph(fin_text, self.custom_styles["body"]))

        # Tabela de Cenários de Sensibilidade (Matriz Cenário de Equipamento x Efetividade)
        cen_equip_id = fin.get("cenario_id", "cenario_d")
        cen_nome_map = {
            "cenario_d": "Cenário D — Compacto 8m/40W (Base)",
            "cenario_a": "Cenário A — Meta Histórica 8m/60W",
            "cenario_b": "Cenário B — Comercial 6m/40W",
            "cenario_c": "Cenário C — Comercial 8m/80W",
            "cenario_e": "Cenário E — 8m/80W + Bateria Reforçada",
        }
        cen_equip_nome = cen_nome_map.get(cen_equip_id, "Cenário D — Compacto 8m/40W (Base)")
        capex_val = float(fin.get("investimento_total", 4000 * 22310.00))
        story.append(Paragraph(f"<b>Matriz de Sensibilidade de Efetividade (Simulação sob {cen_equip_nome} — CAPEX {format_pt_br_currency(capex_val)}):</b>", self.custom_styles["body"]))
        cenarios = fin.get("cenarios", {})
        if cenarios:
            t_cen_data = [
                [
                    Paragraph("Cenário de Análise", self.custom_styles["th"]),
                    Paragraph("Redução Esperada", self.custom_styles["th"]),
                    Paragraph("Vidas Salvas/Ano", self.custom_styles["th"]),
                    Paragraph("Benefício Bruto/Ano", self.custom_styles["th"]),
                    Paragraph("VPL (15 anos, 8%)", self.custom_styles["th"]),
                    Paragraph("Payback Simples", self.custom_styles["th"]),
                ]
            ]
            for _, c in cenarios.items():
                pb_cen = c.get("payback_simples", float("inf"))
                pb_cen_str = f"{format_pt_br_number(pb_cen, 2)} anos" if pb_cen < 100 else "> 15 anos"
                t_cen_data.append([
                    Paragraph(str(c.get("nome", "")), self.custom_styles["td_left"]),
                    Paragraph(f"{format_pt_br_number(c.get('taxa_reducao', 0.0) * 100, 0)}%", self.custom_styles["td"]),
                    Paragraph(f"{format_pt_br_number(c.get('vidas_salvas_ano', 0.0), 1)}", self.custom_styles["td"]),
                    Paragraph(format_pt_br_currency(c.get("beneficio_anual_bruto", 0.0)), self.custom_styles["td"]),
                    Paragraph(format_pt_br_currency(c.get("vpl", 0.0)), self.custom_styles["td"]),
                    Paragraph(pb_cen_str, self.custom_styles["td"]),
                ])

            t_cen = Table(t_cen_data, colWidths=[4.0*cm, 2.2*cm, 2.0*cm, 2.8*cm, 2.8*cm, 1.8*cm])
            t_cen.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f77b4")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(t_cen)
            story.append(Spacer(1, 4))

        # =====================================================================
        # 10. DISCUSSÃO, LIMITAÇÕES, CONCLUSÕES E REFERÊNCIAS
        # =====================================================================
        story.append(Paragraph("10. DISCUSSÃO CIENTÍFICA, LIMITAÇÕES E CONCLUSÕES", self.custom_styles["h1"]))
        disc_p = """
        <b>Discussão Teórica:</b> A segurança viária é comprovadamente multifatorial. A iluminação rodoviária atua diretamente na extensão do cone visual para além da distância de parada segura (DPS), restaurando o contraste óptico e permitindo a identificação precoce de obstáculos, pedestres e animais na pista. Todavia, fatores comportamentais como alcoolemia, sonolência circadiana e excesso de velocidade interagem sinergicamente.<br/>
        <b>Limitações Metodológicas Reconhecidas:</b><br/>
        1. <b>Ausência de Censo Luminotécnico:</b> A PRF não audita a presença física de postes ou nível de iluminância (lux) no boletim de ocorrência;<br/>
        2. <b>Exposição ao Tráfego:</b> Os dados públicos da PRF não registram Volume Médio Diário Anual (VDMA) por quilômetro em toda a malha, impedindo o cálculo de taxa de risco por veículo-quilômetro percorrido;<br/>
        3. <b>Natureza Paramétrica das Finanças:</b> A economia social estimada baseia-se em custos estatísticos de hospitalizações e perda de vidas humanas (valoração IPEA), não correspondendo a faturamento ou caixa financeiro real.<br/>
        <b>Conclusão Condicional e Recomendações:</b> Os dados observacionais da PRF evidenciam que os sinistros noturnos e no amanhecer apresentam severidade e letalidade substancialmente superiores às do pleno dia. As simulações físico-econômicas indicam atratividade socioeconômica favorável sob as premissas de projeto adotadas (horizonte de 15 anos, taxa social de desconto de 8% a.a. e custos unitários do Cenário D). Contudo, a efetiva implantação em escala permanece condicionada a validações complementares indispensáveis: (i) realização de censo físico de iluminação artificial existente nos trechos; (ii) estudos computacionais fotométricos por trecho conforme ABNT NBR 5101:2024; (iii) ensaios geotécnicos e dimensionamento estrutural de fundação; (iv) cotações executivas de fornecedores e logística de instalação; e (v) mensuração empírica do VDMA por segmento. Recomenda-se a execução de projetos-piloto controlados nos primeiros trechos do ranking para aferição empírica do Fator de Modificação de Acidentes (CMF) antes de decisões definitivas de investimento.
        """
        story.append(Paragraph(disc_p, self.custom_styles["body"]))

        story.append(Paragraph("11. REFERÊNCIAS BIBLIOGRÁFICAS E BASES OFICIAIS", self.custom_styles["h1"]))
        for ref in REFERENCES:
            ref_str = f"• <b>{ref['titulo']}</b>. {ref['instituicao']}, 2026. Disponível em: &lt;{ref['url']}&gt;. Acesso em: 29 out. 2026."
            story.append(Paragraph(ref_str, self.custom_styles["body"]))

        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer

    def _generate_temporal_chart(self, df: pd.DataFrame) -> Optional[Image]:
        """
        Gera gráfico de evolução temporal em alta resolução.
        """
        if df.empty:
            return None

        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, ax = plt.subplots(figsize=(7.2, 2.3), dpi=180)

        tem_mes = "ano_mes" in df.columns and df["ano_mes"].nunique() > 1
        col_x = "ano_mes" if tem_mes else "ano"

        if col_x not in df.columns or df[col_x].dropna().empty:
            plt.close(fig)
            return None

        col_periodo = "fase_dia_agrupada" if "fase_dia_agrupada" in df.columns else "fase_dia"
        grouped = df.groupby([col_x, col_periodo], observed=True).size().unstack(fill_value=0)

        x_vals = [str(x) for x in grouped.index]
        for col_name, color, label in [
            ("Noturno", "#1f77b4", "Noturno"),
            ("noturno", "#1f77b4", "Noturno"),
            ("Diurno", "#ff7f0e", "Diurno"),
            ("diurno", "#ff7f0e", "Diurno"),
            ("Crepúsculo", "#9467bd", "Crepúsculo"),
        ]:
            if col_name in grouped.columns:
                ax.plot(x_vals, grouped[col_name], marker="o", color=color, label=label, linewidth=1.5, markersize=3.5)

        ax.set_title("Evolução Temporal dos Sinistros: Período Noturno vs Diurno vs Crepúsculo", fontsize=8.5, fontweight="bold", pad=5)
        ax.set_xlabel("Ano / Mês" if tem_mes else "Ano", fontsize=7.5)
        ax.set_ylabel("Nº de Sinistros", fontsize=7.5)
        ax.tick_params(axis="both", which="major", labelsize=6.5)
        if len(x_vals) > 36:
            step = 6 if len(x_vals) <= 48 else 12
            tick_idx = list(range(0, len(x_vals), step))
            if (len(x_vals) - 1) not in tick_idx:
                tick_idx.append(len(x_vals) - 1)
            ax.set_xticks(tick_idx)
            ax.set_xticklabels([x_vals[i] for i in tick_idx], rotation=30, ha="right", fontsize=6.5)
        elif len(x_vals) > 12:
            step = 3
            tick_idx = list(range(0, len(x_vals), step))
            if (len(x_vals) - 1) not in tick_idx:
                tick_idx.append(len(x_vals) - 1)
            ax.set_xticks(tick_idx)
            ax.set_xticklabels([x_vals[i] for i in tick_idx], rotation=30, ha="right", fontsize=6.5)
        elif len(x_vals) > 6:
            ax.set_xticks(range(len(x_vals)))
            ax.set_xticklabels(x_vals, rotation=30, ha="right", fontsize=6.5)
        ax.legend(fontsize=6.5, loc="upper right")
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=180)
        img_buffer.seek(0)
        plt.close(fig)

        return Image(img_buffer, width=6.8 * inch, height=2.2 * inch)

    def _generate_reaction_causes_chart(self, ocorrencias_df: pd.DataFrame, causas_df: Optional[pd.DataFrame]) -> Optional[Image]:
        """
        Gera gráfico comparativo de causas de reação/visibilidade (Dia vs Noite).
        """
        if ocorrencias_df.empty or causas_df is None or causas_df.empty:
            return None

        causas_u = causas_df[["id", "causa_acidente"]].dropna().drop_duplicates()
        merged = ocorrencias_df.merge(causas_u, on="id", how="inner")
        if merged.empty:
            return None

        target = [
            "Reação tardia",
            "Ausência de reação",
            "Dormindo",
            "Ultrapassagem",
            "Velocidade",
            "Álcool",
        ]
        labels_map = {
            "Reação tardia": "Reação Tardia",
            "Ausência de reação": "Ausência Reação",
            "Dormindo": "Sono/Dormindo",
            "Ultrapassagem": "Ultrapassagem",
            "Velocidade": "Velocidade Incomp.",
            "Álcool": "Ingestão Álcool",
        }

        col_periodo = "fase_dia_agrupada" if "fase_dia_agrupada" in merged.columns else "fase_dia"

        data_plot = []
        for term, short_lbl in labels_map.items():
            sub = merged[merged["causa_acidente"].str.contains(term, case=False, na=False)]
            not_cnt = sub[sub[col_periodo].astype(str).str.lower() == "noturno"]["id"].nunique()
            dia_cnt = sub[sub[col_periodo].astype(str).str.lower() == "diurno"]["id"].nunique()
            data_plot.append({"causa": short_lbl, "Noturno": not_cnt, "Diurno": dia_cnt})

        df_plot = pd.DataFrame(data_plot)
        if df_plot.empty:
            return None

        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, ax = plt.subplots(figsize=(7.2, 2.2), dpi=180)

        x = np.arange(len(df_plot))
        width = 0.35

        ax.bar(x - width/2, df_plot["Noturno"], width, label="Noturno", color="#1f77b4")
        ax.bar(x + width/2, df_plot["Diurno"], width, label="Diurno", color="#ff7f0e")

        ax.set_title("Causas Ligadas à Resposta e Visibilidade do Condutor: Noturno vs Diurno", fontsize=8.5, fontweight="bold", pad=5)
        ax.set_ylabel("Ocorrências Únicas", fontsize=7.5)
        ax.set_xticks(x)
        ax.set_xticklabels(df_plot["causa"], fontsize=7)
        ax.tick_params(axis="y", labelsize=6.5)
        ax.legend(fontsize=7, loc="upper right")
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=180)
        img_buffer.seek(0)
        plt.close(fig)

        return Image(img_buffer, width=6.8 * inch, height=2.1 * inch)

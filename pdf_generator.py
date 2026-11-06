"""
Módulo de Geração de Relatório Científico e Técnico em PDF.
Implementa todas as seções científicas exigidas, gráficos analíticos em alta resolução,
tabelas formatadas com paginação e integração direta aos resultados calculados no dashboard.
"""

import io
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects

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
    PHASE_COLORS,
)
from financial_model import calcular_balanco_energetico_detalhado, calcular_orcamento_cenarios
from metrics import compute_period_metrics, compute_day_vs_night_comparison
from reaction_analysis import analyze_visibility_and_reaction, REPORT_CAUSE_LABELS
from demographic_analysis import (
    compute_envolvimento_analysis,
    compute_sexo_analysis,
    compute_faixa_etaria_analysis,
    compute_veiculo_analysis,
    compute_tipo_acidente_analysis,
)


def _md_to_reportlab(text: str) -> str:
    """Converte formatação Markdown simples (**negrito**, *itálico*) em tags XML do ReportLab (<b>, <i>)."""
    if not text:
        return ""
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    t = re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)
    return t


def format_pt_br_currency(val: float) -> str:
    """Formata valor em Real brasileiro: R$&nbsp;1.234.567,89 (com espaço inquebrável para não quebrar linha)"""
    if pd.isna(val) or val is None:
        return "R$&nbsp;0,00"
    s = f"{val:,.2f}"
    s_pt = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$&nbsp;{s_pt}"


def format_pt_br_int(val: int) -> str:
    """Formata número inteiro com separador de milhar ponto: 1.234.567"""
    if pd.isna(val) or val is None:
        return "0"
    return f"{int(val):,}".replace(",", ".")


def format_pt_br_number(val: float, decimals: int = 2) -> str:
    """Formata número com separador de milhar ponto e decimal vírgula: 1.234,56"""
    if pd.isna(val) or val is None:
        return "0"
    fmt = f"{{:,.{decimals}f}}"
    s = fmt.format(val)
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


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

        reference_style = ParagraphStyle(
            "Reference_Custom", parent=body_style, fontSize=7.2, leading=9,
            spaceAfter=2,
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
            "reference": reference_style,
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
        # Valores ausentes são uma categoria de qualidade, nunca a string
        # técnica "nan" nas tabelas entregues ao público.
        def _public_missing(df: Optional[pd.DataFrame], columns: tuple[str, ...]) -> Optional[pd.DataFrame]:
            if df is None:
                return None
            clean = df.copy(deep=False)
            for col in columns:
                if col in clean.columns:
                    clean[col] = clean[col].astype(object).replace(r"(?i)^\s*(nan|none|null|n/a|<na>)\s*$", "Não informado", regex=True).fillna("Não informado")
            return clean

        pessoas_df = _public_missing(pessoas_df, ("tipo_envolvido", "tipo_veiculo", "faixa_etaria"))
        veiculos_df = _public_missing(veiculos_df, ("tipo_veiculo",))
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
        if "data_inversa" in filtered_data.columns:
            datas_recorte = pd.to_datetime(filtered_data["data_inversa"], format="%Y-%m-%d", errors="coerce")
            if datas_recorte.isna().any():
                datas_recorte = datas_recorte.fillna(pd.to_datetime(filtered_data["data_inversa"], errors="coerce", dayfirst=True))
            datas_recorte = datas_recorte.dropna()
            if not datas_recorte.empty:
                data_min = datas_recorte.min().strftime("%Y-%m-%d")
                data_max = datas_recorte.max().strftime("%Y-%m-%d")
        
        # Alerta metodológico apenas se houver anos incompletos efetivamente presentes
        alerta_anos_inc = ""
        anos_ativos = set(pd.to_numeric(filtered_data.get("ano", pd.Series(dtype=int)), errors="coerce").dropna().astype(int))
        anos_inc = [(a, m) for a, m in qual.get("anos_incompletos", []) if a in anos_ativos]
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
        Este relatório técnico consolida a auditoria e análise de <b>{format_pt_br_int(total_ocorrencias)} ocorrências desduplicadas</b>, 
        resultando em <b>{format_pt_br_int(total_mortos)} óbitos confirmados</b> e <b>{format_pt_br_int(total_feridos)} pessoas feridas</b> no conjunto analisado.<br/>
        • <b>Percentual de Acidentes Fatais:</b> <b>{format_pt_br_number(pct_fatais_geral, 1)}%</b> dos sinistros resultaram em pelo menos um óbito ({format_pt_br_int(acidentes_fatais)} sinistros fatais).<br/>
        • <b>Taxa de Óbitos por 100 Acidentes:</b> O índice geral é de <b>{format_pt_br_number(obitos_100_geral, 2)} óbitos/100 acidentes</b>.<br/>
        • <b>Assimetria Dia vs Noite:</b> Os acidentes noturnos concentram <b>{format_pt_br_int(acidentes_not)} ocorrências ({format_pt_br_number(perc_not, 1)}%)</b> e <b>{format_pt_br_int(mortos_not)} mortes</b>, com taxa de <b>{format_pt_br_number(let_not, 2)} óbitos/100 acidentes</b> contra <b>{format_pt_br_number(let_dia, 2)} no diurno</b> (letalidade <b>{format_pt_br_number(fator_let, 2)}x maior</b>).<br/>
        • <b>Cenário exploratório:</b> Redução hipotética de 35% corresponde a CMF 0,65 para o desfecho modelado. Aplicar a mesma redução aos óbitos pressupõe proporcionalidade adicional não comprovada; a estimativa de <b>{format_pt_br_number(vidas_salvas_resumo, 1)} óbitos potencialmente evitáveis/ano</b> não prevê o efeito real.
        """
        story.append(Paragraph(resumo_p, self.custom_styles["body"]))

        # =====================================================================
        # 3. METODOLOGIA E AUDITORIA DE DADOS (ESCLARECIMENTO DOS 267 REGISTROS)
        # =====================================================================
        story.append(Paragraph("2. METODOLOGIA, CONFIABILIDADE E AUDITORIA DE REGISTROS", self.custom_styles["h1"]))

        linhas_brutas = qual.get("registros_brutos", total_ocorrencias)
        desdobramentos_consolidados = qual.get("desdobramentos_consolidados", qual.get("duplicatas_linhas_evitadas", 0))
        com_km_count = int(filtered_data["km"].notna().sum()) if "km" in filtered_data else 0
        sem_km_count = total_ocorrencias - com_km_count
        mortos_sem_km = qual.get("mortos_sem_km", 0)
        feridos_sem_km = qual.get("feridos_sem_km", 0)
        km_ausente = qual.get("km_originalmente_ausente", sem_km_count)
        km_invalido = qual.get("km_nao_numerico", 0) + qual.get("km_negativo", 0) + qual.get("km_invalido_extremo", 0)
        km_recuperado = qual.get("km_superior_1500_recuperados", 0)
        pessoas_unicas = qual.get("pessoas_unicas_pesid", len(pessoas_df) if pessoas_df is not None else 0)
        caso_excepcional_txt = ""
        if filtered_data is not None and not filtered_data.empty and "id" in filtered_data.columns:
            m_730910 = filtered_data[filtered_data["id"] == 730910]
            if not m_730910.empty:
                r_730910 = m_730910.iloc[0]
                p_730910 = pessoas_df[pessoas_df["id"] == 730910] if pessoas_df is not None and "id" in pessoas_df.columns else pd.DataFrame()
                n_pes = len(p_730910["pesid"].dropna().unique()) if not p_730910.empty and "pesid" in p_730910.columns else int(r_730910.get("total_vitimas", 0))
                caso_excepcional_txt = f"<br/><b>Caso Excepcional Auditado no Período:</b> A ocorrência ID 730910 na BR-{r_730910.get('br', '423')} ({r_730910.get('uf', 'PE')}), KM {r_730910.get('km', 127):.0f}, de {r_730910.get('data_inversa', '17/10/2025')} ({r_730910.get('fase_dia_oficial', 'Plena Noite')}), foi reconciliada com <b>{format_pt_br_int(n_pes)} pessoas distintas</b> ({format_pt_br_int(int(r_730910.get('mortos', 0)))} óbitos e {format_pt_br_int(int(r_730910.get('total_feridos', 0)))} feridos). A conferência demonstra consistência interna entre identificadores, envolvidos e desfechos, sem validar independentemente a origem dos registros."

        metodologia_p = f"""
        <b>Dicionário e Granularidade:</b> Os microdados abertos da PRF ('todas_causas_tipos') multiplicam linhas para cada envolvido (<code>pesid</code>), veículo e causa registrada. As ocorrências foram desduplicadas pela chave <code>id</code>, as vítimas agregadas por pessoas únicas (<code>pesid</code>) e os veículos por <code>id_veiculo</code>, consolidando <b>{format_pt_br_int(desdobramentos_consolidados)} desdobramentos de ocupantes, veículos e causas</b> a partir de <b>{format_pt_br_int(linhas_brutas)} linhas brutas</b> (total de <b>{format_pt_br_int(pessoas_unicas)} pessoas únicas</b> identificadas).<br/>
        <b>Auditoria Metodológica dos Registros sem Marco Quilométrico:</b><br/>
        - Linhas brutas lidas: <b>{format_pt_br_int(linhas_brutas)}</b> | Ocorrências únicas totais identificadas: <b>{format_pt_br_int(qual.get('ocorrencias_unicas', total_ocorrencias))}</b>.<br/>
        - Linhas brutas com KM ausente nos arquivos carregados: <b>{format_pt_br_int(km_ausente)}</b> (não é contagem de ocorrências e pode não refletir filtros posteriores).<br/>
        - Subtração direta de desdobramentos consolidados: `{format_pt_br_int(linhas_brutas)} - {format_pt_br_int(qual.get('ocorrencias_unicas', total_ocorrencias))} = {format_pt_br_int(desdobramentos_consolidados)}`.<br/>
        - Ocorrências com KM numericamente válido: <b>{format_pt_br_int(com_km_count)}</b> | Ocorrências sem KM válido: <b>{format_pt_br_int(sem_km_count)}</b> ({format_pt_br_int(mortos_sem_km)} óbito(s) e {format_pt_br_int(feridos_sem_km)} ferido(s)).<br/>
        - Por ocorrência única no recorte: ausente <b>{format_pt_br_int(int((filtered_data['km_status'] == 'ausente').sum()) if 'km_status' in filtered_data else 0)}</b>; inválido <b>{format_pt_br_int(int(filtered_data['km_status'].isin(['nao_numerico', 'negativo', 'invalido_extremo', 'invalido']).sum()) if 'km_status' in filtered_data else 0)}</b>; recuperado acima de 1.500 <b>{format_pt_br_int(int((filtered_data['km_status'] == 'superior_1500_recuperado').sum()) if 'km_status' in filtered_data else 0)}</b>. A validação numérica não comprova localização física.<br/>
        - Todas as ocorrências permanecem nas estatísticas gerais. A segmentação exige também BR e UF válidas; sua exclusão pode superar o total sem KM válido.{caso_excepcional_txt}
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
                    Paragraph(format_pt_br_int(r.get('n_acidentes', 0)), self.custom_styles["td"]),
                    Paragraph(f"{format_pt_br_number(r.get('participacao_acidentes_pct', 0.0), 1)}%", self.custom_styles["td"]),
                    Paragraph(format_pt_br_int(r.get('total_mortos', 0)), self.custom_styles["td"]),
                    Paragraph(format_pt_br_int(r.get('total_feridos', 0)), self.custom_styles["td"]),
                    Paragraph(format_pt_br_int(r.get('acidentes_fatais', 0)), self.custom_styles["td"]),
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
        texto_fases = _md_to_reportlab(day_night_comp.get("texto_interpretativo_fases", ""))

        fases_callout = f"""
        <b>Discussão Científica — Indicadores de Severidade por Fase do Dia (Foco Crítico: {fase_top_nome} com {format_pt_br_number(fase_top_val, 2)} óbitos/100 acidentes):</b><br/>
        {texto_fases}
        """
        story.append(KeepTogether([Paragraph(fases_callout, self.custom_styles["callout"])]))

        # =====================================================================
        # 6. CAUSAS DE ACIDENTES, REAÇÃO TARDIA E AUSÊNCIA DE REAÇÃO
        # =====================================================================
        story.append(Paragraph("5. VISIBILIDADE NOTURNA, TEMPO DE REAÇÃO E CAUSAS CONCORRENTES", self.custom_styles["h1"]))

        vis_analysis = analyze_visibility_and_reaction(
            filtered_data,
            causas_df if causas_df is not None else pd.DataFrame(),
            include_details=False,
        )
        causas_fases_df = vis_analysis.get("causas_fases_df", pd.DataFrame())

        # Gráfico comparativo de causas
        img_reaction = self._generate_reaction_causes_chart(filtered_data, causas_df)
        if img_reaction:
            story.append(img_reaction)
            story.append(Spacer(1, 4))

        # Tabela das causas específicas de reação e visibilidade
        if not causas_fases_df.empty:
            target_causes = REPORT_CAUSE_LABELS
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
                        Paragraph(c_nome, self.custom_styles["td_left"]),
                        Paragraph(str(r["fase_dia_oficial"]), self.custom_styles["td"]),
                        Paragraph(format_pt_br_int(r['n_acidentes']), self.custom_styles["td"]),
                        Paragraph(format_pt_br_int(r['total_mortos']), self.custom_styles["td"]),
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
        • <b>Fundamentação Externa (Escopo FHWA):</b> <i>Proven Safety Countermeasures: Lighting</i> apresenta resultados para tipos e locais específicos de acidentes noturnos. O cenário de 35% é uma hipótese independente, não uma estimativa comprovada de redução de óbitos em rodovias brasileiras.
        """
        story.append(KeepTogether([Paragraph(vis_text, self.custom_styles["callout"])]))
        del vis_analysis

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
                        Paragraph(format_pt_br_int(r['total_envolvidos']), self.custom_styles["td"]),
                        Paragraph(format_pt_br_int(r['mortos']), self.custom_styles["td"]),
                        Paragraph(format_pt_br_int(r['feridos_graves']), self.custom_styles["td"]),
                        Paragraph(format_pt_br_int(r['feridos_leves']), self.custom_styles["td"]),
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
                    f"<i>(Idades Válidas: {format_pt_br_int(qual_idade.get('idades_validas', 0))} [{format_pt_br_number(qual_idade.get('perc_idades_validas', 0.0), 1)}%] | "
                    f"Inconsistentes/Ausentes: {format_pt_br_int(qual_idade.get('idades_inconsistentes_ou_ausentes', 0))} [{format_pt_br_number(qual_idade.get('perc_inconsistentes', 0.0), 1)}%] | "
                    f"Idades > 110 anos isoladas: {format_pt_br_int(qual_idade.get('idades_superiores_110_anos', 0))})</i>",
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
                        Paragraph(format_pt_br_int(r['total_pessoas']), self.custom_styles["td"]),
                        Paragraph(format_pt_br_int(r['mortos']), self.custom_styles["td"]),
                        Paragraph(format_pt_br_int(r['feridos_graves']), self.custom_styles["td"]),
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
                v_summary_str = ", ".join([f"{str(r['tipo_veiculo']).replace('Semireboque', 'Semirreboque')}: {format_pt_br_int(r['total_veiculos'])} veículos ({format_pt_br_int(r.get('mortos', 0))} {'óbito' if int(r.get('mortos', 0)) == 1 else 'óbitos'} entre ocupantes vinculados)" for _, r in tbl_v.iterrows()])
                story.append(Paragraph(
                    f"<b>Frota Veicular Predominante:</b> As categorias com maior envolvimento em acidentes são: {v_summary_str}.",
                    self.custom_styles["body"]
                ))
                story.append(Paragraph(
                    "<i>Granularidade: a frota conta veículos distintos por ocorrência e id_veiculo; os óbitos contam somente pessoas vinculadas ao tipo de veículo registrado. Assim, 72.864 semirreboques e 1 óbito vinculado não representam letalidade dos acidentes com semirreboques nem mortes dos ocupantes do conjunto trator-semirreboque. Há registros de pessoas com tipo de envolvimento não informado.</i>",
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
                    f"Entre os {format_pt_br_int(ped_tot)} pedestres identificados na base, registraram-se {format_pt_br_int(ped_mort)} fatalidades "
                    f"({format_pt_br_number(ped_taxa, 2)}% de letalidade específica, a maior entre as classes de usuários). "
                    f"Trata-se de evidência observacional de elevada vulnerabilidade dos modos ativos em rodovias federais, influenciada por "
                    f"fatores de risco concorrentes como travessias em nível, ausência de passarelas e velocidades elevadas, "
                    f"sem atribuição de causalidade exclusiva à ausência de iluminação."
                )
            else:
                pedestre_txt += "Pedestres apresentam a maior taxa específica de mortalidade observacional entre todas as classes de usuários."
        else:
            pedestre_txt += "Pedestres apresentam a maior taxa específica de mortalidade observacional entre todas as classes de usuários."

        story.append(KeepTogether([Paragraph(pedestre_txt, self.custom_styles["callout"])]))
        # A partir daqui o PDF contém apenas os agregados já convertidos em
        # elementos ReportLab; liberar as visões de pessoas e veículos antes
        # de montar o documento e carregar o renderizador final.
        del pessoas_df, veiculos_df, p_df, v_df

        # =====================================================================
        # 7. RANKING DE TRECHOS CRÍTICOS E FÓRMULA DE PONTUAÇÃO
        # =====================================================================
        story.append(Paragraph("7. RANKING DE TRECHOS CRÍTICOS PARA ILUMINAÇÃO SOLAR", self.custom_styles["h1"]))

        formula_desc = """
        <b>Fórmula de Priorização para Iluminação Solar:</b><br/>
        Os trechos são segmentados em intervalos regulares contínuos de 2,0 km (ex: KM 144,0 a 146,0). O score prioriza a gravidade e a recorrência no período <b>noturno</b>:<br/>
        <code>Score_Solar = (5 × Mortos_not + 3 × FeridosGraves_not + 1 × FeridosLeves_not + 2 × Acidentes_not) × (1 + %Noturno / 100)</code><br/>
        Esta classificação é exploratória: os pesos são heurísticos, sem calibração empírica, e a prioridade muda com as premissas escolhidas. O score mede concentração histórica de sinistros; não comprova ausência de iluminação nem efeito causal de postes solares.
        """
        story.append(Paragraph(formula_desc, self.custom_styles["body"]))

        if not top_segments.empty:
            t_trecho_data = [
                [
                    Paragraph("#", self.custom_styles["th"]),
                    Paragraph("Trecho (BR - UF - Extensão)", self.custom_styles["th"]),
                    Paragraph("Ac. Not.", self.custom_styles["th"]),
                    Paragraph("Óbitos", self.custom_styles["th"]),
                    Paragraph("Feridos Graves", self.custom_styles["th"]),
                    Paragraph("Score", self.custom_styles["th"]),
                    Paragraph("CAPEX (R$)", self.custom_styles["th"]),
                    Paragraph("Benefício<br/>bruto/ano", self.custom_styles["th"]),
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
                    Paragraph(format_pt_br_int(r.get('n_acidentes_noturnos', r.get('n_acidentes', 0))), self.custom_styles["td"]),
                    Paragraph(format_pt_br_int(r.get('mortos_noturno', r.get('mortos', 0))), self.custom_styles["td"]),
                    Paragraph(format_pt_br_int(r.get('feridos_graves_noturno', 0)), self.custom_styles["td"]),
                    Paragraph(f"{format_pt_br_number(float(r.get('score_iluminacao_solar', r.get('score_prioridade', 0))), 1)}", self.custom_styles["td"]),
                    Paragraph(format_pt_br_currency(inv_trecho_val), self.custom_styles["td"]),
                    Paragraph(format_pt_br_currency(float(r.get("economia_anual_trecho", 0.0))), self.custom_styles["td"]),
                ])

            t_seg = Table(t_trecho_data, colWidths=[0.8*cm, 4.6*cm, 1.4*cm, 1.4*cm, 1.4*cm, 1.6*cm, 2.2*cm, 2.2*cm], repeatRows=1)
            t_seg.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(t_seg)
            story.append(Spacer(1, 4))

            # Callout de Auditoria de Ranking e Análise de Sensibilidade a Eventos Excepcionais (BR-116 MG KM 286-288)
            has_br116_2024 = (
                filtered_data is not None and "id" in filtered_data.columns
                and (filtered_data["id"] == 661121).any()
            )
            exceptional_detail = """
            • <b>Auditoria do Caso Extremo BR-116 (MG) KM 286,0–288,0:</b> A ocorrência ID 661121, de 21/12/2024, é exibida somente porque pertence ao período ativo. Eventos excepcionais permanecem na série histórica, mas não autorizam inferir que iluminação isolada evitaria colisões de múltiplas causas.
            """ if has_br116_2024 else """
            • <b>Auditoria de período:</b> Não há referência a ocorrências de 2024 fora do conjunto elegível deste relatório. O ranking e os exemplos narrativos usam exclusivamente os eventos dos filtros ativos.
            """
            audit_callout = f"""
            <b>Auditoria Metodológica de Ranking e Análise de Sensibilidade a Eventos Excepcionais:</b><br/>
            • <b>Diferenciação Metodológica:</b> Distingue-se o <i>Ranking de Gravidade Histórica Acumulada</i> (influenciado pelo total de vítimas) da <i>Prioridade de Intervenção Luminotécnica</i> (focada na reatividade à iluminação solar contínua).<br/>
            {exceptional_detail}<br/>
            • <b>Análise de Sensibilidade:</b> Redução hipotética de 35% equivale a CMF 0,65 para o desfecho modelado. Sua aplicação proporcional aos óbitos é uma premissa adicional exploratória, não eficácia comprovada para os trechos brasileiros.<br/>
            • <b>Diretriz de Decisão:</b> Eventos reais não devem ser expurgados da série histórica, mas intervenções de engenharia não devem presumir que a iluminação isoladamente evitaria sinistros com múltiplas causas complexas (fadiga extrema, velocidade e colisão frontal múltipla). Recomenda-se ranking de sensibilidade em projetos executivos.
            """
            story.append(KeepTogether([Paragraph(audit_callout, self.custom_styles["callout"])]))
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
        • <b>Conjunto Solar Compacto Integrado:</b> Módulo fotovoltaico monocristalino de <b>240 Wp</b>, com inclinação conceitual de 22°, sujeita à localização, orientação e sombreamento do trecho.<br/>
        • <b>Luminária Viária LED:</b> Potência de <b>40 W</b> com ótica viária Tipo II (corte total anti-ofuscamento), sensor Doppler por radar de micro-ondas e antena de telemetria.<br/>
        <br/>
        <b>Balanço Energético Auditado e Autonomia com ZERO Geração Solar:</b><br/>
        • <b>Consumo Noturno Dimerizado (12h):</b> 4h pico a 100% (160 Wh) + 4h normal a 80% (128 Wh) + 4h repouso a 60% (96 Wh) = <b>384 Wh/noite</b>.<br/>
        • <b>Telemetria e Supervisão 24h:</b> 2 W contínuos &rarr; <b>48 Wh/dia</b>. Consumo Total: <b>{format_pt_br_number(b_eng['consumo_total_diario_wh'], 0)} Wh por dia/noite</b>.<br/>
        • <b>Banco de Baterias LiFePO4 (2.500 Wh nominais):</b> Com 80% DoD e 90% de rendimento MPPT/driver: <b>Capacidade Útil BOL = {format_pt_br_number(b_eng['capacidade_util_bol_wh'], 1)} Wh</b> e <b>Capacidade Útil EOL (80% vida) = {format_pt_br_number(b_eng['capacidade_util_eol_wh'], 1)} Wh</b>.<br/>
        • <b>Autonomia Efetiva com ZERO Sol:</b> <b>{format_pt_br_number(b_eng['autonomia_zero_sol_bol_noites'], 2)} noites (BOL)</b> e <b>{format_pt_br_number(b_eng['autonomia_zero_sol_eol_noites'], 2)} noites (EOL)</b>. Sustenta rigorosamente a meta mandatária de 3 noites consecutivas sem incidência solar.<br/>
        • <b>Geração Solar Diária (4,5 HSP, PR 80%):</b> <b>{format_pt_br_number(b_eng['geracao_solar_sol_pleno_wh'], 1)} Wh/dia</b> (excedente de {format_pt_br_number(b_eng['excedente_diario_sol_wh'], 1)} Wh/dia para recarga completa em {format_pt_br_number(b_eng['dias_recarga_apos_3_noites'], 1)} dias de sol pleno).<br/>
        • <b>Dias Nublados vs Zero Sol:</b> Em dias nublados (25% de irradiação padrão), a geração é de <b>{format_pt_br_number(b_eng['geracao_solar_dia_nublado_wh'], 1)} Wh/dia</b> (déficit diário de {format_pt_br_number(abs(b_eng['balanco_liquido_nublado_wh']), 1)} Wh/dia). Com banco plenamente carregado, a autonomia estimada em dias nublados contínuos é de <b>{format_pt_br_number(b_eng['capacidade_util_bol_wh'] / abs(b_eng['balanco_liquido_nublado_wh']), 1)} dias em início de vida (BOL)</b> e <b>{format_pt_br_number(b_eng['capacidade_util_eol_wh'] / abs(b_eng['balanco_liquido_nublado_wh']), 1)} dias em fim de vida (EOL 80%)</b>.<br/>
        • <b>Hipótese de Inclinação e Localização:</b> A inclinação referencial de 22° adotada na simulação constitui parâmetro de modelagem média nacional, devendo ser calibrada para a latitude específica de cada trecho rodoviário.<br/>
        <br/>
        <b>Segurança Luminotécnica e Validação Pendente (ABNT NBR 5101:2024):</b><br/>
        A potência de 40 W é hipótese preliminar. Os requisitos de luminância (cd/m²), iluminância (lux), uniformidade e ofuscamento dependem da classe viária e das condições específicas. A conformidade com a ABNT NBR 5101:2024 requer classificação e estudo fotométrico em DIALux evo ou ferramenta equivalente; não foi demonstrada neste projeto.
        """
        story.append(Paragraph(eng_p, self.custom_styles["body"]))

        # =====================================================================
        # 9. MODELAGEM ORÇAMENTÁRIA MULTI-CENÁRIOS E RETORNO FINANCEIRO
        # =====================================================================
        story.append(Paragraph("9. MODELAGEM ECONÔMICA E CENÁRIOS COMPARÁVEIS (A a E)", self.custom_styles["h1"]))

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
                Paragraph("CAPEX<br/>(R$ mi)", self.custom_styles["th"]),
                Paragraph("VPL Social<br/>(R$ mi)", self.custom_styles["th"]),
                Paragraph("TIR (% a.a.)", self.custom_styles["th"]),
                Paragraph("Payback<br/>Simples", self.custom_styles["th"]),
            ]
        ]
        for _, row_c in comp_df.iterrows():
            tir_c_str = f"{format_pt_br_number(row_c['TIR (% a.a.)'], 1)}%" if pd.notna(row_c['TIR (% a.a.)']) else "N/A"
            pb_c_val = row_c['Payback Simples (anos)']
            pb_c_str = f"{format_pt_br_number(pb_c_val, 2)} ano" if pb_c_val < 1 else f"{format_pt_br_number(pb_c_val, 2)} anos" if pb_c_val < 100 else "> 15 anos"
            t_cen_multi_data.append([
                Paragraph(str(row_c["Cenário"]), self.custom_styles["td_left"]),
                Paragraph({"estimativa historica": "Estimativa Histórica", "pesquisado comercial": "Pesquisa Comercial", "hipotese conceitual": "Hipótese Conceitual", "hipotese composta": "Hipótese Composta"}.get(str(row_c["Tipo"]).casefold(), str(row_c["Tipo"])), self.custom_styles["td"]),
                Paragraph(f"{row_c['Altura']} / {row_c['LED']}", self.custom_styles["td"]),
                Paragraph(format_pt_br_currency(row_c["Custo Unitário (R$)"]), self.custom_styles["td"]),
                Paragraph(format_pt_br_number(row_c['CAPEX Total (R$ M)'], 2), self.custom_styles["td"]),
                Paragraph(format_pt_br_number(row_c['VPL 15 Anos (R$ M)'], 2), self.custom_styles["td"]),
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
        story.append(Paragraph("CAPEX e VPL social em R$ milhões; VPL calculado para horizonte de 15 anos.", self.custom_styles["reference"]))
        story.append(Spacer(1, 4))

        fin = financial_summary or {}
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
        capex_a_str = f"R$&nbsp;{format_pt_br_number(row_a['CAPEX Total (R$ M)'].iloc[0], 2)} milhões" if not row_a.empty else "N/A"
        pb_a_str = f"{format_pt_br_number(row_a['Payback Simples (anos)'].iloc[0], 2)} anos" if not row_a.empty else "N/A"

        row_d = comp_df[comp_df["Cenário"].astype(str).str.contains("Cenário D", na=False)]
        custo_d_str = format_pt_br_currency(row_d['Custo Unitário (R$)'].iloc[0]) if not row_d.empty else "N/A"
        capex_d_str = f"R$&nbsp;{format_pt_br_number(row_d['CAPEX Total (R$ M)'].iloc[0], 2)} milhões" if not row_d.empty else "N/A"
        vpl_d_str = f"R$&nbsp;{format_pt_br_number(row_d['VPL 15 Anos (R$ M)'].iloc[0], 2)} milhões" if not row_d.empty else "N/A"
        pb_d_str = f"{format_pt_br_number(row_d['Payback Simples (anos)'].iloc[0], 2)} anos" if not row_d.empty else "N/A"

        fin_text = f"""
        <b>Memória de Cálculo de Vidas Potencialmente Preservadas ({format_pt_br_number(vidas_salvas, 1)} vidas/ano em {n_trechos_top} Trechos Críticos):</b><br/>
        1. <b>Acúmulo Histórico:</b> Nos {n_trechos_top} trechos prioritários selecionados, ocorreram <b>{format_pt_br_int(mortos_top)} óbitos noturnos</b> no horizonte de {format_pt_br_number(anos_base, 1)} anos analisados.<br/>
        2. <b>Taxa Baseline Anualizada:</b> `{format_pt_br_int(mortos_top)} óbitos / {format_pt_br_number(anos_base, 1)} anos = {format_pt_br_number(mortos_top / anos_denom, 1)} óbitos noturnos por ano`.<br/>
        3. <b>Hipótese exploratória:</b> Redução de 35% (CMF 0,65) aplicada proporcionalmente aos óbitos como premissa adicional não comprovada &rarr; `{format_pt_br_number(mortos_top / anos_denom, 1)} × 0,35 = {format_pt_br_number(vidas_salvas, 1)} óbitos potencialmente evitáveis por ano`.<br/>
        4. <b>Rastreabilidade de Seleção Amostral:</b> O conjunto de trechos críticos é ranqueado dinamicamente para o período analisado. Diferenças nos totais anualizados entre janelas temporais refletem a composição dos segmentos prioritários de cada base.<br/>
        5. <b>Valoração paramétrica provisória:</b> Os valores por óbito ({format_pt_br_currency(ECONOMIC_VALUES['valor_vida_estatistica'])}), ferido grave ({format_pt_br_currency(ECONOMIC_VALUES['custo_medio_acidente_grave'])}) e leve ({format_pt_br_currency(ECONOMIC_VALUES['custo_medio_acidente_leve'])}) têm fonte, ano-base e atualização pendentes de validação. São premissas do modelo, não valores atribuídos ao Ipea. Benefício social bruto simulado: <b>{format_pt_br_currency(beneficio_anual)}/ano</b>.<br/>
        6. <b>Custos de Implantação e Retorno Socioeconômico Comparado:</b><br/>
        • <b>Meta Histórica (Cenário A):</b> CAPEX {capex_a_str} | Payback Simples: {pb_a_str}.<br/>
        • <b>Conceitual Compacto 8m/40W (Cenário D - Base):</b> Custo/un {custo_d_str} | CAPEX {capex_d_str} | Payback Simples: {pb_d_str} | VPL Social 15 anos: {vpl_d_str}.<br/>
        <br/>
        <b>Plano Conceitual de Manutenção e Telemetria:</b><br/>
        Supervisão remota contínua (telemetria LoRaWAN/NB-IoT a 2W) monitorando tensão da bateria, corrente do painel e integridade do LED. Provisão de OPEX com manutenção preventiva (R$ 500/poste/ano) e reserva para troca de baterias a cada 5 anos (R$ 3.800/un).<br/>
        <i>Aviso Metodológico Obrigatório: Os cálculos representam simulações socioeconômicas conceituais sob taxa social de desconto de 8% a.a. e horizonte de 15 anos. A valoração da vida estatística (VSL) é uma métrica de custo-benefício social e não constitui receita financeira. Não existem postes físicos instalados nesta etapa acadêmica do projeto.</i>
        """
        story.append(KeepTogether([Paragraph(fin_text, self.custom_styles["body"])]))

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
        sensitivity_title = Paragraph(f"<b>Matriz de Sensibilidade de Efetividade (Simulação sob {cen_equip_nome} — CAPEX {format_pt_br_currency(capex_val)}):</b>", self.custom_styles["body"])
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
            story.append(KeepTogether([sensitivity_title, t_cen]))
            story.append(Spacer(1, 4))

        # =====================================================================
        # 10. DISCUSSÃO, LIMITAÇÕES, CONCLUSÕES E REFERÊNCIAS
        # =====================================================================
        story.append(Paragraph("10. DISCUSSÃO CIENTÍFICA, LIMITAÇÕES E CONCLUSÕES", self.custom_styles["h1"]))
        disc_p = """
        <b>Discussão Teórica:</b> A segurança viária é multifatorial. A iluminação rodoviária adequadamente projetada pode ampliar as condições de visibilidade noturna e favorecer o reconhecimento de obstáculos, usuários e características da via. Sua efetividade depende das condições geométricas, ambientais e operacionais, além do dimensionamento luminotécnico específico. Alcoolemia, fadiga e velocidade também influenciam os desfechos.<br/>
        <b>Limitações Metodológicas Reconhecidas:</b><br/>
        1. <b>Ausência de Censo Luminotécnico:</b> A PRF não audita a presença física de postes ou nível de iluminância (lux) no boletim de ocorrência;<br/>
        2. <b>Exposição ao Tráfego:</b> Os dados públicos da PRF não registram Volume Médio Diário Anual (VDMA) por quilômetro em toda a malha, impedindo o cálculo de taxa de risco por veículo-quilômetro percorrido;<br/>
        3. <b>Natureza Paramétrica das Finanças:</b> Os valores socioeconômicos são premissas provisórias com fonte e atualização pendentes, não correspondendo a faturamento ou caixa financeiro real.<br/>
        <b>Conclusão Condicional e Recomendações:</b> Os dados observacionais da PRF evidenciam que os sinistros noturnos e no amanhecer apresentam severidade e letalidade substancialmente superiores às do pleno dia. As simulações físico-econômicas indicam atratividade socioeconômica favorável sob as premissas de projeto adotadas (horizonte de 15 anos, taxa social de desconto de 8% a.a. e custos unitários do Cenário D). Contudo, a efetiva implantação em escala permanece condicionada a validações complementares indispensáveis: (i) realização de censo físico de iluminação artificial existente nos trechos; (ii) estudos computacionais fotométricos por trecho conforme ABNT NBR 5101:2024; (iii) ensaios geotécnicos e dimensionamento estrutural de fundação; (iv) cotações executivas de fornecedores e logística de instalação; e (v) mensuração empírica do VDMA por segmento. Recomenda-se a execução de projetos-piloto controlados nos primeiros trechos do ranking para aferição empírica do Fator de Modificação de Acidentes (CMF) antes de decisões definitivas de investimento.
        """
        story.append(KeepTogether([Paragraph(disc_p, self.custom_styles["body"])]))

        reference_block = [Paragraph("11. REFERÊNCIAS BIBLIOGRÁFICAS E BASES OFICIAIS", self.custom_styles["h1"])]
        for ref in REFERENCES:
            ref_str = f"• <b>{ref['titulo']}</b>. {ref['instituicao']}, {ref['ano']}. <link href=\"{ref['url']}\" color=\"#1769aa\">Acesso à fonte</link>. Consultado em: 29 out. 2026."
            reference_block.append(Paragraph(ref_str, self.custom_styles["reference"]))
        story.append(KeepTogether(reference_block))

        doc.build(story)
        # Carimba sobre cada página com uma biblioteca PDF leve. A mesclagem
        # preserva o conteúdo e os links, inclusive quando tabelas usam recorte.
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter(clone_from=PdfReader(buffer))
        total_pages = len(writer.pages)
        _, page_height = A4
        for page_num, page in enumerate(writer.pages, start=1):
            stamp_buffer = io.BytesIO()
            stamp_canvas = canvas.Canvas(stamp_buffer, pagesize=A4)
            stamp_canvas.setFont("Helvetica", 8)
            stamp_canvas.setFillColor(colors.HexColor("#555555"))
            stamp_canvas.setStrokeColor(colors.HexColor("#cccccc"))
            if page_num > 1:
                stamp_canvas.drawString(55, page_height - 20, "Iluminar para Proteger — Relatório Técnico e Científico de Segurança Viária")
                stamp_canvas.line(55, page_height - 30, 540, page_height - 30)
            stamp_canvas.line(55, 30, 540, 30)
            stamp_canvas.drawString(55, 18, "Projeto de Extensão em Ciência de Dados — UNINTER | Fontes: PRF / IPEA / FHWA")
            stamp_canvas.drawRightString(540, 18, f"Página {page_num} de {total_pages}")
            stamp_canvas.save()
            stamp_buffer.seek(0)
            page.merge_page(PdfReader(stamp_buffer).pages[0], over=True)
        final_pdf = io.BytesIO()
        writer.write(final_pdf)
        final_pdf.seek(0)
        return final_pdf

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
        for col_name, color, label, line_style, marker in [
            ("Noturno", PHASE_COLORS["Noturno"], "Noturno", "-", "o"),
            ("noturno", PHASE_COLORS["Noturno"], "Noturno", "-", "o"),
            ("Diurno", PHASE_COLORS["Diurno"], "Diurno", "--", "s"),
            ("diurno", PHASE_COLORS["Diurno"], "Diurno", "--", "s"),
            ("Crepúsculo", PHASE_COLORS["Crepúsculo"], "Crepúsculo", "-.", "^"),
        ]:
            if col_name in grouped.columns:
                line, = ax.plot(x_vals, grouped[col_name], marker=marker, color=color, label=label,
                                linestyle=line_style, linewidth=1.8, markersize=3.5)
                line.set_path_effects([
                    path_effects.Stroke(linewidth=2.7, foreground="#334155"),
                    path_effects.Normal(),
                ])

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
        ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=3)
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
        periodo_col = "fase_dia_agrupada" if "fase_dia_agrupada" in ocorrencias_df.columns else "fase_dia"
        merged = ocorrencias_df[["id", periodo_col]].merge(causas_u, on="id", how="inner")
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

        ax.bar(x - width/2, df_plot["Noturno"], width, label="Noturno",
               color=PHASE_COLORS["Noturno"], edgecolor="#334155", linewidth=0.6)
        ax.bar(x + width/2, df_plot["Diurno"], width, label="Diurno",
               color=PHASE_COLORS["Diurno"], edgecolor="#334155", linewidth=0.6)

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

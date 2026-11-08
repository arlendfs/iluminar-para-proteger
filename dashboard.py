"""
Dashboard Interativo do Sistema Iluminar para Proteger.
Interface científica com Streamlit, Plotly e Folium.
Apresenta análises estatísticas, tempo de reação e visibilidade,
segmentação de trechos, mapa, viabilidade econômica e protótipo 3D.
"""

import os
import gc
import time
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
import branca.element

from config import (
    COLOR_PALETTE,
    PHASE_COLORS,
    SEVERITY_COLORS,
    SEX_COLORS,
    FINANCIAL_CHART_COLORS,
    APP_CONFIG,
    FINANCIAL_PARAMS,
    EFFECTIVENESS_PARAMS,
    ECONOMIC_VALUES,
    DEFAULT_SPACING_M,
    DEFAULT_COMPRIMENTO_TRECHO_KM,
    DEFAULT_TRECHOS_TOP_N,
    SCENARIOS,
    CENARIOS_ORCAMENTO,
    ENGENHARIA_SISTEMA_SOLAR_COMPACTO,
    LUMINOTECNICA_PARAMETROS,
    TELEMETRIA_CONFIG,
    CAUSAS_VISIBILIDADE_REACAO,
    RSSPeakSampler,
)
from analyzer import AccidentAnalyzer
from metrics import compute_period_metrics, compute_day_vs_night_comparison
from reaction_analysis import analyze_visibility_and_reaction
from demographic_analysis import (
    compute_envolvimento_analysis,
    compute_sexo_analysis,
    compute_faixa_etaria_analysis,
    compute_veiculo_analysis,
    compute_tipo_acidente_analysis,
)
from financial_model import calcular_orcamento_cenarios, calcular_balanco_energetico_detalhado
from pathlib import Path
from folium.plugins import MarkerCluster
from pdf_generator import ReportGenerator, format_pt_br_currency, format_pt_br_number

PDF_GENERATION_LOCK = threading.Lock()

def format_pt_br_currency(val: float) -> str:
    """Formata valor em Real brasileiro: R$ 1.234.567,89"""
    if pd.isna(val) or val is None:
        return "R$ 0,00"
    s = f"{val:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")



def render_legacy_full_dashboard(analyzer: AccidentAnalyzer):
    """
    Constrói o painel de controle e visualizações com dados auditados.
    """
    data = analyzer.filtered_data
    if data is None or data.empty:
        st.warning("⚠️ Não há registros para exibir com os filtros selecionados.")
        return

    # =========================================================================
    # 1. RESUMO DE QUALIDADE E AUDITORIA DOS DADOS
    # =========================================================================
    quality = analyzer.quality_summary or {}
    total_linhas_brutas = quality.get("registros_brutos", len(data))
    ocorrencias_unicas = len(data)
    desdobramentos_consolidados = quality.get("desdobramentos_consolidados", quality.get("duplicatas_linhas_evitadas", total_linhas_brutas - ocorrencias_unicas))
    com_km = int(data["km"].notna().sum())
    sem_km = quality.get("ocorrencias_sem_km", ocorrencias_unicas - com_km)
    mortos_sem_km = quality.get("mortos_sem_km", 0)
    feridos_sem_km = quality.get("feridos_sem_km", 0)
    com_geo = int((data["latitude"].notna() & data["longitude"].notna()).sum())
    pessoas_unicas = quality.get("pessoas_unicas_pesid", len(analyzer.pessoas_data) if analyzer.pessoas_data is not None else 0)
    veiculos_unicos = quality.get("veiculos_unicos", len(analyzer.veiculos_data) if analyzer.veiculos_data is not None else 0)

    with st.expander("🛡️ Auditoria Metodológica e Resumo de Qualidade dos Dados", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Linhas Brutas Lidas", f"{total_linhas_brutas:,}")
        c2.metric("Ocorrências Únicas", f"{ocorrencias_unicas:,}", help="Desduplicadas pelo ID de sinistro")
        c3.metric("Desdobramentos Consolidados", f"{desdobramentos_consolidados:,}", help="Consolidação de linhas múltiplas por ocupante, veículo e causa em ocorrências únicas")
        c4.metric("Com Coordenadas Válidas", f"{com_geo:,} ({(com_geo/ocorrencias_unicas*100):.1f}%)" if ocorrencias_unicas > 0 else "0")

        st.markdown(
            f"""
            **Auditoria dos Registros e Regras de Elegibilidade Metodológica:**
            - **Total de linhas brutas nos arquivos de entrada:** **{total_linhas_brutas:,}**.
            - **Ocorrências únicas totais no banco de dados:** **{quality.get('ocorrencias_unicas', ocorrencias_unicas):,}** (desduplicadas estritamente pelo ID de sinistro).
            - **Pessoas únicas com pesid informado:** **{pessoas_unicas:,}** | **Veículos únicos envolvidos:** **{veiculos_unicos:,}**.
            - **Desdobramentos por Ocupante e Causa Consolidados:** `{total_linhas_brutas:,} - {quality.get('ocorrencias_unicas', ocorrencias_unicas):,} = {desdobramentos_consolidados:,}`.
            - **Ocorrências com marco quilométrico (KM) verificado:** **{com_km:,}**.
            - **Ocorrências com KM ausente / desconhecido na PRF:** **{sem_km:,}** ({mortos_sem_km:,} óbito(s) e {feridos_sem_km:,} ferido(s)).
            
            **Diretrizes de Elegibilidade por Módulo:**
            1. **Análise Nacional, Regional, Temporal, Fatais, Causas e Demografia:** Utilizam **todas as {ocorrencias_unicas:,} ocorrências elegíveis**, garantindo que nenhum acidente real seja descartado das estatísticas gerais.
            2. **Ranking Segmentado por Quilômetro:** Utiliza **exclusivamente as {com_km:,} ocorrências com KM e BR válidos**, impedindo a distorção física de concentração artificial em KM 0,0.
            3. **Mapa Geográfico:** Mapeia **todas as {com_geo:,} ocorrências com coordenadas geográficas válidas**.
            """
        )

        if quality.get("anos_incompletos"):
            for ano_inc, meses_inc in quality["anos_incompletos"]:
                st.info(f"ℹ️ **Aviso Metodológico:** O ano de {ano_inc} está incompleto na base (dados até o mês {max(meses_inc)}). O sistema utiliza taxa anualizada ponderada.")

        # Auditoria do registro excepcional BR-423 PE KM 127 APENAS se presente na base ativa
        if "id" in data.columns and 730910 in data["id"].values:
            m_730910 = data[data["id"] == 730910].iloc[0]
            p_730910 = analyzer.filtered_pessoas[analyzer.filtered_pessoas["id"] == 730910] if analyzer.filtered_pessoas is not None else pd.DataFrame()
            n_pes = len(p_730910["pesid"].dropna().unique()) if not p_730910.empty and "pesid" in p_730910.columns else int(m_730910.get("total_vitimas", 0))
            st.markdown(
                f"""
                🚨 **Auditoria de Registro Excepcional no Período Selecionado — BR-{m_730910.get('br', '423')} ({m_730910.get('uf', 'PE')}), KM {m_730910.get('km', 127):.0f}:**  
                Identificada a ocorrência de alta gravidade **ID 730910**, ocorrida em **{m_730910.get('data_inversa', '17/10/2025')} às {m_730910.get('horario', '20h20')} ({m_730910.get('fase_dia_oficial', 'Plena Noite')})** no município de **Saloá/PE**.  
                - **Tipo de Acidente:** {m_730910.get('tipo_acidente', 'Tombamento de Ônibus')}.  
                - **Causas Registradas:** *Ausência de reação do condutor* e *Velocidade Incompatível*.  
                - **Verificação de Pessoas:** Rastreamento de **{n_pes} pessoas com identificadores distintos (`pesid`)**, confirmando **{int(m_730910.get('mortos', 0))} óbitos**, **{int(m_730910.get('feridos_graves', 0))} feridos graves** e **{int(m_730910.get('feridos_leves', 0))} feridos leves** (totalizando **{int(m_730910.get('total_feridos', 0))} feridos**).  
                - **Conclusão:** O sinistro é verídico e documentado pela PRF, não se tratando de duplicidade ou erro de sistema.
                """
            )

    # =========================================================================
    # 2. CARDS DE MÉTRICAS PRINCIPAIS
    # =========================================================================
    total_mortos = int(data["mortos"].sum()) if "mortos" in data.columns else 0
    total_feridos = int(data["total_feridos"].sum()) if "total_feridos" in data.columns else 0
    acidentes_fatais = int(data["acidente_fatal"].sum()) if "acidente_fatal" in data.columns else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🚗 Acidentes Únicos", f"{ocorrencias_unicas:,}")
    col2.metric("💀 Pessoas Mortas", f"{total_mortos:,}")
    col3.metric("🤕 Total de Feridos", f"{total_feridos:,}")
    taxa_fatais = (acidentes_fatais / ocorrencias_unicas * 100) if ocorrencias_unicas > 0 else 0.0
    col4.metric(
        "🚨 Percentual de acidentes fatais",
        f"{taxa_fatais:.1f}%",
        help=f"Proporção de acidentes com pelo menos 1 óbito: {acidentes_fatais:,} fatais / {ocorrencias_unicas:,} ocorrências"
    )
    obitos_100 = (total_mortos / ocorrencias_unicas * 100) if ocorrencias_unicas > 0 else 0.0
    col5.metric(
        "📊 Óbitos por 100 acidentes",
        f"{obitos_100:.2f}",
        help=f"Taxa média geral de fatalidade: {total_mortos:,} óbitos para cada 100 acidentes"
    )

    st.markdown("---")

    # =========================================================================
    # 3. ANÁLISE COMPARATIVA DIA VERSUS NOITE
    # =========================================================================
    st.subheader("🌗 Análise Comparativa: Período Diurno vs Noturno")

    day_night_comp = compute_day_vs_night_comparison(data)
    noturno_metrics = day_night_comp.get("noturno") or {}
    diurno_metrics = day_night_comp.get("diurno") or {}
    tabela_oficial = day_night_comp.get("tabela_oficial")

    # Informações em destaque
    c_info1, c_info2, c_info3 = st.columns(3)
    let_not = noturno_metrics.get("mortos_por_100_acidentes", 0.0)
    let_dia = diurno_metrics.get("mortos_por_100_acidentes", 0.0)
    razao_let = day_night_comp.get("razao_letalidade_obitos", 1.0)
    prop_fat_not = noturno_metrics.get("prop_acidentes_fatais_pct", 0.0)
    prop_fat_dia = diurno_metrics.get("prop_acidentes_fatais_pct", 0.0)

    c_info1.metric(
        "🌙 Óbitos/100 Acidentes (Noturno)",
        f"{let_not:.2f}",
        delta=f"+{let_not - let_dia:.2f} vs Diurno" if let_not > let_dia else f"{let_not - let_dia:.2f}",
        delta_color="inverse",
        help="Taxa de fatalidade por 100 acidentes registrados no período noturno"
    )
    c_info2.metric(
        "☀️ Óbitos/100 Acidentes (Diurno)",
        f"{let_dia:.2f}",
        help="Taxa de fatalidade por 100 acidentes registrados no período diurno"
    )
    c_info3.metric(
        "⚖️ Fator Comparativo de Letalidade",
        f"{razao_let:.2f}x",
        help="Razão entre a taxa noturna e a taxa diurna (não representa risco por viagem)"
    )

    # Gráficos da Comparação Dia vs Noite
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if tabela_oficial is not None and not tabela_oficial.empty:
            fig_fases = px.pie(
                tabela_oficial,
                names="fase_dia_oficial",
                values="n_acidentes",
                title="Distribuição de Ocorrências por Fase do Dia (PRF)",
                color="fase_dia_oficial",
                color_discrete_map=PHASE_COLORS,
                hole=0.4,
            )
            fig_fases.update_traces(textinfo="percent+label", hovertemplate="<b>%{label}</b><br>Acidentes: %{value:,}<br>Part.: %{percent:.1%}")
            st.plotly_chart(fig_fases)

    with col_g2:
        if tabela_oficial is not None and not tabela_oficial.empty:
            fig_bar_let = px.bar(
                tabela_oficial,
                x="fase_dia_oficial",
                y="mortos_por_100_acidentes",
                color="fase_dia_oficial",
                title="Taxa de Mortalidade: Óbitos por 100 Acidentes por Período",
                labels={"fase_dia_oficial": "Fase do Dia", "mortos_por_100_acidentes": "Óbitos / 100 Acidentes"},
                color_discrete_map=PHASE_COLORS,
            )
            fig_bar_let.update_traces(hovertemplate="<b>%{x}</b><br>Óbitos/100 Ac.: %{y:.2f}")
            st.plotly_chart(fig_bar_let)
            if day_night_comp.get("texto_interpretativo_fases"):
                st.info(f"💡 **Interpretação Científica:** {day_night_comp.get('texto_interpretativo_fases')}")

    # Tabela detalhada de indicadores por período
    if tabela_oficial is not None and not tabela_oficial.empty:
        st.dataframe(
            tabela_oficial[[
                "fase_dia_oficial", "n_acidentes", "participacao_acidentes_pct",
                "total_mortos", "mortos_por_100_acidentes", "acidentes_fatais",
                "prop_acidentes_fatais_pct", "total_feridos", "vitimas_por_100_acidentes"
            ]],
            column_config={
                "fase_dia_oficial": "Fase do Dia (PRF)",
                "n_acidentes": st.column_config.NumberColumn("Acidentes", format="%d"),
                "participacao_acidentes_pct": st.column_config.NumberColumn("Part. (%)", format="%.1f%%"),
                "total_mortos": st.column_config.NumberColumn("Óbitos", format="%d"),
                "mortos_por_100_acidentes": st.column_config.NumberColumn("Óbitos / 100 Ac.", format="%.2f"),
                "acidentes_fatais": st.column_config.NumberColumn("Sinistros Fatais", format="%d"),
                "prop_acidentes_fatais_pct": st.column_config.NumberColumn("% Fatais", format="%.1f%%"),
                "total_feridos": st.column_config.NumberColumn("Total Feridos", format="%d"),
                "vitimas_por_100_acidentes": st.column_config.NumberColumn("Vítimas / 100 Ac.", format="%.2f"),
            },
            hide_index=True,
            width="stretch",
        )

    st.markdown("---")

    # =========================================================================
    # 4. VISIBILIDADE NOTURNA, TEMPO DE REAÇÃO E FATORES ASSOCIADOS
    # =========================================================================
    st.subheader("👁️ Visibilidade Noturna, Tempo de Reação e Fatores Associados")
    st.markdown(
        """
        Esta seção investiga hipóteses sobre o impacto da escuridão e da redução da visibilidade 
        na capacidade de percepção e tempo de reação do condutor (*Mecanismo PIEV*).
        """
    )

    vis_data = analyze_visibility_and_reaction(
        data,
        analyzer.filtered_causas if analyzer.filtered_causas is not None else pd.DataFrame()
    )

    pivot_causas = vis_data.get("pivot_causas", pd.DataFrame())
    reacao_df = vis_data.get("reacao_df", pd.DataFrame())

    if not pivot_causas.empty:
        col_v1, col_v2 = st.columns([3, 2])
        with col_v1:
            # Gráfico das causas de reação no Diurno vs Noturno
            top_reacao = pivot_causas[pivot_causas["is_reacao_visibilidade"]].copy()
            if not top_reacao.empty:
                col_n_not = [c for c in top_reacao.columns if "n_acidentes_noturno" in c]
                col_n_dia = [c for c in top_reacao.columns if "n_acidentes_diurno" in c]
                if col_n_not and col_n_dia:
                    top_plot = top_reacao.sort_values(col_n_not[0], ascending=False).head(8)
                    fig_reacao = go.Figure(data=[
                        go.Bar(name="Noturno", x=top_plot["causa_normalizada"], y=top_plot[col_n_not[0]], marker_color=COLOR_PALETTE["noturno"]),
                        go.Bar(name="Diurno", x=top_plot["causa_normalizada"], y=top_plot[col_n_dia[0]], marker_color=COLOR_PALETTE["diurno"]),
                    ])
                    fig_reacao.update_layout(
                        title="Acidentes por Causa Ligada à Resposta do Condutor: Noturno vs Diurno",
                        barmode="group",
                        xaxis_tickangle=-30,
                        height=420,
                    )
                    st.plotly_chart(fig_reacao)

        with col_v2:
            st.html(
                f"""
                <div class="highlight-box">
                    <h4>🔬 Rigor Científico e Cautela Metodológica</h4>
                    <p><strong>Evidência Observacional:</strong> {vis_data.get('evidencias_texto')}</p>
                    <p><strong>Hipótese Interpretativa:</strong> {vis_data.get('hipotese_texto')}</p>
                    <p><strong>Limitação Metodológica:</strong> {vis_data.get('limitacoes_texto')}</p>
                    <p><small><em>Referência: {vis_data.get('referencia_fhwa')}</em></small></p>
                </div>
                """
            )

    # Estratificação por Meteorologia e Tipo de Pista
    meteo_strat = vis_data.get("meteo_strat", pd.DataFrame())
    pista_strat = vis_data.get("pista_strat", pd.DataFrame())

    if not meteo_strat.empty or not pista_strat.empty:
        st.markdown("##### 🌧️ Estratificação Ambiental e Geometria da Via")
        cm1, cm2 = st.columns(2)
        with cm1:
            if not meteo_strat.empty:
                fig_meteo = px.bar(
                    meteo_strat,
                    x="condicao_metereologica",
                    y="n_acidentes",
                    color="fase_dia_agrupada" if "fase_dia_agrupada" in meteo_strat.columns else None,
                    barmode="group",
                    title="Causas de Visibilidade/Reação por Condição Meteorológica",
                    labels={"condicao_metereologica": "Meteorologia", "n_acidentes": "Acidentes"},
                    color_discrete_map=PHASE_COLORS,
                )
                fig_meteo.update_layout(xaxis_tickangle=-25)
                st.plotly_chart(fig_meteo)

        with cm2:
            if not pista_strat.empty:
                fig_pista = px.bar(
                    pista_strat,
                    x="tipo_pista",
                    y="n_acidentes",
                    color="fase_dia_agrupada" if "fase_dia_agrupada" in pista_strat.columns else None,
                    barmode="group",
                    title="Causas de Visibilidade/Reação por Tipo de Pista",
                    labels={"tipo_pista": "Tipo de Pista", "n_acidentes": "Acidentes"},
                    color_discrete_map=PHASE_COLORS,
                )
                st.plotly_chart(fig_pista)

    st.markdown("---")

    # =========================================================================
    # 5. TENDÊNCIAS TEMPORAIS
    # =========================================================================
    st.subheader("📈 Evolução Temporal dos Acidentes")

    anos_presentes = sorted([int(a) for a in data["ano"].dropna().unique()]) if "ano" in data.columns else []
    tem_multiplos_meses = "ano_mes" in data.columns and data["ano_mes"].nunique() > 1

    if len(anos_presentes) == 1 and tem_multiplos_meses:
        # Série mensal para ano único (ex: 2026 de janeiro a agosto)
        st.info(f"📅 Exibindo série temporal mensal para o ano de {anos_presentes[0]} ({data['ano_mes'].nunique()} meses disponíveis na base).")
        tendencia_mensal = (
            data.groupby(["ano_mes", "fase_dia_agrupada"], observed=True)
            .size()
            .reset_index(name="n_acidentes")
        )
        fig_temp = px.line(
            tendencia_mensal,
            x="ano_mes",
            y="n_acidentes",
            color="fase_dia_agrupada",
            markers=True,
            title=f"Evolução Mensal de Acidentes ({anos_presentes[0]})",
            labels={"ano_mes": "Mês", "n_acidentes": "Acidentes", "fase_dia_agrupada": "Período"},
            color_discrete_map=PHASE_COLORS,
        )
        st.plotly_chart(fig_temp)

    elif len(anos_presentes) > 1:
        tab_ano, tab_mes = st.tabs(["📅 Evolução Anual", "📊 Evolução Mensal Detalhada"])
        with tab_ano:
            tendencia_ano = (
                data.groupby(["ano", "fase_dia_agrupada"], observed=True)
                .size()
                .reset_index(name="n_acidentes")
            )
            fig_ano = px.line(
                tendencia_ano,
                x="ano",
                y="n_acidentes",
                color="fase_dia_agrupada",
                markers=True,
                title=f"Evolução Anual ({anos_presentes[0]} - {anos_presentes[-1]})",
                labels={"ano": "Ano", "n_acidentes": "Acidentes", "fase_dia_agrupada": "Período"},
                color_discrete_map=PHASE_COLORS,
            )
            fig_ano.update_layout(xaxis_type="category")
            st.plotly_chart(fig_ano)

        with tab_mes:
            if tem_multiplos_meses:
                tendencia_mes = (
                    data.groupby(["ano_mes", "fase_dia_agrupada"], observed=True)
                    .size()
                    .reset_index(name="n_acidentes")
                )
                fig_mes = px.line(
                    tendencia_mes,
                    x="ano_mes",
                    y="n_acidentes",
                    color="fase_dia_agrupada",
                    markers=True,
                    title="Evolução Mensal Histórica",
                    labels={"ano_mes": "Ano-Mês", "n_acidentes": "Acidentes"},
                    color_discrete_map=PHASE_COLORS,
                )
                fig_mes.update_layout(xaxis_tickangle=-45)
                n_meses_unicos = tendencia_mes["ano_mes"].nunique()
                if n_meses_unicos > 36:
                    fig_mes.update_xaxes(dtick=6)
                elif n_meses_unicos > 12:
                    fig_mes.update_xaxes(dtick=3)
                st.plotly_chart(fig_mes)

    st.markdown("---")

    # =========================================================================
    # 6. PERFIL DEMOGRÁFICO DOS ENVOLVIDOS, FROTA VEICULAR E TIPOLOGIA DOS ACIDENTES
    # =========================================================================
    st.subheader("👥 Perfil Demográfico dos Envolvidos, Frota Veicular e Tipologia dos Acidentes")
    st.markdown(
        """
        Esta seção detalha o perfil dos indivíduos envolvidos nos sinistros, estratificando por tipo de envolvimento,
        sexo, faixas etárias, frota veicular e tipologia dos acidentes cruzada com as fases do dia.
        """
    )

    pessoas_data = analyzer.filtered_pessoas if analyzer.filtered_pessoas is not None else pd.DataFrame()
    veiculos_data = analyzer.filtered_veiculos if analyzer.filtered_veiculos is not None else pd.DataFrame()

    tab_env, tab_idade, tab_sexo, tab_frota, tab_tipo_acid = st.tabs([
        "👥 Tipo de Envolvimento",
        "🎂 Faixa Etária & Gravidade",
        "⚧️ Sexo & Letalidade",
        "🚛 Frota Veicular",
        "💥 Tipologia do Acidente",
    ])

    with tab_env:
        if not pessoas_data.empty:
            res_env = compute_envolvimento_analysis(pessoas_data)
            tbl_env = res_env.get("resumo_envolvimento", pd.DataFrame())
            cruz_env = res_env.get("cruzamento_fase_dia", pd.DataFrame())

            if not tbl_env.empty:
                tbl_env = tbl_env.copy()
                tbl_env["tipo_envolvido"] = _public_label_series(tbl_env["tipo_envolvido"])
                col_e1, col_e2 = st.columns([3, 2])
                with col_e1:
                    fig_env = px.bar(
                        tbl_env,
                        x="tipo_envolvido",
                        y=["mortos", "feridos_graves", "feridos_leves"],
                        title="Vítimas por Tipo de Envolvimento",
                        labels={"value": "Pessoas", "tipo_envolvido": "Envolvimento", "variable": "Gravidade"},
                        color_discrete_map=SEVERITY_COLORS,
                        barmode="stack",
                    )
                    st.plotly_chart(fig_env)

                with col_e2:
                    fig_taxa_env = px.bar(
                        tbl_env,
                        x="tipo_envolvido",
                        y="taxa_mortalidade_pct",
                        title="Taxa de Mortalidade por Envolvimento (%)",
                        labels={"taxa_mortalidade_pct": "Mortalidade (%)", "tipo_envolvido": "Envolvimento"},
                        color_discrete_sequence=[COLOR_PALETTE["taxa"]],
                    )
                    st.plotly_chart(fig_taxa_env)

                st.dataframe(
                    tbl_env[[
                        "tipo_envolvido", "total_envolvidos", "mortos", "feridos_graves",
                        "feridos_leves", "ilesos", "taxa_mortalidade_pct", "prop_total_mortos_pct"
                    ]],
                    column_config={
                        "tipo_envolvido": "Tipo de Envolvimento",
                        "total_envolvidos": st.column_config.NumberColumn("Total Envolvidos", format="%d"),
                        "mortos": st.column_config.NumberColumn("Óbitos", format="%d"),
                        "feridos_graves": st.column_config.NumberColumn("Feridos Graves", format="%d"),
                        "feridos_leves": st.column_config.NumberColumn("Feridos Leves", format="%d"),
                        "ilesos": st.column_config.NumberColumn("Ilesos", format="%d"),
                        "taxa_mortalidade_pct": st.column_config.NumberColumn("Taxa Mortalidade (%)", format="%.2f%%"),
                        "prop_total_mortos_pct": st.column_config.NumberColumn("Part. nos Óbitos (%)", format="%.2f%%"),
                    },
                    hide_index=True,
                    width="stretch",
                )

                if not cruz_env.empty and "fase_dia_oficial" in cruz_env.columns:
                    st.markdown("##### 🌙 Cruzamento: Tipo de Envolvimento por Fase do Dia")
                    fig_cruz_env = px.bar(
                        cruz_env,
                        x="tipo_envolvido",
                        y="mortos",
                        color="fase_dia_oficial",
                        barmode="group",
                        title="Óbitos por Tipo de Envolvimento e Fase do Dia",
                        labels={"mortos": "Óbitos", "tipo_envolvido": "Envolvimento", "fase_dia_oficial": "Fase do Dia"},
                        color_discrete_map=PHASE_COLORS,
                    )
                    st.plotly_chart(fig_cruz_env)
        else:
            st.info("ℹ️ Dados de pessoas não disponíveis para os filtros atuais.")

    with tab_idade:
        if not pessoas_data.empty:
            res_idade = compute_faixa_etaria_analysis(pessoas_data)
            tbl_faixa = res_idade.get("resumo_faixa_etaria", pd.DataFrame())
            tbl_estat = res_idade.get("idade_por_gravidade", pd.DataFrame())
            qual_idade = res_idade.get("metricas_qualidade_idade", {})

            col_q1, col_q2, col_q3 = st.columns(3)
            col_q1.metric("Idades Válidas (0 a 110 anos)", f"{qual_idade.get('idades_validas', 0):,} ({qual_idade.get('perc_idades_validas', 0.0):.1f}%)")
            col_q2.metric("Inconsistentes / Não Informadas", f"{qual_idade.get('idades_inconsistentes_ou_ausentes', 0):,} ({qual_idade.get('perc_inconsistentes', 0.0):.1f}%)")
            col_q3.metric("Registros com Idade > 110 anos", f"{qual_idade.get('idades_superiores_110_anos', 0):,}", help="Valores biológicos implausíveis tratados estritamente como inconsistentes")

            if not tbl_faixa.empty:
                col_i1, col_i2 = st.columns(2)
                with col_i1:
                    fig_faixa = px.bar(
                        tbl_faixa,
                        x="faixa_etaria",
                        y="total_pessoas",
                        title="Distribuição de Pessoas Envolvidas por Faixa Etária",
                        labels={"faixa_etaria": "Faixa Etária", "total_pessoas": "Pessoas"},
                        color_discrete_sequence=[COLOR_PALETTE["contagem"]],
                    )
                    fig_faixa.update_layout(showlegend=False, xaxis_tickangle=-25)
                    st.plotly_chart(fig_faixa)

                with col_i2:
                    fig_obitos_faixa = px.bar(
                        tbl_faixa,
                        x="faixa_etaria",
                        y="mortos",
                        title="Óbitos por Faixa Etária",
                        labels={"faixa_etaria": "Faixa Etária", "mortos": "Óbitos"},
                        color_discrete_sequence=[COLOR_PALETTE["obitos"]],
                    )
                    fig_obitos_faixa.update_layout(xaxis_tickangle=-25)
                    st.plotly_chart(fig_obitos_faixa)

                st.markdown("##### 📊 Estatísticas Descritivas de Idade por Nível de Severidade")
                if not tbl_estat.empty:
                    st.dataframe(
                        tbl_estat,
                        hide_index=True,
                        width="stretch",
                    )
        else:
            st.info("ℹ️ Dados de idade não disponíveis.")

    with tab_sexo:
        if not pessoas_data.empty:
            res_sexo = compute_sexo_analysis(pessoas_data)
            tbl_sexo = res_sexo.get("resumo_sexo", pd.DataFrame())

            if not tbl_sexo.empty:
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    fig_sexo_p = px.pie(
                        tbl_sexo,
                        names="sexo",
                        values="total_pessoas",
                        title="Distribuição de Envolvidos por Sexo",
                        hole=0.4,
                        color="sexo",
                        color_discrete_map=SEX_COLORS,
                    )
                    st.plotly_chart(fig_sexo_p)

                with col_s2:
                    fig_sexo_m = px.bar(
                        tbl_sexo,
                        x="sexo",
                        y="taxa_mortalidade_pct",
                        title="Taxa de Mortalidade por Sexo (%)",
                        labels={"taxa_mortalidade_pct": "Mortalidade (%)", "sexo": "Sexo"},
                        color="sexo",
                        color_discrete_map=SEX_COLORS,
                    )
                    st.plotly_chart(fig_sexo_m)

                st.dataframe(
                    tbl_sexo[[
                        "sexo", "total_pessoas", "mortos", "feridos_graves",
                        "feridos_leves", "ilesos", "taxa_mortalidade_pct", "prop_total_mortos_pct"
                    ]],
                    column_config={
                        "sexo": "Sexo",
                        "total_pessoas": st.column_config.NumberColumn("Total Pessoas", format="%d"),
                        "mortos": st.column_config.NumberColumn("Óbitos", format="%d"),
                        "feridos_graves": st.column_config.NumberColumn("Feridos Graves", format="%d"),
                        "feridos_leves": st.column_config.NumberColumn("Feridos Leves", format="%d"),
                        "ilesos": st.column_config.NumberColumn("Ilesos", format="%d"),
                        "taxa_mortalidade_pct": st.column_config.NumberColumn("Taxa Mortalidade (%)", format="%.2f%%"),
                        "prop_total_mortos_pct": st.column_config.NumberColumn("Part. nos Óbitos (%)", format="%.2f%%"),
                    },
                    hide_index=True,
                    width="stretch",
                )
        else:
            st.info("ℹ️ Dados de sexo não disponíveis.")

    with tab_frota:
        if not veiculos_data.empty:
            tbl_veic = compute_veiculo_analysis(veiculos_data, pessoas_data)
            if not tbl_veic.empty:
                top_v = tbl_veic.head(10)
                fig_v = px.bar(
                    top_v,
                    x="tipo_veiculo",
                    y="total_veiculos",
                    title="Top 10 Tipos de Veículos Envolvidos em Sinistros",
                    labels={"total_veiculos": "Veículos", "tipo_veiculo": "Tipo de Veículo"},
                    color_discrete_sequence=[COLOR_PALETTE["contagem"]],
                )
                fig_v.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(fig_v)

                st.dataframe(
                    tbl_veic,
                    column_config={
                        "tipo_veiculo": "Tipo de Veículo",
                        "total_veiculos": st.column_config.NumberColumn("Total Veículos", format="%d"),
                        "total_ocupantes": st.column_config.NumberColumn("Total Ocupantes", format="%d"),
                        "mortos": st.column_config.NumberColumn("Óbitos de Ocupantes", format="%d"),
                        "feridos_graves": st.column_config.NumberColumn("Feridos Graves", format="%d"),
                        "feridos_leves": st.column_config.NumberColumn("Feridos Leves", format="%d"),
                        "taxa_letalidade_ocupante_pct": st.column_config.NumberColumn("Letalidade Ocupante (%)", format="%.2f%%"),
                    },
                    hide_index=True,
                    width="stretch",
                )
        else:
            st.info("ℹ️ Dados de frota veicular não disponíveis.")

    with tab_tipo_acid:
        res_tipo = compute_tipo_acidente_analysis(data)
        tbl_tipo = res_tipo.get("resumo_tipo_acidente", pd.DataFrame())
        cruz_tipo = res_tipo.get("cruzamento_fase_dia", pd.DataFrame())

        if not tbl_tipo.empty:
            top_t = tbl_tipo.head(10)
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                fig_tipo_acid = px.bar(
                    top_t,
                    x="tipo_acidente",
                    y="mortos",
                    title="Top 10 Tipos de Acidentes por Número de Óbitos",
                    labels={"mortos": "Óbitos", "tipo_acidente": "Tipo de Acidente"},
                    color_discrete_sequence=[COLOR_PALETTE["obitos"]],
                )
                fig_tipo_acid.update_layout(xaxis_tickangle=-35)
                st.plotly_chart(fig_tipo_acid)

            with col_t2:
                fig_tipo_taxa = px.bar(
                    top_t,
                    x="tipo_acidente",
                    y="obitos_por_100_acidentes",
                    title="Óbitos por 100 Acidentes por Tipologia",
                    labels={"obitos_por_100_acidentes": "Óbitos / 100 Ac.", "tipo_acidente": "Tipo de Acidente"},
                    color_discrete_sequence=[COLOR_PALETTE["taxa"]],
                )
                fig_tipo_taxa.update_layout(xaxis_tickangle=-35)
                st.plotly_chart(fig_tipo_taxa)

            st.dataframe(
                tbl_tipo[[
                    "tipo_acidente", "n_acidentes", "mortos", "feridos_graves",
                    "total_feridos", "acidentes_fatais", "obitos_por_100_acidentes", "prop_acidentes_fatais_pct"
                ]],
                column_config={
                    "tipo_acidente": "Tipo de Acidente",
                    "n_acidentes": st.column_config.NumberColumn("Acidentes", format="%d"),
                    "mortos": st.column_config.NumberColumn("Óbitos", format="%d"),
                    "feridos_graves": st.column_config.NumberColumn("Feridos Graves", format="%d"),
                    "total_feridos": st.column_config.NumberColumn("Total Feridos", format="%d"),
                    "acidentes_fatais": st.column_config.NumberColumn("Sinistros Fatais", format="%d"),
                    "obitos_por_100_acidentes": st.column_config.NumberColumn("Óbitos / 100 Ac.", format="%.2f"),
                    "prop_acidentes_fatais_pct": st.column_config.NumberColumn("% Fatais", format="%.2f%%"),
                },
                hide_index=True,
                width="stretch",
            )

            if not cruz_tipo.empty and "fase_dia_oficial" in cruz_tipo.columns:
                st.markdown("##### 🌙 Tipologia de Acidentes Cruzada com a Fase do Dia")
                top_tipos_nomes = list(top_t["tipo_acidente"].head(6))
                cruz_top = cruz_tipo[cruz_tipo["tipo_acidente"].isin(top_tipos_nomes)].copy()
                fig_cruz_t = px.bar(
                    cruz_top,
                    x="tipo_acidente",
                    y="mortos",
                    color="fase_dia_oficial",
                    barmode="group",
                    title="Óbitos por Tipologia de Sinistro nas Fases do Dia (Top Tipos)",
                    labels={"mortos": "Óbitos", "tipo_acidente": "Tipo de Acidente", "fase_dia_oficial": "Fase do Dia"},
                    color_discrete_map=PHASE_COLORS,
                )
                fig_cruz_t.update_layout(xaxis_tickangle=-25)
                st.plotly_chart(fig_cruz_t)

    st.markdown("---")

    # =========================================================================
    # 7. RANKING DE TRECHOS CRÍTICOS E DIMENSIONAMENTO SOLAR
    # =========================================================================
    st.subheader("🚨 Priorização de Trechos Críticos para Iluminação Solar")

    # Controles na sidebar para parametrização de engenharia
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔧 Parâmetros de Dimensionamento e Finanças")
    spacing_m = st.sidebar.slider(
        "Espaçamento entre Postes (m)",
        min_value=20,
        max_value=100,
        value=DEFAULT_SPACING_M,
        step=5,
        help="Distância linear média entre luminárias solares (padrão: 50 m)"
    )
    comprimento_km = st.sidebar.slider(
        "Extensão do Trecho Segmentado (km)",
        min_value=0.5,
        max_value=10.0,
        value=DEFAULT_COMPRIMENTO_TRECHO_KM,
        step=0.5,
        help="Comprimento de cada segmento viário agrupado (padrão: 2.0 km)"
    )
    top_n_trechos = st.sidebar.slider(
        "Quantidade de Trechos Prioritários (Top N)",
        min_value=5,
        max_value=200,
        value=DEFAULT_TRECHOS_TOP_N,
        step=5,
        help="Número de trechos mais críticos selecionados para intervenção solar"
    )

    cenario_selecionado = st.sidebar.selectbox(
        "Cenário de Equipamento Solar (CAPEX)",
        options=["cenario_d", "cenario_a", "cenario_b", "cenario_c", "cenario_e"],
        index=0,
        format_func=lambda c: {
            "cenario_d": "Cenário D — Conceitual Compacto 8m/40W (R$ 22.310 - Base)",
            "cenario_a": "Cenário A — Meta Histórica 8m/60W (R$ 15.000)",
            "cenario_b": "Cenário B — Comercial 6m/40W (R$ 17.018,85)",
            "cenario_c": "Cenário C — Comercial 8m/80W (R$ 28.288,85)",
            "cenario_e": "Cenário E — 8m/80W com Bateria Reforçada (R$ 34.038,85)",
        }.get(c, c),
        help="Define o conjunto de luminária, poste, painel e bateria para cálculo do CAPEX por trecho e projeto."
    )

    criterio_ranking = st.sidebar.selectbox(
        "Critério de Ranqueamento",
        options=["iluminacao_solar", "geral"],
        format_func=lambda x: "Prioridade para Iluminação Solar (Foco Noturno e Severidade)" if x == "iluminacao_solar" else "Ranking Geral de Acidentes 24h",
    )

    # Execução da análise de trechos com segmentação regular
    with st.spinner("⚙️ Processando segmentação viária e modelo financeiro..."):
        top_df, agregados = analyzer.analyze_top_n(
            df=data,
            top_n=top_n_trechos,
            comprimento_km=comprimento_km,
            spacing_m=spacing_m,
            criterio_ranking=criterio_ranking,
            cenario_id=cenario_selecionado,
        )

    if not top_df.empty and agregados:
        dim = agregados.get("dimensionamento") or {}
        postes_trecho = dim.get("postes_por_trecho", int(np.ceil(comprimento_km * 1000 / spacing_m)))
        total_postes = dim.get("total_postes", postes_trecho * len(top_df))

        # Painel Resumo Financeiro
        vidas_salvas = agregados.get('vidas_salvas_ano', 0.0)
        graves_evitados = agregados.get('graves_evitados_ano', 0.0)
        leves_evitados = agregados.get('leves_evitados_ano', 0.0)
        mortos_acc = top_df['mortos_noturno'].sum() if 'mortos_noturno' in top_df.columns else 0
        anos_base = agregados.get('anos_base', 1.0)

        st.html(
            f"""
            <div class="metric-container">
                <h4>💰 Resumo da Modelagem Financeira e Dimensionamento — Top {len(top_df)} Trechos</h4>
                <div style="display: flex; justify-content: space-between; flex-wrap: wrap; margin-top: 10px;">
                    <div style="flex: 1; min-width: 200px; padding: 5px;">
                        <p><strong>Extensão Total Coberta:</strong> {len(top_df) * comprimento_km:.1f} km</p>
                        <p><strong>Postes Solares por Trecho:</strong> {postes_trecho} unidades ({comprimento_km*1000:.0f}m / {spacing_m}m)</p>
                        <p><strong>Total de Postes Solares:</strong> {total_postes:,} unidades</p>
                    </div>
                    <div style="flex: 1; min-width: 200px; padding: 5px;">
                        <p><strong>Investimento Total (CAPEX):</strong> R$ {agregados['investimento_total']:,.2f}</p>
                        <p><strong>Benefício Social Anual Bruto:</strong> R$ {agregados['economia_anual']:,.2f}</p>
                        <p><strong>Benefício Social Anual Líquido:</strong> R$ {agregados['economia_liquida_anual']:,.2f}</p>
                    </div>
                    <div style="flex: 1; min-width: 200px; padding: 5px;">
                        <p><strong>VPL (15 anos, taxa 8% a.a.):</strong> R$ {agregados['vpl']:,.2f}</p>
                        <p><strong>TIR Social:</strong> {agregados['tir']*100:.2f}% a.a.</p>
                        <p><strong>Payback Simples / Descontado:</strong> {agregados['payback_simples_anos']:.2f} anos / {agregados['payback_descontado_anos']:.2f} anos</p>
                        <p><strong>Vidas Humanas Salvas/Ano:</strong> {vidas_salvas:.1f} vidas/ano</p>
                    </div>
                </div>
            </div>
            """
        )

        # Memória de cálculo das vidas salvas/ano
        n_trechos_kpi = len(top_df)
        capex_total_kpi = agregados.get('capex_total', 0.0)
        economia_bruta_kpi = agregados.get('economia_anual', 0.0)
        economia_liq_kpi = agregados.get('economia_liquida_anual', 0.0)
        payback_kpi = agregados.get('payback_simples_anos', 0.0)
        anos_list = sorted([int(a) for a in data["ano"].dropna().unique()]) if "ano" in data.columns else []
        anos_str = f"{len(anos_list)} anos ({', '.join(str(a) for a in anos_list)})" if anos_list else f"{anos_base:.1f} anos"

        with st.expander(f"🧮 Memória de Cálculo Científico: Como as {vidas_salvas:.1f} vidas salvas/ano foram estimadas", expanded=False):
            st.markdown(
                f"""
                **Rastreabilidade Estrita aos Dados:**
                1. **Vítimas Noturnas nos {n_trechos_kpi} Trechos Prioritários:** Foram registrados **{mortos_acc} óbitos noturnos** nos {n_trechos_kpi} trechos contemplados durante o período da base ({anos_base:.1f} anos analisados: {anos_str}).
                2. **Taxa Anual Baseline:** `{mortos_acc} óbitos / {anos_base:.1f} anos = {mortos_acc / anos_base:.1f} óbitos noturnos/ano` nos trechos prioritários.
                3. **Fator de Redução por Iluminação Viária (Simulação CMF):** Adotou-se **35% de redução esperada** com base no catálogo de contramedidas recomendadas da *Federal Highway Administration (FHWA)*.
                4. **Cálculo de Vidas Salvas:** `{(mortos_acc / anos_base):.1f} óbitos/ano × 35% = {vidas_salvas:.1f} vidas humanas salvas por ano`.
                5. **Valoração Socioeconômica (IPEA/PRF):**
                   - Vidas Salvas: `{vidas_salvas:.1f} × R$ 5.787.720,00 = R$ {vidas_salvas * 5787720:,.2f}`
                   - Feridos Graves Evitados: `{graves_evitados:.1f}/ano × R$ 90.000,00 = R$ {graves_evitados * 90000:,.2f}`
                   - Feridos Leves Evitados: `{leves_evitados:.1f}/ano × R$ 25.000,00 = R$ {leves_evitados * 25000:,.2f}`
                   - **Benefício Social Bruto Anual:** **R$ {economia_bruta_kpi:,.2f}**.
                   - **Benefício Social Líquido Anual:** **R$ {economia_liq_kpi:,.2f}**.
                   - **Payback Simples:** `{format_pt_br_currency(capex_total_kpi)} / {format_pt_br_currency(economia_liq_kpi)} = {payback_kpi:.2f} anos`.
                """
            )

        # =====================================================================
        # BALANÇO ENERGÉTICO DETALHADO (8m / 40W / 240Wp / 2.500Wh LiFePO4)
        # =====================================================================
        balanco_eng = calcular_balanco_energetico_detalhado()
        with st.expander("⚡ Balanço Energético Detalhado e Autonomia (Cenário Compacto 8m / 40W)", expanded=False):
            st.markdown(
                f"""
                **Dimensionamento Elétrico e Balanço Energético Auditado:**
                - **Luminária LED Viária:** 40 W de alta eficiência (140 lm/W).
                - **Perfil Noturno Inteligente (12h):**
                  - 4h de fluxo intenso a 100% (40 W): **160 Wh**
                  - 4h normal a 80% (32 W): **128 Wh**
                  - 4h de repouso a 60% (24 W): **96 Wh**
                  - *Subtotal LED:* **384 Wh por noite**
                - **Supervisão e Telemetria Remota:** 2 W contínuos (24h) = **48 Wh por dia**.
                - **Consumo Total Diário Ponderado:** `{balanco_eng['consumo_led_wh']:.0f} Wh + {balanco_eng['consumo_telemetria_wh']:.0f} Wh = {balanco_eng['consumo_total_diario_wh']:.0f} Wh/dia`.
                - **Demanda para 3 Noites de Autonomia Estrita:** `{balanco_eng['consumo_total_diario_wh']:.0f} Wh × 3 = {balanco_eng['consumo_3_noites_wh']:.0f} Wh`.
                
                **Banco de Baterias LiFePO4 (2.500 Wh nominais):**
                - **Profundidade de Descarga (DoD):** 80% (preserva 3.000+ ciclos úteis).
                - **Eficiência Bateria / MPPT / Driver:** 90%.
                - **Capacidade Útil no Início da Vida (BOL):** `{balanco_eng['capacidade_util_bol_wh']:.1f} Wh úteis`.
                - **Capacidade Útil no Fim da Vida (EOL - 80% remanescente):** `{balanco_eng['capacidade_util_eol_wh']:.1f} Wh úteis`.
                - **Autonomia Efetiva com ZERO Geração Solar:**
                  - Em Início de Vida (BOL): **{balanco_eng['autonomia_zero_sol_bol_noites']:.2f} noites** (atende a meta de 3 noites com folga de 39%).
                  - Em Fim de Vida (EOL): **{balanco_eng['autonomia_zero_sol_eol_noites']:.2f} noites** (permanece acima do limite normativo de 3 noites).
                
                **Geração Solar e Recuperação da Carga:**
                - **Módulo Fotovoltaico Compacto:** 240 Wp integrado ao topo a 22°.
                - **Geração a Sol Pleno (4,5 HSP, PR 80%):** `{balanco_eng['geracao_solar_sol_pleno_wh']:.1f} Wh/dia` (excedente diário de `{balanco_eng['excedente_diario_sol_wh']:.1f} Wh/dia`).
                - **Dias para Recuperação Completa:** `{balanco_eng['consumo_3_noites_wh']:.0f} Wh / {balanco_eng['excedente_diario_sol_wh']:.1f} Wh/dia = {balanco_eng['dias_recarga_apos_3_noites']:.1f} dias de sol pleno`.
                - **Operação em Dias Nublados:** Gera `{balanco_eng['geracao_solar_dia_nublado_wh']:.1f} Wh/dia` (déficit diário de `{abs(balanco_eng['balanco_liquido_nublado_wh']):.1f} Wh/dia`, suportando até {balanco_eng['capacidade_util_bol_wh'] / abs(balanco_eng['balanco_liquido_nublado_wh']):.1f} dias nublados consecutivos em início de vida [BOL] e até {balanco_eng['capacidade_util_eol_wh'] / abs(balanco_eng['balanco_liquido_nublado_wh']):.1f} dias em fim de vida [EOL 80%]).
                
                *{balanco_eng['status_aviso']}*
                """
            )

        # =====================================================================
        # SEGURANÇA LUMINOTÉCNICA E ABNT NBR 5101:2024
        # =====================================================================
        with st.expander("🛡️ Segurança Luminotécnica e Validação Pendente (ABNT NBR 5101:2024)", expanded=False):
            st.warning("⚠️ **Status da Validação Luminotécnica:** PENDENTE DE ESTUDO COMPUTACIONAL (DIALux EVO / Relux).")
            st.markdown(
                r"""
                **Aviso Metodológico de Engenharia de Tráfego:**  
                A potência preliminar de 40W é uma **hipótese de trabalho conceitual**, não devendo ser considerada automaticamente suficiente para rodovias federais.  
                A conformidade luminotécnica com a norma **ABNT NBR 5101:2024 (Iluminação Pública e Rodoviária)** depende de múltiplos fatores que devem ser modelados em software especializado antes de qualquer instalação:
                - **Classificação da Via (Classes V1 a V5):** Exige luminância média de pista ($L_m$) entre 1,0 e 2,0 cd/m², uniformidade geral ($U_0 \ge 0,35$ a $0,40$) e controle de ofuscamento ($TI \le 10\%$).
                - **Geometria da Rodovia:** Pista simples (7m) vs pista dupla (duas faixas de 3,5m + acostamento), canteiro central e defensas metálicas.
                - **Geometria de Montagem:** Altura do poste (8m), ângulo de inclinação do braço, avanço sobre a pista (1,5m) e o espaçamento configurado (**50 metros**).
                - **Distribuição Fotométrica:** A luminária deve possuir curva IESNA Tipo II Média / Curta com corte total (*Full Cutoff*) para direcionar o fluxo luminoso exclusivamente à faixa de rolamento sem poluição luminosa ou ofuscamento aos motoristas.
                """
            )

        # =====================================================================
        # MODELAGEM ORÇAMENTÁRIA MULTI-CENÁRIOS (CENÁRIOS A A E)
        # =====================================================================
        orcamento_multi = calcular_orcamento_cenarios(
            top_segments_df=top_df,
            n_trechos=len(top_df),
            comprimento_km=comprimento_km,
            espacamento_m=spacing_m,
            anos_base_dados=anos_base,
            taxa_reducao=EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"],
            taxa_desconto=FINANCIAL_PARAMS["taxa_desconto_anual"],
            anos_vida_util=FINANCIAL_PARAMS["vida_util_anos"],
        )

        with st.expander("📊 Comparativo de Orçamentos e Cenários (A a E)", expanded=True):
            st.markdown("##### 🏷️ Comparação Dinâmica dos Cenários Orçamentários")
            st.caption("Substituição do modelo orçamentário único por múltiplos cenários comparáveis com custos pesquisados, comerciais e hipóteses conceituais.")

            comp_df = orcamento_multi["comparativo_df"]
            st.dataframe(
                comp_df,
                column_config={
                    "Cenário": "Cenário de Intervenção",
                    "Tipo": "Classificação",
                    "Altura": "Altura",
                    "LED": "LED",
                    "Custo Unitário (R$)": st.column_config.NumberColumn("Custo/Poste (R$)", format="R$ %.2f"),
                    "CAPEX Total (R$ M)": st.column_config.NumberColumn("CAPEX (R$ Milhões)", format="R$ %.2f M"),
                    "VPL 15 Anos (R$ M)": st.column_config.NumberColumn("VPL Social (R$ M)", format="R$ %.2f M"),
                    "TIR (% a.a.)": st.column_config.NumberColumn("TIR (% a.a.)", format="%.1f%%"),
                    "Payback Simples (anos)": st.column_config.NumberColumn("Payback Simples", format="%.2f anos"),
                    "Payback Descontado (anos)": st.column_config.NumberColumn("Payback Descontado", format="%.2f anos"),
                },
                hide_index=True,
                width="stretch",
            )

            # Gráfico de Barras Comparativo de CAPEX vs VPL
            fig_cen = go.Figure()
            fig_cen.add_trace(go.Bar(
                x=comp_df["Cenário"],
                y=comp_df["CAPEX Total (R$ M)"],
                name="CAPEX Inicial (R$ Milhões)",
                marker_color=COLOR_PALETTE["capex"],
            ))
            fig_cen.add_trace(go.Bar(
                x=comp_df["Cenário"],
                y=comp_df["VPL 15 Anos (R$ M)"],
                name="VPL Social Líquido Estimado (R$ Milhões)",
                marker_color=COLOR_PALETTE["beneficio_social"],
            ))
            fig_cen.update_layout(
                title="Comparativo Financeiro: Investimento Inicial (CAPEX) vs Retorno Social Líquido (VPL)",
                barmode="group",
                height=360,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_cen)

            # Detalhes dinâmicos das premissas de cada cenário baseados no dimensionamento real
            linhas_cenarios_md = ["**Detalhamento Técnico dos Cenários Orçamentários:**"]
            for _, r_c in comp_df.iterrows():
                pb_c = f"{r_c['Payback Simples (anos)']:.2f} anos" if r_c['Payback Simples (anos)'] < 100 else "> 15 anos"
                linhas_cenarios_md.append(
                    f"- **{r_c['Cenário']} ({r_c['Tipo']}):** {r_c['Altura']} / {r_c['LED']} | "
                    f"Custo Unitário: R$ {r_c['Custo Unitário (R$)']:,.2f} | "
                    f"CAPEX Total: **R$ {r_c['CAPEX Total (R$ M)']:.2f}M** | "
                    f"VPL Social: **R$ {r_c['VPL 15 Anos (R$ M)']:.2f}M** | "
                    f"Payback Simples: **{pb_c}**"
                )
            st.markdown("\n".join(linhas_cenarios_md))

        # Tabela completa de fluxo de caixa anual
        fluxo_df = agregados.get("tabela_fluxo_caixa_df")
        if fluxo_df is not None and not fluxo_df.empty:
            with st.expander("📈 Tabela de Fluxo de Caixa Anual Descontado (Anos 0 a 15)", expanded=False):
                st.dataframe(
                    fluxo_df,
                    column_config={
                        "ano": st.column_config.NumberColumn("Ano", format="%d"),
                        "capex": st.column_config.NumberColumn("CAPEX (R$)", format="R$ %.2f"),
                        "opex": st.column_config.NumberColumn("OPEX (R$)", format="R$ %.2f"),
                        "beneficio_bruto": st.column_config.NumberColumn("Benefício Bruto (R$)", format="R$ %.2f"),
                        "beneficio_liquido": st.column_config.NumberColumn("Benefício Líquido (R$)", format="R$ %.2f"),
                        "fator_desconto": st.column_config.NumberColumn("Fator Desc. (8%)", format="%.4f"),
                        "fluxo_descontado": st.column_config.NumberColumn("Fluxo Descontado (R$)", format="R$ %.2f"),
                        "saldo_acumulado_descontado": st.column_config.NumberColumn("Saldo Acum. Descontado (R$)", format="R$ %.2f"),
                    },
                    hide_index=True,
                    width="stretch",
                )

        # Tabela dos Top Trechos
        st.markdown(f"##### 📋 Tabela dos Top {len(top_df)} Trechos Prioritários")
        st.dataframe(
            top_df[[
                "ranking",
                "trecho",
                "n_acidentes",
                "mortos",
                "total_feridos",
                "score_prioridade",
                "confiabilidade_geo",
                "investimento_trecho",
                "economia_anual_trecho",
                "payback_anos",
            ]],
            column_config={
                "ranking": st.column_config.NumberColumn("#", format="%d"),
                "trecho": "Trecho Rodoviário Segmentado",
                "n_acidentes": st.column_config.NumberColumn("Acidentes Noturnos", format="%d"),
                "mortos": st.column_config.NumberColumn("Óbitos Noturnos", format="%d"),
                "total_feridos": st.column_config.NumberColumn("Feridos Noturnos", format="%d"),
                "score_prioridade": st.column_config.NumberColumn("Score Solar", format="%.1f"),
                "confiabilidade_geo": "Localização",
                "investimento_trecho": st.column_config.NumberColumn("CAPEX Trecho", format="R$ %.2f"),
                "economia_anual_trecho": st.column_config.NumberColumn("Benefício Anual", format="R$ %.2f"),
                "payback_anos": st.column_config.NumberColumn("Payback (anos)", format="%.2f"),
            },
            hide_index=True,
            width="stretch",
            height=380,
        )

        # Análise de Cenários e Sensibilidade
        cenarios = agregados.get("cenarios", {})
        if cenarios:
            st.markdown("##### 🎯 Análise de Cenários de Efetividade da Iluminação")
            cen_rows = []
            for k, c in cenarios.items():
                pb_str = f"{c['payback_simples']:.2f} anos" if c['payback_simples'] < 100 else "> 15 anos"
                cen_rows.append({
                    "Cenário": c["nome"],
                    "Redução Esperada": f"{c['taxa_reducao']:.0%}",
                    "Vidas Salvas/Ano": f"{c['vidas_salvas_ano']:.1f}",
                    "Benefício Social Anual": f"R$ {c['beneficio_anual_bruto']:,.2f}",
                    "VPL (15 anos, 8%)": f"R$ {c['vpl']:,.2f}",
                    "Payback Simples": pb_str,
                })
            st.dataframe(pd.DataFrame(cen_rows), hide_index=True, width="stretch")

    st.markdown("---")

    # =========================================================================
    # 7. MAPA GEOGRÁFICO INTERATIVO
    # =========================================================================
    st.subheader("🗺️ Mapa Geográfico de Ocorrências e Trechos Críticos")

    mask_map = (
        data["latitude"].notna() &
        data["longitude"].notna() &
        (data["latitude"] >= -34.0) & (data["latitude"] <= 5.5) &
        (data["longitude"] >= -74.0) & (data["longitude"] <= -32.0)
    )
    map_points = data[mask_map]

    if not map_points.empty:
        max_pts = APP_CONFIG.get("max_map_points", 800)
        total_valid_map = len(map_points)
        if total_valid_map > max_pts:
            st.caption(f"ℹ️ Exibindo amostra representativa de {max_pts} pontos georreferenciados (de {total_valid_map:,} totais) para otimizar fluidez de renderização.")
            map_sample = map_points.sample(max_pts, random_state=42)
        else:
            map_sample = map_points

        center_lat = float(map_sample["latitude"].median())
        center_lon = float(map_sample["longitude"].median())

        m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="OpenStreetMap")

        from folium.plugins import MarkerCluster
        cluster = MarkerCluster(name="Acidentes").add_to(m)

        for _, row in map_sample.iterrows():
            is_not = row.get("fase_dia_agrupada") == "Noturno" or row.get("fase_dia") == "noturno"
            is_fatal = row.get("acidente_fatal", 0) == 1
            color = "#d62728" if is_fatal else ("#1f77b4" if is_not else "#ff7f0e")

            popup_text = f"""
            <b>BR-{row.get('br', 'N/A')} KM {row.get('km', 'N/A')} ({row.get('uf', '')})</b><br/>
            Período: {row.get('fase_dia_oficial', row.get('fase_dia', ''))}<br/>
            Óbitos: {int(row.get('mortos', 0))}<br/>
            Feridos: {int(row.get('total_feridos', 0))}<br/>
            Causa: {row.get('causa_acidente', 'Não informada')}
            """

            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=4 if not is_fatal else 6,
                popup=popup_text,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=1,
            ).add_to(cluster)

        folium_static(m, width=1100, height=500)
    else:
        st.warning("⚠️ Não foram encontradas coordenadas geográficas válidas dentro do território nacional para os filtros selecionados.")

    st.markdown("---")

    # =========================================================================
    # 8. SUPERVISÃO REMOTA E TELEMETRIA DE INFRAESTRUTURA (CONCEITUAL)
    # =========================================================================
    st.subheader("📡 Supervisão Remota e Telemetria de Infraestrutura (Conceitual)")

    st.warning(
        "⚠️ **AVISO OBRIGATÓRIO DE SIMULAÇÃO:** O painel abaixo é uma **representação conceitual e simulada** "
        "dos requisitos funcionais de software para o monitoramento remoto de 4.000 postes solares ao longo dos 100 trechos críticos prioritários. "
        "**Não existem postes físicos instalados nesta etapa acadêmica do projeto.**"
    )

    t_col1, t_col2, t_col3, t_col4, t_col5, t_col6 = st.columns(6)
    t_col1.metric("Postes Ativos", "4.000 un", "100 Trechos")
    t_col2.metric("🟢 Operação Normal", "3.842 (96,1%)", "Sem alertas")
    t_col3.metric("🟡 Bateria Baixa", "78 (2,0%)", "SOC < 20%")
    t_col4.metric("🔴 Falha LED", "24 (0,6%)", "Substituição")
    t_col5.metric("🚨 Violação Gabinete", "14 (0,4%)", "Sensor intrusão")
    t_col6.metric("⚪ Sem Sinal", "24 (0,6%)", "Reconexão 4G")

    with st.expander("📋 Gestão Simulada de Incidentes e Demonstração de Ordem de Serviço (OS)", expanded=False):
        st.markdown(
            """
            Demonstração conceitual do ciclo de vida de supervisão de ativos (*Smart Asset Management*):  
            **Ciclo de Vida do Alerta:** `Alerta Detectado ➔ Ordem de Serviço Gerada ➔ Em Análise ➔ Equipe Técnica em Rota ➔ Manutenção Concluída`
            """
        )

        # Tabela de Incidentes Simulados
        incidentes_simulados = pd.DataFrame([
            {"Poste ID": "PST-SC-101-042", "Trecho": "BR-101 (SC) KM 144–146", "Tipo de Alerta": "🚨 Violação de Gabinete", "SOC Bateria": "82%", "LED": "OK", "Status OS": "Equipe Despachada", "Abertura": "30/10/2026 01:15"},
            {"Poste ID": "PST-SP-116-108", "Trecho": "BR-116 (SP) KM 220–222", "Tipo de Alerta": "🔴 Falha na Luminária LED", "SOC Bateria": "91%", "LED": "Circuito Aberto", "Status OS": "Em Análise", "Abertura": "29/10/2026 23:40"},
            {"Poste ID": "PST-MG-381-019", "Trecho": "BR-381 (MG) KM 480–482", "Tipo de Alerta": "🟡 Bateria Crítica (SOC 12%)", "SOC Bateria": "12%", "LED": "Dimerizado 20%", "Status OS": "Aberta", "Abertura": "30/10/2026 02:05"},
            {"Poste ID": "PST-PE-423-007", "Trecho": "BR-423 (PE) KM 126–128", "Tipo de Alerta": "⚪ Perda de Sinal (Timeout)", "SOC Bateria": "Desconhecido", "LED": "Último Estado Ligado", "Status OS": "Aguardando Reconexão", "Abertura": "30/10/2026 00:30"},
            {"Poste ID": "PST-PR-277-085", "Trecho": "BR-277 (PR) KM 310–312", "Tipo de Alerta": "🟠 Falha Carregamento PV", "SOC Bateria": "45%", "LED": "OK", "Status OS": "Em Atendimento", "Abertura": "29/10/2026 18:20"},
        ])

        st.dataframe(incidentes_simulados, hide_index=True, width="stretch")

        col_os_btn, col_os_msg = st.columns([1, 2])
        with col_os_btn:
            if st.button("🔧 Simular Emissão de Ordem de Serviço"):
                st.session_state["os_emitida"] = True

        with col_os_msg:
            if st.session_state.get("os_emitida"):
                st.success("✅ Ordem de Serviço Fictícia #OS-2026-8941 emitida com sucesso para o lote BR-101/SC! (Demonstração de integração de software)")

    st.markdown("---")

    # =========================================================================
    # 9. PROTÓTIPO 3D DO POSTE SOLAR INTELIGENTE COMPACTO
    # =========================================================================
    st.subheader("🌟 Protótipo 3D Interativo — Poste Solar Inteligente Compacto")
    col_3d_1, col_3d_2 = st.columns([3, 1])

    with col_3d_1:
        try:
            path_3d = Path(__file__).resolve().parent / "solar_post_3d.html"
            with open(path_3d, encoding="UTF-8") as f:
                html_3d = f.read()
            components.html(html_3d, height=640)
        except FileNotFoundError:
            st.error("Arquivo 'solar_post_3d.html' não encontrado.")

    with col_3d_2:
        st.html(
            """
            <div class="metric-container">
                <h4>🎮 Controles e Navegação 3D</h4>
                <p>Interaja com o modelo tridimensional com proporções de engenharia viária.</p>
                <p><strong>Recursos Interativos:</strong></p>
                <p>• 🌙 Alternar Modo Dia / Noite</p>
                <p>• 💡 Ligar / Desligar LED viário</p>
                <p>• 🔍 <strong>Modo Raio-X:</strong> Visualizar bateria LiFePO4 e MPPT internos</p>
                <p>• 🚗 <strong>Passagem de Veículo:</strong> Ativação do radar Doppler</p>
                <p>• 🚨 <strong>Simulação de Falhas:</strong> Violação, queima de LED, painel sem geração</p>
                <p>• 📷 Resetar Posição da Câmera</p>
                <hr style="margin: 8px 0;">
                <p><small><em>Nota de Rigor Acadêmico: Este modelo tridimensional constitui representação visual e conceitual de engenharia. A autonomia real depende de irradiação solar local (HSP), temperatura e perfil de tráfego.</em></small></p>
            </div>
            """
        )

    st.markdown("---")

    # =========================================================================
    # 10. GERAÇÃO E DOWNLOAD DO RELATÓRIO PDF CIENTÍFICO
    # =========================================================================
    st.subheader("📄 Relatório Técnico e Científico em PDF")
    st.markdown("Gere um relatório acadêmico completo com todas as seções metodológicas, tabelas e gráficos em alta resolução.")

    if st.button("📄 Gerar Relatório Científico Completo (PDF)", width="stretch", type="primary"):
        try:
            with st.spinner("📄 Compilando relatório PDF de acordo com as normas científicas..."):
                generator = ReportGenerator()
                report_buffer = generator.generate_accident_analysis_report(
                    filtered_data=data,
                    top_segments=top_df,
                    causas_df=analyzer.filtered_causas,
                    financial_summary=agregados,
                    quality_summary=quality,
                    pessoas_df=analyzer.filtered_pessoas,
                    veiculos_df=analyzer.filtered_veiculos,
                )

                session_id = st.session_state.get("session_id", "default")
                reports_dir = os.path.join("reports", session_id)
                os.makedirs(reports_dir, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"relatorio_cientifico_iluminar_{timestamp}.pdf"
                save_path = os.path.join(reports_dir, file_name)

                with open(save_path, "wb") as f:
                    f.write(report_buffer.getvalue())
                report_buffer.seek(0)

                st.download_button(
                    label=f"📥 Baixar Relatório PDF ({file_name})",
                    data=report_buffer,
                    file_name=file_name,
                    mime="application/pdf",
                    width="stretch",
                )
                st.success(f"✅ Relatório gerado com sucesso e arquivado em '{save_path}'!")
        except Exception as e:
            st.error(f"❌ Erro ao gerar relatório PDF: {str(e)}")

    gc.collect()


# ---------------------------------------------------------------------------
# Navegação progressiva.  A implementação anterior foi mantida acima como
# referência histórica, mas não é chamada: expanders/tabs do Streamlit não
# interrompem a execução do código que contêm.
# ---------------------------------------------------------------------------
def _time_module(name: str, started: float) -> None:
    timings = st.session_state.setdefault("module_timings", {})
    timings[name] = round(time.perf_counter() - started, 3)


def _period_label(data: pd.DataFrame) -> str:
    if "ano" not in data.columns or data["ano"].dropna().empty:
        return "período selecionado"
    years = sorted(data["ano"].dropna().astype(int).unique())
    return str(years[0]) if len(years) == 1 else f"{years[0]}–{years[-1]}"


def render_visao_geral(analyzer: AccidentAnalyzer) -> None:
    """Único módulo executado imediatamente após a ingestão."""
    started = time.perf_counter()
    data = analyzer.filtered_data
    total = len(data)
    mortos = int(data.get("mortos", pd.Series(dtype=int)).sum())
    feridos = int(data.get("total_feridos", pd.Series(dtype=int)).sum())
    fatais = int(data.get("acidente_fatal", pd.Series(dtype=int)).sum())
    comp = compute_day_vs_night_comparison(data)
    noite = (comp.get("noturno") or {}).get("mortos_por_100_acidentes", 0.0)
    dia = (comp.get("diurno") or {}).get("mortos_por_100_acidentes", 0.0)

    st.subheader("Visão geral")
    st.caption(f"Período ativo: {_period_label(data)} · filtros globais já aplicados")
    cols = st.columns(6)
    for col, label, value in zip(cols, [
        "Acidentes", "Pessoas mortas", "Pessoas feridas", "Acidentes fatais",
        "Óbitos / 100 acidentes", "Plena noite vs. pleno dia",
    ], [
        f"{total:,}", f"{mortos:,}", f"{feridos:,}", f"{fatais:,}",
        f"{(mortos / total * 100) if total else 0:.2f}", f"{noite:.2f} / {dia:.2f}",
    ]):
        col.metric(label, value)
    st.info("Os módulos analíticos, mapa, protótipo 3D e PDF são carregados apenas quando selecionados.")
    _time_module("Visão geral", started)


def render_analise_cientifica(analyzer: AccidentAnalyzer) -> None:
    started = time.perf_counter()
    data, causas = analyzer.filtered_data, analyzer.filtered_causas
    result = analyze_visibility_and_reaction(data, causas if causas is not None else pd.DataFrame())
    st.subheader("Análise científica: visibilidade e reação")
    st.caption(result.get("evidencias_texto", ""))
    pivot = result.get("pivot_causas", pd.DataFrame())
    if not pivot.empty:
        numeric = [c for c in pivot.columns if c.startswith("n_acidentes_")]
        if numeric:
            plot = pivot.sort_values(numeric[0], ascending=False).head(12)
            st.plotly_chart(px.bar(plot, x="causa_normalizada", y=numeric, barmode="group",
                                   title="Causas associadas à visibilidade/reação"), config={"displaylogo": False, "responsive": True})
    st.warning(result.get("limitacoes_texto", "Resultados observacionais; não estabelecem causalidade individual."))
    _time_module("Análise científica", started)


def render_perfil_vitimas(analyzer: AccidentAnalyzer) -> None:
    started = time.perf_counter()
    pessoas = analyzer.filtered_pessoas if analyzer.filtered_pessoas is not None else pd.DataFrame()
    veiculos = analyzer.filtered_veiculos if analyzer.filtered_veiculos is not None else pd.DataFrame()
    st.subheader("Perfil das vítimas e envolvidos")
    envolvimento = compute_envolvimento_analysis(pessoas).get("resumo_envolvimento", pd.DataFrame())
    if not envolvimento.empty:
        st.dataframe(envolvimento, hide_index=True, width="stretch")
    sexo = compute_sexo_analysis(pessoas).get("resumo_sexo", pd.DataFrame())
    if not sexo.empty:
        st.plotly_chart(px.bar(sexo, x=sexo.columns[0], y="mortos", title="Óbitos por sexo"), config={"displaylogo": False, "responsive": True})
    if not veiculos.empty and "tipo_veiculo" in veiculos:
        top = veiculos["tipo_veiculo"].fillna("Não informado").replace({"nan": "Não informado", "NaN": "Não informado"}).value_counts().head(12)
        st.plotly_chart(px.bar(top, title="Veículos envolvidos"), config={"displaylogo": False, "responsive": True})
    _time_module("Perfil de vítimas", started)


# Camada central de apresentação: mantém os DataFrames científicos intactos e
# impede que nomes de implementação sejam exibidos ao visitante.
PRESENTATION_LABELS = {
    "fase_dia": "Fase do Dia", "fase_dia_oficial": "Fase Oficial do Dia",
    "fase_dia_agrupada": "Período do Dia", "ano_mes": "Ano/Mês",
    "causa_normalizada": "Causa do Acidente", "tipo_envolvido": "Tipo de Envolvimento",
    "total_envolvidos": "Total de Envolvidos", "mortos_noturno": "Óbitos Noturnos",
    "n_acidentes_total": "Total de Acidentes", "n_acidentes_noturnos": "Acidentes Noturnos",
    "km_inicio": "KM Inicial", "km_fim": "KM Final", "taxa_mortalidade_pct": "Percentual de Mortalidade",
    "mortos_excepcionais_noturno": "Óbitos Noturnos em Eventos Excepcionais",
    "n_acidentes": "Acidentes", "total_mortos": "Óbitos", "total_feridos": "Feridos",
    "acidentes_fatais": "Acidentes Fatais", "obitos_por_100_acidentes": "Óbitos por 100 Acidentes",
    "prop_acidentes_fatais_pct": "Percentual de Acidentes Fatais", "value": "Valor da Métrica",
}
PLOTLY_CONFIG = {"displayModeBar": True, "displaylogo": False, "responsive": True}


def _public_label_series(values: pd.Series) -> pd.Series:
    """Normaliza apenas rótulos exibidos, preservando linhas e indicadores."""
    return values.astype(object).replace(
        r"(?i)^\s*(nan|none|null|n/a|<na>)\s*$", "Não informado", regex=True
    ).fillna("Não informado")


def present_dataframe(frame: pd.DataFrame, **kwargs: Any) -> None:
    """Mostra cópia rotulada, sem alterar estruturas usadas pelos cálculos."""
    public = frame.copy()
    text_columns = public.select_dtypes(include=["object", "string", "category"]).columns
    for column in text_columns:
        public[column] = _public_label_series(public[column])
    public = public.rename(columns=PRESENTATION_LABELS)
    st.dataframe(public, hide_index=True, use_container_width=True, **kwargs)


def present_plot(fig: Any) -> None:
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def financial_comparison_chart(scenarios: pd.DataFrame) -> go.Figure:
    """Distingue custo de VPL social estimado somente na apresentação."""
    fig = px.bar(
        scenarios, x="Cenário", y=["CAPEX Total (R$ M)", "VPL 15 Anos (R$ M)"],
        barmode="group", title="Comparativo Financeiro: Investimento Inicial (CAPEX) vs VPL Social Líquido",
        labels={"value": "R$ milhões", "variable": "Indicador"},
        color_discrete_map=FINANCIAL_CHART_COLORS,
    )
    fig.for_each_trace(
        lambda trace: trace.update(name="VPL social estimado (R$ M)")
        if trace.name == "VPL 15 Anos (R$ M)" else None
    )
    return fig


def _temporal_measure(frame: pd.DataFrame, group_cols: list[str], metric: str) -> pd.DataFrame:
    aggregated = frame.groupby(group_cols, observed=True).agg(
        acidentes=("id", "nunique"), obitos=("mortos", "sum"), feridos=("total_feridos", "sum"),
        acidentes_fatais=("acidente_fatal", "sum"),
    ).reset_index()
    if metric == "Óbitos por 100 acidentes":
        aggregated["valor"] = aggregated["obitos"] / aggregated["acidentes"].replace(0, np.nan) * 100
    elif metric == "Percentual de acidentes fatais":
        aggregated["valor"] = aggregated["acidentes_fatais"] / aggregated["acidentes"].replace(0, np.nan) * 100
    else:
        aggregated["valor"] = aggregated[{"Acidentes": "acidentes", "Óbitos": "obitos", "Feridos": "feridos", "Acidentes fatais": "acidentes_fatais"}[metric]]
    numeric = aggregated.select_dtypes(include=[np.number]).columns
    aggregated[numeric] = aggregated[numeric].fillna(0)
    return aggregated


def _render_evolucao_temporal_full(analyzer: AccidentAnalyzer) -> None:
    """Séries anuais/mensais sob demanda, a partir da base já filtrada."""
    started = time.perf_counter(); data = analyzer.filtered_data.copy()
    st.subheader("Evolução Temporal dos Acidentes Rodoviários")
    view = st.segmented_control("Visualização", ["Evolução Anual", "Evolução Mensal Detalhada"], default="Evolução Anual", key="temporal_view")
    metric = st.selectbox("Métrica", ["Acidentes", "Óbitos", "Feridos", "Acidentes fatais", "Óbitos por 100 acidentes", "Percentual de acidentes fatais"], key="temporal_metric")
    phase = st.selectbox("Fase do dia", ["Todas", "Diurno", "Noturno", "Crepúsculo", "Pleno dia", "Plena Noite", "Amanhecer", "Anoitecer"], key="temporal_phase")
    comparison = st.selectbox("Comparação", ["Totais absolutos", "Participação percentual", "Variação entre períodos"], key="temporal_comparison")
    if phase != "Todas":
        field = "fase_dia_agrupada" if phase in {"Diurno", "Noturno", "Crepúsculo"} else "fase_dia_oficial"
        if field in data: data = data[data[field].astype(str).str.casefold() == phase.casefold()]
    years = sorted(data["ano"].dropna().astype(int).unique()) if "ano" in data else []
    if 2026 in years and "mes" in data:
        months = sorted(data.loc[data["ano"] == 2026, "mes"].dropna().unique())
        if len(months) < 12: st.warning(f"2026 contém somente {len(months)} mês(es) observado(s); totais não são anualizados automaticamente.")
    if view == "Evolução Anual":
        grouping = st.radio("Séries", ["Três períodos agrupados", "Quatro fases oficiais"], horizontal=True, key="annual_series")
        phase_col = "fase_dia_agrupada" if grouping.startswith("Três") else "fase_dia_oficial"
        series = _temporal_measure(data, ["ano", phase_col], metric)
        if comparison == "Participação percentual": series["valor"] = series["valor"] / series.groupby("ano")["valor"].transform("sum").replace(0, np.nan) * 100
        elif comparison == "Variação entre períodos": series["valor"] = series.sort_values("ano").groupby(phase_col)["valor"].pct_change() * 100
        labels = {"ano": "Ano", phase_col: "Período do Dia", "valor": "Percentual (%)" if comparison != "Totais absolutos" else metric}
        fig = px.line(series, x="ano", y="valor", color=phase_col, markers=True, title="Evolução Anual dos Acidentes por Período", labels=labels, color_discrete_map=PHASE_COLORS)
        fig.update_xaxes(dtick=1, tickformat="d")
        present_plot(fig)
        annual = _temporal_measure(data, ["ano"], "Acidentes")
        annual["obitos_por_100"] = annual["obitos"] / annual["acidentes"].replace(0, np.nan) * 100
        annual["variacao_anual_pct"] = annual["acidentes"].pct_change() * 100
        present_dataframe(annual.rename(columns={"obitos_por_100": "Óbitos por 100 Acidentes", "variacao_anual_pct": "Variação anual (%)"}))
        st.caption("Agrupamentos: Diurno = Pleno dia; Noturno = Plena Noite; Crepúsculo = Amanhecer + Anoitecer. As quatro fases oficiais permanecem disponíveis no seletor.")
    else:
        if "ano_mes" not in data: st.info("A granularidade mensal não está disponível nesta base."); _time_module("Evolução temporal", started); return
        selected_years = st.multiselect("Anos para comparação sazonal", years, default=years, key="monthly_years")
        monthly = data[data["ano"].isin(selected_years)] if selected_years else data.iloc[0:0]
        split = st.checkbox("Separar por fase do dia", value=True, key="monthly_split")
        cols = ["ano_mes"] + (["fase_dia_oficial"] if split else [])
        series = _temporal_measure(monthly, cols, metric)
        fig = px.line(series, x="ano_mes", y="valor", color="fase_dia_oficial" if split else None, markers=True, title="Evolução Mensal Detalhada", labels={"ano_mes": "Ano/Mês", "valor": metric, "fase_dia_oficial": "Fase Oficial do Dia"}, hover_data={"acidentes": True, "obitos": True, "feridos": True}, color_discrete_map=PHASE_COLORS)
        fig.update_xaxes(tickangle=-45); present_plot(fig)
        if st.checkbox("Comparar sazonalidade por mês", key="seasonality") and "mes" in monthly:
            seasonal = _temporal_measure(monthly, ["ano", "mes"], metric)
            present_plot(px.line(seasonal, x="mes", y="valor", color="ano", markers=True, title="Sazonalidade: comparação entre anos", labels={"mes": "Mês", "valor": metric, "ano": "Ano"}))
    annual_all = _temporal_measure(data, ["ano"], "Acidentes") if "ano" in data else pd.DataFrame()
    if not annual_all.empty:
        annual_all["taxa"] = annual_all["obitos"] / annual_all["acidentes"].replace(0, np.nan) * 100
        night = data[data.get("fase_dia_agrupada", pd.Series(index=data.index)).eq("Noturno")].groupby("ano", observed=True)["id"].nunique()
        shares = (night / annual_all.set_index("ano")["acidentes"] * 100).dropna()
        st.markdown("#### Interpretação da Evolução Temporal")
        st.info(f"O maior total de acidentes ocorreu em {int(annual_all.loc[annual_all['acidentes'].idxmax(), 'ano'])}. A maior taxa de óbitos por 100 acidentes foi {annual_all['taxa'].max():.2f}. A participação noturna variou entre {shares.min():.1f}% e {shares.max():.1f}% nos anos comparáveis. As tendências são descritivas: não demonstram causalidade nem efeito de iluminação.")
    _time_module("Evolução temporal", started)


def _render_trechos_financas_full(analyzer: AccidentAnalyzer) -> None:
    """Painel completo, calculado apenas quando este módulo é selecionado."""
    started = time.perf_counter(); data = analyzer.filtered_data
    st.subheader("Priorização de Trechos Críticos e Viabilidade de Iluminação Solar")
    with st.form("trechos_local_controls"):
        a, b, c, d = st.columns(4)
        spacing = a.slider("Espaçamento entre postes (m)", 20, 100, DEFAULT_SPACING_M, 5)
        length = b.slider("Extensão do trecho (km)", .5, 10., DEFAULT_COMPRIMENTO_TRECHO_KM, .5)
        ranking_mode = c.selectbox("Critério de priorização", ["iluminacao_solar", "geral"], format_func=lambda x: "Iluminação solar" if x == "iluminacao_solar" else "Gravidade geral")
        scenario = d.selectbox("Cenário de equipamento", ["cenario_d", "cenario_a", "cenario_b", "cenario_c", "cenario_e"], format_func=lambda x: {"cenario_a":"A — Meta histórica", "cenario_b":"B — Comercial 6 m / 40 W", "cenario_c":"C — Comercial 8 m / 80 W", "cenario_d":"D — Compacto 8 m / 40 W", "cenario_e":"E — Bateria reforçada"}[x])
        update = st.form_submit_button("Atualizar análise")
    params = st.session_state.setdefault("trechos_params", {"spacing": spacing, "length": length, "mode": ranking_mode, "scenario": scenario})
    if update: params.update({"spacing": spacing, "length": length, "mode": ranking_mode, "scenario": scenario})
    signature = (len(data), tuple(data.get("id", pd.Series(dtype=str)).head(50).astype(str)), tuple(params.values()))
    cached = st.session_state.get("trechos_full_cache")
    if cached and cached[0] == signature: top, summary = cached[1], cached[2]
    else:
        with st.spinner("Calculando ranking e viabilidade para o cenário ativo..."):
            top, summary = analyzer.analyze_top_n(data, top_n=100, comprimento_km=params["length"], spacing_m=params["spacing"], criterio_ranking=params["mode"], cenario_id=params["scenario"])
        st.session_state["trechos_full_cache"] = (signature, top, summary)
    if top.empty: st.warning("Não há ocorrências com BR e marco quilométrico elegíveis para o ranking."); return
    dim = summary.get("dimensionamento", {}); vidas = summary.get("vidas_salvas_ano", 0)
    st.markdown("#### 1. Resumo financeiro do cenário selecionado")
    values = [("Extensão contemplada", f"{len(top) * params['length']:.1f} km"), ("Postes por trecho", f"{dim.get('postes_por_trecho', 0):,}"), ("Total de postes", f"{dim.get('total_postes', 0):,}"), ("CAPEX", format_pt_br_currency(summary.get("investimento_total", 0))), ("OPEX anual", format_pt_br_currency(summary.get("opex_anual", summary.get("dimensionamento", {}).get("opex_anual", 0)))), ("Benefício bruto anual", format_pt_br_currency(summary.get("economia_anual", 0))), ("Benefício líquido anual", format_pt_br_currency(summary.get("economia_liquida_anual", 0))), ("VPL social", format_pt_br_currency(summary.get("vpl", 0))), ("TIR social", f"{(summary.get('tir') or 0) * 100:.2f}% a.a."), ("Payback simples", f"{summary.get('payback_simples_anos', 0):.2f} anos"), ("Payback descontado", f"{summary.get('payback_descontado_anos', 0):.2f} anos"), ("Óbitos potencialmente evitáveis/ano", f"{vidas:.1f} (simulação)")]
    for row in range(0, len(values), 4):
        for col, (label, value) in zip(st.columns(4), values[row:row+4]): col.metric(label, value)
    st.caption("O benefício líquido é uma média anual que inclui a provisão de reposições. A manutenção anual é o OPEX ordinário; reposições ocorrem nos anos previstos. A redução de 35% corresponde a CMF 0,65 para o desfecho modelado. A aplicação proporcional aos óbitos é uma hipótese adicional exploratória, não eficácia comprovada.")
    st.markdown("#### 2. Ranking de trechos críticos")
    count = st.segmented_control("Quantidade exibida", [10, 20, 50, 100], default=20, key="top_segments_count") or 20
    rank_metric = st.selectbox("Métrica do gráfico de priorização", ["Acidentes noturnos", "Óbitos noturnos", "Feridos graves", "Pontuação de prioridade"], key="ranking_metric")
    metric_col = {"Acidentes noturnos":"n_acidentes_noturnos", "Óbitos noturnos":"mortos_noturno", "Feridos graves":"feridos_graves_noturno", "Pontuação de prioridade":"score_prioridade"}[rank_metric]
    shown = top.head(int(count)).copy(); shown["Trecho"] = shown.get("trecho", shown.get("trecho_id", "Não Informado"))
    present_plot(px.bar(shown.sort_values(metric_col), x=metric_col, y="Trecho", orientation="h", title=f"Top {count} trechos por {rank_metric}", labels={metric_col: rank_metric, "Trecho": "Trecho rodoviário"}, color_discrete_sequence=[COLOR_PALETTE["contagem"]]))
    public_cols = [x for x in ["ranking", "br", "uf", "km_inicio", "km_fim", "n_acidentes_noturnos", "mortos_noturno", "feridos_graves_noturno", "score_prioridade", "investimento_trecho"] if x in shown]
    present_dataframe(shown[public_cols], height=420)
    with st.expander("Dados técnicos completos e exportação", expanded=False):
        st.download_button("Baixar ranking em CSV", top.to_csv(index=False).encode("utf-8-sig"), "ranking_trechos.csv", "text/csv")
        present_dataframe(top)
    st.markdown("#### 3. Acidentes noturnos versus diurnos nos trechos priorizados")
    night = int(top.get("n_acidentes_noturnos", pd.Series(dtype=int)).sum()); total = int(top.get("n_acidentes_total", pd.Series(dtype=int)).sum()); day = max(total-night, 0)
    comparison = pd.DataFrame({"Período":["Noturno", "Diurno"], "Acidentes":[night, day], "Óbitos":[top.get("mortos_noturno", pd.Series(dtype=float)).sum(), max(top.get("mortos", pd.Series(dtype=float)).sum()-top.get("mortos_noturno", pd.Series(dtype=float)).sum(), 0)]})
    left, right = st.columns(2); left.plotly_chart(px.bar(comparison, x="Período", y="Acidentes", color="Período", title="Ocorrências nos trechos priorizados", color_discrete_map=PHASE_COLORS), use_container_width=True, config=PLOTLY_CONFIG); right.plotly_chart(px.bar(comparison, x="Período", y="Óbitos", color="Período", title="Óbitos nos trechos priorizados", color_discrete_map=PHASE_COLORS), use_container_width=True, config=PLOTLY_CONFIG)
    st.caption("Esta comparação refere-se somente aos segmentos priorizados; não representa o total nacional mostrado na Visão Geral.")
    st.markdown("#### 4. Análises estatísticas avançadas")
    state_metric = st.selectbox("Métrica por estado", ["Acidentes", "Óbitos", "Feridos", "Total de vítimas", "Acidentes fatais", "Óbitos por 100 acidentes"], key="state_metric")
    states = data.groupby("uf", observed=True).agg(Acidentes=("id", "nunique"), Óbitos=("mortos", "sum"), Feridos=("total_feridos", "sum"), **{"Acidentes fatais":("acidente_fatal", "sum")}).reset_index(); states["Total de vítimas"] = states["Óbitos"] + states["Feridos"]; states["Óbitos por 100 acidentes"] = states["Óbitos"] / states["Acidentes"].replace(0, np.nan) * 100
    causes = analyzer.filtered_causas if analyzer.filtered_causas is not None else pd.DataFrame()
    left, right = st.columns(2)
    with left: present_plot(px.bar(states.nlargest(10, state_metric).sort_values(state_metric), x=state_metric, y="uf", orientation="h", title=f"Top 10 estados — {state_metric}", labels={"uf":"UF"}, color_discrete_sequence=[COLOR_PALETTE["taxa"] if "por 100" in state_metric else COLOR_PALETTE["contagem"]]))
    with right:
        if not causes.empty and {"id", "causa_acidente"}.issubset(causes):
            merged = causes[["id", "causa_acidente"]].drop_duplicates().merge(data[["id", "mortos", "total_feridos", "fase_dia_agrupada"]], on="id", how="inner")
            cause_metric = st.selectbox("Métrica das causas", ["Ocorrências associadas", "Óbitos associados", "Feridos associados"], key="cause_metric")
            cg = merged.groupby("causa_acidente", observed=True).agg(**{"Ocorrências associadas":("id","nunique"), "Óbitos associados":("mortos","sum"), "Feridos associados":("total_feridos","sum")}).reset_index()
            present_plot(px.bar(cg.nlargest(10,cause_metric).sort_values(cause_metric),x=cause_metric,y="causa_acidente",orientation="h",title="Top 10 causas registradas",labels={"causa_acidente":"Causa do acidente"},color_discrete_sequence=[COLOR_PALETTE["obitos"] if cause_metric == "Óbitos associados" else COLOR_PALETTE["contagem"]]))
            st.caption("Causas podem coexistir na mesma ocorrência; barras não devem ser somadas como categorias exclusivas.")
    st.markdown("#### 5. Memória de cálculo e engenharia solar")
    deaths = float(top.get("mortos_noturno", pd.Series(dtype=float)).sum()); years = summary.get("anos_base", 1) or 1
    with st.expander("Memória de cálculo científico", expanded=False): st.markdown(f"Óbitos noturnos históricos: **{deaths:.0f}**; horizonte: **{years:.1f} anos**; baseline anualizado: **{deaths/years:.1f} óbitos/ano**; hipótese CMF: **35%**; projeção condicional: **{vidas:.1f} óbitos potencialmente evitáveis/ano**. CAPEX: **{format_pt_br_currency(summary.get('investimento_total',0))}**; benefício bruto/líquido: **{format_pt_br_currency(summary.get('economia_anual',0))} / {format_pt_br_currency(summary.get('economia_liquida_anual',0))}**; VPL, TIR e payback constam dos cards do cenário ativo.")
    energy = calcular_balanco_energetico_detalhado()
    with st.expander("Balanço energético e autonomia", expanded=False): st.markdown(f"LED: **{energy['consumo_led_wh']:.0f} Wh/noite**; telemetria: **{energy['consumo_telemetria_wh']:.0f} Wh/dia**; bateria útil BOL/EOL: **{energy['capacidade_util_bol_wh']:.0f}/{energy['capacidade_util_eol_wh']:.0f} Wh**; autonomia BOL/EOL: **{energy['autonomia_zero_sol_bol_noites']:.2f}/{energy['autonomia_zero_sol_eol_noites']:.2f} noites**; geração solar plena/nublada: **{energy['geracao_solar_sol_pleno_wh']:.0f}/{energy['geracao_solar_dia_nublado_wh']:.0f} Wh/dia**; recuperação: **{energy['dias_recarga_apos_3_noites']:.1f} dias**. {energy['status_aviso']}")
    with st.expander("Segurança luminotécnica", expanded=False): st.warning("A autonomia energética não comprova atendimento à ABNT NBR 5101:2024. São necessários estudo fotométrico, classificação da via, uniformidade, controle de ofuscamento e geometria de instalação.")
    st.markdown("#### 6. Cenários orçamentários A–E e sensibilidade")
    multi = calcular_orcamento_cenarios(top, len(top), params["length"], params["spacing"], years, EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"], FINANCIAL_PARAMS["taxa_desconto_anual"], FINANCIAL_PARAMS["vida_util_anos"]); scenarios = multi.get("comparativo_df", pd.DataFrame())
    if not scenarios.empty:
        present_dataframe(scenarios)
        present_plot(financial_comparison_chart(scenarios))
    sensitivity = summary.get("cenarios", {})
    if sensitivity:
        sensitivity_table = pd.DataFrame([{"Cenário": row["nome"], "Redução hipotética": f"{row['taxa_reducao']:.0%}", "Óbitos potencialmente evitáveis/ano": row["vidas_salvas_ano"], "VPL social": format_pt_br_currency(row["vpl"]), "Payback simples": f"{row['payback_simples']:.2f} anos"} for row in sensitivity.values()])
        present_dataframe(sensitivity_table)
    _time_module("Trechos e finanças", started)


def render_evolucao_temporal(analyzer: AccidentAnalyzer) -> None:
    started=time.perf_counter(); data=analyzer.filtered_data
    st.subheader("Evolução temporal dos acidentes")
    mode=st.radio("Série",["Evolução anual","Evolução mensal detalhada"],horizontal=True,key="temporal_mode")
    years=sorted(data["ano"].dropna().astype(int).unique()) if "ano" in data else []
    partial=2026 in years and "mes" in data and data.loc[data["ano"]==2026,"mes"].nunique()<12
    if partial: st.warning("2026 possui cobertura parcial e não deve ser comparado diretamente como ano completo.")
    phase="fase_dia_agrupada" if "fase_dia_agrupada" in data else None
    if mode=="Evolução anual" and "ano" in data:
        grouped=data.groupby(["ano",phase],observed=True).size().reset_index(name="acidentes") if phase else data.groupby("ano",observed=True).size().reset_index(name="acidentes")
        st.plotly_chart(px.line(grouped,x="ano",y="acidentes",color=phase,markers=True,title="Evolução anual por período",labels={"acidentes":"Ocorrências","ano":"Ano","fase_dia_agrupada":"Período"}))
    elif "ano_mes" in data:
        grouped=data.groupby(["ano_mes",phase],observed=True).size().reset_index(name="acidentes") if phase else data.groupby("ano_mes",observed=True).size().reset_index(name="acidentes")
        fig=px.line(grouped,x="ano_mes",y="acidentes",color=phase,markers=True,title="Evolução mensal e sazonalidade",labels={"ano_mes":"Ano-mês","acidentes":"Ocorrências","fase_dia_agrupada":"Período"}); fig.update_xaxes(tickangle=-45); st.plotly_chart(fig)
    else: st.info("A base selecionada não contém granularidade mensal.")
    _time_module("Evolução temporal",started)


def render_trechos_financas(analyzer: AccidentAnalyzer) -> None:
    started=time.perf_counter(); data=analyzer.filtered_data
    st.subheader("Trechos prioritários, engenharia e viabilidade financeira")
    with st.form("financial_parameters"):
        a,b,c=st.columns(3); spacing=a.slider("Espaçamento entre postes (m)",20,100,DEFAULT_SPACING_M,5); length=b.slider("Extensão do trecho (km)",.5,10.,DEFAULT_COMPRIMENTO_TRECHO_KM,.5); top_n=c.slider("Trechos prioritários",5,200,DEFAULT_TRECHOS_TOP_N,5)
        scenario=st.selectbox("Cenário de equipamento",["cenario_d","cenario_a","cenario_b","cenario_c","cenario_e"],format_func=lambda x: {"cenario_a":"A — Meta histórica 8 m / 60 W", "cenario_b":"B — Comercial 6 m / 40 W", "cenario_c":"C — Comercial 8 m / 80 W", "cenario_d":"D — Compacto conceitual 8 m / 40 W", "cenario_e":"E — 8 m / 80 W com bateria reforçada"}[x])
        criterion=st.selectbox("Critério de ranqueamento",["iluminacao_solar","geral"],format_func=lambda x:"Prioridade para iluminação solar" if x=="iluminacao_solar" else "Ranking geral de acidentes")
        submitted=st.form_submit_button("Atualizar cenário")
    params=st.session_state.setdefault("financial_params",{"spacing":spacing,"length":length,"top_n":top_n,"scenario":scenario,"criterion":criterion})
    if submitted: params.update({"spacing":spacing,"length":length,"top_n":top_n,"scenario":scenario,"criterion":criterion})
    cache_key=(len(data),tuple(sorted(data["id"].astype(str).head(100))) if "id" in data else (),tuple(params.values()))
    cached=st.session_state.get("rich_financial_results")
    if cached and cached[0]==cache_key: top,summary=cached[1],cached[2]
    else:
        with st.spinner("Segmentando trechos e calculando o cenário selecionado..."):
            top,summary=analyzer.analyze_top_n(data,top_n=params["top_n"],comprimento_km=params["length"],spacing_m=params["spacing"],criterio_ranking=params["criterion"],cenario_id=params["scenario"])
        st.session_state["rich_financial_results"]=(cache_key,top,summary)
    if top.empty: st.warning("Não há trechos com BR e KM elegíveis."); return
    dim=summary.get("dimensionamento",{}); vidas=summary.get("vidas_salvas_ano",0); anos=summary.get("anos_base",1) or 1; mortos=int(top.get("mortos_noturno",pd.Series(dtype=int)).sum())
    cols=st.columns(5)
    for col,label,value in zip(cols,["Extensão total","Postes","CAPEX","VPL social","Payback simples"],[f"{len(top)*params['length']:.1f} km",f"{dim.get('total_postes',0):,}",format_pt_br_currency(summary.get('investimento_total',0)),format_pt_br_currency(summary.get('vpl',0)),f"{summary.get('payback_simples_anos',0):.2f} anos"]): col.metric(label,value)
    st.info(f"Cenário de sensibilidade: {vidas:.1f} óbitos potencialmente evitáveis/ano; o CMF de 35% não é uma eficácia comprovada para os trechos.")
    with st.expander("Memória de cálculo científico",expanded=False):
        st.markdown(f"Foram observados **{mortos:,} óbitos noturnos** nos {len(top)} trechos ao longo de **{anos:.1f} anos**. A taxa anualizada é **{mortos/anos:.1f}**; o cenário aplica **35%** como hipótese paramétrica, resultando em **{vidas:.1f}** óbitos potencialmente evitáveis/ano. O benefício social anual bruto é {format_pt_br_currency(summary.get('economia_anual',0))}, o líquido é {format_pt_br_currency(summary.get('economia_liquida_anual',0))}, com OPEX e desconto incorporados no VPL.")
    energy=calcular_balanco_energetico_detalhado()
    with st.expander("Balanço energético e autonomia — 8 m / 40 W",expanded=False):
        st.markdown(f"LED: **{energy['consumo_led_wh']:.0f} Wh/noite**; telemetria: **{energy['consumo_telemetria_wh']:.0f} Wh/dia**; consumo total: **{energy['consumo_total_diario_wh']:.0f} Wh/dia**. Bateria útil BOL/EOL: **{energy['capacidade_util_bol_wh']:.0f}/{energy['capacidade_util_eol_wh']:.0f} Wh**; autonomia sem geração: **{energy['autonomia_zero_sol_bol_noites']:.2f}/{energy['autonomia_zero_sol_eol_noites']:.2f} noites**. Geração em sol pleno: **{energy['geracao_solar_sol_pleno_wh']:.0f} Wh/dia**; nublado: **{energy['geracao_solar_dia_nublado_wh']:.0f} Wh/dia**. {energy['status_aviso']}")
    with st.expander("Validação luminotécnica pendente — ABNT NBR 5101:2024",expanded=False): st.warning("A simulação energética não comprova conformidade luminotécnica. São necessários estudo DIALux/Relux, classe da via, luminância, uniformidade, ofuscamento e geometria local.")
    multi=calcular_orcamento_cenarios(top,len(top),params["length"],params["spacing"],anos,EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"],FINANCIAL_PARAMS["taxa_desconto_anual"],FINANCIAL_PARAMS["vida_util_anos"]); comparison=multi.get("comparativo_df",pd.DataFrame())
    if not comparison.empty:
        st.markdown("#### Comparativo de orçamentos A–E")
        st.dataframe(comparison,hide_index=True,width="stretch")
        st.plotly_chart(px.bar(comparison,x="Cenário",y=["CAPEX Total (R$ M)","VPL 15 Anos (R$ M)"],barmode="group",title="CAPEX versus VPL social (R$ milhões)"))
    st.markdown("#### Ranking dos trechos prioritários")
    essential=[x for x in ["ranking","trecho","n_acidentes","mortos","total_feridos","score_prioridade","confiabilidade_geo","investimento_trecho","economia_anual_trecho","payback_anos"] if x in top]
    st.dataframe(top[essential],hide_index=True,width="stretch",height=380,column_config={"ranking":"Posição","trecho":"BR / UF / intervalo de KM","n_acidentes":"Acidentes noturnos","mortos":"Óbitos noturnos","total_feridos":"Feridos noturnos","score_prioridade":"Pontuação","confiabilidade_geo":"Confiabilidade geográfica","investimento_trecho":"CAPEX (R$)","economia_anual_trecho":"Benefício social anual (R$)","payback_anos":"Payback (anos)"})
    with st.expander("Dados técnicos completos e exportação",expanded=False): st.download_button("Baixar ranking CSV",top.to_csv(index=False).encode("utf-8-sig"),"ranking_trechos.csv","text/csv"); st.dataframe(top,hide_index=True,width="stretch")
    _time_module("Trechos e finanças",started)


def render_mapa(analyzer: AccidentAnalyzer) -> None:
    started=time.perf_counter(); data=analyzer.filtered_data
    st.subheader("Mapa geográfico de ocorrências e trechos críticos")
    if not {"latitude","longitude"}.issubset(data): st.warning("A base não possui coordenadas geográficas."); return
    eligible=data[data["latitude"].notna() & data["longitude"].notna() & data["latitude"].between(-34,5.5) & data["longitude"].between(-74,-32)].copy()
    limit=st.slider("Máximo de marcadores exibidos",100,2000,APP_CONFIG.get("max_map_points",800),100,key="map_limit")
    shown=eligible.sample(min(len(eligible),limit),random_state=42) if len(eligible)>limit else eligible
    st.caption(f"Total georreferenciado elegível: {len(eligible):,}; exibido: {len(shown):,}. A limitação visual não altera estatísticas nem ranking.")
    if shown.empty: st.warning("Não há coordenadas válidas para os filtros atuais."); return
    m=folium.Map(location=[float(shown.latitude.median()),float(shown.longitude.median())],zoom_start=6,tiles="OpenStreetMap"); cluster=MarkerCluster(name="Ocorrências").add_to(m)
    cols=[x for x in ["latitude","longitude","br","uf","km","mortos","total_feridos","fase_dia_oficial","causa_acidente"] if x in shown]
    for row in shown[cols].itertuples(index=False):
        item=dict(zip(cols,row)); fatal=item.get("mortos",0)>0; night=item.get("fase_dia_oficial")=="Plena Noite"; color="#d62728" if fatal else ("#1f77b4" if night else "#ff7f0e")
        text=f"<b>BR-{item.get('br','Não informado')} / {item.get('uf','')}</b><br>KM: {item.get('km','Não informado')}<br>Óbitos: {item.get('mortos',0)}<br>Feridos: {item.get('total_feridos',0)}<br>Fase: {item.get('fase_dia_oficial','Não informado')}"
        folium.CircleMarker([item["latitude"],item["longitude"]],radius=6 if fatal else 4,popup=text,color=color,fill=True,fill_color=color,fill_opacity=.7).add_to(cluster)
    folium_static(m,width=1100,height=520)
    st.caption("Vermelho: ocorrência fatal; azul: plena noite; laranja: demais fases. O agrupamento reduz a sobrecarga do navegador.")
    _time_module("Mapa",started)


def render_prototipo_3d() -> None:
    started=time.perf_counter(); st.subheader("Protótipo 3D — poste solar inteligente compacto")
    left,right=st.columns([3,1])
    with left:
        try: components.html((Path(__file__).parent / "solar_post_3d.html").read_text(encoding="utf-8"),height=640)
        except OSError: st.error("Arquivo solar_post_3d.html não encontrado.")
    with right:
        st.html("<div class='metric-container'><h4>Controles do modelo</h4><p>🌙 Dia/noite e LED</p><p>🔋 Bateria, painel e MPPT</p><p>📡 Telemetria e radar</p><p>🚨 Falhas simuladas e alertas</p><p>📷 Movimento e reinicialização da câmera</p><hr><small>Representação conceitual: não substitui dimensionamento fotométrico, estrutural ou solar local.</small></div>")
    _time_module("Protótipo 3D",started)


def render_evolucao_temporal(analyzer: AccidentAnalyzer) -> None:
    started = time.perf_counter()
    data = analyzer.filtered_data
    st.subheader("Evolução temporal")
    group_col = "ano_mes" if "ano_mes" in data.columns and data["ano_mes"].nunique() > 1 else "ano"
    if group_col in data.columns:
        series = data.groupby(group_col, observed=True).size().reset_index(name="acidentes")
        st.plotly_chart(px.line(series, x=group_col, y="acidentes", markers=True,
                                title="Ocorrências no período"), config={"displaylogo": False, "responsive": True})
    _time_module("Evolução temporal", started)


def _financial_results(analyzer: AccidentAnalyzer) -> tuple[pd.DataFrame, Dict[str, Any]]:
    data = analyzer.filtered_data
    signature = (tuple(sorted(data.get("id", pd.Series(dtype=int)).astype(str).head(50))), len(data))
    cached = st.session_state.get("financial_results")
    if cached and cached[0] == signature:
        return cached[1], cached[2]
    top, summary = analyzer.analyze_top_n(data)
    st.session_state["financial_results"] = (signature, top, summary)
    return top, summary


def render_trechos_financas(analyzer: AccidentAnalyzer) -> None:
    started = time.perf_counter()
    st.subheader("Trechos prioritários e cenário financeiro")
    top, summary = _financial_results(analyzer)
    if top.empty:
        st.warning("Não há ocorrências elegíveis com BR e KM para a segmentação.")
    else:
        st.dataframe(top.head(100), hide_index=True, width="stretch", height=420)
        st.caption("O CMF de 35% é uma hipótese de sensibilidade para o cenário, não uma previsão de vidas efetivamente salvas.")
        st.metric("VPL social estimado", format_pt_br_currency(summary.get("vpl", 0)))
    _time_module("Trechos e finanças", started)


def render_mapa(analyzer: AccidentAnalyzer) -> None:
    started = time.perf_counter()
    data = analyzer.filtered_data
    st.subheader("Mapa geográfico")
    mask = data["latitude"].notna() & data["longitude"].notna() if {"latitude", "longitude"}.issubset(data.columns) else pd.Series(False, index=data.index)
    eligible = data[mask]
    limit = APP_CONFIG.get("max_map_points", 800)
    shown = eligible.sample(min(len(eligible), limit), random_state=42) if not eligible.empty else eligible
    st.caption(f"Ocorrências georreferenciadas elegíveis: {len(eligible):,}; exibidas: {len(shown):,}. A limitação é visual e não altera os totais.")
    if not shown.empty:
        m = folium.Map(location=[float(shown.latitude.median()), float(shown.longitude.median())], zoom_start=6)
        cluster = MarkerCluster().add_to(m)
        for row in shown[["latitude", "longitude", "br", "uf", "km", "mortos"]].itertuples(index=False):
            folium.CircleMarker([row.latitude, row.longitude], radius=4, popup=f"BR-{row.br}/{row.uf} · KM {row.km} · óbitos {row.mortos}").add_to(cluster)
        folium_static(m, width=1100, height=520)
    else:
        st.warning("Não há coordenadas válidas para os filtros ativos.")
    _time_module("Mapa", started)


def render_prototipo_3d() -> None:
    started = time.perf_counter()
    st.subheader("Protótipo 3D do poste solar")
    try:
        components.html((Path(__file__).parent / "solar_post_3d.html").read_text(encoding="utf-8"), height=640)
    except OSError:
        st.error("Arquivo solar_post_3d.html não encontrado.")
    _time_module("Protótipo 3D", started)


def render_relatorio_pdf(analyzer: AccidentAnalyzer) -> None:
    st.subheader("Relatório científico em PDF")
    st.caption("A geração é independente dos módulos visuais; só calcula a segmentação necessária após o clique.")
    if st.button("Gerar relatório PDF", type="primary", key="generate_lazy_pdf"):
        started = time.perf_counter()
        with RSSPeakSampler() as pdf_peak:
            with st.spinner("Gerando relatório e suas agregações necessárias..."):
                # Matplotlib usa estado global; PDFs simultâneos podem perder gráficos.
                with PDF_GENERATION_LOCK:
                    pdf_peak.set_stage("Finanças e segmentação")
                    top, summary = _financial_results(analyzer)
                    pdf_peak.set_stage("Renderização do PDF")
                    result = ReportGenerator().generate_accident_analysis_report(
                        filtered_data=analyzer.filtered_data, top_segments=top,
                        financial_summary=summary, quality_summary=analyzer.quality_summary,
                        pessoas_df=analyzer.filtered_pessoas, veiculos_df=analyzer.filtered_veiculos,
                        causas_df=analyzer.filtered_causas,
                    )
                    pdf_peak.set_stage("Finalização do PDF")
                    st.session_state["generated_pdf"] = (result.getvalue(), "relatorio_cientifico_iluminar_" + datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y%m%d_%H%M%S") + ".pdf")
        st.session_state["peak_pdf_rss_mib"] = pdf_peak.peak_mib
        st.session_state["peak_pdf_stages_mib"] = pdf_peak.stage_peaks_mib.copy()
        _time_module("PDF", started)
    if st.session_state.get("peak_pdf_rss_mib") is not None:
        if st.session_state.get("diagnostics_allowed"):
            st.caption(f"Pico RSS amostrado durante a última geração: {st.session_state['peak_pdf_rss_mib']:.1f} MiB (intervalo de 20 ms).")
        if st.session_state.get("diagnostics_allowed"):
            with st.expander("Picos RSS por etapa do PDF"):
                for stage, peak_mib in st.session_state.get("peak_pdf_stages_mib", {}).items():
                    st.caption(f"{stage}: {peak_mib:.1f} MiB")
    if "generated_pdf" in st.session_state:
        pdf_bytes, pdf_name = st.session_state["generated_pdf"]
        st.download_button("Baixar PDF", pdf_bytes, pdf_name, "application/pdf")


def create_dashboard(analyzer: AccidentAnalyzer) -> None:
    """Despacha somente o módulo selecionado; não usa tabs/expanders como lazy-load."""
    if analyzer.filtered_data is None or analyzer.filtered_data.empty:
        st.warning("Não há registros para exibir com os filtros selecionados.")
        return
    modules = {
        "Visão geral": lambda: render_visao_geral(analyzer),
        "Análise científica": lambda: render_analise_cientifica(analyzer),
        "Perfil de vítimas": lambda: render_perfil_vitimas(analyzer),
        "Evolução temporal": lambda: render_evolucao_temporal(analyzer),
        "Trechos e finanças": lambda: render_trechos_financas(analyzer),
        "Mapa": lambda: render_mapa(analyzer),
        "Protótipo 3D": render_prototipo_3d,
        "Relatório PDF": lambda: render_relatorio_pdf(analyzer),
        "Estudos Territoriais": lambda: _render_territorial_case_lazy(analyzer),
    }
    active = st.radio("Módulo", list(modules), horizontal=True, key="active_dashboard_module")
    render_started = time.perf_counter()
    rss_before = None
    if st.session_state.get("diagnostics_allowed"):
        from config import get_current_rss_mb
        rss_before = get_current_rss_mb()
    modules[active]()
    if st.session_state.get("diagnostics_allowed"):
        from config import get_current_rss_mb
        st.session_state["last_render_diagnostic"] = {
            "module": active, "seconds": round(time.perf_counter() - render_started, 3),
            "rss_mib": round(get_current_rss_mb(), 1),
            "rss_before_mib": round(rss_before, 1),
        }
    timings = st.session_state.get("module_timings", {})
    if timings:
        st.caption("Tempo Python do último carregamento: " + ", ".join(f"{k}: {v:.2f}s" for k, v in timings.items()))


def _render_territorial_case_lazy(analyzer: AccidentAnalyzer) -> None:
    from territorial_platform import render_territorial_platform
    render_territorial_platform(analyzer)


# Recuperação seletiva do conteúdo existente em render_legacy_full_dashboard.
# Estas funções substituem as versões resumidas acima; a navegação continua a
# chamar uma única função por vez e, portanto, não reintroduz renderização geral.
def render_visao_geral(analyzer: AccidentAnalyzer) -> None:
    started = time.perf_counter(); data = analyzer.filtered_data; quality = analyzer.quality_summary or {}
    total, mortos = len(data), int(data["mortos"].sum())
    feridos, fatais = int(data["total_feridos"].sum()), int(data["acidente_fatal"].sum())
    com_km = int(data["km"].notna().sum()) if "km" in data else 0
    com_geo = int((data["latitude"].notna() & data["longitude"].notna()).sum()) if {"latitude", "longitude"}.issubset(data) else 0
    st.subheader("Visão geral e auditoria metodológica")
    with st.expander("Auditoria metodológica e qualidade dos dados", expanded=False):
        cols = st.columns(4)
        vals = [("Linhas brutas", quality.get("registros_brutos", total)), ("Ocorrências únicas", total),
                ("Pessoas identificadas", quality.get("pessoas_unicas_pesid", 0)), ("Veículos únicos", quality.get("veiculos_unicos", 0))]
        for col, (label, value) in zip(cols, vals): col.metric(label, f"{value:,}")
        st.markdown(f"**Desdobramentos consolidados:** {quality.get('desdobramentos_consolidados', 0):,} · "
                    f"**KM informado:** {com_km:,} · **KM ausente:** {quality.get('ocorrencias_sem_km', total-com_km):,} · "
                    f"**Coordenadas válidas:** {com_geo:,}.  Estatísticas nacionais usam todas as ocorrências; "
                    "o ranking físico usa somente BR e KM elegíveis.")
    metrics = st.columns(6)
    for col, label, value in zip(metrics, ["Acidentes únicos", "Pessoas mortas", "Pessoas feridas", "Acidentes fatais", "% de acidentes fatais", "Óbitos / 100 acidentes"],
                                 [total, mortos, feridos, fatais, fatais / total * 100 if total else 0, mortos / total * 100 if total else 0]):
        col.metric(label, f"{value:,}" if isinstance(value, int) else f"{value:.2f}" + ("%" if label.startswith("%") else ""))
    comp = compute_day_vs_night_comparison(data); tabela = comp.get("tabela_oficial", pd.DataFrame())
    noite, dia = comp.get("noturno") or {}, comp.get("diurno") or {}
    st.subheader("Comparação por fase oficial do dia")
    a, b, c = st.columns(3)
    a.metric("Óbitos / 100 na plena noite", f"{noite.get('mortos_por_100_acidentes', 0):.2f}")
    b.metric("Óbitos / 100 no pleno dia", f"{dia.get('mortos_por_100_acidentes', 0):.2f}")
    c.metric("Razão de letalidade", f"{comp.get('razao_letalidade_obitos', 0):.2f}x")
    if not tabela.empty:
        left, right = st.columns(2)
        with left: st.plotly_chart(px.pie(tabela, names="fase_dia_oficial", values="n_acidentes", hole=.4, title="Distribuição de ocorrências por fase", color="fase_dia_oficial", color_discrete_map=PHASE_COLORS))
        with right: st.plotly_chart(px.bar(tabela, x="fase_dia_oficial", y="mortos_por_100_acidentes", color="fase_dia_oficial", title="Óbitos por 100 acidentes", color_discrete_map=PHASE_COLORS))
        present_dataframe(tabela)
        st.info(comp.get("texto_interpretativo_fases", "Comparação descritiva; não representa risco por viagem."))
    _time_module("Visão geral", started)


def render_analise_cientifica(analyzer: AccidentAnalyzer) -> None:
    started = time.perf_counter(); data = analyzer.filtered_data
    result = analyze_visibility_and_reaction(data, analyzer.filtered_causas if analyzer.filtered_causas is not None else pd.DataFrame())
    st.subheader("Visibilidade noturna, tempo de reação e fatores associados")
    pivot = result.get("pivot_causas", pd.DataFrame()); reacao = result.get("reacao_df", pd.DataFrame())
    if not pivot.empty:
        selected = pivot[pivot.get("is_reacao_visibilidade", False)].copy()
        noturno = next((x for x in selected.columns if "n_acidentes_noturno" in x), None); diurno = next((x for x in selected.columns if "n_acidentes_diurno" in x), None)
        left, right = st.columns([3, 2])
        with left:
            if noturno and diurno:
                plot = selected.sort_values(noturno, ascending=False).head(12)
                fig = go.Figure([go.Bar(name="Noturno", x=plot["causa_normalizada"], y=plot[noturno], marker_color=COLOR_PALETTE["noturno"]), go.Bar(name="Diurno", x=plot["causa_normalizada"], y=plot[diurno], marker_color=COLOR_PALETTE["diurno"])])
                fig.update_layout(title="Ocorrências por causa: noturno versus diurno", barmode="group", xaxis_tickangle=-30); st.plotly_chart(fig)
        with right:
            st.html(f"<div class='highlight-box'><h4>Rigor científico</h4><p><b>Evidência observacional:</b> {result.get('evidencias_texto','')}</p><p><b>Hipótese interpretativa:</b> {result.get('hipotese_texto','')}</p><p><b>Limitações:</b> {result.get('limitacoes_texto','')}</p></div>")
        present_dataframe(selected)
    meteo, pista = result.get("meteo_strat", pd.DataFrame()), result.get("pista_strat", pd.DataFrame())
    st.markdown("#### Estratificação ambiental e geometria da via")
    left, right = st.columns(2)
    if not meteo.empty:
        with left: st.plotly_chart(px.bar(meteo, x="condicao_metereologica", y="n_acidentes", color="fase_dia_agrupada", barmode="group", title="Causas por condição meteorológica", labels={"condicao_metereologica":"Meteorologia", "n_acidentes":"Ocorrências"}, color_discrete_map=PHASE_COLORS))
    if not pista.empty:
        with right: st.plotly_chart(px.bar(pista, x="tipo_pista", y="n_acidentes", color="fase_dia_agrupada", barmode="group", title="Causas por tipo de pista", labels={"tipo_pista":"Tipo de pista", "n_acidentes":"Ocorrências"}, color_discrete_map=PHASE_COLORS))
    if not reacao.empty:
        st.markdown("#### Estatísticas detalhadas de causas, gravidade e período")
        present_dataframe(reacao)
    _time_module("Análise científica", started)


def render_perfil_vitimas(analyzer: AccidentAnalyzer) -> None:
    started = time.perf_counter(); pessoas = analyzer.filtered_pessoas if analyzer.filtered_pessoas is not None else pd.DataFrame(); veiculos = analyzer.filtered_veiculos if analyzer.filtered_veiculos is not None else pd.DataFrame(); data = analyzer.filtered_data
    st.subheader("Perfil de vítimas, frota e tipologia")
    choice = st.radio("Dimensão", ["Envolvimento", "Faixa etária", "Sexo", "Frota", "Tipo de acidente"], horizontal=True, key="profile_dimension")
    if choice == "Envolvimento" and not pessoas.empty:
        res = compute_envolvimento_analysis(pessoas); tbl = res.get("resumo_envolvimento", pd.DataFrame())
        if not tbl.empty:
            tbl = tbl.copy()
            tbl["tipo_envolvido"] = _public_label_series(tbl["tipo_envolvido"])
            vitimas_plot = tbl[["tipo_envolvido", "mortos", "feridos_graves", "feridos_leves"]].copy()
            vitimas_plot = vitimas_plot.melt(id_vars="tipo_envolvido", var_name="gravidade", value_name="quantidade")
            vitimas_plot["gravidade"] = vitimas_plot["gravidade"].map({"mortos": "Óbitos", "feridos_graves": "Feridos graves", "feridos_leves": "Feridos leves"})
            a,b=st.columns(2); a.plotly_chart(px.bar(vitimas_plot,x="tipo_envolvido",y="quantidade",color="gravidade",barmode="stack",title="Distribuição de Vítimas por Tipo de Envolvimento",labels={"quantidade":"Pessoas", "gravidade":"Gravidade", "tipo_envolvido":"Envolvimento"},color_discrete_map=SEVERITY_COLORS)); b.plotly_chart(px.bar(tbl,x="tipo_envolvido",y="taxa_mortalidade_pct",title="Taxa de mortalidade por envolvimento",labels={"taxa_mortalidade_pct":"Mortalidade (%)","tipo_envolvido":"Envolvimento"},color_discrete_sequence=[COLOR_PALETTE["taxa"]]))
            present_dataframe(tbl)
    elif choice == "Faixa etária" and not pessoas.empty:
        res=compute_faixa_etaria_analysis(pessoas); tbl=res.get("resumo_faixa_etaria",pd.DataFrame()); q=res.get("metricas_qualidade_idade",{})
        c=st.columns(3); c[0].metric("Idades válidas",f"{q.get('idades_validas',0):,}"); c[1].metric("Não informadas/inconsistentes",f"{q.get('idades_inconsistentes_ou_ausentes',0):,}"); c[2].metric("Acima de 110 anos",f"{q.get('idades_superiores_110_anos',0):,}")
        if not tbl.empty: a,b=st.columns(2); a.plotly_chart(px.bar(tbl,x="faixa_etaria",y="total_pessoas",title="Pessoas por faixa etária",labels={"faixa_etaria":"Faixa etária","total_pessoas":"Pessoas"},color_discrete_sequence=[COLOR_PALETTE["contagem"]])); b.plotly_chart(px.bar(tbl,x="faixa_etaria",y="mortos",title="Óbitos por faixa etária",labels={"faixa_etaria":"Faixa etária","mortos":"Óbitos"},color_discrete_sequence=[COLOR_PALETTE["obitos"]])); present_dataframe(tbl)
    elif choice == "Sexo" and not pessoas.empty:
        tbl=compute_sexo_analysis(pessoas).get("resumo_sexo",pd.DataFrame())
        if not tbl.empty: a,b=st.columns(2); a.plotly_chart(px.pie(tbl,names="sexo",values="total_pessoas",hole=.4,title="Envolvidos por sexo",labels={"total_pessoas":"Pessoas"},color="sexo",color_discrete_map=SEX_COLORS)); b.plotly_chart(px.bar(tbl,x="sexo",y="taxa_mortalidade_pct",title="Mortalidade por sexo",labels={"taxa_mortalidade_pct":"Percentual de mortalidade"},color="sexo",color_discrete_map=SEX_COLORS)); present_dataframe(tbl)
    elif choice == "Frota" and not veiculos.empty:
        tbl=compute_veiculo_analysis(veiculos,pessoas)
        if not tbl.empty: st.plotly_chart(px.bar(tbl.head(10),x="tipo_veiculo",y="total_veiculos",title="Top 10 veículos envolvidos",labels={"tipo_veiculo":"Tipo de veículo","total_veiculos":"Veículos"},color_discrete_sequence=[COLOR_PALETTE["contagem"]])); present_dataframe(tbl)
    else:
        res=compute_tipo_acidente_analysis(data); tbl=res.get("resumo_tipo_acidente",pd.DataFrame())
        if not tbl.empty: a,b=st.columns(2); a.plotly_chart(px.bar(tbl.head(10),x="tipo_acidente",y="mortos",title="Tipos de acidente por óbitos",labels={"tipo_acidente":"Tipo de acidente","mortos":"Óbitos"},color_discrete_sequence=[COLOR_PALETTE["obitos"]])); b.plotly_chart(px.bar(tbl.head(10),x="tipo_acidente",y="obitos_por_100_acidentes",title="Óbitos por 100 acidentes",labels={"tipo_acidente":"Tipo de acidente","obitos_por_100_acidentes":"Óbitos por 100 acidentes"},color_discrete_sequence=[COLOR_PALETTE["taxa"]])); present_dataframe(tbl)
    _time_module("Perfil de vítimas", started)


# Os despachantes abaixo são definidos por último para prevalecer sobre as
# versões simplificadas mantidas no arquivo apenas para histórico local.
def render_evolucao_temporal(analyzer: AccidentAnalyzer) -> None:
    _render_evolucao_temporal_full(analyzer)


def render_trechos_financas(analyzer: AccidentAnalyzer) -> None:
    _render_trechos_financas_full(analyzer)

from analyzer import AccidentAnalyzer
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
import branca.element
from datetime import datetime
import os
import streamlit.components.v1 as components
from config import COLOR_PALETTE


def _get_dynamic_year_range(data):
    """
    Cria uma string dinâmica listando todos os anos presentes (ex:
    (2020-2022-2024)).
    """
    if "ano" not in data.columns or data["ano"].dropna().empty:
        return ""
    anos_presentes = sorted(
        pd.Series(data["ano"].dropna().unique()).astype(int)
    )
    anos_formatados = [str(a) for a in anos_presentes]
    return f"({'-'.join(anos_formatados)})"


def create_dashboard(analyzer: AccidentAnalyzer):
    """Cria o dashboard principal com as análises"""
    data = analyzer.filtered_data
    if data is None or data.empty:
        st.warning("Não há dados filtrados para exibir no dashboard.")
        return

    # Métricas principais
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🚗 Total de Acidentes", f"{len(data):,}")
    with col2:
        mortos_total = data["mortos"].sum() if "mortos" in data.columns else 0
        st.metric("💀 Total de Mortos", f"{int(mortos_total):,}")
    with col3:
        feridos_total = (
            data["total_feridos"].sum()
            if "total_feridos" in data.columns
            else 0
        )
        st.metric("🤕 Total de Feridos", f"{int(feridos_total):,}")
    with col4:
        acidentes_noturnos = (
            len(data[data["fase_dia"] == "noturno"])
            if "fase_dia" in data.columns
            else 0
        )
        st.metric("🌙 Acidentes Noturnos", f"{acidentes_noturnos:,}")
    with col5:
        acidentes_diurnos = (
            len(data[data["fase_dia"] == "diurno"])
            if "fase_dia" in data.columns
            else 0
        )
        st.metric("☀️ Acidentes Diurnos", f"{acidentes_diurnos:,}")

    st.markdown("---")

    # Análise Noturno vs Diurno
    st.subheader("🌗 Análise Comparativa: Acidentes Noturnos vs Diurnos")
    if "fase_dia" in data.columns:
        col1, col2 = st.columns(2)
        with col1:
            fase_counts = data["fase_dia"].value_counts()
            # Usa paleta de cores config
            color_map = {
                "noturno": COLOR_PALETTE.get("primary", "#1f77b4"),
                "diurno": COLOR_PALETTE.get("secondary", "#ff7f0e"),
            }
            fig_pie = px.pie(
                values=fase_counts.values,
                names=fase_counts.index,
                title="Distribuição de Acidentes por Período",
                color=fase_counts.index,
                color_discrete_map=color_map,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            if "mortos" in data.columns:
                severidade_periodo = (
                    data.groupby("fase_dia")
                    .agg(
                        {
                            "mortos": "mean",
                            "total_feridos": "mean",
                            "total_vitimas": "mean",
                        }
                    )
                    .round(2)
                )
                fig_bar = px.bar(
                    severidade_periodo,
                    y=severidade_periodo.index,
                    x="mortos",
                    title="Média de Mortos por Acidente por Período",
                    orientation="h",
                    color=severidade_periodo.index,
                    color_discrete_map={
                        "noturno": "#1f77b4",
                        "diurno": "#ff7f0e",
                    },
                )
                st.plotly_chart(fig_bar, use_container_width=True)

    # Top trechos críticos
    st.subheader("🚨 Top 20 Trechos Mais Críticos para Iluminação Solar")

    # Inicializa trechos_criticos e trechos_com_roi para garantir
    # que as variáveis sempre existam antes do uso (evita NameError no export)
    trechos_criticos = pd.DataFrame()
    trechos_com_roi = pd.DataFrame()

    if all(col in data.columns for col in ["br", "km", "uf"]):
        data["trecho"] = (
            data["br"].astype(str)
            + " - KM "
            + data["km"].astype(str)
            + " ("
            + data["uf"].astype(str)
            + ")"
        )
        acidentes_noturnos_data = (
            data[data["fase_dia"] == "noturno"]
            if "fase_dia" in data.columns
            else data
        )

        trechos_criticos_base = (
            acidentes_noturnos_data.groupby(["br", "km", "uf"])
            .agg(
                {
                    "mortos": "sum",
                    "feridos_graves": "sum",
                    "feridos_leves": "sum",
                    "total_feridos": "sum",
                    "total_vitimas": "sum",
                    "trecho": "first",
                }
            )
            .reset_index()
        )

        if not trechos_criticos_base.empty:
            trechos_criticos_base["score_prioridade"] = (
                trechos_criticos_base["mortos"] * 3
                + trechos_criticos_base["total_feridos"]
            )
            contagem_acidentes = (
                acidentes_noturnos_data.groupby(["br", "km", "uf"])
                .size()
                .reset_index(name="n_acidentes")
            )
            trechos_criticos = trechos_criticos_base.merge(
                contagem_acidentes, on=["br", "km", "uf"]
            )

        st.sidebar.subheader("🔧 Parâmetros de Dimensionamento")
        spacing_m = st.sidebar.number_input(
            "Espaçamento entre postes (m)",
            min_value=10,
            max_value=200,
            value=50,
            step=5,
        )
        comprimento_km_default = st.sidebar.number_input(
            "Comprimento médio por trecho (km)",
            min_value=0.1,
            max_value=20.0,
            value=2.0,
            step=0.1,
        )
        n_trechos_prioritarios = st.sidebar.slider(
            "Número de trechos a considerar (Top N)",
            min_value=1,
            max_value=100,
            value=100,
            step=1,
        )

        # Chamar o método da classe
        trechos_com_roi, agregados = analyzer.analyze_top_n(
            df=trechos_criticos,
            top_n=n_trechos_prioritarios,
            comprimento_km=comprimento_km_default,
            spacing_m=spacing_m,
        )

        # O Resumo Financeiro
        st.html(
            f"""
            <div class="metric-container">
                <h4>📊 Resumo Financeiro - Top {n_trechos_prioritarios} Trechos</h4>
                <p><strong>Investimento Total Estimado:</strong> R$ {agregados['investimento_total']:,.2f}</p>
                <p><strong>Vítimas Evitadas/Ano:</strong> {agregados['vitimas_evitadas_total']:.1f}</p>
                <p><strong>Economia Anual Estimada: R$ {agregados['economia_anual']:,.2f}</strong></p>
                <hr style="margin: 5px 0;">
                <p style="font-size: 0.8rem; margin-bottom: 2px;">
                    <em>Detalhes da Economia:</em><br>
                    - <strong>Vidas Salvas:</strong> R$ {agregados['economia_mortos']:,.2f}<br>
                    - <strong>Fer. Graves Evitados:</strong> R$ {agregados['economia_graves']:,.2f}<br>
                    - <strong>Fer. Leves Evitados:</strong> R$ {agregados['economia_leves']:,.2f}
                </p>
            </div>
            """
        )

        # A tabela de exibição agora usa o DataFrame 'top_df'
        st.dataframe(
            agregados["top_df"][
                [
                    "trecho",
                    "n_acidentes",
                    "mortos",
                    "total_feridos",
                    "score_prioridade",
                    "investimento_trecho",
                    "payback_anos",
                    "roi_10anos",
                ]
            ],
            column_config={
                "trecho": "Trecho (BR-KM-UF)",
                "n_acidentes": st.column_config.NumberColumn(
                    "Acidentes Noturnos", format="%d"
                ),
                "mortos": st.column_config.NumberColumn("Mortos", format="%d"),
                "total_feridos": st.column_config.NumberColumn(
                    "Feridos", format="%d"
                ),
                "score_prioridade": st.column_config.NumberColumn(
                    "Score", format="%d"
                ),
                "investimento_trecho": st.column_config.NumberColumn(
                    "Investimento (R$)", format="R$ %.2f"
                ),
                "payback_anos": st.column_config.NumberColumn(
                    "Payback (anos)", format="%.2f"
                ),
                "roi_10anos": st.column_config.NumberColumn(
                    "ROI 10 anos (%)", format="%.2f%%"
                ),
            },
            use_container_width=True,
            height=400,
        )

    # Mapa de acidentes
    if all(col in data.columns for col in ["latitude", "longitude"]):
        st.subheader("🗺️ Mapa de Acidentes")
        map_data = data.dropna(subset=["latitude", "longitude"])
        map_data = map_data[
            (map_data["latitude"] >= -35) & (map_data["latitude"] <= 5)
        ]
        map_data = map_data[
            (map_data["longitude"] >= -75) & (map_data["longitude"] <= -32)
        ]

        if not map_data.empty:
            if len(map_data) > 1000:
                map_data = map_data.sample(1000)
            center_lat, center_lon = (
                map_data["latitude"].mean(),
                map_data["longitude"].mean(),
            )
            m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
            for _, row in map_data.iterrows():
                color = "red" if row.get("fase_dia") == "noturno" else "blue"
                folium.CircleMarker(
                    location=[row["latitude"], row["longitude"]],
                    radius=3,
                    popup=f"BR-{row['br']} KM {row['km']} - {row['uf']}",
                    color=color,
                    fillColor=color,
                    weight=1,
                    fillOpacity=0.6,
                ).add_to(m)
            legend_html = """
                <div style="position: fixed; 
                    bottom: 50px; left: 50px; 
                    width: 150px; height: 90px;                         
                    background-color: white;
                    border:2px solid grey; z-index:9999;                         
                    font-size:14px;
                    padding: 10px">             
                    <b>Legenda</b><br>             
                    <i class="fa fa-circle" style="color:red"></i> 
                    Noturno<br>             
                    <i class="fa fa-circle"
                    style="color:blue">
                    </i> Diurno             
                </div>
                """
            legend_macro = branca.element.Element(legend_html)
            m.add_child(legend_macro)
            folium_static(m)

    # Tendências temporais
    if "ano" in data.columns and not data["ano"].empty:
        year_range_str = _get_dynamic_year_range(data)
        title_text = f"Evolução dos Acidentes por Período {year_range_str}"

        st.subheader(f"📈 Tendências Temporais {year_range_str}")

        tendencia_ano = (
            data.groupby(["ano", "fase_dia"])
            .size()
            .reset_index(name="Número de Acidentes")
        )

        fig_tendencia = px.line(
            tendencia_ano,
            x="ano",
            y="Número de Acidentes",
            color="fase_dia",
            markers=True,
            title=title_text,
            color_discrete_map={"noturno": "#1f77b4", "diurno": "#ff7f0e"},
            labels={"fase_dia": "Período"},
        )

        fig_tendencia.update_layout(
            hovermode="x unified",
            xaxis_type="category",
        )
        st.plotly_chart(fig_tendencia, use_container_width=True)

    # Análises estatísticas avançadas
    st.subheader("📊 Análises Estatísticas Avançadas")
    col1, col2 = st.columns(2)
    with col1:
        if "uf" in data.columns:
            acidentes_uf = (
                data.groupby("uf")
                .agg({"mortos": "sum", "total_feridos": "sum"})
                .reset_index()
            )
            acidentes_uf["total_vitimas"] = (
                acidentes_uf["mortos"] + acidentes_uf["total_feridos"]
            )
            acidentes_uf = acidentes_uf.sort_values(
                "total_vitimas", ascending=False
            ).head(10)
            fig_uf = px.bar(
                acidentes_uf,
                x="uf",
                y="total_vitimas",
                title="Top 10 Estados - Total de Vítimas",
                color="total_vitimas",
                color_continuous_scale="Reds",
            )
            st.plotly_chart(fig_uf, use_container_width=True)
    with col2:
        if "causa_acidente" in data.columns:
            causas = data["causa_acidente"].value_counts().head(10)
            fig_causas = px.bar(
                x=causas.values,
                y=causas.index,
                orientation="h",
                title="Top 10 Principais Causas de Acidentes",
                color=causas.values,
                color_continuous_scale="Blues",
            )
            fig_causas.update_layout(height=400)
            st.plotly_chart(fig_causas, use_container_width=True)

    # Conclusões e recomendações
    st.subheader("🎯 Conclusões e Recomendações")

    if "fase_dia" in data.columns:
        total_acidentes = len(data)
        acidentes_noturnos = len(data[data["fase_dia"] == "noturno"])
        perc_noturnos = (
            (acidentes_noturnos / total_acidentes) * 100
            if total_acidentes > 0
            else 0
        )
        mortalidade_noturna = (
            data[data["fase_dia"] == "noturno"]["mortos"].mean()
            if "mortos" in data.columns
            else 0
        )
        mortalidade_diurna = (
            data[data["fase_dia"] == "diurno"]["mortos"].mean()
            if "mortos" in data.columns
            else 0
        )
        st.html(
            f"""
                <div class="highlight-box">         
                <h4>🔍 Principais Descobertas:</h4>
                <ul>             
                <li>📊 <strong>{perc_noturnos:.1f}%</strong> dos acidentes ocorrem no período noturno</li>             
                <li>💀 Taxa de mortalidade noturna: <strong>{mortalidade_noturna:.2f}</strong> mortos/acidente</li>
                <li>💀 Taxa de mortalidade diurna: <strong>{mortalidade_diurna:.2f}</strong> mortos/acidente</li>             
                <li>🔺 Acidentes noturnos são <strong>{(mortalidade_noturna/mortalidade_diurna if mortalidade_diurna > 0 else 1):.1f}x</strong> mais letais</li>         
                </ul>         
                <h4>💡 Recomendações Estratégicas:</h4>         
                <ol>             
                <li><strong>Priorização Imediata:</strong> Implementar iluminação solar nos top 100 trechos críticos</li>           
                <li><strong>Investimento Focado:</strong> Concentrar recursos em rodovias com maior ROI</li>
                <li><strong>Monitoramento:</strong> Acompanhar redução de acidentes pós-instalação</li>             
                <li><strong>Expansão Gradual:</strong> Expandir programa baseado em resultados iniciais</li>         
                </ol>         
                </div>
            """
        )

    # Protótipo 3D do Poste Solar
    st.subheader("🌟 Protótipo 3D - Poste Solar Inteligente")
    col1, col2 = st.columns([2, 1])
    with col1:
        try:
            with open("solar_post_3d.html", encoding="UTF-8") as f:
                html_code = f.read()
            components.html(html_code, height=600)
        except FileNotFoundError:
            st.error("Arquivo 'solar_post_3d.html' não encontrado. Coloque-o na raiz do projeto.")
    with col2:
        st.html(
            """
         <div class="metric-container">             
            <h4>🎮 Como Usar o Protótipo 3D</h4>             
            <p>Use o mouse para rotacionar a câmera e os botões de controle para interagir com a cena.</p>             
            <p><strong>Botões de Controle:</strong></p>             
            <p>• 🌙 Alternar Dia/Noite</p>
            <p>• 💡 Ligar/Desligar LED</p>             
            <p>• 🚶 Simular Movimento</p>
            <p>• 📷 Reset Câmera</p>             
            <p><strong>Atalhos do Teclado:</strong></p>
            <p>Pressione 'H' dentro do protótipo para ver todos os atalhos.</p>
            </div>
        """,
        )

    # Impacto da tecnologia
    st.subheader("🚀 O Papel da Tecnologia na Segurança Viária")
    st.html(
        """
        <div class="highlight-box">
            <h4>💻 Tecnologia para Salvar Vidas</h4>
            <p>Este projeto demonstra como a análise de dados pode ser
            uma ferramenta poderosa para:</p>
            <ul>
            <li>🎯
             <strong>Identificar Padrões:</strong>
             Correlações entre iluminação e acidentes</li>
             <li>📍 <strong>Localizar Prioridades:</strong> Trechos
            com maior potencial de impacto</li>
            <li>💰 <strong>Otimizar
            Recursos:</strong> Maximizar retorno do investimento público</li>
            <li>📊
            <strong>Mensurar Resultados:</strong> Acompanhar efetividade das
            intervenções</li>
            </ul>
        </div>
        """
    )

    # Botão para export
    if st.button("📄 Gerar Relatório PDF", use_container_width=True):
        try:
            from pdf_generator import ReportGenerator

            with st.spinner("📄 Gerando relatório PDF..."):
                generator = ReportGenerator()
                report_buffer = generator.generate_accident_analysis_report(
                    filtered_data=data, top_segments=trechos_com_roi
                )

                # Salvar e oferecer para download
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"relatorio_acidentes_{timestamp}.pdf"
                save_path = os.path.join("reports", file_name)

                with open(save_path, "wb") as f:
                    f.write(report_buffer.getvalue())
                report_buffer.seek(0)

                st.download_button(
                    label="📥 Baixar Relatório PDF",
                    data=report_buffer,
                    file_name=file_name,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success(f"✅ Relatório gerado e salvo em '{save_path}'!")
        except ImportError:
            st.error("❌ Módulo pdf_generator não encontrado.")
        except Exception as e:
            st.error(f"❌ Erro ao gerar relatório: {str(e)}")

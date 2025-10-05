import streamlit as st
from datetime import datetime
import os
import warnings
from analyzer import AccidentAnalyzer
from dashboard import create_dashboard
from config import APP_CONFIG, DATA_DIR, REPORTS_DIR

warnings.filterwarnings("ignore")

# Configuração da página
st.set_page_config(
    page_title=APP_CONFIG["title"] + " - Análise de Acidentes Rodoviários",
    page_icon=APP_CONFIG["icon"],
    layout=APP_CONFIG["layout"],
    initial_sidebar_state="expanded",
)

# Estilo CSS customizado
st.html(
    """
     <style>
        .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom:
        2rem;
        font-weight: bold;
    }
    .metric-container, .highlight-box {
        background-color: #fff;
        color: #222 !important;
        padding: 1rem;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
        border-radius: 10px;
    }
    .metric-container h4, .highlight-box h3, .highlight-box h4 {
        color: #1f77b4 !important;
    }

    @media (prefers-color-scheme: dark) {
        .metric-container, .highlight-box {
        background-color: #1a2332;
        color: #f0f2f6 !important;
        border-left: 5px solid #4fa3ff;
    }
    .metric-container h4, .highlight-box h3, .highlight-box h4 {
        color: #4fa3ff !important;
        }
    }
    </style>
    """,
)


def main():
    st.markdown(
        '<h1 class="main-header">🌟 Iluminar para Proteger</h1>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """<p style="text-align: center; font-size: 1.2rem;">
        Análise Inteligente de Acidentes Rodoviários para Implementação de
        Iluminação Solar</p>""",
        unsafe_allow_html=True,
    )

    analyzer = AccidentAnalyzer()

    # Lógica da Sidebar
    st.sidebar.header("📊 Controles do Dashboard")
    st.sidebar.subheader("📁 Carregamento de Dados")
    uploaded_files = st.sidebar.file_uploader(
        "Selecione os arquivos CSV de acidentes",
        type=["csv"],
        accept_multiple_files=True,
        help="Arquivos de 2020-2024 com dados de acidentes rodoviários",
    )

    # Usa a variável do config
    data_dir = str(DATA_DIR)
    local_files = []
    if os.path.exists(data_dir):
        local_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

    use_local_files = False
    if local_files:
        st.sidebar.info(
            f"📂 {len(local_files)} arquivo(s) encontrado(s) na pasta /data"
        )
        use_local_files = st.sidebar.checkbox(
            "Usar arquivos locais da pasta /data",
            key="use_local_files_checkbox",
        )

    # Seção para listar, baixar e apagar relatórios salvos
    st.sidebar.subheader("📄 Relatórios Salvos")

    reports_dir = str(REPORTS_DIR)
    try:
        report_files = [
            f for f in os.listdir(reports_dir) if f.endswith(".pdf")
        ]
        if not report_files:
            st.sidebar.info("Nenhum relatório foi gerado ainda.")
        else:
            reports_with_dates = []
            for report_name in report_files:
                report_path = os.path.join(reports_dir, report_name)
                mod_time = os.path.getmtime(report_path)
                reports_with_dates.append(
                    {
                        "name": report_name,
                        "path": report_path,
                        "date": datetime.fromtimestamp(mod_time),
                    }
                )
            reports_with_dates.sort(key=lambda x: x["date"], reverse=True)

            for report in reports_with_dates:
                report_name = report["name"]
                report_path = report["path"]
                report_date = report["date"].strftime("%d/%m/%Y %H:%M")
                col1, col2 = st.sidebar.columns([3, 1])
                with col1:
                    with open(report_path, "rb") as f:
                        pdf_bytes = f.read()
                    st.download_button(
                        label=f"📥 {report_name.replace('.pdf', '')}",
                        data=pdf_bytes,
                        file_name=report_name,
                        mime="application/pdf",
                        help=f"Gerado em: {report_date}",
                    )
                with col2:
                    if st.button(
                        "🗑️",
                        key=f"delete_{report_name}",
                        help="Apagar este relatório",
                    ):
                        os.remove(report_path)
                        st.rerun()
    except FileNotFoundError:
        st.sidebar.error("A pasta '/reports' não foi encontrada.")

    # Lógica Principal de Carregamento e Filtros
    if uploaded_files or (use_local_files and local_files):
        with st.spinner("🔄 Carregando e processando dados..."):
            if use_local_files and local_files:
                analyzer.data = analyzer.load_local_files(
                    data_dir, local_files
                )
            else:
                analyzer.data = analyzer.load_data(uploaded_files)

        if analyzer.data is not None:
            st.success(
                f"""✅ Dados carregados com sucesso!
                    Total: {len(analyzer.data):,} registros
                """
            )

            st.sidebar.subheader("🔍 Filtros de Análise")

            # Filtro de anos
            if "ano" in analyzer.data.columns:
                anos_disponiveis = sorted(
                    analyzer.data["ano"].dropna().unique()
                )
                anos_selecionados = st.sidebar.multiselect(
                    "📅 Anos", anos_disponiveis, default=anos_disponiveis
                )
            else:
                anos_selecionados = []

            # Filtro de UF
            if "uf" in analyzer.data.columns:
                ufs_disponiveis = sorted(analyzer.data["uf"].dropna().unique())
                default_ufs = ufs_disponiveis
                ufs_selecionadas = st.sidebar.multiselect(
                    "📍 Estados (UF)",
                    ufs_disponiveis,
                    default=default_ufs,
                )
            else:
                ufs_selecionadas = []

            # Filtro de BR
            if "br" in analyzer.data.columns:
                brs_disponiveis = sorted(analyzer.data["br"].dropna().unique())
                brs_selecionadas = st.sidebar.multiselect(
                    "🛣️ Rodovias (BR)",
                    brs_disponiveis,
                    default=brs_disponiveis,
                )
            else:
                brs_selecionadas = []

            # Filtro de fase do dia
            if "fase_dia" in analyzer.data.columns:
                fases_disponiveis = analyzer.data["fase_dia"].dropna().unique()
                fases_selecionadas = st.sidebar.multiselect(
                    "🌙 Fase do Dia",
                    fases_disponiveis,
                    default=fases_disponiveis,
                )
            else:
                fases_selecionadas = []

            # Filtro de condição meteorológica
            if "condicao_metereologica" in analyzer.data.columns:
                condicoes_disponiveis = (
                    analyzer.data["condicao_metereologica"].dropna().unique()
                )
                condicoes_selecionadas = st.sidebar.multiselect(
                    "🌤️ Condição Meteorológica",
                    condicoes_disponiveis,
                    default=(
                        condicoes_disponiveis[:5]
                        if len(condicoes_disponiveis) > 5
                        else condicoes_disponiveis
                    ),
                )
            else:
                condicoes_selecionadas = []

            # Aplicar filtros
            filters = {
                "anos": anos_selecionados,
                "ufs": ufs_selecionadas,
                "brs": brs_selecionadas,
                "fase_dia": fases_selecionadas,
                "condicao_meteorologica": condicoes_selecionadas,
            }
            analyzer.filtered_data = analyzer.apply_filters(
                analyzer.data, filters
            )

            if not analyzer.filtered_data.empty:
                create_dashboard(analyzer)
            else:
                st.warning(
                    "⚠️ Nenhum dado encontrado com os filtros aplicados."
                )
    else:
        st.info(
            (
                """📤 Faça upload dos arquivos CSV ou coloque-os na pasta
                /data para começar a análise."""
            )
        )
        st.markdown(
            """
             <div class="highlight-box"> <h3>🎯 Sobre o Projeto
            "Iluminar para Proteger"</h3> <p>Este aplicativo analisa dados de
            acidentes rodoviários no Brasil (2020-2024) para identificar
            trechos críticos onde a instalação de iluminação solar pode
            reduzir acidentes
            noturnos.</p>
            <h4>📋 Funcionalidades Principais:</h4>
            <ul>
            <li>🔍 Análise comparativa de acidentes noturnos vsdiurnos</li>
            <li>📊 Identificação de trechos prioritários (BR + KM + UF)</li>
            <li>💰 Cálculo de ROI para instalação de postes solares</li>
            <li>🗺️ Visualização geográfica de acidentes</li>
            <li>📈 Tendências temporais e análises estatísticas</li>
            <li>📑
            Relatórios em PDF para tomada de decisão</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()

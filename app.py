"""
Ponto de Entrada da Aplicação Streamlit — Iluminar para Proteger.
Configura interface, gerencia upload/carregamento em cache,
controles de sidebar e delega renderização ao dashboard.
"""

import os
import warnings
from datetime import datetime
import streamlit as st
from analyzer import AccidentAnalyzer
from dashboard import create_dashboard
from config import APP_CONFIG, DATA_DIR, REPORTS_DIR, FASES_DIA_OFICIAIS, CAUSAS_VISIBILIDADE_REACAO

warnings.filterwarnings("ignore")

# Configuração da página
st.set_page_config(
    page_title=APP_CONFIG["title"] + " — Análise Científica de Segurança Viária",
    page_icon=APP_CONFIG["icon"],
    layout=APP_CONFIG["layout"],
    initial_sidebar_state="expanded",
)

# Estilo CSS customizado (preserva identidade visual escura/clara)
st.html(
    """
    <style>
    .main-header {
        font-size: 2.6rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .main-subtitle {
        text-align: center;
        font-size: 1.15rem;
        color: #6c757d;
        margin-bottom: 1.8rem;
    }
    .metric-container, .highlight-box {
        background-color: #ffffff;
        color: #222222 !important;
        padding: 1.2rem;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .metric-container h4, .highlight-box h3, .highlight-box h4 {
        color: #1f77b4 !important;
        margin-top: 0;
    }

    @media (prefers-color-scheme: dark) {
        .metric-container, .highlight-box {
            background-color: #1a2332;
            color: #f0f2f6 !important;
            border-left: 5px solid #4fa3ff;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        .metric-container h4, .highlight-box h3, .highlight-box h4 {
            color: #4fa3ff !important;
        }
        .main-subtitle {
            color: #a0aec0;
        }
    }
    </style>
    """
)


def main():
    st.markdown('<h1 class="main-header">🌟 Iluminar para Proteger</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="main-subtitle">{APP_CONFIG["subtitle"]}</p>',
        unsafe_allow_html=True,
    )

    analyzer = AccidentAnalyzer()

    # =========================================================================
    # SIDEBAR: CONTROLES DE CARREGAMENTO
    # =========================================================================
    st.sidebar.header("📊 Controles do Sistema")
    st.sidebar.subheader("📁 Carregamento de Dados")

    st.sidebar.info("""
    📄 **Formatos suportados:**
    - Parquet (.parquet) — Alta performance e leitura rápida
    - CSV (.csv) — Microdados oficiais da PRF
    """)

    uploaded_files = st.sidebar.file_uploader(
        "Selecione arquivos de acidentes",
        type=["csv", "parquet"],
        accept_multiple_files=True,
        help="Arquivos CSV ou Parquet da PRF (ex: acidentes_todas_causas_tipos)",
    )

    data_dir = str(DATA_DIR)
    local_files = []
    if os.path.exists(data_dir):
        local_files = [f for f in os.listdir(data_dir) if f.endswith((".csv", ".parquet"))]

    # Se a pasta /data estiver vazia (ex: deploy em nuvem no Streamlit Community Cloud),
    # utiliza automaticamente as bases Parquet de 2025 e 2026 do repositório.
    if not local_files and os.path.exists("parquet_samples"):
        data_dir = "parquet_samples"
        parquets_25_26 = [f for f in os.listdir(data_dir) if ("2025" in f or "2026" in f) and f.endswith(".parquet")]
        local_files = sorted(parquets_25_26) if parquets_25_26 else sorted([f for f in os.listdir(data_dir) if f.endswith(".parquet")])

    use_local_files = False
    if local_files:
        st.sidebar.caption(f"📂 {len(local_files)} arquivo(s) disponível(is) na pasta `{data_dir}`")
        use_local_files = st.sidebar.checkbox(
            f"Usar dados da pasta /{data_dir}",
            value=True if not uploaded_files else False,
            key="use_local_files_checkbox",
        )

    # =========================================================================
    # SIDEBAR: RELATÓRIOS SALVOS
    # =========================================================================
    st.sidebar.subheader("📄 Relatórios Técnicos Salvos")
    reports_dir = str(REPORTS_DIR)
    try:
        report_files = [f for f in os.listdir(reports_dir) if f.endswith(".pdf")]
        if not report_files:
            st.sidebar.caption("Nenhum relatório gerado ainda.")
        else:
            reports_with_dates = []
            for r_name in report_files:
                r_path = os.path.join(reports_dir, r_name)
                reports_with_dates.append({
                    "name": r_name,
                    "path": r_path,
                    "date": datetime.fromtimestamp(os.path.getmtime(r_path)),
                })
            reports_with_dates.sort(key=lambda x: x["date"], reverse=True)

            for rep in reports_with_dates[:5]:
                col_btn, col_del = st.sidebar.columns([3, 1])
                with col_btn:
                    with open(rep["path"], "rb") as f_rep:
                        pdf_bytes = f_rep.read()
                    st.download_button(
                        label=f"📥 {rep['name'][:22]}...",
                        data=pdf_bytes,
                        file_name=rep["name"],
                        mime="application/pdf",
                        help=f"{rep['name']} — Gerado em: {rep['date'].strftime('%d/%m/%Y %H:%M')}",
                    )
                with col_del:
                    if st.button("🗑️", key=f"del_{rep['name']}", help="Excluir relatório"):
                        os.remove(rep["path"])
                        st.rerun()
    except Exception:
        pass

    # =========================================================================
    # CARREGAMENTO COM GESTÃO DE CACHE EM MEMÓRIA
    # =========================================================================
    has_data_source = uploaded_files or (use_local_files and local_files)

    if has_data_source:
        # Assinatura dos arquivos para detecção de mudança
        file_signature = (
            "local_" + "_".join(sorted(local_files))
            if (use_local_files and local_files)
            else "upload_" + "_".join(sorted([f.name for f in uploaded_files]))
        )

        # Se já estiver carregado no session_state para esta mesma assinatura, reusa
        if (
            "cached_analyzer_data" in st.session_state
            and st.session_state.get("cached_file_signature") == file_signature
        ):
            analyzer.data = st.session_state["cached_analyzer_data"]
            analyzer.pessoas_data = st.session_state.get("cached_analyzer_pessoas")
            analyzer.veiculos_data = st.session_state.get("cached_analyzer_veiculos")
            analyzer.causas_data = st.session_state["cached_analyzer_causas"]
            analyzer.quality_summary = st.session_state["cached_analyzer_quality"]
        else:
            with st.spinner("🔄 Carregando e auditando dados com desduplicação..."):
                if use_local_files and local_files:
                    analyzer.data = analyzer.load_local_files(data_dir, local_files)
                else:
                    analyzer.data = analyzer.load_data(uploaded_files)

            if analyzer.data is not None:
                st.session_state["cached_analyzer_data"] = analyzer.data
                st.session_state["cached_analyzer_pessoas"] = analyzer.pessoas_data
                st.session_state["cached_analyzer_veiculos"] = analyzer.veiculos_data
                st.session_state["cached_analyzer_causas"] = analyzer.causas_data
                st.session_state["cached_analyzer_quality"] = analyzer.quality_summary
                st.session_state["cached_file_signature"] = file_signature

        if analyzer.data is not None and not analyzer.data.empty:
            # =================================================================
            # SIDEBAR: FILTROS DINÂMICOS
            # =================================================================
            st.sidebar.markdown("---")
            st.sidebar.subheader("🔍 Filtros Dinâmicos")

            # 1. Filtro de Anos
            if "ano" in analyzer.data.columns:
                anos_disp = sorted([int(a) for a in analyzer.data["ano"].dropna().unique()])
                anos_sel = st.sidebar.multiselect("📅 Ano(s)", anos_disp, default=anos_disp)
            else:
                anos_sel = []

            # 2. Filtro de Estados (UF)
            if "uf" in analyzer.data.columns:
                ufs_disp = sorted([str(u) for u in analyzer.data["uf"].dropna().unique()])
                ufs_sel = st.sidebar.multiselect("📍 Estados (UF)", ufs_disp, default=ufs_disp)
            else:
                ufs_sel = []

            # 3. Filtro de Rodovias (BR)
            if "br" in analyzer.data.columns:
                brs_disp = sorted([str(b) for b in analyzer.data["br"].dropna().unique() if str(b) != "N/A"])
                brs_sel = st.sidebar.multiselect(
                    "🛣️ Rodovias Federais (BR)",
                    brs_disp,
                    default=brs_disp,
                    help="Por padrão, inclui todas as rodovias nominais e ocorrências elegíveis para análise nacional (121.241 registros).",
                )
            else:
                brs_sel = []

            # 4. Filtro de Fase do Dia (Oficial da PRF)
            col_fase = "fase_dia_oficial" if "fase_dia_oficial" in analyzer.data.columns else "fase_dia"
            fases_disp = sorted([str(f) for f in analyzer.data[col_fase].dropna().unique()])
            fases_sel = st.sidebar.multiselect(
                "🌙 Fase do Dia",
                fases_disp,
                default=fases_disp,
                help="Categorias oficiais da PRF: Pleno dia, Plena Noite, Amanhecer, Anoitecer",
            )

            # 5. Filtro de Condição Meteorológica
            if "condicao_metereologica" in analyzer.data.columns:
                cond_disp = sorted([str(c) for c in analyzer.data["condicao_metereologica"].dropna().unique()])
                cond_sel = st.sidebar.multiselect("🌤️ Condição Meteorológica", cond_disp, default=cond_disp)
            else:
                cond_sel = []

            # 6. Filtro Opcional por Grupo de Causas
            causas_sel = []
            if analyzer.causas_data is not None and not analyzer.causas_data.empty:
                opcoes_causas = st.sidebar.checkbox("Filtrar apenas causas de visibilidade/reação", value=False)
                if opcoes_causas:
                    causas_disp = sorted([
                        c for c in analyzer.causas_data["causa_acidente"].dropna().unique()
                        if any(term.lower() in str(c).lower() for term in ["reação", "dormindo", "velocidade", "ultrapassagem", "atenção", "álcool", "pedestre", "faixa"])
                    ])
                    causas_sel = st.sidebar.multiselect("Causas Selecionadas", causas_disp, default=causas_disp[:10])

            # 7. Filtros Demográficos e de Frota (Opcionais)
            tipos_env_sel = []
            sexos_sel = []
            faixas_sel = []
            tipos_veic_sel = []

            if analyzer.pessoas_data is not None and not analyzer.pessoas_data.empty:
                with st.sidebar.expander("👥 Perfil Demográfico e Frota", expanded=False):
                    # Envolvimento
                    if "tipo_envolvido" in analyzer.pessoas_data.columns:
                        env_disp = sorted([str(e) for e in analyzer.pessoas_data["tipo_envolvido"].dropna().unique()])
                        env_user = st.multiselect("Tipo de Envolvimento", env_disp, default=env_disp)
                        if len(env_user) < len(env_disp):
                            tipos_env_sel = env_user

                    # Sexo
                    if "sexo" in analyzer.pessoas_data.columns:
                        sex_disp = sorted([str(s) for s in analyzer.pessoas_data["sexo"].dropna().unique()])
                        sex_user = st.multiselect("Sexo", sex_disp, default=sex_disp)
                        if len(sex_user) < len(sex_disp):
                            sexos_sel = sex_user

                    # Faixa Etária
                    if "faixa_etaria" in analyzer.pessoas_data.columns:
                        faixas_disp = sorted([str(f) for f in analyzer.pessoas_data["faixa_etaria"].dropna().unique()])
                        faixas_user = st.multiselect("Faixa Etária", faixas_disp, default=faixas_disp)
                        if len(faixas_user) < len(faixas_disp):
                            faixas_sel = faixas_user

                    # Tipo de Veículo
                    if analyzer.veiculos_data is not None and not analyzer.veiculos_data.empty and "tipo_veiculo" in analyzer.veiculos_data.columns:
                        veic_disp = sorted([str(v) for v in analyzer.veiculos_data["tipo_veiculo"].dropna().unique()])
                        veic_user = st.multiselect("Tipo de Veículo", veic_disp, default=veic_disp)
                        if len(veic_user) < len(veic_disp):
                            tipos_veic_sel = veic_user

            # Aplicar filtros
            filters = {
                "anos": anos_sel,
                "ufs": ufs_sel,
                "brs": brs_sel,
                "fase_dia": fases_sel,
                "condicao_meteorologica": cond_sel,
                "causas_selecionadas": causas_sel,
                "tipos_envolvido": tipos_env_sel,
                "sexos": sexos_sel,
                "faixas_etarias": faixas_sel,
                "tipos_veiculo": tipos_veic_sel,
            }
            analyzer.filtered_data = analyzer.apply_filters(analyzer.data, filters)

            if not analyzer.filtered_data.empty:
                create_dashboard(analyzer)
            else:
                st.warning("⚠️ Nenhum registro encontrado com a combinação atual de filtros.")

    else:
        # Mensagem inicial quando não há arquivos selecionados
        st.info("📤 Faça upload dos arquivos CSV/Parquet ou ative a opção de arquivos locais na barra lateral para iniciar a análise.")
        st.html(
            """
            <div class="highlight-box">
                <h3>🎯 Sobre o Projeto Iluminar para Proteger</h3>
                <p>Este sistema realiza a auditoria e análise científica dos acidentes registrados pela Polícia Rodoviária Federal (PRF), 
                investigando a severidade das ocorrências noturnas e modelando a viabilidade de postes solares inteligentes autônomos 
                como contramedida comprovada de segurança viária.</p>
                <h4>📋 Módulos Principais do Sistema:</h4>
                <ul>
                    <li>🛡️ <strong>Auditoria de Dados:</strong> Desduplicação estrita de pessoas e causas e eliminação do erro de KM 0,0</li>
                    <li>🌗 <strong>Comparação Dia vs Noite:</strong> Indicadores de letalidade e severidade por 100 acidentes</li>
                    <li>👁️ <strong>Tempo de Reação e Visibilidade:</strong> Avaliação empírica do mecanismo PIEV com rigor causal</li>
                    <li>🚨 <strong>Segmentação Viária:</strong> Identificação de trechos críticos de 2 km baseada em severidade noturna</li>
                    <li>💰 <strong>Viabilidade Financeira:</strong> Dimensionamento físico, CAPEX, OPEX, VPL, TIR e Payback</li>
                    <li>🌟 <strong>Protótipo 3D:</strong> Simulação interativa do poste solar inteligente</li>
                    <li>📄 <strong>Relatório Científico:</strong> Exportação completa em PDF com todas as 15 seções acadêmicas</li>
                </ul>
            </div>
            """
        )


if __name__ == "__main__":
    main()

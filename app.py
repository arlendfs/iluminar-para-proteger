"""
Ponto de Entrada da Aplicação Streamlit — Iluminar para Proteger.
Configura interface, gerencia upload/carregamento em cache,
controles de sidebar e delega renderização ao dashboard.
"""

import os
import re
import gc
import time
import uuid
import shutil
import threading
import warnings
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import streamlit as st
from analyzer import AccidentAnalyzer
from dashboard import create_dashboard
try:
    from config import (
        APP_CONFIG,
        BASE_DIR,
        DATA_DIR,
        REPORTS_DIR,
        PARQUET_SAMPLES_DIR,
        FASES_DIA_OFICIAIS,
        CAUSAS_VISIBILIDADE_REACAO,
        get_current_rss_mb,
        log_memory_checkpoint,
        get_container_memory_info,
    )
except ImportError:
    import importlib
    import config
    importlib.reload(config)
    from config import (
        APP_CONFIG,
        BASE_DIR,
        DATA_DIR,
        REPORTS_DIR,
        PARQUET_SAMPLES_DIR,
        FASES_DIA_OFICIAIS,
        CAUSAS_VISIBILIDADE_REACAO,
        get_current_rss_mb,
        log_memory_checkpoint,
    )
    get_container_memory_info = getattr(
        config,
        "get_container_memory_info",
        lambda: {"container_limit_mb": None, "limit_mb": None, "detected_environment": "fallback"}
    )

# Controle global de concorrência para processamento intensivo (máximo 2 análises pesadas simultâneas)
HEAVY_ANALYSIS_SEMAPHORE = threading.BoundedSemaphore(2)

# Rastreamento de sessões ativas sem expor identidades de usuários
ACTIVE_SESSIONS: Dict[str, float] = {}

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


def scan_project_folder(folder_name: str) -> List[Dict[str, Any]]:
    """
    Lista arquivos CSV e Parquet reais da pasta indicada ('data' ou 'parquet_samples').
    Garante resolução absoluta via Path(__file__).resolve().parent sem fallback automático.
    """
    base_dir = Path(__file__).resolve().parent
    folder_path = base_dir / folder_name
    if not folder_path.exists() or not folder_path.is_dir():
        return []

    files_info = []
    for p in folder_path.iterdir():
        if p.is_file() and p.suffix.lower() in [".parquet", ".csv"]:
            size_bytes = p.stat().st_size
            mtime = p.stat().st_mtime
            if size_bytes >= 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size_bytes / 1024:.0f} KB"
            m = re.search(r"(20[0-9]{2})", p.name)
            year = int(m.group(1)) if m else None
            files_info.append({
                "name": p.name,
                "path": str(p),
                "extension": p.suffix.lower(),
                "year": year,
                "size_bytes": size_bytes,
                "size_str": size_str,
                "mtime": mtime,
            })
    return sorted(files_info, key=lambda x: (x["year"] or 0, x["name"]))


def main():
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())[:8]
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    now = time.time()
    ACTIVE_SESSIONS[st.session_state["session_id"]] = now
    for sid in list(ACTIVE_SESSIONS.keys()):
        if now - ACTIVE_SESSIONS[sid] > 1800:
            ACTIVE_SESSIONS.pop(sid, None)
    active_sessions_count = len(ACTIVE_SESSIONS)

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

    # 1. Upload do Computador
    uploaded_files = st.sidebar.file_uploader(
        "Selecione arquivos de acidentes",
        type=["csv", "parquet"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state['uploader_key']}",
        help="Arquivos CSV ou Parquet da PRF (ex: acidentes_todas_causas_tipos)",
    )

    # 2. Checkbox obrigatório: inicia SEMPRE DESLIGADO (value=False)
    use_local_folder = st.sidebar.checkbox(
        "Usar arquivos de uma pasta do projeto",
        value=False,
        key="use_local_folder",
        help="Habilita a seleção direta de pastas locais de microdados do repositório.",
    )

    selected_local_files = []
    selected_folder = None
    folder_path_str = None
    file_map = {}

    if use_local_folder:
        # Seletor com exatamente duas opções independentes
        selected_folder = st.sidebar.selectbox(
            "Selecione a pasta do projeto",
            options=["parquet_samples", "data"],
            format_func=lambda x: f"/{x}",
            index=0,
            key="selected_project_folder",
        )
        base_dir = Path(__file__).resolve().parent
        folder_path = base_dir / selected_folder
        folder_path_str = str(folder_path)

        files_available = scan_project_folder(selected_folder)
        if not files_available:
            st.sidebar.warning(f"⚠️ A pasta `/{selected_folder}` está vazia ou não contém arquivos CSV/Parquet válidos.")
        else:
            st.sidebar.caption(f"📂 {len(files_available)} arquivo(s) disponível(is) na pasta `/{selected_folder}`:")

            # Mapeamento e identificação de duplicidades por ano
            years_count = {}
            for f in files_available:
                file_map[f["name"]] = f
                if f["year"]:
                    years_count.setdefault(f["year"], []).append(f)

            duplicates_info = {yr: flist for yr, flist in years_count.items() if len(flist) > 1}
            if duplicates_info:
                st.sidebar.info("ℹ️ Identificados arquivos CSV e Parquet para o mesmo ano. O sistema pré-seleciona Parquet por padrão para máxima performance.")

            # Seleção padrão sugerida: se houver duplicata de ano, prioriza Parquet
            default_selection = []
            seen_years = set()
            sorted_by_pref = sorted(files_available, key=lambda x: (x["year"] or 0, 0 if x["extension"] == ".parquet" else 1))
            for f in sorted_by_pref:
                if f["year"] not in seen_years:
                    default_selection.append(f["name"])
                    seen_years.add(f["year"])
                elif f["year"] is None:
                    default_selection.append(f["name"])

            file_options = [f["name"] for f in files_available]
            selected_local_files = st.sidebar.multiselect(
                "Selecione os arquivos para análise",
                options=file_options,
                default=default_selection,
                format_func=lambda name: f"{name} ({file_map[name]['year'] or 'S/A'} - {file_map[name]['size_str']})",
                help="Selecione um ou mais arquivos. Nenhuma base é processada automaticamente.",
            )

    # =========================================================================
    # REGRAS DE ORIGEM MUTUAMENTE EXCLUSIVA
    # =========================================================================
    active_source = None
    if uploaded_files and (use_local_folder and selected_local_files):
        st.sidebar.warning("⚠️ Detectados upload e pasta local simultaneamente. Escolha qual origem utilizar:")
        chosen_source = st.sidebar.radio(
            "Origem ativa:",
            options=["Upload de Arquivos", f"Pasta /{selected_folder}"],
            index=0,
            key="exclusive_source_choice",
        )
        if chosen_source == "Upload de Arquivos":
            active_source = "upload"
        else:
            active_source = "local"
    elif uploaded_files:
        active_source = "upload"
    elif use_local_folder and selected_local_files:
        active_source = "local"

    # =========================================================================
    # BOTÃO EXPLÍCITO DE PROCESSAMENTO
    # =========================================================================
    btn_carregar = False
    if active_source is not None:
        btn_carregar = st.sidebar.button(
            "🚀 Carregar e analisar arquivos selecionados",
            type="primary",
            width="stretch",
            key="btn_carregar_dados",
        )

    # Assinatura estrita da fonte para controle de cache e invalidação
    if active_source == "local":
        file_signature = f"local_{selected_folder}_" + "_".join(
            sorted([f"{f}_{file_map[f]['size_bytes']}_{file_map[f]['mtime']}" for f in selected_local_files])
        )
    elif active_source == "upload":
        file_signature = "upload_" + "_".join(
            sorted([f"{f.name}_{getattr(f, 'size', 0)}" for f in uploaded_files])
        )
    else:
        file_signature = None

    # Invalidação de cache caso a fonte ou seleção tenha sido modificada
    if st.session_state.get("cached_file_signature") != file_signature:
        st.session_state.pop("cached_analyzer_data", None)
        st.session_state.pop("cached_analyzer_pessoas", None)
        st.session_state.pop("cached_analyzer_veiculos", None)
        st.session_state.pop("cached_analyzer_causas", None)
        st.session_state.pop("cached_analyzer_quality", None)
        st.session_state.pop("data_processed_once", None)
        gc.collect()

    # =========================================================================
    # SIDEBAR: GESTÃO DE MEMÓRIA DA SESSÃO
    # =========================================================================
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧹 Gestão de Recursos da Sessão")
    if st.sidebar.button(
        "Limpar minha análise e liberar recursos",
        type="secondary",
        width="stretch",
        help="Invalida os dados da sua sessão, remove arquivos temporários exclusivos e executa liberação de memória sem afetar outros usuários.",
        key="btn_limpar_memoria_usuario",
    ):
        for k in [
            "cached_analyzer_data",
            "cached_analyzer_pessoas",
            "cached_analyzer_veiculos",
            "cached_analyzer_causas",
            "cached_analyzer_quality",
            "cached_file_signature",
            "data_processed_once",
        ]:
            st.session_state.pop(k, None)
        st.session_state["uploader_key"] = st.session_state.get("uploader_key", 0) + 1
        sess_temp = BASE_DIR / "temp" / st.session_state.get("session_id", "")
        if sess_temp.exists():
            shutil.rmtree(sess_temp, ignore_errors=True)
        analyzer.clear()
        gc.collect()
        st.sidebar.success("Recursos liberados para a sua sessão.")
        st.rerun()

    # Diagnóstico de Memória e Recursos do Servidor
    current_rss = get_current_rss_mb()
    c_info = get_container_memory_info()
    st.sidebar.caption(f"💾 Memória do Processo (RSS): **{current_rss:.1f} MB**")
    if c_info.get("limit_mb") and c_info["limit_mb"] < 100000:
        st.sidebar.caption(f"🖥️ Limite do Contêiner: **{c_info['limit_mb']:.0f} MB**")
    st.sidebar.caption(f"👥 Sessões ativas estimadas: **{active_sessions_count}**")

    # =========================================================================
    # SIDEBAR: RELATÓRIOS SALVOS DA SESSÃO
    # =========================================================================
    st.sidebar.subheader("📄 Relatórios Técnicos Salvos")
    session_reports_dir = REPORTS_DIR / st.session_state["session_id"]
    session_reports_dir.mkdir(parents=True, exist_ok=True)
    try:
        report_files = [f for f in os.listdir(str(session_reports_dir)) if f.endswith(".pdf")]
        if not report_files:
            st.sidebar.caption("Nenhum relatório gerado nesta sessão ainda.")
        else:
            reports_with_dates = []
            for r_name in report_files:
                r_path = os.path.join(str(session_reports_dir), r_name)
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
                        width="stretch",
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
    has_data_source = active_source is not None and (
        (active_source == "upload" and uploaded_files)
        or (active_source == "local" and selected_local_files)
    )

    # Processamento somente mediante ação explícita (clique no botão ou reuso de cache consistente)
    should_process = has_data_source and (
        btn_carregar
        or (
            "cached_analyzer_data" in st.session_state
            and st.session_state.get("cached_file_signature") == file_signature
            and st.session_state.get("data_processed_once", False)
        )
    )

    if should_process:
        if (
            "cached_analyzer_data" in st.session_state
            and st.session_state.get("cached_file_signature") == file_signature
        ):
            analyzer.data = st.session_state["cached_analyzer_data"]
            analyzer.pessoas_data = st.session_state.get("cached_analyzer_pessoas")
            analyzer.veiculos_data = st.session_state.get("cached_analyzer_veiculos")
            analyzer.causas_data = st.session_state.get("cached_analyzer_causas")
            analyzer.quality_summary = st.session_state.get("cached_analyzer_quality", {})
        else:
            acquired = HEAVY_ANALYSIS_SEMAPHORE.acquire(blocking=False)
            if not acquired:
                st.sidebar.error("⚠️ O servidor atingiu o limite de análises concorrentes (máximo de 2 simultâneas). Por favor, aguarde alguns instantes e tente novamente.")
                st.stop()
            try:
                with st.spinner("🔄 Processando arquivos incrementalmente e auditando dados com desduplicação..."):
                    t_load_start = time.time()
                    if active_source == "local":
                        analyzer.data = analyzer.load_local_files(folder_path_str, selected_local_files)
                    else:
                        analyzer.data = analyzer.load_data(uploaded_files, session_id=st.session_state["session_id"])
                    log_memory_checkpoint("Carga incremental e auditoria concluída", start_time=t_load_start)
            except MemoryError:
                st.error("❌ Memória insuficiente para processar a seleção de dados. Por favor, reduza a quantidade de arquivos/anos selecionados.")
                analyzer.clear()
                gc.collect()
                st.stop()
            except Exception as e:
                st.error(f"❌ Erro durante o processamento de dados: {str(e)}")
                analyzer.clear()
                gc.collect()
                st.stop()
            finally:
                HEAVY_ANALYSIS_SEMAPHORE.release()

            if analyzer.data is not None and not analyzer.data.empty:
                st.session_state["cached_analyzer_data"] = analyzer.data
                st.session_state["cached_analyzer_pessoas"] = analyzer.pessoas_data
                st.session_state["cached_analyzer_veiculos"] = analyzer.veiculos_data
                st.session_state["cached_analyzer_causas"] = analyzer.causas_data
                st.session_state["cached_analyzer_quality"] = analyzer.quality_summary
                st.session_state["cached_file_signature"] = file_signature
                st.session_state["data_processed_once"] = True

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
        # Apresentação inicial quando nenhuma fonte foi processada
        st.info("📤 Para iniciar, selecione os arquivos desejados na barra lateral (via upload do computador ou ativando 'Usar arquivos de uma pasta do projeto') e clique no botão **Carregar e analisar arquivos selecionados**.")
        st.html(
            """
            <div class="highlight-box">
                <h3>🎯 Sobre o Projeto Iluminar para Proteger</h3>
                <p>Este sistema realiza a auditoria e análise científica dos acidentes registrados pela Polícia Rodoviária Federal (PRF), 
                investigando a severidade das ocorrências noturnas e modelando a viabilidade técnica e socioeconômica de postes solares inteligentes autônomos 
                como proposta de intervenção de segurança viária (baseada em contramedidas recomendadas pela FHWA, sujeita a validação de campo).</p>
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

"""
Módulo de Análise Científica de Visibilidade Noturna, Tempo de Reação e Fatores Associados.
Examina causas de acidentes ligadas à percepção visual e resposta do condutor,
contrastando frequências, letalidade e estratificações ambientais/viárias.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from config import CAUSAS_VISIBILIDADE_REACAO


REPORT_CAUSE_LABELS = (
    "Reação tardia ou ineficiente do condutor",
    "Ausência de reação do condutor",
    "Condutor Dormindo",
    "Ultrapassagem Indevida",
    "Velocidade Incompatível",
    "Ingestão de Álcool pelo condutor",
)


def filter_reaction_causes(causes_df: pd.DataFrame, custom_causes: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Filtra a tabela de causas para aquelas relacionadas à percepção,
    visibilidade, tempo de reação e resposta psicomotora do condutor.
    """
    if causes_df.empty or "causa_acidente" not in causes_df.columns:
        return pd.DataFrame()

    target_causes = custom_causes if custom_causes else CAUSAS_VISIBILIDADE_REACAO
    # Cria regex case-insensitive para correspondência robusta
    pattern = "|".join([re_escape(c) for c in target_causes])
    mask = causes_df["causa_acidente"].astype(str).str.contains(pattern, case=False, na=False)
    return causes_df[mask].copy()


def re_escape(text: str) -> str:
    """Escapa caracteres especiais para regex preservando palavras-chave."""
    import re
    return re.escape(text)


def analyze_visibility_and_reaction(
    ocorrencias_df: pd.DataFrame,
    causas_df: pd.DataFrame,
    selected_causes: Optional[List[str]] = None,
    include_details: bool = True,
) -> Dict[str, Any]:
    """
    Realiza a análise integrada de causas de visibilidade e reação:
    - Cruza ocorrências com causas
    - Calcula participação relativa em cada período (Diurno vs Noturno)
    - Calcula taxa de mortalidade e severidade por causa
    - Estratifica por condição meteorológica, tipo de pista e traçado
    """
    if ocorrencias_df.empty:
        return {}

    # As agregações abaixo usam apenas estas medidas. Evita materializar
    # todas as colunas descritivas/geográficas em cada junção causa–ocorrência.
    phase_column = "fase_dia_agrupada" if "fase_dia_agrupada" in ocorrencias_df.columns else "fase_dia"
    needed = [
        "id", "mortos", "total_feridos", "acidente_fatal",
        phase_column, "fase_dia_oficial", "condicao_metereologica", "tipo_pista",
    ]
    if causas_df.empty:
        needed.append("causa_acidente")
    occurrence_columns = [col for col in needed if col in ocorrencias_df.columns]
    occurrence_view = ocorrencias_df[occurrence_columns]

    # Se a tabela de causas estiver vazia mas ocorrencias tiver causa_acidente, usar da ocorrencia
    if causas_df.empty and "causa_acidente" in ocorrencias_df.columns:
        merged = occurrence_view.copy()
    elif not causas_df.empty and "id" in causas_df.columns:
        # Garantir chave única (id, causa_acidente) para não duplicar vítimas da ocorrência
        if include_details:
            causas_relevantes = causas_df[["id", "causa_acidente"]]
        else:
            # O PDF mostra somente estas seis causas; filtrar antes da junção
            # evita multiplicar todas as ocorrências por causas não exibidas.
            report_pattern = "|".join(re_escape(label) for label in REPORT_CAUSE_LABELS)
            mask_relevantes = causas_df["causa_acidente"].str.contains(report_pattern, case=False, na=False)
            causas_relevantes = causas_df.loc[mask_relevantes, ["id", "causa_acidente"]]
        causas_unicas = causas_relevantes.dropna().drop_duplicates()
        merged = occurrence_view.drop(columns=["causa_acidente"], errors="ignore").merge(causas_unicas, on="id", how="inner")
    else:
        merged = occurrence_view.copy()

    if "causa_acidente" not in merged.columns or merged["causa_acidente"].dropna().empty:
        return {
            "tabela_causas_resumo": pd.DataFrame(),
            "causas_visibilidade_noturna": pd.DataFrame(),
            "evidencias": "Dados de causas não disponíveis na base selecionada.",
        }

    # Limpeza e padronização dos nomes das causas
    merged["causa_normalizada"] = merged["causa_acidente"].astype(str).str.strip()
    
    # Período agrupado
    col_periodo = "fase_dia_agrupada" if "fase_dia_agrupada" in merged.columns else "fase_dia"

    if include_details:
        # 1. Ranking Geral de Causas com métricas de gravidade
        ranking_causas = (
            merged.groupby("causa_normalizada", observed=True)
            .agg(
                total_ocorrencias=("id", "nunique"),
                total_mortos=("mortos", "sum"),
                total_feridos=("total_feridos", "sum"),
                acidentes_fatais=("acidente_fatal", "sum"),
            )
            .reset_index()
        )
        ranking_causas["total_ocorrencias"] = pd.to_numeric(ranking_causas["total_ocorrencias"], errors="coerce").fillna(0)
        ranking_causas["acidentes_fatais"] = pd.to_numeric(ranking_causas["acidentes_fatais"], errors="coerce").fillna(0)
        ranking_causas["total_mortos"] = pd.to_numeric(ranking_causas["total_mortos"], errors="coerce").fillna(0)
        ranking_causas["letalidade_pct"] = (
            ranking_causas["acidentes_fatais"] / ranking_causas["total_ocorrencias"].replace(0, np.nan) * 100
        ).fillna(0)
        ranking_causas["obitos_por_100"] = (
            ranking_causas["total_mortos"] / ranking_causas["total_ocorrencias"].replace(0, np.nan) * 100
        ).fillna(0)
        ranking_causas = ranking_causas.sort_values("total_ocorrencias", ascending=False)

        # 2. Distribuição das Causas por Período (Dia vs Noite)
        causas_periodo = (
            merged.groupby(["causa_normalizada", col_periodo], observed=True)
            .agg(
                n_acidentes=("id", "nunique"),
                mortos=("mortos", "sum"),
                acidentes_fatais=("acidente_fatal", "sum"),
            )
            .reset_index()
        )

        # Calcular participação percentual de cada causa dentro do período respectivo
        totais_por_periodo = merged.groupby(col_periodo, observed=True)["id"].nunique()
        map_totais = {str(k): float(v) for k, v in totais_por_periodo.to_dict().items()}
        causas_periodo["total_periodo"] = pd.to_numeric(
            causas_periodo[col_periodo].astype(str).map(map_totais), errors="coerce"
        ).fillna(0)
        causas_periodo["n_acidentes"] = pd.to_numeric(causas_periodo["n_acidentes"], errors="coerce").fillna(0)
        causas_periodo["participacao_no_periodo_pct"] = (
            causas_periodo["n_acidentes"] / causas_periodo["total_periodo"].replace(0, np.nan) * 100
        ).fillna(0)

        # Tabela dinâmica (pivot) para comparar Diurno vs Noturno lado a lado
        pivot_causas = causas_periodo.pivot_table(
            index="causa_normalizada",
            columns=col_periodo,
            values=["n_acidentes", "participacao_no_periodo_pct", "mortos"],
            fill_value=0,
            observed=True,
        )
        # Aplanar colunas multiindex
        pivot_causas.columns = [f"{col}_{val}".lower() for col, val in pivot_causas.columns]
        pivot_causas = pivot_causas.reset_index()

        # Identificar quais são do grupo de Visibilidade e Tempo de Reação
        pattern_reacao = "|".join([re_escape(c) for c in (selected_causes or CAUSAS_VISIBILIDADE_REACAO)])
        pivot_causas["is_reacao_visibilidade"] = pivot_causas["causa_normalizada"].str.contains(pattern_reacao, case=False, na=False)

        # Estratificação das causas de reação por Meteorologia
        reacao_df = merged[merged["causa_normalizada"].str.contains(pattern_reacao, case=False, na=False)]
    
        meteo_strat = pd.DataFrame()
        if "condicao_metereologica" in reacao_df.columns:
            meteo_strat = (
                reacao_df.groupby(["condicao_metereologica", col_periodo], observed=True)
                .agg(n_acidentes=("id", "nunique"), mortos=("mortos", "sum"))
                .reset_index()
            )

        # Estratificação por Tipo de Pista
        pista_strat = pd.DataFrame()
        if "tipo_pista" in reacao_df.columns:
            pista_strat = (
                reacao_df.groupby(["tipo_pista", col_periodo], observed=True)
                .agg(n_acidentes=("id", "nunique"), mortos=("mortos", "sum"))
                .reset_index()
            )

    else:
        ranking_causas = pd.DataFrame()
        causas_periodo = pd.DataFrame()
        pivot_causas = pd.DataFrame()
        reacao_df = pd.DataFrame()
        meteo_strat = pd.DataFrame()
        pista_strat = pd.DataFrame()

    # Tabela detalhada das principais causas por fase oficial da PRF
    col_fase_oficial = "fase_dia_oficial" if "fase_dia_oficial" in merged.columns else col_periodo
    causas_fases_df = (
        merged.groupby(["causa_normalizada", col_fase_oficial], observed=True)
        .agg(
            n_acidentes=("id", "nunique"),
            total_mortos=("mortos", "sum"),
            total_feridos=("total_feridos", "sum"),
            acidentes_fatais=("acidente_fatal", "sum"),
        )
        .reset_index()
    )
    causas_fases_df["total_mortos"] = pd.to_numeric(causas_fases_df["total_mortos"], errors="coerce").fillna(0)
    causas_fases_df["acidentes_fatais"] = pd.to_numeric(causas_fases_df["acidentes_fatais"], errors="coerce").fillna(0)
    causas_fases_df["n_acidentes"] = pd.to_numeric(causas_fases_df["n_acidentes"], errors="coerce").fillna(0)
    causas_fases_df["mortos_por_100"] = (
        causas_fases_df["total_mortos"] / causas_fases_df["n_acidentes"].replace(0, np.nan) * 100
    ).fillna(0).round(2)
    causas_fases_df["prop_fatais_pct"] = (
        causas_fases_df["acidentes_fatais"] / causas_fases_df["n_acidentes"].replace(0, np.nan) * 100
    ).fillna(0).round(2)

    # Cálculos dinâmicos e reconciliação de sobreposição para causas de reação psicomotora
    m_rt = merged["causa_normalizada"].str.contains("reação tardia", case=False, na=False)
    m_ar = merged["causa_normalizada"].str.contains("ausência de reação", case=False, na=False)

    ids_rt = set(merged.loc[m_rt, "id"].dropna())
    ids_ar = set(merged.loc[m_ar, "id"].dropna())
    ids_reacao_uniao = ids_rt.union(ids_ar)
    ids_reacao_intersecao = ids_rt.intersection(ids_ar)

    mask_uniao = ocorrencias_df["id"].isin(ids_reacao_uniao)
    mortos_reacao = int(ocorrencias_df.loc[mask_uniao, "mortos"].sum()) if "mortos" in ocorrencias_df.columns else 0
    feridos_reacao = int(ocorrencias_df.loc[mask_uniao, "total_feridos"].sum()) if "total_feridos" in ocorrencias_df.columns else 0

    col_fase_of = "fase_dia_oficial" if "fase_dia_oficial" in ocorrencias_df.columns else col_periodo
    phase_labels = {}
    if col_fase_of in ocorrencias_df.columns:
        labels = ocorrencias_df[col_fase_of].dropna().unique()
        phase_labels = {
            term: [label for label in labels if term in str(label).casefold()]
            for term in ("plena noite", "pleno dia")
        }

    def get_let_fase(ids_set, fase_busca):
        if not ids_set or col_fase_of not in ocorrencias_df.columns:
            return 0.0, 0
        mask = ocorrencias_df["id"].isin(ids_set) & ocorrencias_df[col_fase_of].isin(phase_labels[fase_busca])
        n = int(mask.sum())
        mort = ocorrencias_df.loc[mask, "mortos"].sum() if "mortos" in ocorrencias_df.columns else 0
        return ((mort / n * 100) if n > 0 else 0.0), n

    let_rt_pn, n_rt_pn = get_let_fase(ids_rt, "plena noite")
    let_rt_pd, n_rt_pd = get_let_fase(ids_rt, "pleno dia")
    let_ar_pn, n_ar_pn = get_let_fase(ids_ar, "plena noite")
    let_ar_pd, n_ar_pd = get_let_fase(ids_ar, "pleno dia")

    resumo_reacao_dinamico = {
        "n_assoc_reacao_tardia": len(ids_rt),
        "n_assoc_ausencia_reacao": len(ids_ar),
        "total_associacoes_soma": len(ids_rt) + len(ids_ar),
        "n_acidentes_sobrepostos": len(ids_reacao_intersecao),
        "n_acidentes_unicos_reacao": len(ids_reacao_uniao),
        "total_mortos_reacao": mortos_reacao,
        "total_feridos_reacao": feridos_reacao,
        "let_rt_plena_noite": let_rt_pn,
        "let_rt_pleno_dia": let_rt_pd,
        "let_ar_plena_noite": let_ar_pn,
        "let_ar_pleno_dia": let_ar_pd,
    }

    # Textos de fundamentação e rigor científico rigorosamente dinâmicos
    def pt_num(value, decimals=0):
        return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

    evidencias_texto = (
        f"EVIDÊNCIA OBSERVACIONAL AUDITADA: As ocorrências com registro de 'Reação tardia ou ineficiente' "
        f"({pt_num(len(ids_rt))} associações) e 'Ausência de reação' ({pt_num(len(ids_ar))} associações) somam "
        f"{pt_num(len(ids_rt) + len(ids_ar))} apontamentos de causa. Após expurgo de sobreposições "
        f"({pt_num(len(ids_reacao_intersecao))} acidentes com ambas as causas registradas conjuntamente), "
        f"identificam-se {pt_num(len(ids_reacao_uniao))} sinistros únicos, resultando em {pt_num(mortos_reacao)} óbitos "
        f"e {pt_num(feridos_reacao)} feridos. A taxa de mortalidade em Plena Noite atinge {pt_num(let_rt_pn, 2)} óbitos/100 para reação tardia "
        f"e {pt_num(let_ar_pn, 2)} óbitos/100 para ausência de reação, contrastando com {pt_num(let_rt_pd, 2)} e {pt_num(let_ar_pd, 2)} em Pleno Dia."
    )
    hipotese_texto = (
        "HIPÓTESE INTERPRETATIVA (MECANISMO PIEV): A identificação de um risco depende da visibilidade disponível "
        "e do processo de Percepção, Identificação, Emoção e Volição (PIEV). A distância de parada depende da velocidade, "
        "do tempo de percepção e reação, do atrito, da declividade, da condição da pista e da eficiência de frenagem. "
        "O alcance dos faróis também varia com a óptica, o alinhamento, o veículo e o ambiente. Os dados analisados "
        "não medem essas condições nem permitem atribuir os sinistros à iluminação isoladamente."
    )
    limitacoes_texto = (
        "LIMITAÇÃO METODOLÓGICA EXPLÍCITA: A base pública da PRF não apresenta medições diretas de iluminância "
        "artificial (lux), luminância da superfície viária (cd/m²) ou inventário completo da iluminação existente nos locais "
        "dos acidentes. Fatores concorrentes (como alcoolemia, fadiga e distração) coexistem nas "
        "ocorrências. Portanto, correlações estatísticas não configuram causalidade isolada ou exclusiva da falta de iluminação."
    )

    return {
        "ranking_causas": ranking_causas,
        "causas_periodo": causas_periodo,
        "causas_fases_df": causas_fases_df,
        "pivot_causas": pivot_causas,
        "reacao_df": reacao_df,
        "meteo_strat": meteo_strat,
        "pista_strat": pista_strat,
        "resumo_reacao_dinamico": resumo_reacao_dinamico,
        "evidencias_texto": evidencias_texto,
        "hipotese_texto": hipotese_texto,
        "limitacoes_texto": limitacoes_texto,
        "referencia_fhwa": "FHWA Proven Safety Countermeasures: Lighting (U.S. DOT)",
    }


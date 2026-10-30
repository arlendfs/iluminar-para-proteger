"""
Módulo de Análise Científica de Visibilidade Noturna, Tempo de Reação e Fatores Associados.
Examina causas de acidentes ligadas à percepção visual e resposta do condutor,
contrastando frequências, letalidade e estratificações ambientais/viárias.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from config import CAUSAS_VISIBILIDADE_REACAO


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
    selected_causes: Optional[List[str]] = None
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

    # Se a tabela de causas estiver vazia mas ocorrencias tiver causa_acidente, usar da ocorrencia
    if causas_df.empty and "causa_acidente" in ocorrencias_df.columns:
        merged = ocorrencias_df.copy()
    elif not causas_df.empty and "id" in causas_df.columns:
        # Garantir chave única (id, causa_acidente) para não duplicar vítimas da ocorrência
        causas_unicas = causas_df[["id", "causa_acidente"]].dropna().drop_duplicates()
        merged = ocorrencias_df.merge(causas_unicas, on="id", how="inner")
    else:
        merged = ocorrencias_df.copy()

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

    # Textos de fundamentação e rigor científico
    evidencias_texto = (
        "EVIDÊNCIA OBSERVACIONAL: A base da PRF registra a frequência de causas como 'Reação tardia "
        "ou ineficiente' e 'Ausência de reação', permitindo contrastar sua ocorrência no período noturno versus diurno. "
        "Ressalta-se que uma mesma ocorrência pode conter múltiplas causas apontadas pelo agente rodoviário, "
        "de modo que as categorias podem apresentar sobreposição parcial."
    )
    hipotese_texto = (
        "HIPÓTESE INTERPRETATIVA: A visibilidade reduzida e o alcance limitado dos faróis à noite podem encurtar a "
        "distância de visão disponível em relação à distância de parada segura (DPS), diminuindo o tempo hábil "
        "para a resposta do motorista (mecanismo PIEV - Percepção, Identificação, Emoção, Volição)."
    )
    limitacoes_texto = (
        "LIMITAÇÃO CIENTÍFICA: A base oficial da PRF não possui uma variável direta indicando a presença ou "
        "nível de iluminância artificial nos trechos no momento do sinistro. Portanto, correlações observadas não "
        "comprovam isoladamente que a ausência de iluminação foi a causa exclusiva do acidente."
    )

    return {
        "ranking_causas": ranking_causas,
        "causas_periodo": causas_periodo,
        "causas_fases_df": causas_fases_df,
        "pivot_causas": pivot_causas,
        "reacao_df": reacao_df,
        "meteo_strat": meteo_strat,
        "pista_strat": pista_strat,
        "evidencias_texto": evidencias_texto,
        "hipotese_texto": hipotese_texto,
        "limitacoes_texto": limitacoes_texto,
        "referencia_fhwa": "FHWA Proven Safety Countermeasures: Lighting (U.S. DOT)",
    }


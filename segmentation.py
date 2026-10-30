"""
Módulo de Segmentação Geográfica e Classificação de Trechos Críticos.
Agrupa acidentes em segmentos contínuos regulares de extensão definida (ex: 2.0 km),
elimina distorções de KM 0.0 e separa ranking geral do ranking para iluminação solar.
"""

from typing import Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
from config import DEFAULT_COMPRIMENTO_TRECHO_KM


def create_road_segments(
    ocorrencias_df: pd.DataFrame,
    comprimento_km: float = DEFAULT_COMPRIMENTO_TRECHO_KM,
    apenas_noturnos_para_prioridade: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Agrupa acidentes válidos em segmentos regulares de extensão 'comprimento_km'
    (ex: [0, 2), [2, 4), etc.) por Rodovia (BR) e Estado (UF).
    
    Registros com KM ausente ou inválido são contabilizados separadamente
    e NÃO são atribuídos erroneamente ao KM 0.0.
    """
    if ocorrencias_df.empty:
        return pd.DataFrame(), {}

    total_acidentes_base = len(ocorrencias_df)

    # Filtrar apenas registros com localização viária consistente (BR, UF e KM válidos)
    mask_com_km = ocorrencias_df["km"].notna() & ocorrencias_df["uf"].notna() & (ocorrencias_df["br"] != "N/A")
    valid_df = ocorrencias_df[mask_com_km].copy()
    sem_km_count = int((~mask_com_km).sum())

    if valid_df.empty:
        return pd.DataFrame(), {
            "total_acidentes": total_acidentes_base,
            "acidentes_com_km": 0,
            "acidentes_sem_km": sem_km_count,
            "total_segmentos": 0,
        }

    # Criar intervalo de KM regular
    # Exemplo: se comprimento_km = 2.0, km 3.4 cai no intervalo km_inicio = 2.0, km_fim = 4.0
    valid_df["km_inicio"] = np.floor(valid_df["km"] / comprimento_km) * comprimento_km
    valid_df["km_fim"] = valid_df["km_inicio"] + comprimento_km

    # Identificador legível do trecho: BR-101 (SC) KM 144.0 - 146.0
    valid_df["trecho_id"] = (
        "BR-" + valid_df["br"].astype(str) + " (" + valid_df["uf"].astype(str) + ") " +
        "KM " + valid_df["km_inicio"].map(lambda x: f"{x:.1f}") + " - " +
        valid_df["km_fim"].map(lambda x: f"{x:.1f}")
    )

    # Coordenadas médias do segmento (apenas com coordenadas válidas)
    valid_df["has_geo"] = valid_df["latitude"].notna() & valid_df["longitude"].notna()

    # Período noturno
    is_noturno = (valid_df["fase_dia_agrupada"] == "Noturno") if "fase_dia_agrupada" in valid_df.columns else (valid_df["fase_dia"] == "noturno")
    valid_df["is_noturno"] = is_noturno.astype(int)
    valid_df["_mortos_not"] = valid_df["mortos"] * valid_df["is_noturno"]
    valid_df["_graves_not"] = valid_df["feridos_graves"] * valid_df["is_noturno"]
    valid_df["_leves_not"] = valid_df["feridos_leves"] * valid_df["is_noturno"]
    valid_df["_feridos_not"] = valid_df["total_feridos"] * valid_df["is_noturno"]
    valid_df["_vitimas_not"] = valid_df["total_vitimas"] * valid_df["is_noturno"]
    valid_df["_fatais_not"] = valid_df["acidente_fatal"] * valid_df["is_noturno"]

    # Agregação por segmento (vetorizada de alta performance)
    segmentos = (
        valid_df.groupby(["trecho_id", "br", "uf", "km_inicio", "km_fim"], observed=True)
        .agg(
            n_acidentes_total=("id", "count"),
            n_acidentes_noturnos=("is_noturno", "sum"),
            mortos_total=("mortos", "sum"),
            mortos_noturno=("_mortos_not", "sum"),
            feridos_graves_total=("feridos_graves", "sum"),
            feridos_graves_noturno=("_graves_not", "sum"),
            feridos_leves_total=("feridos_leves", "sum"),
            feridos_leves_noturno=("_leves_not", "sum"),
            total_feridos_noturno=("_feridos_not", "sum"),
            total_vitimas_noturno=("_vitimas_not", "sum"),
            acidentes_fatais_noturno=("_fatais_not", "sum"),
            latitude_media=("latitude", "mean"),
            longitude_media=("longitude", "mean"),
            registros_com_geo=("has_geo", "sum"),
        )
        .reset_index()
    )

    # Percentual noturno
    segmentos["perc_noturno"] = (
        segmentos["n_acidentes_noturnos"] / segmentos["n_acidentes_total"].replace(0, np.nan) * 100
    ).fillna(0)

    # Confiabilidade da geolocalização do trecho
    segmentos["confiabilidade_geo"] = np.where(
        segmentos["registros_com_geo"] == segmentos["n_acidentes_total"],
        "Alta (100% coordenadas)",
        np.where(
            segmentos["registros_com_geo"] > 0,
            "Parcial (" + (segmentos["registros_com_geo"] / segmentos["n_acidentes_total"] * 100).round(0).astype(str) + "%)",
            "Apenas Marco Quilométrico (Sem Lat/Lon)"
        )
    )

    # Score de Gravidade Geral: 5 * mortos + 3 * graves + 1 * leves
    segmentos["score_gravidade_geral"] = (
        segmentos["mortos_total"] * 5 +
        segmentos["feridos_graves_total"] * 3 +
        segmentos["feridos_leves_total"] * 1
    )

    # Score de Prioridade para Iluminação Solar:
    # Focado no período NOTURNO: severidade noturna ponderada pela concentração noturna
    segmentos["score_iluminacao_solar"] = (
        (segmentos["mortos_noturno"] * 5 +
         segmentos["feridos_graves_noturno"] * 3 +
         segmentos["feridos_leves_noturno"] * 1 +
         segmentos["n_acidentes_noturnos"] * 2) *
        (1 + (segmentos["perc_noturno"] / 100))
    ).round(1)

    # Score legível / justificativa
    segmentos["justificativa_prioridade"] = (
        segmentos["n_acidentes_noturnos"].astype(str) + " acid. noturnos | " +
        segmentos["mortos_noturno"].astype(str) + " óbitos | " +
        segmentos["perc_noturno"].round(1).astype(str) + "% noturno"
    )

    # Metadados de segmentação
    info_segmentacao = {
        "total_acidentes_base": total_acidentes_base,
        "acidentes_com_km_validos": len(valid_df),
        "acidentes_sem_km_descartados_do_ranking": sem_km_count,
        "perc_acidentes_com_km": (len(valid_df) / total_acidentes_base * 100) if total_acidentes_base > 0 else 0.0,
        "comprimento_segmento_km": comprimento_km,
        "total_segmentos_gerados": len(segmentos),
    }

    return segmentos, info_segmentacao


def rank_segments(
    segmentos_df: pd.DataFrame,
    top_n: int = 100,
    criterio: str = "iluminacao_solar"
) -> pd.DataFrame:
    """
    Ordena e extrai o Top N trechos de acordo com o critério escolhido:
    - 'iluminacao_solar': Foco em severidade e concentração de acidentes noturnos
    - 'geral': Foco no total de acidentes e gravidade 24h
    """
    if segmentos_df.empty:
        return pd.DataFrame()

    col_sort = "score_iluminacao_solar" if criterio == "iluminacao_solar" else "score_gravidade_geral"
    ranked = segmentos_df.sort_values(col_sort, ascending=False).reset_index(drop=True)
    ranked["ranking"] = np.arange(1, len(ranked) + 1)
    return ranked.head(top_n).copy()


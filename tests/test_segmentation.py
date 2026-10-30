"""
Testes automatizados para o módulo de segmentação de trechos e ranking.
"""

import pytest
import pandas as pd
import numpy as np
from segmentation import create_road_segments, rank_segments


def test_create_road_segments_regular_intervals():
    # Testa agrupamento em segmentos regulares de 2 km
    # KM 144.2 e KM 145.8 caem no trecho [144.0 - 146.0]
    # KM 147.1 cai no trecho [146.0 - 148.0]
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "br": ["101", "101", "101"],
        "uf": ["SC", "SC", "SC"],
        "km": [144.2, 145.8, 147.1],
        "latitude": [-27.08, -27.09, -27.10],
        "longitude": [-48.60, -48.61, -48.62],
        "fase_dia_agrupada": ["Noturno", "Noturno", "Diurno"],
        "mortos": [1, 0, 0],
        "feridos_graves": [0, 1, 0],
        "feridos_leves": [1, 1, 2],
        "total_feridos": [1, 2, 2],
        "total_vitimas": [2, 2, 2],
        "acidente_fatal": [1, 0, 0],
    })

    segmentos, info = create_road_segments(df, comprimento_km=2.0)
    assert len(segmentos) == 2
    assert info["acidentes_com_km_validos"] == 3
    assert info["acidentes_sem_km_descartados_do_ranking"] == 0

    trecho_144 = segmentos[segmentos["km_inicio"] == 144.0].iloc[0]
    assert trecho_144["n_acidentes_total"] == 2
    assert trecho_144["n_acidentes_noturnos"] == 2
    assert trecho_144["mortos_noturno"] == 1


def test_missing_km_not_assigned_to_zero():
    # Registros com KM nulo NÃO podem ser somados ao KM 0.0
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "br": ["101", "101", "101"],
        "uf": ["SC", "SC", "SC"],
        "km": [np.nan, None, 0.0],  # 2 nulos e 1 legítimo KM 0.0
        "latitude": [-27.08, -27.09, -27.10],
        "longitude": [-48.60, -48.61, -48.62],
        "fase_dia_agrupada": ["Noturno", "Diurno", "Noturno"],
        "mortos": [2, 1, 0],
        "feridos_graves": [0, 0, 0],
        "feridos_leves": [0, 0, 0],
        "total_feridos": [0, 0, 0],
        "total_vitimas": [2, 1, 0],
        "acidente_fatal": [1, 1, 0],
    })

    segmentos, info = create_road_segments(df, comprimento_km=2.0)
    assert info["acidentes_sem_km_descartados_do_ranking"] == 2
    assert info["acidentes_com_km_validos"] == 1
    assert len(segmentos) == 1

    trecho_0 = segmentos.iloc[0]
    assert trecho_0["km_inicio"] == 0.0
    assert trecho_0["n_acidentes_total"] == 1  # Apenas o legítimo, não os 2 nulos!
    assert trecho_0["mortos_total"] == 0       # Não absorveu as 2 mortes com KM nulo!


def test_ranking_segments():
    df = pd.DataFrame({
        "trecho_id": ["T1", "T2"],
        "score_iluminacao_solar": [50.0, 10.0],
        "score_gravidade_geral": [20.0, 30.0],
    })

    ranked_solar = rank_segments(df, top_n=10, criterio="iluminacao_solar")
    assert ranked_solar.iloc[0]["trecho_id"] == "T1"

    ranked_geral = rank_segments(df, top_n=10, criterio="geral")
    assert ranked_geral.iloc[0]["trecho_id"] == "T2"


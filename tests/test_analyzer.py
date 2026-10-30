"""
Testes automatizados para a classe AccidentAnalyzer em analyzer.py.
"""

import pytest
import pandas as pd
import numpy as np
from analyzer import AccidentAnalyzer, calculate_roi


def test_calculate_roi_compatibility():
    roi, payback, invest, econ, evitados = calculate_roi(
        total_mortos=2,
        total_feridos_graves=4,
        total_feridos_leves=10,
        comprimento_trecho_km=2.0,
        spacing_m=50,
        anos_base=1.0,
    )
    # 2000m / 50m = 40 postes * 15000 = 600.000
    assert invest == 600_000.0
    assert econ > 0
    assert payback > 0
    assert isinstance(roi, float)
    assert evitados > 0


def test_analyzer_apply_filters():
    analyzer = AccidentAnalyzer()
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "ano": [2024, 2024, 2025, 2026],
        "uf": ["SC", "PR", "SC", "SP"],
        "br": ["101", "376", "101", "116"],
        "fase_dia_oficial": ["Plena Noite", "Pleno dia", "Plena Noite", "Anoitecer"],
        "fase_dia_agrupada": ["Noturno", "Diurno", "Noturno", "Crepúsculo"],
        "condicao_metereologica": ["Chuva", "Céu Claro", "Céu Claro", "Nublado"],
    })

    analyzer.data = df
    # Filtrar apenas SC
    f_sc = analyzer.apply_filters(df, {"ufs": ["SC"]})
    assert len(f_sc) == 2
    assert set(f_sc["uf"]) == {"SC"}

    # Filtrar Noturno
    f_not = analyzer.apply_filters(df, {"fase_dia": ["Noturno"]})
    assert len(f_not) == 2


def test_analyzer_top_n():
    analyzer = AccidentAnalyzer()
    df = pd.DataFrame({
        "id": range(1, 11),
        "br": ["101"] * 10,
        "uf": ["SC"] * 10,
        "km": [145.2, 145.5, 145.8, 147.0, 147.2, 200.1, 200.5, 300.0, 301.0, 302.0],
        "latitude": [-27.0] * 10,
        "longitude": [-48.0] * 10,
        "fase_dia_agrupada": ["Noturno"] * 10,
        "mortos": [1, 0, 1, 0, 0, 2, 0, 0, 0, 0],
        "feridos_graves": [1, 1, 0, 0, 1, 1, 0, 0, 0, 0],
        "feridos_leves": [1, 2, 1, 1, 0, 2, 1, 1, 0, 0],
        "total_feridos": [2, 3, 1, 1, 1, 3, 1, 1, 0, 0],
        "total_vitimas": [3, 3, 2, 1, 1, 5, 1, 1, 0, 0],
        "acidente_fatal": [1, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    })

    top_df, agregados = analyzer.analyze_top_n(
        df=df,
        top_n=5,
        comprimento_km=2.0,
        spacing_m=50,
        anos_base=1.0,
    )

    assert not top_df.empty
    assert "investimento_total" in agregados
    assert "vpl" in agregados
    assert "payback_simples_anos" in agregados
    assert agregados["investimento_total"] > 0


def test_elegibilidade_ocorrencias_nacionais_vs_segmentadas():
    """
    Testa a regra de elegibilidade:
    - Ocorrências sem KM (br='N/A') são elegíveis para estatísticas nacionais e mantidas no filtro padrão;
    - Apenas na segmentação viária (analyze_top_n) elas são isoladas para não concentrar no KM 0.0.
    """
    analyzer = AccidentAnalyzer()
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],  # id 4 é sem KM e br='N/A'
        "ano": [2025, 2025, 2026, 2026],
        "uf": ["SC", "PR", "SP", "RJ"],
        "br": ["101", "376", "116", "N/A"],
        "km": [145.2, 50.0, 220.0, np.nan],
        "latitude": [-27.0, -25.5, -23.5, -22.9],
        "longitude": [-48.0, -49.2, -46.6, -43.2],
        "fase_dia_agrupada": ["Noturno", "Diurno", "Noturno", "Noturno"],
        "fase_dia_oficial": ["Plena Noite", "Pleno dia", "Plena Noite", "Plena Noite"],
        "mortos": [1, 0, 0, 0],
        "feridos_graves": [1, 0, 1, 1],
        "feridos_leves": [0, 1, 2, 0],
        "total_feridos": [1, 1, 3, 1],
        "total_vitimas": [2, 1, 3, 1],
        "acidente_fatal": [1, 0, 0, 0],
    })
    analyzer.data = df.copy()

    # Filtro padrão com todas as BRs nominais
    filtros_padrao = {
        "brs": ["101", "376", "116"],  # Todas as BRs conhecidas selecionadas
    }
    filtered = analyzer.apply_filters(df, filtros_padrao)

    # Todas as 4 ocorrências devem ser mantidas na análise geral
    assert len(filtered) == 4
    assert 4 in filtered["id"].values

    # Na segmentação viária, a ocorrência sem KM é excluída dos trechos
    top_df, agregados = analyzer.analyze_top_n(
        df=filtered,
        top_n=5,
        comprimento_km=2.0,
        spacing_m=50,
        anos_base=2.0,
    )
    # Apenas os 3 sinistros com KM válido participam dos trechos
    assert not top_df.empty
    # Nenhum trecho deve ter KM nulo ou 'N/A'
    assert not any("N/A" in str(tid) for tid in top_df["trecho_id"])



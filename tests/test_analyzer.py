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


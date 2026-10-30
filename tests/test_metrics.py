"""
Testes automatizados para o módulo de métricas estatísticas e comparação Dia vs Noite.
"""

import pytest
import pandas as pd
import numpy as np
from metrics import compute_period_metrics, compute_day_vs_night_comparison


def test_compute_period_metrics():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "fase_dia_oficial": ["Pleno dia", "Pleno dia", "Plena Noite", "Plena Noite"],
        "mortos": [0, 1, 2, 0],
        "feridos_graves": [1, 0, 1, 1],
        "feridos_leves": [2, 0, 0, 1],
        "total_feridos": [3, 0, 1, 2],
        "total_vitimas": [3, 1, 3, 2],
        "acidente_fatal": [0, 1, 1, 0],
    })

    res = compute_period_metrics(df, period_col="fase_dia_oficial")
    assert len(res) == 2

    dia = res[res["fase_dia_oficial"] == "Pleno dia"].iloc[0]
    noite = res[res["fase_dia_oficial"] == "Plena Noite"].iloc[0]

    assert dia["n_acidentes"] == 2
    assert dia["total_mortos"] == 1
    assert dia["acidentes_fatais"] == 1
    assert dia["prop_acidentes_fatais_pct"] == 50.0
    assert dia["mortos_por_100_acidentes"] == 50.0

    assert noite["n_acidentes"] == 2
    assert noite["total_mortos"] == 2
    assert noite["acidentes_fatais"] == 1
    assert noite["mortos_por_100_acidentes"] == 100.0


def test_compute_day_vs_night_comparison():
    df = pd.DataFrame({
        "id": range(10),
        "fase_dia_agrupada": ["Diurno"] * 6 + ["Noturno"] * 4,
        "mortos": [0, 0, 0, 1, 0, 0] + [1, 1, 0, 0],  # 1 morto em 6 de dia (1/6 = 0.167), 2 mortos em 4 à noite (2/4 = 0.5)
        "total_feridos": [1] * 10,
        "total_vitimas": [1, 1, 1, 2, 1, 1, 2, 2, 1, 1],
        "acidente_fatal": [0, 0, 0, 1, 0, 0, 1, 1, 0, 0],
    })

    comp = compute_day_vs_night_comparison(df)
    assert comp["total_acidentes"] == 10
    assert comp["total_mortos"] == 3
    assert comp["noturno"]["n_acidentes"] == 4
    assert comp["diurno"]["n_acidentes"] == 6

    # Razão de letalidade: (2/4) / (1/6) = 0.5 / 0.1667 = 3.0
    assert pytest.approx(comp["razao_letalidade_obitos"], 0.01) == 3.0


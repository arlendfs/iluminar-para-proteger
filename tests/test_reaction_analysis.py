"""
Testes automatizados para o módulo de visibilidade e tempo de reação.
"""

import pytest
import pandas as pd
from reaction_analysis import filter_reaction_causes, analyze_visibility_and_reaction


def test_filter_reaction_causes():
    causes_df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "causa_acidente": [
            "Reação tardia ou ineficiente do condutor",
            "Defeito mecânico no veículo",
            "Condutor Dormindo",
            "Furo no pneu",
        ]
    })

    filtered = filter_reaction_causes(causes_df)
    assert len(filtered) == 2
    assert "Reação tardia ou ineficiente do condutor" in filtered["causa_acidente"].values
    assert "Condutor Dormindo" in filtered["causa_acidente"].values


def test_analyze_visibility_and_reaction():
    ocorrencias = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "fase_dia_agrupada": ["Noturno", "Noturno", "Diurno", "Diurno"],
        "mortos": [1, 0, 0, 0],
        "total_feridos": [1, 2, 0, 1],
        "total_vitimas": [2, 2, 0, 1],
        "acidente_fatal": [1, 0, 0, 0],
        "condicao_metereologica": ["Chuva", "Céu Claro", "Céu Claro", "Nublado"],
        "tipo_pista": ["Dupla", "Simples", "Simples", "Dupla"],
    })

    causas = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "causa_acidente": [
            "Reação tardia ou ineficiente do condutor",
            "Ausência de reação do condutor",
            "Reação tardia ou ineficiente do condutor",
            "Velocidade Incompatível",
        ]
    })

    res = analyze_visibility_and_reaction(ocorrencias, causas)
    assert "ranking_causas" in res
    assert "pivot_causas" in res
    assert not res["ranking_causas"].empty
    assert "evidencias_texto" in res
    assert "hipotese_texto" in res
    assert "limitacoes_texto" in res


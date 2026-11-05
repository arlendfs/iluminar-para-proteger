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
    assert "causas_fases_df" in res
    assert not res["ranking_causas"].empty
    assert "evidencias_texto" in res
    assert "hipotese_texto" in res
    assert "limitacoes_texto" in res


def test_multiple_causes_overlap_and_distinct_counts():
    """
    Verifica que causas múltiplas para o mesmo acidente:
    1. São contadas como ocorrências distintas por categoria de causa;
    2. Não duplicam mortos dentro da mesma categoria;
    3. Permitem sobreposição entre categorias distintas.
    """
    # 1 acidente (id=10) com 2 causas e 1 morto
    ocorrencias = pd.DataFrame({
        "id": [10],
        "fase_dia_oficial": ["Plena Noite"],
        "fase_dia_agrupada": ["Noturno"],
        "mortos": [1],
        "total_feridos": [0],
        "total_vitimas": [1],
        "acidente_fatal": [1],
    })

    causas = pd.DataFrame({
        "id": [10, 10],
        "causa_acidente": [
            "Reação tardia ou ineficiente do condutor",
            "Ausência de reação do condutor",
        ],
    })

    res = analyze_visibility_and_reaction(ocorrencias, causas)
    ranking = res["ranking_causas"]
    assert len(ranking) == 2
    # Cada causa lista 1 ocorrência e 1 morto
    assert ranking[ranking["causa_normalizada"] == "Reação tardia ou ineficiente do condutor"]["total_ocorrencias"].iloc[0] == 1
    assert ranking[ranking["causa_normalizada"] == "Ausência de reação do condutor"]["total_ocorrencias"].iloc[0] == 1
    # Óbitos por 100 acidentes nesta causa é 100.0
    assert ranking[ranking["causa_normalizada"] == "Reação tardia ou ineficiente do condutor"]["obitos_por_100"].iloc[0] == 100.0


def test_analyze_visibility_and_reaction_with_categorical_columns():
    """
    Garante que colunas com tipo category (ex.: fase_dia_agrupada, fase_dia_oficial)
    não quebram divisões aritméticas no Pandas.
    """
    ocorrencias = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "fase_dia_agrupada": pd.Categorical(["Noturno", "Noturno", "Diurno", "Diurno"]),
        "fase_dia_oficial": pd.Categorical(["Plena Noite", "Plena Noite", "Pleno Dia", "Pleno Dia"]),
        "mortos": [1, 0, 0, 0],
        "total_feridos": [1, 2, 0, 1],
        "total_vitimas": [2, 2, 0, 1],
        "acidente_fatal": [1, 0, 0, 0],
        "condicao_metereologica": pd.Categorical(["Chuva", "Céu Claro", "Céu Claro", "Nublado"]),
        "tipo_pista": pd.Categorical(["Dupla", "Simples", "Simples", "Dupla"]),
    })

    causas = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "causa_acidente": pd.Categorical([
            "Reação tardia ou ineficiente do condutor",
            "Ausência de reação do condutor",
            "Reação tardia ou ineficiente do condutor",
            "Velocidade Incompatível",
        ]),
    })

    res = analyze_visibility_and_reaction(ocorrencias, causas)
    assert "ranking_causas" in res
    assert "causas_periodo" in res
    assert "causas_fases_df" in res
    assert not res["causas_periodo"].empty
    # Verificar que participacao_no_periodo_pct é numérico e calculado
    assert pd.api.types.is_numeric_dtype(res["causas_periodo"]["participacao_no_periodo_pct"])
    assert pd.api.types.is_numeric_dtype(res["ranking_causas"]["letalidade_pct"])
    assert pd.api.types.is_numeric_dtype(res["causas_fases_df"]["mortos_por_100"])


def test_report_summary_matches_full_analysis_for_displayed_causes():
    occurrences = pd.DataFrame({
        "id": [1, 2, 3],
        "fase_dia_oficial": ["Plena Noite", "Pleno Dia", "Plena Noite"],
        "fase_dia_agrupada": ["Noturno", "Diurno", "Noturno"],
        "mortos": [1, 0, 0],
        "total_feridos": [0, 1, 0],
        "acidente_fatal": [1, 0, 0],
    })
    causes = pd.DataFrame({
        "id": [1, 2, 3, 3],
        "causa_acidente": [
            "Reação tardia ou ineficiente do condutor",
            "Ausência de reação do condutor",
            "Condutor Dormindo",
            "Defeito mecânico no veículo",
        ],
    })
    full = analyze_visibility_and_reaction(occurrences, causes)
    report = analyze_visibility_and_reaction(occurrences, causes, include_details=False)

    expected = full["causas_fases_df"].query("causa_normalizada != 'Defeito mecânico no veículo'")
    pd.testing.assert_frame_equal(
        report["causas_fases_df"].sort_values(["causa_normalizada", "fase_dia_oficial"]).reset_index(drop=True),
        expected.sort_values(["causa_normalizada", "fase_dia_oficial"]).reset_index(drop=True),
    )
    assert report["resumo_reacao_dinamico"] == full["resumo_reacao_dinamico"]
    assert report["ranking_causas"].empty




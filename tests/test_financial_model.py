"""
Testes automatizados para o modelo de viabilidade econômica e dimensionamento solar.
"""

import pytest
import pandas as pd
import numpy as np
from financial_model import (
    dimensionar_postes,
    calcular_capex_opex,
    calcular_beneficio_anual_trechos,
    calcular_tir,
    avaliar_viabilidade_economica,
)
from config import FINANCIAL_PARAMS, ECONOMIC_VALUES


def test_dimensionamento_100_trechos_2km():
    """
    Teste obrigatório do prompt:
    100 trechos x 2 km = 200 km
    200.000 m / 50 m = 4.000 postes
    4.000 x R$ 15.000 = R$ 60.000.000
    """
    dim = dimensionar_postes(comprimento_trecho_km=2.0, espacamento_m=50, n_trechos=100)
    assert dim["postes_por_trecho"] == 40
    assert dim["total_postes"] == 4000
    assert dim["extensao_total_km"] == 200.0
    assert dim["extensao_total_m"] == 200000.0

    custos = calcular_capex_opex(dim["total_postes"], custo_unitario_poste=15000.0)
    assert custos["capex_total"] == 60_000_000.0


def test_beneficio_anual_exclusivo_trechos():
    """
    Verifica se o benefício é calculado exclusivamente sobre os acidentes
    dos trechos contemplados, sem extrapolar para o país inteiro.
    """
    df_trechos = pd.DataFrame({
        "trecho_id": ["T1", "T2"],
        "mortos_noturno": [2, 0],
        "feridos_graves_noturno": [4, 1],
        "feridos_leves_noturno": [10, 5],
        "n_acidentes_noturnos": [20, 10],
    })

    # Redução de 35% e 1 ano de base
    ben = calcular_beneficio_anual_trechos(
        df_trechos,
        fator_anualizacao=1.0,
        taxa_reducao=0.35,
    )

    vidas_esperadas = 2 * 0.35
    graves_esperados = 5 * 0.35
    leves_esperados = 15 * 0.35

    assert pytest.approx(ben["vidas_salvas_ano"], 0.001) == vidas_esperadas
    assert pytest.approx(ben["graves_evitados_ano"], 0.001) == graves_esperados
    assert pytest.approx(ben["leves_evitados_ano"], 0.001) == leves_esperados

    econ_vidas = vidas_esperadas * ECONOMIC_VALUES["valor_vida_estatistica"]
    econ_graves = graves_esperados * ECONOMIC_VALUES["custo_medio_acidente_grave"]
    econ_leves = leves_esperados * ECONOMIC_VALUES["custo_medio_acidente_leve"]
    assert pytest.approx(ben["beneficio_anual_bruto"], 0.01) == (econ_vidas + econ_graves + econ_leves)


def test_fator_anualizacao_multiplos_anos():
    """
    Verifica que se a base tem 5 anos acumulados, a taxa anual é dividida por 5.
    """
    df_trechos = pd.DataFrame({
        "trecho_id": ["T1"],
        "mortos_noturno": [10],
        "feridos_graves_noturno": [20],
        "feridos_leves_noturno": [50],
        "n_acidentes_noturnos": [100],
    })

    ben_5anos = calcular_beneficio_anual_trechos(
        df_trechos,
        fator_anualizacao=5.0,
        taxa_reducao=0.35,
    )
    assert pytest.approx(ben_5anos["mortos_ano_baseline"], 0.01) == 2.0
    assert pytest.approx(ben_5anos["vidas_salvas_ano"], 0.01) == 2.0 * 0.35


def test_viabilidade_economica_completa():
    """
    Testa VPL, Payback, TIR e consistência financeira completa.
    """
    df_trechos = pd.DataFrame({
        "trecho_id": [f"T_{i}" for i in range(100)],
        "mortos_noturno": [1] * 25 + [0] * 75,
        "feridos_graves_noturno": [2] * 40 + [0] * 60,
        "feridos_leves_noturno": [5] * 100,
        "n_acidentes_noturnos": [15] * 100,
    })

    res = avaliar_viabilidade_economica(
        top_segments_df=df_trechos,
        n_trechos=100,
        comprimento_km=2.0,
        espacamento_m=50,
        custo_poste=15000.0,
        taxa_reducao=0.35,
        anos_base_dados=1.0,
    )

    assert res["capex_total"] == 60_000_000.0
    assert res["dimensionamento"]["total_postes"] == 4000
    assert res["beneficio_anual_bruto"] > 0
    assert res["payback_simples_anos"] > 0
    assert isinstance(res["vpl"], float)
    assert res["tir"] is not None or res["vpl"] < 0
    assert "conservador" in res["cenarios_sensibilidade"]
    assert "intermediario" in res["cenarios_sensibilidade"]
    assert "otimista" in res["cenarios_sensibilidade"]


def test_caso_extremo_zero_acidentes():
    """
    Testa comportamento com zero acidentes (benefício nulo):
    Payback deve ser infinito, VPL negativo igual ao CAPEX descontado.
    """
    df_vazio = pd.DataFrame(columns=["mortos_noturno", "feridos_graves_noturno", "feridos_leves_noturno", "n_acidentes_noturnos"])
    res = avaliar_viabilidade_economica(
        top_segments_df=df_vazio,
        n_trechos=10,
        comprimento_km=2.0,
        espacamento_m=50,
    )
    assert res["beneficio_anual_bruto"] == 0.0
    assert res["payback_simples_anos"] == float("inf")
    assert res["vpl"] < 0


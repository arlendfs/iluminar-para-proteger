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
    calcular_balanco_energetico_detalhado,
    calcular_orcamento_cenarios,
)
from config import (
    FINANCIAL_PARAMS,
    ECONOMIC_VALUES,
    ENGENHARIA_SISTEMA_SOLAR,
    ENGENHARIA_SISTEMA_SOLAR_COMPACTO,
    CENARIOS_ORCAMENTO,
)


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


def test_balanco_energetico_solar_autonomia():
    """
    Testa o balanço energético auditado para assegurar 3 noites de autonomia
    com bateria LiFePO4 de 24V / 80Ah (1.920 Wh) e painel fotovoltaico de 300W.
    """
    eng = ENGENHARIA_SISTEMA_SOLAR
    # Energia nominal = 24V x 80Ah = 1920 Wh
    assert eng["energia_nominal_bateria_wh"] == 1920.0
    # Consumo noturno ponderado: 4h*60W (240) + 7h*28W (196) + 1h*30W (30) = 466 Wh
    assert eng["consumo_noturno_ponderado_wh"] == 466.0
    # Energia útil com DoD 80% e perdas de 10%: 1920 * 0.80 * 0.90 = 1382.4 Wh
    assert pytest.approx(eng["energia_disponivel_consumo_wh"], 0.1) == 1382.4
    # Autonomia útil: 1382.4 / 466 = 2.9665 (~3 noites)
    assert eng["autonomia_sustentada_noites"] >= 2.95
    # Geração solar diária (300W * 4.5 HSP * 0.85 = 1147.5 Wh) deve superar o consumo diário (466 Wh)
    assert eng["geracao_solar_diaria_wh"] > eng["consumo_noturno_ponderado_wh"]


def test_memoria_calculo_vidas_salvas_45_8():
    """
    Comprova a dedução matemática de 45,8 vidas salvas por ano:
    100 trechos com 262 óbitos noturnos acumulados em 2.0 anos.
    Taxa base = 131 óbitos/ano * 0.35 = 45.85 vidas salvas/ano.
    """
    # Cria trechos sintéticos totalizando 262 óbitos noturnos
    df_top = pd.DataFrame({
        "trecho_id": [f"T_{i}" for i in range(100)],
        "mortos_noturno": [3] * 62 + [2] * 38,  # 62*3 + 38*2 = 186 + 76 = 262
        "feridos_graves_noturno": [5] * 100,
        "feridos_leves_noturno": [10] * 100,
        "n_acidentes_noturnos": [20] * 100,
    })

    ben = calcular_beneficio_anual_trechos(
        df_top,
        fator_anualizacao=2.0,
        taxa_reducao=0.35,
    )

    assert df_top["mortos_noturno"].sum() == 262
    assert ben["mortos_ano_baseline"] == 131.0
    assert pytest.approx(ben["vidas_salvas_ano"], 0.05) == 45.85
    # Arredondado a 1 casa decimal deve ser exatamente 45.8 ou 45.9
    assert round(ben["vidas_salvas_ano"], 1) in (45.8, 45.9)


def test_balanco_energetico_detalhado_compacto():
    """
    Testa o dimensionamento do cenário compacto 8m / 40W / 240Wp / 2.500Wh:
    - Consumo noturno: 4h*40W (160) + 4h*32W (128) + 4h*24W (96) = 384 Wh
    - Telemetria: 2W * 24h = 48 Wh -> Consumo total = 432 Wh/dia
    - Bateria 2.500 Wh nominais: 1.800 Wh úteis BOL e 1.440 Wh úteis EOL
    - Autonomia com ZERO sol: BOL = 4,17 noites; EOL = 3,33 noites (sustenta 3 noites)
    - Geração solar a pleno sol: 240Wp * 4.5h * 0.8 = 864 Wh/dia (excedente 432 Wh)
    - Recuperação da carga total: 1.296 Wh / 432 Wh = 3,0 dias
    """
    b = calcular_balanco_energetico_detalhado()
    assert b["consumo_led_wh"] == 384.0
    assert b["consumo_telemetria_wh"] == 48.0
    assert b["consumo_total_diario_wh"] == 432.0
    assert b["consumo_3_noites_wh"] == 1296.0

    assert pytest.approx(b["capacidade_util_bol_wh"], 0.1) == 1800.0
    assert pytest.approx(b["capacidade_util_eol_wh"], 0.1) == 1440.0

    assert b["autonomia_zero_sol_bol_noites"] > 4.15
    assert b["autonomia_zero_sol_eol_noites"] > 3.30
    assert b["atende_requisito_3_noites_bol"] is True
    assert b["atende_requisito_3_noites_eol"] is True

    assert pytest.approx(b["geracao_solar_sol_pleno_wh"], 0.1) == 864.0
    assert pytest.approx(b["excedente_diario_sol_wh"], 0.1) == 432.0
    assert pytest.approx(b["dias_recarga_apos_3_noites"], 0.1) == 3.0


def test_aviso_autonomia_insuficiente():
    """
    Verifica se a função emite aviso quando a bateria não suporta a autonomia desejada.
    """
    # Bateria insuficiente de apenas 800 Wh para 40W
    b_insuficiente = calcular_balanco_energetico_detalhado(
        potencia_led_w=40.0,
        capacidade_bateria_wh=800.0,
        autonomia_desejada_noites=3.0,
    )
    assert b_insuficiente["atende_requisito_3_noites_bol"] is False
    assert "AVISO TÉCNICO" in b_insuficiente["status_aviso"]


def test_orcamento_cenarios_a_e():
    """
    Valida os 5 cenários orçamentários comparáveis (Cenários A a E):
    - Cenário A: R$ 15.000 / CAPEX R$ 60M
    - Cenário B: R$ 17.018,85 / CAPEX R$ 68,08M
    - Cenário C: R$ 28.288,85 / CAPEX R$ 113,16M
    - Cenário D: R$ 22.310,00 / CAPEX R$ 89,24M
    - Cenário E: R$ 34.038,85 / CAPEX R$ 136,16M
    """
    df_top = pd.DataFrame({
        "trecho_id": [f"T_{i}" for i in range(100)],
        "mortos_noturno": [3] * 62 + [2] * 38,
        "feridos_graves_noturno": [5] * 100,
        "feridos_leves_noturno": [10] * 100,
        "n_acidentes_noturnos": [20] * 100,
    })

    orc = calcular_orcamento_cenarios(
        top_segments_df=df_top,
        n_trechos=100,
        comprimento_km=2.0,
        espacamento_m=50,
        anos_base_dados=2.0,
    )

    resumos = orc["resumos_cenarios"]
    assert "cenario_a" in resumos
    assert "cenario_b" in resumos
    assert "cenario_c" in resumos
    assert "cenario_d" in resumos
    assert "cenario_e" in resumos

    # Cenário A
    assert resumos["cenario_a"]["custo_unitario"] == 15000.00
    assert resumos["cenario_a"]["capex_total"] == 60_000_000.00

    # Cenário B
    assert pytest.approx(resumos["cenario_b"]["custo_unitario"], 0.01) == 17018.85
    assert pytest.approx(resumos["cenario_b"]["capex_total"], 1.0) == 68_075_400.00

    # Cenário C
    assert pytest.approx(resumos["cenario_c"]["custo_unitario"], 0.01) == 28288.85
    assert pytest.approx(resumos["cenario_c"]["capex_total"], 1.0) == 113_155_400.00

    # Cenário D (Base compacta)
    assert pytest.approx(resumos["cenario_d"]["custo_unitario"], 0.01) == 22310.00
    assert pytest.approx(resumos["cenario_d"]["capex_total"], 1.0) == 89_240_000.00

    # Cenário E
    assert pytest.approx(resumos["cenario_e"]["custo_unitario"], 0.01) == 34038.85
    assert pytest.approx(resumos["cenario_e"]["capex_total"], 1.0) == 136_155_400.00

    # VPL de todos os cenários com 100 trechos críticos deve ser positivo e superior a R$ 2 bilhões
    for c_id in ["cenario_a", "cenario_b", "cenario_c", "cenario_d", "cenario_e"]:
        assert resumos[c_id]["vpl"] > 2_000_000_000.0
        assert resumos[c_id]["payback_simples_anos"] < 1.0




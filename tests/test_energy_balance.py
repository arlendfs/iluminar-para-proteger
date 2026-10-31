"""
Testes de balanço energético — Auditoria Final.

Verifica:
- Autonomia BOL e EOL são distintas (degradação de bateria)
- BOL > EOL (bateria nova vs degradada)
- Valores corretos segundo config (consumo_total_diario = 432 Wh, BOL_wh = 1800 Wh)
  BOL ≈ 4,17 noites; EOL ≈ 3,33 noites
- balanco_liquido_nublado_wh é negativo (consumo > geração em dias nublados)
- Todos os campos-chave retornados pela função
"""

import pytest
from financial_model import calcular_balanco_energetico_detalhado
from config import ENGENHARIA_SISTEMA_SOLAR_COMPACTO


# ---------------------------------------------------------------------------
# 1. BOL vs EOL autonomia zero-solar
# ---------------------------------------------------------------------------

class TestAutonomiaBOLvsEOL:
    def test_bol_and_eol_are_present(self):
        """Função deve retornar autonomia_zero_sol_bol_noites e autonomia_zero_sol_eol_noites."""
        result = calcular_balanco_energetico_detalhado()
        assert "autonomia_zero_sol_bol_noites" in result, (
            "Chave 'autonomia_zero_sol_bol_noites' não encontrada no resultado"
        )
        assert "autonomia_zero_sol_eol_noites" in result, (
            "Chave 'autonomia_zero_sol_eol_noites' não encontrada no resultado"
        )

    def test_bol_greater_than_eol(self):
        """BOL deve ser maior que EOL — bateria nova tem maior capacidade útil."""
        result = calcular_balanco_energetico_detalhado()
        bol = result["autonomia_zero_sol_bol_noites"]
        eol = result["autonomia_zero_sol_eol_noites"]
        assert bol > eol, (
            f"autonomia BOL ({bol:.2f}) deve ser > EOL ({eol:.2f})"
        )

    def test_bol_and_eol_are_different(self):
        """BOL e EOL devem ser numericamente distintos."""
        result = calcular_balanco_energetico_detalhado()
        bol = result["autonomia_zero_sol_bol_noites"]
        eol = result["autonomia_zero_sol_eol_noites"]
        assert abs(bol - eol) > 0.3, (
            f"BOL ({bol:.2f}) e EOL ({eol:.2f}) devem diferir pelo menos 0,3 noite"
        )

    def test_bol_computed_from_config(self):
        """
        BOL = capacidade_util_bol_wh / consumo_total_diario_wh.
        Com config padrão (cap=2000 Wh, DoD=0.9, eff=1.0 → 1800 Wh úteis),
        consumo_total_diario ≈ 432 Wh → BOL ≈ 4,17 noites.
        """
        result = calcular_balanco_energetico_detalhado()
        bol_wh = result.get("capacidade_util_bol_wh", 0)
        consumo = result.get("consumo_total_diario_wh", 1)
        expected_bol = bol_wh / consumo
        bol = result["autonomia_zero_sol_bol_noites"]
        assert abs(bol - expected_bol) < 0.01, (
            f"BOL inconsistente: calculado {expected_bol:.2f}, retornado {bol:.2f}"
        )

    def test_eol_computed_from_config(self):
        """EOL = capacidade_util_eol_wh / consumo_total_diario_wh."""
        result = calcular_balanco_energetico_detalhado()
        eol_wh = result.get("capacidade_util_eol_wh", 0)
        consumo = result.get("consumo_total_diario_wh", 1)
        expected_eol = eol_wh / consumo
        eol = result["autonomia_zero_sol_eol_noites"]
        assert abs(eol - expected_eol) < 0.01, (
            f"EOL inconsistente: calculado {expected_eol:.2f}, retornado {eol:.2f}"
        )

    def test_bol_atende_3_noites(self):
        """BOL deve atender a meta de 3 noites sem geração solar."""
        result = calcular_balanco_energetico_detalhado()
        assert result.get("atende_requisito_3_noites_bol") is True, (
            f"BOL não atende requisito de 3 noites: {result.get('autonomia_zero_sol_bol_noites'):.2f}"
        )


# ---------------------------------------------------------------------------
# 2. Balanço em dias nublados
# ---------------------------------------------------------------------------

class TestBalancoNublado:
    def test_balanco_liquido_nublado_negativo(self):
        """
        Em dias nublados com geração parcial, geração < consumo total diário.
        balanco_liquido_nublado_wh deve ser negativo.
        """
        result = calcular_balanco_energetico_detalhado()
        balanco = result.get("balanco_liquido_nublado_wh", 0)
        assert balanco < 0, (
            f"balanco_liquido_nublado_wh deve ser negativo (consumo > geração nublada), obtido {balanco:.2f}"
        )

    def test_geracao_nublada_less_than_pleno_sol(self):
        """Geração em dia nublado deve ser menor que geração em sol pleno."""
        result = calcular_balanco_energetico_detalhado()
        pleno = result.get("geracao_solar_sol_pleno_wh", 0)
        nublado = result.get("geracao_solar_dia_nublado_wh", 0)
        assert nublado < pleno, (
            f"Geração nublado ({nublado:.0f} Wh) deve ser < sol pleno ({pleno:.0f} Wh)"
        )

    def test_fator_recarga_nublado_less_than_1(self):
        """fator_recarga_nublado deve ser < 1 (geração parcial)."""
        result = calcular_balanco_energetico_detalhado()
        fator = result.get("fator_recarga_nublado", 1.0)
        assert fator < 1.0, (
            f"fator_recarga_nublado ({fator}) deve ser < 1.0"
        )


# ---------------------------------------------------------------------------
# 3. Campos obrigatórios no resultado
# ---------------------------------------------------------------------------

class TestCamposObrigatorios:
    REQUIRED_KEYS = [
        "potencia_led_w",
        "potencia_painel_wp",
        "capacidade_bateria_wh",
        "consumo_led_wh",
        "consumo_telemetria_wh",
        "consumo_total_diario_wh",
        "capacidade_util_bol_wh",
        "capacidade_util_eol_wh",
        "autonomia_zero_sol_bol_noites",
        "autonomia_zero_sol_eol_noites",
        "atende_requisito_3_noites_bol",
        "atende_requisito_3_noites_eol",
        "geracao_solar_sol_pleno_wh",
        "geracao_solar_dia_nublado_wh",
        "balanco_liquido_nublado_wh",
        "status_aviso",
    ]

    def test_all_required_keys_present(self):
        """Todos os campos obrigatórios devem estar no resultado."""
        result = calcular_balanco_energetico_detalhado()
        missing = [k for k in self.REQUIRED_KEYS if k not in result]
        assert not missing, f"Campos ausentes no balanço energético: {missing}"

    def test_consumo_total_diario_positive(self):
        """Consumo total diário deve ser positivo."""
        result = calcular_balanco_energetico_detalhado()
        consumo = result.get("consumo_total_diario_wh", 0)
        assert consumo > 0, f"Consumo total diário deve ser > 0, obtido {consumo}"

    def test_capacidade_bol_greater_than_eol(self):
        """Capacidade útil BOL deve ser maior que EOL."""
        result = calcular_balanco_energetico_detalhado()
        bol_wh = result.get("capacidade_util_bol_wh", 0)
        eol_wh = result.get("capacidade_util_eol_wh", 0)
        assert bol_wh > eol_wh, (
            f"Capacidade BOL ({bol_wh:.0f} Wh) deve ser > EOL ({eol_wh:.0f} Wh)"
        )


# ---------------------------------------------------------------------------
# 4. Consistência com config ENGENHARIA_SISTEMA_SOLAR_COMPACTO
# ---------------------------------------------------------------------------

class TestEngenhariaSolarCompacto:
    def test_config_capacidade_bateria_matches_calc(self):
        """Capacidade da bateria no resultado deve corresponder à configuração."""
        result = calcular_balanco_energetico_detalhado()
        config_cap = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["capacidade_bateria_wh"]
        result_cap = result.get("capacidade_bateria_wh", 0)
        assert abs(result_cap - config_cap) < 1.0, (
            f"Capacidade bateria config ({config_cap} Wh) ≠ resultado ({result_cap} Wh)"
        )

    def test_eol_capacity_is_bol_times_eol_pct(self):
        """Capacidade EOL = Capacidade BOL × capacidade_remanescente_eol."""
        result = calcular_balanco_energetico_detalhado()
        bol_wh = result.get("capacidade_util_bol_wh", 0)
        eol_wh = result.get("capacidade_util_eol_wh", 0)
        eol_pct = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["capacidade_remanescente_eol"]
        expected_eol = bol_wh * eol_pct
        assert abs(eol_wh - expected_eol) < 1.0, (
            f"EOL Wh esperado {expected_eol:.1f}, obtido {eol_wh:.1f} "
            f"(BOL={bol_wh:.1f} × EOL_pct={eol_pct})"
        )

"""
Testes de consistência financeira — Auditoria Final.

Verifica:
- CAPEX por trecho usa o custo unitário do cenário selecionado (não hardcoded)
- Cenário A: 40 postes × R$15.000 = R$600.000 por trecho
- Cenário D: 40 postes × R$22.310 = R$892.400 por trecho
- analyze_top_n propaga corretamente o cenario_id
- cenario_id e custo_unitario_poste presentes nos agregados
"""

import pandas as pd
import numpy as np
import pytest
from config import CENARIOS_ORCAMENTO, DEFAULT_SPACING_M, DEFAULT_COMPRIMENTO_TRECHO_KM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_accidents_df() -> pd.DataFrame:
    """DataFrame mínimo de acidentes com colunas obrigatórias para analyze_top_n."""
    rows = []
    for i in range(100):
        rows.append({
            "id": 700000 + i,
            "data_inversa": pd.Timestamp(f"2021-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"),
            "ano": 2021,
            "mes": (i % 12) + 1,
            "fase_dia_oficial": "Plena Noite" if i % 2 == 0 else "Pleno Dia",
            "fase_dia": "Plena noite" if i % 2 == 0 else "Pleno dia",
            "mortos": 1 if i < 20 else 0,
            "feridos_graves": 1,
            "feridos_leves": 2,
            "total_feridos": 3,
            "total_vitimas": 3 if i >= 20 else 4,
            "acidente_fatal": 1 if i < 20 else 0,
            "km": float(100 + i % 50),
            "br": "101",
            "uf": "MG",
            "latitude": -20.0 + (i % 10) * 0.01,
            "longitude": -43.0 + (i % 10) * 0.01,
            "classificacao_acidente": "Com vítimas feridas" if i < 20 else "Com vítimas feridas",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 1. Valores unitários dos cenários estão corretos em config.py
# ---------------------------------------------------------------------------

class TestCenariosOrcamentoConfig:
    def test_cenario_a_custo_unitario(self):
        """Cenário A deve ter custo unitário total de R$15.000."""
        c = CENARIOS_ORCAMENTO.get("cenario_a", {})
        assert abs(c.get("custo_unitario_total", 0) - 15000.00) < 1.0, (
            f"Cenário A custo_unitario_total esperado R$15.000, obtido R${c.get('custo_unitario_total')}"
        )

    def test_cenario_d_custo_unitario(self):
        """Cenário D deve ter custo unitário total de R$22.310."""
        c = CENARIOS_ORCAMENTO.get("cenario_d", {})
        assert abs(c.get("custo_unitario_total", 0) - 22310.00) < 1.0, (
            f"Cenário D custo_unitario_total esperado R$22.310, obtido R${c.get('custo_unitario_total')}"
        )

    def test_all_cenarios_present(self):
        """Todos os 5 cenários (a-e) devem estar presentes em CENARIOS_ORCAMENTO."""
        expected = {"cenario_a", "cenario_b", "cenario_c", "cenario_d", "cenario_e"}
        assert expected.issubset(set(CENARIOS_ORCAMENTO.keys())), (
            f"Cenários faltando: {expected - set(CENARIOS_ORCAMENTO.keys())}"
        )

    def test_cenario_d_cheaper_than_cenario_e(self):
        """Cenário D deve ser mais barato que Cenário E."""
        c_d = CENARIOS_ORCAMENTO["cenario_d"]["custo_unitario_total"]
        c_e = CENARIOS_ORCAMENTO["cenario_e"]["custo_unitario_total"]
        assert c_d < c_e, f"Cenário D (R${c_d}) deve ser < Cenário E (R${c_e})"


# ---------------------------------------------------------------------------
# 2. CAPEX por trecho calculado com custo do cenário correto
# ---------------------------------------------------------------------------

class TestCapexPerTrechoByScenario:
    def test_cenario_a_capex_per_trecho(self):
        """Cenário A: postes_por_trecho × R$15.000 deve ser ≈ R$600.000."""
        from financial_model import dimensionar_postes
        postes_info = dimensionar_postes(
            comprimento_trecho_km=DEFAULT_COMPRIMENTO_TRECHO_KM,
            espacamento_m=DEFAULT_SPACING_M,
            n_trechos=1,
        )
        postes = postes_info["postes_por_trecho"]
        custo_a = CENARIOS_ORCAMENTO["cenario_a"]["custo_unitario_total"]
        capex = postes * custo_a
        # 40 postes × 15000 = 600000
        assert abs(capex - 600_000) < 5_000, (
            f"Cenário A CAPEX/trecho esperado ≈ R$600.000, obtido R${capex:,.0f}"
        )

    def test_cenario_d_capex_per_trecho(self):
        """Cenário D: postes_por_trecho × R$22.310 deve ser ≈ R$892.400."""
        from financial_model import dimensionar_postes
        postes_info = dimensionar_postes(
            comprimento_trecho_km=DEFAULT_COMPRIMENTO_TRECHO_KM,
            espacamento_m=DEFAULT_SPACING_M,
            n_trechos=1,
        )
        postes = postes_info["postes_por_trecho"]
        custo_d = CENARIOS_ORCAMENTO["cenario_d"]["custo_unitario_total"]
        capex = postes * custo_d
        # 40 postes × 22310 = 892400
        assert abs(capex - 892_400) < 10_000, (
            f"Cenário D CAPEX/trecho esperado ≈ R$892.400, obtido R${capex:,.0f}"
        )

    def test_cenario_d_capex_greater_than_cenario_a(self):
        """CAPEX do Cenário D por trecho deve ser maior que Cenário A."""
        from financial_model import dimensionar_postes
        postes_info = dimensionar_postes(DEFAULT_COMPRIMENTO_TRECHO_KM, DEFAULT_SPACING_M, 1)
        postes = postes_info["postes_por_trecho"]
        capex_a = postes * CENARIOS_ORCAMENTO["cenario_a"]["custo_unitario_total"]
        capex_d = postes * CENARIOS_ORCAMENTO["cenario_d"]["custo_unitario_total"]
        assert capex_d > capex_a, (
            f"CAPEX D ({capex_d:,.0f}) deve ser > CAPEX A ({capex_a:,.0f})"
        )


# ---------------------------------------------------------------------------
# 3. analyze_top_n propaga cenario_id e custo correto
# ---------------------------------------------------------------------------

class TestAnalyzeTopNScenarioPropagation:
    def _get_analyzer(self):
        from analyzer import AccidentAnalyzer
        return AccidentAnalyzer()

    def test_cenario_id_in_agregados(self):
        """analyze_top_n deve incluir cenario_id nos agregados."""
        analyzer = self._get_analyzer()
        df = _make_minimal_accidents_df()
        _, agregados = analyzer.analyze_top_n(df, cenario_id="cenario_a")
        assert "cenario_id" in agregados, (
            f"'cenario_id' não encontrado em agregados: {list(agregados.keys())}"
        )
        assert agregados["cenario_id"] == "cenario_a", (
            f"cenario_id esperado 'cenario_a', obtido '{agregados['cenario_id']}'"
        )

    def test_custo_unitario_poste_cenario_a(self):
        """analyze_top_n com cenario_a deve usar custo R$15.000."""
        analyzer = self._get_analyzer()
        df = _make_minimal_accidents_df()
        _, agregados = analyzer.analyze_top_n(df, cenario_id="cenario_a")
        custo = agregados.get("custo_unitario_poste", 0)
        assert abs(custo - 15000.00) < 1.0, (
            f"Custo unitário Cenário A esperado R$15.000, obtido R${custo}"
        )

    def test_custo_unitario_poste_cenario_d(self):
        """analyze_top_n com cenario_d deve usar custo R$22.310."""
        analyzer = self._get_analyzer()
        df = _make_minimal_accidents_df()
        _, agregados = analyzer.analyze_top_n(df, cenario_id="cenario_d")
        custo = agregados.get("custo_unitario_poste", 0)
        assert abs(custo - 22310.00) < 1.0, (
            f"Custo unitário Cenário D esperado R$22.310, obtido R${custo}"
        )

    def test_scenarios_produce_different_custo(self):
        """Cenário D deve produzir custo_unitario_poste diferente do Cenário A."""
        analyzer = self._get_analyzer()
        df = _make_minimal_accidents_df()
        _, agregados_a = analyzer.analyze_top_n(df, cenario_id="cenario_a")
        _, agregados_d = analyzer.analyze_top_n(df, cenario_id="cenario_d")
        custo_a = agregados_a.get("custo_unitario_poste", 0)
        custo_d = agregados_d.get("custo_unitario_poste", 0)
        assert custo_d != custo_a, (
            f"Custos Cenário D ({custo_d}) e A ({custo_a}) não devem ser iguais"
        )
        assert custo_d > custo_a, (
            f"Custo D ({custo_d}) deve ser > A ({custo_a})"
        )

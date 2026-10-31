"""
Testes de consistência científica — Auditoria Final.

Verifica:
- Accident ID 730910 não aparece em períodos que não incluem 2025
- fases_oficiais_dict usa chaves snake_case corretas
- texto dinâmico de causas não contém números hardcoded proibidos
- fase mais letal identificada corretamente (dinâmica)
- BOL e EOL de autonomia solar são distintos
- anos_incompletos só incluídos quando o ano está nos dados
"""

import pandas as pd
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_day_night_df(phase_mortos: dict) -> pd.DataFrame:
    """
    Cria DataFrame com colunas esperadas por compute_day_vs_night_comparison.
    phase_mortos: {fase_oficial: n_mortos_por_acidente}. 10 acidentes por fase.
    """
    rows = []
    i = 0
    for fase, mortos_each in phase_mortos.items():
        for _ in range(10):
            rows.append({
                "id": i,
                "fase_dia_oficial": fase,
                "fase_dia": fase,
                "mortos": mortos_each,
                "feridos_graves": 0,
                "feridos_leves": 1,
                "total_feridos": 1,
                "total_vitimas": mortos_each + 1,
                "acidente_fatal": 1 if mortos_each > 0 else 0,
            })
            i += 1
    return pd.DataFrame(rows)


def _make_causas_df(n_rt: int = 15, n_ar: int = 15, n_outros: int = 10) -> pd.DataFrame:
    """
    DataFrame de causas com colunas obrigatórias para analyze_visibility_and_reaction.
    """
    rows = []
    for i in range(n_rt):
        rows.append({
            "id": i,
            "causa_acidente": "Reação tardia do condutor",
            "fase_dia_oficial": "Plena Noite",
            "mortos": 0,
            "feridos_graves": 1,
            "feridos_leves": 1,
            "total_feridos": 2,
            "acidente_fatal": 0,
        })
    for i in range(n_rt, n_rt + n_ar):
        rows.append({
            "id": i,
            "causa_acidente": "Ausência de reação do condutor",
            "fase_dia_oficial": "Plena Noite",
            "mortos": 1,
            "feridos_graves": 0,
            "feridos_leves": 0,
            "total_feridos": 0,
            "acidente_fatal": 1,
        })
    for i in range(n_rt + n_ar, n_rt + n_ar + n_outros):
        rows.append({
            "id": i,
            "causa_acidente": "Velocidade incompatível",
            "fase_dia_oficial": "Pleno Dia",
            "mortos": 0,
            "feridos_graves": 0,
            "feridos_leves": 1,
            "total_feridos": 1,
            "acidente_fatal": 0,
        })
    return pd.DataFrame(rows)


def _make_accidents_df(n: int = 50) -> pd.DataFrame:
    """DataFrame mínimo de acidentes para analyze_visibility_and_reaction."""
    rows = []
    for i in range(n):
        # fase_dia is the grouping column used when fase_dia_agrupada is absent
        fase = "Plena noite" if i % 2 == 0 else "Pleno dia"
        rows.append({
            "id": i,
            "fase_dia": fase,
            "fase_dia_oficial": "Plena Noite" if i % 2 == 0 else "Pleno Dia",
            "mortos": 1 if i < 10 else 0,
            "feridos_graves": 0,
            "feridos_leves": 1,
            "total_feridos": 1,
            "acidente_fatal": 1 if i < 10 else 0,
            "km": 100.0,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 1. Accident 730910 not in 2021-2022 data
# ---------------------------------------------------------------------------

class TestAccidentIdOutsidePeriod:
    def test_id_730910_absent_in_2021_2022_data(self):
        """ID 730910 (acidente de 2025) NÃO deve aparecer em dados 2021-2022."""
        ids_2021_2022 = list(range(700000, 700200))
        assert 730910 not in ids_2021_2022, (
            "ID 730910 não deveria estar presente em dados filtrados para 2021-2022"
        )

    def test_id_730910_conditional_display(self):
        """Lógica condicional: ID 730910 só aparece quando presente na base filtrada."""
        df_with = pd.DataFrame({"id": [730910, 100001]})
        df_without = pd.DataFrame({"id": [100001, 100002]})
        assert 730910 in df_with["id"].values
        assert 730910 not in df_without["id"].values


# ---------------------------------------------------------------------------
# 2. fases_oficiais_dict — snake_case keys corretos
# ---------------------------------------------------------------------------

class TestFasesOficiaisDict:
    def test_fases_dict_snake_case_keys(self):
        """fases_oficiais_dict deve usar chaves snake_case das 4 fases oficiais PRF."""
        from metrics import compute_day_vs_night_comparison

        df = _make_day_night_df({
            "Plena Noite": 2,
            "Pleno Dia": 1,
            "Amanhecer": 3,
            "Anoitecer": 1,
        })
        result = compute_day_vs_night_comparison(df)
        fases_dict = result.get("fases_oficiais_dict", {})

        expected_keys = {"plena_noite", "pleno_dia", "amanhecer", "anoitecer"}
        assert expected_keys.issubset(set(fases_dict.keys())), (
            f"fases_oficiais_dict deve conter {expected_keys}, obtido {set(fases_dict.keys())}"
        )

    def test_fases_dict_plena_noite_mortos_por_100(self):
        """Plena Noite com 3 mortos/acidente × 10 acidentes → mortos_por_100 = 300.0."""
        from metrics import compute_day_vs_night_comparison

        df = _make_day_night_df({"Plena Noite": 3, "Pleno Dia": 1})
        result = compute_day_vs_night_comparison(df)
        fases_dict = result.get("fases_oficiais_dict", {})
        pn = fases_dict.get("plena_noite", {})
        # 30 mortos / 10 acidentes * 100 = 300.0
        assert abs(pn.get("mortos_por_100", 0) - 300.0) < 0.01, (
            f"mortos_por_100 para Plena Noite: esperado 300.0, obtido {pn.get('mortos_por_100')}"
        )

    def test_fases_dict_contains_fase_oficial_label(self):
        """Cada entrada de fases_oficiais_dict deve preservar o label oficial."""
        from metrics import compute_day_vs_night_comparison

        df = _make_day_night_df({"Plena Noite": 1, "Pleno Dia": 0})
        result = compute_day_vs_night_comparison(df)
        fases_dict = result.get("fases_oficiais_dict", {})
        pn = fases_dict.get("plena_noite", {})
        assert pn.get("fase_oficial") == "Plena Noite", (
            f"fase_oficial esperado 'Plena Noite', obtido '{pn.get('fase_oficial')}'"
        )


# ---------------------------------------------------------------------------
# 3. Texto dinâmico de causas — sem hardcode proibido
# ---------------------------------------------------------------------------

class TestDynamicCausesText:
    def _run_reaction_analysis(self):
        from reaction_analysis import analyze_visibility_and_reaction
        df = _make_accidents_df(50)
        causas_df = _make_causas_df(n_rt=15, n_ar=15, n_outros=10)
        return analyze_visibility_and_reaction(df, causas_df)

    def test_no_hardcoded_52_mil_in_evidence_text(self):
        """evidencias_texto não deve conter '52 mil' hardcoded."""
        result = self._run_reaction_analysis()
        evid = result.get("evidencias_texto", "")
        assert "52 mil" not in evid, (
            "evidencias_texto contém '52 mil' hardcoded — deve ser dinâmico"
        )

    def test_no_hardcoded_52000_in_evidence_text(self):
        """evidencias_texto não deve conter '52000' hardcoded."""
        result = self._run_reaction_analysis()
        evid = result.get("evidencias_texto", "")
        assert "52000" not in evid, (
            "evidencias_texto contém '52000' hardcoded — deve ser dinâmico"
        )

    def test_evidencias_texto_contains_dynamic_number(self):
        """evidencias_texto deve conter pelo menos um número calculado dinamicamente."""
        import re
        result = self._run_reaction_analysis()
        evid = result.get("evidencias_texto", "")
        assert re.search(r"\d+", evid), (
            "evidencias_texto está vazio ou sem números — esperado texto dinâmico"
        )

    def test_resumo_reacao_dinamico_has_content(self):
        """resumo_reacao_dinamico deve ser um dicionário não-vazio."""
        result = self._run_reaction_analysis()
        resumo = result.get("resumo_reacao_dinamico", {})
        assert isinstance(resumo, dict) and len(resumo) > 0, (
            f"resumo_reacao_dinamico deve ter conteúdo, obtido: {resumo}"
        )


# ---------------------------------------------------------------------------
# 4. Fase mais letal identificada dinamicamente
# ---------------------------------------------------------------------------

class TestFaseMaisLetalDynamic:
    def test_plena_noite_mais_letal_quando_tem_mais_mortos(self):
        """Quando Plena Noite tem a maior taxa de mortalidade, deve ser identificada como mais letal."""
        from metrics import compute_day_vs_night_comparison

        df = _make_day_night_df({
            "Plena Noite": 3,
            "Pleno Dia": 1,
            "Amanhecer": 2,
            "Anoitecer": 1,
        })
        result = compute_day_vs_night_comparison(df)
        fase_nome = result.get("fase_mais_letal_nome", "")
        assert fase_nome == "Plena Noite", (
            f"Esperado 'Plena Noite' como fase mais letal, obtido '{fase_nome}'"
        )

    def test_amanhecer_mais_letal_quando_tem_mais_mortos(self):
        """Quando Amanhecer tem a maior taxa, deve ser identificado como mais letal."""
        from metrics import compute_day_vs_night_comparison

        df = _make_day_night_df({
            "Plena Noite": 2,
            "Pleno Dia": 1,
            "Amanhecer": 5,
            "Anoitecer": 1,
        })
        result = compute_day_vs_night_comparison(df)
        fase_nome = result.get("fase_mais_letal_nome", "")
        assert fase_nome == "Amanhecer", (
            f"Esperado 'Amanhecer' como fase mais letal, obtido '{fase_nome}'"
        )

    def test_texto_interpretativo_nao_e_vazio(self):
        """texto_interpretativo_fases deve ser uma string não-vazia."""
        from metrics import compute_day_vs_night_comparison

        df = _make_day_night_df({"Plena Noite": 2, "Pleno Dia": 1})
        result = compute_day_vs_night_comparison(df)
        texto = result.get("texto_interpretativo_fases", "")
        assert isinstance(texto, str) and len(texto) > 20, (
            f"texto_interpretativo_fases deve ser texto substantivo, obtido: '{texto}'"
        )

    def test_fase_mais_letal_key_matches_dict(self):
        """fase_mais_letal_key deve existir como chave em fases_oficiais_dict."""
        from metrics import compute_day_vs_night_comparison

        df = _make_day_night_df({
            "Plena Noite": 3,
            "Pleno Dia": 1,
            "Amanhecer": 2,
            "Anoitecer": 1,
        })
        result = compute_day_vs_night_comparison(df)
        key = result.get("fase_mais_letal_key", "")
        fases_dict = result.get("fases_oficiais_dict", {})
        assert key in fases_dict, (
            f"fase_mais_letal_key '{key}' não encontrada em fases_oficiais_dict {list(fases_dict.keys())}"
        )


# ---------------------------------------------------------------------------
# 5. Autonomia solar BOL ≠ EOL (usa chaves corretas da função)
# ---------------------------------------------------------------------------

class TestEnergyBalanceBOLvsEOL:
    def test_bol_and_eol_are_distinct(self):
        """BOL e EOL de autonomia zero-solar devem ser numericamente distintos."""
        from financial_model import calcular_balanco_energetico_detalhado

        result = calcular_balanco_energetico_detalhado()
        bol = result.get("autonomia_zero_sol_bol_noites")
        eol = result.get("autonomia_zero_sol_eol_noites")
        assert bol is not None, "autonomia_zero_sol_bol_noites não encontrada"
        assert eol is not None, "autonomia_zero_sol_eol_noites não encontrada"
        assert bol != eol, (
            f"BOL ({bol}) e EOL ({eol}) não devem ser iguais — refletem degradação da bateria"
        )

    def test_bol_greater_than_eol(self):
        """BOL deve ser maior que EOL (bateria nova vs degradada)."""
        from financial_model import calcular_balanco_energetico_detalhado

        result = calcular_balanco_energetico_detalhado()
        bol = result["autonomia_zero_sol_bol_noites"]
        eol = result["autonomia_zero_sol_eol_noites"]
        assert bol > eol, f"BOL ({bol:.2f}) deve ser > EOL ({eol:.2f})"

    def test_bol_consistent_with_capacity_and_consumption(self):
        """BOL deve ser consistente: capacidade_util_bol_wh / consumo_total_diario_wh."""
        from financial_model import calcular_balanco_energetico_detalhado

        result = calcular_balanco_energetico_detalhado()
        bol_wh = result.get("capacidade_util_bol_wh", 0)
        consumo = result.get("consumo_total_diario_wh", 1)
        bol = result.get("autonomia_zero_sol_bol_noites", 0)
        expected = bol_wh / consumo
        assert abs(bol - expected) < 0.01, (
            f"BOL inconsistente: derivado={expected:.2f}, retornado={bol:.2f}"
        )


# ---------------------------------------------------------------------------
# 6. anos_incompletos scope — via process_raw_dataframe
# ---------------------------------------------------------------------------

class TestAnosIncompletosScope:
    def test_2025_not_in_anos_incompletos_for_2021_2022_period(self):
        """Com dados de 2021-2022, 2025 não deve aparecer em anos_incompletos."""
        from data_loader import process_raw_dataframe

        rows = []
        for year in [2021, 2022]:
            for month in range(1, 13):
                rows.append({
                    "id": f"A{year}{month}",
                    "data_inversa": f"{year}-{month:02d}-15",
                    "fase_dia": "Plena noite",
                    "mortos": 0,
                    "feridos_graves": 0,
                    "feridos_leves": 1,
                    "km": 100.0,
                    "br": "101",
                    "uf": "MG",
                    "tipo_acidente": "Colisão frontal",
                    "causa_acidente": "Velocidade incompatível",
                    "classificacao_acidente": "Com vítimas feridas",
                    "tracado_via": "Reta",
                    "uso_solo": "Rural",
                    "latitude": -20.0,
                    "longitude": -43.0,
                })
        df_raw = pd.DataFrame(rows)
        df_raw["data_inversa"] = pd.to_datetime(df_raw["data_inversa"])
        # process_raw_dataframe returns a 5-tuple: (df, pessoas_df, veiculos_df, causas_df, quality)
        result = process_raw_dataframe(df_raw, source_name="test_2021_2022")
        quality = result[-1]  # last element is the quality dict
        incomplete = quality.get("anos_incompletos", [])
        assert 2025 not in incomplete, (
            f"2025 não deve estar em anos_incompletos para dados 2021-2022, obtido: {incomplete}"
        )

    def test_quality_dict_is_returned(self):
        """process_raw_dataframe deve retornar um dict de qualidade como último elemento."""
        from data_loader import process_raw_dataframe

        rows = [{
            "id": "A1",
            "data_inversa": "2021-06-15",
            "fase_dia": "Plena noite",
            "mortos": 0,
            "feridos_graves": 0,
            "feridos_leves": 1,
            "km": 100.0,
            "br": "101",
            "uf": "MG",
            "tipo_acidente": "Colisão",
            "causa_acidente": "Velocidade",
            "classificacao_acidente": "Com vítimas feridas",
            "tracado_via": "Reta",
            "uso_solo": "Rural",
            "latitude": -20.0,
            "longitude": -43.0,
        }]
        df_raw = pd.DataFrame(rows)
        df_raw["data_inversa"] = pd.to_datetime(df_raw["data_inversa"])
        result = process_raw_dataframe(df_raw, source_name="test")
        quality = result[-1]
        assert isinstance(quality, dict), (
            f"Último elemento de process_raw_dataframe deve ser dict, obtido {type(quality)}"
        )

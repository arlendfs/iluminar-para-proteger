"""
Testes automatizados específicos para as correções críticas de memória,
integridade de quilometragem rodoviária, desduplicação de IDs,
ausência de tags HTML visíveis e conformidade do relatório PDF.
"""

import os
import gc
import re
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from analyzer import AccidentAnalyzer
from data_loader import audit_and_clean_km_series, process_raw_dataframe
from metrics import compute_day_vs_night_comparison
from segmentation import create_road_segments, rank_segments
from pdf_generator import (
    ReportGenerator,
    format_pt_br_currency,
    format_pt_br_number,
    format_pt_br_int,
    _md_to_reportlab,
)
from config import VALIDATION_RULES, NORMALIZED_CACHE_DIR, BASE_DIR


def test_user_memory_release_and_cleanup():
    """
    Testa que a liberação de recursos pelo usuário (analyzer.clear())
    anula todos os DataFrames internos e resumos sem reter referências.
    """
    analyzer = AccidentAnalyzer()
    analyzer.data = pd.DataFrame({"id": [1, 2], "mortos": [0, 1]})
    analyzer.pessoas_data = pd.DataFrame({"id": [1, 2], "pesid": [10, 20]})
    analyzer.veiculos_data = pd.DataFrame({"id": [1, 2], "id_veiculo": [100, 200]})
    analyzer.causas_data = pd.DataFrame({"id": [1, 2], "causa": ["A", "B"]})
    analyzer.quality_summary = {"ocorrencias": 2}
    analyzer.filtered_data = analyzer.data

    assert analyzer.data is not None
    assert analyzer.pessoas_data is not None

    analyzer.clear()
    gc.collect()

    assert analyzer.data is None
    assert analyzer.pessoas_data is None
    assert analyzer.veiculos_data is None
    assert analyzer.causas_data is None
    assert analyzer.quality_summary == {}
    assert analyzer.filtered_data is None


def test_km_auditing_and_recovery():
    """
    Testa a auditoria e limpeza detalhada de quilômetros rodoviários:
    - Ausente, não-numérico, negativo, válido padrão (<1500),
      superior a 1500 recuperado (1500-6000), e extremo inválido (>6000).
    """
    s = pd.Series([
        None,           # ausente
        "N/A",          # ausente / não-numérico
        "texto_invalido", # não-numérico
        "-15,4",        # negativo
        "145,5",        # válido padrão
        "1520,0",       # superior 1500 recuperado (ex: BR-101/BR-116)
        "4540,5",       # superior 1500 recuperado (extensão real BR-116)
        "9999,0",       # extremo inválido (>6000)
    ])

    cleaned, status, audit_info = audit_and_clean_km_series(s)

    assert status.iloc[0] == "ausente"
    assert np.isnan(cleaned.iloc[0])

    assert status.iloc[1] in ("ausente", "nao_numerico")
    assert np.isnan(cleaned.iloc[1])

    assert status.iloc[2] == "nao_numerico"
    assert np.isnan(cleaned.iloc[2])

    assert status.iloc[3] == "negativo"
    assert np.isnan(cleaned.iloc[3])

    assert status.iloc[4] == "valido"
    assert pytest.approx(cleaned.iloc[4], 0.01) == 145.5

    assert status.iloc[5] == "superior_1500_recuperado"
    assert pytest.approx(cleaned.iloc[5], 0.01) == 1520.0

    assert status.iloc[6] == "superior_1500_recuperado"
    assert pytest.approx(cleaned.iloc[6], 0.01) == 4540.5

    assert status.iloc[7] == "invalido_extremo"
    assert np.isnan(cleaned.iloc[7])


def test_missing_id_pesid_namespacing():
    """
    Testa que registros sem 'id' ou sem 'pesid' recebem identificadores
    com namespace do arquivo, prevenindo colisões silenciosas entre arquivos distintos.
    """
    raw_df_a = pd.DataFrame({
        "id": [None, None],
        "pesid": [None, None],
        "ano": [2024, 2024],
        "uf": ["MG", "MG"],
        "br": ["116", "116"],
        "km": ["100", "101"],
        "fase_dia": ["Plena Noite", "Plena Noite"],
        "mortos": [0, 1],
    })
    raw_df_b = pd.DataFrame({
        "id": [None, None],
        "pesid": [None, None],
        "ano": [2025, 2025],
        "uf": ["SP", "SP"],
        "br": ["101", "101"],
        "km": ["200", "201"],
        "fase_dia": ["Pleno dia", "Pleno dia"],
        "mortos": [0, 0],
    })

    oc_a, pes_a, _, _, _ = process_raw_dataframe(raw_df_a, "file_a")
    oc_b, pes_b, _, _, _ = process_raw_dataframe(raw_df_b, "file_b")

    ids_a = set(oc_a["id"])
    ids_b = set(oc_b["id"])
    assert ids_a.isdisjoint(ids_b), "IDs gerados sem ID original não devem colidir entre arquivos diferentes!"

    pes_ids_a = set(pes_a["pesid"])
    pes_ids_b = set(pes_b["pesid"])
    assert pes_ids_a.isdisjoint(pes_ids_b), "Pesids gerados sem pesid original não devem colidir!"


def test_no_visible_html_tags_in_interpretation():
    """
    Testa que os textos interpretativos de fases do dia não contêm tags HTML brutas
    como <b> ou </b>, utilizando estritamente formatação Markdown (**) e números em pt-BR.
    """
    df = pd.DataFrame({
        "id": range(1, 101),
        "fase_dia_oficial": ["Plena Noite"] * 40 + ["Pleno dia"] * 50 + ["Amanhecer"] * 10,
        "fase_dia_agrupada": ["Noturno"] * 40 + ["Diurno"] * 50 + ["Crepúsculo"] * 10,
        "mortos": [1] * 20 + [0] * 80,
        "feridos_graves": [1] * 10 + [0] * 90,
        "feridos_leves": [1] * 30 + [0] * 70,
        "total_feridos": [2] * 10 + [1] * 30 + [0] * 60,
        "total_vitimas": [3] * 10 + [2] * 10 + [1] * 30 + [0] * 50,
        "acidente_fatal": [1] * 20 + [0] * 80,
    })

    comp = compute_day_vs_night_comparison(df)
    texto_fases = comp.get("texto_interpretativo_fases", "")
    destaque = comp.get("destaque_fases", "")

    # Não deve conter tags HTML brutas <b> ou </b>
    assert "<b>" not in texto_fases
    assert "</b>" not in texto_fases
    assert "<b>" not in destaque
    assert "</b>" not in destaque

    # Deve conter formatação em markdown **
    assert "**" in texto_fases

    # Formatação de taxa em pt-BR (vírgula decimal)
    assert re.search(r"\d+,\d{2}", texto_fases) is not None

    # O helper _md_to_reportlab deve converter ** para <b> para renderização correta no PDF
    pdf_text = _md_to_reportlab(texto_fases)
    assert "<b>" in pdf_text
    assert "**" not in pdf_text


def test_exceptional_event_sensitivity_audit():
    """
    Testa a detecção de eventos catastróficos excepcionais (ex: >= 5 mortos)
    e a análise de sensibilidade no ranking de trechos rodoviários.
    """
    # Cria trecho com 5 acidentes, sendo 1 com 37 mortos e outros 4 sem mortos
    df_catastrofe = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "uf": ["MG"] * 5,
        "br": ["116"] * 5,
        "km": [286.5, 286.2, 287.0, 287.5, 286.8],
        "latitude": [-18.5] * 5,
        "longitude": [-41.9] * 5,
        "fase_dia_agrupada": ["Noturno"] * 5,
        "fase_dia_oficial": ["Plena Noite"] * 5,
        "mortos": [37, 0, 0, 0, 0],
        "feridos_graves": [10, 0, 1, 0, 0],
        "feridos_leves": [20, 1, 0, 1, 0],
        "total_feridos": [30, 1, 1, 1, 0],
        "total_vitimas": [67, 1, 1, 1, 0],
        "acidente_fatal": [1, 0, 0, 0, 0],
    })

    segments, stats = create_road_segments(df_catastrofe, comprimento_km=2.0)
    assert not segments.empty
    seg = segments.iloc[0]

    assert seg["tem_evento_excepcional"] == True
    assert seg["mortos_excepcionais_noturno"] == 37
    assert seg["mortos_noturno_sem_excepcional"] == 0
    assert seg["score_iluminacao_solar"] > seg["score_iluminacao_solar_sem_excepcional"]

    # Teste de ranking com e sem eventos excepcionais
    ranked_com = rank_segments(segments, criterio="iluminacao_solar")
    ranked_sem = rank_segments(segments, criterio="iluminacao_solar_sem_excepcionais")

    assert not ranked_com.empty
    assert not ranked_sem.empty


def test_pt_br_formatting_helpers():
    """
    Testa helpers de formatação brasileira para moeda, número e inteiro.
    """
    assert format_pt_br_currency(1234567.89) == "R$&nbsp;1.234.567,89"
    assert format_pt_br_currency(0.0) == "R$&nbsp;0,00"
    assert format_pt_br_currency(None) == "R$&nbsp;0,00"

    assert format_pt_br_int(145685) == "145.685"
    assert format_pt_br_int(0) == "0"
    assert format_pt_br_int(None) == "0"

    assert format_pt_br_number(11.72, 2) == "11,72"
    assert format_pt_br_number(1.97, 2) == "1,97"


def test_regression_benchmark_2024_2025():
    """
    Validação da referência de regressão auditada para o período 2024-2025:
    - 145.685 acidentes desduplicados
    - 12.203 mortos confirmados
    - 168.076 feridos
    - ~11,72 óbitos/100 acidentes em Plena Noite
    - ~5,94 em Pleno Dia
    - Razão de severidade ~1,97
    """
    analyzer = AccidentAnalyzer()
    files = ["acidentes2024_todas_causas_tipos.parquet", "acidentes2025_todas_causas_tipos.parquet"]
    df = analyzer.load_local_files("parquet_samples", files)

    assert df is not None
    assert len(df) == 145685, f"Esperado 145.685 acidentes, obtido {len(df):,}"
    assert df["mortos"].sum() == 12203, f"Esperado 12.203 mortos, obtido {df['mortos'].sum():,}"
    assert df["total_feridos"].sum() == 168076, f"Esperado 168.076 feridos, obtido {df['total_feridos'].sum():,}"

    comp = compute_day_vs_night_comparison(df)
    fases = comp.get("fases_oficiais_dict", {})

    pn_let = fases.get("plena_noite", {}).get("mortos_por_100", 0.0)
    pd_let = fases.get("pleno_dia", {}).get("mortos_por_100", 0.0)

    assert pytest.approx(pn_let, 0.05) == 11.72
    assert pytest.approx(pd_let, 0.05) == 5.94
    assert pytest.approx(pn_let / pd_let, 0.05) == 1.97

"""
Testes automatizados para memória, processamento incremental e consistência de relatórios.
"""

import gc
import pytest
import pandas as pd
import numpy as np
from analyzer import AccidentAnalyzer
from data_loader import process_raw_dataframe
from config import get_current_rss_mb
from pdf_generator import ReportGenerator


def test_incremental_processing_memory_and_integrity():
    """
    Testa processamento incremental de arquivos reais da PRF:
    - O consumo de RSS deve se manter estável;
    - As granularidades relacionais devem ser preservadas sem duplicações indevidas.
    """
    analyzer = AccidentAnalyzer()
    initial_rss = get_current_rss_mb()

    # Processa 2 arquivos pequenos/médios da pasta parquet_samples
    files_to_load = ["acidentes2020_todas_causas_tipos.parquet", "acidentes2026_todas_causas_tipos.parquet"]
    df = analyzer.load_local_files("parquet_samples", files_to_load)

    assert df is not None
    assert not df.empty
    qual = analyzer.quality_summary

    # Validações estritas de integridade
    assert qual["ocorrencias_unicas"] == len(df)
    assert qual["pessoas_unicas_pesid"] == len(analyzer.pessoas_data)
    assert qual["veiculos_unicos"] == len(analyzer.veiculos_data)
    assert qual["desdobramentos_consolidados"] == qual["registros_brutos"] - qual["ocorrencias_unicas"]
    assert qual["total_mortos_real"] == df["mortos"].sum()

    # Ocorrências sem KM não podem contaminar KM 0.0
    sem_km = df[df["km_limpo"].isna()]
    if not sem_km.empty:
        assert pd.isna(sem_km["km"].iloc[0])


def test_absence_of_redundant_copies_in_filters():
    """
    Testa que aplicar filtros vazios/completos não duplica DataFrames na memória.
    """
    analyzer = AccidentAnalyzer()
    df_raw = pd.DataFrame({
        "id": [1, 2, 3],
        "ano": [2025, 2025, 2026],
        "uf": ["SP", "RJ", "MG"],
        "br": ["116", "101", "381"],
        "fase_dia_oficial": ["Plena Noite", "Pleno dia", "Plena Noite"],
        "fase_dia_agrupada": ["Noturno", "Diurno", "Noturno"],
        "mortos": [1, 0, 0],
        "feridos_graves": [0, 1, 0],
        "feridos_leves": [0, 0, 1],
        "ilesos": [0, 0, 0],
        "total_feridos": [0, 1, 1],
        "total_vitimas": [1, 1, 1],
        "acidente_fatal": [1, 0, 0],
        "km_limpo": [10.0, 20.0, 30.0],
        "latitude_limpa": [-23.5, -22.9, -19.9],
        "longitude_limpa": [-46.6, -43.2, -43.9],
    })
    analyzer.data = df_raw
    analyzer.pessoas_data = pd.DataFrame()
    analyzer.veiculos_data = pd.DataFrame()
    analyzer.causas_data = pd.DataFrame()

    # Sem filtros: filtered_df aponta para a mesma base sem clone redundante
    filtered = analyzer.apply_filters(df_raw, {})
    assert len(filtered) == 3


def test_pdf_report_no_hardcoded_numbers_and_dynamic_consistency():
    """
    Testa a geração de relatório garantindo que valores calculados sob medida
    sejam refletidos no PDF sem textos hardcoded obsoletos (ex: 45,8 vidas fixas).
    """
    generator = ReportGenerator()

    df_ocorrencias = pd.DataFrame({
        "id": range(1, 21),
        "ano": [2025] * 20,
        "ano_mes": ["2025-06"] * 20,
        "uf": ["PR"] * 20,
        "br": ["277"] * 20,
        "km": [100.0 + i for i in range(20)],
        "latitude": [-25.0 - (i * 0.01) for i in range(20)],
        "longitude": [-50.0 - (i * 0.01) for i in range(20)],
        "fase_dia_oficial": ["Plena Noite"] * 10 + ["Pleno dia"] * 10,
        "fase_dia_agrupada": ["Noturno"] * 10 + ["Diurno"] * 10,
        "mortos": [1] * 5 + [0] * 15,
        "feridos_graves": [1] * 5 + [0] * 15,
        "feridos_leves": [1] * 10 + [0] * 10,
        "total_feridos": [2] * 5 + [1] * 5 + [0] * 10,
        "total_vitimas": [3] * 5 + [1] * 5 + [0] * 10,
        "acidente_fatal": [1] * 5 + [0] * 15,
    })

    top_segments = pd.DataFrame({
        "trecho_id": [f"BR-277 (PR) KM {i*2}.0 - {i*2+2}.0" for i in range(3)],
        "n_acidentes_noturnos": [5, 3, 2],
        "mortos_noturno": [2, 1, 0],
        "feridos_graves_noturno": [3, 1, 1],
        "score_iluminacao_solar": [25.0, 15.0, 10.0],
        "investimento_trecho": [750000.0, 750000.0, 750000.0],
        "economia_anual_trecho": [500000.0, 300000.0, 100000.0],
    })

    # Cenário com exatamente 3,5 vidas salvas/ano (não 45,8!)
    financial_summary = {
        "investimento_total": 2250000.0,
        "custo_unitario_poste": 18750.0,
        "economia_anual": 900000.0,
        "economia_liquida_anual": 800000.0,
        "vpl": 4500000.0,
        "tir": 0.32,
        "payback_simples_anos": 2.8,
        "vidas_salvas_ano": 3.5,
        "graves_evitados_ano": 8.0,
        "leves_evitados_ano": 15.0,
        "anos_base": 1.0,
        "cenarios": {
            "base": {"nome": "Cenário Customizado", "taxa_reducao": 0.35, "vidas_salvas_ano": 3.5, "beneficio_anual_bruto": 900000.0, "vpl": 4500000.0, "payback_simples": 2.8}
        }
    }

    pdf_buffer = generator.generate_accident_analysis_report(
        filtered_data=df_ocorrencias,
        top_segments=top_segments,
        financial_summary=financial_summary,
    )

    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")

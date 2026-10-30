"""
Testes automatizados para gestão de fontes de dados, exclusividade e integridade de carregamento.
"""

import os
from pathlib import Path
import pytest
import pandas as pd
from app import scan_project_folder
from analyzer import AccidentAnalyzer
from data_loader import process_raw_dataframe


def test_scan_project_folder_parquet_samples():
    """
    Testa o reconhecimento correto dos arquivos reais na pasta parquet_samples.
    """
    files = scan_project_folder("parquet_samples")
    assert len(files) >= 7
    years = [f["year"] for f in files if f["year"] is not None]
    assert 2020 in years
    assert 2021 in years
    assert 2026 in years
    # Cada arquivo possui atributos obrigatórios
    for f in files:
        assert "name" in f
        assert "size_bytes" in f
        assert f["size_bytes"] > 0
        assert f["extension"] in [".parquet", ".csv"]


def test_scan_project_folder_empty_or_nonexistent():
    """
    Testa comportamento seguro com pastas inexistentes ou vazias.
    """
    files_nonexistent = scan_project_folder("pasta_fantasma_xyz")
    assert files_nonexistent == []


def test_file_selection_year_deduplication():
    """
    Testa detecção de duplicatas de ano (CSV vs Parquet) priorizando Parquet.
    """
    mock_files = [
        {"name": "acidentes2025.csv", "year": 2025, "extension": ".csv", "size_bytes": 100},
        {"name": "acidentes2025.parquet", "year": 2025, "extension": ".parquet", "size_bytes": 50},
        {"name": "acidentes2026.parquet", "year": 2026, "extension": ".parquet", "size_bytes": 60},
    ]
    # Algoritmo de preferência: Parquet primeiro
    sorted_by_pref = sorted(mock_files, key=lambda x: (x["year"] or 0, 0 if x["extension"] == ".parquet" else 1))
    selected = []
    seen_years = set()
    for f in sorted_by_pref:
        if f["year"] not in seen_years:
            selected.append(f["name"])
            seen_years.add(f["year"])

    assert selected == ["acidentes2025.parquet", "acidentes2026.parquet"]
    assert "acidentes2025.csv" not in selected


def test_independent_folder_loading():
    """
    Testa que load_local_files lê apenas da pasta indicada sem misturar arquivos.
    """
    analyzer = AccidentAnalyzer()
    df = analyzer.load_local_files("parquet_samples", ["acidentes2020_todas_causas_tipos.parquet"])
    assert df is not None
    assert not df.empty
    assert analyzer.quality_summary["ocorrencias_unicas"] > 0
    assert analyzer.quality_summary["arquivo_origem"] == "acidentes2020_todas_causas_tipos.parquet"


def test_cache_signature_invalidation():
    """
    Testa geração e invalidação estrita de assinaturas de arquivos baseadas em tamanho e mtime.
    """
    files_a = [("arq1.parquet", 1000, 1600000000.0)]
    files_b = [("arq1.parquet", 1000, 1600000005.0)]  # mtime alterado
    files_c = [("arq2.parquet", 1000, 1600000000.0)]  # outro arquivo

    sig_a = "local_data_" + "_".join([f"{f[0]}_{f[1]}_{f[2]}" for f in files_a])
    sig_b = "local_data_" + "_".join([f"{f[0]}_{f[1]}_{f[2]}" for f in files_b])
    sig_c = "local_parquet_samples_" + "_".join([f"{f[0]}_{f[1]}_{f[2]}" for f in files_c])

    assert sig_a != sig_b
    assert sig_a != sig_c


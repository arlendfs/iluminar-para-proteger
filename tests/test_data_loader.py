"""
Testes automatizados para o módulo de ingestão, limpeza e qualidade de dados.
"""

import pytest
import pandas as pd
import numpy as np
from data_loader import (
    clean_brazilian_float,
    clean_km_series,
    clean_coordinate_series,
    standardize_fase_dia,
    get_fase_dia_agrupada,
    process_raw_dataframe,
)


def test_clean_brazilian_float():
    assert clean_brazilian_float("123,45") == 123.45
    assert clean_brazilian_float("123.45") == 123.45
    assert clean_brazilian_float("-27,08476806") == pytest.approx(-27.08476806)
    assert clean_brazilian_float(None) is None
    assert clean_brazilian_float(np.nan) is None
    assert clean_brazilian_float("") is None
    assert clean_brazilian_float("nan") is None
    assert clean_brazilian_float("N/A") is None
    # Não deve converter strings inválidas em zero
    assert clean_brazilian_float("invalido") is None


def test_clean_km_series():
    s = pd.Series(["145", "639,3", None, "abc", "174,4", "-5", "2000"])
    cleaned = clean_km_series(s)
    assert cleaned.iloc[0] == 145.0
    assert pytest.approx(cleaned.iloc[1], 0.01) == 639.3
    assert np.isnan(cleaned.iloc[2])  # Preserva nulo
    assert np.isnan(cleaned.iloc[3])  # Inválido vira NaN
    assert pytest.approx(cleaned.iloc[4], 0.01) == 174.4
    assert np.isnan(cleaned.iloc[5])  # Negativo vira NaN
    assert np.isnan(cleaned.iloc[6])  # Acima de 1500 vira NaN


def test_clean_coordinate_series():
    lats = pd.Series(["-27,08476806", "0,0", "-15.5", "50.0", None])
    cleaned_lat = clean_coordinate_series(lats, "latitude")
    assert pytest.approx(cleaned_lat.iloc[0], 0.0001) == -27.08476806
    # 0.0 é tecnicamente no Equador (dentro de -34 a +5.5), mas latitude 50.0 está fora do Brasil
    assert pytest.approx(cleaned_lat.iloc[2], 0.01) == -15.5
    assert np.isnan(cleaned_lat.iloc[3])  # Fora do Brasil
    assert np.isnan(cleaned_lat.iloc[4])


def test_fase_dia_standardization():
    assert standardize_fase_dia("Pleno dia") == "Pleno dia"
    assert standardize_fase_dia("pleno dia") == "Pleno dia"
    assert standardize_fase_dia("Plena Noite") == "Plena Noite"
    assert standardize_fase_dia("Anoitecer") == "Anoitecer"
    assert standardize_fase_dia("Amanhecer") == "Amanhecer"

    assert get_fase_dia_agrupada("Pleno dia") == "Diurno"
    assert get_fase_dia_agrupada("Plena Noite") == "Noturno"
    assert get_fase_dia_agrupada("Anoitecer") == "Crepúsculo"
    assert get_fase_dia_agrupada("Amanhecer") == "Crepúsculo"


def test_process_raw_dataframe_deduplication():
    # Simula base PRF com 1 ocorrência repetida para 2 pessoas e 2 causas (4 linhas)
    raw_data = {
        "id": [1001, 1001, 1001, 1001],
        "pesid": [501, 501, 502, 502],
        "data_inversa": ["2026-03-15"] * 4,
        "uf": ["SC"] * 4,
        "br": ["101"] * 4,
        "km": ["145,5"] * 4,
        "latitude": ["-27,08"] * 4,
        "longitude": ["-48,60"] * 4,
        "fase_dia": ["Plena Noite"] * 4,
        "causa_acidente": ["Reação tardia", "Velocidade incompatível", "Reação tardia", "Velocidade incompatível"],
        "estado_fisico": ["Óbito", "Óbito", "Lesões Graves", "Lesões Graves"],
        "mortos": [1.0, 1.0, 0.0, 0.0],
        "feridos_graves": [0.0, 0.0, 1.0, 1.0],
        "feridos_leves": [0.0, 0.0, 0.0, 0.0],
        "ilesos": [0.0, 0.0, 0.0, 0.0],
    }
    raw_df = pd.DataFrame(raw_data)

    ocorrencias, pessoas, veiculos, causas, quality = process_raw_dataframe(raw_df, "teste_sintetico")

    # Deve ter exatamente 1 ocorrência desduplicada
    assert len(ocorrencias) == 1
    # 1 pessoa morreu, 1 pessoa ferida gravemente
    assert ocorrencias["mortos"].iloc[0] == 1
    assert ocorrencias["feridos_graves"].iloc[0] == 1
    assert ocorrencias["total_vitimas"].iloc[0] == 2
    assert ocorrencias["acidente_fatal"].iloc[0] == 1

    # Tabela de pessoas: 2 pessoas únicas (501 e 502)
    assert len(pessoas) == 2
    assert set(pessoas["pesid"]) == {501, 502}

    # KM deve ser float 145.5, não 0.0
    assert pytest.approx(ocorrencias["km"].iloc[0], 0.01) == 145.5

    # Tabela de causas deve ter 2 causas distintas associadas ao ID 1001
    assert len(causas) == 2
    assert set(causas["causa_acidente"]) == {"Reação tardia", "Velocidade incompatível"}

    # Resumo de qualidade
    assert quality["registros_brutos"] == 4
    assert quality["ocorrencias_unicas"] == 1
    assert quality["desdobramentos_consolidados"] == 3
    assert quality["duplicatas_linhas_evitadas"] == 3


def test_missing_km_audit_tracking():
    """
    Testa a rastreabilidade exata de ocorrências sem KM, replicando a matemática
    auditada de ocorrências sem quilômetro e compatibilidade com return_relational=False.
    """
    raw_data = {
        "id": [101, 102, 103, 103],  # 103 duplicado em pessoas
        "pesid": [1, 2, 3, 4],
        "data_inversa": ["2025-01-01"] * 4,
        "uf": ["SP", "MG", "PR", "PR"],
        "br": ["116", "381", "277", "277"],
        "km": [None, "50,2", "120,0", "120,0"],  # id 101 tem KM nulo
        "fase_dia": ["Plena Noite"] * 4,
        "causa_acidente": ["Falta de Atenção"] * 4,
    }
    raw_df = pd.DataFrame(raw_data)
    # Testa modo legado return_relational=False
    ocorrencias, causas, quality = process_raw_dataframe(raw_df, "teste_km", return_relational=False)

    assert quality["registros_brutos"] == 4
    assert quality["ocorrencias_unicas"] == 3
    assert quality["duplicatas_linhas_evitadas"] == 1  # 4 - 3 = 1
    assert quality["desdobramentos_consolidados"] == 1
    assert quality["ocorrencias_sem_km"] == 1          # 101 tem KM nulo
    assert quality["ocorrencias_com_km"] == 2          # 102 e 103

    # Ocorrência sem KM não pode ter virado KM 0.0
    sem_km = ocorrencias[ocorrencias["id"] == 101]
    assert len(sem_km) == 1
    assert pd.isna(sem_km["km"].iloc[0])


def test_clean_age_series_and_brackets():
    """
    Testa a limpeza rigorosa de idades:
    - Idades válidas entre 0 e 110 anos;
    - Idades > 110 anos tratadas como inconsistentes (sem converter para 0);
    - Idades ausentes/nulas tratadas como 'Não informada / Inconsistente'.
    """
    from data_loader import clean_age_series

    idades = pd.Series([0, 15, 22, 30, 45, 60, 75, 110, 115, 140, None, np.nan, "inválido"])
    limpa, faixas, flags = clean_age_series(idades)

    # 115, 140, None, np.nan, 'inválido' não são válidas
    assert flags.iloc[0] == True   # 0 anos (bebê)
    assert flags.iloc[7] == True   # 110 anos
    assert flags.iloc[8] == False  # 115 anos (> 110)
    assert flags.iloc[9] == False  # 140 anos (> 110)
    assert flags.iloc[10] == False # None
    assert flags.iloc[11] == False # NaN

    assert pd.isna(limpa.iloc[8])  # Preserva NaN, não converte para 0!
    assert pd.isna(limpa.iloc[10]) # Preserva NaN, não converte para 0!

    assert faixas.iloc[0] == "0 a 17 anos"
    assert faixas.iloc[1] == "0 a 17 anos"
    assert faixas.iloc[2] == "18 a 24 anos"
    assert faixas.iloc[3] == "25 a 34 anos"
    assert faixas.iloc[4] == "35 a 49 anos"
    assert faixas.iloc[5] == "50 a 64 anos"
    assert faixas.iloc[6] == "65 anos ou mais"
    assert faixas.iloc[7] == "65 anos ou mais"
    assert faixas.iloc[8] == "Não informada / Inconsistente"
    assert faixas.iloc[9] == "Não informada / Inconsistente"
    assert faixas.iloc[10] == "Não informada / Inconsistente"


def test_audited_classification_when_death_present():
    """
    Testa se uma ocorrência com mortos > 0 mas classificacao_acidente ausente
    (como os casos reais ID 652519 e 742921) é identificada como fatal auditada.
    """
    raw_data = {
        "id": [9999],
        "pesid": [8888],
        "data_inversa": ["2025-05-10"],
        "uf": ["GO"],
        "br": ["060"],
        "km": ["100,0"],
        "fase_dia": ["Plena Noite"],
        "causa_acidente": ["Reação tardia"],
        "mortos": [1],
        "feridos_graves": [0],
        "feridos_leves": [0],
        "ilesos": [0],
        "classificacao_acidente": [None],  # Ausente no boletim
    }
    raw_df = pd.DataFrame(raw_data)
    ocorrencias, pessoas, veiculos, causas, quality = process_raw_dataframe(raw_df, "teste_classificacao")

    assert ocorrencias["mortos"].iloc[0] == 1
    assert ocorrencias["acidente_fatal"].iloc[0] == 1
    assert ocorrencias["classificacao_acidente"].iloc[0] == "Com Vítimas Fatais (Auditada)"
    assert len(quality["divergencias_classificacao"]) == 1
    assert quality["divergencias_classificacao"][0]["id"] == 9999



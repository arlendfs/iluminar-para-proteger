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

    ocorrencias, causas, quality = process_raw_dataframe(raw_df, "teste_sintetico")

    # Deve ter exatamente 1 ocorrência desduplicada
    assert len(ocorrencias) == 1
    # 1 pessoa morreu, 1 pessoa ferida gravemente
    assert ocorrencias["mortos"].iloc[0] == 1
    assert ocorrencias["feridos_graves"].iloc[0] == 1
    assert ocorrencias["total_vitimas"].iloc[0] == 2
    assert ocorrencias["acidente_fatal"].iloc[0] == 1

    # KM deve ser float 145.5, não 0.0
    assert pytest.approx(ocorrencias["km"].iloc[0], 0.01) == 145.5

    # Tabela de causas deve ter 2 causas distintas associadas ao ID 1001
    assert len(causas) == 2
    assert set(causas["causa_acidente"]) == {"Reação tardia", "Velocidade incompatível"}

    # Resumo de qualidade
    assert quality["registros_brutos"] == 4
    assert quality["ocorrencias_unicas"] == 1
    assert quality["duplicatas_linhas_evitadas"] == 3


"""
Testes automatizados para a geração do relatório PDF.
"""

import pytest
import pandas as pd
import numpy as np
from pdf_generator import ReportGenerator


def test_pdf_generation_complete():
    generator = ReportGenerator()

    # Base sintética para o relatório
    df_ocorrencias = pd.DataFrame({
        "id": range(1, 101),
        "ano": [2026] * 100,
        "ano_mes": ["2026-01"] * 50 + ["2026-02"] * 50,
        "uf": ["SC"] * 60 + ["PR"] * 40,
        "br": ["101"] * 60 + ["376"] * 40,
        "km": [145.0 + (i * 0.1) for i in range(100)],
        "latitude": [-27.0 - (i * 0.01) for i in range(100)],
        "longitude": [-48.0 - (i * 0.01) for i in range(100)],
        "fase_dia_oficial": ["Plena Noite"] * 45 + ["Pleno dia"] * 45 + ["Anoitecer"] * 10,
        "fase_dia_agrupada": ["Noturno"] * 45 + ["Diurno"] * 45 + ["Crepúsculo"] * 10,
        "mortos": [1] * 10 + [0] * 90,
        "feridos_graves": [1] * 20 + [0] * 80,
        "feridos_leves": [2] * 40 + [0] * 60,
        "total_feridos": [3] * 20 + [2] * 20 + [0] * 60,
        "total_vitimas": [4] * 10 + [3] * 10 + [2] * 20 + [0] * 60,
        "acidente_fatal": [1] * 10 + [0] * 90,
    })

    df_causas = pd.DataFrame({
        "id": list(range(1, 101)),
        "causa_acidente": ["Reação tardia ou ineficiente do condutor"] * 40 + ["Velocidade Incompatível"] * 30 + ["Condutor Dormindo"] * 30,
    })

    top_segments = pd.DataFrame({
        "trecho_id": [f"BR-101 (SC) KM {i*2}.0 - {i*2+2}.0" for i in range(10)],
        "n_acidentes_noturnos": [15, 12, 10, 8, 7, 6, 5, 4, 3, 2],
        "mortos_noturno": [3, 2, 1, 1, 0, 0, 0, 0, 0, 0],
        "total_feridos_noturno": [10, 8, 7, 5, 4, 3, 2, 2, 1, 1],
        "score_iluminacao_solar": [45.0, 35.0, 28.0, 22.0, 18.0, 15.0, 12.0, 10.0, 8.0, 6.0],
        "confiabilidade_geo": ["Alta (100%)"] * 10,
    })

    financial_summary = {
        "investimento_total": 6000000.0,
        "economia_anual": 2500000.0,
        "economia_liquida_anual": 2300000.0,
        "vpl": 12000000.0,
        "tir": 0.28,
        "payback_simples_anos": 2.6,
        "roi_descontado_pct": 200.0,
        "vidas_salvas_ano": 1.5,
        "cenarios": {
            "conservador": {"nome": "Conservador", "taxa_reducao": 0.2, "vidas_salvas_ano": 0.8, "beneficio_anual_bruto": 1400000.0, "vpl": 5000000.0, "payback_simples": 4.5},
            "intermediario": {"nome": "Intermediário", "taxa_reducao": 0.35, "vidas_salvas_ano": 1.5, "beneficio_anual_bruto": 2500000.0, "vpl": 12000000.0, "payback_simples": 2.6},
            "otimista": {"nome": "Otimista", "taxa_reducao": 0.5, "vidas_salvas_ano": 2.2, "beneficio_anual_bruto": 3600000.0, "vpl": 19000000.0, "payback_simples": 1.8},
        }
    }

    pdf_buffer = generator.generate_accident_analysis_report(
        filtered_data=df_ocorrencias,
        top_segments=top_segments,
        causas_df=df_causas,
        financial_summary=financial_summary,
    )

    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 5000  # O PDF gerado tem conteúdo substancial
    assert pdf_bytes.startswith(b"%PDF")  # Cabeçalho válido de arquivo PDF


def test_pdf_generation_with_demographics_and_fleet():
    """
    Testa a compilação do PDF completo com as tabelas de pessoas (envolvimento, idade, sexo)
    e frota veicular.
    """
    generator = ReportGenerator()

    df_ocorrencias = pd.DataFrame({
        "id": [1, 2],
        "ano": [2025, 2025],
        "ano_mes": ["2025-03", "2025-03"],
        "uf": ["PR", "SC"],
        "br": ["277", "101"],
        "km": [10.0, 50.0],
        "latitude": [-25.4, -27.1],
        "longitude": [-49.2, -48.6],
        "fase_dia_oficial": ["Plena Noite", "Pleno dia"],
        "fase_dia_agrupada": ["Noturno", "Diurno"],
        "mortos": [1, 0],
        "feridos_graves": [1, 0],
        "feridos_leves": [0, 1],
        "total_feridos": [1, 1],
        "total_vitimas": [2, 1],
        "acidente_fatal": [1, 0],
    })

    df_pessoas = pd.DataFrame({
        "id": [1, 1, 2],
        "pesid": [101, 102, 201],
        "tipo_envolvido": ["Pedestre", "Condutor", "Passageiro"],
        "sexo": ["Masculino", "Masculino", "Feminino"],
        "faixa_etaria": ["65 anos ou mais", "35 a 49 anos", "18 a 24 anos"],
        "idade": [70, 40, 22],
        "idade_valida_flag": [True, True, True],
        "mortos": [1, 0, 0],
        "feridos_graves": [0, 1, 0],
        "feridos_leves": [0, 0, 1],
        "ilesos": [0, 0, 0],
    })

    df_veiculos = pd.DataFrame({
        "id": [1, 2],
        "id_veiculo": [1, 2],
        "tipo_veiculo": ["Automóvel", "Motocicleta"],
    })

    top_segments = pd.DataFrame({
        "trecho_id": ["BR-277 (PR) KM 10.0 - 12.0"],
        "n_acidentes_noturnos": [5],
        "mortos_noturno": [1],
        "feridos_graves_noturno": [1],
        "total_feridos_noturno": [2],
        "score_iluminacao_solar": [20.0],
    })

    financial_summary = {
        "investimento_total": 600000.0,
        "economia_anual": 250000.0,
        "economia_liquida_anual": 230000.0,
        "vpl": 1200000.0,
        "tir": 0.28,
        "payback_simples_anos": 2.6,
        "vidas_salvas_ano": 0.35,
        "cenarios": {},
    }

    quality_summary = {
        "registros_brutos": 6,
        "ocorrencias_unicas": 2,
        "desdobramentos_consolidados": 4,
        "duplicatas_linhas_evitadas": 4,
        "ocorrencias_com_km": 2,
        "ocorrencias_sem_km": 0,
        "mortos_sem_km": 0,
        "feridos_sem_km": 0,
        "pessoas_unicas_pesid": 3,
    }

    pdf_buffer = generator.generate_accident_analysis_report(
        filtered_data=df_ocorrencias,
        top_segments=top_segments,
        pessoas_df=df_pessoas,
        veiculos_df=df_veiculos,
        financial_summary=financial_summary,
        quality_summary=quality_summary,
    )

    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 5000
    assert pdf_bytes.startswith(b"%PDF")


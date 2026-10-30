"""
Testes Automatizados para o Módulo de Análise Demográfica, Frota Veicular e Filtros Relacionais.
Cobre casos sintéticos rigorosos para garantir integridade e ausência de contaminação cruzada.
"""

import pytest
import pandas as pd
import numpy as np
from data_loader import process_raw_dataframe, clean_age_series
from demographic_analysis import (
    compute_envolvimento_analysis,
    compute_sexo_analysis,
    compute_faixa_etaria_analysis,
    compute_veiculo_analysis,
    compute_tipo_acidente_analysis,
)
from analyzer import AccidentAnalyzer


def test_synthetic_accident_with_multiple_people_and_causes():
    """
    Cenário Sintético 1:
    1 único acidente (ID 10) envolvendo 5 pessoas (1 Condutor, 3 Passageiros, 1 Pedestre),
    2 veículos, e 2 causas registradas no boletim.
    Vítimas: 1 pedestre morto, 1 passageiro morto, 1 motorista ferido grave, 1 passageiro ferido leve, 1 passageiro ileso.
    Total: 2 mortos, 1 ferido grave, 1 ferido leve, 1 ileso = 5 pessoas envolvidas, 4 vítimas.
    Como há 2 causas, cada pessoa gera 2 linhas brutas = 10 linhas brutas.
    """
    raw_rows = []
    # Pessoas: pesid 101 a 105
    people_specs = [
        {"pesid": 101, "tipo_envolvido": "Condutor", "sexo": "Masculino", "idade": 35, "id_veiculo": 1, "tipo_veiculo": "Automóvel", "mortos": 0, "feridos_graves": 1, "feridos_leves": 0, "ilesos": 0, "estado_fisico": "Lesões Graves"},
        {"pesid": 102, "tipo_envolvido": "Passageiro", "sexo": "Feminino", "idade": 30, "id_veiculo": 1, "tipo_veiculo": "Automóvel", "mortos": 1, "feridos_graves": 0, "feridos_leves": 0, "ilesos": 0, "estado_fisico": "Óbito"},
        {"pesid": 103, "tipo_envolvido": "Passageiro", "sexo": "Masculino", "idade": 8, "id_veiculo": 1, "tipo_veiculo": "Automóvel", "mortos": 0, "feridos_graves": 0, "feridos_leves": 1, "ilesos": 0, "estado_fisico": "Lesões Leves"},
        {"pesid": 104, "tipo_envolvido": "Passageiro", "sexo": "Feminino", "idade": 65, "id_veiculo": 1, "tipo_veiculo": "Automóvel", "mortos": 0, "feridos_graves": 0, "feridos_leves": 0, "ilesos": 1, "estado_fisico": "Ileso"},
        {"pesid": 105, "tipo_envolvido": "Pedestre", "sexo": "Masculino", "idade": 72, "id_veiculo": None, "tipo_veiculo": None, "mortos": 1, "feridos_graves": 0, "feridos_leves": 0, "ilesos": 0, "estado_fisico": "Óbito"},
    ]

    causas = ["Reação tardia ou ineficiente do condutor", "Ausência de reação do condutor"]

    for p in people_specs:
        for c in causas:
            raw_rows.append({
                "id": 10,
                "pesid": p["pesid"],
                "data_inversa": "2025-06-20",
                "uf": "PR",
                "br": "277",
                "km": "100,0",
                "fase_dia": "Plena Noite",
                "condicao_metereologica": "Céu Claro",
                "tipo_acidente": "Atropelamento de Pedestre",
                "causa_acidente": c,
                "tipo_envolvido": p["tipo_envolvido"],
                "sexo": p["sexo"],
                "idade": p["idade"],
                "id_veiculo": p["id_veiculo"],
                "tipo_veiculo": p["tipo_veiculo"],
                "mortos": p["mortos"],
                "feridos_graves": p["feridos_graves"],
                "feridos_leves": p["feridos_leves"],
                "ilesos": p["ilesos"],
                "estado_fisico": p["estado_fisico"],
            })

    raw_df = pd.DataFrame(raw_rows)
    assert len(raw_df) == 10  # 10 linhas brutas

    # 1. Processamento e desdobramentos
    ocorrencias, pessoas, veiculos, causas_df, quality = process_raw_dataframe(raw_df, "teste_multiplo")

    # Ocorrência única:
    assert len(ocorrencias) == 1
    assert quality["registros_brutos"] == 10
    assert quality["ocorrencias_unicas"] == 1
    assert quality["desdobramentos_consolidados"] == 9
    assert ocorrencias["mortos"].iloc[0] == 2
    assert ocorrencias["feridos_graves"].iloc[0] == 1
    assert ocorrencias["feridos_leves"].iloc[0] == 1
    assert ocorrencias["total_feridos"].iloc[0] == 2
    assert ocorrencias["ilesos"].iloc[0] == 1
    assert ocorrencias["total_vitimas"].iloc[0] == 4
    assert ocorrencias["acidente_fatal"].iloc[0] == 1

    # Pessoas únicas: 5 pessoas
    assert len(pessoas) == 5
    assert pessoas["mortos"].sum() == 2
    assert pessoas["feridos_graves"].sum() == 1
    assert pessoas["feridos_leves"].sum() == 1
    assert pessoas["ilesos"].sum() == 1

    # Causas únicas: 2 causas
    assert len(causas_df) == 2

    # Veículos únicos: 1 veículo
    assert len(veiculos) == 1

    # 2. Análise de Envolvimento
    res_env = compute_envolvimento_analysis(pessoas)
    tbl_env = res_env["resumo_envolvimento"]
    pedestre_row = tbl_env[tbl_env["tipo_envolvido"] == "Pedestre"].iloc[0]
    assert pedestre_row["total_envolvidos"] == 1
    assert pedestre_row["mortos"] == 1
    assert pedestre_row["taxa_mortalidade_pct"] == 100.0

    passageiro_row = tbl_env[tbl_env["tipo_envolvido"] == "Passageiro"].iloc[0]
    assert passageiro_row["total_envolvidos"] == 3
    assert passageiro_row["mortos"] == 1
    assert passageiro_row["taxa_mortalidade_pct"] == pytest.approx(33.33, 0.01)

    condutor_row = tbl_env[tbl_env["tipo_envolvido"] == "Condutor"].iloc[0]
    assert condutor_row["total_envolvidos"] == 1
    assert condutor_row["mortos"] == 0
    assert condutor_row["feridos_graves"] == 1

    # 3. Análise de Faixa Etária
    res_faixa = compute_faixa_etaria_analysis(pessoas)
    tbl_faixa = res_faixa["resumo_faixa_etaria"]
    # 8 anos -> 0 a 17 anos (ileso=0, leves=1, mortos=0)
    row_crianca = tbl_faixa[tbl_faixa["faixa_etaria"] == "0 a 17 anos"].iloc[0]
    assert row_crianca["total_pessoas"] == 1
    assert row_crianca["feridos_leves"] == 1

    # 65 e 72 anos -> 65 anos ou mais (2 pessoas, 1 morta, 1 ilesa)
    row_idoso = tbl_faixa[tbl_faixa["faixa_etaria"] == "65 anos ou mais"].iloc[0]
    assert row_idoso["total_pessoas"] == 2
    assert row_idoso["mortos"] == 1
    assert row_idoso["ilesos"] == 1

    # 4. Análise de Sexo
    res_sexo = compute_sexo_analysis(pessoas)
    tbl_sexo = res_sexo["resumo_sexo"]
    masc_row = tbl_sexo[tbl_sexo["sexo"] == "Masculino"].iloc[0]
    fem_row = tbl_sexo[tbl_sexo["sexo"] == "Feminino"].iloc[0]
    assert masc_row["total_pessoas"] == 3  # 101 (condutor), 103 (criança), 105 (pedestre)
    assert masc_row["mortos"] == 1         # pedestre
    assert fem_row["total_pessoas"] == 2   # 102 (passageira), 104 (idosa)
    assert fem_row["mortos"] == 1          # passageira 102


def test_demographic_filter_isolation_no_victim_contamination():
    """
    Testa se ao filtrar por 'Pedestre', as mortes de ocupantes do mesmo veículo
    NÃO são atribuídas aos pedestres.
    """
    analyzer = AccidentAnalyzer()
    raw_data = {
        "id": [1, 1],
        "pesid": [10, 20],
        "data_inversa": ["2025-01-01", "2025-01-01"],
        "uf": ["SP", "SP"],
        "br": ["116", "116"],
        "km": ["10,0", "10,0"],
        "fase_dia": ["Plena Noite", "Plena Noite"],
        "causa_acidente": ["Falta de Atenção", "Falta de Atenção"],
        "tipo_envolvido": ["Passageiro", "Pedestre"],
        "sexo": ["Feminino", "Masculino"],
        "idade": [25, 40],
        "mortos": [1, 0],              # Passageiro morreu, pedestre NÃO morreu!
        "feridos_graves": [0, 1],       # Pedestre ferido grave
        "feridos_leves": [0, 0],
        "ilesos": [0, 0],
        "estado_fisico": ["Óbito", "Lesões Graves"],
    }
    raw_df = pd.DataFrame(raw_data)
    ocorrencias, pessoas, veiculos, causas, quality = process_raw_dataframe(raw_df, "teste_filtro")

    analyzer.data = ocorrencias
    analyzer.pessoas_data = pessoas
    analyzer.veiculos_data = veiculos
    analyzer.causas_data = causas
    analyzer.quality_summary = quality

    # Filtra exclusivamente por PEDESTRE
    filtros = {"tipos_envolvido": ["Pedestre"]}
    filtered_df = analyzer.apply_filters(analyzer.data, filtros)

    # Ocorrência deve ser mantida (o sinistro envolveu pedestre)
    assert len(filtered_df) == 1
    # MAS as mortes do grupo filtrado devem ser ZERO (pois quem morreu foi o passageiro!)
    assert filtered_df["mortos"].iloc[0] == 0
    assert filtered_df["feridos_graves"].iloc[0] == 1
    assert filtered_df["acidente_fatal"].iloc[0] == 0

    # As pessoas filtradas contêm apenas o pedestre
    assert len(analyzer.filtered_pessoas) == 1
    assert analyzer.filtered_pessoas["tipo_envolvido"].iloc[0] == "Pedestre"
    assert analyzer.filtered_pessoas["mortos"].iloc[0] == 0


def test_invalid_and_extreme_ages():
    """
    Testa idades inválidas (>110 e ausentes) e confirma que não viram 0.
    """
    raw_data = {
        "id": [1, 2, 3],
        "pesid": [11, 22, 33],
        "data_inversa": ["2025-01-01"] * 3,
        "uf": ["MG"] * 3,
        "br": ["381"] * 3,
        "km": ["50,0"] * 3,
        "fase_dia": ["Plena Noite"] * 3,
        "causa_acidente": ["Velocidade Incompatível"] * 3,
        "idade": [140, None, 25],
        "mortos": [0, 0, 0],
        "feridos_graves": [0, 0, 0],
        "feridos_leves": [1, 1, 1],
        "ilesos": [0, 0, 0],
    }
    raw_df = pd.DataFrame(raw_data)
    ocorrencias, pessoas, veiculos, causas, quality = process_raw_dataframe(raw_df, "teste_idades")

    assert quality["idades_validas"] == 1
    assert quality["idades_inconsistentes_ou_ausentes"] == 2
    assert quality["idades_superiores_110_anos"] == 1

    p140 = pessoas[pessoas["pesid"] == 11].iloc[0]
    assert p140["faixa_etaria"] == "Não informada / Inconsistente"
    assert pd.isna(p140["idade_limpa"])
    assert p140["idade_valida_flag"] == False

    p_nan = pessoas[pessoas["pesid"] == 22].iloc[0]
    assert p_nan["faixa_etaria"] == "Não informada / Inconsistente"
    assert pd.isna(p_nan["idade_limpa"])


def test_missing_pesid_handling():
    """
    Testa linhas brutas sem pesid (não associadas a pessoa específica).
    Confirma que a ocorrência e causa são preservadas e a contagem de sem pesid é registrada.
    """
    raw_data = {
        "id": [1, 1],
        "pesid": [100, None],  # Uma linha com pesid, outra sem
        "data_inversa": ["2025-01-01", "2025-01-01"],
        "uf": ["RJ", "RJ"],
        "br": ["101", "101"],
        "km": ["20,0", "20,0"],
        "fase_dia": ["Plena Noite", "Plena Noite"],
        "causa_acidente": ["Defeito mecânico", "Outra"],
        "mortos": [0, 0],
        "feridos_graves": [1, 0],
        "feridos_leves": [0, 0],
        "ilesos": [0, 0],
    }
    raw_df = pd.DataFrame(raw_data)
    ocorrencias, pessoas, veiculos, causas, quality = process_raw_dataframe(raw_df, "teste_sem_pesid")

    assert len(ocorrencias) == 1
    assert len(pessoas) == 1  # Apenas a pessoa válida é indexada na tabela de pessoas
    assert quality["linhas_sem_pesid"] == 1
    assert len(causas) == 2   # Ambas as causas são preservadas


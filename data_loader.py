"""
Módulo de Ingestão, Validação e Qualidade de Dados.
Responsável por carregar CSV e Parquet, tratar decimais brasileiros,
desduplicar ocorrências e gerar relatório de qualidade de dados.
"""

import os
import re
import gc
from typing import Tuple, Dict, Any, Optional, List, Union
import pandas as pd
import numpy as np
from config import (
    COLUMN_MAPPING,
    VALIDATION_RULES,
    FASES_DIA_OFICIAIS,
    VALUE_STANDARDIZATION,
    FAIXAS_ETARIAS_ORDEM,
    TIPOS_ENVOLVIDO_PADRAO,
)


def clean_brazilian_float(val: Any) -> Optional[float]:
    """
    Converte valores numéricos no formato brasileiro (com vírgula)
    ou internacional (com ponto) para float.
    Retorna None se for nulo, vazio ou inválido.
    NÃO converte nulos para zero.
    """
    if pd.isna(val):
        return None
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "", "n/a", "<na>"):
        return None
    # Substituir vírgula por ponto
    s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def clean_km_series(series: pd.Series) -> pd.Series:
    """
    Limpa uma série de KM preservando valores nulos como NaN.
    Valida limites razoáveis de rodovia federal (0 a 1500 km).
    Vetorizado para altíssima performance e baixo consumo de memória.
    """
    if series.dtype == "object":
        s = series.astype(str).str.strip().str.replace(",", ".", regex=False)
        cleaned = pd.to_numeric(s, errors="coerce")
    else:
        cleaned = pd.to_numeric(series, errors="coerce")
    min_km = VALIDATION_RULES["km"]["min"]
    max_km = VALIDATION_RULES["km"]["max"]
    cleaned = cleaned.where((cleaned >= min_km) & (cleaned <= max_km), np.nan)
    return cleaned.astype("float32")


def clean_coordinate_series(series: pd.Series, coord_type: str) -> pd.Series:
    """
    Limpa latitudes ou longitudes tratando vírgulas decimais
    e validando os limites geográficos do Brasil.
    Não converte nulos para (0, 0).
    Vetorizado para altíssima performance e baixo consumo de memória.
    """
    if series.dtype == "object":
        s = series.astype(str).str.strip().str.replace(",", ".", regex=False)
        cleaned = pd.to_numeric(s, errors="coerce")
    else:
        cleaned = pd.to_numeric(series, errors="coerce")
    min_val = VALIDATION_RULES[coord_type]["min"]
    max_val = VALIDATION_RULES[coord_type]["max"]
    cleaned = cleaned.where((cleaned >= min_val) & (cleaned <= max_val), np.nan)
    return cleaned.astype("float32")


def clean_age_series(series: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Processa a coluna de idade dos envolvidos com validação epidemiológica:
    - Idades válidas: 0 <= idade <= 110 anos.
    - Idades ausentes ou superiores a 110 anos (erros de digitação, ex: 1985, 2020)
      NÃO são convertidas para zero, pois 0 representa bebês < 1 ano.
    - Retorna tupla:
        - idade_limpa: pd.Series float com NaN para inválidas.
        - faixa_etaria: pd.Series com categorias demográficas padronizadas.
        - idade_valida_flag: pd.Series booleana (True para 0 <= idade <= 110).
    """
    num_series = pd.to_numeric(series.apply(clean_brazilian_float), errors="coerce")
    idade_valida_flag = num_series.notna() & (num_series >= 0) & (num_series <= 110)
    idade_limpa = num_series.where(idade_valida_flag, np.nan)

    # Atribuição vetorizada das faixas etárias
    condicoes = [
        idade_valida_flag & (idade_limpa < 18),
        idade_valida_flag & (idade_limpa >= 18) & (idade_limpa <= 24),
        idade_valida_flag & (idade_limpa >= 25) & (idade_limpa <= 34),
        idade_valida_flag & (idade_limpa >= 35) & (idade_limpa <= 49),
        idade_valida_flag & (idade_limpa >= 50) & (idade_limpa <= 64),
        idade_valida_flag & (idade_limpa >= 65),
    ]
    escolhas = [
        "0 a 17 anos",
        "18 a 24 anos",
        "25 a 34 anos",
        "35 a 49 anos",
        "50 a 64 anos",
        "65 anos ou mais",
    ]
    faixa_etaria = pd.Series(
        np.select(condicoes, escolhas, default="Não informada / Inconsistente"),
        index=series.index,
    )

    return idade_limpa, faixa_etaria, idade_valida_flag


def clean_tipo_envolvido_series(series: pd.Series) -> pd.Series:
    """
    Normaliza a categoria de envolvimento dos ocupantes / pedestres.
    """
    def _norm(val):
        if pd.isna(val):
            return "Não informado"
        s = str(val).strip().lower()
        if "condutor" in s:
            return "Condutor"
        if "passageir" in s:
            return "Passageiro"
        if "pedestre" in s:
            return "Pedestre"
        if "cavaleir" in s:
            return "Cavaleiro"
        if "testemunha" in s:
            return "Testemunha"
        return str(val).strip().title()

    return series.apply(_norm)


def clean_sexo_series(series: pd.Series) -> pd.Series:
    """
    Normaliza sexo para Masculino, Feminino ou Não informado / Ignorado.
    """
    def _norm(val):
        if pd.isna(val):
            return "Não informado / Ignorado"
        s = str(val).strip().lower()
        if s in ["masculino", "m"]:
            return "Masculino"
        if s in ["feminino", "f"]:
            return "Feminino"
        return "Não informado / Ignorado"

    return series.apply(_norm)


def clean_estado_fisico_series(series: pd.Series) -> pd.Series:
    """
    Normaliza o estado físico das vítimas da PRF.
    """
    def _norm(val):
        if pd.isna(val):
            return "Não Informado"
        s = str(val).strip().lower()
        if "obito" in s or "óbito" in s or "mort" in s or "bito" in s or "\xf3bito" in s:
            return "Óbito"
        if "grave" in s:
            return "Lesões Graves"
        if "leve" in s:
            return "Lesões Leves"
        if "ileso" in s:
            return "Ileso"
        return "Não Informado"

    return series.apply(_norm)


def clean_tipo_veiculo_series(series: pd.Series) -> pd.Series:
    """
    Normaliza o tipo de veículo envolvido.
    """
    def _norm(val):
        if pd.isna(val):
            return "Não informado"
        s = str(val).strip().title()
        return s

    return series.apply(_norm)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza os nomes das colunas de acordo com COLUMN_MAPPING.
    """
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.lower()
        .str.strip()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
    for standard_col, aliases in COLUMN_MAPPING.items():
        if standard_col not in df.columns:
            for alias in aliases:
                norm_alias = alias.lower().strip().replace(" ", "_").replace("-", "_")
                if norm_alias in df.columns:
                    df.rename(columns={norm_alias: standard_col}, inplace=True)
                    break
    return df


def standardize_fase_dia(val: Any) -> str:
    """
    Normaliza a fase do dia preservando as 4 categorias oficiais da PRF:
    'Pleno dia', 'Plena Noite', 'Anoitecer', 'Amanhecer'.
    """
    if pd.isna(val):
        return "Não informado"
    s = str(val).strip().lower()
    if "pleno dia" in s or (s in ["dia", "diurno", "manhã", "tarde", "manha"]):
        return "Pleno dia"
    if "plena noite" in s or (s in ["noite", "noturno", "madrugada"]):
        return "Plena Noite"
    if "anoitecer" in s or "crepúsculo vespertino" in s:
        return "Anoitecer"
    if "amanhecer" in s or "crepúsculo matutino" in s or "alvorada" in s:
        return "Amanhecer"
    return str(val).strip().title()


def get_fase_dia_agrupada(fase_original: str) -> str:
    """
    Retorna a classificação agregada: 'Diurno', 'Noturno' ou 'Crepúsculo'.
    """
    if fase_original == "Pleno dia":
        return "Diurno"
    elif fase_original == "Plena Noite":
        return "Noturno"
    elif fase_original in ("Anoitecer", "Amanhecer"):
        return "Crepúsculo"
    return "Outro"


def process_raw_dataframe(
    raw_df: pd.DataFrame,
    source_name: str = "",
    return_relational: bool = True,
) -> Any:
    """
    Processa o DataFrame bruto da PRF preservando a granularidade relacional:
    1. Tabela de Ocorrências: 1 linha por 'id' único.
    2. Tabela de Pessoas: 1 linha por '(id, pesid)', preservando perfil demográfico.
    3. Tabela de Veículos: 1 linha por '(id, id_veiculo)', preservando frota.
    4. Tabela de Causas: todas as causas e tipos de acidentes associados.
    5. Resumo de Qualidade: métricas dinâmicas de integridade, KMs nulos e divergências.

    Se return_relational=True: retorna (ocorrencias, pessoas, veiculos, causas, quality_summary).
    Se return_relational=False: retorna (ocorrencias, causas, quality_summary) para compatibilidade legada.
    """
    df = normalize_column_names(raw_df)
    total_linhas_brutas = len(df)

    # 1. Extrair ano, mês, dia e período
    if "data_inversa" in df.columns:
        df["data_dt"] = pd.to_datetime(df["data_inversa"], errors="coerce")
        df["ano"] = df["data_dt"].dt.year
        df["mes"] = df["data_dt"].dt.month
        df["ano_mes"] = df["data_dt"].dt.to_period("M").astype(str)
        if "dia_semana" not in df.columns:
            dias_semana_pt = {0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira", 3: "quinta-feira", 4: "sexta-feira", 5: "sábado", 6: "domingo"}
            df["dia_semana"] = df["data_dt"].dt.dayofweek.map(dias_semana_pt)
    elif "ano" not in df.columns and source_name:
        m = re.search(r"(20[0-9]{2})", source_name)
        if m:
            df["ano"] = int(m.group(1))

    # 2. Limpeza de KM e Coordenadas
    if "km" in df.columns:
        df["km_limpo"] = clean_km_series(df["km"])
    else:
        df["km_limpo"] = np.nan

    if "latitude" in df.columns:
        df["latitude_limpa"] = clean_coordinate_series(df["latitude"], "latitude")
    else:
        df["latitude_limpa"] = np.nan

    if "longitude" in df.columns:
        df["longitude_limpa"] = clean_coordinate_series(df["longitude"], "longitude")
    else:
        df["longitude_limpa"] = np.nan

    # 3. Normalização de Fase do Dia
    if "fase_dia" in df.columns:
        df["fase_dia_oficial"] = df["fase_dia"].apply(standardize_fase_dia)
        df["fase_dia_agrupada"] = df["fase_dia_oficial"].apply(get_fase_dia_agrupada)
    else:
        df["fase_dia_oficial"] = "Não informado"
        df["fase_dia_agrupada"] = "Não informado"

    # 4. Tratar UF e BR
    if "uf" in df.columns:
        df["uf"] = df["uf"].astype(str).str.strip().str.upper()
        df.loc[df["uf"].isin(["NAN", "NONE", "", "NULL"]), "uf"] = np.nan

    if "br" in df.columns:
        def clean_br(v):
            if pd.isna(v):
                return "N/A"
            s = str(v).strip().replace(".0", "")
            return s if s else "N/A"
        df["br"] = df["br"].apply(clean_br)

    tem_id = "id" in df.columns
    if not tem_id:
        df["id"] = np.arange(1, len(df) + 1)

    tem_pesid = "pesid" in df.columns
    total_linhas_sem_pesid = int(df["pesid"].isna().sum()) if tem_pesid else 0

    # =========================================================================
    # TABELA 1: PESSOAS (pessoas_df)
    # =========================================================================
    if tem_pesid:
        pessoas_raw = df.dropna(subset=["pesid"]).drop_duplicates(subset=["id", "pesid"]).copy()
    else:
        pessoas_raw = df.copy()
        pessoas_raw["pesid"] = np.arange(1, len(pessoas_raw) + 1)

    # Limpeza e padronização demográfica de pessoas
    if "idade" in pessoas_raw.columns:
        id_limpa, fx_etaria, id_val_flag = clean_age_series(pessoas_raw["idade"])
        pessoas_raw["idade_limpa"] = id_limpa
        pessoas_raw["faixa_etaria"] = fx_etaria
        pessoas_raw["idade_valida_flag"] = id_val_flag
    else:
        pessoas_raw["idade_limpa"] = np.nan
        pessoas_raw["faixa_etaria"] = "Não informada / Inconsistente"
        pessoas_raw["idade_valida_flag"] = False

    if "tipo_envolvido" in pessoas_raw.columns:
        pessoas_raw["tipo_envolvido"] = clean_tipo_envolvido_series(pessoas_raw["tipo_envolvido"])
    else:
        pessoas_raw["tipo_envolvido"] = "Não informado"

    if "sexo" in pessoas_raw.columns:
        pessoas_raw["sexo"] = clean_sexo_series(pessoas_raw["sexo"])
    else:
        pessoas_raw["sexo"] = "Não informado / Ignorado"

    if "estado_fisico" in pessoas_raw.columns:
        pessoas_raw["estado_fisico"] = clean_estado_fisico_series(pessoas_raw["estado_fisico"])
    else:
        pessoas_raw["estado_fisico"] = "Não Informado"

    if "tipo_veiculo" in pessoas_raw.columns:
        pessoas_raw["tipo_veiculo"] = clean_tipo_veiculo_series(pessoas_raw["tipo_veiculo"])

    # Conversão rigorosa de vítimas por pessoa
    # Se estado_fisico for Óbito ou mortos > 0, pessoa conta como 1 óbito
    for col in ["mortos", "feridos_graves", "feridos_leves", "ilesos"]:
        if col in pessoas_raw.columns:
            pessoas_raw[col] = pd.to_numeric(pessoas_raw[col].apply(clean_brazilian_float), errors="coerce").fillna(0)
        else:
            pessoas_raw[col] = 0.0

    pessoas_raw["mortos"] = ((pessoas_raw["estado_fisico"] == "Óbito") | (pessoas_raw["mortos"] > 0)).astype("uint16")
    pessoas_raw["feridos_graves"] = ((pessoas_raw["estado_fisico"] == "Lesões Graves") | (pessoas_raw["feridos_graves"] > 0)).astype("uint16")
    pessoas_raw["feridos_leves"] = ((pessoas_raw["estado_fisico"] == "Lesões Leves") | (pessoas_raw["feridos_leves"] > 0)).astype("uint16")
    pessoas_raw["ilesos"] = ((pessoas_raw["estado_fisico"] == "Ileso") | (pessoas_raw["ilesos"] > 0)).astype("uint16")
    pessoas_raw["total_feridos"] = (pessoas_raw["feridos_graves"] + pessoas_raw["feridos_leves"]).astype("uint16")
    pessoas_raw["total_vitimas"] = (pessoas_raw["mortos"] + pessoas_raw["total_feridos"]).astype("uint16")

    # Colunas finais da tabela de pessoas
    cols_pessoa = [
        "id", "pesid", "tipo_envolvido", "estado_fisico", "sexo", "idade",
        "idade_limpa", "faixa_etaria", "idade_valida_flag",
        "mortos", "feridos_graves", "feridos_leves", "ilesos", "total_feridos", "total_vitimas",
        "id_veiculo", "tipo_veiculo", "ano", "mes", "uf", "br", "km_limpo",
        "fase_dia_oficial", "fase_dia_agrupada", "condicao_metereologica", "tipo_acidente"
    ]
    cols_existentes_p = [c for c in cols_pessoa if c in pessoas_raw.columns]
    pessoas_df = pessoas_raw[cols_existentes_p].copy()
    pessoas_df["km"] = pessoas_df["km_limpo"] if "km_limpo" in pessoas_df.columns else np.nan

    # =========================================================================
    # TABELA 2: VEÍCULOS (veiculos_df)
    # =========================================================================
    if "id_veiculo" in df.columns:
        veic_validos = df.dropna(subset=["id_veiculo"]).drop_duplicates(subset=["id", "id_veiculo"]).copy()
        if "tipo_veiculo" in veic_validos.columns:
            veic_validos["tipo_veiculo"] = clean_tipo_veiculo_series(veic_validos["tipo_veiculo"])
        cols_veic = ["id", "id_veiculo", "tipo_veiculo", "marca", "ano_fabricacao_veiculo", "uf", "br", "ano", "fase_dia_oficial", "fase_dia_agrupada"]
        cols_existentes_v = [c for c in cols_veic if c in veic_validos.columns]
        veiculos_df = veic_validos[cols_existentes_v].copy()
    else:
        veiculos_df = pd.DataFrame(columns=["id", "id_veiculo", "tipo_veiculo", "marca", "ano_fabricacao_veiculo"])

    # =========================================================================
    # TABELA 3: CAUSAS (causas_df)
    # =========================================================================
    cols_causas = ["id", "causa_acidente", "causa_principal", "ordem_tipo_acidente", "tipo_acidente"]
    cols_causas_existentes = [c for c in cols_causas if c in df.columns]
    if "causa_acidente" in df.columns:
        causas_df = df[cols_causas_existentes].dropna(subset=["causa_acidente"]).drop_duplicates().copy()
    else:
        causas_df = pd.DataFrame(columns=["id", "causa_acidente"])

    # =========================================================================
    # TABELA 4: OCORRÊNCIAS (ocorrencias_df)
    # =========================================================================
    cols_ocorrencia = [
        "id", "data_inversa", "data_dt", "ano", "mes", "ano_mes", "horario", "dia_semana",
        "uf", "br", "km_limpo", "latitude_limpa", "longitude_limpa",
        "fase_dia_oficial", "fase_dia_agrupada", "condicao_metereologica",
        "tipo_pista", "tracado_via", "uso_solo", "sentido_via",
        "tipo_acidente", "classificacao_acidente", "municipio"
    ]
    cols_existentes_o = [c for c in cols_ocorrencia if c in df.columns]
    ocorrencias = df.drop_duplicates(subset=["id"], keep="first")[cols_existentes_o].copy()

    # Agregar vítimas das pessoas únicas por ocorrência (id)
    vitimas_por_id = (
        pessoas_df.groupby("id")
        .agg({
            "mortos": "sum",
            "feridos_graves": "sum",
            "feridos_leves": "sum",
            "ilesos": "sum",
        })
        .reset_index()
    )
    ocorrencias = ocorrencias.merge(vitimas_por_id, on="id", how="left")
    ocorrencias["mortos"] = ocorrencias["mortos"].fillna(0).astype("uint16")
    ocorrencias["feridos_graves"] = ocorrencias["feridos_graves"].fillna(0).astype("uint16")
    ocorrencias["feridos_leves"] = ocorrencias["feridos_leves"].fillna(0).astype("uint16")
    ocorrencias["ilesos"] = ocorrencias["ilesos"].fillna(0).astype("uint16")
    ocorrencias["total_feridos"] = (ocorrencias["feridos_graves"] + ocorrencias["feridos_leves"]).astype("uint16")
    ocorrencias["total_vitimas"] = (ocorrencias["mortos"] + ocorrencias["total_feridos"]).astype("uint16")
    ocorrencias["acidente_fatal"] = (ocorrencias["mortos"] > 0).astype("uint8")

    # Preservar colunas padrão
    ocorrencias["km"] = ocorrencias["km_limpo"]
    ocorrencias["latitude"] = ocorrencias["latitude_limpa"]
    ocorrencias["longitude"] = ocorrencias["longitude_limpa"]
    ocorrencias["fase_dia"] = ocorrencias["fase_dia_agrupada"].astype(str).str.lower()

    # Validação da classificação de acidente e identificação de divergências
    if "classificacao_acidente" in ocorrencias.columns:
        ocorrencias["classificacao_acidente_original"] = ocorrencias["classificacao_acidente"].copy()
    else:
        ocorrencias["classificacao_acidente_original"] = np.nan
        ocorrencias["classificacao_acidente"] = np.nan

    ocorrencias["classificacao_acidente"] = ocorrencias["classificacao_acidente"].astype(object)
    
    # Vetorização da auditoria de classificação de acidentes fatais
    fatais_mask = ocorrencias["acidente_fatal"] == 1
    orig_str = ocorrencias["classificacao_acidente_original"].astype(str).str.lower()
    div_mask = fatais_mask & (~orig_str.str.contains("fatal", na=False))
    
    divergencias_classificacao = []
    if div_mask.any():
        for _, row_div in ocorrencias[div_mask].iterrows():
            orig_val = str(row_div["classificacao_acidente_original"])
            divergencias_classificacao.append({
                "id": row_div["id"],
                "mortos": int(row_div["mortos"]),
                "classificacao_original": orig_val if orig_val not in ["nan", "None", ""] else "Ausente",
                "motivo": "Morte confirmada nos registros de pessoas, porém classificação de acidente ausente ou não-fatal no boletim original"
            })
        ocorrencias.loc[div_mask, "classificacao_acidente"] = "Com Vítimas Fatais (Auditada)"

    # =========================================================================
    # RELATÓRIO DE AUDITORIA E QUALIDADE DOS DADOS (quality_summary)
    # =========================================================================
    total_ocorrencias = len(ocorrencias)
    ocorrencias_com_km = int(ocorrencias["km_limpo"].notna().sum())
    ocorrencias_sem_km = total_ocorrencias - ocorrencias_com_km
    
    # Mortos e feridos nas ocorrências sem marco quilométrico
    sem_km_df = ocorrencias[ocorrencias["km_limpo"].isna()]
    mortos_sem_km = int(sem_km_df["mortos"].sum())
    feridos_sem_km = int(sem_km_df["total_feridos"].sum())

    ocorrencias_com_geo = int((ocorrencias["latitude_limpa"].notna() & ocorrencias["longitude_limpa"].notna()).sum())
    ocorrencias_sem_geo = total_ocorrencias - ocorrencias_com_geo

    total_mortos_real = int(ocorrencias["mortos"].sum())
    total_feridos_graves_real = int(ocorrencias["feridos_graves"].sum())
    total_feridos_leves_real = int(ocorrencias["feridos_leves"].sum())
    total_feridos_real = int(ocorrencias["total_feridos"].sum())
    acidentes_fatais_real = int(ocorrencias["acidente_fatal"].sum())

    # Estatísticas de idade
    idades_validas_count = int(pessoas_df["idade_valida_flag"].sum()) if "idade_valida_flag" in pessoas_df.columns else 0
    idades_invalidas_count = len(pessoas_df) - idades_validas_count
    idades_maior_110_count = int((pd.to_numeric(pessoas_raw.get("idade", pd.Series()), errors="coerce") > 110).sum())

    # Mortos por tipo de envolvimento
    mortos_envolvidos = (
        pessoas_df[pessoas_df["mortos"] > 0]["tipo_envolvido"].value_counts().to_dict()
        if "tipo_envolvido" in pessoas_df.columns else {}
    )

    anos_presentes = sorted([int(a) for a in ocorrencias["ano"].dropna().unique()]) if "ano" in ocorrencias.columns else []
    anos_incompletos = []
    if "ano" in ocorrencias.columns and "mes" in ocorrencias.columns:
        for a in anos_presentes:
            meses = ocorrencias[ocorrencias["ano"] == a]["mes"].dropna().unique()
            if len(meses) < 12 and a >= 2024:
                anos_incompletos.append((a, sorted(list(meses))))

    quality_summary = {
        "arquivo_origem": source_name,
        "registros_brutos": total_linhas_brutas,
        "ocorrencias_unicas": total_ocorrencias,
        "pessoas_unicas_pesid": len(pessoas_df),
        "linhas_sem_pesid": total_linhas_sem_pesid,
        "veiculos_unicos": len(veiculos_df),
        "desdobramentos_consolidados": total_linhas_brutas - total_ocorrencias,
        "duplicatas_linhas_evitadas": total_linhas_brutas - total_ocorrencias,  # alias mantido para compatibilidade
        "taxa_consolidacao": (total_linhas_brutas / total_ocorrencias) if total_ocorrencias > 0 else 1.0,
        "ocorrencias_com_km": ocorrencias_com_km,
        "ocorrencias_sem_km": ocorrencias_sem_km,
        "mortos_sem_km": mortos_sem_km,
        "feridos_sem_km": feridos_sem_km,
        "perc_com_km": (ocorrencias_com_km / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
        "ocorrencias_com_geo": ocorrencias_com_geo,
        "ocorrencias_sem_geo": ocorrencias_sem_geo,
        "perc_com_geo": (ocorrencias_com_geo / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
        "total_mortos_real": total_mortos_real,
        "total_feridos_graves_real": total_feridos_graves_real,
        "total_feridos_leves_real": total_feridos_leves_real,
        "total_feridos_real": total_feridos_real,
        "acidentes_fatais_real": acidentes_fatais_real,
        "taxa_acidentes_fatais_pct": (acidentes_fatais_real / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
        "obitos_por_100_acidentes": (total_mortos_real / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
        "idades_validas": idades_validas_count,
        "idades_inconsistentes_ou_ausentes": idades_invalidas_count,
        "idades_superiores_110_anos": idades_maior_110_count,
        "divergencias_classificacao": divergencias_classificacao,
        "mortos_por_envolvimento": mortos_envolvidos,
        "anos_presentes": anos_presentes,
        "anos_incompletos": anos_incompletos,
        "data_minima": str(ocorrencias["data_inversa"].min()) if "data_inversa" in ocorrencias.columns else "N/A",
        "data_maxima": str(ocorrencias["data_inversa"].max()) if "data_inversa" in ocorrencias.columns else "N/A",
    }

    # Compactação de tipos categóricos para redução drástica de consumo de memória
    for c in ["uf", "br", "fase_dia_oficial", "fase_dia_agrupada", "fase_dia", "condicao_metereologica", "tipo_pista", "tracado_via", "uso_solo", "sentido_via", "tipo_acidente"]:
        if c in ocorrencias.columns:
            ocorrencias[c] = ocorrencias[c].astype("category")

    if pessoas_df is not None and not pessoas_df.empty:
        for c in ["tipo_envolvido", "estado_fisico", "sexo", "faixa_etaria", "uf", "br", "fase_dia_oficial", "fase_dia_agrupada", "condicao_metereologica", "tipo_acidente"]:
            if c in pessoas_df.columns:
                pessoas_df[c] = pessoas_df[c].astype("category")

    if veiculos_df is not None and not veiculos_df.empty:
        for c in ["tipo_veiculo", "uf", "br", "fase_dia_oficial", "fase_dia_agrupada"]:
            if c in veiculos_df.columns:
                veiculos_df[c] = veiculos_df[c].astype("category")

    if causas_df is not None and not causas_df.empty:
        for c in ["causa_principal"]:
            if c in causas_df.columns:
                causas_df[c] = causas_df[c].astype("category")

    gc.collect()

    if return_relational:
        return ocorrencias, pessoas_df, veiculos_df, causas_df, quality_summary
    else:
        return ocorrencias, causas_df, quality_summary



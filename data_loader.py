"""
Módulo de Ingestão, Validação e Qualidade de Dados.
Responsável por carregar CSV e Parquet, tratar decimais brasileiros,
desduplicar ocorrências e gerar relatório de qualidade de dados.
"""

import os
import re
import gc
from typing import Tuple, Dict, Any, Optional, List
import pandas as pd
import numpy as np
from config import (
    COLUMN_MAPPING,
    VALIDATION_RULES,
    FASES_DIA_OFICIAIS,
    VALUE_STANDARDIZATION,
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
    """
    cleaned = series.apply(clean_brazilian_float)
    min_km = VALIDATION_RULES["km"]["min"]
    max_km = VALIDATION_RULES["km"]["max"]
    # Marcar fora do intervalo como NaN (inválidos)
    cleaned = cleaned.apply(lambda x: x if (x is not None and min_km <= x <= max_km) else np.nan)
    return cleaned.astype("float32")


def clean_coordinate_series(series: pd.Series, coord_type: str) -> pd.Series:
    """
    Limpa latitudes ou longitudes tratando vírgulas decimais
    e validando os limites geográficos do Brasil.
    Não converte nulos para (0, 0).
    """
    cleaned = series.apply(clean_brazilian_float)
    min_val = VALIDATION_RULES[coord_type]["min"]
    max_val = VALIDATION_RULES[coord_type]["max"]
    cleaned = cleaned.apply(lambda x: x if (x is not None and min_val <= x <= max_val) else np.nan)
    return cleaned.astype("float32")


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


def process_raw_dataframe(raw_df: pd.DataFrame, source_name: str = "") -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Processa o DataFrame bruto da PRF:
    - Normaliza colunas e tipos
    - Detecta se a base possui granularidade de pessoas/causas (ex: pesid, causas múltiplas)
    - Desduplica ocorrências usando 'id' único
    - Agrega fatalidades e feridos reais por ocorrência
    - Separa base de ocorrências únicas e base de causas associadas
    - Gera métricas completas de auditoria e qualidade dos dados
    """
    df = normalize_column_names(raw_df)
    total_linhas_brutas = len(df)
    
    # Extrair ano da data ou do nome do arquivo se não existir
    if "data_inversa" in df.columns:
        df["data_dt"] = pd.to_datetime(df["data_inversa"], errors="coerce")
        df["ano"] = df["data_dt"].dt.year
        df["mes"] = df["data_dt"].dt.month
        df["ano_mes"] = df["data_dt"].dt.to_period("M").astype(str)
    elif "ano" not in df.columns and source_name:
        m = re.search(r"(20[0-9]{2})", source_name)
        if m:
            df["ano"] = int(m.group(1))

    # Limpeza de KM e Coordenadas
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

    # Normalização de Fase do Dia
    if "fase_dia" in df.columns:
        df["fase_dia_oficial"] = df["fase_dia"].apply(standardize_fase_dia)
        df["fase_dia_agrupada"] = df["fase_dia_oficial"].apply(get_fase_dia_agrupada)
    else:
        df["fase_dia_oficial"] = "Não informado"
        df["fase_dia_agrupada"] = "Não informado"

    # Tratar UF e BR
    if "uf" in df.columns:
        df["uf"] = df["uf"].astype(str).str.strip().str.upper()
        df.loc[df["uf"].isin(["NAN", "NONE", "", "NULL"]), "uf"] = np.nan
    
    if "br" in df.columns:
        # Limpar BR (ex: '101', '101.0' -> '101')
        def clean_br(v):
            if pd.isna(v):
                return "N/A"
            s = str(v).strip().replace(".0", "")
            return s if s else "N/A"
        df["br"] = df["br"].apply(clean_br)

    # Identificar ocorrências e pessoas
    tem_id = "id" in df.columns
    tem_pesid = "pesid" in df.columns

    if tem_id:
        # Desduplicar pessoas para contagem precisa de mortos e feridos
        if tem_pesid:
            # Pessoas únicas por (id, pesid)
            pessoas_validas = df.dropna(subset=["pesid"]).drop_duplicates(subset=["id", "pesid"])
            
            # Somar vítimas por ocorrência (id)
            for col in ["mortos", "feridos_graves", "feridos_leves", "ilesos"]:
                if col in pessoas_validas.columns:
                    pessoas_validas[col] = pd.to_numeric(
                        pessoas_validas[col].apply(clean_brazilian_float), errors="coerce"
                    ).fillna(0)
                else:
                    pessoas_validas[col] = 0.0

            vitimas_por_id = (
                pessoas_validas.groupby("id")
                .agg({
                    "mortos": "sum",
                    "feridos_graves": "sum",
                    "feridos_leves": "sum",
                    "ilesos": "sum",
                })
                .reset_index()
            )
        else:
            # Se não tem pesid, verificar se já está agregada por ocorrência
            # Agrupar por id pegando o máximo de vítimas registradas para não inflar
            for col in ["mortos", "feridos_graves", "feridos_leves", "ilesos"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(
                        df[col].apply(clean_brazilian_float), errors="coerce"
                    ).fillna(0)
                else:
                    df[col] = 0.0
            
            vitimas_por_id = (
                df.groupby("id")
                .agg({
                    "mortos": "max",
                    "feridos_graves": "max",
                    "feridos_leves": "max",
                    "ilesos": "max",
                })
                .reset_index()
            )

        # Montar a tabela desduplicada de ocorrências únicas
        # Colunas de nível de ocorrência:
        cols_ocorrencia = [
            "id", "data_inversa", "ano", "mes", "ano_mes", "horario",
            "uf", "br", "km_limpo", "latitude_limpa", "longitude_limpa",
            "fase_dia_oficial", "fase_dia_agrupada", "condicao_metereologica",
            "tipo_pista", "tracado_via", "municipio", "classificacao_acidente"
        ]
        cols_existentes = [c for c in cols_ocorrencia if c in df.columns]
        
        # Pega a primeira ocorrência não nula para cada atributo do acidente
        ocorrencias = df.groupby("id", as_index=False)[cols_existentes].first()
        
        # Fazer merge com as vítimas desduplicadas
        ocorrencias = ocorrencias.merge(vitimas_por_id, on="id", how="left")
        ocorrencias["mortos"] = ocorrencias["mortos"].fillna(0).astype("uint16")
        ocorrencias["feridos_graves"] = ocorrencias["feridos_graves"].fillna(0).astype("uint16")
        ocorrencias["feridos_leves"] = ocorrencias["feridos_leves"].fillna(0).astype("uint16")
        ocorrencias["ilesos"] = ocorrencias["ilesos"].fillna(0).astype("uint16")
        ocorrencias["total_feridos"] = (ocorrencias["feridos_graves"] + ocorrencias["feridos_leves"]).astype("uint16")
        ocorrencias["total_vitimas"] = (ocorrencias["mortos"] + ocorrencias["total_feridos"]).astype("uint16")
        ocorrencias["acidente_fatal"] = (ocorrencias["mortos"] > 0).astype("uint8")
        
        # Manter compatibilidade com colunas padrão usadas no sistema
        ocorrencias["km"] = ocorrencias["km_limpo"]
        ocorrencias["latitude"] = ocorrencias["latitude_limpa"]
        ocorrencias["longitude"] = ocorrencias["longitude_limpa"]
        ocorrencias["fase_dia"] = ocorrencias["fase_dia_agrupada"].str.lower()
        
        # Tabela de causas (preserva cada causa associada ao id)
        cols_causas = ["id", "causa_acidente", "causa_principal", "tipo_acidente"]
        cols_causas_existentes = [c for c in cols_causas if c in df.columns]
        if "causa_acidente" in df.columns:
            causas_df = df[cols_causas_existentes].dropna(subset=["causa_acidente"]).drop_duplicates()
        else:
            causas_df = pd.DataFrame(columns=["id", "causa_acidente"])

    else:
        # Base sem coluna ID (cada linha é tratada como ocorrência)
        ocorrencias = df.copy()
        ocorrencias["id"] = np.arange(1, len(ocorrencias) + 1)
        for col in ["mortos", "feridos_graves", "feridos_leves", "ilesos"]:
            if col in ocorrencias.columns:
                ocorrencias[col] = pd.to_numeric(
                    ocorrencias[col].apply(clean_brazilian_float), errors="coerce"
                ).fillna(0).astype("uint16")
            else:
                ocorrencias[col] = 0
        ocorrencias["total_feridos"] = ocorrencias["feridos_graves"] + ocorrencias["feridos_leves"]
        ocorrencias["total_vitimas"] = ocorrencias["mortos"] + ocorrencias["total_feridos"]
        ocorrencias["acidente_fatal"] = (ocorrencias["mortos"] > 0).astype("uint8")
        ocorrencias["km"] = ocorrencias["km_limpo"]
        ocorrencias["latitude"] = ocorrencias["latitude_limpa"]
        ocorrencias["longitude"] = ocorrencias["longitude_limpa"]
        ocorrencias["fase_dia"] = ocorrencias["fase_dia_agrupada"].str.lower()
        causas_df = ocorrencias[["id", "causa_acidente"]].copy() if "causa_acidente" in ocorrencias.columns else pd.DataFrame()

    # Relatório de Auditoria e Qualidade
    total_ocorrencias = len(ocorrencias)
    ocorrencias_com_km = int(ocorrencias["km_limpo"].notna().sum())
    ocorrencias_sem_km = total_ocorrencias - ocorrencias_com_km
    ocorrencias_com_geo = int((ocorrencias["latitude_limpa"].notna() & ocorrencias["longitude_limpa"].notna()).sum())
    ocorrencias_sem_geo = total_ocorrencias - ocorrencias_com_geo
    
    anos_presentes = sorted([int(a) for a in ocorrencias["ano"].dropna().unique()]) if "ano" in ocorrencias.columns else []
    
    # Identificar anos incompletos (ex: 2026 com meses até agosto)
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
        "duplicatas_linhas_evitadas": total_linhas_brutas - total_ocorrencias,
        "taxa_desduplicacao": (total_linhas_brutas / total_ocorrencias) if total_ocorrencias > 0 else 1.0,
        "ocorrencias_com_km": ocorrencias_com_km,
        "ocorrencias_sem_km": ocorrencias_sem_km,
        "perc_com_km": (ocorrencias_com_km / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
        "ocorrencias_com_geo": ocorrencias_com_geo,
        "ocorrencias_sem_geo": ocorrencias_sem_geo,
        "perc_com_geo": (ocorrencias_com_geo / total_ocorrencias * 100) if total_ocorrencias > 0 else 0.0,
        "total_mortos_real": int(ocorrencias["mortos"].sum()),
        "total_feridos_real": int(ocorrencias["total_feridos"].sum()),
        "acidentes_fatais_real": int(ocorrencias["acidente_fatal"].sum()),
        "anos_presentes": anos_presentes,
        "anos_incompletos": anos_incompletos,
        "data_minima": str(ocorrencias["data_inversa"].min()) if "data_inversa" in ocorrencias.columns else "N/A",
        "data_maxima": str(ocorrencias["data_inversa"].max()) if "data_inversa" in ocorrencias.columns else "N/A",
    }

    return ocorrencias, causas_df, quality_summary


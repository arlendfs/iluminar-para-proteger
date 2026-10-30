"""
Módulo de Análise Demográfica, Perfil das Vítimas e Tipologia Veicular.
Implementa agregação rigorosa de pessoas (id, pesid), veículos (id, id_veiculo)
e ocorrências (id), garantindo a diferenciação entre métricas de pessoas e de sinistros,
além do tratamento de faixas etárias, sexo, tipos de envolvimento e tipos de acidentes.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from config import FAIXAS_ETARIAS_ORDEM, FASES_DIA_OFICIAIS


def compute_envolvimento_analysis(
    pessoas_df: pd.DataFrame,
    col_fase: str = "fase_dia_oficial",
) -> Dict[str, Any]:
    """
    Analisa as vítimas e envolvidos por tipo de envolvimento (Condutor, Passageiro, Pedestre, etc.):
    - Contagem de pessoas únicas por tipo de envolvimento;
    - Total de mortos, feridos graves, feridos leves e ilesos;
    - Taxa de mortalidade específica (% de óbitos sobre o total de envolvidos da categoria);
    - Proporção de óbitos sobre a mortalidade geral;
    - Estratificação cruzada por fase do dia (Pleno dia, Plena Noite, Amanhecer, Anoitecer).
    """
    if pessoas_df is None or pessoas_df.empty:
        return {
            "resumo_envolvimento": pd.DataFrame(),
            "cruzamento_fase_dia": pd.DataFrame(),
        }

    df = pessoas_df.copy()
    col_env = "tipo_envolvido" if "tipo_envolvido" in df.columns else "tipo_envolvido_limpo"
    if col_env not in df.columns:
        df[col_env] = "Não informado"

    # 1. Resumo por tipo de envolvimento
    resumo = (
        df.groupby(col_env, observed=True)
        .agg(
            total_envolvidos=("pesid", "count"),
            mortos=("mortos", "sum"),
            feridos_graves=("feridos_graves", "sum"),
            feridos_leves=("feridos_leves", "sum"),
            ilesos=("ilesos", "sum"),
        )
        .reset_index()
    )
    resumo["total_feridos"] = resumo["feridos_graves"] + resumo["feridos_leves"]
    resumo["total_vitimas"] = resumo["mortos"] + resumo["total_feridos"]
    
    total_geral_mortos = resumo["mortos"].sum()
    resumo["taxa_mortalidade_pct"] = (
        resumo["mortos"] / resumo["total_envolvidos"].replace(0, np.nan) * 100
    ).fillna(0).round(2)
    resumo["prop_total_mortos_pct"] = (
        resumo["mortos"] / (total_geral_mortos if total_geral_mortos > 0 else 1) * 100
    ).round(2)

    resumo = resumo.sort_values("mortos", ascending=False)

    # 2. Cruzamento com Fase do Dia
    cruzamento = pd.DataFrame()
    fase_field = col_fase if col_fase in df.columns else ("fase_dia_agrupada" if "fase_dia_agrupada" in df.columns else None)
    if fase_field:
        cruzamento = (
            df.groupby([col_env, fase_field], observed=True)
            .agg(
                total_envolvidos=("pesid", "count"),
                mortos=("mortos", "sum"),
                feridos_graves=("feridos_graves", "sum"),
                feridos_leves=("feridos_leves", "sum"),
            )
            .reset_index()
        )
        cruzamento["taxa_mortalidade_pct"] = (
            cruzamento["mortos"] / cruzamento["total_envolvidos"].replace(0, np.nan) * 100
        ).fillna(0).round(2)

    return {
        "resumo_envolvimento": resumo,
        "cruzamento_fase_dia": cruzamento,
    }


def compute_sexo_analysis(
    pessoas_df: pd.DataFrame,
    col_fase: str = "fase_dia_oficial",
) -> Dict[str, Any]:
    """
    Analisa a distribuição por sexo:
    - Total de pessoas, mortos, feridos graves e leves;
    - Taxa de mortalidade por sexo e participação sobre as fatalidades totais;
    - Comparativo Dia vs Noite vs Crepúsculo.
    """
    if pessoas_df is None or pessoas_df.empty:
        return {
            "resumo_sexo": pd.DataFrame(),
            "cruzamento_fase_dia": pd.DataFrame(),
        }

    df = pessoas_df.copy()
    col_sexo = "sexo" if "sexo" in df.columns else "sexo_limpo"
    if col_sexo not in df.columns:
        df[col_sexo] = "Não informado"

    resumo = (
        df.groupby(col_sexo, observed=True)
        .agg(
            total_pessoas=("pesid", "count"),
            mortos=("mortos", "sum"),
            feridos_graves=("feridos_graves", "sum"),
            feridos_leves=("feridos_leves", "sum"),
            ilesos=("ilesos", "sum"),
        )
        .reset_index()
    )
    resumo["total_feridos"] = resumo["feridos_graves"] + resumo["feridos_leves"]
    total_mortos = resumo["mortos"].sum()
    resumo["taxa_mortalidade_pct"] = (
        resumo["mortos"] / resumo["total_pessoas"].replace(0, np.nan) * 100
    ).fillna(0).round(2)
    resumo["prop_total_mortos_pct"] = (
        resumo["mortos"] / (total_mortos if total_mortos > 0 else 1) * 100
    ).round(2)

    resumo = resumo.sort_values("mortos", ascending=False)

    fase_field = col_fase if col_fase in df.columns else ("fase_dia_agrupada" if "fase_dia_agrupada" in df.columns else None)
    cruzamento = pd.DataFrame()
    if fase_field:
        cruzamento = (
            df.groupby([col_sexo, fase_field], observed=True)
            .agg(
                total_pessoas=("pesid", "count"),
                mortos=("mortos", "sum"),
                feridos_graves=("feridos_graves", "sum"),
            )
            .reset_index()
        )

    return {
        "resumo_sexo": resumo,
        "cruzamento_fase_dia": cruzamento,
    }


def compute_faixa_etaria_analysis(
    pessoas_df: pd.DataFrame,
    col_fase: str = "fase_dia_oficial",
) -> Dict[str, Any]:
    """
    Analisa a distribuição por faixa etária preservando a ordenação demográfica.
    Trata estritamente idades ausentes ou superiores a 110 anos como inconsistentes,
    sem convertê-las para zero.
    """
    if pessoas_df is None or pessoas_df.empty:
        return {
            "resumo_faixa_etaria": pd.DataFrame(),
            "idade_por_gravidade": pd.DataFrame(),
            "metricas_qualidade_idade": {},
        }

    df = pessoas_df.copy()
    if "faixa_etaria" not in df.columns:
        df["faixa_etaria"] = "Não informada / Inconsistente"
    if "idade_valida_flag" not in df.columns:
        df["idade_valida_flag"] = df["idade"].apply(lambda v: pd.notna(v) and 0 <= float(v) <= 110)

    # 1. Resumo por faixa etária ordenada
    resumo = (
        df.groupby("faixa_etaria", observed=True)
        .agg(
            total_pessoas=("pesid", "count"),
            mortos=("mortos", "sum"),
            feridos_graves=("feridos_graves", "sum"),
            feridos_leves=("feridos_leves", "sum"),
            ilesos=("ilesos", "sum"),
        )
        .reset_index()
    )
    resumo["total_feridos"] = resumo["feridos_graves"] + resumo["feridos_leves"]
    total_mortos = resumo["mortos"].sum()
    resumo["taxa_mortalidade_pct"] = (
        resumo["mortos"] / resumo["total_pessoas"].replace(0, np.nan) * 100
    ).fillna(0).round(2)
    resumo["prop_total_mortos_pct"] = (
        resumo["mortos"] / (total_mortos if total_mortos > 0 else 1) * 100
    ).round(2)

    # Ordenar pelas categorias padronizadas
    ordem_map = {f: i for i, f in enumerate(FAIXAS_ETARIAS_ORDEM)}
    resumo["ordem"] = resumo["faixa_etaria"].map(ordem_map).fillna(99)
    resumo = resumo.sort_values("ordem").drop(columns=["ordem"])

    # 2. Estatísticas de idade por gravidade (apenas idades válidas de 0 a 110 anos)
    validos = df[df["idade_valida_flag"] == True].copy()
    col_idade_num = "idade_limpa" if "idade_limpa" in validos.columns else "idade"
    validos[col_idade_num] = pd.to_numeric(validos[col_idade_num], errors="coerce")

    estat_gravidade = []
    # Óbito
    obitos = validos[validos["mortos"] > 0][col_idade_num].dropna()
    if not obitos.empty:
        estat_gravidade.append({
            "Estado Físico / Gravidade": "Óbito (Vítima Fatal)",
            "Registros Válidos": len(obitos),
            "Idade Média": round(obitos.mean(), 1),
            "Mediana": round(obitos.median(), 1),
            "Desvio Padrão": round(obitos.std(), 1),
            "Idade Mínima": int(obitos.min()),
            "Idade Máxima": int(obitos.max()),
        })

    # Feridos Graves
    graves = validos[(validos["feridos_graves"] > 0) & (validos["mortos"] == 0)][col_idade_num].dropna()
    if not graves.empty:
        estat_gravidade.append({
            "Estado Físico / Gravidade": "Lesões Graves",
            "Registros Válidos": len(graves),
            "Idade Média": round(graves.mean(), 1),
            "Mediana": round(graves.median(), 1),
            "Desvio Padrão": round(graves.std(), 1),
            "Idade Mínima": int(graves.min()),
            "Idade Máxima": int(graves.max()),
        })

    # Feridos Leves
    leves = validos[(validos["feridos_leves"] > 0) & (validos["mortos"] == 0) & (validos["feridos_graves"] == 0)][col_idade_num].dropna()
    if not leves.empty:
        estat_gravidade.append({
            "Estado Físico / Gravidade": "Lesões Leves",
            "Registros Válidos": len(leves),
            "Idade Média": round(leves.mean(), 1),
            "Mediana": round(leves.median(), 1),
            "Desvio Padrão": round(leves.std(), 1),
            "Idade Mínima": int(leves.min()),
            "Idade Máxima": int(leves.max()),
        })

    # Ilesos
    ilesos = validos[validos["ilesos"] > 0][col_idade_num].dropna()
    if not ilesos.empty:
        estat_gravidade.append({
            "Estado Físico / Gravidade": "Ileso",
            "Registros Válidos": len(ilesos),
            "Idade Média": round(ilesos.mean(), 1),
            "Mediana": round(ilesos.median(), 1),
            "Desvio Padrão": round(ilesos.std(), 1),
            "Idade Mínima": int(ilesos.min()),
            "Idade Máxima": int(ilesos.max()),
        })

    idade_por_gravidade = pd.DataFrame(estat_gravidade)

    # 3. Métricas de Qualidade dos Dados Etários
    total_pessoas = len(df)
    n_validos = int(df["idade_valida_flag"].sum())
    n_invalidos = total_pessoas - n_validos
    maior_110 = int((pd.to_numeric(df["idade"], errors="coerce") > 110).sum())
    
    qual_idade = {
        "total_pessoas": total_pessoas,
        "idades_validas": n_validos,
        "perc_idades_validas": round(n_validos / total_pessoas * 100, 1) if total_pessoas > 0 else 0.0,
        "idades_inconsistentes_ou_ausentes": n_invalidos,
        "perc_inconsistentes": round(n_invalidos / total_pessoas * 100, 1) if total_pessoas > 0 else 0.0,
        "idades_superiores_110_anos": maior_110,
    }

    return {
        "resumo_faixa_etaria": resumo,
        "idade_por_gravidade": idade_por_gravidade,
        "metricas_qualidade_idade": qual_idade,
    }


def compute_veiculo_analysis(
    veiculos_df: pd.DataFrame,
    pessoas_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Analisa a frota de veículos envolvidos e cruza com a gravidade dos ocupantes:
    - Contagem de veículos únicos por (id, id_veiculo);
    - Vítimas e fatalidades associadas ao tipo de veículo;
    - Taxa de severidade por tipo veicular.
    """
    if veiculos_df is None or veiculos_df.empty:
        return pd.DataFrame()

    col_tipo = "tipo_veiculo" if "tipo_veiculo" in veiculos_df.columns else "tipo_veiculo_limpo"
    resumo_veic = (
        veiculos_df.groupby(col_tipo, observed=True)
        .agg(total_veiculos=("id_veiculo", "count"))
        .reset_index()
    )

    if pessoas_df is not None and not pessoas_df.empty and "id_veiculo" in pessoas_df.columns:
        p_com_veic = pessoas_df.dropna(subset=["id_veiculo"]).copy()
        if "tipo_veiculo" in p_com_veic.columns:
            vitimas_veic = (
                p_com_veic.groupby("tipo_veiculo", observed=True)
                .agg(
                    total_ocupantes=("pesid", "count"),
                    mortos=("mortos", "sum"),
                    feridos_graves=("feridos_graves", "sum"),
                    feridos_leves=("feridos_leves", "sum"),
                )
                .reset_index()
            )
            resumo_veic = resumo_veic.merge(
                vitimas_veic, left_on=col_tipo, right_on="tipo_veiculo", how="left"
            ).fillna(0)
            resumo_veic["taxa_letalidade_ocupante_pct"] = (
                resumo_veic["mortos"] / resumo_veic["total_ocupantes"].replace(0, np.nan) * 100
            ).fillna(0).round(2)

    return resumo_veic.sort_values("total_veiculos", ascending=False)


def compute_tipo_acidente_analysis(
    ocorrencias_df: pd.DataFrame,
    col_fase: str = "fase_dia_oficial",
) -> Dict[str, pd.DataFrame]:
    """
    Analisa os tipos de acidentes (Colisão frontal, Saída de leito, Tombamento, etc.):
    - Contagem de sinistros únicos por tipo de acidente;
    - Total de mortos e feridos por tipo;
    - Taxa de mortalidade por 100 acidentes e percentual de acidentes fatais;
    - Cruzamento com a fase do dia (Pleno dia, Plena Noite, Amanhecer, Anoitecer).
    """
    if ocorrencias_df is None or ocorrencias_df.empty or "tipo_acidente" not in ocorrencias_df.columns:
        return {"resumo_tipo_acidente": pd.DataFrame(), "cruzamento_fase_dia": pd.DataFrame()}

    resumo = (
        ocorrencias_df.groupby("tipo_acidente", observed=True)
        .agg(
            n_acidentes=("id", "count"),
            mortos=("mortos", "sum"),
            feridos_graves=("feridos_graves", "sum"),
            feridos_leves=("feridos_leves", "sum"),
            acidentes_fatais=("acidente_fatal", "sum"),
        )
        .reset_index()
    )
    resumo["total_feridos"] = resumo["feridos_graves"] + resumo["feridos_leves"]
    resumo["obitos_por_100_acidentes"] = (
        resumo["mortos"] / resumo["n_acidentes"].replace(0, np.nan) * 100
    ).fillna(0).round(2)
    resumo["prop_acidentes_fatais_pct"] = (
        resumo["acidentes_fatais"] / resumo["n_acidentes"].replace(0, np.nan) * 100
    ).fillna(0).round(2)
    resumo = resumo.sort_values("mortos", ascending=False)

    fase_field = col_fase if col_fase in ocorrencias_df.columns else ("fase_dia_agrupada" if "fase_dia_agrupada" in ocorrencias_df.columns else None)
    cruzamento = pd.DataFrame()
    if fase_field:
        cruzamento = (
            ocorrencias_df.groupby(["tipo_acidente", fase_field], observed=True)
            .agg(
                n_acidentes=("id", "count"),
                mortos=("mortos", "sum"),
                feridos_graves=("feridos_graves", "sum"),
                feridos_leves=("feridos_leves", "sum"),
                acidentes_fatais=("acidente_fatal", "sum"),
            )
            .reset_index()
        )
        cruzamento["total_feridos"] = cruzamento["feridos_graves"] + cruzamento["feridos_leves"]
        cruzamento["obitos_por_100_acidentes"] = (
            cruzamento["mortos"] / cruzamento["n_acidentes"].replace(0, np.nan) * 100
        ).fillna(0).round(2)

    return {
        "resumo_tipo_acidente": resumo,
        "cruzamento_fase_dia": cruzamento,
    }


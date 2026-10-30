"""
Módulo de Métricas Estatísticas e Comparação Temporal/Dia vs Noite.
Calcula com rigor científico indicadores de severidade, letalidade,
proporções, taxas por 100 e 1.000 acidentes e razões comparativas.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def compute_period_metrics(df: pd.DataFrame, period_col: str = "fase_dia_oficial") -> pd.DataFrame:
    """
    Calcula indicadores estatísticos detalhados por período/fase do dia:
    - n_acidentes: Total de ocorrências únicas no período
    - acidentes_fatais: Quantidade de acidentes com pelo menos 1 óbito
    - prop_acidentes_fatais_pct: (acidentes_fatais / n_acidentes) * 100
    - total_mortos: Quantidade total de pessoas mortas
    - mortos_por_100_acidentes: (total_mortos / n_acidentes) * 100
    - mortos_por_1000_acidentes: (total_mortos / n_acidentes) * 1000
    - media_obitos_por_acidente: total_mortos / n_acidentes
    - feridos_graves: Total de feridos graves
    - feridos_leves: Total de feridos leves
    - total_feridos: feridos_graves + feridos_leves
    - total_vitimas: total_mortos + total_feridos
    - vitimas_por_100_acidentes: (total_vitimas / n_acidentes) * 100
    - indice_severidade: (3 * total_mortos + total_feridos)
    """
    if df.empty or period_col not in df.columns:
        return pd.DataFrame()

    df_calc = df.copy()
    for col in ["mortos", "feridos_graves", "feridos_leves", "total_feridos", "total_vitimas", "acidente_fatal"]:
        if col not in df_calc.columns:
            df_calc[col] = 0

    grouped = df_calc.groupby(period_col, observed=True).agg(
        n_acidentes=("id", "count"),
        acidentes_fatais=("acidente_fatal", "sum"),
        total_mortos=("mortos", "sum"),
        feridos_graves=("feridos_graves", "sum"),
        feridos_leves=("feridos_leves", "sum"),
        total_feridos=("total_feridos", "sum"),
        total_vitimas=("total_vitimas", "sum"),
    ).reset_index()

    # Denominador: n_acidentes do período
    n = grouped["n_acidentes"].replace(0, np.nan)
    
    grouped["prop_acidentes_fatais_pct"] = (grouped["acidentes_fatais"] / n) * 100
    grouped["media_obitos_por_acidente"] = grouped["total_mortos"] / n
    grouped["mortos_por_100_acidentes"] = (grouped["total_mortos"] / n) * 100
    grouped["mortos_por_1000_acidentes"] = (grouped["total_mortos"] / n) * 1000
    grouped["vitimas_por_100_acidentes"] = (grouped["total_vitimas"] / n) * 100
    grouped["indice_severidade"] = grouped["total_mortos"] * 3 + grouped["total_feridos"]
    
    # Participação percentual sobre o total de acidentes da base
    total_base = df["id"].count()
    grouped["participacao_acidentes_pct"] = (grouped["n_acidentes"] / total_base) * 100 if total_base > 0 else 0.0

    return grouped


def compute_day_vs_night_comparison(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compara estritamente o período Noturno (Plena Noite) vs Diurno (Pleno Dia),
    além de reportar os períodos de transição (Crepúsculos: Amanhecer e Anoitecer).
    Calcula razões de letalidade e severidade.
    """
    if df.empty:
        return {}

    # Usar fase_dia_agrupada se disponível, senão derivar
    col = "fase_dia_agrupada" if "fase_dia_agrupada" in df.columns else "fase_dia"
    
    metrics_by_group = compute_period_metrics(df, period_col=col)
    metrics_official = compute_period_metrics(df, period_col="fase_dia_oficial") if "fase_dia_oficial" in df.columns else metrics_by_group

    # Extrair registros específicos de Noturno e Diurno
    def get_row(df_metrics, val):
        m = df_metrics[df_metrics[col].astype(str).str.lower() == val.lower()]
        return m.iloc[0].to_dict() if not m.empty else None

    noturno = get_row(metrics_by_group, "noturno")
    diurno = get_row(metrics_by_group, "diurno")
    crepusculo = get_row(metrics_by_group, "crepúsculo") or get_row(metrics_by_group, "crepusculo")

    total_acidentes = len(df)
    total_mortos = int(df["mortos"].sum())
    total_feridos = int(df["total_feridos"].sum())
    total_vitimas = int(df["total_vitimas"].sum())
    acidentes_fatais = int(df["acidente_fatal"].sum())

    # Razões entre Noturno e Diurno
    razao_letalidade_obitos = 1.0
    razao_letalidade_fatais = 1.0
    razao_severidade = 1.0

    if noturno and diurno:
        d_med_obitos = diurno.get("media_obitos_por_acidente", 0.0)
        n_med_obitos = noturno.get("media_obitos_por_acidente", 0.0)
        if d_med_obitos > 0:
            razao_letalidade_obitos = n_med_obitos / d_med_obitos

        d_prop_fatais = diurno.get("prop_acidentes_fatais_pct", 0.0)
        n_prop_fatais = noturno.get("prop_acidentes_fatais_pct", 0.0)
        if d_prop_fatais > 0:
            razao_letalidade_fatais = n_prop_fatais / d_prop_fatais

        d_vit_100 = diurno.get("vitimas_por_100_acidentes", 0.0)
        n_vit_100 = noturno.get("vitimas_por_100_acidentes", 0.0)
        if d_vit_100 > 0:
            razao_severidade = n_vit_100 / d_vit_100

    return {
        "total_acidentes": total_acidentes,
        "total_mortos": total_mortos,
        "total_feridos": total_feridos,
        "total_vitimas": total_vitimas,
        "acidentes_fatais": acidentes_fatais,
        "taxa_letalidade_geral_pct": (acidentes_fatais / total_acidentes * 100) if total_acidentes > 0 else 0.0,
        "obitos_por_100_geral": (total_mortos / total_acidentes * 100) if total_acidentes > 0 else 0.0,
        "noturno": noturno,
        "diurno": diurno,
        "crepusculo": crepusculo,
        "razao_letalidade_obitos": razao_letalidade_obitos,
        "razao_letalidade_fatais": razao_letalidade_fatais,
        "razao_severidade": razao_severidade,
        "tabela_agrupada": metrics_by_group,
        "tabela_oficial": metrics_official,
    }

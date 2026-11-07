"""Cruzamentos observacionais por ocorrência única para o estudo territorial."""

from __future__ import annotations

import pandas as pd
from math import sqrt

from territorial_case import indicators, normalize_municipality


MECHANISMS = {
    "Reação tardia": ("reacao tardia", "reacao ineficiente"),
    "Ausência de reação": ("ausencia de reacao",),
    "Velocidade incompatível": ("velocidade incompativel",),
    "Ultrapassagem indevida": ("ultrapassagem indevida",),
    "Condutor dormindo": ("condutor dormindo",),
    "Álcool": ("ingestao de alcool", "alcool"),
}


def mechanism_flags(data: pd.DataFrame, causes: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por ocorrência; causas múltiplas geram flags, nunca novas ocorrências."""
    base = data.drop_duplicates("id").set_index("id")
    columns = ["fase_dia_oficial", "condicao_metereologica", "tipo_acidente", "mortos", "feridos_graves", "feridos_leves", "acidente_fatal"]
    result = base.reindex(columns=[name for name in columns if name in base]).copy()
    for name in MECHANISMS:
        result[name] = False
    if causes is None or causes.empty or not {"id", "causa_acidente"}.issubset(causes):
        return result
    cause_table = causes.loc[causes["id"].isin(result.index), ["id", "causa_acidente"]].drop_duplicates()
    normalized = cause_table["causa_acidente"].map(normalize_municipality).str.lower()
    for name, patterns in MECHANISMS.items():
        matched_ids = cause_table.loc[normalized.map(lambda value: any(pattern in value for pattern in patterns)), "id"].unique()
        result.loc[result.index.isin(matched_ids), name] = True
    return result


def mechanism_table(flags: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for phase in ("Plena Noite", "Pleno dia"):
        subset = flags.loc[flags["fase_dia_oficial"].eq(phase)]
        denom = len(subset)
        for name in MECHANISMS:
            associated = subset.loc[subset[name]]
            rows.append({
                "Fase": phase, "Fator registrado": name,
                "Ocorrências associadas": len(associated), "Denominador de acidentes": denom,
                "Participação (%)": 100 * len(associated) / denom if denom else None,
                "Acidentes fatais": int(associated["acidente_fatal"].sum()) if "acidente_fatal" in associated else 0,
                "Pessoas mortas": int(associated["mortos"].sum()) if "mortos" in associated else 0,
                "Feridos graves": int(associated["feridos_graves"].sum()) if "feridos_graves" in associated else 0,
            })
    return pd.DataFrame(rows)


def combined_table(flags: pd.DataFrame) -> pd.DataFrame:
    if flags.empty or not {"fase_dia_oficial", "condicao_metereologica", "mortos", "acidente_fatal"}.issubset(flags):
        return pd.DataFrame()
    working = flags.copy()
    working["Reação registrada"] = working[["Reação tardia", "Ausência de reação"]].any(axis=1)
    working["Gravidade"] = "Sem óbito"
    working.loc[working["acidente_fatal"].fillna(False).astype(bool), "Gravidade"] = "Fatal"
    return (working.groupby(["fase_dia_oficial", "condicao_metereologica", "Reação registrada", "Gravidade"], observed=True)
            .agg(ocorrencias=("mortos", "size"), obitos=("mortos", "sum"))
            .reset_index().loc[lambda frame: frame.ocorrencias.gt(0)])


def scientific_summary(data: pd.DataFrame, flags: pd.DataFrame, name: str) -> str:
    metrics = indicators(data)
    if not metrics["acidentes"]:
        return f"{name}: sem ocorrências elegíveis no período selecionado."
    text = (f"{name}: {metrics['acidentes']} acidentes únicos, {metrics['noturnos']} na plena noite, "
            f"{metrics['diurnos']} no pleno dia e {metrics['obitos']} óbitos. ")
    if metrics["noturnos"] >= 20 and metrics["diurnos"] >= 20:
        text += (f"Óbitos por 100 acidentes: {metrics['taxa_noturna']:.2f} na plena noite e "
                 f"{metrics['taxa_diurna']:.2f} no pleno dia. ")
    else:
        text += "A amostra por fase é pequena para comparar taxas com estabilidade. "
    text += ("Fase do dia, reação e meteorologia são registros observacionais. Exposição ao tráfego, velocidade, "
             "álcool, fadiga e geometria da via também podem explicar diferenças; não há lux nem inventário de iluminação. "
             "A hipótese de visibilidade permanece inconclusiva sem estudo técnico específico.")
    return text


def phase_severity(flags: pd.DataFrame) -> pd.DataFrame:
    """Taxas descritivas e IC Wilson 95% para proporção de acidentes fatais."""
    rows = []
    for phase in ("Plena Noite", "Pleno dia", "Amanhecer", "Anoitecer"):
        group = flags.loc[flags["fase_dia_oficial"].eq(phase)]
        n = len(group)
        if not n:
            continue
        fatal = int(group["acidente_fatal"].sum()) if "acidente_fatal" in group else 0
        deaths = int(group["mortos"].sum()) if "mortos" in group else 0
        severe = int(group["feridos_graves"].sum()) if "feridos_graves" in group else 0
        p = fatal / n
        z = 1.96
        denom = 1 + z*z/n
        center = (p + z*z/(2*n)) / denom
        half = z * sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
        rows.append({"Fase": phase, "Acidentes": n, "Acidentes fatais": fatal,
                     "Óbitos": deaths, "Feridos graves": severe,
                     "Óbitos por 100 acidentes": deaths/n*100,
                     "Fatalidade (%)": p*100, "IC Wilson 95% inferior (%)": max(0, center-half)*100,
                     "IC Wilson 95% superior (%)": min(1, center+half)*100})
    return pd.DataFrame(rows)

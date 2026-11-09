"""Cruzamentos observacionais por ocorrência única para o estudo territorial."""

from __future__ import annotations

import pandas as pd
from math import sqrt

from territorial_case import indicators, normalize_municipality
from ptbr_text import number_ptbr, quantity


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
        return f"{name}: não foram encontrados acidentes para o recorte e período selecionados."
    years = sorted(data["ano"].dropna().astype(int).unique()) if "ano" in data else []
    period = f"Entre {years[0]} e {years[-1]}, " if years else "No período selecionado, "
    text = (f"{period}o recorte {name} registrou {quantity(metrics['acidentes'], 'acidente')} "
            f"({quantity(metrics['noturnos'], 'acidente')} em plena noite e "
            f"{quantity(metrics['diurnos'], 'acidente')} em pleno dia) e {quantity(metrics['obitos'], 'óbito')}. ")
    if metrics["noturnos"] >= 20 and metrics["diurnos"] >= 20:
        night_rate = number_ptbr(metrics['taxa_noturna'], 2)
        day_rate = number_ptbr(metrics['taxa_diurna'], 2)
        text += (f"Óbitos por 100 acidentes: {night_rate} na plena noite e "
                 f"{day_rate} no pleno dia. ")
        if metrics['taxa_diurna'] > 0:
            text += (f"A razão entre essas taxas foi aproximadamente "
                     f"{number_ptbr(metrics['taxa_noturna']/metrics['taxa_diurna'], 2)}. ")
        text += ("A diferença descreve mortes por acidente registrado; não mede risco por veículo em circulação "
                 "nem demonstra causalidade da ausência de iluminação. ")
    else:
        text += "A amostra por fase é pequena para comparar taxas com estabilidade. "
    if metrics["acidentes"] < 200:
        text += "O tamanho da amostra territorial torna as taxas especialmente instáveis. "
    table = mechanism_table(flags) if flags is not None and not flags.empty else pd.DataFrame()
    if not table.empty:
        comparisons = []
        differences = []
        for factor in ("Reação tardia", "Ausência de reação"):
            rows = table.loc[table["Fator registrado"].eq(factor)].set_index("Fase")
            if all(phase in rows.index and rows.loc[phase, "Denominador de acidentes"] >= 20 for phase in ("Plena Noite", "Pleno dia")):
                night, day = rows.loc["Plena Noite"], rows.loc["Pleno dia"]
                comparisons.append(f"{factor.lower()}: {quantity(night['Ocorrências associadas'], 'ocorrência')} de "
                                   f"{number_ptbr(night['Denominador de acidentes'])} ({number_ptbr(night['Participação (%)'], 1)}%) "
                                   f"na plena noite e {quantity(day['Ocorrências associadas'], 'ocorrência')} de "
                                   f"{number_ptbr(day['Denominador de acidentes'])} ({number_ptbr(day['Participação (%)'], 1)}%) no pleno dia")
                differences.append(abs(night["Participação (%)"] - day["Participação (%)"]))
        if comparisons:
            text += "Causas associadas registradas pela PRF: " + "; ".join(comparisons) + ". "
            if len(differences) == 2 and max(differences) < 2:
                text += ("As proporções dessas categorias foram semelhantes entre as fases; os registros não "
                         "demonstram aumento expressivo no período noturno. ")
    text += ("Fase do dia, reação e meteorologia são registros observacionais. Alcance dos faróis, contraste, "
             "distância de percepção, identificação de obstáculos, decisão e frenagem são mecanismos físicos possíveis; "
             "a PRF não mediu esses mecanismos nem lux. Velocidade, álcool, fadiga, falhas mecânicas, pista, chuva, "
             "neblina, ofuscamento, geometria e exposição ao tráfego podem influir; a hipótese de visibilidade "
             "exige estudo técnico específico e não comprova eficácia de uma intervenção não instalada.")
    return text


def mortality_explanation(flags: pd.DataFrame | None, accidents: int) -> str:
    """Distingue zero observado, ausência de registros e mortalidade não informada."""
    if not accidents:
        return "Não foram encontrados acidentes para o recorte e período selecionados."
    if flags is None or "mortos" not in flags or flags["mortos"].notna().sum() != len(flags):
        return "Óbitos não informados nos dados disponíveis; não é possível calcular a mortalidade por fase."
    if pd.to_numeric(flags["mortos"], errors="coerce").sum() == 0:
        return (f"Nenhum óbito registrado nos {quantity(accidents, 'acidente')} analisados no período selecionado. "
                "Os indicadores de mortalidade são iguais a zero para todas as fases do dia. "
                "Isso não significa ausência de acidentes ou de outros danos.")
    return ""


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

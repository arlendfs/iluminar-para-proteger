"""Recortes auditáveis do estudo extensionista de Vila Velha.

A malha de 2025 do IBGE é aberta somente quando o estudo de caso é solicitado.
O rótulo PRF sem coordenadas permanece elegível para tabelas, nunca para mapa.
"""

from __future__ import annotations

import gzip
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from shapely import covers, points
from shapely.geometry import shape

from config import (
    CENARIOS_ORCAMENTO, COMMUNITY_CONFIG, DEFAULT_COMPRIMENTO_TRECHO_KM,
    DEFAULT_SPACING_M, FINANCIAL_PARAMS,
)
from financial_model import calcular_orcamento_cenarios, dimensionar_postes
from segmentation import create_road_segments, rank_segments


MALHA_PATH = Path(__file__).parent / "assets" / "ibge_rmgv_2025.geojson.gz"
MALHA_SOURCE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2025/UFs/ES/ES_Municipios_2025.zip"
)
METRO_SOURCE = "https://planometropolitano.es.gov.br/comdevit"
BR447_SOURCE = "https://www.gov.br/dnit/pt-br/assuntos/noticias/obras-da-br-447-es-atingem-90-de-conclusao-com-entrega-prevista-para-dezembro"
METRO_MUNICIPALITIES = frozenset({
    "VILA VELHA", "VITORIA", "CARIACICA", "VIANA", "SERRA", "GUARAPARI", "FUNDAO"
})
SCOPE_VILA = "Vila Velha — ocorrências municipais"
SCOPE_ENTORNO = "Corredores do entorno de Vila Velha"
SCOPE_METRO = "Região Metropolitana da Grande Vitória"
SCOPE_ES = "Espírito Santo"
SCOPE_BRASIL = "Brasil — referência nacional"
SCOPES = (SCOPE_VILA, SCOPE_ENTORNO, SCOPE_METRO, SCOPE_ES, SCOPE_BRASIL)
CORRIDOR_BRS = frozenset({"101", "262", "447"})


def normalize_municipality(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value).upper())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def municipal_mesh() -> tuple[dict, dict]:
    """Retorna GeoJSON para mapa e geometrias EPSG:4326 para validação."""
    with gzip.open(MALHA_PATH, "rt", encoding="utf-8") as source:
        geojson = json.load(source)
    geometries = {
        feature["properties"]["codigo_ibge"]: shape(feature["geometry"])
        for feature in geojson["features"]
    }
    return geojson, geometries


@lru_cache(maxsize=1)
def state_geometry():
    return shape(municipal_mesh()[0]["es_geometry"])


def principal_period(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty or "ano" not in data:
        return data.iloc[0:0]
    years = set(COMMUNITY_CONFIG["periodo_principal"])
    if set(data["ano"].dropna().unique()).issubset(years):
        return data
    return data.loc[data["ano"].isin(years)]


def territorial_audit(data: pd.DataFrame) -> pd.DataFrame:
    """Classifica registros ES sem alterar a base nacional ou inventar pontos.

    Um ponto dentro da malha prevalece sobre município textual divergente. Um
    rótulo municipal sem coordenada é mantido apenas para análise tabular.
    """
    columns = ["municipio_prf", "municipio_normalizado", "coordenada_valida", "dentro_es", "es_elegivel",
               "dentro_vila_velha", "dentro_metropole", "municipio_por_coordenada",
               "divergencia_municipio_coordenada", "vila_elegivel", "metro_elegivel",
               "entorno_elegivel", "situacao_localizacao"]
    if data.empty or not {"uf", "municipio"}.issubset(data):
        return pd.DataFrame(index=data.iloc[0:0].index, columns=columns)
    es = data.loc[data["uf"].astype(str).str.upper().eq("ES")]
    audit = pd.DataFrame(index=es.index)
    audit["municipio_prf"] = es["municipio"]
    audit["municipio_normalizado"] = es["municipio"].map(normalize_municipality)
    lat = pd.to_numeric(es["latitude"], errors="coerce") if "latitude" in es else pd.Series(np.nan, index=es.index)
    lon = pd.to_numeric(es["longitude"], errors="coerce") if "longitude" in es else pd.Series(np.nan, index=es.index)
    valid = lat.between(-34, 5.5) & lon.between(-74, -32)
    audit["coordenada_valida"] = valid
    audit["municipio_por_coordenada"] = ""
    audit["dentro_vila_velha"] = False
    audit["dentro_metropole"] = False
    audit["dentro_es"] = False
    if valid.any():
        geojson, geometries = municipal_mesh()
        geo = es.loc[valid]
        xy = points(lon.loc[valid].to_numpy(), lat.loc[valid].to_numpy())
        audit.loc[geo.index, "dentro_es"] = covers(state_geometry(), xy)
        for code, geom in geometries.items():
            inside = covers(geom, xy)
            if inside.any():
                name = next(feature["properties"]["municipio"] for feature in municipal_mesh()[0]["features"]
                            if feature["properties"]["codigo_ibge"] == code)
                matched = geo.index[inside]
                audit.loc[matched, "municipio_por_coordenada"] = normalize_municipality(name)
                audit.loc[matched, "dentro_metropole"] = True
                if code == COMMUNITY_CONFIG["codigo_ibge"]:
                    audit.loc[matched, "dentro_vila_velha"] = True
    label_vila = audit["municipio_normalizado"].eq("VILA VELHA")
    label_metro = audit["municipio_normalizado"].isin(METRO_MUNICIPALITIES)
    known_point = audit["municipio_por_coordenada"].ne("")
    audit["divergencia_municipio_coordenada"] = (
        (known_point & audit["municipio_normalizado"].ne(audit["municipio_por_coordenada"]))
        | (valid & label_vila & ~audit["dentro_vila_velha"])
        | (valid & label_metro & ~audit["dentro_metropole"])
        | (valid & ~audit["dentro_es"])
    )
    audit["es_elegivel"] = audit["dentro_es"] | ~valid
    audit["vila_elegivel"] = audit["dentro_vila_velha"] | (label_vila & ~valid)
    audit["metro_elegivel"] = audit["dentro_metropole"] | (label_metro & ~valid)
    br = es["br"].astype(str).str.replace(r"\D", "", regex=True) if "br" in es else pd.Series("", index=es.index)
    audit["entorno_elegivel"] = audit["metro_elegivel"] & ~audit["vila_elegivel"] & br.isin(CORRIDOR_BRS)
    audit["situacao_localizacao"] = np.select(
        [audit["dentro_vila_velha"], audit["vila_elegivel"],
         audit["entorno_elegivel"], audit["metro_elegivel"]],
        ["Vila Velha: coordenada confirmada", "Vila Velha: apenas município PRF",
         "Entorno metropolitano", "Outro município metropolitano"],
        default="Fora do recorte metropolitano",
    )
    return audit


def select_scope(data: pd.DataFrame, audit: pd.DataFrame, scope: str) -> pd.DataFrame:
    if scope == SCOPE_BRASIL:
        return data
    if scope == SCOPE_ES:
        return data.loc[audit.index[audit["es_elegivel"].fillna(False)]]
    mask_column = {
        SCOPE_VILA: "vila_elegivel", SCOPE_ENTORNO: "entorno_elegivel",
        SCOPE_METRO: "metro_elegivel",
    }.get(scope)
    if mask_column is None:
        raise ValueError(f"Recorte desconhecido: {scope}")
    return data.loc[audit.index[audit[mask_column].fillna(False)]]


def indicators(data: pd.DataFrame) -> dict:
    """Métricas de ocorrência única exclusivamente do quadro recebido."""
    count = int(data["id"].nunique()) if "id" in data else len(data)
    night = data["fase_dia_oficial"].eq("Plena Noite") if "fase_dia_oficial" in data else pd.Series(False, index=data.index)
    day = data["fase_dia_oficial"].eq("Pleno dia") if "fase_dia_oficial" in data else pd.Series(False, index=data.index)
    deaths = int(data["mortos"].sum()) if "mortos" in data else 0
    severe = int(data["feridos_graves"].sum()) if "feridos_graves" in data else 0
    mild = int(data["feridos_leves"].sum()) if "feridos_leves" in data else 0
    fatal = int(data["acidente_fatal"].sum()) if "acidente_fatal" in data else 0
    night_count, day_count = int(night.sum()), int(day.sum())
    return {
        "acidentes": count, "noturnos": night_count, "diurnos": day_count,
        "obitos": deaths, "feridos_graves": severe, "feridos_leves": mild,
        "acidentes_fatais": fatal,
        "percentual_fatais": fatal / count * 100 if count else None,
        "obitos_por_100": deaths / count * 100 if count else None,
        "taxa_noturna": float(data.loc[night, "mortos"].sum()) / night_count * 100 if night_count else None,
        "taxa_diurna": float(data.loc[day, "mortos"].sum()) / day_count * 100 if day_count else None,
    }


def cause_counts(data: pd.DataFrame, causes: pd.DataFrame) -> pd.DataFrame:
    if data.empty or causes is None or causes.empty or not {"id", "causa_acidente"}.issubset(causes):
        return pd.DataFrame(columns=["causa_acidente", "ocorrencias_associadas"])
    selected = causes.loc[causes["id"].isin(data["id"]), ["id", "causa_acidente"]].drop_duplicates()
    return (selected.groupby("causa_acidente", observed=True)["id"].nunique()
            .sort_values(ascending=False).rename("ocorrencias_associadas").reset_index())


def local_ranking(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame()
    segments, _ = create_road_segments(data)
    return rank_segments(segments, top_n=len(segments)) if not segments.empty else pd.DataFrame()


def projection_eligible(data: pd.DataFrame, ranking: pd.DataFrame) -> bool:
    """Guarda operacional; não confere validade causal à projeção."""
    metrics = indicators(data)
    return metrics["acidentes"] >= 200 and metrics["noturnos"] >= 30 and len(ranking) >= 5


def simulate_selected_segments(
    data: pd.DataFrame, selected_segments: pd.DataFrame, scenario_id: str,
    spacing_m: float = DEFAULT_SPACING_M,
) -> dict:
    """Custos locais sempre; VPL exploratório apenas com amostra suficiente."""
    if selected_segments.empty:
        return {}
    if scenario_id not in CENARIOS_ORCAMENTO:
        raise ValueError(f"Cenário desconhecido: {scenario_id}")
    scenario = CENARIOS_ORCAMENTO[scenario_id]
    count = len(selected_segments)
    dimension = dimensionar_postes(DEFAULT_COMPRIMENTO_TRECHO_KM, spacing_m, count)
    posts = dimension["total_postes"]
    unit = float(scenario["custo_unitario_total"])
    years = FINANCIAL_PARAMS["vida_util_anos"]
    maintenance = posts * FINANCIAL_PARAMS["custo_manutencao_anual_por_poste"]
    replacements = posts * FINANCIAL_PARAMS["custo_substituicao_bateria_un"] * (
        (years - 1) // FINANCIAL_PARAMS["intervalo_substituicao_bateria_anos"]
    )
    result = {
        "cenario": scenario["nome"], "segmentos": count,
        "extensao_km": count * DEFAULT_COMPRIMENTO_TRECHO_KM,
        "espacamento_m": spacing_m, "postes": posts, "custo_unitario": unit,
        "capex": posts * unit, "manutencao_anual": maintenance,
        "reserva_reposicoes_baterias_15_anos": replacements,
        "horizonte_anos": years, "taxa_desconto": FINANCIAL_PARAMS["taxa_desconto_anual"],
        "vpl_exploratorio_disponivel": False, "sensibilidade": {},
    }
    if projection_eligible(data, selected_segments):
        for reduction in (0.20, 0.35, 0.50):
            simulated = calcular_orcamento_cenarios(
                selected_segments, n_trechos=count,
                comprimento_km=DEFAULT_COMPRIMENTO_TRECHO_KM,
                espacamento_m=spacing_m,
                anos_base_dados=max(int(data["ano"].nunique()), 1),
                taxa_reducao=reduction,
                taxa_desconto=FINANCIAL_PARAMS["taxa_desconto_anual"],
                anos_vida_util=years,
                cenarios_dict={scenario_id: scenario},
            )
            result["sensibilidade"][reduction] = simulated["resumos_cenarios"][scenario_id]["vpl"]
        result["vpl_exploratorio_disponivel"] = True
    return result


def territorial_diagnostics(audit: pd.DataFrame) -> dict:
    return {
        "rotulo_vila": int(audit["municipio_normalizado"].eq("VILA VELHA").sum()),
        "vila_confirmada": int(audit["dentro_vila_velha"].sum()),
        "vila_sem_coordenada": int((audit["vila_elegivel"] & ~audit["coordenada_valida"]).sum()),
        "divergencias": int(audit["divergencia_municipio_coordenada"].sum()),
        "coordenadas_invalidas_es": int((~audit["coordenada_valida"]).sum()),
        "pontos_prf_es_fora_malha_es": int((audit["coordenada_valida"] & ~audit["dentro_es"]).sum()),
        "rotulo_vila_ponto_fora": int((audit["municipio_normalizado"].eq("VILA VELHA") & audit["coordenada_valida"] & ~audit["dentro_vila_velha"]).sum()),
        "ponto_vila_rotulo_outro": int((audit["dentro_vila_velha"] & audit["municipio_normalizado"].ne("VILA VELHA")).sum()),
    }

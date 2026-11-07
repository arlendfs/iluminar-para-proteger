"""Confronto exploratório PRF × traçado SNV/DNIT no Espírito Santo.

O traçado espelha a camada DNIT do Geobases ES, versão SNV 202507A.
Distâncias são planas em SIRGAS 2000 / UTM 24S (EPSG:31984).
"""

from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform


SOURCE = "https://gis.geobases.es.gov.br/server/rest/services/gb/DNIT_Rodovias_Federais_ES/MapServer/0"
ASSET = Path(__file__).parent / "assets" / "dnit_es_snv_202507a.geojson.gz"
ROAD_TOLERANCE_M = 100.0  # triagem, não precisão cadastral ou confirmação de pista
KM_TOLERANCE = 1.0  # tolera mudanças de marco quilométrico e arredondamento


@lru_cache(maxsize=1)
def road_geojson():
    with gzip.open(ASSET, "rt", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def road_geometry():
    geojson = road_geojson()
    projector = Transformer.from_crs("EPSG:4326", "EPSG:31984", always_xy=True).transform
    grouped = {}
    for feature in geojson["features"]:
        props = feature["properties"]
        br = str(props["vl_br"]).zfill(3)
        grouped.setdefault(br, []).append((
            transform(projector, shape(feature["geometry"])),
            float(props["vl_km_inic"]), float(props["vl_km_fina"]),
        ))
    return grouped, projector


def audit_road_positions(data: pd.DataFrame) -> pd.DataFrame:
    """Distância ao traçado da BR informada; KM testado separadamente.

    Um ponto perto da linha pode ainda estar incorreto ou em segmento alterado.
    """
    result = pd.DataFrame(index=data.index, columns=[
        "distancia_rodovia_m", "br_proxima", "km_compativel_snv",
        "situacao_rodovia", "coordenada_repetida", "coordenada_arredondada",
    ])
    if data.empty:
        return result
    grouped, projector = road_geometry()
    pairs = data[["latitude", "longitude"]].apply(pd.to_numeric, errors="coerce")
    valid = pairs.notna().all(axis=1) & pairs["latitude"].between(-34, 5.5) & pairs["longitude"].between(-74, -32)
    frequency = pairs.loc[valid].groupby(["latitude", "longitude"], dropna=False).size()
    result["coordenada_repetida"] = False
    result["coordenada_arredondada"] = False
    result["km_compativel_snv"] = pd.NA
    result["situacao_rodovia"] = "Informação geográfica insuficiente"
    for idx in data.index[valid]:
        latitude, longitude = pairs.loc[idx, ["latitude", "longitude"]]
        result.at[idx, "coordenada_repetida"] = frequency.loc[(latitude, longitude)] > 1
        result.at[idx, "coordenada_arredondada"] = (
            abs(latitude - round(latitude, 3)) < 1e-10
            and abs(longitude - round(longitude, 3)) < 1e-10
        )
        br_value = pd.to_numeric(data.at[idx, "br"], errors="coerce")
        br = str(int(br_value)).zfill(3) if pd.notna(br_value) else ""
        lines = grouped.get(br)
        if not lines:
            result.at[idx, "situacao_rodovia"] = "BR sem traçado disponível no recorte SNV"
            continue
        point = Point(*projector(longitude, latitude))
        nearest = min(lines, key=lambda item: item[0].distance(point))
        distance = float(nearest[0].distance(point))
        result.at[idx, "distancia_rodovia_m"] = round(distance, 1)
        result.at[idx, "br_proxima"] = br
        km = pd.to_numeric(data.at[idx, "km"], errors="coerce")
        matches = bool(pd.notna(km) and min(nearest[1:]) - KM_TOLERANCE <= km <= max(nearest[1:]) + KM_TOLERANCE)
        result.at[idx, "km_compativel_snv"] = matches if pd.notna(km) else pd.NA
        if distance > ROAD_TOLERANCE_M:
            status = "Divergência não resolvida: distante da BR informada"
        elif result.at[idx, "coordenada_arredondada"]:
            status = "Localização aproximada: coordenada arredondada"
        elif not matches:
            status = "BR próxima; KM incompatível com segmento SNV mais próximo"
        else:
            status = "Correspondência com rodovia plausível"
        result.at[idx, "situacao_rodovia"] = status
    return result

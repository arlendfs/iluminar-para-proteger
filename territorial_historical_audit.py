"""Event-level PRF × historical DNIT SNV ES spatial screening.

The SNV version code identifies a reference month, not a verified publication
or road opening date. A positive spatial match is therefore never automatically
called an operational or historical confirmation.
"""

from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

from territorial_road_audit import KM_TOLERANCE, ROAD_TOLERANCE_M


ROOT = Path(__file__).parent
ASSET_DIR = ROOT / "assets" / "snv_es_historico"
MANIFEST = ROOT / "assets" / "snv_es_historico_manifest.json"


@lru_cache(maxsize=1)
def historical_geometry():
    versions = sorted(entry["version"] for entry in json.loads(MANIFEST.read_text(encoding="utf-8"))["versions"])
    projector = Transformer.from_crs("EPSG:4326", "EPSG:31984", always_xy=True).transform
    return versions, projector


@lru_cache(maxsize=8)
def _version_roads(version: str, br: str):
    _, projector = historical_geometry()
    with gzip.open(ASSET_DIR / f"{version}.geojson.gz", "rt", encoding="utf-8") as handle:
        features = json.load(handle)["features"]
    return [(transform(projector, shape(feature["geometry"])), feature["properties"])
            for feature in features if str(feature["properties"]["vl_br"]).zfill(3) == br]


def reference_version(date: pd.Timestamp, versions: list[str]) -> tuple[str | None, int | None]:
    if pd.isna(date):
        return None, None
    event_month = date.year * 12 + date.month
    # The release day is unknown, so even a same-month snapshot could postdate
    # the crash. Use only an earlier reference month.
    candidates = [v for v in versions if int(v[:4]) * 12 + int(v[4:6]) < event_month]
    if not candidates:
        return None, None
    version = candidates[-1]
    lag = event_month - (int(version[:4]) * 12 + int(version[4:6]))
    return version, lag


def audit_historical_positions(data: pd.DataFrame, geographic_municipality: pd.Series | None = None) -> pd.DataFrame:
    versions, projector = historical_geometry()
    rows = []
    for idx, row in data.iterrows():
        date = pd.to_datetime(row.get("data_inversa"), errors="coerce")
        version, lag = reference_version(date, versions)
        lat = pd.to_numeric(row.get("latitude"), errors="coerce")
        lon = pd.to_numeric(row.get("longitude"), errors="coerce")
        km = pd.to_numeric(row.get("km"), errors="coerce")
        br_value = pd.to_numeric(row.get("br"), errors="coerce")
        br = str(int(br_value)).zfill(3) if pd.notna(br_value) else ""
        event_id = row.get("id")
        if pd.notna(event_id) and isinstance(event_id, (int, float)) and float(event_id).is_integer():
            event_id = str(int(event_id))
        result = {"id": event_id, "data": date.date().isoformat() if pd.notna(date) else None,
                  "municipio_prf": row.get("municipio"),
                  "municipio_geografico": geographic_municipality.get(idx) if geographic_municipality is not None else None,
                  "br": br, "km": km, "latitude": lat, "longitude": lon,
                  "versao_snv": version, "defasagem_referencia_meses": lag,
                  "situacao_historica": None, "distancia_tracado_m": None,
                  "status_localizacao": "Informação insuficiente", "justificativa": ""}
        if version is None:
            result["justificativa"] = "Data ausente ou anterior à primeira referência SNV disponível."
        elif pd.isna(lat) or pd.isna(lon) or not (-34 <= lat <= 5.5 and -74 <= lon <= -32):
            result["justificativa"] = "Coordenada ausente ou numericamente inválida."
        elif not br or pd.isna(km):
            result["justificativa"] = "BR ou KM ausente."
        elif not _version_roads(version, br):
            result["justificativa"] = "BR sem traçado na versão SNV ES selecionada."
        else:
            point = transform(projector, Point(float(lon), float(lat)))
            geometry, props = min(_version_roads(version, br), key=lambda pair: pair[0].distance(point))
            distance = geometry.distance(point)
            result["distancia_tracado_m"] = round(distance, 1)
            result["situacao_historica"] = props.get("ds_legenda") or props.get("ds_sup_fed")
            km_match = float(props["vl_km_inic"]) - KM_TOLERANCE <= km <= float(props["vl_km_fina"]) + KM_TOLERANCE
            if distance > ROAD_TOLERANCE_M:
                result["status_localizacao"] = "Divergência identificada"
                result["justificativa"] = f"Distância {distance:.1f} m acima de {ROAD_TOLERANCE_M:g} m para a BR informada."
            elif not km_match:
                result["status_localizacao"] = "Divergência identificada"
                result["justificativa"] = "KM fora do intervalo do traçado mais próximo, com tolerância de 1 km."
            elif str(props.get("ds_sup_fed", "")).upper() == "PLA" or str(props.get("ds_obra", "")).upper() == "EOI":
                result["status_localizacao"] = "Divergência identificada"
                result["justificativa"] = "SNV classifica o trecho mais próximo como planejado ou em obra de implantação; operação não comprovada."
            else:
                result["status_localizacao"] = "Correspondência espacial plausível, sem confirmação histórica"
                result["justificativa"] = "BR, KM e proximidade compatíveis na referência mensal; publicação e operação não comprovadas."
        rows.append(result)
    return pd.DataFrame(rows, index=data.index)


def segment_history_quality(ranking: pd.DataFrame, data: pd.DataFrame, audit: pd.DataFrame) -> pd.DataFrame:
    """Add event-level screening counts to displayed segment rows, without certification."""
    result = ranking.copy()
    if result.empty:
        return result
    br_values = pd.to_numeric(data["br"], errors="coerce")
    km_values = pd.to_numeric(data["km"], errors="coerce")
    labels = []
    for segment in result.itertuples():
        mask = (br_values.eq(pd.to_numeric(segment.br, errors="coerce"))
                & data["uf"].astype(str).eq(str(segment.uf))
                & km_values.between(segment.km_inicio, segment.km_fim, inclusive="left"))
        statuses = audit.loc[data.index[mask], "status_localizacao"].value_counts()
        plausible = int(statuses.get("Correspondência espacial plausível, sem confirmação histórica", 0))
        divergent = int(statuses.get("Divergência identificada", 0))
        insufficient = int(statuses.get("Informação insuficiente", 0))
        labels.append(f"P{plausible}/D{divergent}/I{insufficient}")
    result["triagem_snv"] = labels
    return result

"""Seleção territorial lazy, com malha IBGE 2025 carregada por UF.

Falha na rede nunca transforma rótulo PRF em confirmação espacial.
"""

from __future__ import annotations

import io
import zipfile
from functools import lru_cache

import numpy as np
import pandas as pd
import requests
import shapefile
from shapely import covers, points, union_all
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

from territorial_case import normalize_municipality, municipal_mesh, state_geometry


IBGE_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2025/UFs/{uf}/{uf}_Municipios_2025.zip"
)


@lru_cache(maxsize=4)
def ibge_municipalities(uf: str) -> dict[str, tuple[str, object]]:
    """Retorna código IBGE -> (nome, geometria SIRGAS 2000)."""
    uf = uf.upper()
    response = requests.get(IBGE_URL.format(uf=uf), timeout=40)
    response.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    basename = f"{uf}_Municipios_2025"
    reader = shapefile.Reader(
        shp=io.BytesIO(archive.read(basename + ".shp")),
        dbf=io.BytesIO(archive.read(basename + ".dbf")),
        encoding="utf-8",
    )
    return {
        record.record["CD_MUN"]: (record.record["NM_MUN"], shape(record.shape.__geo_interface__))
        for record in reader.iterShapeRecords()
    }


def municipality_options(data: pd.DataFrame, uf: str) -> list[str]:
    values = data.loc[data["uf"].astype(str).str.upper().eq(uf), "municipio"].dropna()
    labels = {normalize_municipality(value) for value in values.astype(str)}
    if uf == "ES":
        geojson, _ = municipal_mesh()
        official = {normalize_municipality(item["properties"]["municipio"]): item["properties"]["municipio"]
                    for item in geojson["features"]}
    else:
        try:
            official = {normalize_municipality(name): name for name, _ in ibge_municipalities(uf).values()}
        except (requests.RequestException, zipfile.BadZipFile, KeyError, ValueError):
            official = {}
    return sorted((official.get(label, label.title()) for label in labels), key=normalize_municipality)


def select_municipality(data: pd.DataFrame, uf: str, municipality: str) -> tuple[pd.DataFrame, dict]:
    """Prioriza ponto no polígono; usa rótulo apenas quando ponto não existe."""
    subset = data.loc[data["uf"].astype(str).str.upper().eq(uf)]
    label = subset["municipio"].map(normalize_municipality).eq(normalize_municipality(municipality))
    latitude = pd.to_numeric(subset["latitude"], errors="coerce")
    longitude = pd.to_numeric(subset["longitude"], errors="coerce")
    valid = latitude.between(-34, 5.5) & longitude.between(-74, -32)
    try:
        if uf == "ES":
            geojson, compact = municipal_mesh()
            compact_names = {f["properties"]["codigo_ibge"]: f["properties"]["municipio"] for f in geojson["features"]}
            if normalize_municipality(municipality) in {normalize_municipality(value) for value in compact_names.values()}:
                mesh = {code: (compact_names[code], geom) for code, geom in compact.items()}
            else:
                mesh = ibge_municipalities(uf)
        else:
            mesh = ibge_municipalities(uf)
        matched = [(code, geom) for code, (name, geom) in mesh.items()
                   if normalize_municipality(name) == normalize_municipality(municipality)]
        if len(matched) != 1:
            raise LookupError("município não encontrado na malha IBGE")
        code, geom = matched[0]
        inside = pd.Series(False, index=subset.index)
        if valid.any():
            inside.loc[valid] = covers(geom, points(longitude.loc[valid].to_numpy(), latitude.loc[valid].to_numpy()))
        eligible = inside | (label & ~valid)
        return subset.loc[eligible], {
            "codigo_ibge": code, "geometria": geom, "malha_disponivel": True,
            "rotulos_prf": int(label.sum()), "pontos_confirmados": int(inside.sum()),
            "rotulo_externo": int((label & valid & ~inside).sum()),
            "ponto_interno_rotulo_outro": int((inside & ~label).sum()),
            "apenas_rotulo": int((label & ~valid).sum()),
        }
    except (requests.RequestException, zipfile.BadZipFile, LookupError, KeyError, ValueError) as exc:
        return subset.loc[label], {
            "codigo_ibge": None, "geometria": None, "malha_disponivel": False,
            "limite": f"Malha IBGE indisponível: {exc}. Recorte apenas pelo rótulo PRF, sem confirmação espacial.",
        }


def select_territory(
    data: pd.DataFrame, kind: str, uf: str = "ES", municipality: str = "Vila Velha",
    municipalities: tuple[str, ...] = (), distance_km: float = 20.0,
) -> tuple[pd.DataFrame, dict]:
    """Retorna dados e proveniência da seleção, sem alterar a base nacional."""
    if kind == "Brasil":
        return data, {"nome": "Brasil", "uf": None, "codigo_ibge": None, "geometrias": [], "metodo": "base PRF carregada"}
    if kind == "Estado":
        subset = data.loc[data["uf"].astype(str).str.upper().eq(uf)]
        try:
            boundary = state_geometry() if uf == "ES" else union_all([geom for _, geom in ibge_municipalities(uf).values()])
            lat = pd.to_numeric(subset["latitude"], errors="coerce")
            lon = pd.to_numeric(subset["longitude"], errors="coerce")
            valid = lat.between(-34, 5.5) & lon.between(-74, -32)
            inside = pd.Series(False, index=subset.index)
            if valid.any():
                inside.loc[valid] = covers(boundary, points(lon.loc[valid].to_numpy(), lat.loc[valid].to_numpy()))
            selected = subset.loc[inside | ~valid]
            return selected, {"nome": uf, "uf": uf, "codigo_ibge": None, "geometrias": [boundary],
                              "metodo": "UF PRF e polígono estadual derivado da malha IBGE 2025; sem ponto fica apenas o rótulo",
                              "pontos_uf_externos": int((valid & ~inside).sum())}
        except (requests.RequestException, zipfile.BadZipFile, KeyError, ValueError) as exc:
            return subset, {"nome": uf, "uf": uf, "codigo_ibge": None, "geometrias": [],
                            "metodo": f"somente rótulo UF PRF; malha indisponível: {exc}"}
    if kind == "Região Metropolitana":
        if uf != "ES":
            return data.iloc[0:0], {"nome": "Região Metropolitana não cadastrada", "uf": uf, "codigo_ibge": None, "geometrias": [], "metodo": "somente RMGV oficialmente cadastrada"}
        from territorial_case import SCOPE_METRO, select_scope, territorial_audit, municipal_mesh
        audit = territorial_audit(data)
        selected = select_scope(data, audit, SCOPE_METRO)
        _, geoms = municipal_mesh()
        return selected, {"nome": "Região Metropolitana da Grande Vitória", "uf": uf, "codigo_ibge": None,
                          "geometrias": list(geoms.values()), "metodo": "malha IBGE 2025 dos sete municípios da RMGV"}
    names = municipalities if kind == "Municípios selecionados" else (municipality,)
    pieces, details = [], []
    for name in names:
        piece, detail = select_municipality(data, uf, name)
        detail["municipio"] = name
        pieces.append(piece)
        details.append(detail)
    selected = pd.concat(pieces).loc[lambda frame: ~frame.index.duplicated()] if pieces else data.iloc[0:0]
    geometries = [item["geometria"] for item in details if item.get("geometria") is not None]
    if kind == "Entorno de município" and geometries:
        geom = geometries[0]
        longitude = geom.representative_point().x
        zone = int((longitude + 180) // 6) + 1
        projected = Transformer.from_crs("EPSG:4326", f"EPSG:{32700 + zone}", always_xy=True).transform
        boundary = transform(projected, geom.boundary)
        candidates = data.loc[data["uf"].astype(str).str.upper().eq(uf)]
        lat = pd.to_numeric(candidates["latitude"], errors="coerce")
        lon = pd.to_numeric(candidates["longitude"], errors="coerce")
        valid = lat.between(-34, 5.5) & lon.between(-74, -32)
        point_array = points(lon.loc[valid].to_numpy(), lat.loc[valid].to_numpy())
        outside = ~covers(geom, point_array)
        distances = np.array([transform(projected, point).distance(boundary) for point in point_array])
        selected = candidates.loc[valid].loc[outside & (distances <= distance_km * 1000)]
    title = f"Entorno de {municipality} ({distance_km:g} km)" if kind == "Entorno de município" else (
        ", ".join(names) if kind == "Municípios selecionados" else municipality
    )
    return selected, {
        "nome": title, "uf": uf, "codigo_ibge": details[0].get("codigo_ibge") if len(details) == 1 else None,
        "geometrias": geometries, "metodo": "malha IBGE 2025 por coordenadas; rótulo PRF só para pontos ausentes",
        "detalhes": details,
    }

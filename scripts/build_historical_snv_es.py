"""Build compact ES extracts from official DNIT SNV shapefile archives.

Raw ZIPs live in temp/snv_historico (ignored by Git). Never infer a publication
date from the version code or from the cloud file's last-modified timestamp.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import quote

import shapefile


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "temp" / "snv_historico"
OUT = ROOT / "assets" / "snv_es_historico"
MANIFEST = ROOT / "assets" / "snv_es_historico_manifest.json"
SOURCE = "https://servicos.dnit.gov.br/dnitcloud/index.php/s/oTpPRmYs5AAdiNr"
FIELDS = ("vl_br", "sg_uf", "vl_km_inic", "vl_km_fina", "ds_sup_fed",
          "ds_obra", "ds_legenda", "ds_tipo_ad", "ds_superfi", "vl_codigo", "versao_snv")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for archive in sorted(RAW.glob("*.zip")):
        version = archive.stem
        if not re.fullmatch(r"20\d{4}[A-Z]", version):
            continue
        with zipfile.ZipFile(archive) as zipped:
            prefix = f"SNV_{version}"
            reader = shapefile.Reader(
                shp=io.BytesIO(zipped.read(prefix + ".shp")),
                shx=io.BytesIO(zipped.read(prefix + ".shx")),
                dbf=io.BytesIO(zipped.read(prefix + ".dbf")),
                encoding="utf-8", encodingErrors="replace",
            )
            crs = zipped.read(prefix + ".prj").decode("utf-8")
            features = []
            for record in reader.iterShapeRecords():
                props = record.record.as_dict()
                if props.get("sg_uf") != "ES":
                    continue
                features.append({"type": "Feature", "geometry": record.shape.__geo_interface__,
                                 "properties": {key: props.get(key) for key in FIELDS}})
            with gzip.open(OUT / f"{version}.geojson.gz", "wt", encoding="utf-8", compresslevel=9) as handle:
                json.dump({"type": "FeatureCollection", "features": features}, handle,
                          ensure_ascii=False, separators=(",", ":"))
        entries.append({"version": version, "year_reference": int(version[:4]),
                        "month_reference": int(version[4:6]), "raw_filename": archive.name,
                        "raw_bytes": archive.stat().st_size,
                        "raw_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                        "source": SOURCE, "publication_date": None,
                        "direct_url": "https://servicos.dnit.gov.br/dnitcloud/public.php/webdav/" + quote("SNV Bases Geométricas (2013-Atual) (SHP)/" + archive.name),
                        "cloud_modified_is_not_publication_date": True,
                        "source_crs_wkt": crs, "es_features": len(features),
                        "fields_retained": list(FIELDS)})
    if not entries:
        raise FileNotFoundError("No raw SNV archives in temp/snv_historico")
    MANIFEST.write_text(json.dumps({"source": SOURCE, "versions": entries},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(len(entries), sum(item["es_features"] for item in entries),
          sum(path.stat().st_size for path in OUT.glob("*.geojson.gz")))


if __name__ == "__main__":
    main()

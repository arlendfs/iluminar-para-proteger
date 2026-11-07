"""Export reviewable event-level audits from the local PRF sample Parquets."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyzer import AccidentAnalyzer
from territorial_dynamic import select_territory
from territorial_historical_audit import audit_historical_positions


OUT = ROOT / "output" / "auditoria"


def main() -> None:
    analyzer = AccidentAnalyzer()
    names = [f"acidentes{year}_todas_causas_tipos.parquet" for year in range(2021, 2026)]
    analyzer.load_local_files(str(ROOT / "parquet_samples"), names)
    OUT.mkdir(parents=True, exist_ok=True)
    for city, slug in (("Vila Velha", "vila_velha"), ("Vitória", "vitoria")):
        selected, _ = select_territory(analyzer.data, "Município", "ES", city)
        names_by_geometry = selected["municipio"].copy()
        names_by_geometry.loc[:] = city
        names_by_geometry.loc[selected[["latitude", "longitude"]].isna().any(axis=1)] = None
        audit = audit_historical_positions(selected, names_by_geometry)
        path = OUT / f"auditoria_snv_{slug}_2021_2025.csv"
        audit.to_csv(path, sep=";", decimal=",", index=False, encoding="utf-8-sig")
        print(path, len(audit), audit["status_localizacao"].value_counts().to_dict())


if __name__ == "__main__":
    main()

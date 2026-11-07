import pandas as pd

from territorial_dynamic import select_municipality, select_territory


def test_other_municipality_uses_its_own_ibge_polygon():
    cases = pd.DataFrame({
        "id": [1, 2, 3], "uf": ["ES"] * 3,
        "municipio": ["Vila Velha", "Vitória", "Vila Velha"],
        "latitude": [-20.350422, -20.320020, None],
        "longitude": [-40.333519, -40.337780, None],
    })
    selected, details = select_municipality(cases, "ES", "Vitória")
    assert details["codigo_ibge"] == "3205309"
    assert 1 not in selected.id.tolist()
    assert 2 in selected.id.tolist()


def test_year_filter_and_uf_selection_are_explicit():
    cases = pd.DataFrame({"id": [1, 2, 3], "uf": ["ES", "ES", "MG"],
                          "municipio": ["VILA VELHA", "VILA VELHA", "BELO HORIZONTE"],
                          "ano": [2021, 2025, 2025], "latitude": [-20.350422, -20.350422, None],
                          "longitude": [-40.333519, -40.333519, None]})
    selected, meta = select_territory(cases.loc[cases.ano.eq(2025)], "Município", "ES", "Vila Velha")
    assert selected.id.tolist() == [2]
    assert meta["codigo_ibge"] == "3205200"

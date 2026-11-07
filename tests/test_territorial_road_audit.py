import pandas as pd

from territorial_road_audit import audit_road_positions


def test_road_audit_separates_line_proximity_from_missing_geometry():
    cases = pd.DataFrame({
        "br": [447, 447, 999], "km": [12.9, 12.9, 1.0],
        "latitude": [-20.350422, -20.350422, -20.350422],
        "longitude": [-40.333519, -40.333519, -40.333519],
    })
    result = audit_road_positions(cases)
    assert result.loc[0, "distancia_rodovia_m"] < 100
    assert result.loc[0, "coordenada_repetida"]
    assert result.loc[0, "situacao_rodovia"] == "Correspondência com rodovia plausível"
    assert result.loc[2, "situacao_rodovia"] == "BR sem traçado disponível no recorte SNV"


def test_missing_coordinate_is_not_road_confirmed():
    cases = pd.DataFrame({"br": [101], "km": [315.0], "latitude": [None], "longitude": [None]})
    result = audit_road_positions(cases)
    assert pd.isna(result.loc[0, "distancia_rodovia_m"])
    assert result.loc[0, "situacao_rodovia"] == "Informação geográfica insuficiente"

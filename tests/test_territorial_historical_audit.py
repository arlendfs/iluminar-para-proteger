import pandas as pd

from territorial_historical_audit import audit_historical_positions, historical_geometry, reference_version, segment_history_quality


def test_version_precedes_crash_month_when_publication_day_unknown():
    versions = ["202010A", "202101A", "202104A"]
    assert reference_version(pd.Timestamp("2021-01-30"), versions) == ("202010A", 3)
    assert reference_version(pd.Timestamp("2021-02-01"), versions) == ("202101A", 1)


def test_historical_result_never_claims_operational_confirmation():
    versions, _ = historical_geometry()
    assert "202110A" in versions and "202507A" in versions
    sample = pd.DataFrame({"id": [1], "data_inversa": ["2022-07-01"],
                           "municipio": ["VILA VELHA"], "br": [447], "km": [12.8],
                           "latitude": [-20.348], "longitude": [-40.343]})
    result = audit_historical_positions(sample)
    assert result.loc[0, "versao_snv"] == "202206A"
    assert result.loc[0, "status_localizacao"] != "Correspondência histórica confirmada"
    assert result.loc[0, "justificativa"]


def test_segment_quality_counts_each_event_once():
    data = pd.DataFrame({"id": [1, 2], "uf": ["ES", "ES"], "br": [101, 101], "km": [314.1, 314.9]})
    audit = pd.DataFrame({"status_localizacao": ["Divergência identificada",
                                                  "Correspondência espacial plausível, sem confirmação histórica"]})
    ranking = pd.DataFrame({"trecho_id": ["BR-101 KM 314.0 - 316.0"], "uf": ["ES"], "br": [101],
                            "km_inicio": [314.0], "km_fim": [316.0]})
    result = segment_history_quality(ranking, data, audit)
    assert result.loc[0, "triagem_snv"] == "P1/D1/I0"

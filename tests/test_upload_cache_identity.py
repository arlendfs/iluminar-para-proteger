from io import BytesIO

import pandas as pd

from analyzer import AccidentAnalyzer, uploaded_file_digest


def test_upload_with_official_filename_uses_its_own_content():
    upload = BytesIO()
    pd.DataFrame({
        "id": [999999999.0],
        "data_inversa": ["2025-01-01"],
        "uf": ["SP"],
        "br": ["101"],
        "km": ["10,0"],
        "fase_dia": ["Plena Noite"],
        "mortos": [0],
        "causa_acidente": ["Teste distinto"],
    }).to_parquet(upload, index=False)
    upload.seek(0)
    upload.name = "acidentes2025_todas_causas_tipos.parquet"

    analyzer = AccidentAnalyzer()
    result = analyzer.load_data([upload], session_id="teste_identidade_upload")

    assert len(result) == 1
    assert result["id"].iloc[0] == 999999999.0
    assert analyzer.quality_summary["registros_brutos"] == 1


def test_upload_digest_distinguishes_equal_sized_payloads_without_moving_cursor():
    first = BytesIO(b"arquivo A")
    second = BytesIO(b"arquivo B")
    first.seek(3)
    assert uploaded_file_digest(first) != uploaded_file_digest(second)
    assert first.tell() == 3

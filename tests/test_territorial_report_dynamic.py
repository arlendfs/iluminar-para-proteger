from io import BytesIO

import pandas as pd
from pypdf import PdfReader

from territorial_report_dynamic import generate_selected_territory_report
from territorial_science import mechanism_flags
from territorial_platform import territory_pdf_filename
from territorial_report_dynamic import _segment_name
from datetime import datetime


def test_vitoria_report_does_not_inherit_br447_caveat_or_vila_velha_name():
    data = pd.DataFrame({
        "id": [1], "ano": [2025], "uf": ["ES"], "municipio": ["VITÓRIA"],
        "br": [262], "km": [0.5], "latitude": [-20.32], "longitude": [-40.34],
        "fase_dia_oficial": ["Pleno dia"], "mortos": [0], "feridos_graves": [0],
        "feridos_leves": [1], "acidente_fatal": [False],
        "condicao_metereologica": ["Céu Claro"], "tipo_acidente": ["Colisão traseira"],
    })
    flags = mechanism_flags(data, pd.DataFrame(columns=["id", "causa_acidente"]))
    meta = {"nome": "Vitória", "uf": "ES", "codigo_ibge": "3205309",
            "metodo": "teste municipal", "geometrias": []}
    pdf = generate_selected_territory_report(data, data, meta, flags, pd.DataFrame(), {})
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf)).pages)
    assert "Vitória" in text
    assert "Vila Velha" not in text
    assert "BR-447 exige" not in text


def test_pdf_filenames_identify_scope_and_municipality():
    day = datetime(2026, 11, 8)
    assert territory_pdf_filename("Município", "Vila Velha", "ES", "3205200", day) == "relatorio_territorial_municipio_vila_velha_es_3205200_20261108.pdf"
    assert territory_pdf_filename("Estado", "ES", "ES", None, day) == "relatorio_territorial_estado_espirito_santo_es_20261108.pdf"
    assert territory_pdf_filename("Município", "Vitória", "ES", "3205309", day) != territory_pdf_filename("Município", "Vila Velha", "ES", "3205200", day)


def test_portuguese_segment_range_and_rates():
    assert _segment_name("BR-101 (ES) km 314.0 - 316.0") == "BR-101 (ES) km 314,0 a 316,0"

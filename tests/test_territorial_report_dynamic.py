from io import BytesIO

import pandas as pd
from pypdf import PdfReader

from territorial_report_dynamic import generate_selected_territory_report
from territorial_science import mechanism_flags
from territorial_platform import territory_pdf_filename
from territorial_report_dynamic import _segment_name
from territorial_report_dynamic import _phase_figure
from datetime import datetime
from unittest.mock import patch


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


def test_pdf_ranking_shows_all_small_scope_and_declares_large_scope_partial():
    data = pd.DataFrame({"id": [1], "ano": [2025], "uf": ["ES"], "municipio": ["TESTE"],
                         "br": [101], "km": [1.0], "latitude": [-20.3], "longitude": [-40.3],
                         "fase_dia_oficial": ["Pleno dia"], "mortos": [0], "feridos_graves": [0],
                         "feridos_leves": [1], "acidente_fatal": [False]})
    flags = mechanism_flags(data, pd.DataFrame())

    def report(n):
        ranking = pd.DataFrame({"trecho_id": [f"SEG-{i:02d}" for i in range(1, n+1)],
                                "n_acidentes_total": [1] * n, "n_acidentes_noturnos": [0] * n,
                                "score_iluminacao_solar": list(range(n, 0, -1)),
                                "triagem_snv": ["P1/D0/I0"] * n})
        meta = {"nome": "Teste", "uf": "ES", "abrangencia": "Município", "codigo_ibge": "1234567",
                "metodo": "teste", "geometrias": []}
        pdf = generate_selected_territory_report(data, data, meta, flags, ranking, {})
        pages = PdfReader(BytesIO(pdf)).pages
        return "\n".join(page.extract_text() or "" for page in pages), len(pages)

    for n in (9, 6):
        text, _ = report(n)
        assert f"{n} segmentos identificados" in text
        assert f"{n} segmentos apresentados" in text
        assert "Ranking completo" in text
        assert all(f"SEG-{i:02d}" in text for i in range(1, n+1))
    text, pages = report(45)
    assert "45 segmentos identificados" in text
    assert "40 segmentos apresentados" in text
    assert "Ranking parcial" in text
    assert pages >= 2
    assert all(f"SEG-{i:02d}" in text for i in range(1, 41))
    assert "SEG-41" not in text


def test_zero_mortality_figure_has_no_artificial_bars():
    zero = pd.DataFrame({"fase_dia_oficial": ["Plena Noite", "Pleno dia"],
                         "mortos": [0, 0], "feridos_graves": [1, 0], "acidente_fatal": [False, False]})
    with patch("matplotlib.axes.Axes.bar") as bars:
        assert _phase_figure(zero).getvalue().startswith(b"\x89PNG")
    bars.assert_not_called()
    assert _phase_figure(zero.iloc[0:0]).getvalue().startswith(b"\x89PNG")
    missing = zero.copy()
    missing["mortos"] = None
    with patch("matplotlib.axes.Axes.bar") as bars:
        _phase_figure(missing)
    bars.assert_not_called()
    positive = zero.copy()
    positive.loc[0, "mortos"] = 1
    positive.loc[0, "acidente_fatal"] = True
    assert _phase_figure(positive).getvalue().startswith(b"\x89PNG")

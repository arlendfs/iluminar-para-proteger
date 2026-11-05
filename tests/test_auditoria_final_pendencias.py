"""Regressões específicas P01–P08 da auditoria do relatório entregue."""

import io
import re

import pandas as pd
import pytest

from config import REFERENCES
from demographic_analysis import compute_veiculo_analysis
from metrics import compute_day_vs_night_comparison
from pdf_generator import ReportGenerator


@pytest.fixture(scope="module")
def report():
    pymupdf = pytest.importorskip("pymupdf")
    phases = ["Amanhecer", "Plena Noite", "Pleno dia", "Anoitecer"]
    grouped = ["Crepúsculo", "Noturno", "Diurno", "Crepúsculo"]
    oc = pd.DataFrame({
        "id": [1, 2, 3, 4], "ano": [2025] * 4, "ano_mes": ["2025-01"] * 4,
        "data_inversa": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
        "uf": ["PR"] * 4, "br": ["277"] * 4, "km": [10., 11., 12., 13.],
        "fase_dia_oficial": phases, "fase_dia_agrupada": grouped,
        "mortos": [1, 0, 0, 0], "feridos_graves": [0] * 4,
        "feridos_leves": [0] * 4, "total_feridos": [0] * 4,
        "total_vitimas": [1, 0, 0, 0], "acidente_fatal": [1, 0, 0, 0],
    })
    people = pd.DataFrame({
        "id": [1], "pesid": [11], "id_veiculo": [101],
        "tipo_envolvido": ["Nan"], "tipo_veiculo": ["Semireboque"],
        "sexo": ["Não informado"], "idade": [30], "idade_valida_flag": [True],
        "faixa_etaria": ["25 a 34 anos"], "mortos": [1],
        "feridos_graves": [0], "feridos_leves": [0], "ilesos": [0],
    })
    vehicles = pd.DataFrame({"id": [1], "id_veiculo": [101], "tipo_veiculo": ["Semireboque"]})
    causes = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "causa_acidente": ["Reação tardia ou ineficiente do condutor", "Ausência de reação do condutor", "Condutor Dormindo", "Velocidade Incompatível"],
    })
    top = pd.DataFrame({
        "trecho_id": ["BR-277 (PR) KM 10,0 a 12,0"], "n_acidentes_noturnos": [1],
        "mortos_noturno": [0], "feridos_graves_noturno": [0],
        "score_iluminacao_solar": [1.],
    })
    finance = {
        "investimento_total": 89240000., "economia_anual": 237027056.,
        "economia_liquida_anual": 235027056., "vpl": 1905083671.30,
        "tir": 2.63, "payback_simples_anos": .38, "vidas_salvas_ano": 1.,
        "anos_base": 1., "cenarios": {
            "base": {"nome": "Base", "taxa_reducao": .35,
                     "vidas_salvas_ano": 1., "beneficio_anual_bruto": 237027056.,
                     "vpl": 1905083671.30, "payback_simples": .38},
        },
    }
    raw = ReportGenerator().generate_accident_analysis_report(
        oc, top, pessoas_df=people, veiculos_df=vehicles, causas_df=causes,
        financial_summary=finance,
        quality_summary={"data_minima": "2020-01-01", "data_maxima": "2026-12-31"},
    ).getvalue()
    doc = pymupdf.open(stream=raw, filetype="pdf")
    return doc, re.sub(r"\s+", " ", "\n".join(page.get_text() for page in doc))


def test_p01_amanhecer_condicional():
    oc = pd.DataFrame({
        "id": [1, 2], "fase_dia_oficial": ["Amanhecer", "Plena Noite"],
        "fase_dia_agrupada": ["Crepúsculo", "Noturno"], "mortos": [1, 0],
        "feridos_graves": [0, 0], "feridos_leves": [0, 0],
        "total_feridos": [0, 0], "total_vitimas": [1, 0],
        "acidente_fatal": [1, 0],
    })
    wording = compute_day_vs_night_comparison(oc)["texto_interpretativo_fases"]
    assert "hipóteses possíveis" in wording
    assert "não permitem isolar" in wording


def test_p02_unidades_fotometricas(report):
    text = report[1]
    assert re.search(r"\bluminância artificial \(lux\)", text) is None
    assert "iluminância (lux)" in text
    assert "luminância (cd/m²)" in text


def test_p03_rotulos_e_granularidade(report):
    text = report[1]
    assert re.search(r"\bNan\b", text) is None
    fleet_text = text.split("Frota Veicular Predominante:", 1)[1].split("Granularidade:", 1)[0]
    assert "1 óbitos" not in fleet_text
    assert "Semirreboque" in text
    assert "Granularidade:" in text
    vehicles = pd.DataFrame({"id": [1], "id_veiculo": [101], "tipo_veiculo": ["Semireboque"]})
    people = pd.DataFrame({"id": [1], "pesid": [11], "id_veiculo": [101],
                           "tipo_veiculo": ["Semireboque"], "mortos": [1],
                           "feridos_graves": [0], "feridos_leves": [0]})
    summary = compute_veiculo_analysis(vehicles, people)
    assert summary.iloc[0]["total_veiculos"] == 1
    assert summary.iloc[0]["mortos"] == 1


def test_p04_referencias_com_ano_e_edicao(report):
    text = report[1]
    assert "(FHWA-SA-21-050)" in text and "2021." in text
    assert "(IPR-726, 3ª edição)" in text and "2006." in text
    assert "5101:2024" in text and "4ª edição" in text
    assert next(r for r in REFERENCES if "Impactos Sociais" in r["titulo"])["ano"] == 2006


def test_p05_formato_brasileiro(report):
    text = report[1]
    assert "1.800,0 Wh" in text
    assert "0,38 ano" in text
    assert "1800.0 Wh" not in text
    assert "11.25 óbitos" not in text
    assert "1.905.083.671,30" in text


def test_p06_titulo_e_matriz_juntos(report):
    doc = report[0]
    title_pages = [i for i, p in enumerate(doc) if "Matriz de Sensibilidade" in p.get_text()]
    assert len(title_pages) == 1
    page_text = doc[title_pages[0]].get_text()
    assert "Cenário de Análise" in page_text and "Base" in page_text
    assert "CAPEX" in report[1] and "VPL" in report[1] and "15 anos" in report[1]


def test_p07_ranking_exploratorio_e_ressalvas(report):
    text = report[1]
    assert "pesos são heurísticos" in text
    assert "não comprova ausência de iluminação" in text
    for phrase in ["35%", "censo físico de iluminação", "VDMA", "fotométricos"]:
        assert phrase in text


def test_p08_pdf_e_graficos_estruturais(report):
    doc = report[0]
    assert 2 <= len(doc) <= 8
    assert all(p.rect.width > 500 and p.rect.height > 700 for p in doc)
    assert all(len(p.get_text()) > 300 for p in doc)
    assert "EVOLUÇÃO TEMPORAL DOS ACIDENTES" in report[1]
    assert any(page.get_images() for page in doc)


def test_periodo_do_pdf_reflete_apenas_recorte_ativo(report):
    text = report[1]
    assert "2025-01-01 a 2025-01-04" in text
    assert "2020-01-01 a 2026-12-31" not in text


def test_dashboard_e_pdf_formatam_os_mesmos_valores_financeiros(report):
    from dashboard import format_pt_br_currency as dashboard_currency
    from pdf_generator import format_pt_br_currency as pdf_currency

    for value in (89240000., 237027056., 1905083671.30):
        displayed = dashboard_currency(value).replace(" ", "")
        reported = pdf_currency(value).replace("&nbsp;", "").replace(" ", "")
        assert displayed == reported
        assert reported in report[1].replace(" ", "")


def test_c01_rotulos_publicos_aceitam_todos_os_nulos():
    from dashboard import _public_label_series
    values = pd.Series([None, pd.NA, float("nan"), "Nan", "None", "<NA>", "null", "Condutor"])
    result = _public_label_series(values)
    assert result.tolist() == ["Não informado"] * 7 + ["Condutor"]
    assert len(result) == len(values)


def test_c02_formato_pt_br_em_todo_o_texto_cientifico(report):
    text = report[1]
    for forbidden in ("11.25", "12.97", "6.10", "6.79", "1800.0 Wh", "1440.0 Wh", "4.17 noites", "3.33 noites", "864.0 Wh", "0.38 anos"):
        assert forbidden not in text
    for expected in ("1.800,0 Wh", "1.440,0 Wh", "4,17 noites", "3,33 noites", "864,0 Wh", "0,38 ano"):
        assert expected in text


def test_c03_grandezas_fotometricas_no_pdf(report):
    text = report[1]
    assert "iluminância artificial (lux)" in text
    assert "luminância da superfície viária (cd/m²)" in text
    assert re.search(r"(?<!i)luminância artificial \(lux\)", text) is None


def test_c04_discussao_amanhecer_sem_duplicacao(report):
    text = report[1]
    assert "Hipóteses e limitações:" not in text
    assert "fadiga" in text
    assert "não permitem isolar" in text


def test_c05_dps_sem_distancias_universais(report):
    text = report[1]
    assert "30 a 50 metros" not in text
    assert "80 a 140 metros" not in text
    assert "Percepção, Identificação, Emoção e Volição" in text
    assert "atrito" in text and "declividade" in text


def test_c06_auditoria_nao_valida_autenticidade_por_um_caso():
    import inspect
    source = inspect.getsource(ReportGenerator.generate_accident_analysis_report)
    assert "atestando a autenticidade" not in source
    assert "consistência interna" in source
    assert "total rigor estatístico" not in source


def test_c07_score_heuristico_sem_alegacao_causal(report):
    text = report[1]
    assert "pesos são heurísticos" in text
    assert "prioridade muda com as premissas" in text
    assert "não comprova ausência de iluminação" in text
    assert "efeito causal de postes solares" in text


def test_c08_cabecalhos_e_classificacao_financeira(report):
    text = report[1]
    assert "Estimativa Histórica" in text
    assert "Hipótese Conceitual" in text
    assert "Payback Simples" in text
    assert "VPL Social" in text
    assert "Estimativa Historica" not in text
    assert "Hipotese Conceitual" not in text


def test_c09_anos_bibliograficos_especificos(report):
    text = report[1]
    assert "(FHWA-SA-21-050)" in text
    assert "(IPR-726, 3ª edição)" in text
    assert "NBR 5101:2024" in text
    assert {r["ano"] for r in REFERENCES if "Impactos Sociais" in r["titulo"]} == {2006}


def test_c10_conclusao_condicional(report):
    text = report[1]
    assert "pode ampliar as condições de visibilidade" in text
    assert "atu[a] diretamente na extensão do cone visual" not in text
    assert "não correspondendo a faturamento" in text
    assert "projetos-piloto" in text


def test_c11_pdf_visualmente_inspecionavel(report):
    doc = report[0]
    assert all(page.rect.width > 500 and page.rect.height > 700 for page in doc)
    assert any(page.get_images() for page in doc)
    assert all("Página" in page.get_text() for page in doc)

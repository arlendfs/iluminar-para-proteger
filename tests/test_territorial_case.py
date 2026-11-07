from io import BytesIO

import pandas as pd
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

from territorial_case import (
    SCOPES, SCOPE_BRASIL, SCOPE_ENTORNO, SCOPE_ES, SCOPE_METRO,
    SCOPE_VILA, cause_counts, indicators, involvement_counts, local_ranking, municipal_mesh,
    normalize_municipality, projection_eligible, select_scope,
    simulate_selected_segments, territorial_audit,
)
from territorial_pdf import generate_territorial_report


def _sample():
    _, geometries = municipal_mesh()
    vv = geometries["3205200"].representative_point()
    viana = geometries["3205101"].representative_point()
    serra = geometries["3205002"].representative_point()
    rows = [
        (1, "VILA VELHA", "ES", vv.y, vv.x, "101", 310, "Plena Noite", 1),
        (2, "Viana", "ES", vv.y, vv.x, "447", 12, "Pleno dia", 0),
        (3, "Vila Velha", "ES", viana.y, viana.x, "262", 4, "Plena Noite", 2),
        (4, "VILA VELHA", "ES", None, None, "101", 312, "Pleno dia", 0),
        (5, "SERRA", "ES", serra.y, serra.x, "101", 250, "Plena Noite", 0),
        (6, "VILA VELHA", "MG", vv.y, vv.x, "101", 314, "Plena Noite", 9),
    ]
    frame = pd.DataFrame(rows, columns=["id", "municipio", "uf", "latitude", "longitude", "br", "km", "fase_dia_oficial", "mortos"])
    frame["ano"] = 2025
    frame["feridos_graves"] = [1, 0, 0, 0, 0, 0]
    frame["feridos_leves"] = [0, 1, 0, 0, 0, 0]
    frame["total_feridos"] = frame["feridos_graves"] + frame["feridos_leves"]
    frame["total_vitimas"] = frame["total_feridos"] + frame["mortos"]
    frame["acidente_fatal"] = frame["mortos"].gt(0).astype(int)
    frame["fase_dia_agrupada"] = frame["fase_dia_oficial"].map({"Plena Noite": "Noturno", "Pleno dia": "Diurno"})
    frame["tipo_acidente"] = "Colisão"
    return frame


def test_ibge_mesh_and_normalization():
    geojson, polygons = municipal_mesh()
    assert geojson["metadata"]["crs_origem"] == "SIRGAS 2000 / EPSG:4674"
    assert geojson["metadata"]["crs_saida"] == "WGS 84 / EPSG:4326"
    assert len(polygons) == 7 and "3205200" in polygons
    assert normalize_municipality("  Vitória  ") == "VITORIA"
    assert normalize_municipality(None) == ""


def test_geographic_reconciliation_and_separate_scopes():
    data = _sample()
    audit = territorial_audit(data)
    assert audit.loc[0, "dentro_vila_velha"]
    assert audit.loc[1, "divergencia_municipio_coordenada"]
    assert audit.loc[2, "divergencia_municipio_coordenada"]
    assert audit.loc[3, "vila_elegivel"] and not audit.loc[3, "coordenada_valida"]
    assert set(select_scope(data, audit, SCOPE_VILA).id) == {1, 2, 4}
    assert set(select_scope(data, audit, SCOPE_ENTORNO).id) == {3, 5}
    assert set(select_scope(data, audit, SCOPE_METRO).id) == {1, 2, 3, 4, 5}
    assert set(select_scope(data, audit, SCOPE_ES).id) == {1, 2, 3, 4, 5}
    assert set(select_scope(data, audit, SCOPE_BRASIL).id) == {1, 2, 3, 4, 5, 6}
    assert SCOPES[0] == SCOPE_VILA


def test_local_metrics_do_not_import_national_values():
    data = _sample()
    local = select_scope(data, territorial_audit(data), SCOPE_VILA)
    result = indicators(local)
    assert result["acidentes"] == 3
    assert result["noturnos"] == 1 and result["diurnos"] == 2
    assert result["obitos"] == 1
    assert result["acidentes_fatais"] == 1
    assert round(result["percentual_fatais"], 2) == 33.33
    assert round(result["obitos_por_100"], 2) == 33.33
    assert result["taxa_noturna"] == 100
    assert result["taxa_diurna"] == 0
    assert indicators(data)["obitos"] == 12
    assert indicators(local.iloc[:0])["obitos_por_100"] is None


def test_cause_join_deduplicates_only_exact_associations_and_ranks_local():
    data = _sample()
    local = select_scope(data, territorial_audit(data), SCOPE_VILA)
    causes = pd.DataFrame({"id": [1, 1, 1, 2, 3], "causa_acidente": ["Reação", "Reação", "Velocidade", "Reação", "Álcool"]})
    counted = cause_counts(local, causes).set_index("causa_acidente")["ocorrencias_associadas"].to_dict()
    assert counted == {"Reação": 2, "Velocidade": 1}
    ranked = local_ranking(local)
    assert ranked["n_acidentes_total"].sum() == 3
    assert ranked["ranking"].tolist() == list(range(1, len(ranked) + 1))
    assert not ranked["trecho_id"].str.contains("MG").any()


def test_people_are_reused_only_for_selected_occurrences_without_empty_categories():
    data = _sample()
    local = select_scope(data, territorial_audit(data), SCOPE_VILA)
    people = pd.DataFrame({
        "id": [1, 1, 2, 3, 6],
        "tipo_envolvido": pd.Categorical(["Condutor", "Condutor", None, "Pedestre", "Pedestre"],
                                         categories=["Condutor", "Pedestre", "Cavaleiro"]),
    })
    assert involvement_counts(local, people).to_dict() == {"Condutor": 2, "Não informado": 1}


def test_cost_only_when_local_sample_is_small_and_finance_uses_selected_segments():
    data = _sample()
    local = select_scope(data, territorial_audit(data), SCOPE_VILA)
    ranking = local_ranking(local)
    selected = ranking.head(2)
    assert not projection_eligible(local, selected)
    result = simulate_selected_segments(local, selected, "cenario_d")
    assert result["segmentos"] == 2
    assert result["extensao_km"] == 4
    assert result["postes"] == 80
    assert result["capex"] == 80 * 22310
    assert result["vpl_exploratorio_disponivel"] is False
    assert result["sensibilidade"] == {}
    assert simulate_selected_segments(local, ranking.iloc[:0], "cenario_d") == {}


def test_conditional_finance_uses_only_selected_local_segments_and_three_hypotheses():
    data = pd.DataFrame({
        "id": range(200), "ano": [2021 + index % 5 for index in range(200)],
        "fase_dia_oficial": ["Plena Noite" if index % 2 else "Pleno dia" for index in range(200)],
        "mortos": [0] * 200, "feridos_graves": [0] * 200,
        "feridos_leves": [0] * 200, "acidente_fatal": [0] * 200,
    })
    selected = pd.DataFrame({
        "trecho_id": [f"BR-101 KM {index}" for index in range(5)],
        "n_acidentes_noturnos": [20] * 5,
        "mortos_noturno": [1] * 5,
        "feridos_graves_noturno": [2] * 5,
        "feridos_leves_noturno": [3] * 5,
    })
    result = simulate_selected_segments(data, selected, "cenario_d")
    assert result["vpl_exploratorio_disponivel"] is True
    assert list(result["sensibilidade"]) == [0.20, 0.35, 0.50]
    assert result["sensibilidade"][0.20] < result["sensibilidade"][0.35] < result["sensibilidade"][0.50]
    assert result["capex"] == 200 * 22310


def test_local_pdf_reports_separate_local_and_national_counts_and_no_false_activity():
    data = _sample()
    audit = territorial_audit(data)
    local = select_scope(data, audit, SCOPE_VILA)
    causes = cause_counts(local, pd.DataFrame({"id": [1, 2], "causa_acidente": ["Reação", "Velocidade"]}))
    ranking = local_ranking(local)
    finance = simulate_selected_segments(local, ranking.head(1), "cenario_d")
    pdf = generate_territorial_report(SCOPE_VILA, local, data, causes, ranking, ranking.head(1), finance, audit)
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf)).pages)
    assert "3 ocorrências" in text
    assert "Referência nacional indisponível" in text
    assert "6 ocorrências" not in text
    assert "R$ 1.905" not in text
    assert "não foram fornecidas" in text.lower()
    assert "VPL local" in text
    assert "14. Referências" in text


def test_new_module_is_lazy_navigable_and_defaults_to_vila_velha():
    script = """
import pandas as pd
import streamlit as st
from types import SimpleNamespace
from tests.test_territorial_case import _sample
import dashboard
import territorial_platform
territorial_platform.folium_static = lambda *args, **kwargs: None
data = _sample()
analyzer = SimpleNamespace(data=data, filtered_data=data, filtered_causas=pd.DataFrame(), filtered_pessoas=pd.DataFrame())
st.session_state["active_dashboard_module"] = "Estudos Territoriais"
dashboard.create_dashboard(analyzer)
"""
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception
    assert app.radio[0].value == "Estudos Territoriais"
    assert app.selectbox(key="territory_kind").value == "Município"
    assert app.selectbox(key="territory_city").value == "Vila Velha"
    assert app.metric[0].value == "3"


def test_brazil_reference_does_not_recompute_national_ranking_in_case_module():
    script = """
import pandas as pd
import streamlit as st
from types import SimpleNamespace
from tests.test_territorial_case import _sample
import territorial_dashboard as case
ufs = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
base = _sample().iloc[[0]]
data = pd.concat([base.assign(id=index + 100, uf=uf) for index, uf in enumerate(ufs)], ignore_index=True)
st.session_state["vv_scope"] = "Brasil \\u2014 refer\\u00eancia nacional"
case.local_ranking = lambda _: (_ for _ in ()).throw(AssertionError("national ranking was recomputed"))
case.render_territorial_case(SimpleNamespace(data=data, filtered_data=data, filtered_causas=pd.DataFrame(), filtered_pessoas=pd.DataFrame()))
"""
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception
    assert app.selectbox[0].value == SCOPE_BRASIL
    assert not app.get("download_button")


def test_brazil_reference_table_has_one_value_column():
    from territorial_dashboard import _metric_table

    metrics = indicators(_sample())
    assert _metric_table(SCOPE_BRASIL, metrics, metrics, True).columns.tolist() == [
        "Indicador", SCOPE_BRASIL,
    ]

import base64

import numpy as np
import pandas as pd
import plotly.io as pio
from streamlit.testing.v1 import AppTest

import dashboard
from config import (
    COLOR_PALETTE,
    FINANCIAL_CHART_COLORS,
    PHASE_COLORS,
    SEVERITY_COLORS,
    SEX_COLORS,
)


def _figures(test):
    return [pio.from_json(element.proto.spec) for element in test.get("plotly_chart")]


def _numbers(values):
    if isinstance(values, dict):
        return np.frombuffer(base64.b64decode(values["bdata"]), dtype=np.dtype(values["dtype"])).tolist()
    return list(values)


def _contrast(first, second):
    def luminance(value):
        channels = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    a, b = sorted((luminance(first), luminance(second)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def test_semantic_maps_and_dark_theme_contrast():
    assert PHASE_COLORS == {
        "Pleno dia": "#F59E0B", "Diurno": "#F59E0B",
        "Plena Noite": "#38BDF8", "Noturno": "#38BDF8",
        "Amanhecer": "#C4B5FD", "Anoitecer": "#8B5CF6",
        "Crepúsculo": "#A78BFA",
    }
    assert len({PHASE_COLORS[name] for name in ("Pleno dia", "Plena Noite", "Amanhecer", "Anoitecer")}) == 4
    assert [SEVERITY_COLORS[name] for name in ("Óbitos", "Feridos graves", "Feridos leves", "Ilesos", "Não informado")] == [
        "#EF4444", "#F97316", "#FBBF24", "#94A3B8", "#64748B",
    ]
    assert SEX_COLORS["Não informado / Ignorado"] == SEX_COLORS["Ignorado"] == "#94A3B8"
    assert FINANCIAL_CHART_COLORS == {"CAPEX Total (R$ M)": "#F87171", "VPL 15 Anos (R$ M)": "#34D399"}
    assert all(_contrast(color, COLOR_PALETTE["dark"]) >= 3 for color in set(PHASE_COLORS.values()))


def test_active_profile_charts_preserve_values_and_meanings(monkeypatch):
    involvement = pd.DataFrame({
        "tipo_envolvido": ["Condutor", "Pedestre"],
        "mortos": [2, 1], "feridos_graves": [3, 4], "feridos_leves": [5, 6],
        "taxa_mortalidade_pct": [20.0, 10.0],
    })
    monkeypatch.setattr(dashboard, "compute_envolvimento_analysis", lambda _: {"resumo_envolvimento": involvement})
    monkeypatch.setattr(dashboard, "compute_sexo_analysis", lambda _: {"resumo_sexo": pd.DataFrame({
        "sexo": ["Masculino", "Feminino", "Não informado / Ignorado"],
        "total_pessoas": [10, 8, 2], "taxa_mortalidade_pct": [5.0, 3.0, 0.0],
    })})
    app = AppTest.from_string("""
import pandas as pd
from types import SimpleNamespace
import dashboard
analyzer = SimpleNamespace(filtered_pessoas=pd.DataFrame({"present": [1]}), filtered_veiculos=pd.DataFrame(), filtered_data=pd.DataFrame())
dashboard.render_perfil_vitimas(analyzer)
""", default_timeout=30).run()
    assert not app.exception
    severity, rate = _figures(app)
    assert {trace.name: trace.marker.color for trace in severity.data} == {
        "Óbitos": "#EF4444", "Feridos graves": "#F97316", "Feridos leves": "#FBBF24",
    }
    assert {trace.name: _numbers(trace.y) for trace in severity.data} == {
        "Óbitos": [2, 1], "Feridos graves": [3, 4], "Feridos leves": [5, 6],
    }
    assert rate.data[0].marker.color == COLOR_PALETTE["taxa"]

    app.radio[0].set_value("Sexo").run()
    assert not app.exception
    donut, mortality = _figures(app)
    assert dict(zip(donut.data[0].labels, donut.data[0].marker.colors)) == {
        "Masculino": SEX_COLORS["Masculino"],
        "Feminino": SEX_COLORS["Feminino"],
        "Não informado / Ignorado": SEX_COLORS["Não informado / Ignorado"],
    }
    assert {trace.name: trace.marker.color for trace in mortality.data} == {
        "Masculino": SEX_COLORS["Masculino"],
        "Feminino": SEX_COLORS["Feminino"],
        "Não informado / Ignorado": SEX_COLORS["Não informado / Ignorado"],
    }


def test_active_temporal_chart_reuses_phase_colors_across_groupings():
    script = """
import pandas as pd
from types import SimpleNamespace
import dashboard
phases = ["Pleno dia", "Plena Noite", "Amanhecer", "Anoitecer"] * 2
data = pd.DataFrame({
    "id": range(8), "ano": [2024] * 4 + [2025] * 4,
    "mes": [1] * 8, "ano_mes": ["2024-01"] * 4 + ["2025-01"] * 4,
    "fase_dia_oficial": phases,
    "fase_dia_agrupada": ["Diurno", "Noturno", "Crep\\u00fasculo", "Crep\\u00fasculo"] * 2,
    "mortos": [0] * 8, "total_feridos": [1] * 8, "acidente_fatal": [0] * 8,
})
dashboard._render_evolucao_temporal_full(SimpleNamespace(filtered_data=data))
"""
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception
    grouped = _figures(app)[0]
    assert {trace.name: trace.line.color for trace in grouped.data} == {
        name: PHASE_COLORS[name] for name in ("Diurno", "Noturno", "Crepúsculo")
    }
    official_script = script.replace(
        "dashboard._render_evolucao_temporal_full(SimpleNamespace(filtered_data=data))",
        'import streamlit as st\nst.session_state["annual_series"] = "Quatro fases oficiais"\n'
        'dashboard._render_evolucao_temporal_full(SimpleNamespace(filtered_data=data))',
    )
    official_app = AppTest.from_string(official_script, default_timeout=30).run()
    assert not official_app.exception
    official = _figures(official_app)[0]
    assert {trace.name: trace.line.color for trace in official.data} == {
        name: PHASE_COLORS[name] for name in ("Pleno dia", "Plena Noite", "Amanhecer", "Anoitecer")
    }
    monthly_script = script.replace(
        "dashboard._render_evolucao_temporal_full(SimpleNamespace(filtered_data=data))",
        'import streamlit as st\nst.session_state["temporal_view"] = "Evolu\\u00e7\\u00e3o Mensal Detalhada"\n'
        'dashboard._render_evolucao_temporal_full(SimpleNamespace(filtered_data=data))',
    )
    monthly_app = AppTest.from_string(monthly_script, default_timeout=30).run()
    assert not monthly_app.exception
    monthly = _figures(monthly_app)[0]
    assert {trace.name: trace.line.color for trace in monthly.data} == {
        name: PHASE_COLORS[name] for name in ("Pleno dia", "Plena Noite", "Amanhecer", "Anoitecer")
    }


def test_financial_legend_distinguishes_cost_from_social_estimate_without_changing_values():
    scenarios = pd.DataFrame({
        "Cenário": ["A", "B"],
        "CAPEX Total (R$ M)": [2.5, 3.5],
        "VPL 15 Anos (R$ M)": [8.0, 9.0],
    })
    figure = dashboard.financial_comparison_chart(scenarios)
    assert [(trace.name, trace.marker.color, list(trace.y)) for trace in figure.data] == [
        ("CAPEX Total (R$ M)", "#F87171", [2.5, 3.5]),
        ("VPL social estimado (R$ M)", "#34D399", [8.0, 9.0]),
    ]
    assert figure.layout.yaxis.title.text == "R$ milhões"


def test_pdf_charts_use_phase_colors_on_white_with_outlines(monkeypatch):
    import pdf_generator

    figures = []
    original_subplots = pdf_generator.plt.subplots

    def capture(*args, **kwargs):
        figure, axes = original_subplots(*args, **kwargs)
        figures.append(figure)
        return figure, axes

    monkeypatch.setattr(pdf_generator.plt, "subplots", capture)
    generator = pdf_generator.ReportGenerator()
    occurrences = pd.DataFrame({
        "id": [1, 2, 3], "ano_mes": ["2025-01", "2025-02", "2025-02"],
        "fase_dia_agrupada": ["Noturno", "Diurno", "Crepúsculo"],
    })
    assert generator._generate_temporal_chart(occurrences) is not None
    lines = figures[-1].axes[0].lines
    assert {line.get_label(): line.get_color() for line in lines} == {
        "Noturno": PHASE_COLORS["Noturno"], "Diurno": PHASE_COLORS["Diurno"],
        "Crepúsculo": PHASE_COLORS["Crepúsculo"],
    }
    assert len({line.get_linestyle() for line in lines}) == 3
    assert all(line.get_path_effects() for line in lines)

    causes = pd.DataFrame({"id": [1, 2], "causa_acidente": ["Reação tardia", "Reação tardia"]})
    assert generator._generate_reaction_causes_chart(occurrences, causes) is not None
    bars = figures[-1].axes[0].containers
    assert [container.patches[0].get_facecolor() for container in bars] == [
        __import__("matplotlib").colors.to_rgba(PHASE_COLORS["Noturno"]),
        __import__("matplotlib").colors.to_rgba(PHASE_COLORS["Diurno"]),
    ]
    assert _contrast("#334155", "#FFFFFF") >= 4.5

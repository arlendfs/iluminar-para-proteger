"""Regressões da arquitetura modular e da cobertura informacional do painel."""

from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "dashboard.py"


def test_dispatcher_has_the_eight_lazy_modules():
    text = SOURCE.read_text(encoding="utf-8")
    for module in (
        "Visão geral", "Análise científica", "Perfil de vítimas", "Evolução temporal",
        "Trechos e finanças", "Mapa", "Protótipo 3D", "Relatório PDF",
    ):
        assert f'"{module}"' in text
    assert "render_legacy_full_dashboard(analyzer)" not in text


def test_restored_sections_remain_in_the_module_implementations():
    text = SOURCE.read_text(encoding="utf-8")
    for section in (
        "Auditoria metodológica", "Comparação por fase oficial do dia",
        "Estratificação ambiental", "Faixa etária", "Evolução mensal detalhada",
        "Memória de cálculo científico", "Balanço energético", "ABNT NBR 5101:2024",
        "Comparativo de orçamentos A–E", "Dados técnicos completos e exportação",
    ):
        assert section in text


def test_temporal_and_financial_modules_keep_their_full_controls():
    text = SOURCE.read_text(encoding="utf-8")
    for control in (
        "Evolução Anual", "Evolução Mensal Detalhada", "Interpretação da Evolução Temporal",
        "Top 10 estados", "Top 10 causas", "Balanço energético e autonomia",
        "Comparativo Financeiro: Investimento Inicial (CAPEX) vs VPL Social Líquido",
        "Óbitos potencialmente evitáveis/ano",
    ):
        assert control in text
    assert "PRESENTATION_LABELS" in text
    assert "PLOTLY_CONFIG" in text

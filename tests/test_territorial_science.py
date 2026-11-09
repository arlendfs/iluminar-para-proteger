import pandas as pd

from territorial_science import mechanism_flags, mechanism_table, phase_severity, mortality_explanation, scientific_summary


def test_multiple_causes_do_not_duplicate_occurrences():
    accidents = pd.DataFrame({"id": [1, 2], "fase_dia_oficial": ["Plena Noite", "Pleno dia"],
                              "mortos": [1, 0], "feridos_graves": [0, 1],
                              "acidente_fatal": [True, False], "condicao_metereologica": ["Chuva", "Sol"]})
    causes = pd.DataFrame({"id": [1, 1, 1, 2], "causa_acidente": [
        "Reação tardia ou ineficiente do condutor", "Reação tardia ou ineficiente do condutor",
        "Velocidade Incompatível", "Reação tardia ou ineficiente do condutor"]})
    flags = mechanism_flags(accidents, causes)
    assert len(flags) == 2
    table = mechanism_table(flags)
    night = table.loc[table["Fase"].eq("Plena Noite") & table["Fator registrado"].eq("Reação tardia")].iloc[0]
    assert night["Ocorrências associadas"] == 1
    assert night["Denominador de acidentes"] == 1
    severity = phase_severity(flags)
    assert severity.loc[severity.Fase.eq("Plena Noite"), "Óbitos por 100 acidentes"].iloc[0] == 100


def test_mortality_messages_distinguish_zero_missing_and_no_accidents():
    zero = pd.DataFrame({"mortos": [0, 0]})
    assert "Nenhum óbito registrado nos 2 acidentes" in mortality_explanation(zero, 2)
    assert "outros danos" in mortality_explanation(zero, 2)
    assert "Não foram encontrados acidentes" in mortality_explanation(zero, 0)
    assert "não informados" in mortality_explanation(pd.DataFrame({"mortos": [None]}), 1)
    assert mortality_explanation(pd.DataFrame({"mortos": [0, 1]}), 2) == ""


def test_scientific_summary_reports_ratio_without_causal_claim():
    n_night, n_day = 52, 58
    phases = ["Plena Noite"] * n_night + ["Pleno dia"] * n_day
    deaths = [1] * 9 + [0] * (n_night - 9) + [1] * 4 + [0] * (n_day - 4)
    data = pd.DataFrame({"id": range(110), "ano": [2025] * 110, "fase_dia_oficial": phases,
                         "mortos": deaths, "feridos_graves": [0] * 110, "feridos_leves": [0] * 110,
                         "acidente_fatal": [bool(x) for x in deaths]})
    flags = mechanism_flags(data, pd.DataFrame())
    text = scientific_summary(data, flags, "Vila Velha")
    assert "17,31" in text and "6,90" in text and "2,51" in text
    assert "não mede risco por veículo" in text
    assert "tamanho da amostra" in text
    assert "Vila Velha" not in scientific_summary(data, flags, "Outro município")


def test_scientific_summary_reports_similar_reaction_proportions():
    phases = ["Plena Noite"] * 4010 + ["Pleno dia"] * 6836
    data = pd.DataFrame({"id": range(len(phases)), "ano": [2025] * len(phases),
                         "fase_dia_oficial": phases, "mortos": [0] * len(phases),
                         "feridos_graves": [0] * len(phases), "feridos_leves": [0] * len(phases),
                         "acidente_fatal": [False] * len(phases)})
    flags = mechanism_flags(data, pd.DataFrame())
    flags.iloc[:654, flags.columns.get_loc("Reação tardia")] = True
    flags.iloc[4010:4010+1118, flags.columns.get_loc("Reação tardia")] = True
    flags.iloc[:559, flags.columns.get_loc("Ausência de reação")] = True
    flags.iloc[4010:4010+954, flags.columns.get_loc("Ausência de reação")] = True
    text = scientific_summary(data, flags, "Espírito Santo")
    assert all(value in text for value in ("16,3%", "16,4%", "13,9%", "14,0%"))
    assert "proporções dessas categorias foram semelhantes" in text

import pandas as pd

from territorial_science import mechanism_flags, mechanism_table, phase_severity


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

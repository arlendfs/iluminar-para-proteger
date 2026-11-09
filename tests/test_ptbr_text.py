import pytest

from ptbr_text import number_ptbr, quantity


@pytest.mark.parametrize("n,expected", [(0, "0 acidentes"), (1, "1 acidente"), (2, "2 acidentes")])
def test_accident_inflection(n, expected):
    assert quantity(n, "acidente") == expected


@pytest.mark.parametrize("n,expected", [(0, "0 óbitos"), (1, "1 óbito"), (2, "2 óbitos")])
def test_death_inflection(n, expected):
    assert quantity(n, "óbito") == expected


def test_other_inflections_and_brazilian_numbers():
    for singular, plural in (("pessoa morta", "pessoas mortas"), ("ferido grave", "feridos graves"),
                             ("vítima", "vítimas"), ("ocorrência", "ocorrências"),
                             ("segmento", "segmentos"), ("município", "municípios"),
                             ("rodovia", "rodovias"), ("poste", "postes")):
        assert quantity(1, singular) == f"1 {singular}"
        assert quantity(2, singular) == f"2 {plural}"
    assert number_ptbr(1234.56, 2) == "1.234,56"
    assert quantity(1234, "acidente") == "1.234 acidentes"

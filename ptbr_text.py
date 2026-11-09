"""Formatação de quantidades em textos públicos, sem alterar cálculos."""

from __future__ import annotations


PLURALS = {
    "acidente": "acidentes", "óbito": "óbitos", "pessoa morta": "pessoas mortas",
    "ferido": "feridos", "ferido grave": "feridos graves", "ferido leve": "feridos leves",
    "vítima": "vítimas", "ocorrência": "ocorrências", "ocorrência única": "ocorrências únicas",
    "segmento": "segmentos", "município": "municípios", "rodovia": "rodovias",
    "poste": "postes", "acidente fatal": "acidentes fatais",
    "ponto": "pontos", "par distinto": "pares distintos", "divergência": "divergências",
    "associação": "associações", "apontamento": "apontamentos", "sinistro único": "sinistros únicos",
}


def number_ptbr(value: int | float, digits: int = 0) -> str:
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def quantity(value: int, singular: str, plural: str | None = None) -> str:
    count = int(value)
    form = singular if count == 1 else (plural or PLURALS[singular])
    return f"{number_ptbr(count)} {form}"

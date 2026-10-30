"""
Módulo de Viabilidade Econômica, Engenharia Financeira e Dimensionamento Solar.
Calcula CAPEX, OPEX, Benefícios Sociais Anuais, Fluxo de Caixa Descontado,
VPL (NPV), TIR (IRR), Payback Simples e Descontado, e ROI com rigor matemático.
"""

import math
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from config import (
    FINANCIAL_PARAMS,
    EFFECTIVENESS_PARAMS,
    ECONOMIC_VALUES,
    SCENARIOS,
    DEFAULT_SPACING_M,
    DEFAULT_COMPRIMENTO_TRECHO_KM,
    DEFAULT_TRECHOS_TOP_N,
)


def dimensionar_postes(
    comprimento_trecho_km: float,
    espacamento_m: float,
    n_trechos: int,
) -> Dict[str, Any]:
    """
    Calcula a quantidade física de postes solares autônomos.
    Extensão em metros / espaçamento em metros por trecho, arredondado para cima.
    """
    if espacamento_m <= 0 or comprimento_trecho_km <= 0 or n_trechos <= 0:
        return {
            "postes_por_trecho": 0,
            "total_postes": 0,
            "extensao_total_km": 0.0,
            "extensao_total_m": 0.0,
        }

    extensao_m = comprimento_trecho_km * 1000.0
    postes_por_trecho = int(math.ceil(extensao_m / espacamento_m))
    total_postes = postes_por_trecho * n_trechos
    extensao_total_km = comprimento_trecho_km * n_trechos

    return {
        "postes_por_trecho": postes_por_trecho,
        "total_postes": total_postes,
        "extensao_total_km": extensao_total_km,
        "extensao_total_m": extensao_total_km * 1000.0,
    }


def calcular_capex_opex(
    total_postes: int,
    custo_unitario_poste: float = FINANCIAL_PARAMS["custo_poste_solar"],
    custo_manutencao_anual_un: float = FINANCIAL_PARAMS["custo_manutencao_anual_por_poste"],
    custo_bateria_un: float = FINANCIAL_PARAMS["custo_substituicao_bateria_un"],
    anos_vida_util: int = FINANCIAL_PARAMS["vida_util_anos"],
    intervalo_troca_bateria: int = FINANCIAL_PARAMS["intervalo_substituicao_bateria_anos"],
) -> Dict[str, Any]:
    """
    Calcula o investimento inicial (CAPEX) e os custos operacionais anuais (OPEX).
    Considera o ciclo de substituição periódica de baterias nos anos previstos.
    """
    capex_total = total_postes * custo_unitario_poste
    opex_anual_ordinario = total_postes * custo_manutencao_anual_un
    capex_troca_baterias = total_postes * custo_bateria_un

    fluxo_opex = []
    for ano in range(1, anos_vida_util + 1):
        # Nos anos de substituição de baterias (ex: anos 5 e 10), adiciona o custo de reposição
        custo_ano = opex_anual_ordinario
        if ano % intervalo_troca_bateria == 0 and ano < anos_vida_util:
            custo_ano += capex_troca_baterias
        fluxo_opex.append(custo_ano)

    return {
        "capex_total": capex_total,
        "opex_anual_ordinario": opex_anual_ordinario,
        "custo_troca_baterias_ciclo": capex_troca_baterias,
        "fluxo_opex_anual": fluxo_opex,
        "anos_vida_util": anos_vida_util,
    }


def calcular_beneficio_anual_trechos(
    top_segments_df: pd.DataFrame,
    fator_anualizacao: float = 1.0,
    taxa_reducao: float = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"],
    vsl: float = ECONOMIC_VALUES["valor_vida_estatistica"],
    custo_grave: float = ECONOMIC_VALUES["custo_medio_acidente_grave"],
    custo_leve: float = ECONOMIC_VALUES["custo_medio_acidente_leve"],
) -> Dict[str, Any]:
    """
    Calcula os benefícios socioeconômicos anuais esperados com rigor:
    - Aplica a taxa de redução EXCLUSIVAMENTE aos acidentes NOTURNOS elegíveis
      ocorridos nos trechos contemplados no ranking.
    - Normaliza a frequência pelo fator de anualização da base
      (ex: se a base tem 5 anos, divide por 5; se tem 8 meses, divide por 0.67).
    - Evita dupla contagem: fatalidades usam VSL; feridos graves e leves usam seus custos médios.
    """
    if top_segments_df.empty:
        return {
            "beneficio_anual_bruto": 0.0,
            "economia_vidas_ano": 0.0,
            "economia_graves_ano": 0.0,
            "economia_leves_ano": 0.0,
            "vidas_salvas_ano": 0.0,
            "graves_evitados_ano": 0.0,
            "leves_evitados_ano": 0.0,
            "acidentes_noturnos_ano": 0.0,
            "acidentes_evitados_ano": 0.0,
        }

    # Total de vítimas noturnas acumuladas nos trechos do ranking
    mortos_acc = top_segments_df["mortos_noturno"].sum() if "mortos_noturno" in top_segments_df.columns else top_segments_df.get("mortos", 0).sum()
    graves_acc = top_segments_df["feridos_graves_noturno"].sum() if "feridos_graves_noturno" in top_segments_df.columns else top_segments_df.get("feridos_graves", 0).sum()
    leves_acc = top_segments_df["feridos_leves_noturno"].sum() if "feridos_leves_noturno" in top_segments_df.columns else top_segments_df.get("feridos_leves", 0).sum()
    acidentes_acc = top_segments_df["n_acidentes_noturnos"].sum() if "n_acidentes_noturnos" in top_segments_df.columns else top_segments_df.get("n_acidentes", 0).sum()

    # Normalizar para taxa anual: taxa_anual = acumulado / anos_base
    fator = max(fator_anualizacao, 0.08)  # evitar divisão por zero
    mortos_ano = mortos_acc / fator
    graves_ano = graves_acc / fator
    leves_ano = leves_acc / fator
    acidentes_ano = acidentes_acc / fator

    # Vítimas e sinistros potencialmente evitáveis
    vidas_salvas_ano = mortos_ano * taxa_reducao
    graves_evitados_ano = graves_ano * taxa_reducao
    leves_evitados_ano = leves_ano * taxa_reducao
    acidentes_evitados_ano = acidentes_ano * taxa_reducao

    # Valoração econômica anual (IPEA)
    economia_vidas_ano = vidas_salvas_ano * vsl
    economia_graves_ano = graves_evitados_ano * custo_grave
    economia_leves_ano = leves_evitados_ano * custo_leve
    beneficio_anual_bruto = economia_vidas_ano + economia_graves_ano + economia_leves_ano

    return {
        "beneficio_anual_bruto": beneficio_anual_bruto,
        "economia_vidas_ano": economia_vidas_ano,
        "economia_graves_ano": economia_graves_ano,
        "economia_leves_ano": economia_leves_ano,
        "vidas_salvas_ano": vidas_salvas_ano,
        "graves_evitados_ano": graves_evitados_ano,
        "leves_evitados_ano": leves_evitados_ano,
        "acidentes_noturnos_ano": acidentes_ano,
        "acidentes_evitados_ano": acidentes_evitados_ano,
        "mortos_ano_baseline": mortos_ano,
        "graves_ano_baseline": graves_ano,
        "leves_ano_baseline": leves_ano,
    }


def calcular_tir(fluxo_caixa: List[float], guess: float = 0.1, max_iter: int = 100, tol: float = 1e-6) -> Optional[float]:
    """
    Calcula a Taxa Interna de Retorno (TIR) via método numérico de Newton-Raphson.
    Retorna None se o fluxo não convergir ou não possuir inversão de sinal.
    """
    # Verificar se há pelo menos um valor negativo e um positivo
    tem_negativo = any(x < 0 for x in fluxo_caixa)
    tem_positivo = any(x > 0 for x in fluxo_caixa)
    if not (tem_negativo and tem_positivo):
        return None

    r = guess
    for _ in range(max_iter):
        npv = 0.0
        d_npv = 0.0
        for t, cf in enumerate(fluxo_caixa):
            factor = (1.0 + r) ** t
            if factor == 0:
                return None
            npv += cf / factor
            if t > 0:
                d_npv -= (t * cf) / ((1.0 + r) ** (t + 1))
        
        if abs(npv) < tol:
            return r
        if abs(d_npv) < 1e-12:
            break
        r_novo = r - npv / d_npv
        if r_novo <= -1.0 or r_novo > 10.0:  # limites econômicos razoáveis
            break
        r = r_novo

    # Busca binária como fallback
    low, high = -0.9, 5.0
    for _ in range(100):
        mid = (low + high) / 2.0
        npv_mid = sum(cf / ((1.0 + mid) ** t) for t, cf in enumerate(fluxo_caixa))
        if abs(npv_mid) < tol:
            return mid
        # Avaliar inclinação
        npv_low = sum(cf / ((1.0 + low) ** t) for t, cf in enumerate(fluxo_caixa))
        if (npv_mid > 0 and npv_low > 0) or (npv_mid < 0 and npv_low < 0):
            low = mid
        else:
            high = mid

    return r if abs(sum(cf / ((1.0 + r) ** t) for t, cf in enumerate(fluxo_caixa))) < 1000.0 else None


def avaliar_viabilidade_economica(
    top_segments_df: pd.DataFrame,
    n_trechos: int = DEFAULT_TRECHOS_TOP_N,
    comprimento_km: float = DEFAULT_COMPRIMENTO_TRECHO_KM,
    espacamento_m: float = DEFAULT_SPACING_M,
    custo_poste: float = FINANCIAL_PARAMS["custo_poste_solar"],
    custo_manutencao_anual_un: float = FINANCIAL_PARAMS["custo_manutencao_anual_por_poste"],
    taxa_desconto: float = FINANCIAL_PARAMS["taxa_desconto_anual"],
    anos_vida_util: int = FINANCIAL_PARAMS["vida_util_anos"],
    taxa_reducao: float = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"],
    anos_base_dados: float = 1.0,
) -> Dict[str, Any]:
    """
    Modelo financeiro integrado de viabilidade econômica:
    - Dimensiona postes
    - Calcula CAPEX e fluxo OPEX
    - Calcula Benefício Social Anual elegível
    - Constrói o Fluxo de Caixa Líquido (Benefício - OPEX)
    - Calcula VPL, TIR, Payback Simples, Payback Descontado e ROI
    """
    dim = dimensionar_postes(comprimento_km, espacamento_m, n_trechos)
    total_postes = dim["total_postes"]

    custos = calcular_capex_opex(
        total_postes=total_postes,
        custo_unitario_poste=custo_poste,
        custo_manutencao_anual_un=custo_manutencao_anual_un,
        anos_vida_util=anos_vida_util,
    )
    capex = custos["capex_total"]
    fluxo_opex = custos["fluxo_opex_anual"]

    beneficios = calcular_beneficio_anual_trechos(
        top_segments_df=top_segments_df.head(n_trechos),
        fator_anualizacao=anos_base_dados,
        taxa_reducao=taxa_reducao,
    )
    beneficio_anual_bruto = beneficios["beneficio_anual_bruto"]

    # Montar Fluxo de Caixa para o projeto
    # Ano 0: -CAPEX
    # Anos 1 a vida_util: Benefício Social Bruto - OPEX do ano
    fluxo_caixa_liquido = [-capex]
    fluxo_descontado = [-capex]
    saldo_acumulado_simples = [-capex]
    saldo_acumulado_descontado = [-capex]

    vpl = -capex
    beneficio_liquido_total_descontado = 0.0
    beneficio_liquido_medio_anual = beneficio_anual_bruto - (sum(fluxo_opex) / anos_vida_util)

    for ano in range(1, anos_vida_util + 1):
        opex_ano = fluxo_opex[ano - 1]
        beneficio_liquido_ano = beneficio_anual_bruto - opex_ano
        fluxo_caixa_liquido.append(beneficio_liquido_ano)

        # Desconto financeiro
        fator_desc = (1.0 + taxa_desconto) ** ano
        beneficio_liquido_descontado = beneficio_liquido_ano / fator_desc
        fluxo_descontado.append(beneficio_liquido_descontado)
        vpl += beneficio_liquido_descontado
        beneficio_liquido_total_descontado += beneficio_liquido_descontado

        saldo_acumulado_simples.append(saldo_acumulado_simples[-1] + beneficio_liquido_ano)
        saldo_acumulado_descontado.append(saldo_acumulado_descontado[-1] + beneficio_liquido_descontado)

    # Payback Simples: CAPEX / Benefício Líquido Anual Médio
    if beneficio_liquido_medio_anual > 0:
        payback_simples_anos = capex / beneficio_liquido_medio_anual
    else:
        payback_simples_anos = float("inf")

    # Payback Descontado (ano exato em que o saldo acumulado descontado cruza o zero)
    payback_descontado_anos = None
    for ano in range(1, anos_vida_util + 1):
        if saldo_acumulado_descontado[ano] >= 0:
            # Interpolação linear no ano de transição
            saldo_anterior = saldo_acumulado_descontado[ano - 1]
            fluxo_ano = fluxo_descontado[ano]
            fracao = abs(saldo_anterior) / fluxo_ano if fluxo_ano > 0 else 0.0
            payback_descontado_anos = (ano - 1) + fracao
            break

    # TIR (Taxa Interna de Retorno)
    tir = calcular_tir(fluxo_caixa_liquido)

    # ROI no horizonte de vida útil: (Benefício Líquido Total Descontado / CAPEX) * 100%
    if capex > 0:
        roi_descontado_pct = ((beneficio_liquido_total_descontado - capex) / capex) * 100.0
        roi_simples_pct = ((sum(fluxo_caixa_liquido[1:]) - capex) / capex) * 100.0
        relacao_beneficio_custo = (beneficio_liquido_total_descontado + capex) / capex if capex > 0 else 0.0
    else:
        roi_descontado_pct = 0.0
        roi_simples_pct = 0.0
        relacao_beneficio_custo = 0.0

    # Cenários de sensibilidade (Conservador, Base, Otimista)
    cenarios_sensibilidade = {}
    for chave, cenario in SCENARIOS.items():
        taxa_cen = cenario["reducao_noturna"]
        ben_cen = calcular_beneficio_anual_trechos(
            top_segments_df.head(n_trechos),
            fator_anualizacao=anos_base_dados,
            taxa_reducao=taxa_cen,
        )
        ben_bruto_cen = ben_cen["beneficio_anual_bruto"]
        ben_liq_med_cen = ben_bruto_cen - (sum(fluxo_opex) / anos_vida_util)
        
        # VPL do cenário
        vpl_cen = -capex
        for ano in range(1, anos_vida_util + 1):
            opex_ano = fluxo_opex[ano - 1]
            vpl_cen += (ben_bruto_cen - opex_ano) / ((1.0 + taxa_desconto) ** ano)
            
        cenarios_sensibilidade[chave] = {
            "nome": cenario["nome"],
            "taxa_reducao": taxa_cen,
            "beneficio_anual_bruto": ben_bruto_cen,
            "beneficio_liquido_anual": ben_liq_med_cen,
            "vidas_salvas_ano": ben_cen["vidas_salvas_ano"],
            "vpl": vpl_cen,
            "payback_simples": (capex / ben_liq_med_cen) if ben_liq_med_cen > 0 else float("inf"),
        }

    # Tabela detalhada de fluxos anuais (Ano 0 a 15)
    linhas_tabela = []
    # Ano 0:
    linhas_tabela.append({
        "ano": 0,
        "capex": capex,
        "opex": 0.0,
        "beneficio_bruto": 0.0,
        "beneficio_liquido": -capex,
        "fator_desconto": 1.0,
        "fluxo_descontado": -capex,
        "saldo_acumulado_descontado": -capex,
    })
    for ano in range(1, anos_vida_util + 1):
        fator_d = (1.0 + taxa_desconto) ** ano
        linhas_tabela.append({
            "ano": ano,
            "capex": 0.0,
            "opex": fluxo_opex[ano - 1],
            "beneficio_bruto": beneficio_anual_bruto,
            "beneficio_liquido": fluxo_caixa_liquido[ano],
            "fator_desconto": fator_d,
            "fluxo_descontado": fluxo_descontado[ano],
            "saldo_acumulado_descontado": saldo_acumulado_descontado[ano],
        })
    tabela_fluxo_caixa_df = pd.DataFrame(linhas_tabela)

    return {
        "dimensionamento": dim,
        "custos": custos,
        "beneficios": beneficios,
        "capex_total": capex,
        "opex_medio_anual": sum(fluxo_opex) / anos_vida_util,
        "beneficio_anual_bruto": beneficio_anual_bruto,
        "beneficio_anual_liquido": beneficio_liquido_medio_anual,
        "vidas_salvas_ano": beneficios["vidas_salvas_ano"],
        "graves_evitados_ano": beneficios["graves_evitados_ano"],
        "leves_evitados_ano": beneficios["leves_evitados_ano"],
        "vpl": vpl,
        "tir": tir,
        "payback_simples_anos": payback_simples_anos,
        "payback_descontado_anos": payback_descontado_anos,
        "roi_descontado_pct": roi_descontado_pct,
        "roi_simples_pct": roi_simples_pct,
        "relacao_beneficio_custo": relacao_beneficio_custo,
        "taxa_desconto": taxa_desconto,
        "anos_vida_util": anos_vida_util,
        "taxa_reducao_adotada": taxa_reducao,
        "anos_base_dados": anos_base_dados,
        "fluxo_caixa_liquido": fluxo_caixa_liquido,
        "fluxo_descontado": fluxo_descontado,
        "saldo_acumulado_descontado": saldo_acumulado_descontado,
        "tabela_fluxo_caixa_df": tabela_fluxo_caixa_df,
        "cenarios_sensibilidade": cenarios_sensibilidade,
    }

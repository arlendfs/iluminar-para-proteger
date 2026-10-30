"""
Módulo de Viabilidade Econômica, Engenharia Financeira e Dimensionamento Solar.
Calcula CAPEX, OPEX, Benefícios Sociais Anuais, Fluxo de Caixa Descontado,
VPL (NPV), TIR (IRR), Payback Simples e Descontado, e ROI com rigor matemático.
"""

import math
import os
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from config import (
    FINANCIAL_PARAMS,
    EFFECTIVENESS_PARAMS,
    ECONOMIC_VALUES,
    SCENARIOS,
    CENARIOS_ORCAMENTO,
    ENGENHARIA_SISTEMA_SOLAR_COMPACTO,
    LUMINOTECNICA_PARAMETROS,
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
    mortos_acc = (
        top_segments_df["mortos_noturno"].sum() if "mortos_noturno" in top_segments_df.columns
        else (top_segments_df["mortos"].sum() if "mortos" in top_segments_df.columns else 0)
    )
    graves_acc = (
        top_segments_df["feridos_graves_noturno"].sum() if "feridos_graves_noturno" in top_segments_df.columns
        else (top_segments_df["feridos_graves"].sum() if "feridos_graves" in top_segments_df.columns else 0)
    )
    leves_acc = (
        top_segments_df["feridos_leves_noturno"].sum() if "feridos_leves_noturno" in top_segments_df.columns
        else (top_segments_df["feridos_leves"].sum() if "feridos_leves" in top_segments_df.columns else 0)
    )
    acidentes_acc = (
        top_segments_df["n_acidentes_noturnos"].sum() if "n_acidentes_noturnos" in top_segments_df.columns
        else (top_segments_df["n_acidentes"].sum() if "n_acidentes" in top_segments_df.columns else 0)
    )

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


def calcular_balanco_energetico_detalhado(
    potencia_led_w: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["potencia_led_w"],
    potencia_painel_wp: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["potencia_painel_wp"],
    capacidade_bateria_wh: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["capacidade_bateria_wh"],
    h_100: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["perfil_noturno_horas"]["h_100_pct"],
    h_80: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["perfil_noturno_horas"]["h_80_pct"],
    h_60: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["perfil_noturno_horas"]["h_60_pct"],
    potencia_telemetria_w: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["telemetria_w"],
    autonomia_desejada_noites: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["autonomia_desejada_noites"],
    dod: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["profundidade_descarga_dod"],
    eficiencia_global: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["eficiencia_bateria_driver"],
    capacidade_eol_pct: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["capacidade_remanescente_eol"],
    hsp: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["hsp_padrao"],
    rendimento_geracao_pr: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["desempenho_global_pr"],
    fator_recarga_nublado: float = ENGENHARIA_SISTEMA_SOLAR_COMPACTO["fator_recarga_nublado"],
) -> Dict[str, Any]:
    """
    Modela o balanço energético completo do poste solar autônomo com rigor técnico.
    Diferencia estritamente:
    1. Autonomia com ZERO geração solar (noites consecutivas sem sol).
    2. Operação em dias nublados com geração parcial.
    3. Impacto da degradação da bateria (BOL vs EOL a 80%).
    4. Tempo em dias de sol pleno para recuperar o banco de baterias após descarga profunda.
    """
    # 1. Consumo Noturno e Diário
    consumo_led_wh = (h_100 * potencia_led_w * 1.0) + (h_80 * potencia_led_w * 0.8) + (h_60 * potencia_led_w * 0.6)
    consumo_telemetria_wh = potencia_telemetria_w * 24.0
    consumo_total_diario_wh = consumo_led_wh + consumo_telemetria_wh
    consumo_3_noites_wh = consumo_total_diario_wh * autonomia_desejada_noites

    # 2. Capacidade Utilizável da Bateria (BOL e EOL)
    capacidade_util_bol_wh = capacidade_bateria_wh * dod * eficiencia_global
    capacidade_util_eol_wh = capacidade_util_bol_wh * capacidade_eol_pct

    # 3. Autonomia em Noites com ZERO geração solar
    autonomia_bol_noites = (capacidade_util_bol_wh / consumo_total_diario_wh) if consumo_total_diario_wh > 0 else 0.0
    autonomia_eol_noites = (capacidade_util_eol_wh / consumo_total_diario_wh) if consumo_total_diario_wh > 0 else 0.0

    atende_bol = autonomia_bol_noites >= autonomia_desejada_noites
    atende_eol = autonomia_eol_noites >= autonomia_desejada_noites

    # 4. Geração Solar Diária
    geracao_solar_pleno_wh = potencia_painel_wp * hsp * rendimento_geracao_pr
    excedente_diario_sol_wh = geracao_solar_pleno_wh - consumo_total_diario_wh

    geracao_solar_nublado_wh = geracao_solar_pleno_wh * fator_recarga_nublado
    balanco_liquido_nublado_wh = geracao_solar_nublado_wh - consumo_total_diario_wh

    # 5. Dias para recuperar carga após 3 noites sem sol
    if excedente_diario_sol_wh > 10.0:
        dias_recarga = consumo_3_noites_wh / excedente_diario_sol_wh
    else:
        dias_recarga = float("inf")

    # Diagnóstico e aviso
    if not atende_bol:
        status_aviso = (
            f"⚠️ AVISO TÉCNICO: A bateria nominal de {capacidade_bateria_wh:.0f} Wh fornece apenas "
            f"{autonomia_bol_noites:.2f} noites de autonomia útil, NÃO atingindo a meta de {autonomia_desejada_noites:.1f} noites sem geração."
        )
    elif not atende_eol:
        status_aviso = (
            f"⚠️ ATENÇÃO: Atende no início de vida ({autonomia_bol_noites:.2f} noites), mas na condição de fim de vida (EOL 80%) "
            f"atinge {autonomia_eol_noites:.2f} noites (abaixo de {autonomia_desejada_noites:.1f} noites)."
        )
    else:
        status_aviso = (
            f"✅ BALANÇO VALIDADO: Sustenta {autonomia_bol_noites:.2f} noites (BOL) e {autonomia_eol_noites:.2f} noites (EOL) "
            f"com ZERO geração solar. Recuperação completa em {dias_recarga:.1f} dias de sol pleno."
        )

    return {
        "potencia_led_w": potencia_led_w,
        "potencia_painel_wp": potencia_painel_wp,
        "capacidade_bateria_wh": capacidade_bateria_wh,
        "consumo_led_wh": consumo_led_wh,
        "consumo_telemetria_wh": consumo_telemetria_wh,
        "consumo_total_diario_wh": consumo_total_diario_wh,
        "consumo_3_noites_wh": consumo_3_noites_wh,
        "capacidade_util_bol_wh": capacidade_util_bol_wh,
        "capacidade_util_eol_wh": capacidade_util_eol_wh,
        "autonomia_zero_sol_bol_noites": autonomia_bol_noites,
        "autonomia_zero_sol_eol_noites": autonomia_eol_noites,
        "atende_requisito_3_noites_bol": atende_bol,
        "atende_requisito_3_noites_eol": atende_eol,
        "geracao_solar_sol_pleno_wh": geracao_solar_pleno_wh,
        "geracao_solar_dia_nublado_wh": geracao_solar_nublado_wh,
        "excedente_diario_sol_wh": excedente_diario_sol_wh,
        "balanco_liquido_nublado_wh": balanco_liquido_nublado_wh,
        "dias_recarga_apos_3_noites": dias_recarga,
        "status_aviso": status_aviso,
        "hsp": hsp,
        "rendimento_geracao_pr": rendimento_geracao_pr,
        "fator_recarga_nublado": fator_recarga_nublado,
    }


def calcular_orcamento_cenarios(
    top_segments_df: pd.DataFrame,
    n_trechos: int = DEFAULT_TRECHOS_TOP_N,
    comprimento_km: float = DEFAULT_COMPRIMENTO_TRECHO_KM,
    espacamento_m: float = DEFAULT_SPACING_M,
    anos_base_dados: float = 2.0,
    taxa_reducao: float = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"],
    taxa_desconto: float = FINANCIAL_PARAMS["taxa_desconto_anual"],
    anos_vida_util: int = FINANCIAL_PARAMS["vida_util_anos"],
    cenarios_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calcula e compara dinamicamente os 5 cenários orçamentários (Cenários A a E):
    - Cenário A: Meta histórica (R$ 15.000 / R$ 60M)
    - Cenário B: Comercial 6m / 40W (NeoSolar ZTL6-40, R$ 17.018,85 / R$ 68,08M)
    - Cenário C: Comercial 8m / 80W (NeoSolar ZTL8-80, R$ 28.288,85 / R$ 113,16M)
    - Cenário D: Conceitual compacto 8m / 40W (R$ 22.310,00 / R$ 89,24M)
    - Cenário E: 8m / 80W com bateria reforçada (R$ 34.038,85 / R$ 136,16M)
    Permite parâmetros editáveis e cotações adicionais.
    """
    cenarios = cenarios_dict or CENARIOS_ORCAMENTO
    dim = dimensionar_postes(comprimento_km, espacamento_m, n_trechos)
    total_postes = dim["total_postes"]

    # Benefício socioeconômico anual sobre os trechos
    beneficios = calcular_beneficio_anual_trechos(
        top_segments_df.head(n_trechos),
        fator_anualizacao=anos_base_dados,
        taxa_reducao=taxa_reducao,
    )
    beneficio_bruto = beneficios["beneficio_anual_bruto"]

    resumos_cenarios = {}
    linhas_tabela = []

    for c_id, c_info in cenarios.items():
        # Custo unitário configurável ou calculado
        custo_kit = c_info.get("custo_kit", 0.0)
        custo_inst = c_info.get("custo_instalacao_fundacao", 0.0)
        custo_tele = c_info.get("custo_telemetria", 0.0)
        reserva_bat = c_info.get("reserva_bateria", 0.0)
        contingencia_pct = c_info.get("contingencia_pct", 0.15)

        if "custo_unitario_total" in c_info and c_info["custo_unitario_total"] > 0:
            custo_unitario = float(c_info["custo_unitario_total"])
        else:
            subtotal = custo_kit + custo_inst + custo_tele + reserva_bat
            custo_unitario = subtotal * (1.0 + contingencia_pct)

        capex = total_postes * custo_unitario

        # OPEX e substituição de baterias
        custos_op = calcular_capex_opex(
            total_postes=total_postes,
            custo_unitario_poste=custo_unitario,
            custo_manutencao_anual_un=FINANCIAL_PARAMS["custo_manutencao_anual_por_poste"],
            custo_bateria_un=FINANCIAL_PARAMS["custo_substituicao_bateria_un"],
            anos_vida_util=anos_vida_util,
            intervalo_troca_bateria=FINANCIAL_PARAMS["intervalo_substituicao_bateria_anos"],
        )
        fluxo_opex = custos_op["fluxo_opex_anual"]
        opex_medio = sum(fluxo_opex) / anos_vida_util
        beneficio_liquido_anual = beneficio_bruto - opex_medio

        # Fluxo de caixa e indicadores
        fluxo_liquido = [-capex] + [beneficio_bruto - opex for opex in fluxo_opex]
        vpl = -capex
        for ano in range(1, anos_vida_util + 1):
            vpl += fluxo_liquido[ano] / ((1.0 + taxa_desconto) ** ano)

        tir = calcular_tir(fluxo_liquido)
        payback_simples = (capex / beneficio_liquido_anual) if beneficio_liquido_anual > 0 else float("inf")

        # Payback descontado
        saldo = -capex
        payback_desc = None
        for ano in range(1, anos_vida_util + 1):
            saldo += fluxo_liquido[ano] / ((1.0 + taxa_desconto) ** ano)
            if saldo >= 0 and payback_desc is None:
                saldo_ant = saldo - (fluxo_liquido[ano] / ((1.0 + taxa_desconto) ** ano))
                fluxo_ano = fluxo_liquido[ano] / ((1.0 + taxa_desconto) ** ano)
                frac = abs(saldo_ant) / fluxo_ano if fluxo_ano > 0 else 0.0
                payback_desc = (ano - 1) + frac

        resumo_c = {
            "id": c_id,
            "nome": c_info.get("nome", c_id),
            "descricao": c_info.get("descricao", ""),
            "tipo": c_info.get("tipo", "estimativa"),
            "altura_poste_m": c_info.get("altura_poste_m", 8.0),
            "potencia_led_w": c_info.get("potencia_led_w", 40.0),
            "custo_unitario": custo_unitario,
            "capex_total": capex,
            "opex_medio_anual": opex_medio,
            "beneficio_bruto_anual": beneficio_bruto,
            "beneficio_liquido_anual": beneficio_liquido_anual,
            "vpl": vpl,
            "tir": tir,
            "payback_simples_anos": payback_simples,
            "payback_descontado_anos": payback_desc,
            "fornecedor_referencia": c_info.get("fornecedor_referencia", "N/A"),
        }
        resumos_cenarios[c_id] = resumo_c

        linhas_tabela.append({
            "Cenário": c_info.get("nome", c_id),
            "Tipo": c_info.get("tipo", "estimativa").replace("_", " ").title(),
            "Altura": f"{c_info.get('altura_poste_m', 8.0):.0f} m",
            "LED": f"{c_info.get('potencia_led_w', 40.0):.0f} W",
            "Custo Unitário (R$)": custo_unitario,
            "CAPEX Total (R$ M)": capex / 1_000_000.0,
            "VPL 15 Anos (R$ M)": vpl / 1_000_000.0,
            "TIR (% a.a.)": (tir * 100) if tir else None,
            "Payback Simples (anos)": payback_simples,
            "Payback Descontado (anos)": payback_desc,
        })

    comparativo_df = pd.DataFrame(linhas_tabela)

    return {
        "dimensionamento": dim,
        "beneficios": beneficios,
        "resumos_cenarios": resumos_cenarios,
        "comparativo_df": comparativo_df,
    }


def carregar_orcamento_excel(caminho_arquivo: str) -> Optional[Dict[str, Any]]:
    """
    Lê planilha Excel de orçamento revisado quando fornecida pelo usuário,
    extraindo parâmetros de fornecedor, kit, montagem e contingência.
    """
    if not os.path.exists(caminho_arquivo):
        return None
    try:
        df_excel = pd.read_excel(caminho_arquivo)
        return {"tabela_bruta": df_excel, "status": "sucesso"}
    except Exception as e:
        return {"erro": str(e), "status": "falha"}


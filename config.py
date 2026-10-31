"""
Arquivo de configuração para o sistema Iluminar para Proteger.
Define constantes, parâmetros de cálculo, engenharia e configurações do sistema.
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

# =============================================================================
# CONFIGURAÇÕES GERAIS E DIRETÓRIOS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMP_DIR = BASE_DIR / "temp"
REPORTS_DIR = BASE_DIR / "reports"
PARQUET_SAMPLES_DIR = BASE_DIR / "parquet_samples"
NORMALIZED_CACHE_DIR = BASE_DIR / "normalized_cache"

# Criar diretórios se não existirem
for directory in [DATA_DIR, TEMP_DIR, REPORTS_DIR, PARQUET_SAMPLES_DIR, NORMALIZED_CACHE_DIR]:
    directory.mkdir(exist_ok=True)


def get_current_rss_mb() -> float:
    """
    Retorna o consumo de memória RSS atual do processo em megabytes (MB).
    """
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def get_container_memory_info() -> Dict[str, Any]:
    """
    Detecta limites de memória do contêiner (cgroups v1/v2 em ambientes Streamlit Cloud / Docker)
    e do sistema hospedeiro, evitando presumir limites fixos de 1 GB.
    """
    info = {
        "container_limit_mb": None,
        "container_usage_mb": None,
        "host_total_mb": None,
        "host_available_mb": None,
        "host_percent": None,
        "detected_environment": "local",
    }
    try:
        import psutil
        vm = psutil.virtual_memory()
        info["host_total_mb"] = vm.total / (1024.0 * 1024.0)
        info["host_available_mb"] = vm.available / (1024.0 * 1024.0)
        info["host_percent"] = vm.percent
    except Exception:
        pass

    # Tentar ler cgroups v2 (Linux / contêineres modernos)
    cgroup_max = Path("/sys/fs/cgroup/memory.max")
    cgroup_current = Path("/sys/fs/cgroup/memory.current")
    if cgroup_max.exists():
        try:
            content = cgroup_max.read_text().strip()
            if content != "max":
                info["container_limit_mb"] = int(content) / (1024.0 * 1024.0)
                info["detected_environment"] = "cgroup_v2"
        except Exception:
            pass
    if cgroup_current.exists():
        try:
            info["container_usage_mb"] = int(cgroup_current.read_text().strip()) / (1024.0 * 1024.0)
        except Exception:
            pass

    # Tentar cgroups v1 se v2 não encontrou
    if info["container_limit_mb"] is None:
        cgroup1_limit = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")
        cgroup1_usage = Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")
        if cgroup1_limit.exists():
            try:
                val = int(cgroup1_limit.read_text().strip())
                if val < 10**15:
                    info["container_limit_mb"] = val / (1024.0 * 1024.0)
                    info["detected_environment"] = "cgroup_v1"
            except Exception:
                pass
        if cgroup1_usage.exists():
            try:
                info["container_usage_mb"] = int(cgroup1_usage.read_text().strip()) / (1024.0 * 1024.0)
            except Exception:
                pass

    info["limit_mb"] = info["container_limit_mb"]
    return info


def log_memory_checkpoint(stage: str, start_time: Optional[float] = None) -> float:
    """
    Registra consumo de memória e tempo de execução sem expor dados pessoais ou internos ao público.
    """
    rss = get_current_rss_mb()
    c_info = get_container_memory_info()
    c_limit = f" | Contêiner: {c_info['container_usage_mb']:.1f}/{c_info['container_limit_mb']:.0f} MB" if c_info.get("container_limit_mb") else ""
    if start_time is not None:
        elapsed = time.time() - start_time
        print(f"[DIAGNÓSTICO MEMÓRIA] {stage} | Duração: {elapsed:.2f}s | RSS: {rss:.1f} MB{c_limit}")
    else:
        print(f"[DIAGNÓSTICO MEMÓRIA] {stage} | RSS: {rss:.1f} MB{c_limit}")
    return rss

APP_CONFIG = {
    "title": "Iluminar para Proteger",
    "subtitle": (
        "Análise Científica de Acidentes Rodoviários e "
        "Viabilidade de Iluminação Solar"
    ),
    "icon": "🚗",
    "layout": "wide",
    "max_file_size": 200,  # MB
    "chunk_size": 50000,   # Registros por chunk
    "max_map_points": 800, # Pontos no mapa para fluidez
}

# =============================================================================
# PARÂMETROS FINANCEIROS, ENGENHARIA E VALORES SOCIAIS
# =============================================================================

# Especificações técnicas e dimensionamento energético auditado para 3 noites de autonomia
ENGENHARIA_SISTEMA_SOLAR = {
    "tensao_sistema_v": 24,                            # Sistema em 24V para reduzir perdas por efeito Joule
    "capacidade_bateria_ah": 80,                       # Bateria LiFePO4 24V 80Ah (= 1.920 Wh nominais)
    "energia_nominal_bateria_wh": 1920.0,              # 24V * 80Ah = 1.920 Wh (ou 12V 160Ah)
    "profundidade_descarga_max_dod": 0.80,             # 80% DoD para garantir ciclo de vida de 3.000+ ciclos
    "energia_util_bateria_wh": 1536.0,                 # 1.920 Wh * 0.80 = 1.536 Wh úteis
    "eficiencia_sistema_perdas": 0.90,                 # 90% (perdas em cabeamento e controlador MPPT)
    "energia_disponivel_consumo_wh": 1382.4,           # 1.536 * 0.90 = 1.382,4 Wh entregues à luminária
    "potencia_led_nominal_w": 60,                      # Luminária LED de 60W com ótica viária
    "perfil_dimerizacao": {
        "pico_18h_22h_h": 4.0,                         # 4 horas a 100% (60W) = 240 Wh
        "repouso_22h_05h_h": 7.0,                      # 7 horas dimerizado a 20% com sensor de radar (méd. 28W) = 196 Wh
        "matutino_05h_06h_h": 1.0,                     # 1 hora a 50% (30W) = 30 Wh
    },
    "consumo_noturno_ponderado_wh": 466.0,             # 240 + 196 + 30 = 466 Wh por noite de 12 horas
    "autonomia_sustentada_noites": 2.97,               # 1.382,4 Wh / 466 Wh = ~3 noites completas
    "potencia_modulo_fotovoltaico_w": 300,             # Módulo fotovoltaico de 300W (ou 2x 150W)
    "horas_sol_pleno_hsp_media": 4.5,                  # Média Brasil de Horas de Sol Pleno diárias
    "geracao_solar_diaria_wh": 1012.5,                 # 300W * 4.5h * 0.75 ef. = 1.012,5 Wh/dia
}

# Novo Conceito Físico e Energético Compacto (8m / 40W / 240Wp / 2.500Wh LiFePO4)
ENGENHARIA_SISTEMA_SOLAR_COMPACTO = {
    "altura_poste_m": 8.0,                             # Poste cônico galvanizado a fogo de 8 metros
    "potencia_led_w": 40.0,                            # Luminária viária LED de 40W de alta eficiência
    "potencia_painel_wp": 240.0,                       # Painel fotovoltaico compacto integrado de 240 Wp
    "capacidade_bateria_wh": 2500.0,                   # Bateria LiFePO4 de 2.500 Wh nominais integrada
    "perfil_noturno_horas": {
        "h_100_pct": 4.0,                              # 4h a 100% (40W) = 160 Wh
        "h_80_pct": 4.0,                               # 4h a 80% (32W) = 128 Wh
        "h_60_pct": 4.0,                               # 4h a 60% (24W) = 96 Wh
    },
    "telemetria_w": 2.0,                               # 2W contínuos durante 24 horas = 48 Wh/dia
    "autonomia_desejada_noites": 3.0,                  # Meta estrita de 3 noites com ZERO geração solar
    "profundidade_descarga_dod": 0.80,                 # 80% DoD para garantir ciclo de vida
    "eficiencia_bateria_driver": 0.90,                 # 90% rendimento combinado bateria/driver/MPPT
    "capacidade_remanescente_eol": 0.80,               # 80% no fim de vida útil (End of Life)
    "hsp_padrao": 4.5,                                 # Horas de Sol Pleno diárias
    "desempenho_global_pr": 0.80,                      # Performance Ratio (perdas térmicas, poeira, ângulo)
    "fator_recarga_nublado": 0.25,                     # 25% da irradiação padrão em dias nublados
}

# Cenários Orçamentários Comparáveis (A a E)
CENARIOS_ORCAMENTO = {
    "cenario_a": {
        "id": "cenario_a",
        "nome": "Cenário A — Meta Histórica",
        "descricao": "Orçamento preliminar anterior sem cotação técnica atualizada (R$ 15.000 fixo).",
        "tipo": "estimativa_historica",
        "altura_poste_m": 8.0,
        "potencia_led_w": 60.0,
        "custo_kit": 15000.00,
        "custo_instalacao_fundacao": 0.00,
        "custo_telemetria": 0.00,
        "contingencia_pct": 0.0,
        "custo_unitario_total": 15000.00,
        "fornecedor_referencia": "Estimativa Acadêmica Preliminar",
    },
    "cenario_b": {
        "id": "cenario_b",
        "nome": "Cenário B — Comercial 6m / 40W",
        "descricao": "Kit comercial de referência (NeoSolar ZTL6-40). Não equivalente a poste viário de 8m.",
        "tipo": "pesquisado_comercial",
        "altura_poste_m": 6.0,
        "potencia_led_w": 40.0,
        "custo_kit": 11599.00,
        "custo_instalacao_fundacao": 2500.00,
        "custo_telemetria": 700.00,
        "contingencia_pct": 0.15,
        "custo_unitario_total": 17018.85,  # (11.599 + 2.500 + 700) * 1.15
        "fornecedor_referencia": "NeoSolar ZTL6-40 (Cotação Pública Online)",
    },
    "cenario_c": {
        "id": "cenario_c",
        "nome": "Cenário C — Comercial 8m / 80W",
        "descricao": "Kit comercial de referência (NeoSolar ZTL8-80) para vias arteriais.",
        "tipo": "pesquisado_comercial",
        "altura_poste_m": 8.0,
        "potencia_led_w": 80.0,
        "custo_kit": 20699.00,
        "custo_instalacao_fundacao": 3000.00,
        "custo_telemetria": 900.00,
        "contingencia_pct": 0.15,
        "custo_unitario_total": 28288.85,  # (20.699 + 3.000 + 900) * 1.15
        "fornecedor_referencia": "NeoSolar ZTL8-80 (Cotação Pública Online)",
    },
    "cenario_d": {
        "id": "cenario_d",
        "nome": "Cenário D — Conceitual Compacto 8m / 40W (Base)",
        "descricao": "Conjunto solar compacto com painel 240 Wp e bateria LiFePO4 de 2.500 Wh nominais.",
        "tipo": "hipotese_conceitual",
        "altura_poste_m": 8.0,
        "potencia_led_w": 40.0,
        "custo_kit": 15500.00,
        "custo_instalacao_fundacao": 3000.00,
        "custo_telemetria": 900.00,
        "contingencia_pct": 0.15,
        "custo_unitario_total": 22310.00,  # (15.500 + 3.000 + 900) * 1.15 = 19.400 * 1.15 = 22.310
        "fornecedor_referencia": "Composição Conceitual Iluminar para Proteger",
    },
    "cenario_e": {
        "id": "cenario_e",
        "nome": "Cenário E — 8m / 80W com Bateria Reforçada",
        "descricao": "Kit comercial de 8m/80W acrescido de reserva técnica de R$ 5.000 para expansão de bateria.",
        "tipo": "hipotese_composta",
        "altura_poste_m": 8.0,
        "potencia_led_w": 80.0,
        "custo_kit": 20699.00,
        "reserva_bateria": 5000.00,
        "custo_instalacao_fundacao": 3000.00,
        "custo_telemetria": 900.00,
        "contingencia_pct": 0.15,
        "custo_unitario_total": 34038.85,  # (20.699 + 5.000 + 3.000 + 900) * 1.15 = 29.599 * 1.15 = 34.038,85
        "fornecedor_referencia": "NeoSolar ZTL8-80 + Reserva de Armazenamento",
    },
}

# Parâmetros de Segurança Luminotécnica (ABNT NBR 5101:2024)
LUMINOTECNICA_PARAMETROS = {
    "norma_referencia": "ABNT NBR 5101:2024 — Iluminação Pública e Rodoviária",
    "status_conformidade": "Pendente de Validação Fotométrica (DIALux EVO)",
    "aviso_metodologico": (
        "A potência de 40W é uma hipótese energética preliminar. A adequação luminotécnica viária "
        "depende do tipo de pista (simples/dupla), largura da faixa de rolamento, classificação da via (V1 a V5), "
        "altura de montagem (8m), espaçamento (50m), distribuição fotométrica da luminária (ótipo IESNA Tipo II/III) "
        "e uniformidade de luminância (Lm e U0). Exige-se cálculo computacional antes de qualquer implantação física."
    ),
    "classes_via": {
        "V1": {"descricao": "Vias de trânsito rápido / autopistas", "luminancia_media_cd_m2": 2.0, "uniformidade_u0": 0.40},
        "V2": {"descricao": "Vias arteriais de grande fluxo", "luminancia_media_cd_m2": 1.5, "uniformidade_u0": 0.40},
        "V3": {"descricao": "Vias coletoras e rodovias padrão", "luminancia_media_cd_m2": 1.0, "uniformidade_u0": 0.35},
        "V4": {"descricao": "Vias locais / rodovias de baixo fluxo", "luminancia_media_cd_m2": 0.75, "uniformidade_u0": 0.30},
    },
}

# Parâmetros de Supervisão e Telemetria Conceitual
TELEMETRIA_CONFIG = {
    "disclaimer_obrigatorio": "SISTEMA DE TELEMETRIA SIMULADO — Representação conceitual de supervisão de ativos. Não existem postes físicos instalados.",
    "protocolos_suportados": ["LoRaWAN", "NB-IoT / 4G Cat-M1", "MQTT"],
    "estados_operacionais": {
        "normal": {"label": "Operação Normal", "cor": "#28a745", "icone": "🟢"},
        "bateria_baixa": {"label": "Bateria Baixa (< 20% SOC)", "cor": "#ffc107", "icone": "🟡"},
        "falha_led": {"label": "Falha na Luminária LED", "cor": "#dc3545", "icone": "🔴"},
        "falha_carregamento": {"label": "Falha no Carregamento Solar", "cor": "#fd7e14", "icone": "🟠"},
        "violacao_gabinete": {"label": "Possível Violação / Furto", "cor": "#e83e8c", "icone": "🚨"},
        "sem_comunicacao": {"label": "Perda de Comunicação", "cor": "#6c757d", "icone": "⚪"},
        "manutencao_necessaria": {"label": "Manutenção Preventiva Agendada", "cor": "#17a2b8", "icone": "🔧"},
    },
    "ciclo_vida_ordem_servico": ["Aberta", "Em Análise", "Em Atendimento", "Concluída"],
}

# Composição analítica do custo de um poste solar autônomo auditado (Total R$ 15.000,00)
POSTE_CUSTO_DETALHADO = {
    "estrutura_poste_galvanizado": 3500.00,            # Poste cônico de 8m galvanizado a fogo
    "modulo_fotovoltaico_300w": 1500.00,               # Painel solar monocristalino 300W (2x150W)
    "bateria_lifepo4_1920wh": 3800.00,                 # Bateria LiFePO4 24V 80Ah (1.920 Wh)
    "luminaria_led_dimerizavel": 1500.00,              # LED viário 60W dimerizável com ótica Tipo II
    "controlador_mppt_sensores_radar": 1000.00,        # MPPT 20A com sensor micro-ondas integrado
    "fundacao_civil_ancoragem": 1300.00,               # Bloco de concreto e chumbadores J
    "mao_de_obra_instalacao": 1400.00,                 # Montagem em campo e comissionamento
    "logistica_projetos_engenharia": 1000.00,          # ART, projeto elétrico/mecânico e frete
}

FINANCIAL_PARAMS = {
    "custo_poste_solar": sum(POSTE_CUSTO_DETALHADO.values()),  # R$ 15.000,00
    "custo_manutencao_anual_por_poste": 500.00,                # R$ 500,00/ano por poste
    "custo_substituicao_bateria_un": 3800.00,                  # Troca de bateria LiFePO4
    "intervalo_substituicao_bateria_anos": 5,                  # Baterias LiFePO4 duram ~5 a 7 anos
    "taxa_desconto_anual": 0.08,                               # 8% a.a. (taxa social de desconto / WACC)
    "vida_util_anos": 15,                                      # Vida útil total do sistema
}

# Parâmetros de efetividade e cenários de intervenção
# Baseado em estudos internacionais de iluminação viária (FHWA / AASHTO)
EFFECTIVENESS_PARAMS = {
    "reducao_acidentes_noturnos": 0.35,  # Cenário Intermediário: 35% de redução esperada
    "reducao_acidentes_diurnos": 0.00,   # Iluminação solar noturna não altera acidentes diurnos
    "fator_severidade_noturno": 2.0,
}

SCENARIOS = {
    "conservador": {
        "nome": "Cenário Conservador",
        "reducao_noturna": 0.20,
        "descricao": "Redução de 20% nos acidentes noturnos elegíveis.",
    },
    "intermediario": {
        "nome": "Cenário Intermediário (Base)",
        "reducao_noturna": 0.35,
        "descricao": "Redução de 35% nos acidentes noturnos (referência FHWA para iluminação de rodovias).",
    },
    "otimista": {
        "nome": "Cenário Otimista",
        "reducao_noturna": 0.50,
        "descricao": "Redução de 50% nos acidentes noturnos em trechos críticos concentrados.",
    },
}

# Custos sociais médios de acidentes no Brasil (IPEA / PRF / ANTT)
ECONOMIC_VALUES = {
    "valor_vida_estatistica": 5_787_720.0,      # Custo estatístico por fatalidade (R$ 5,78M)
    "custo_medio_acidente_grave": 90_000.0,     # Custo médio por ferido grave (hospitalização, sequelas)
    "custo_medio_acidente_leve": 25_000.0,      # Custo médio por ferido leve e danos materiais
}

# Defaults de dimensionamento
DEFAULT_SPACING_M = 50                 # Espaçamento padrão entre postes (m)
DEFAULT_TRECHOS_TOP_N = 100            # Quantidade padrão de trechos prioritários
DEFAULT_COMPRIMENTO_TRECHO_KM = 2.0    # Comprimento padrão de cada trecho segmentado (km)

# =============================================================================
# MAPEAMENTO DE COLUNAS E PADRONIZAÇÃO (DICIONÁRIO OFICIAL DA PRF)
# =============================================================================

COLUMN_MAPPING = {
    "id": ["id", "id_acidente", "num_ocorrencia"],
    "pesid": ["pesid", "id_pessoa", "id_envolvido"],
    "data_inversa": ["data_inversa", "data", "datahora", "data_hora", "dia"],
    "horario": ["horario", "hora"],
    "fase_dia": ["fase_dia", "fase do dia", "periodo", "periodo_dia"],
    "condicao_metereologica": [
        "condicao_metereologica",
        "condicao_meteorologica",
        "tempo",
        "condicao",
    ],
    "uf": ["uf", "estado", "sigla_uf"],
    "br": ["br", "rodovia", "numero_br"],
    "km": ["km", "quilometro", "kilometro"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lng", "lon"],
    "mortos": ["mortos", "obitos", "fatais"],
    "feridos_graves": ["feridos_graves", "feridos graves", "lesoes_graves"],
    "feridos_leves": ["feridos_leves", "feridos leves", "lesoes_leves"],
    "ilesos": ["ilesos", "ileso", "nao_feridos"],
    "classificacao_acidente": ["classificacao_acidente", "classificacao"],
    "tipo_acidente": ["tipo_acidente", "tipo"],
    "causa_acidente": ["causa_acidente", "causa", "causa_principal_nome"],
    "causa_principal": ["causa_principal"],
    "tipo_pista": ["tipo_pista"],
    "tracado_via": ["tracado_via"],
    "ano": ["ano", "ano_ocorrencia"],
    "estado_fisico": ["estado_fisico"],
    "municipio": ["municipio", "cidade"],
    "tipo_envolvido": ["tipo_envolvido", "tipo_envolvimento", "envolvido"],
    "idade": ["idade", "idade_anos"],
    "sexo": ["sexo", "genero"],
    "id_veiculo": ["id_veiculo", "veiculo_id", "num_veiculo"],
    "tipo_veiculo": ["tipo_veiculo", "veiculo_tipo", "especie_veiculo"],
    "marca": ["marca", "marca_modelo"],
    "ano_fabricacao_veiculo": ["ano_fabricacao_veiculo", "ano_fabricacao"],
}

# Categorias oficiais de Faixas Etárias para Análise Demográfica
FAIXAS_ETARIAS_ORDEM = [
    "0 a 17 anos",
    "18 a 24 anos",
    "25 a 34 anos",
    "35 a 49 anos",
    "50 a 64 anos",
    "65 anos ou mais",
    "Não informada / Inconsistente",
]

# Categorias oficiais de Tipo de Envolvimento
TIPOS_ENVOLVIDO_PADRAO = [
    "Condutor",
    "Passageiro",
    "Pedestre",
    "Cavaleiro",
    "Testemunha",
    "Outro",
]

# Categorias oficiais de Fase do Dia da PRF
FASES_DIA_OFICIAIS = [
    "Pleno dia",
    "Plena Noite",
    "Anoitecer",
    "Amanhecer",
]

# Agrupamento analítico dia vs noite
VALUE_STANDARDIZATION = {
    "fase_dia_agrupada": {
        "noturno": ["plena noite", "noite", "noturno"],
        "diurno": ["pleno dia", "dia", "diurno"],
        "crepusculo": ["anoitecer", "amanhecer"],
    }
}

# Causas relacionadas à visibilidade, tempo de reação e resposta do condutor
CAUSAS_VISIBILIDADE_REACAO = [
    "Reação tardia ou ineficiente do condutor",
    "Ausência de reação do condutor",
    "Condutor Dormindo",
    "Velocidade Incompatível",
    "Falta de Atenção à Condução",
    "Ultrapassagem Indevida",
    "Manobra de mudança de faixa",
    "Ingestão de Álcool pelo condutor",
    "Ingestão de substâncias psicoativas pelo condutor",
    "Pedestre andava na pista",
    "Entrada inopinada de pedestre",
    "Animais na Pista",
    "Objeto sobre a pista",
]

# =============================================================================
# LIMITES DE VALIDAÇÃO E REGRAS GEOGRÁFICAS
# =============================================================================

VALIDATION_RULES = {
    "latitude": {
        "min": -34.0,  # Extremo sul do Brasil (~Chuí)
        "max": 5.5,    # Extremo norte do Brasil (~Monte Caburaí)
    },
    "longitude": {
        "min": -74.0,  # Extremo oeste do Brasil (~Serra do Divisor)
        "max": -32.0,  # Extremo leste do Brasil (~Ponta do Seixas / Fernando de Noronha)
    },
    "km": {
        "min": 0.0,
        "max": 6000.0,         # Limite máximo físico para rodovias federais contínuas (ex: BR-101 ~4.650 km, BR-116 ~4.540 km)
        "legacy_max": 1500.0,  # Limite legado anterior mantido estritamente para fins de auditoria de registros recuperados
    },
    "ano": {
        "min": 2000,
        "max": 2030,
    },
}

# =============================================================================
# CORES E IDENTIDADE VISUAL
# =============================================================================

COLOR_PALETTE = {
    "primary": "#1f77b4",       # Azul institucional
    "secondary": "#ff7f0e",     # Laranja diurno
    "danger": "#d62728",        # Vermelho acidentes/mortes
    "success": "#2ca02c",       # Verde economia/benefício
    "warning": "#ffbb78",       # Crepúsculo
    "info": "#17becf",          # Ciano tecnologia
    "light": "#f8f9fa",
    "dark": "#1a2332",          # Fundo escuro
    "noturno": "#1f77b4",       # Noturno
    "diurno": "#ff7f0e",        # Diurno
    "amanhecer": "#ffbb78",     # Amanhecer
    "anoitecer": "#9467bd",     # Anoitecer
}

# =============================================================================
# CONFIGURAÇÕES DO RELATÓRIO PDF
# =============================================================================

PDF_CONFIG = {
    "page_size": "A4",
    "margins": {
        "top": 36,
        "bottom": 36,
        "left": 40,
        "right": 40,
    },
    "font_sizes": {
        "title": 20,
        "subtitle": 14,
        "heading": 12,
        "normal": 9.5,
        "small": 8,
    },
    "colors": {
        "title": "#1f77b4",
        "subtitle": "#1a2332",
        "text": "#222222",
        "accent": "#0056b3",
        "card_bg": "#f4f6f9",
        "alert_bg": "#fff3cd",
    },
}

# =============================================================================
# REFERÊNCIAS CIENTÍFICAS E INSTITUCIONAIS AUDITADAS
# =============================================================================

REFERENCES = [
    {
        "titulo": "Dados Abertos da Polícia Rodoviária Federal — Acidentes",
        "instituicao": "Polícia Rodoviária Federal (PRF / Ministério da Justiça e Segurança Pública)",
        "ano": 2026,
        "url": "https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf",
        "descricao": "Microdados oficiais de ocorrências, causas, tipologia e pessoas envolvidas nas rodovias federais do Brasil (2020 a 2026).",
    },
    {
        "titulo": "Dicionário de Dados de Acidentes da PRF",
        "instituicao": "Coordenação-Geral de Gestão Operacional / PRF",
        "ano": 2024,
        "url": "https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dicionario-acidentes",
        "descricao": "Definição formal de variáveis cadastrais, chaves primárias (id, pesid, id_veiculo), classificações de gravidade e fases do dia.",
    },
    {
        "titulo": "Proven Safety Countermeasures: Lighting (FHWA-SA-21-050)",
        "instituicao": "Federal Highway Administration (FHWA / U.S. Department of Transportation)",
        "ano": 2021,
        "url": "https://highways.dot.gov/safety/proven-safety-countermeasures/lighting",
        "descricao": "Resultados por contexto e desfecho específicos; a hipótese de 35% aplicada a óbitos no projeto não é eficácia demonstrada por esta publicação.",
    },
    {
        "titulo": "Impactos Sociais e Econômicos dos Acidentes de Trânsito nas Rodovias Brasileiras",
        "instituicao": "Instituto de Pesquisa Econômica Aplicada (IPEA / DNIT / ANTP)",
        "ano": 2006,
        "url": "https://repositorio.ipea.gov.br/bitstream/11058/16059/1/impactos_sociais_e_economicos_dos_acidentes_de_transito_relatorio_final.pdf",
        "descricao": "Estudo de custos de acidentes; não comprova os parâmetros específicos nem sua atualização neste modelo.",
    },
    {
        "titulo": "Diretrizes Básicas para Elaboração de Estudos e Projetos Rodoviários - Escopos Básicos e Instruções de Serviço (IPR-726)",
        "instituicao": "Departamento Nacional de Infraestrutura de Transportes (DNIT / Instituto de Pesquisas Rodoviárias)",
        "ano": 2006,
        "url": "https://www.gov.br/dnit/pt-br/assuntos/planejamento-e-pesquisa/ipr/coletanea-de-manuais/publicacao-ipr-726-diretrizes-basicas-para-elaboracao-de-estudos-e-projetos-rodoviarios-escopos-basicos-e-instrucoes-de-servico",
        "descricao": "Diretrizes gerais de estudos e projetos rodoviários.",
    },
    {
        "titulo": "ABNT NBR 5101:2024 — Iluminação Pública e Rodoviária: Procedimento",
        "instituicao": "Associação Brasileira de Normas Técnicas (ABNT)",
        "ano": 2024,
        "url": "https://www.abntcatalogo.com.br/norma.aspx?ID=524810",
        "descricao": "Critérios normativos de iluminância e luminância para classes viárias V1 a V5, controle de ofuscamento e uniformidade longitudinal.",
    },
    {
        "titulo": "Referência Técnica Comercial — Poste Solar ZTL (NeoSolar)",
        "instituicao": "NeoSolar Energia (Kits ZTL6-40 / ZTL8-80)",
        "ano": 2026,
        "url": "https://www.neosolar.com.br/loja/poste-solar-ztroon",
        "descricao": "Cotações públicas e folhas de dados de sistemas solares autônomos integrados em poste de 6m/8m com bateria LiFePO4.",
    },
    {
        "titulo": "Sistema Nacional de Viação (SNV) e Malha Rodoviária Federal",
        "instituicao": "Departamento Nacional de Infraestrutura de Transportes (DNIT)",
        "ano": 2024,
        "url": "https://www.gov.br/dnit/pt-br/assuntos/planejamento-e-pesquisa/snv",
        "descricao": "Inventário oficial de extensão quilométrica contínua e por unidade federativa da malha rodoviária federal brasileira.",
    },
]

"""
Arquivo de configuração para o sistema Iluminar para Proteger.
Define constantes, parâmetros de cálculo, engenharia e configurações do sistema.
"""

from pathlib import Path

# =============================================================================
# CONFIGURAÇÕES GERAIS E DIRETÓRIOS
# =============================================================================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TEMP_DIR = BASE_DIR / "temp"
REPORTS_DIR = BASE_DIR / "reports"
PARQUET_SAMPLES_DIR = BASE_DIR / "parquet_samples"

# Criar diretórios se não existirem
for directory in [DATA_DIR, TEMP_DIR, REPORTS_DIR]:
    directory.mkdir(exist_ok=True)

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
    "geracao_solar_diaria_wh": 1012.5,                 # 300W * 4.5h * 0.75 ef. = 1.012,5 Wh/dia (cobre consumo diário e recarrega reserva)
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
}

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
        "max": 1500.0, # Limite razoável para quilometragem contínua em rodovias federais
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
# REFERÊNCIAS CIENTÍFICAS E INSTITUCIONAIS
# =============================================================================

REFERENCES = [
    {
        "titulo": "Dados Abertos da Polícia Rodoviária Federal — Acidentes",
        "instituicao": "Polícia Rodoviária Federal (PRF / Ministério da Justiça)",
        "url": "https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf",
        "descricao": "Registros oficiais de acidentes em rodovias federais brasileiras.",
    },
    {
        "titulo": "Dicionário de Dados de Acidentes da PRF",
        "instituicao": "Polícia Rodoviária Federal (PRF)",
        "url": "https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dicionario-acidentes",
        "descricao": "Estrutura descritiva de colunas, variáveis e classificações.",
    },
    {
        "titulo": "Proven Safety Countermeasures: Roadway Lighting",
        "instituicao": "Federal Highway Administration (FHWA / U.S. DOT)",
        "url": "https://highways.fhwa.dot.gov/safety/proven-safety-countermeasures/lighting",
        "descricao": "Evidências e pesquisas que indicam redução de 28% a 42% em acidentes noturnos com iluminação viária adequada.",
    },
    {
        "titulo": "Estimativa dos Custos dos Acidentes de Trânsito no Brasil",
        "instituicao": "Instituto de Pesquisa Econômica Aplicada (IPEA)",
        "url": "https://www.ipea.gov.br",
        "descricao": "Metodologia de valoração do custo social de acidentes, hospitalizações e perda de vidas humanas.",
    },
    {
        "titulo": "Manual de Projeto de Iluminação Rodoviária",
        "instituicao": "Departamento Nacional de Infraestrutura de Transportes (DNIT)",
        "url": "https://www.gov.br/dnit/pt-br",
        "descricao": "Diretrizes de engenharia para projetos luminotécnicos viários.",
    },
]

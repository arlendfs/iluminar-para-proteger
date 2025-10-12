"""
 Arquivo de configuração para o sistema Iluminar para Proteger Define
constantes, parâmetros de cálculo e configurações do sistema
"""

from pathlib import Path

# =============================================================================
# CONFIGURAÇÕES GERAIS
# =============================================================================

# Diretórios
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TEMP_DIR = BASE_DIR / "temp"
REPORTS_DIR = BASE_DIR / "reports"

# Criar diretórios se não existirem
for directory in [DATA_DIR, TEMP_DIR, REPORTS_DIR]:
    directory.mkdir(exist_ok=True)

# Configurações da aplicação
APP_CONFIG = {
    "title": "Iluminar para Proteger",
    "subtitle": (
        """Análise Inteligente de Acidentes Rodoviários para
          Implementação de Iluminação Solar"""
    ),
    "icon": "🚗",
    "layout": "wide",
    "max_file_size": 200,  # MB
    "chunk_size": 10000,  # Registros por chunk
    "max_map_points": 1000,  # Pontos máximos no mapa
}

# =============================================================================
# PARÂMETROS FINANCEIROS E ROI
# =============================================================================

# Custos de implementação (em Reais)
FINANCIAL_PARAMS = {
    "custo_poste_solar": 15000.00,
    # **CORREÇÃO**: Adicionada a chave que estava faltando
    "custo_manutencao_anual_por_poste": 2000.00,
    "valor_vida_estatistica": 5787720.00,
    "custo_medio_acidente_grave": 90000.00,
    "custo_medio_acidente_leve": 25000.00,
    "vida_util_anos": 15,
}

# Parâmetros de efetividade
EFFECTIVENESS_PARAMS = {
    # Espera-se redução de 40% dos acidentes noturnos
    "reducao_acidentes_noturnos": 0.40,
    # Redução secundária de acidentes diurnos (5%)
    "reducao_acidentes_diurnos": 0.05,
    # Acidentes noturnos tendem a ter custos 2,5x maiores
    "fator_severidade_noturno": 2.5,
}

ECONOMIC_VALUES = {
    # Valor estatístico de uma vida (VSL)
    "valor_vida_estatistica": 5_787_720.0,
    # Custos médios por tipo de acidente
    "custo_medio_acidente_grave": 90_000.0,
    "custo_medio_acidente_leve": 25_000.0,
}

# ----------------------
# Defaults de dimensionamento
# ----------------------

DEFAULT_SPACING_M = 50  # espaçamento padrão entre postes (m)
DEFAULT_TRECHOS_TOP_N = 100  # top N padrão para relatórios
DEFAULT_COMPRIMENTO_TRECHO_KM = 2.0  # comprimento médio padrão por trecho (km)

# =============================================================================
# CONFIGURAÇÕES DE DADOS
# =============================================================================

# Mapeamento de colunas (flexibilidade para diferentes formatos)
COLUMN_MAPPING = {
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
    "mortos": ["mortos", "obitos", "fatais", "estado_fisico"],
    "feridos_leves": ["feridos_leves", "feridos leves"],
    "feridos_graves": ["feridos_graves", "feridos graves"],
    "classificacao_acidente": [
        "classificacao_acidente",
        "classificacao",
        "tipo_acidente",
    ],
    "causa_acidente": ["causa_acidente", "causa principal", "causa"],
    "ano": ["ano", "ano_ocorrencia"],
    "data_inversa": [
        "data_inversa",
        "data",
        "datahora",
        "data_hora",
        "dia",
    ],
    "ileso": ["ileso", "nao_feridos"],
}

# Padronização de valores
VALUE_STANDARDIZATION = {
    "fase_dia": {
        "noturno": [
            "noite",
            "noturno",
            "anoitecer",
            "madrugada",
            "amanhecer",
            "plena noite",
        ],
        "diurno": ["dia", "diurno", "manhã", "tarde", "manha", "pleno dia"],
    },
    "condicao_metereologica": {
        "ceu_claro": ["ceu claro", "claro", "limpo", "sol"],
        "nublado": ["nublado", "ceu nublado", "encoberto"],
        "chuva": ["chuva", "chuvoso", "precipitacao"],
        "neblina": ["neblina", "cerração", "nevoeiro"],
        "vento": ["vento forte", "ventania"],
        "neve": ["neve", "granizo"],
    },
}

# =============================================================================
# CONFIGURAÇÕES DE VISUALIZAÇÃO
# =============================================================================

# Cores para gráficos
COLOR_PALETTE = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e",
    "danger": "#d62728",
    "success": "#2ca02c",
    "warning": "#ff7f0e",
    "info": "#17becf",
    "light": "#f8f9fa",
    "dark": "#2c3e50",
}

# =============================================================================
# CONFIGURAÇÕES DE PERFORMANCE
# =============================================================================

# Limites de performance
PERFORMANCE_LIMITS = {
    # Registros máximos para análise completa
    "max_records_full_analysis": 100000,
    # Registros máximos para mapa
    "max_records_map": 5000,
    # Tamanho da amostra para datasets grandes
    "sample_size_large_datasets": 10000,
    "cache_ttl_seconds": 3600,  # TTL do cache (1 hora)
}

# =============================================================================
# CONFIGURAÇÕES DE RELATÓRIOS
# =============================================================================

# Configurações de PDF
PDF_CONFIG = {
    "page_size": "A4",
    "margins": {
        "top": 72,
        "bottom": 18,
        "left": 72,
        "right": 72,
    },
    "font_sizes": {
        "title": 24,
        "subtitle": 16,
        "heading": 14,
        "normal": 11,
        "small": 9,
    },
    "colors": {
        "title": "#1f77b4",
        "subtitle": "#2c3e50",
        "text": "#000000",
        "accent": "#17becf",
    },
}

# =============================================================================
# VALIDAÇÃO E QUALIDADE DE DADOS
# =============================================================================

# Regras de validação
VALIDATION_RULES = {
    "latitude": {
        "min": -33.75,  # Limite sul do Brasil
        "max": 5.27,  # Limite norte do Brasil
    },
    "longitude": {
        "min": -73.98,  # Limite oeste do Brasil
        "max": -28.84,  # Limite leste do Brasil
    },
    "km": {
        "min": 0,
        "max": 9999,
    },
    "ano": {
        "min": 2000,
        "max": 2030,
    },
    "mortos": {
        "min": 0,
        "max": 100,  # Limite razoável para um único acidente
    },
    "feridos_leves": {"min": 0, "max": 500},
    "feridos_graves": {"min": 0, "max": 500},
}

# =============================================================================
# MENSAGENS E TEXTOS
# =============================================================================

# Mensagens do sistema
MESSAGES = {
    "loading": "🔄 Carregando e processando dados...",
    "success_load": "✅ Dados carregados com sucesso!",
    "error_load": """❌ Erro ao carregar os dados.
        Verifique o formato dos arquivos.""",
    "no_data": "⚠️ Nenhum dado encontrado com os filtros aplicados.",
    "upload_info": "📤 Faça upload dos arquivos CSV ou coloque-os na pasta /data para começar a análise.",
    "processing": "🔄 Processando análises...",
    "generating_report": "📄 Gerando relatório...",
    "export_complete": "✅ Relatório gerado com sucesso!",
}

# =============================================================================
# FUNÇÃO PARA CARREGAR CONFIGURAÇÕES CUSTOMIZADAS
# =============================================================================


def load_custom_config():
    """
    Carrega configurações customizadas de um arquivo local se existir
    """
    custom_config_file = BASE_DIR / "config_custom.py"
    if custom_config_file.exists():
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "config_custom", custom_config_file
            )
            if spec and spec.loader:
                custom_config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(custom_config)

                # Atualizar configurações com valores customizados
                for attr_name in dir(custom_config):
                    if not attr_name.startswith("_") and attr_name.isupper():
                        globals()[attr_name] = getattr(
                            custom_config, attr_name
                        )
            else:
                print(
                    "⚠️ Não foi possível carregar config_custom.py (loader ausente)"
                )

        except Exception as e:
            print(f"Erro ao carregar configurações customizadas: {e}")


# Carregar configurações customizadas se existirem
load_custom_config()

# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================


def get_file_paths():
    """Retorna lista de arquivos CSV na pasta data"""
    csv_files = list(DATA_DIR.glob("*.csv"))
    return sorted(csv_files)


def validate_config():
    """Valida se as configurações estão corretas"""
    errors = []

    # Validar parâmetros financeiros
    if FINANCIAL_PARAMS["custo_poste_solar"] <= 0:
        errors.append("Custo do poste solar deve ser maior que zero")

    # Validar parâmetros de efetividade
    if not (0 <= EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"] <= 1):
        errors.append("Redução de acidentes deve estar entre 0 e 1")

    # Validar limites geográficos
    lat_min, lat_max = (
        VALIDATION_RULES["latitude"]["min"],
        VALIDATION_RULES["latitude"]["max"],
    )
    if lat_min >= lat_max:
        errors.append("Limites de latitude inválidos")

    return errors


def get_config_summary():
    """Retorna resumo das configurações principais"""
    return {
        "custo_poste": f"R$ {FINANCIAL_PARAMS['custo_poste_solar']:,}",
        "reducao_esperada": f"{EFFECTIVENESS_PARAMS['reducao_acidentes_noturnos']*100:.0f}%",
        "vida_util": f"{FINANCIAL_PARAMS['vida_util_anos']} anos",
        "chunk_size": f"{APP_CONFIG['chunk_size']:,} registros",
        "max_file_size": f"{APP_CONFIG['max_file_size']} MB",
    }


if __name__ == "__main__":
    # Teste das configurações
    errors = validate_config()
    if errors:
        print("Erros de configuração encontrados:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Configurações validadas com sucesso!")

    print("\nResumo das configurações:")
    summary = get_config_summary()

    for key, value in summary.items():
        print(f"  {key}: {value}")

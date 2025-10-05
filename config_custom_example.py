"""
Arquivo de configurações personalizadas (OPCIONAL)
Copie este arquivo para config_custom.py e ajuste os valores conforme necessário

IMPORTANTE: O arquivo config_custom.py será ignorado pelo Git (.gitignore)
para proteger suas configurações locais
"""

# =============================================================================
# EXEMPLO: PARÂMETROS FINANCEIROS CUSTOMIZADOS
# =============================================================================

# Descomente e ajuste os valores abaixo conforme sua necessidade:

# FINANCIAL_PARAMS = {
#     "custo_poste_solar": 45000,         # Ajuste o custo se conseguir melhor preço
#     "custo_manutencao_anual": 1800,     # Ajuste custos de manutenção
#     "vida_util_anos": 20,               # Vida útil estimada diferente
#     "taxa_desconto": 0.10,              # Taxa de desconto do projeto
# }

# =============================================================================
# EXEMPLO: PARÂMETROS DE EFETIVIDADE CUSTOMIZADOS
# =============================================================================

# EFFECTIVENESS_PARAMS = {
#     "reducao_acidentes_noturnos": 0.45,  # Estimativa mais otimista
#     "reducao_acidentes_diurnos": 0.08,   # Efeito indireto
#     "fator_severidade_noturno": 3.0,     # Acidentes noturnos mais severos
# }

# =============================================================================
# EXEMPLO: VALORES ECONÔMICOS REGIONAIS
# =============================================================================

# ECONOMIC_VALUES = {
#     "valor_vida_estatistica": 1200000,   # Valor estatístico atualizado
#     "custo_medio_acidente_fatal": 500000,  # Custos regionais
#     "custo_medio_acidente_grave": 120000,
#     "custo_medio_acidente_leve": 30000,
# }

# =============================================================================
# EXEMPLO: CONFIGURAÇÕES DE PERFORMANCE
# =============================================================================

# PERFORMANCE_LIMITS = {
#     'max_records_full_analysis': 200000,  # Hardware mais potente
#     'max_records_map': 10000,              # Renderizar mais pontos
#     'sample_size_large_datasets': 50000,
#     'cache_ttl_seconds': 7200,            # Cache por 2 horas
# }

# =============================================================================
# EXEMPLO: CONFIGURAÇÕES DE VISUALIZAÇÃO
# =============================================================================

# COLOR_PALETTE = {
#     'primary': '#2196F3',      # Azul Material Design
#     'secondary': '#FF9800',    # Laranja Material Design
#     'danger': '#F44336',       # Vermelho Material Design
#     'success': '#4CAF50',      # Verde Material Design
#     'warning': '#FFC107',      # Amarelo Material Design
#     'info': '#00BCD4',         # Ciano Material Design
#     'light': '#FAFAFA',
#     'dark': '#212121',
# }

# =============================================================================
# EXEMPLO: MENSAGENS PERSONALIZADAS
# =============================================================================

# MESSAGES = {
#     'loading': "⏳ Carregando dados do sistema...",
#     'success_load': "✓ Dados importados com sucesso!",
#     'error_load': "✗ Falha ao carregar arquivos. Verifique o formato.",
#     'no_data': "⚠ Filtros não retornaram resultados.",
#     'upload_info': "↑ Faça upload dos arquivos CSV de acidentes.",
#     'processing': "⏳ Processando informações...",
#     'generating_report': "📄 Criando relatório...",
#     'export_complete': "✓ Relatório exportado!",
# }

# =============================================================================
# INSTRUÇÕES DE USO
# =============================================================================

"""
COMO USAR ESTE ARQUIVO:

1. Copie este arquivo para config_custom.py:
   cp config_custom.py.example config_custom.py

2. Descomente as seções que deseja customizar

3. Ajuste os valores conforme suas necessidades

4. Execute o aplicativo normalmente:
   streamlit run app.py

5. Suas configurações customizadas serão carregadas automaticamente

OBSERVAÇÕES:

- O arquivo config_custom.py não será versionado no Git
- Mantenha uma cópia de backup de suas configurações
- Valores não definidos aqui usarão os padrões de config.py
- Você pode definir apenas os parâmetros que deseja alterar
- Configurações incorretas podem causar erros na aplicação

EXEMPLOS DE USO:

Cenário 1: Projeto piloto com custos reduzidos
FINANCIAL_PARAMS = {
    "custo_poste_solar": 40000,
    "custo_manutencao_anual": 1500,
}

Cenário 2: Análise conservadora
EFFECTIVENESS_PARAMS = {
    "reducao_acidentes_noturnos": 0.30,
}

Cenário 3: Hardware limitado
PERFORMANCE_LIMITS = {
    'max_records_full_analysis': 50000,
    'max_records_map': 1000,
}
"""

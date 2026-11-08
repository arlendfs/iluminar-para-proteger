# 🌟 Iluminar para Proteger

## Estudo exploratório de acidentes rodoviários e cenários de iluminação solar

> **Projeto de Extensão Universitária em Ciência de Dados — UNINTER**\
> _Auditoria Científica, Estatística, Financeira e Técnica de Acidentes
> Rodoviários da PRF_

[Dashboard público](https://iluminar-para-proteger.streamlit.app/) · [Metodologia e fontes](docs/METODOLOGIA_E_FONTES.md) · [Validação pré-publicação](docs/VALIDACAO_PRE_PUBLICACAO.md)

---

## 📑 Sumário Executivo

1. [Contexto e Objetivos](#-1-contexto-e-objetivos)
2. [Alinhamento ODS/ONU](#-2-alinhamento-com-os-objetivos-de-desenvolvimento-sustentável-odsonu)
3. [Auditoria e Diagnóstico Técnico](#-3-auditoria-e-diagnóstico-técnico)
4. [Arquitetura Modular do Software](#-4-arquitetura-modular-do-software)
5. [Confiabilidade e Qualidade dos Dados (PRF)](#-5-confiabilidade-e-qualidade-dos-dados-prf)
6. [Metodologia Estatística: Dia vs Noite](#-6-metodologia-estatística-dia-vs-noite)
7. [Visibilidade Noturna e Tempo de Reação](#-7-visibilidade-noturna-tempo-de-reação-e-fatores-associados)
8. [Segmentação Geográfica e Correção do KM 0,0](#-8-segmentação-geográfica-e-correção-do-km-00)
9. [Modelo Econômico-Financeiro e Dimensionamento](#-9-modelo-econômico-financeiro-e-dimensionamento)
10. [Supervisão remota e telemetria conceitual](#-10-supervisão-remota-e-telemetria-de-infraestrutura-conceitual)
11. [Protótipo 3D Interativo](#-11-protótipo-3d-interativo)
12. [Relatório Técnico-Científico em PDF](#-12-relatório-técnico-científico-em-pdf)
13. [Testes Automatizados (QA)](#-13-testes-automatizados-qa)
14. [Instalação e Execução](#-14-instalação-e-execução)
15. [Limitações Científicas e Referências](#-15-limitações-científicas-e-referências)

---

## 🎯 1. Contexto e Objetivos

O projeto **Iluminar para Proteger** investiga os padrões e a gravidade dos
sinistros rodoviários noturnos no Brasil, avaliando hipóteses relativas à
redução de visibilidade e modelando cenários de viabilidade técnica e financeira
para a implantação de postes solares inteligentes autônomos.

> ⚠️ **Aviso de Escopo:** A implementação acadêmica consiste no software
> funcional, nas auditorias estatísticas e na apresentação dos resultados à
> comunidade científica e aos órgãos de trânsito. **Não há instalação física de
> postes nesta etapa acadêmica.** Simulações socioeconômicas indicam potencial
> de impacto, não constituindo receita de caixa já realizada.

### Comunidade beneficiária: Vila Velha (ES)

A aplicação extensionista está direcionada à comunidade de **Vila Velha (ES)**,
com **ODS 11 - Cidades e Comunidades Sustentáveis** como vínculo principal. O
módulo **Estudos Territoriais** permite escolher Brasil, UF, município, Região
Metropolitana da Grande Vitória, vários municípios ou entorno de um município,
além do período. Vila Velha permanece como comunidade extensionista oficial;
outros recortes geram relatórios territoriais próprios. A análise nacional
continua disponível nos módulos originais.

O período principal do estudo territorial é 2021–2025. O recorte municipal reconcilia os rótulos da PRF com coordenadas e com a
[Malha Municipal Digital 2025 do IBGE](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html).
O relatório territorial é gerado separadamente do relatório científico nacional
e do relatório extensionista específico de Vila Velha. As malhas municipais 2025
são carregadas por UF sob demanda. No ES, o confronto BR/KM usa o traçado
[SNV/DNIT 202507A no Geobases ES](https://gis.geobases.es.gov.br/server/rest/services/gb/DNIT_Rodovias_Federais_ES/MapServer/0),
com tolerâncias exploratórias de 100 m e 1 km. Proximidade não comprova pista,
iluminação nem situação histórica da rodovia. Fora do ES, o traçado viário não
está disponível nesta implantação. Sem estimativa causal local, o módulo exibe
custos condicionais e não calcula VPL territorial.
O acervo histórico oficial do DNIT permite confrontar cada ocorrência do ES com
uma versão cujo mês de referência precede o sinistro. Como a data exata de
publicação não foi confirmada, esse confronto é uma triagem espacial e cadastral,
sem certificação de operação. As 23 versões brutas, hashes e recortes estão
documentados em [Metodologia e Fontes](docs/METODOLOGIA_E_FONTES.md).
A atividade prática consiste em disponibilizar e apresentar o sistema digital;
o software não comprova residência das vítimas, ausência de iluminação,
causalidade ou instalação de postes. Evidências de divulgação ficam vazias até
serem fornecidas pela equipe do projeto.

---

## 🌍 2. Alinhamento com os Objetivos de Desenvolvimento Sustentável (ODS/ONU)

| ODS                                          | Meta                                        | Contribuição do Projeto                                                                                   |
| -------------------------------------------- | ------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **07. Energia Limpa e Acessível**            | 7.2 Aumentar a participação de renováveis   | Postes solares autônomos fotovoltaicos com luminárias LED de alta eficiência e dimerização inteligente.   |
| **09. Indústria, Inovação e Infraestrutura** | 9.1 Infraestrutura sustentável e resiliente | Uso de Ciência de Dados, desduplicação e modelagem de engenharia para infraestrutura viária nacional.     |
| **11. Cidades e Comunidades Sustentáveis**   | 11.2 Mobilidade segura e sustentável        | Foco na redução de mortes e lesões graves em rodovias federais que conectam municípios e centros urbanos. |

---

## 🔍 3. Auditoria e Diagnóstico Técnico

Durante a auditoria integral da base de código original, foram identificadas e
sanadas as seguintes falhas críticas:

1. **Duplicação de Ocorrências:** Os microdados da PRF (`todas_causas_tipos`)
   possuem granularidade de pessoas × causas. A contagem direta de linhas gerava
   contagem de 5 a 6 vezes o número real de acidentes e duplicava óbitos de uma
   mesma pessoa associada a múltiplas causas.
   - _Correção:_ Agrupamento estrito por `id` único da ocorrência e agregação de
     vítimas por `pesid` único.
2. **Distorção do KM 0,0 e Coordenadas Nulas:** Valores com vírgula decimal (ex:
   `639,3` e `-27,08476806`) eram convertidos para `NaN` pelo `pd.to_numeric`
   sem tratamento, e então preenchidos com `0.0`. Isso concentrava milhares de
   acidentes no KM 0,0 e gerava coordenadas no mar (Golfo da Guiné).
   - _Correção:_ Parser robusto de decimais brasileiros
     (`clean_brazilian_float`) e preservação de `NaN` para dados sem
     localização, sem atribuir KM 0,0 artificialmente.
3. **Ausência de Segmentação Geográfica Real:** O sistema agrupava apenas pelo
   ponto exato do KM em vez de intervalos regulares contínuos.
   - _Correção:_ Criação de segmentos regulares de extensão configurável
     (padrão: 2,0 km, ex: `[144.0 - 146.0]`).
4. **Extrapolação Financeira Desconectada:** O cálculo antigo aplicava custos do
   Brasil inteiro a um investimento restrito a 100 trechos, gerando paybacks
   irreais de 8,7 dias e ROI de 90.000%.
   - _Correção:_ Benefícios calculados estritamente sobre as ocorrências
     noturnas elegíveis dos trechos contemplados, com taxa anualizada
     proporcional ao tempo de exposição da base, fluxo de caixa descontado com
     taxa social de 8% a.a., VPL, TIR e OPEX com substituição periódica de
     baterias.
5. **Supressão das Fases Oficiais do Dia:** O código anterior mesclava Amanhecer
   e Anoitecer em Noturno sem rastreabilidade.
   - _Correção:_ Preservação das 4 categorias oficiais da PRF (`Pleno dia`,
     `Plena Noite`, `Amanhecer`, `Anoitecer`), além da visão agregada.

---

## 🏗️ 4. Arquitetura Modular do Software

O sistema foi estruturado com separação estrita de responsabilidades:

```bash
iluminar-para-proteger/
├── app.py                     # Interface Streamlit e controles de sidebar
├── dashboard.py               # Renderização de visualizações, métricas e mapa
├── analyzer.py                # Controladora central AccidentAnalyzer (gestão relacional)
├── data_loader.py             # Ingestão, desduplicação relacional e qualidade de dados
├── demographic_analysis.py    # Perfil demográfico, envolvimento, faixas etárias e frota
├── metrics.py                 # Cálculos estatísticos de letalidade e Dia vs Noite
├── reaction_analysis.py       # Análise de tempo de reação e visibilidade
├── segmentation.py            # Segmentação de trechos viários e ranqueamento
├── financial_model.py         # Modelo financeiro, CAPEX, OPEX, VPL, TIR e ROI
├── pdf_generator.py           # Gerador de relatório científico completo (15 seções)
├── territorial_case.py        # Recortes, validação espacial e indicadores locais
├── territorial_platform.py    # Estudos Territoriais sob demanda
├── territorial_historical_audit.py # Auditoria SNV por referência histórica
├── territorial_pdf.py         # Relatório extensionista de Vila Velha
├── territorial_report_dynamic.py # Relatório do território selecionado
├── assets/ibge_rmgv_2025.geojson.gz  # Malha IBGE 2025 selecionada
├── solar_post_3d.html         # Protótipo 3D interativo (Three.js)
├── config.py                  # Parâmetros técnicos, econômicos e institucionais
├── tests/                     # Suíte de testes automatizados com Pytest
│   ├── test_data_loader.py
│   ├── test_demographic_analysis.py
│   ├── test_metrics.py
│   ├── test_reaction_analysis.py
│   ├── test_segmentation.py
│   ├── test_financial_model.py
│   ├── test_analyzer.py
│   └── test_pdf_generator.py
├── data/                      # CSVs e Parquets da PRF
├── parquet_samples/           # Amostras convertidas de alta velocidade
└── reports/                   # Relatórios técnicos em PDF gerados
```

---

## 📊 5. Confiabilidade e Qualidade dos Dados (PRF)

O sistema consome os dados abertos oficiais da PRF seguindo rigorosamente o
**Dicionário Oficial de Acidentes**:

- **Diferenciação de Granularidade:** Ocorrências únicas identificadas por `id`.
  Envolvidos identificados por `pesid`. Causas múltiplas associadas em tabela
  relacional.
- **Auditoria Transparente:** Exibição no topo do dashboard das linhas brutas
  recebidas, ocorrências desduplicadas, duplicidades evitadas, registros com
  marco KM verificado e coordenadas válidas.
- **Tratamento de Anos Incompletos:** Detecção automática de anos com coleta
  parcial (como 2026, com dados parciais), adotando taxa mensalizada para evitar
  comparações enganosas com anos completos.

---

## 🌗 6. Metodologia Estatística: Dia vs Noite

A análise calcula indicadores com denominadores explicitados:

$$\text{Taxa de Óbitos por 100 Acidentes} = \left(\frac{\text{Total de Pessoas Mortas}}{\text{Total de Ocorrências}}\right) \times 100$$

$$\text{Percentual de Acidentes Fatais (\%)} = \left(\frac{\text{Acidentes com } \ge 1 \text{ Óbito}}{\text{Total de Ocorrências}}\right) \times 100$$

$$\text{Razão Comparativa de Letalidade} = \frac{\text{Óbitos/100 Acidentes (Noturno)}}{\text{Óbitos/100 Acidentes (Diurno)}}$$

> ⚠️ **Nota de Cautela:** A razão de letalidade compara a gravidade observada
> entre os sinistros registrados nos dois períodos. Não deve ser denominada
> "risco de morrer por viagem", pois a base da PRF não contém contagem contínua
> de veículos-quilômetro percorridos (VDMA).

---

## 👁️ 7. Visibilidade Noturna, Tempo de Reação e Fatores Associados

Seção dedicada a investigar causas relacionadas à resposta psicomotora do
condutor (_Mecanismo PIEV — Percepção, Identificação, Emoção e Volição_):

- **Causas Auditadas:** Reação tardia ou ineficiente do condutor, Ausência de
  reação, Condutor dormindo, Velocidade incompatível, Falta de atenção,
  Ultrapassagem indevida, Ingestão de álcool, Animais na pista, Pedestre sem
  visibilidade.
- **Separação Obrigatória:**
  - **Evidência Observacional:** Ocorrência e letalidade das causas registradas
    pelos policiais rodoviários.
  - **Hipótese Interpretativa:** Visibilidade, contraste, velocidade e distância
    de parada podem afetar a percepção e a reação, dependendo da geometria,
    meteorologia, veículo e condutor. Essas grandezas não foram medidas no local.
  - **Limitação:** A PRF não audita a presença física de postes no local do
    sinistro.
  - **Referência:** _Federal Highway Administration (FHWA) — Nighttime
    Visibility_. Efeitos de estudos internacionais não são previsões de mortes
    evitadas nos municípios brasileiros.

---

## 🛣️ 8. Segmentação Geográfica e Correção do KM 0,0

- **Segmentação Regular:** O comprimento do trecho configurável (ex:
  $2{,}0\text{ km}$) define faixas regulares:
  $$\text{KM}_{\text{início}} = \left\lfloor \frac{\text{KM}}{L} \right\rfloor \times L, \quad \text{KM}_{\text{fim}} = \text{KM}_{\text{início}} + L$$
- **Eliminação do Viés de KM 0,0:** Registros sem marco quilométrico são
  contabilizados com transparência no relatório de auditoria e excluídos do
  ranking físico de obras.
- **Score de Prioridade Solar:**
  $$\text{Score}_{\text{Solar}} = (5 \times \text{Mortos}_{\text{not}} + 3 \times \text{Graves}_{\text{not}} + 1 \times \text{Leves}_{\text{not}} + 2 \times \text{Acid}_{\text{not}}) \times \left(1 + \frac{\%_{\text{noturno}}}{100}\right)$$

---

## 💰 9. Modelo Econômico-Financeiro, Cenários Orçamentários e Balanço Energético

### 9.1 Dimensionamento de Postes

$$\text{Postes por Trecho} = \left\lceil \frac{L \times 1.000}{\text{Espaçamento (m)}} \right\rceil$$

Para 100 trechos de $2{,}0\text{ km}$ e espaçamento de $50\text{ m}$:
$$100 \times \left(\frac{2.000}{50}\right) = 4.000 \text{ postes solares}$$

### 9.2 Protótipo energético e custo condicional

O protótipo usa hipóteses de poste de 8 m, luminária LED de 40 W, painel de
240 Wp e bateria LiFePO4 de 2.500 Wh. Consumo, geração e autonomia são
resultados de parâmetros simulados; não medem desempenho em campo. O
espaçamento longitudinal de 50 m serve apenas para estimar quantidades. A
geometria da pista, interseções, curvas, uniformidade, ofuscamento e manutenção
exigem projeto luminotécnico e validação de engenharia.

Os cenários A–E apresentam custos e análise de sensibilidade do modelo
nacional. VPL, TIR e payback dependem de reduções hipotéticas de acidentes e de
valores econômicos cuja fonte, ano-base e atualização precisam ser validados
antes de uso decisório. Não são benefícios realizados, receita financeira nem
previsão local de vidas salvas. O módulo territorial calcula somente CAPEX,
manutenção e reposição de baterias para os segmentos efetivamente selecionados;
não gera VPL municipal.

---

## 📡 10. Supervisão Remota e Telemetria de Infraestrutura (Conceitual)

Módulo conceitual simulado de monitoramento e gestão de ativos:
- **Estados Simulados:** Operação Normal, Bateria Baixa (< 20% SOC), Falha na Luminária LED, Falha de Carga Solar, Violação de Gabinete / Alarme de Furto e Perda de Sinal;
- **Gestão de Incidentes:** Demonstração do ciclo de vida de Ordem de Serviço (OS): `Aberta ➔ Em Análise ➔ Equipe Despachada ➔ Concluída`;
- **Aviso Obrigatório:** Todos os dados de telemetria são 100% simulados para modelagem funcional de software; não há postes físicos instalados.

---

## 🌟 11. Protótipo 3D Interativo

O protótipo 3D funcional (`solar_post_3d.html`), construído em Three.js com WebGL e sombreamento suave, apresenta:

- **Geometria Industrial Viária:** Poste cônico de 8 metros com chapa de base e parafusos de ancoragem;
- **Braço Curvo Viário e Luminária LED:** Modelo viário aerodinâmico com avanço sobre a pista e ótica Tipo II;
- **Conjunto Solar Compacto:** Módulo de 240 Wp proporcional no topo com inclinação de 22°;
- **Modo Raio-X:** Visualização dos componentes internos (Bateria LiFePO4 de 2.500 Wh, BMS e controlador MPPT);
- **Simulação de Veículos:** Ativação dinâmica do radar de micro-ondas com passagem de veículos a 60 km/h;
- **Simulação Interativa de Falhas:** Sliders de potência LED, capacidade de bateria, painel solar, dias sem sol e botões para queima de LED, falha de painel, alarme de intrusão e perda de telemetria;
- **HUD Integrado:** Cálculo em tempo real espelhando o motor Python com consumo diário, geração, autonomia em noites e SOC (%).

---

## 📄 12. Relatório Técnico-Científico em PDF

O gerador `ReportGenerator` produz relatórios formatados em padrão A4, contendo **seções científicas completas**:

1. Identificação Institucional e Metadados
2. Resumo Executivo dos Indicadores Auditados
3. Metodologia, Elegibilidade de Dados e Conciliação dos 267 Registros
4. Evolução Temporal dos Acidentes (Gráfico em Alta Resolução)
5. Comparação Dia vs Noite com Fases Oficiais PRF e Pico no Amanhecer
6. Ranking Geral de Causas de Acidentes e Sobrecarga por Reação Tardia
7. Visibilidade Noturna, Tempo de Reação e Mecanismo Ótico Viário
8. Distribuição Regional (Top Estados e Rodovias)
9. Ranking de Trechos para Investigação (Segmentos de 2 km)
10. Engenharia, Conceito Compacto (8m/40W) e Balanço Energético Auditado
11. Modelagem Econômica e Tabela Comparativa de Cenários Orçamentários (A a E)
12. Supervisão Remota e Telemetria Conceitual
13. Limitações Metodológicas e Científicas
14. Conclusões e Recomendações
15. Referências Oficiais e Normativas (PRF, IPEA, FHWA, ABNT NBR 5101, NeoSolar, EcoSoli, Módulo Energia)

---

## 🧪 13. Testes Automatizados (QA)

A suíte de testes cobre as camadas principais do sistema com **149 testes aprovados na execução local de 2026-11-08** via Pytest:

- **Dados:** Limpeza de decimais com vírgula, preservação de nulos em KM e coordenadas, desduplicação por `id` e `pesid`, auditoria das 267 ocorrências sem KM.
- **Elegibilidade:** Inclusão de sinistros sem KM nas estatísticas nacionais e isolamento apenas na segmentação viária por KM.
- **Estatísticas:** Taxas por 100 acidentes, proporções de fatais e razões comparativas dia vs noite.
- **Balanço Energético:** Coerência aritmética dos parâmetros e alertas de capacidade, sem homologação de autonomia em campo.
- **Cenários Orçamentários:** Verificação da implementação aritmética de CAPEX, OPEX, VPL, TIR e payback sob hipóteses explícitas; testes não validam efetividade causal.
- **Segmentação e Causas:** Segmentos regulares de 2 km, eliminação de KM 0,0 artificial, e causas sobrepostas sem dupla contagem de vítimas.
- **PDF:** Compilação completa do relatório técnico sem falhas de sintaxe ou layout.
- **Finanças:** Dimensionamento geométrico, seleção de trechos sem sobreposição e casos de zero acidentes. Os custos territoriais não incluem VPL.
- **Relatório PDF:** Geração completa sem erros e validação de cabeçalho PDF
  binário.

Para executar os testes:

```bash
python -m pytest tests/ -v
```

---

## 🚀 14. Instalação e Execução

### Pré-requisitos

- Python 3.11+ (testado em Python 3.13)
- Gerenciador `pip`

### Instalação

```bash
git clone https://github.com/arlendfs/iluminar-para-proteger.git
cd iluminar-para-proteger
python -m venv .venv
```

No PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

No Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Para reproduzir a validação territorial, mantenha os cinco Parquets PRF 2021–2025 em `parquet_samples/` e siga [Metodologia e fontes](docs/METODOLOGIA_E_FONTES.md).

### Executar a Aplicação Web

```bash
python -m streamlit run app.py
```

---

## 📚 15. Limitações Científicas e Referências

### Limitações Metodológicas

1. A PRF não registra o nível de iluminância artificial (lux) ou presença de
   postes nos boletins de ocorrência.
2. Não há dados abertos de exposição ao tráfego (VDMA) por quilômetro para toda
   a malha federal.
3. As simulações socioeconômicas constituem modelagem paramétrica para tomada de
   decisão e priorização de investimentos públicos.

### Referências Oficiais

- **PRF:**
  [Dados Abertos de Acidentes da Polícia Rodoviária Federal](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf)
- **PRF:**
  [Dicionário Oficial de Dados de Acidentes](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dicionario-acidentes)
- **FHWA:**
  [Proven Safety Countermeasures: Roadway Lighting](https://highways.fhwa.dot.gov/safety/proven-safety-countermeasures/lighting)
- **IPEA:**
  [Estimativa dos Custos dos Acidentes de Trânsito no Brasil](https://www.ipea.gov.br)
- **DNIT:**
  [Manual de Projeto de Iluminação Rodoviária](https://www.gov.br/dnit/pt-br)

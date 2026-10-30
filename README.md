# 🌟 Iluminar para Proteger

## Energia Solar como Solução para a Segurança nas Rodovias Brasileiras

> **Projeto de Extensão Universitária em Ciência de Dados — UNINTER**\
> _Auditoria Científica, Estatística, Financeira e Técnica de Acidentes
> Rodoviários da PRF_

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
10. [Protótipo 3D Interativo](#-10-protótipo-3d-interativo)
11. [Relatório Técnico-Científico em PDF](#-11-relatório-técnico-científico-em-pdf)
12. [Testes Automatizados (QA)](#-12-testes-automatizados-qa)
13. [Instalação e Execução](#-13-instalação-e-execução)
14. [Limitações Científicas e Referências](#-14-limitações-científicas-e-referências)

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
├── analyzer.py                # Controladora central AccidentAnalyzer
├── data_loader.py             # Ingestão, desduplicação e qualidade de dados
├── metrics.py                 # Cálculos estatísticos de letalidade e Dia vs Noite
├── reaction_analysis.py       # Análise de tempo de reação e visibilidade
├── segmentation.py            # Segmentação de trechos viários e ranqueamento
├── financial_model.py         # Modelo financeiro, CAPEX, OPEX, VPL, TIR e ROI
├── pdf_generator.py           # Gerador de relatório científico completo (15 seções)
├── solar_post_3d.html         # Protótipo 3D interativo (Three.js)
├── config.py                  # Parâmetros técnicos, econômicos e institucionais
├── tests/                     # Suíte de testes automatizados com Pytest
│   ├── test_data_loader.py
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
  - **Hipótese Interpretativa:** O alcance dos faróis baixos (30 a 50 metros) é
    inferior à Distância de Parada Segura (DPS) em velocidades de 80 a 110 km/h
    (80 a 140 metros), reduzindo o tempo de reação disponível.
  - **Limitação:** A PRF não audita a presença física de postes no local do
    sinistro.
  - **Referência:** _Federal Highway Administration (FHWA) — Proven Safety
    Countermeasures: Lighting_, que demonstra reduções de 28% a 42% em colisões
    noturnas com iluminação adequada.

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

## 💰 9. Modelo Econômico-Financeiro e Dimensionamento

### 9.1 Dimensionamento de Postes

$$\text{Postes por Trecho} = \left\lceil \frac{L \times 1.000}{\text{Espaçamento (m)}} \right\rceil$$

Para 100 trechos de $2{,}0\text{ km}$ e espaçamento de $50\text{ m}$:
$$100 \times \left(\frac{2.000}{50}\right) = 4.000 \text{ postes solares}$$

### 9.2 CAPEX e OPEX

- **CAPEX Unitário (R$ 15.000,00):** Poste galvanizado (R\$ 3.500), Módulo solar
  (R\$ 1.200), Bateria LiFePO4 (R\$ 3.500), Luminária LED (R\$ 1.800),
  Controlador MPPT/sensores (R\$ 1.000), Fundação/ancoragem (R\$ 1.500),
  Instalação (R\$ 1.500), Logística/projetos (R\$ 1.000).
- **OPEX Anual:** R\$ 500,00 por poste/ano + R\$ 3.500,00 de substituição de
  bateria a cada 5 anos (anos 5 e 10).

### 9.3 Benefício Social Anual (Valoração IPEA)

Calculado exclusivamente sobre os acidentes noturnos elegíveis dos trechos
contemplados:
$$\text{Benefício Anual} = \Delta_{\text{cenário}} \times \left( \frac{\text{Mortos}}{\text{Anos}} \times \text{VSL} + \frac{\text{Graves}}{\text{Anos}} \times C_{\text{grave}} + \frac{\text{Leves}}{\text{Anos}} \times C_{\text{leve}} \right)$$

Onde $\text{VSL} = \text{R\$} 5.787.720,00$,
$C_{\text{grave}} = \text{R\$} 90.000,00$,
$C_{\text{leve}} = \text{R\$} 25.000,00$.

### 9.4 Indicadores Financeiros

- **VPL (Valor Presente Líquido a 8% a.a., 15 anos):**
  $$\text{VPL} = -\text{CAPEX} + \sum_{t=1}^{15} \frac{\text{Benefício Líquido}_t}{(1 + r)^t}$$
- **TIR:** Taxa onde $\text{VPL} = 0$, calculada por convergência numérica de
  Newton-Raphson.
- **Payback Simples e Descontado:** Ano exato de recuperação do investimento.
- **Cenários de Sensibilidade:** Conservador (20%), Intermediário/Base (35%),
  Otimista (50%).

---

## 🌟 10. Protótipo 3D Interativo

O protótipo 3D funcional (`solar_post_3d.html`), construído em Three.js, simula:

- Ciclos de iluminação Dia / Noite;
- Acionamento inteligente de luminária LED viária;
- Sensor de presença por micro-ondas/radar com dimerização automática;
- Navegação de câmera orbital em 360 graus.

---

## 📄 11. Relatório Técnico-Científico em PDF

O gerador `ReportGenerator` produz relatórios formatados em padrão A4, contendo
**15 seções científicas completas**:

1. Identificação Institucional e Metadados
2. Resumo Executivo dos Indicadores Auditados
3. Metodologia e Confiabilidade dos Dados
4. Evolução Temporal dos Acidentes (Gráfico em Alta Resolução)
5. Comparação Dia vs Noite com Fases Oficiais PRF
6. Ranking Geral de Causas de Acidentes
7. Visibilidade Noturna, Tempo de Reação e Referência FHWA
8. Distribuição Regional (Top Estados e Rodovias)
9. Ranking de Trechos Prioritários para Iluminação
10. Engenharia e Dimensionamento do Poste Solar
11. Viabilidade Econômica (CAPEX, OPEX, VPL, TIR, Payback e Cenários)
12. Discussão Científica e Mecanismos Óticos Viários
13. Limitações Metodológicas
14. Conclusões e Recomendações
15. Referências Oficiais (PRF, IPEA, FHWA, DNIT) com links de acesso

---

## 🧪 12. Testes Automatizados (QA)

A suíte de testes cobre todas as camadas do sistema com **21 testes
automatizados** via Pytest:

- **Dados:** Limpeza de decimais com vírgula, preservação de nulos em KM e
  coordenadas, desduplicação por `id` e `pesid`.
- **Estatísticas:** Taxas por 100 acidentes, proporções de fatais e razões
  comparativas.
- **Causas:** Filtragem de termos de visibilidade, tabelas pivô e
  estratificações.
- **Segmentação:** Intervalos regulares de 2 km, isolamento de KMs nulos e
  ranqueamento.
- **Finanças:** Dimensionamento (100 trechos × 2 km com espaçamento de 50m =
  4.000 postes e R$ 60M CAPEX), benefício restrito aos trechos, fator de
  anualização, VPL, TIR e casos extremos de zero acidentes.
- **Relatório PDF:** Geração completa sem erros e validação de cabeçalho PDF
  binário.

Para executar os testes:

```bash
python -m pytest tests/ -v
```

---

## 🚀 13. Instalação e Execução

### Pré-requisitos

- Python 3.8+ (testado e validado em Python 3.13)
- Gerenciador `pip`

### Instalação

```bash
git clone <url_do_repositorio>
cd iluminar-para-proteger
python -m venv venv
venv\Scripts\activate  # No Windows
pip install -r requirements.txt
```

### Executar a Aplicação Web

```bash
streamlit run app.py
```

---

## 📚 14. Limitações Científicas e Referências

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

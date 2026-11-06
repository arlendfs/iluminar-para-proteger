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

### Comunidade beneficiária: Vila Velha (ES)

A aplicação extensionista está direcionada à comunidade de **Vila Velha (ES)**,
com **ODS 11 - Cidades e Comunidades Sustentáveis** como vínculo principal. O
módulo **Estudo de Caso — Vila Velha** apresenta separadamente ocorrências do
município, corredores federais do entorno metropolitano, Região Metropolitana
da Grande Vitória, Espírito Santo e a referência brasileira. A análise nacional
existente continua disponível nos módulos originais.

O recorte municipal reconcilia os rótulos da PRF com coordenadas e com a
[Malha Municipal Digital 2025 do IBGE](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html).
O relatório territorial é gerado separadamente do relatório científico nacional.
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
├── territorial_dashboard.py   # Estudo de caso sob demanda
├── territorial_pdf.py         # Relatório territorial independente
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

## 💰 9. Modelo Econômico-Financeiro, Cenários Orçamentários e Balanço Energético

### 9.1 Dimensionamento de Postes

$$\text{Postes por Trecho} = \left\lceil \frac{L \times 1.000}{\text{Espaçamento (m)}} \right\rceil$$

Para 100 trechos de $2{,}0\text{ km}$ e espaçamento de $50\text{ m}$:
$$100 \times \left(\frac{2.000}{50}\right) = 4.000 \text{ postes solares}$$

### 9.2 Novo Conceito Físico e Energético Compacto (8m / 40W / 240Wp / 2.500Wh LiFePO4)

Substituição da configuração genérica anterior por um sistema viário compacto e integrado:
- **Poste Metálico Cônico:** Altura de 8,0 metros em aço galvanizado a fogo com base flangeada e chumbadores;
- **Braço Viário Projetado:** Avanço de 1,5m sobre o bordo da pista de rolamento;
- **Luminária LED Viária:** 40 W de alta eficiência com curva fotométrica IESNA Tipo II;
- **Painel Fotovoltaico Integrado:** 240 Wp compacto com inclinação ótima de 22° no topo do poste;
- **Bateria LiFePO4 Integrada:** 2.500 Wh nominais com BMS e controlador MPPT alojados em gabinete protegido na base;
- **Supervisão e Telemetria Remota:** 2 W contínuos durante 24h (48 Wh/dia).

#### Balanço Energético Auditado (Autonomia com ZERO Geração Solar):
- **Consumo Noturno Dimerizado (12h):** 4h a 100% (160 Wh) + 4h a 80% (128 Wh) + 4h a 60% (96 Wh) = **384 Wh/noite**;
- **Consumo Total Diário:** 384 Wh (LED) + 48 Wh (telemetria) = **432 Wh por dia/noite**;
- **Capacidade Útil da Bateria (DoD 80%, Eficiência 90%):**
  - **Início de Vida (BOL):** $2.500 \times 0{,}80 \times 0{,}90 = \mathbf{1.800\text{ Wh úteis}}$;
  - **Fim de Vida (EOL 80%):** $1.800 \times 0{,}80 = \mathbf{1.440\text{ Wh úteis}}$;
- **Autonomia Sustentada (Zero Sol):**
  - BOL: $\frac{1.800}{432} = \mathbf{4{,}17\text{ noites}}$;
  - EOL: $\frac{1.440}{432} = \mathbf{3{,}33\text{ noites}}$ (atende plenamente o requisito mandatário de 3 noites sem sol);
- **Geração Solar (4,5 HSP, PR 80%):** $240 \times 4{,}5 \times 0{,}80 = \mathbf{864\text{ Wh/dia}}$ (excedente de 432 Wh/dia, permitindo recarga completa em **3,0 dias de sol pleno** após descarga profunda).
- **Operação em Dias Nublados:** Gera 216 Wh/dia (suporta até 8 dias nublados consecutivos).

### 9.3 Segurança Luminotécnica e Validação Pendente (ABNT NBR 5101:2024)

> ⚠️ **Aviso de Conformidade:** A potência preliminar de 40W é uma **hipótese técnica preliminar**, sujeita a cálculo fotométrico formal (DIALux EVO / Relux). A conformidade normativa com a **ABNT NBR 5101:2024** para classes V1 a V5 exige verificação de luminância média ($L_m \ge 1{,}0\text{ cd/m}^2$), uniformidade ($U_0 \ge 0{,}35$) e controle de ofuscamento ($TI \le 10\%$) em função da largura da pista e geometria viária.

### 9.4 Comparativo dos 5 Cenários Orçamentários (A a E)

| Cenário | Descrição / Modelo | Custo/Poste (R$) | CAPEX Total (4.000 un) | VPL Social (15 anos) | TIR Social | Payback Simples |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **A — Meta Histórica** | Orçamento preliminar anterior sem cotação | R$ 15.000,00 | R$ 60,00 M | R$ 2,38 bilhões | 480% a.a. | 0,21 anos |
| **B — Comercial 6m/40W** | NeoSolar ZTL6-40 (não equiv. a 8m viário) | R$ 17.018,85 | R$ 68,08 M | R$ 2,37 bilhões | 423% a.a. | 0,23 anos |
| **C — Comercial 8m/80W** | NeoSolar ZTL8-80 para vias arteriais | R$ 28.288,85 | R$ 113,16 M | R$ 2,33 bilhões | 254% a.a. | 0,39 anos |
| **D — Conceitual 8m/40W** | **Base Compacta do Projeto (240Wp/2.500Wh)** | **R$ 22.310,00** | **R$ 89,24 M** | **R$ 2,35 bilhões** | **323% a.a.** | **0,31 anos** |
| **E — 8m/80W Bat. Reforçada** | ZTL8-80 + reserva técnica expansão R$ 5.000 | R$ 34.038,85 | R$ 136,16 M | R$ 2,30 bilhões | 211% a.a. | 0,47 anos |

### 9.5 Benefício Social Anual (Valoração IPEA/PRF)

Calculado exclusivamente sobre os acidentes noturnos elegíveis dos 100 trechos contemplados:
$$\text{Benefício Anual} = \Delta_{\text{cenário}} \times \left( \frac{\text{Mortos}}{\text{Anos}} \times \text{VSL} + \frac{\text{Graves}}{\text{Anos}} \times C_{\text{grave}} + \frac{\text{Leves}}{\text{Anos}} \times C_{\text{leve}} \right)$$

Onde $\text{VSL} = \text{R\$} 5.787.720,00$,
$C_{\text{grave}} = \text{R\$} 90.000,00$,
$C_{\text{leve}} = \text{R\$} 25.000,00$.
- **Vidas Humanas Salvas:** $131{,}0\text{ mortes/ano baseline} \times 0{,}35 = \mathbf{45{,}8\text{ vidas salvas por ano}}$.
- **Benefício Bruto Anual:** **R$ 293,96 milhões/ano**.
- **Benefício Líquido Anual:** **R$ 290,09 milhões/ano** (descontado OPEX de R$ 3,87M/ano).

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
9. Ranking de Trechos Prioritários para Iluminação (Segmentos de 2 km)
10. Engenharia, Conceito Compacto (8m/40W) e Balanço Energético Auditado
11. Modelagem Econômica e Tabela Comparativa de Cenários Orçamentários (A a E)
12. Supervisão Remota e Telemetria Conceitual
13. Limitações Metodológicas e Científicas
14. Conclusões e Recomendações
15. Referências Oficiais e Normativas (PRF, IPEA, FHWA, ABNT NBR 5101, NeoSolar, EcoSoli, Módulo Energia)

---

## 🧪 13. Testes Automatizados (QA)

A suíte de testes cobre todas as camadas do sistema com **29 testes automatizados** via Pytest:

- **Dados:** Limpeza de decimais com vírgula, preservação de nulos em KM e coordenadas, desduplicação por `id` e `pesid`, auditoria das 267 ocorrências sem KM.
- **Elegibilidade:** Inclusão de sinistros sem KM nas estatísticas nacionais e isolamento apenas na segmentação viária por KM.
- **Estatísticas:** Taxas por 100 acidentes, proporções de fatais e razões comparativas dia vs noite.
- **Balanço Energético:** Autonomia com 0 geração solar (BOL >= 4,15 noites, EOL >= 3,30 noites), consumo por dimerização (432 Wh/dia), dias nublados, tempo de recarga (3,0 dias) e aviso de bateria insuficiente.
- **Cenários Orçamentários:** Validação exata dos Cenários A, B, C, D e E com CAPEX, OPEX, VPL, TIR e Payback.
- **Segmentação e Causas:** Segmentos regulares de 2 km, eliminação de KM 0,0 artificial, e causas sobrepostas sem dupla contagem de vítimas.
- **PDF:** Compilação completa do relatório técnico sem falhas de sintaxe ou layout.
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

# 🌟 Iluminar para Proteger
## Energia Solar como Solução para a Segurança nas Rodovias Brasileiras

---

## Sumário
1. Descrição
2. Objetivos
3. Tecnologias Utilizadas
4. Estrutura do Projeto
5. Instalação & Configuração
6. Passo a Passo Rápido
7. Formato dos Dados
8. Uso da Aplicação
9. Metodologia de Cálculo (ROI e Score)
10. Score de Prioridade — regras e limiares
11. Principais Descobertas
12. Recursos Técnicos e Otimização
13. Roadmap e Melhorias Futuras
14. Como Contribuir
15. Estatísticas do Projeto
16. Considerações Finais
17. Licença e Contato

---

## 📊 Dados Utilizados
Os dados de acidentes de trânsito utilizados neste projeto foram obtidos do portal oficial da **Polícia Rodoviária Federal (PRF)**.

📂 Fonte oficial: [https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf/](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf/)

Para reproduzir as análises, baixe os arquivos correspondentes (2020–2024) e coloque-os na pasta `data/`.

---

### 📋 1. Descrição
O projeto **Iluminar para Proteger** é uma aplicação web em Python (Streamlit) que analisa bases de dados de acidentes rodoviários (2020–2024) para identificar trechos prioritários para instalação de postes solares inteligentes, estimar ROI e gerar relatórios acionáveis para gestores públicos e parceiros.

---

### 🎯 2. Objetivos
- Levantar e padronizar dados oficiais (PRF, DNIT, ANTT, bases estaduais).
- Identificar trechos com maior risco noturno e priorizar intervenções.
- Estimar custo-benefício e payback de instalações solares.
- Entregar protótipo 3D do poste, dashboard e relatórios técnicos.
- Propor modelo de parceria público-privada (PPP).

---

### 🛠️ 3. Tecnologias Utilizadas
- **Linguagem:** Python 3.8+
- **Web UI:** Streamlit
- **Manipulação de dados:** Pandas, NumPy
- **Gráficos:** Plotly, Matplotlib
- **Mapas:** Folium, streamlit-folium, branca
- **Protótipo 3D:** Three.js embutido via componente HTML no Streamlit
- **Relatórios:** ReportLab (geração de PDF), Openpyxl (Excel)
- **Outros:** scikit-learn (análises estatísticas/ML futuras), streamlit.cache_data
- **Configuração:** `config.py` (parâmetros financeiros, mapeamento de colunas, limites geográficos)

---

### 📁 4. Estrutura do Projeto
```
iluminar-para-proteger/
├── app.py                         # Aplicação principal Streamlit
├── pdf_generator.py               # Gerador de relatórios PDF
├── config.py                      # Configurações do sistema
├── config_custom.py.example       # Exemplo de configurações personalizadas
├── requirements.txt               # Dependências do projeto
├── .gitignore                     # Arquivos ignorados pelo Git
├── README.md                      # Documentação
├── solar_post_3d.html             # Protótipo 3D standalone
├── data/                          # Pasta para arquivos CSV
│   ├── acidentes2020_todas_causas_tipos.csv
│   ├── acidentes2021_todas_causas_tipos.csv
│   ├── acidentes2022_todas_causas_tipos.csv
│   ├── acidentes2023_todas_causas_tipos.csv
│   └── acidentes2024_todas_causas_tipos.csv
├── reports/                       # PDFs gerados
├── temp/                          # Arquivos temporários
```

---

### ⚙️ 5. Instalação & Configuração
**Pré-requisitos**: Python 3.8+, pip

1. Clone o repositório
```bash
git clone <repository_url>
cd iluminar-para-proteger
```

2. Crie e ative ambiente virtual
- Linux / macOS / WSL (bash/zsh):
```bash
python -m venv venv
source venv/bin/activate
```
- Windows PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
- Windows CMD:
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

3. Instale dependências
```bash
pip install -r requirements.txt
```

4. (Opcional) Ajustes de configuração
- `config.py` contém parâmetros financeiros e mapeamento de colunas; crie `config_custom.py` para sobrescrever valores em ambiente local (ex.: custos, chunk_size).

5. Crie pastas (se não existirem)
```bash
mkdir -p data reports temp
```

---

### ▶️ 6. Passo a Passo Rápido
1. Coloque seus CSVs na pasta `data/` ou use o upload via sidebar.
2. Execute a aplicação:
```bash
streamlit run app.py
```
3. Acesse `http://localhost:8501` e use os filtros na sidebar.
4. Gere relatórios com o botão **Gerar Relatório PDF** (arquivo é salvo em `reports/`).

---

### 🗂️ 7. Formato dos Dados
**Colunas obrigatórias (nomes flexíveis):**
- `uf` / `estado` / `sigla_uf`
- `br` / `rodovia` / `numero_br`
- `km` / `quilometro`

**Colunas recomendadas:**
- `fase_dia` / `periodo` (noturno/diurno)
- `mortos` / `obitos`
- `feridos_leves` / `feridos_graves`
- `latitude`, `longitude`
- `ano` / `data_inversa`
- `causa_acidente` / `causa`
- `condicao_metereologica` / `tempo`

**Observações técnicas:**
- Encoding comum: `latin1` (o código usa `encoding='latin1'` por padrão). Se necessário, converta para UTF-8.
- Arquivos grandes: suportados até ~250 MB (leitura em chunks configurável em `config.py`).
- Separador flexível; o loader usa `engine='python'` para maior tolerância a formatos.

---

### 🧭 8. Uso da Aplicação
- **Upload**: sidebar → selecione múltiplos CSVs.
- **Usar arquivos locais**: marque `Usar arquivos locais da pasta /data`.
- **Filtros**: anos, UFs, BRs, fase do dia e condição meteorológica.
- **Top trechos**: tabela com ranking por `score_prioridade` e indicadores financeiros.
- **Mapa**: folium integrado, amostragem automática (max `max_map_points` em `config.py`).
- **Protótipo 3D**: embutido com Three.js; controla-se dia/noite, LED e simulação de passagem.
- **Relatórios**: botão gera PDF e salva em `reports/`; também há botão para download imediato.
- **Gerenciamento de relatórios**: sidebar lista PDFs gerados, permite download e exclusão.

---

### 🧮 9. Metodologia de Cálculo (ROI e Score)

**Como o investimento é calculado (escala correta):**

- `posts_por_km = 1000 / spacing_m`  (ex.: spacing_m = 50 → 20 postes/km)
- `posts_por_trecho = posts_por_km * comprimento_trecho_km`
- `investimento_trecho = posts_por_trecho * custo_poste`
- `investimento_total_topN = soma(investimento_trecho para cada um dos top N trechos)`

**Custos operacionais:**
- `custo_manutencao_anual_total = custo_manutencao_anual_por_poste * posts_por_trecho`

**Cálculo da economia anual:**
- `economia_mortos = (mortos_no_trecho * reducao_estimada) * valor_vida_estatistica`
- `economia_graves = (feridos_graves * reducao_estimada) * custo_medio_acidente_grave`
- `economia_leves = (feridos_leves * reducao_estimada) * custo_medio_acidente_leve`
- `economia_anual = economia_mortos + economia_graves + economia_leves`

**Payback e ROI:**
- `payback_anos = investimento_trecho / (economia_anual - custo_manutencao_anual_total)` (se denom > 0)
- `ROI_10anos = ((economia_anual * 10 - (investimento_trecho + custo_manutencao_anual_total * 10)) / (investimento_trecho + custo_manutencao_anual_total * 10)) * 100`

## Parâmetros padrão (podem ser alterados no dashboard)
- custo_poste_solar: **R$ 15.000,00**
- custo_manutencao_anual_por_poste: **R$ 2.000,00**
- reducao_acidentes_noturnos: **40%**
- spacing padrão: **50 m**
- comprimento médio por trecho (default): **2.0 km**

---

### 🏷️ 10. Score de Prioridade — regra e limiares
**Fórmula de prioridade** (implementada no código):
```
score_prioridade = (mortos * 3) + total_feridos
```
**Interpretação prática (sugestão de limiares):**
- `Alto` → score >= 50
- `Médio` → 20 <= score < 50
- `Baixo` → score < 20

(Ajuste os limiares conforme a escala e volume dos dados.)

---

### 🔎 11. Principais Descobertas (exemplo de resultados)
- **Acidentes noturnos** representam uma parcela significativa — frequentemente entre **35–45%** do total. (Resultados variam conforme base.)
- **Maior letalidade** em acidentes noturnos: taxa média de mortos por acidente é 2–3× maior.
- **Concentração geográfica**: top 100 trechos concentram grande parte dos acidentes graves.
- **ROI atrativo**: para trechos críticos, payback médio estimado entre **6–8 anos**.

> Observações: números acima são achados típicos do projeto e dependem da base carregada; relatório final traz valores exatos.

---

### ⚙️ 12. Recursos Técnicos e Otimização
- **Chunking**: leitura em blocos (padrão `chunk_size` = 10000) para arquivos grandes.
- **Cache**: Streamlit `@st.cache_data` para acelerar recarregamentos.
- **Amostragem**: mapas limitam a 1.000 pontos por exibição para performance.
- **Validação**: `config.py` contém regras para latitude/longitude, ano, km, limites de vítimas.
- **PDF**: geração via `pdf_generator.py` (ReportLab) com templates executivos/técnicos configuráveis.

---

### 🚀 13. Roadmap e Melhorias Futuras
**Versão 2.0 (curto prazo)**
- [ ] **Machine Learning**: Modelos de Machine Learning para risco preditivo por trecho
- [ ] **API REST**: API REST para integração institucional
- [ ] **Banco de Dados**: Banco de dados PostgreSQL para persistência e versionamento
- [ ] **Autenticação**: Sistema de usuários e permissões

**Versão 2.5 (médio prazo)**
- [ ] **Alertas Automáticos**: Sistema de alertas automáticos e monitoramento pós-instalação
- [ ] **Integração IoT**: Dados em tempo real de sensores
- [ ] **Dashboard Executivo**: Versão simplificada para gestores

**Versão 3.0 (longo prazo)**
- [ ] **Mobile App**: Aplicativo para fiscalização
- [ ] **Simulação**: Simulações avançadas e integração com dados de tráfego em tempo real

---

### 🤝 14. Como Contribuir
1. **Fork** o repositório
2. **Crie** uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. **Push** para a branch (`git push origin feature/AmazingFeature`)
5. **Abra** um Pull Request

**Checklist para PR**: testes de carga, exemplos de CSV, update em `requirements.txt`, documentação atualizada.

---

### 📊 15. Estatísticas do Projeto
- Linhas de código (aprox.): ~2850 (Python)
- Capacidade de processamento: arquivos de até ~250 MB por arquivo
- Tempo médio de análise (depende da máquina): otimizado para análises interativas em < 30s para amostras (variável)

---

### ✍️ 16. Considerações Finais
O projeto demonstrou como a análise de dados, utilizando Python e bibliotecas de ciência de dados, pode transformar informações brutas em insights práticos com impacto social direto.

Principais aprendizados: A análise comprovou o potencial da tecnologia para salvar vidas, mostrando que dados bem trabalhados podem fundamentar políticas públicas mais eficientes e impulsionar o desenvolvimento de cidades inteligentes e sustentáveis.

Maiores dificuldades: O maior desafio foi lidar com bases de dados governamentais desorganizadas e inconsistentes, exigindo esforço intenso de limpeza, tratamento e integração para assegurar a confiabilidade dos resultados.

Conclusão principal: A experiência reforçou a responsabilidade social do profissional de tecnologia em aplicar suas habilidades para resolver problemas reais, reduzir acidentes, salvar vidas e contribuir para o bem-estar da sociedade.

---

### 📄 17. Licença & Contato
- **Licença:** [MIT](./LICENSE)
- **Contato: Arlen Freitas Silva — RU 5093181 — arlenfreitas1@gmail.com**

> _"Transformar dados em luz: tecnologia que ilumina estradas e salva vidas."_

---

**Última atualização**: Outubro 2025
**Versão**: 1.1.0
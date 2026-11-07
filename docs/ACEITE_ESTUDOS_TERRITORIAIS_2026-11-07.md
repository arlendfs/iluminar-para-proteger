# Aceite técnico — Estudos Territoriais (2026-11-07)

## Corrigido e implementado

- Navegação nacional preservada; novo módulo territorial sob demanda para Brasil, UF, município, RMGV, municípios selecionados e entorno municipal.
- Malha IBGE 2025 carregada por UF; reconciliação ponto, polígono e rótulo PRF. Vila Velha permanece comunidade extensionista oficial.
- Traçado DNIT/SNV 202507A para ES, com auditoria BR/KM, coordenadas repetidas/arredondadas e tolerâncias exploratórias (100 m e 1 km). Outros estados informam a ausência de traçado local.
- Tabelas e gráficos por fase, gravidade, meteorologia, causa e reação; intervalos de Wilson para a proporção de acidentes fatais. Sem inferência causal de iluminação.
- Ranking de segmentos, mapa com camadas, custos condicionais sem VPL territorial e dois tipos de PDF: territorial dinâmico e extensionista de Vila Velha.

## Evidência de validação

- `python -m pytest tests/ -q`: 140 aprovados, 3 falhas preexistentes vinculadas exclusivamente à ausência dos Parquets 2020 e 2026 no checkout.
- AppTest com cinco Parquets de 2021 a 2025: Vila Velha com 126 acidentes, 52 em plena noite e 16 óbitos; PDF territorial com 3 páginas. Vitória: 38 acidentes, 7 em plena noite e 0 óbito; PDF com identificação de Vitória e sem texto fixo de Vila Velha.
- PDF extensionista de Vila Velha com 3 páginas. Os três PDFs foram renderizados; mapas, tabelas e identificação territorial inspecionados visualmente.
- Perfil local de processo no AppTest: pico de 778,6 MiB após carga nacional; 894,0 MiB no módulo territorial; 929,8 MiB após geração do PDF. São medições locais, não da instância Streamlit publicada.
- Implantação `iluminar-para-proteger.streamlit.app` verificada após o commit `07a8236`: navegação "Estudos Territoriais", cinco anos 2021–2025, 126 acidentes e 16 óbitos para Vila Velha, e botão de download do PDF territorial gerado. O painel da sessão mostrou RSS de 810,0 MiB após a geração; é leitura instantânea, não pico do processo.

## Arquivos e fontes

- Código: `dashboard.py`, `territorial_platform.py`, `territorial_dynamic.py`, `territorial_science.py`, `territorial_road_audit.py`, `territorial_report_dynamic.py`, `territorial_case.py`, `territorial_dashboard.py`.
- Dados geográficos: `assets/dnit_es_snv_202507a.geojson.gz`; dependência `pyshp` em `requirements.txt`.
- Testes: `tests/test_territorial_case.py`, `tests/test_territorial_dynamic.py`, `tests/test_territorial_road_audit.py`, `tests/test_territorial_science.py`.
- Exemplos locais não versionados: `output/pdf/relatorio_territorial_vila_velha_v2.pdf`, `output/pdf/relatorio_territorial_vitoria_v2.pdf`, `output/pdf/relatorio_extensionista_vila_velha_v2.pdf`.
- [Malhas IBGE](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html), [traçado DNIT no Geobases ES](https://gis.geobases.es.gov.br/server/rest/services/gb/DNIT_Rodovias_Federais_ES/MapServer/0), [dados PRF](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf).

## Pendências e limites

- Os arquivos Parquet 2020 e 2026 estavam removidos antes desta entrega; não foram restaurados nem incluídos no commit. Três testes antigos dependem deles.
- Métricas de memória do servidor publicado dependem do painel de hospedagem; o perfil acima é local.
- A malha rodoviária de outros estados e inventário de iluminação não estão disponíveis. A auditoria BR/KM é triagem espacial, não vistoria ou confirmação histórica.

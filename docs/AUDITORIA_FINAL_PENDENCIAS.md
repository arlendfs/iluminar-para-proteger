# Auditoria final controlada — 03/11/2026

## Rodada de aceite C01–C12 (concluída)

O arquivo de referência `relatorio_cientifico_iluminar_20261102_175932.pdf` não foi encontrado em `reports/`. `AGENTS.md` não existe no repositório nem no diretório pai. A implementação foi confrontada com o PDF mais recente disponível e os requisitos explícitos do prompt. PDF final desta rodada: `reports/relatorio_cientifico_iluminar_20261103_115607.pdf` (5 páginas).

| ID | Requisito | Arquivo/função | Causa raiz | Alteração | Teste específico | Evidência | Status |
|---|---|---|---|---|---|---|---|
| C01 | Categoria Nan | `pdf_generator.py:_public_missing`, `dashboard.py:_public_label_series` | Nulos e strings equivalentes escapavam da apresentação | Normalização para “Não informado” sem excluir linhas | `test_c01_rotulos_publicos_aceitam_todos_os_nulos` | Página 3: 10.282 envolvidos em “Não informado”; sem categoria Nan no PDF | APROVADO |
| C02 | Números pt-BR | `reaction_analysis.py`, `pdf_generator.py` | Texto científico interpolava floats crus | Formatação decimal e de energia na apresentação; fórmulas intactas | `test_c02_formato_pt_br_em_todo_o_texto_cientifico` | PDF: 11,25; 12,97; 1.800,0 Wh; 0,38 ano | APROVADO |
| C03 | Unidades fotométricas | `reaction_analysis.py`, `pdf_generator.py` | Luminância era associada a lux | Iluminância em lux e luminância em cd/m²; limitação da base PRF explicitada | `test_c03_grandezas_fotometricas_no_pdf` | Páginas 2 e 4 com unidades corretas | APROVADO |
| C04 | Discussão do amanhecer | `metrics.py:compute_day_vs_night_comparison`, `pdf_generator.py` | Dois parágrafos repetiam hipóteses | Texto único com quatro taxas e ressalva causal | `test_c04_discussao_amanhecer_sem_duplicacao` | Página 2: 12,70; 11,50; 7,67; 6,06 óbitos/100 acidentes | APROVADO |
| C05 | Faróis, DPS e PIEV | `reaction_analysis.py` | Intervalos de alcance/parada sem premissas verificadas | Explicação qualitativa de PIEV, distância de parada e fatores de visibilidade | `test_c05_dps_sem_distancias_universais` | Página 2 sem regra universal nem inferência causal por faróis | APROVADO |
| C06 | Auditoria de registros | `pdf_generator.py` | Um caso era tratado como prova de autenticidade | Redação limitada à consistência interna; removido “total rigor estatístico” | `test_c06_auditoria_nao_valida_autenticidade_por_um_caso` | Página 1: 2.702.004 linhas, 342.626 ocorrências, 7.680 linhas sem KM, 883 ocorrências sem KM válido, 341.743 com KM válido | APROVADO |
| C07 | Ranking heurístico | `pdf_generator.py` | Pesos apresentados sem explicitar sua natureza exploratória | Fórmula preservada; pesos e limitações descritos; sensibilidade contextualizada | `test_c07_score_heuristico_sem_alegacao_causal` | Página 3 distingue concentração histórica de prioridade efetiva; página 4 ressalva sensibilidade | APROVADO |
| C08 | Tabelas financeiras e cabeçalhos | `pdf_generator.py`, `config.py` | Larguras, rótulos e acentos prejudicavam leitura | Cabeçalhos e classificações corrigidos; CAPEX/VPL em R$ milhões com horizonte de 15 anos | `test_c08_cabecalhos_e_classificacao_financeira` | Páginas 3–5: Óbitos, Feridos Graves, Estimativa Histórica, Hipótese Conceitual, Payback Simples | APROVADO |
| C09 | Bibliografia | `config.py:REFERENCES`, `pdf_generator.py` | Ano de consulta confundido com ano bibliográfico | Metadados de publicação/edição separados da data de acesso | `test_c09_anos_bibliograficos_especificos` | Página 5: FHWA 2021, Ipea 2006, DNIT IPR-726 3ª ed. 2006, ABNT 2024; 9 links | APROVADO |
| C10 | Conclusão sobre iluminação | `pdf_generator.py` | Efeito da iluminação expresso como universal | Discussão condicional e recomendações de validação e piloto | `test_c10_conclusao_condicional` | Página 5: dados observacionais, simulações, inventário, VDMA, fotometria e cotações ressalvados | APROVADO |
| C11 | Visual do PDF | `pdf_generator.py`, `config.py` | Rodapés/cabeçalhos e tabelas sofriam cortes/fragmentação | Margens ajustadas, sobreposição de cabeçalhos/rodapés após renderização, tabelas revisadas | `test_c11_pdf_visualmente_inspecionavel`; PNGs inspecionados | Cinco páginas; gráficos, ranking, finanças, matriz e referências legíveis; sem sobreposições observadas | APROVADO |
| C12 | Teste e inspeção final | `tests/test_auditoria_final_pendencias.py`, `reports/` | Faltava aceite integrado do PDF novo | 11 testes C01–C11, geração 2021–2025, extração textual e renderização visual de 5 páginas | `python -m pytest -q`: 119 passaram; busca textual e inspeção das 5 páginas | 342.626 acidentes, 28.668 óbitos, 391.479 feridos, 24.619 fatais; CAPEX R$ 89,24 mi; VPL social R$ 1.905,08 mi; geração sem recarga redundante | APROVADO |

### Medição desta rodada

- Geração local com cache Parquet 2021–2025: carga 4,51 s; segmentação e finanças 5,80 s; PDF 14,47 s; total 20,28 s; pico RSS amostrado 1.246,6 MB. O pico excede 1 GB; esta rodada não demonstra geração abaixo desse limite.
- O PDF final foi renderizado em `temp/pdf_audit_20261103_115607/page_1.png` a `page_5.png` e cada página foi inspecionada visualmente. Cabeçalhos e rodapés foram conferidos também pela extração de texto e coordenadas, inclusive na página 5.
- O teste textual não encontrou categorias `Nan`, `1 óbitos`, unidade fotométrica incorreta, classificações sem acento ou os decimais ingleses listados no pedido.

## Próximo passo concluído — redução do pico de memória (03/11/2026)

| Item | Causa medida | Correção | Evidência | Status |
|---|---|---|---|---|
| M01 | Cópia integral da tabela de pessoas na agregação veicular | `compute_veiculo_analysis` seleciona somente as cinco colunas usadas | Mesmos totais de frota e vítimas no PDF | APROVADO |
| M02 | Cópia de todas as colunas nas métricas por período, na segmentação e nas junções de causas | Projeção das colunas necessárias em `metrics.py`, `segmentation.py`, `reaction_analysis.py` e gráfico de causas em `pdf_generator.py` | Indicadores e texto do PDF idênticos à rodada C01–C12, exceto horário de emissão | APROVADO |
| M03 | Resumos intermediários permaneciam vivos até a finalização do PDF; último ano conservava referências locais na consolidação | Liberação após uso em `pdf_generator.py` e `analyzer.py` | Pico de RSS amostrado de 1.246,6 para 971,3 MiB (redução de 22,1%) na execução local final | APROVADO |

- Medição: processo Python isolado, cache Parquet local dos anos 2021–2025, `psutil` amostrado a cada 20 ms. Carga 3,31 s; carga, finanças e PDF 24,99 s; pico observado 971,3 MiB (aproximadamente 1,018 GB decimais). Esse teste fica abaixo de 1 GiB (1.024 MiB), mas não comprova operação abaixo de 1 GB decimal ou na implantação Streamlit Cloud, que tem custos adicionais de interface e sessões. A execução anterior da mesma revisão marcou 960,0 MiB; há variação entre processos.
- Novo PDF: `reports/relatorio_cientifico_iluminar_20261103_121854.pdf`, cinco páginas. Texto extraído igual ao PDF C01–C12 após ignorar somente o horário de emissão; hashes das duas imagens incorporadas iguais; nove links na página de referências.
- Suíte completa após as mudanças: **119 testes aprovados** (`python -m pytest -q`). Os números 342.626 acidentes, 28.668 óbitos, 391.479 feridos, 24.619 acidentes fatais, CAPEX R$ 89,24 milhões e VPL social R$ 1.905,08 milhões permaneceram no PDF.

## Verificação no fluxo Streamlit e limite decimal (03/11/2026)

| Item | Causa e alteração | Evidência | Status |
|---|---|---|---|
| M04 | A chamada do PDF calculava rankings, pivôs e estratificações de causas usados somente no painel interativo; `include_details=False` usa as seis causas exibidas no relatório e conserva a análise completa como padrão no painel | Texto extraído e hashes dos dois gráficos do PDF novos iguais aos da rodada C01–C12, exceto horário de emissão; teste de equivalência do resumo e das causas exibidas | APROVADO |
| M05 | A concatenação convertia categorias anuais distintas de pessoas e veículos em colunas `object` extensas; as categorias são alinhadas antes da união, sem alterar os registros | AppTest com pasta local, cinco arquivos 2021–2025, filtros padrão e acionamento do botão do PDF: dois picos RSS de 940,9 e 933,8 MiB | APROVADO |

- A maior das duas medições finais corresponde a aproximadamente **986,6 MB decimais**, abaixo de 1 GB no processo testado. Amostragem de RSS a cada 20 ms por `psutil` no mesmo processo do AppTest; inclui execução do script Streamlit, estado da sessão, cálculo financeiro e geração do PDF. A primeira medição desse fluxo, antes de M04–M05, marcou 1.033,1 MiB.
- PDF final do AppTest: `reports/relatorio_cientifico_iluminar_20261103_184042.pdf` (5 páginas, 9 links de referência). Texto igual ao PDF de aceite C01–C12 exceto horário de emissão; imagens incorporadas idênticas; totais e CAPEX/VPL reconciliados.
- Suíte final: **120 testes aprovados** (`python -m pytest -q`). O limite foi verificado no AppTest local com uma sessão; memória de servidor publicado, múltiplas sessões e carga simultânea ainda precisam de medição no ambiente de implantação.

## Duas sessões e integridade do PDF (03/11/2026)

| Item | Causa e alteração | Evidência | Status |
|---|---|---|---|
| M06 | Cada sessão repetia a leitura e a consolidação dos mesmos cinco arquivos | `app.py:load_shared_local_data` compartilha o resultado local por assinatura de arquivos com cache de recurso | Duas sessões AppTest apontaram para o mesmo DataFrame; segunda carga 0,00 s; pico da segunda carga 834,4 MiB, contra 1.268,9 MiB antes do compartilhamento | APROVADO |
| M07 | Matplotlib tem estado global e gerações paralelas do PDF podiam interferir no resultado | `dashboard.py:PDF_GENERATION_LOCK` serializa cálculo necessário e renderização do PDF | Dois pedidos disparados juntos em threads diretas produziram PDFs completos de 5 páginas, ambos com dois gráficos; pico de 965,5 MiB no ensaio direto | APROVADO |
| M08 | O pós-processamento anterior carregava PyMuPDF no processo servidor | `pdf_generator.py` carimba cabeçalho/rodapé com `pypdf` após o ReportLab | Duas sessões residentes no AppTest, cada uma gerando um PDF completo em sequência: pico total de 939,8 MiB (aprox. 985,5 MB decimais); 5 páginas, 9 links, cabeçalhos/rodapés e gráficos conferidos | APROVADO |

- Os dois PDFs das sessões foram inspecionados por extração de texto e renderização PNG das cinco páginas; indicadores 2021–2025, CAPEX e VPL seguem reconciliados. Os arquivos locais de inspeção são `reports/two_sessions_first.pdf` e `reports/two_sessions_second.pdf`.
- A execução de dois AppTests em threads produziu falha interna do próprio teste (`Runtime hasn't been created!`); por isso o ensaio de sessões residentes usou pedidos de PDF em sequência. A serialização foi exercitada separadamente com dois pedidos concorrentes em threads diretas. O pico desse segundo ensaio, 965,5 MiB (aprox. 1.012,5 MB decimais), **excede 1 GB decimal**. Nenhum desses ensaios substitui medição do servidor publicado.
- A saída do PDF usa [mesclagem de páginas documentada pelo pypdf](https://pypdf.readthedocs.io/en/stable/user/add-watermark.html).

## Verificação da implantação pública (05/11/2026)

- URL informada pelo usuário: https://iluminar-para-proteger.streamlit.app/. A página abriu e despertou normalmente. A interface exibiu limite de contêiner de **3.072 MiB** e RSS inicial de **228,4 MiB** (embora a versão anterior rotulasse esses valores como MB).
- No código atualmente publicado, a pasta `/parquet_samples` ofereceu sete arquivos (2020–2026). A tentativa de retirar 2026 não persistiu na seleção; a carga efetiva processou **seis arquivos, 2021–2026**, confirmados pelo progresso `[1/6]` e pelo resumo de **391.338 ocorrências únicas** a partir de **3.110.897 registros brutos**. Essa observação não é equivalente ao ensaio local de cinco anos (2021–2025).
- Após a carga, um novo processamento da interface exibiu RSS de **1.495,9 MiB**. Uma segunda aba sem carga de dados exibiu **1.536,4 MiB** e contador de apenas uma sessão ativa. O indicador é uma fotografia do RSS no início de cada execução da página, não um monitor de pico; o contador não comprovou duas sessões analíticas ativas.
- Essas leituras foram feitas **antes da publicação** das correções M01–M08 em `3e9e64a`; servem somente como linha de base da versão anterior.

## Publicação e aceite parcial no servidor (05/11/2026)

| Item | Evidência | Status |
|---|---|---|
| M09 | Commit `3e9e64a` enviado ao `main` via HTTPS; a aplicação pública processou cinco arquivos 2021–2025 e mostrou 342.626 ocorrências únicas e 2.702.004 linhas brutas | APROVADO |
| M10 | PDF público baixado com 217.244 bytes, 5 páginas, 2 gráficos, 9 links e numeração correta em todas as páginas; geração exibiu 7,72 s | APROVADO |
| M11 | Após a carga de cinco anos, RSS pontual de 1.272,2 MiB; após gerar PDF e atualizar a interface, 983,2 MiB. A segunda aba carregou o mesmo período, mas o contador da aplicação permaneceu em uma sessão; não há prova de pico nem de duas sessões ativas simultâneas | EM EXECUÇÃO |

- O painel administrativo do Streamlit Cloud exigiu autenticação indisponível nesta sessão. Para medir o pico no próprio servidor, foi acrescentado `RSSPeakSampler` à carga e ao PDF, com amostragem de 20 ms e exibição do resultado na interface. Essa instrumentação ainda precisa ser publicada e exercitada no servidor.
- A função anterior `get_current_rss_mb()` dividia bytes por 1.048.576; os valores mostrados como MB eram, portanto, **MiB**. A interface passa a rotulá-los corretamente. O alvo de 1 GB decimal equivale a aproximadamente **953,7 MiB**.

## Histórico da rodada P01–P08 (02/11/2026)

Referência solicitada: `relatorio_cientifico_iluminar_20261031_171250.pdf` (não localizado no checkout). A comparação foi feita contra o relatório disponível de 31/10/2026 e a validação daquela rodada usou `reports/relatorio_cientifico_iluminar_20261102_174058.pdf` (6 páginas). Os resultados abaixo são históricos; o aceite atual está na seção C01–C12 acima.

| ID | Requisito | Arquivo/função | Status | Evidência de implementação | Evidência de teste | Bloqueio |
|---|---|---|---|---|---|---|
| P01 | Amanhecer sem causalidade presumida | `metrics.py:compute_day_vs_night_comparison` | APROVADO | Texto da página 2 apresenta hipóteses condicionais e mantém as taxas observadas | `test_p01_amanhecer_condicional`; inspeção visual da página 2 | — |
| P02 | Unidades fotométricas | `reaction_analysis.py`, `pdf_generator.py` | APROVADO | Iluminância em lux; luminância em cd/m² | `test_p02_unidades_fotometricas`; busca no texto extraído de todas as páginas | — |
| P03 | Frota, envolvidos e granularidade | `pdf_generator.py:_public_missing`, `compute_veiculo_analysis` | APROVADO | “Não informado”, “Semirreboque”, “1 óbito”; nota distingue veículos de pessoas vinculadas | `test_p03_rotulos_e_granularidade`; consulta aos Parquet 2021–2025: 72.864 veículos, 1 morte vinculada, 9.431 pessoas com envolvimento ausente em 2023; página 3 inspecionada | — |
| P04 | Referências, anos e edições | `config.py:REFERENCES`, `pdf_generator.py` | APROVADO | FHWA 2021, Ipea 2006, IPR-726 3ª edição de 2006, ABNT NBR 5101:2024 4ª edição corrigida; data de consulta separada | `test_p04_referencias_com_ano_e_edicao`; fontes FHWA, DNIT, Ipea e ABNT; página 6 inspecionada | — |
| P05 | Números pt-BR | `reaction_analysis.py`, `pdf_generator.py` | APROVADO | Valores como `11,25`, `1.800,0 Wh`, `0,38 ano`; cálculos financeiros preservados | `test_p05_formato_brasileiro`, `test_dashboard_e_pdf_formatam_os_mesmos_valores_financeiros`; busca no PDF final | — |
| P06 | Paginação e cabeçalhos | `pdf_generator.py:NumberedCanvas`, tabelas de ranking e finanças, referências | APROVADO | Margens ampliadas; ranking repete cabeçalho; matriz mantém título e tabela; bibliografia fica junta | `test_p06_titulo_e_matriz_juntos`; PNGs das 6 páginas vistos individualmente | — |
| P07 | Ranking e conclusões exploratórias | `pdf_generator.py`, `metrics.py` | APROVADO | Pesos heurísticos sem validação empírica; ressalvas sobre inventário de iluminação, VDMA, 35%, custos provisórios e fotometria | `test_p07_ranking_exploratorio_e_ressalvas`; páginas 3 e 5 inspecionadas | — |
| P08 | Gráficos e componentes visuais | `pdf_generator.py` | APROVADO | Legendas, cores, eixos, títulos e unidades dos dois gráficos e tabelas conferidos; nenhuma divergência observada no PDF | `test_p08_pdf_e_graficos_estruturais`; renderização PyMuPDF e inspeção visual das 6 páginas em `temp/pdf_audit_20261102_174058/` | — |

## Validação adicional

- Suíte anterior: 98 testes. Adicionados 10 testes específicos: **108 passaram** (`python -m pytest -q`, 12,69 s).
- Integridade do período: `test_periodo_do_pdf_reflete_apenas_recorte_ativo`; PDF final mostra 2021-01-01 a 2025-12-31 e 342.626 ocorrências. O cabeçalho usa as datas do recorte, não metadados globais.
- Reconciliação: `test_dashboard_e_pdf_formatam_os_mesmos_valores_financeiros`; CAPEX do cenário D no PDF: R$ 89.240.000,00, calculado pela mesma análise que alimenta o dashboard.
- Estrutura: PDF de 6 páginas, páginas com texto e dimensões válidas, gráficos incorporados e referências com links; ausência de `Nan`, `1 óbitos`, unidade fotométrica incorreta e padrões numéricos apontados no pedido.
- Desempenho local medido na geração com os cinco anos, usando cache Parquet: carga 3,47 s; segmentação/finanças concluídas em 4,51 s; geração do PDF 12,58 s; total 17,09 s; pico RSS 1.239,9 MB. A navegação modular e o carregamento sob demanda não foram alterados. **O pico excede 1 GB** nesta execução local; não há comprovação de geração completa abaixo de um teto de 1 GB.

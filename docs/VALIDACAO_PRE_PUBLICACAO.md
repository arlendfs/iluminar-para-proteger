# Validação pré-publicação — 2026-11-08

## Incidente de implantação — 2026-11-09

Após o redeploy, a aplicação pública apresentou `ModuleNotFoundError` no import de `plotly.express`, antes de renderizar o dashboard. O log de implantação recebido mostrou Python **3.14.10**, Plotly baixado e NumPy **2.2.6** compilado a partir do código fonte; a instalação de dependências demorou aproximadamente **46 minutos**. A mensagem completa do módulo ausente não apareceu nos logs disponibilizados. Assim, a causa exata do import não está comprovada, mas o limite `numpy<2.3` selecionava uma versão anterior ao suporte oficial ao Python 3.14.

O `requirements.txt` foi ajustado apenas para selecionar NumPy `>=2.3,<2.6` em Python 3.14+ e preservar `>=1.24,<2.3` nas versões anteriores. Em ambiente limpo local com Python **3.14.10**, `uv` instalou as 73 dependências, incluindo NumPy **2.5.4** binário e Plotly **7.1.0**, em cerca de 16 segundos; `import plotly.express` e `import dashboard` funcionaram. A suíte integral nesse ambiente passou com **161 testes** em 28,84 s. Correção enviada ao `main` no commit `a9eaef3`.

Após o push, a aplicação pública abriu sem autenticação e sem erro de import. Com 2021–2025 carregados, foram confirmadas **342.626 ocorrências únicas nacionais** e a sequência **Vila Velha → Espírito Santo → Vitória → Vila Velha**, com **126 → 12.082 → 38 → 126** ocorrências. O texto publicado de Vila Velha mostra 17,31 versus 6,90 óbitos por 100 acidentes, razão 2,51 e ressalva causal; o estadual mostra reação tardia 16,3% versus 16,4% e ausência de reação 13,9% versus 14,0%; Vitória informa zero óbitos em 38 acidentes sem barras artificiais.

Os PDFs territoriais dos três recortes e o extensionista de Vila Velha foram gerados e **baixados da aplicação pública** com os cinco anos, totalizando **14 páginas** (3, 5, 3 e 3), todas renderizadas e inspecionadas. O ranking municipal de Vila Velha apresenta 9/9 segmentos; o estadual, 40/444 com aviso de parcialidade; Vitória, 6/6. Os arquivos identificam recorte, período, IBGE quando aplicável, fontes e referências. O extensionista declara que não foram fornecidas evidências de apresentação pública ou participação. Uma sessão anônima adicional em `?diagnostics=1` abriu sem apresentar RSS, uso do contêiner ou contador de sessões. Logs de execução após a instalação, RSS e monitoramento longitudinal do contêiner não foram disponibilizados; não se afirma estabilidade contínua. O erro de inicialização observado antes da correção **não se reproduziu** na checagem pública final.

## Ajustes finais pré-divulgação (2026-11-08)

Código e README no commit `2674d71` (`main`). `AGENTS.md` não existe neste checkout. A suíte integral `python -m pytest tests/ -q` passou com **161 testes** em 17,83 s. Os novos testes cobrem flexão 0/1/2, formatação brasileira, ranking completo/limitado com paginação, ausência de barras fictícias na mortalidade zero, dados de mortalidade ausentes, razão de 2,51 em Vila Velha e proporções de reação registradas no ES. Fórmulas estatísticas, score, custos, bases históricas e classificações SNV P/D/I não foram alterados.

Na mesma sessão local, a sequência **Vila Velha → Espírito Santo → Vitória → Vila Velha** retornou **126 → 12.082 → 38 → 126** ocorrências. O PDF municipal de Vila Velha apresenta **9 segmentos identificados e 9 exibidos**, Vitória **6 e 6**. O PDF estadual informa **444 segmentos identificados e 40 exibidos**, com critério de ordem por score e aviso de ranking parcial; a tabela continua em outra página com cabeçalho repetido. Os quatro PDFs (Vila Velha, ES, Vitória e extensionista de Vila Velha) foram gerados, renderizados e inspecionados: **14 páginas** (3, 5, 3 e 3). O gráfico de Vitória declara explicitamente zero óbitos observados entre 38 acidentes, conserva o total de feridos e não desenha barras artificiais. Os textos do ES apresentam reação tardia **16,3% versus 16,4%** e ausência de reação **13,9% versus 14,0%**; Vila Velha apresenta **17,31 versus 6,90**, razão **2,51**, com ressalva de amostra e sem inferência causal. Os campos de aplicação comunitária do PDF extensionista permaneceram vazios.

O README foi revisado quanto a título, comandos PowerShell/Linux, links internos, ausência de placeholders, fontes e número de testes. O ponto de entrada confirmado é `app.py`. Os links internos apontam para arquivos existentes; o dashboard, PRF, DNIT, Geobases e IPEA responderam na checagem HTTP. FHWA respondeu no navegador público; a requisição automatizada ao IBGE foi bloqueada por HTTP 403, sem evidência de URL incorreta. O bloco About do GitHub foi atualizado pela API e confirmado por leitura pública: descrição, website e os oito topics solicitados. O navegador de auditoria estava sem login; a atualização ocorreu com a credencial Git local já autorizada para o repositório.

**Parecer desta etapa:** código e relatórios locais aptos para divulgação científica exploratória e apresentação comunitária, com limitações metodológicas documentadas. A atividade extensionista ainda não foi realizada/comprovada neste registro; vídeo, publicação, data, participantes e feedback exigem evidências reais. Monitoramento longitudinal de memória, logs da hospedagem e validação operacional da BR-447 seguem pendentes sem impedir a divulgação exploratória.

**Implantação pública da revisão:** os commits `2674d71` e o registro de aceite foram enviados ao `main`. Em verificações anônimas logo após o push, o Streamlit ainda exibiu o texto territorial da versão anterior. Portanto, o comportamento novo no servidor publicado **não foi marcado como aprovado** nesta etapa; é necessário confirmar o redeploy no Streamlit Community Cloud e repetir a checagem de texto/ranking/zero óbitos na URL pública. Os downloads e o isolamento entre sessões descritos no fechamento anterior referem-se à implantação anterior à revisão editorial atual.

## Fechamento da versão pública (2026-11-08)

Commit de correção `e9465a8` (`main`). A suíte integral `python -m pytest tests/ -q` passou com **149 testes** em 20,57 s. A reprodução local com os cinco Parquets PRF 2021–2025 percorreu, na mesma sessão, **Vila Velha → Espírito Santo → Vitória → Vila Velha**: 126 → 12.082 → 38 → 126 acidentes. Cada etapa gerou PDF territorial com nome específico de abrangência e recorte, código IBGE municipal, período, indicadores, mapa, ranking e custos condicionais. O relatório estadual apresenta 12.082 ocorrências do recorte estadual; as 126 de Vila Velha não são tratadas como total do ES. O relatório extensionista de Vila Velha foi gerado com campos de evidência vazios.

Foram renderizadas e inspecionadas as 12 páginas dos quatro PDFs resultantes (3 por arquivo), incluindo títulos, números, gráficos, mapas, tabelas e referências. Os arquivos finais locais ficam em `output/pdf/relatorio_territorial_municipio_vila_velha_es_3205200_20261108.pdf`, `output/pdf/relatorio_territorial_estado_espirito_santo_es_20261108.pdf` e `output/pdf/relatorio_extensionista_vila_velha_20261108.pdf`; o PDF de Vitória é artefato adicional da sequência. Os PDFs não são versionados. Na geração local, o processo passou de 194,3 MiB antes da ingestão para 760,4 MiB após a consolidação; são amostras de um ensaio, sem inferência de estabilidade contínua.

O nome anterior `relatorio_territorial_ES_20261108.pdf` era produzido pela regra que usava apenas a UF; não há evidência de renomeação manual. A chave de sessão agora inclui abrangência, código IBGE, período, segmentos, cenário, espaçamento, assinatura da base e identidade dos registros selecionados. Não houve limpeza global de cache. `?diagnostics=1` sem a chave `ILUMINAR_DIAGNOSTICS_TOKEN` configurada no servidor não mostra RSS, limite/uso do contêiner ou contador de sessões. Logs e pico global do contêiner publicado continuam indisponíveis nesta auditoria.

Na implantação pública após `e9465a8`, o acesso anônimo abriu sem GitHub ou autenticação Streamlit. Os cinco anos carregaram 342.626 ocorrências únicas nacionais. A navegação e os downloads seguiram Vila Velha (126) → Espírito Santo (12.082) → Vitória (38) → Vila Velha (126), com nomes de arquivo específicos. Uma segunda sessão anônima carregou apenas 2021 (64.567 ocorrências nacionais); o marcador temporário de feedback da primeira sessão permaneceu ausente no campo correspondente da segunda. O PDF extensionista publicado foi baixado sem evidências preenchidas. A rota pública `?diagnostics=1` não exibiu métricas operacionais. A leitura dos PDFs baixados confirmou os totais por recorte e três páginas por arquivo. O teste não incluiu carga agressiva nem monitoramento contínuo; RSS e uso do contêiner atuais não são observáveis sem a chave administrativa ou o painel da hospedagem.

**Parecer:** apto para divulgação científica exploratória. Entrega extensionista com evidências depende de vídeo/publicação, data, participantes, comentários e resultados reais da apresentação; esses campos não foram preenchidos. Pendências técnicas não impeditivas: acesso a logs do host e monitoramento longitudinal de memória, data exata de publicação dos ZIPs SNV e validação operacional da BR-447. Erros impeditivos de publicação identificados nesta reprodução local: nenhum.

Estados: **APROVADO** (evidência executada), **APROVADO COM RESSALVA** (uso exploratório com limite explícito), **BLOQUEADO** (fonte/acesso externo necessário) e **REPROVADO** (erro conhecido sem mitigação).

| Critério | Estado | Evidência e limite |
|---|---|---|
| 1. Ingestão e deduplicação | APROVADO | Suíte Pytest integral e carga real de cinco Parquets PRF. |
| 2. Totais estatísticos | APROVADO | Vila Velha: 126 acidentes, 16 óbitos, 52 plena noite, 58 pleno dia; 17,31 e 6,90 óbitos/100. |
| 3. Ocorrências e pessoas | APROVADO | `id` e `(id,pesid)` em tabelas distintas; testes de desduplicação. |
| 4. Causas múltiplas | APROVADO | Tabela relacional com ocorrência única e categorias sobrepostas identificadas. |
| 5. Auditoria territorial | APROVADO COM RESSALVA | CSV por ocorrência de Vila Velha e Vitória; ponto no polígono não certifica pista. |
| 6. Proveniência SNV | APROVADO COM RESSALVA | 23 ZIPs oficiais, hashes e recortes ES; data exata de publicação não confirmada. |
| 7. Ranking | APROVADO COM RESSALVA | Score heurístico por BR/KM; segmentos em triagem, sem fluxo de tráfego e sem validação física. |
| 8. Interpretação científica | APROVADO COM RESSALVA | Causas e gravidade distinguidas; sem inferência causal da iluminação. |
| 9. Custos | APROVADO COM RESSALVA | Segmentos selecionados explicitados nos PDFs; hipótese geométrica; sem VPL territorial. |
| 10. PDFs | APROVADO | Vila Velha, Espírito Santo, Vitória e extensionista gerados; 12 páginas renderizadas/inspecionadas; downloads públicos verificados. |
| 11. Fontes | APROVADO COM RESSALVA | PRF, IBGE, DNIT e FHWA citados; publicação exata dos ZIPs SNV indisponível. |
| 12. README | APROVADO COM RESSALVA | Estado atual e limitações revisados; valores hipotéticos nacionais permanecem condicionais. |
| 13. Performance local | APROVADO | Perfil AppTest final: 781,7 MiB após carga; 903,3 MiB no módulo histórico; 941,4 MiB após PDF. Uma execução local, não limite garantido. |
| 14. Performance publicada | APROVADO COM RESSALVA | Três sessões controladas, uma com 2021–2025 e duas com 2021, abriram e renderizaram sem erro; amostras RSS e limite abaixo. Outras sessões preexistiam e não houve acesso a logs ou pico global do contêiner. |
| 15. Testes automatizados | APROVADO | Suíte integral de 2026-11-08: 149 testes aprovados. |
| 16. Navegação pública e downloads | APROVADO | Commit `e9465a8` aberto sem login: sequência de quatro recortes, três PDFs territoriais e extensionista baixados. |
| 17. Segurança dos dados publicados | APROVADO COM RESSALVA | Evidência temporária isolada entre duas sessões; diagnóstico operacional oculto sem chave. Logs e arquivos temporários do servidor não auditados. |
| 18. Limitações documentadas | APROVADO | Metodologia explicita tempo da malha, SNV, amostra, custos e ausência de medição de iluminação. |

## Comparação geográfica por referência

| Município | Base PRF | Referência única SNV 202507A | Referências históricas por mês anterior |
|---|---:|---|---|
| Vila Velha | 126 | 115 plausíveis; 7 KM incompatível; 3 sem traçado; 1 distante | 105 plausíveis sem confirmação histórica; 18 divergências; 3 insuficientes |
| Vitória | 38 | Ver CSV e PDF | 28 plausíveis sem confirmação histórica; 4 divergências; 6 insuficientes |

Os totais de cada método não são intercambiáveis. Na BR-447 de Vila Velha, 40 ocorrências no KM 12–16 passam por referências históricas com 24 plausíveis e 16 divergências; o cadastro do trecho mais próximo é 23 vezes “Pavimentada”, 13 “Planejada” e 4 “Duplicada”. A classificação cadastral não estabelece se a pista específica estava aberta no momento do acidente.

## Artefatos de revisão

- `assets/snv_es_historico_manifest.json`: arquivos, versões e hashes.
- `output/auditoria/auditoria_snv_vila_velha_2021_2025.csv` e `output/auditoria/auditoria_snv_vitoria_2021_2025.csv`: tabelas por ocorrência, não versionadas.
- `output/pdf/relatorio_territorial_municipio_vila_velha_es_3205200_20261108.pdf`, `output/pdf/relatorio_territorial_estado_espirito_santo_es_20261108.pdf` e `output/pdf/relatorio_extensionista_vila_velha_20261108.pdf`: PDFs finais locais, não versionados.

## Medições publicadas controladas

Em `https://iluminar-para-proteger.streamlit.app/?diagnostics=1`, após publicar `55ad31e`, a primeira sessão controlada carregou 2021–2025 com pico RSS amostrado na carga de **1.450,5 MiB** (limite cgroup **3.072 MiB**), renderizou Estudos Territoriais em **11,156 s** para Vila Velha e **11,977 s** para Vitória e gerou PDF territorial em **0,579 s**. RSS apresentado após renderização: **1.249,7–1.263,0 MiB**. Os painéis exibiram 105/18/3 para Vila Velha e 28/4/6 para Vitória.

Após publicar `b52f9e5`, o diagnóstico novo apareceu na implantação: **RSS 1.094,0 MiB**, **uso do contêiner 1.699,3 MiB**, limite ainda **3.072 MiB**, disponibilidade no hospedeiro **90.091 MiB** e **6 sessões ativas estimadas** naquele instante. A memória disponível do hospedeiro não é a folga do contêiner. As sessões de teste abertas por esta auditoria foram fechadas após a observação.

Abriram-se duas sessões adicionais. O contador estimou 3, depois 4 e 5 sessões ativas, pois havia sessões preexistentes; não são contagens exclusivas deste ensaio. A segunda e a terceira carregaram somente o Parquet 2021, com picos de carga informados de **1.109,3 MiB** e **1.096,3 MiB**, respectivamente. A limpeza da terceira sessão retirou sua análise sem impedir que a segunda permanecesse carregada; o RSS imediatamente após limpeza foi **1.099,4 MiB**, sem redução imediata comprovada. As leituras entre abas variaram e podem refletir coleta em momentos ou processos distintos; não se atribui crescimento por sessão a esses números. Não houve teste de carga agressivo.

Para coleta administrativa adicional: configurar `ILUMINAR_DIAGNOSTICS_TOKEN` no servidor, abrir `?diagnostics=1` em sessão isolada e informar a chave; registrar RSS, uso/limite do contêiner e disponibilidade do hospedeiro antes/depois da carga, módulo e PDF. Repetir três reruns e observar sessões adicionais sem carga agressiva. Associar os valores aos logs da hospedagem para obter pico global e detectar reciclagem de processos. Sem acesso ao painel da hospedagem, o pico global e vazamento de longo prazo permanecem **não verificados**.

**Parecer:** apto para divulgação como estudo exploratório, com as ressalvas temporais, geográficas, causais, econômicas e de memória acima. Não equivale a certificação de engenharia rodoviária.

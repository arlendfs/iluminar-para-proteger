# Validação pré-publicação — 2026-11-07

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
| 10. PDFs | APROVADO | Vila Velha, Vitória e extensionista gerados; conteúdo e páginas renderizadas/inspecionadas. |
| 11. Fontes | APROVADO COM RESSALVA | PRF, IBGE, DNIT e FHWA citados; publicação exata dos ZIPs SNV indisponível. |
| 12. README | APROVADO COM RESSALVA | Estado atual e limitações revisados; valores hipotéticos nacionais permanecem condicionais. |
| 13. Performance local | APROVADO | Perfil AppTest final: 781,7 MiB após carga; 903,3 MiB no módulo histórico; 941,4 MiB após PDF. Uma execução local, não limite garantido. |
| 14. Performance publicada | APROVADO COM RESSALVA | Três sessões controladas, uma com 2021–2025 e duas com 2021, abriram e renderizaram sem erro; amostras RSS e limite abaixo. Outras sessões preexistiam e não houve acesso a logs ou pico global do contêiner. |
| 15. Testes automatizados | APROVADO | Última suíte: 147 testes aprovados; repetir após fechamento. |
| 16. Navegação pública e downloads | APROVADO | Commit `55ad31e` aberto em Streamlit: estudos de Vila Velha e Vitória, triagem SNV histórica e botão de download do PDF territorial observados. |
| 17. Segurança dos dados publicados | APROVADO COM RESSALVA | Fonte PRF pública; evidências extensionistas opcionais ficam na sessão. Revisar logs e arquivos temporários após deploy. |
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
- `output/pdf/relatorio_territorial_vila_velha_v2.pdf`, `output/pdf/relatorio_territorial_vitoria_v2.pdf` e `output/pdf/relatorio_extensionista_vila_velha_v2.pdf`: PDFs locais, não versionados.

## Medições publicadas controladas

Em `https://iluminar-para-proteger.streamlit.app/?diagnostics=1`, após publicar `55ad31e`, a primeira sessão controlada carregou 2021–2025 com pico RSS amostrado na carga de **1.450,5 MiB** (limite cgroup **3.072 MiB**), renderizou Estudos Territoriais em **11,156 s** para Vila Velha e **11,977 s** para Vitória e gerou PDF territorial em **0,579 s**. RSS apresentado após renderização: **1.249,7–1.263,0 MiB**. Os painéis exibiram 105/18/3 para Vila Velha e 28/4/6 para Vitória.

Abriram-se duas sessões adicionais. O contador estimou 3, depois 4 e 5 sessões ativas, pois havia sessões preexistentes; não são contagens exclusivas deste ensaio. A segunda e a terceira carregaram somente o Parquet 2021, com picos de carga informados de **1.109,3 MiB** e **1.096,3 MiB**, respectivamente. A limpeza da terceira sessão retirou sua análise sem impedir que a segunda permanecesse carregada; o RSS imediatamente após limpeza foi **1.099,4 MiB**, sem redução imediata comprovada. As leituras entre abas variaram e podem refletir coleta em momentos ou processos distintos; não se atribui crescimento por sessão a esses números. Não houve teste de carga agressivo.

Para coleta manual adicional: abrir `?diagnostics=1` em uma sessão isolada, registrar RSS, uso/limite do contêiner e disponibilidade do hospedeiro antes e depois da carga; registrar tempo e RSS antes/depois de cada módulo e PDF; repetir três reruns idênticos; abrir duas sessões adicionais de forma sequencial, com a mesma seleção, anotando horário e leituras; limpar uma sessão e conferir que as demais mantêm os dados. Associar os valores aos logs e métricas da hospedagem para obter o pico global e detectar reciclagem de processos. Sem acesso ao painel da hospedagem, o pico global e vazamento de longo prazo permanecem **não verificados**.

**Parecer:** apto para divulgação como estudo exploratório, com as ressalvas temporais, geográficas, causais, econômicas e de memória acima. Não equivale a certificação de engenharia rodoviária.

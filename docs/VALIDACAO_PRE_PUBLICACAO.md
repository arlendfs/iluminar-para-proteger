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
| 13. Performance local | APROVADO | Perfil AppTest: pico após módulo histórico otimizado 923,3 MiB; após PDF 954,3 MiB. |
| 14. Performance publicada | BLOQUEADO | Teste de 1–3 sessões e métricas após novo deploy ainda não executados. |
| 15. Testes automatizados | APROVADO | Última suíte: 147 testes aprovados; repetir após fechamento. |
| 16. Navegação pública e downloads | BLOQUEADO | Versão anterior verificada em Streamlit; novas alterações aguardam publicação e conferência. |
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

**Parecer provisório:** divulgação como estudo exploratório condicionada à repetição da suíte final e à verificação da implantação publicada. Nenhuma evidência sustenta certificação de engenharia ou efeito causal de postes.

# Decisão técnica

**Prioridade: medir reutilização de prefixo e retomada no llama.cpp existente.** O código experimental é um harness cliente novo e reversível; não altera runtime, modelos, instalações ou evidência histórica. Os testes de protocolo executados sustentam que o experimento é reproduzível, não que já haja aceleração.

Motivos: a NCMA tem workloads de contexto longo e retomada; prefill repetido pode dominar TTFT. O llama.cpp já fornece LCP, `cache_prompt`, snapshots e cache RAM. Esse caminho não depende de kernels SM100, topologia distribuída nem treinamento de um draft. A hipótese é refutável por `cache_n`, TTFT, tokens processados e custo de restore.

A investigação encontrou obstáculos concretos para o port direto do DeepInfer (FlashMLA SM100f versus RTX SM120, topologia YOCO/CED não genérica e serviço distribuído de KV ausente), mas **não conclui inviabilidade de otimizar o laboratório**. Especulação existente, batch/offload e estabilidade de prompt permanecem alternativas a medir. O suporte `draft-dspark` já presente no llama.cpp evita uma reimplementação prematura; compatibilidade por modelo ainda está em RESEARCH.

## Evidência e limite da conclusão

- [Fonte auditada e versões](SOURCE_AUDIT.md), [matriz](FEASIBILITY.md), [metodologia/evidências](BENCHMARKS.md).
- Suite original executada antes da edição; suite completa e testes HTTP reais contra fixture sem inferência executados após o código final. Resultados em `validation.json`.
- Nenhum runtime/modelo alcançável nesta sessão; NCMA Direct retornou erro interno. Não foi possível inspecionar o Git ou as alterações locais do workspace Windows. Trabalhamos em clone novo da base publicada; nenhum arquivo Windows foi tocado.
- Portanto **ganho de inferência NCMA: NÃO MEDIDO**, compatibilidade de snapshot com os modelos locais: NÃO PROVADA. Benchmark CPU da máquina desta sessão também não substitui a RTX ou a OCI.

## Riscos e critérios de avanço

1. Rodar o harness em servidor isolado já verificado, começando em 16K; confirmar `cache_n=0` no baseline e >0 na variante. Registrar percentual do prefixo realmente reutilizado.
2. Comparar TTFT por repetição, tokens processados, outputs e custo de prime/restore. Só recomendar adoção se o ganho se repetir na carga relevante e não degradar correção/memória. Nenhuma meta percentual foi inventada.
3. Para integração com o agente: preservar prefixo renderizado, ferramenta/template e progresso validado; medir efeito de nova mensagem/compactação separadamente. KV não substitui checkpoint de agente.
4. Antes de snapshots em produção: confirmar serialização de memória híbrida, versão/modelo e reidratação após reinício num teste independente; não usar o teste intra-processo como comprovação de durabilidade.
5. Só depois estudar draft específico por modelo e ajustar offload/batches com RAM/VRAM monitoradas. OCI deve receber uma execução própria, sem inferir resultados CUDA.

Reverter a prova de conceito consiste em remover os diretórios adicionados e o teste novo, ou reverter os commits desta branch. Não há hooks de execução no runtime principal. A branch é publicada para revisão, sem merge automático. O manifesto histórico de publicação e os benchmarks anteriores permanecem intactos.

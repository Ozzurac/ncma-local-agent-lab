# DeepInfer → NCMA Local LLM Optimization

Investigação em **31/10/2026**. Resultado: **harness reproduzível implementado e testado; ganho de inferência ainda NÃO MEDIDO**.

Escolha: demonstrar a reutilização exata de prefixo já existente no llama.cpp, comparando `cache_prompt=false` e `true`; opcionalmente salvar/apagar/restaurar um slot. Evita prefill repetido quando o prefixo realmente coincide. Não porta kernels do DeepInfer nem altera o coordenador NCMA.

| Fonte | Commit auditado |
|---|---|
| DeepInfer | `553741557a57df44a46fb3ab72b6aafeaf945337` |
| llama.cpp | `ddf48f85c933c1f438212a02eb21e7b001d2d37d` |
| NCMA, base preservada | `8e2306c2edc7d3e1c54fb34fe6874f2d84266806` |

O DeepInfer público é voltado a DeepSeek V4.1 Flash e SM100/Ascend 950. A publicação inclui scheduler, DSpark e replay específico do modelo; o armazenamento distribuído completo de KV e os balanceadores de serviço permanecem fora dela. Isso não impede aproveitar princípios de reutilização no runtime local.

- [Auditoria de código e fontes](SOURCE_AUDIT.md): algoritmos, símbolos, hardware, licenças e partes ausentes.
- [Viabilidade e comparação](FEASIBILITY.md): matriz RTX/ARM e distinções entre cache, sliding window e estado do agente.
- [Metodologia e evidências](BENCHMARKS.md): execução realizada, ausência de runtime e limites das medições.
- [Decisão](DECISION.md): prioridade, riscos e critérios para avançar.
- [Experimento e reprodução](../../experiments/deepinfer/README.md).
- [Fontes fixadas](source_lock.json), [verificação de conteúdo](../../benchmarks/deepinfer/evidence/source_verification.json), [validação](../../benchmarks/deepinfer/evidence/validation.json) e [ambiente](../../benchmarks/deepinfer/evidence/environment.json).

Os testes de HTTP usam uma fixture sem LLM. Seus tempos não são publicados como performance. Não foram baixados modelos, compilados kernels ou alterados drivers, Unsloth, OCI ou instalações globais. O checkout Windows não foi acessado: esta branch foi produzida em um clone independente do repositório publicado.

# Viabilidade e comparação com llama.cpp

Estados: **READY** = implementado e testável com runtime/modelo compatíveis; **ADAPT** = integração limitada; **RESEARCH** = falta investigar invariantes/desempenho; **BLOCKED** = impedimento concreto do caminho proposto. READY não significa que houve inferência neste ambiente. Fontes, símbolos e restrições: [auditoria](SOURCE_AUDIT.md).

## Matriz de oportunidades

| Oportunidade | RTX 5070 | OCI Ampere CPU | Custo / manutenção | Regressão | Execução nesta missão | Potencial NCMA (hipótese) |
|---|---|---|---|---|---|---|
| Prefixo exato em slot, `cache_prompt` | READY | READY no backend CPU | Baixo / baixo | Baixo, medir divergência de batch | Harness e contratos executados; LLM indisponível | Alto para retomadas com prefixos estáveis; atua em TTFT |
| Save/erase/restore de slot | ADAPT por modelo/build | ADAPT por modelo/build | Baixo / médio | Médio: estado híbrido, formatos/versionamento | Contrato testado; snapshot real pendente | Evitar prefill após reidratação; I/O pode anular ganho |
| Estabilizar prompt renderizado pelo agente | ADAPT | ADAPT | Médio / médio | Médio: semântica de templates/ferramentas | Diagnóstico proposto, sem mudar agente | Preservar LCP entre turnos; não exige kernel novo |
| Ajustar `-b`, `-ub`, slots e offload | READY | READY, flags CPU distintas | Baixo / baixo | Médio: OOM, latência, competição | Sem runtime; manter A/B separado | Alto se gargalo for batch/memória; não há knob ótimo universal |
| n-gram speculation já presente | RESEARCH | RESEARCH | Baixo / baixo | Médio por tipo de memória/rollback | Código disponível; nenhuma medição | Pode ajudar conteúdo repetitivo; aceitação baixa pode perder |
| Draft externo / EAGLE3 / MTP já presentes | RESEARCH por GGUF/draft | RESEARCH, RAM e CPU limitantes | Médio / médio | Médio/alto | Checkpoints locais não acessíveis | Decode maior se custo de draft compensar verificação |
| DSpark dinâmico de DeepInfer | RESEARCH; port direto BLOCKED por runtime/modelo | BLOCKED como port CUDA | Alto / alto | Alto: confiança, scheduler, sampler | Só leitura estática | Não estimar ganhos EP64 no agente de slot único |
| SWA bounded replay YOCO direto em GGUF genérico | BLOCKED sem topologia/invariantes compatíveis | BLOCKED pelo mesmo motivo | Alto / alto | Alto: atenção aproximada/correção | Nenhuma inferência | Sem benefício genérico demonstrado |
| FlashMLA SM100f / DeepGEMM Mega MoE como substituição direta | BLOCKED no caminho SM100f; novos kernels RESEARCH | BLOCKED sem acelerador | Muito alto / alto | Alto | Guard de arquitetura inspecionado | Nenhum ganho pronto para RTX/ARM |
| Wide-EP / EPLB / DeepEP | BLOCKED na topologia de uma GPU | BLOCKED na A1 sem GPUs | Muito alto / alto | Alto | Sem cluster | Não resolve automaticamente experts offloaded em RAM |
| Pipeline ZOS portada para ggml | RESEARCH | RESEARCH de outra pipeline CPU | Alto / alto | Alto: sincronização/lifetime | Código lido, não portado | Só após perfil mostrar bolhas relevantes |
| Grammar/structured outputs existentes | READY, por contrato de backend | READY, por contrato de backend | Baixo / baixo | Médio: semântica e overhead | Validador NCMA já testado; geração nova pendente | Menos falhas de formato, não necessariamente mais tok/s |
| 3FS KV service / TTL de dias | BLOCKED: serviço completo ausente | BLOCKED: mesma dependência | Muito alto / alto | Alto | Não implantado | Excesso de infraestrutura para uma sessão local |

## O que o llama.cpp já faz

Referência atual `ddf48f85c933c1f438212a02eb21e7b001d2d37d`, diferente do b11588 histórico da NCMA. As opções devem ser verificadas no binário efetivamente usado; não presumimos que o Unsloth embute esse commit.

| Mecanismo existente | Implementação auditada | Aplicação e limite |
|---|---|---|
| LCP do slot e `cache_prompt` | `tools/server/server-context.cpp`: `get_common_prefix`, `stats.n_prompt_cached` | Reaproveita prefixo idêntico; mudança no início perde hits posteriores. `tokens_cached` no resultado é tamanho do slot, **não** hit count; usar `timings.cache_n`. |
| Cache de prompts em RAM | `server_prompt_cache::alloc/load/update`, `tools/server/server-task.cpp`; `--cache-ram`, `--cache-idle-slots` | Guarda/restaura estados e escolhe prefixos; alocação adicional em host. Desativado no experimento para isolar slot residente. |
| Persistência explícita | `/slots/{id}?action=save/restore/erase`, `llama_state_seq_save_file/load_file` | Estado binário e metadados de prompt; não é formato portátil entre versões/modelos. Arquivos de estado permanecem fora do Git público. |
| Especulação | `common/speculative.cpp`, `src/models/dflash.cpp`, `docs/speculative.md` | Draft simples, EAGLE3, MTP, DSpark, DFlash e n-grams existem; compatibilidade precisa de verificação do modelo, tokens, memória e rollback. |
| Continuous batching | loop de slots e batches em `server-context.cpp` | Concorrência entre solicitações; não equivale a threads de agente nem ZOS integral. Fixar um slot no teste de latência. |
| Batch e microbatch | `common/arg.cpp`: `--batch-size`, `--ubatch-size` | Batch lógico vs limite físico de execução; não é correto maximizar ambos cegamente para 12 GB. |
| Offload e KV | `include/llama.h`, backend ggml CUDA, `src/llama-kv-cache.cpp` | Pesos e KV competem com buffers de compute. GGUF/mmap de pesos não é cache persistente de sessão. |

Para atenção padrão, a ordem de grandeza do KV é proporcional a `tokens × camadas × (dim_K + dim_V) × bytes`, com heads, quantização, alinhamento e metadados corretos. SWA, MLA e memória híbrida/recurrente alteram esse cálculo. Não estimar VRAM de 96K somente a partir do número de parâmetros/quantização dos pesos. Mais contexto configurado não significa que todo request usa esse número de tokens.

## Speculation por workload

| Workload declarado | O que foi encontrado | O que falta antes de chamar READY |
|---|---|---|
| GPT-OSS 20B | Suporte base no backend `src/models/openai-moe.cpp`; docs atuais listam draft EAGLE3 específico para GPT-OSS 20B | Hash/arquitetura do GGUF alvo, pesos e licença do draft, versão do runtime, hidden-state contract e medição de memória/aceitação. Não presumir MTP nativo. |
| Qwen 35B MoE | `src/models/qwen35moe.cpp` tem caminho NextN/MTP; n-grams/draft-simple são mecanismos gerais condicionados ao runtime | Nome comercial 35B não identifica arquitetura/conversão; verificar metadados e tensores NextN, inclusive se a quantização os preservou. DSpark Qwen3-4B de exemplo não é draft para qualquer Qwen. |
| Nemotron 74B quantizado | `src/models/nemotron-h-moe.cpp` contém bloco MTP para essa família | Confirmar família do checkpoint local e presença de tensores MTP, capacidade de rollback da memória híbrida, RAM/VRAM e custo CPU. Não generalizar a todo Nemotron. |

A ausência de acesso a esses GGUF é uma lacuna de evidência, não prova de que nenhuma especulação funciona.

## Cinco estados diferentes

| Estado/mecanismo | O que preserva/muda | Relação com nova mensagem |
|---|---|---|
| KV reutilizável | Tensores computados para prefixo/tokens/posições do modelo | Evita computar novamente se modelo, prefixo e estado ainda coincidirem |
| Context shifting / SWA | Descarte/reposicionamento ou atenção limitada por arquitetura | Altera conteúdo/visibilidade; pode invalidar parte do cache e não sumariza a conversa |
| Auto-compactação | O harness troca histórico por resumo/seleção, com política própria | Muda os tokens enviados e exige novo prefill desde a primeira diferença |
| Checkpoint do agente | Plano, decisões verificadas, progresso, referências e ferramentas | Recupera o trabalho após novo processo; não contém necessariamente KV |
| Snapshot de inferência | Estado binário do backend e tokens do slot | Pode evitar prefill após restore compatível; não recupera plano/ferramentas sozinho |

A [recuperação G4H existente](../../docs/G4H_SEQUENCE.md) prova continuidade de progresso validado, não persistência de KV nem correção da auto-compactação do Unsloth. Se um sistema reordena ferramentas, insere timestamps no início ou reescreve resumos, o LCP pode cair mesmo que a aplicação exiba a mesma conversa. O harness mede o mecanismo de inferência; diagnosticar Unsloth exige capturar hashes/tamanhos do prompt renderizado e cache hits no seu processo real, com autorização/dados sanitizados.

## ARM OCI: alvo independente

Usar llama.cpp CPU compilado para a máquina Ampere, um modelo já disponível que caiba em RAM e threads coerentes com OCPUs realmente alocadas. Executar o mesmo harness via loopback; `gpu_layers=0`, sem extrapolar resultados x86/CUDA. Primeiro medir prefill/decode e memória; depois variar threads/batch em experimentos separados. Não foram consultados ou alterados serviços OCI: esse alvo recebeu análise de código, sem benchmark ou inventário ao vivo. Acesso OCI disponível em outras integrações não comprova um runtime pronto nem justifica implantar modelos grandes.

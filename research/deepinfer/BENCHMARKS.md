# Benchmarks e evidências

## O que realmente foi executado

| Execução | Resultado observado | O que NÃO demonstra |
|---|---|---|
| Suite original, antes das alterações | 15 testes, exit 0 | Não é um novo benchmark de modelo |
| Suite final, original + regressões experimentais | Ver contagem e casos em [validation.json](../../benchmarks/deepinfer/evidence/validation.json) | HTTP sintético não mede tok/s de LLM |
| `npm test --prefix experiments/openai-agents-sdk` histórico | Exit 0, **zero testes descobertos** pelo Node desta sessão | Não constitui validação do SDK; não foi instalado pacote ou chamado modelo |
| Verificação dos commits e blobs externos | [source_verification.json](../../benchmarks/deepinfer/evidence/source_verification.json) | Não compila nem executa DeepInfer/llama.cpp |
| Probe loopback do runtime | [runtime_probe/report.json](../../benchmarks/deepinfer/evidence/runtime_probe/report.json): falha de conexão (`URLError`), exit 2 | Não prova que o runtime Windows esteja parado |
| Detecção do ambiente e caminho remoto | [environment.json](../../benchmarks/deepinfer/evidence/environment.json): Linux x86_64; sem GPU/runtime detectados; consultas NCMA Direct falharam | Não é inventário do computador de referência nem da OCI |
| Revisão de publicação | Scanner do repositório + conferência de arquivos adicionados; registro em validation.json | Scanner automatizado não substitui revisão humana futura de resultados locais |

**Nenhuma medição nova de TTFT, prefill/decode tok/s, RAM/VRAM máxima ou ganho percentual está disponível.** O ambiente desta sessão não é o Ryzen/RTX da referência. Não instalamos runtime/toolchains nem baixamos modelo para fabricar um benchmark substituto. Os impedimentos e o probe com saída não zero foram preservados.

Tentativa intermediária preservada em `validation.json`: o verificador de fontes inicialmente não conseguiu gravar em um diretório de saída ainda inexistente (`FileNotFoundError`). O script passou a criar somente o diretório pai e manter abertura exclusiva do arquivo; a reexecução verificou os 74 blobs. A primeira execução bem-sucedida havia conferido 73 blobs; a inclusão da fonte linear ampliou o lock para 74.

Referência histórica (não baseline deste A/B): [G3](../../docs/RESULTS.md) registrou 77.103 input tokens, prefill 162,4 s (~475 tok/s), decode 474,7 s (~34,5 tok/s), sem resposta final. G4H fez 44 chamadas pequenas com checkpoint e validação. Não se pode comparar essas tarefas diretamente ao fixture novo, a outro commit ou a outro modelo.

## Experimento entregue

[Comandos completos e metadata](../../experiments/deepinfer/README.md). Usa apenas stdlib Python, endpoint nativo de llama-server e dados sintéticos fixos. Não executa ferramentas de agente nem entra no processo Unsloth.

1. Servidor dedicado, um slot, speculation/context shifting/cache RAM desligados; anotar exatamente binário, commit, hashes do modelo/tokenizer e flags.
2. Pré-tokenizar prefixo e sufixo via `/tokenize`. Concatenar arrays explicitamente, sem BPE implícito na fronteira. O hash e número efetivo de tokens são gravados.
3. Antes de **cada observação**, executar prime com o prefixo, `cache_prompt=false` e 1 token de geração. O custo do prime é registrado separadamente: não existe cache gratuito em uma sessão fria.
4. Executar a continuação com o array idêntico: baseline `cache_prompt=false`, variante `true`. Fixar sampling, n_predict, slot, tokenizer, hardware e configuração. Alternar ordem entre rodadas.
5. Fazer ≥1 warmup completo e ≥2 repetições medidas (padrão 5). Preservar cada observação, inclusive warmup. Publicar mediana, min/max e desvio amostral de TTFT e total; consultar métricas de servidor em cada trial.
6. Opcional `--snapshot`: prime → save → erase → restore → continuação com cache. Cronometrar todas as operações; `resume_including_restore_ms` soma restore e TTFT. Essa é reidratação no mesmo processo, **não** prova de recuperação após reinício/crash ou entre versões.
7. Rejeitar respostas truncadas, ausência de timings finais, baseline com hit, variante sem hit e orçamento de geração diferente. Preservar trials anteriores e status de falha. Comparar hashes de texto e tokens gerados, sem presumir igualdade bit a bit.

O prefixo enviado no segundo turno é o prompt fixo original, sem anexar a resposta gerada no prime. A finalidade é isolar prefixo estável + sufixo novo; não simula uma conversa completa. Para conclusão sobre o agente, repetir posteriormente usando o prompt realmente renderizado e o contrato de ferramentas correto.

## Definições e interpretação

- **TTFT**: `perf_counter` do POST até primeiro evento SSE com token ID ou conteúdo; ignora keepalives/eventos vazios. Inclui fila, HTTP local e prefill; não inclui tokenização antecipada do setup. É TTFT cliente de tokens, não tempo até primeiro texto visível após reasoning do modelo.
- **Prompt/decode throughput**: valores de `timings.prompt_per_second` / `predicted_per_second` reportados pelo servidor; consultar também `prompt_n`, `predicted_n`, `prompt_ms`, `predicted_ms`. No cache hit o denominador usa trabalho processado, não todos os tokens do request.
- **Cache hit**: `timings.cache_n`; **não** o campo `tokens_cached` (tamanho restante do slot). `reused_prefix_fraction` identifica reutilização parcial, possível em SWA/memória híbrida. Hit >0 não prova que todo o prefixo foi preservado.
- **Retomada**: TTFT da continuação aquecida; variante restored inclui custo de restore em campo separado. Save e erase não estão escondidos na latência total de continuação.
- **Latência total**: POST até fim do stream. Setup/prime/slot I/O são separados e devem ser incluídos se a pergunta for custo de sessão fria inteira.
- **RAM/VRAM**: o harness não tem sampler portátil do processo servidor; campos máximos são `null`. Não são zero nem máximos do processo cliente. Para medir de verdade, instrumentar PID servidor e GPU dedicada com frequência conhecida, incluindo warmup e estados salvos; registrar se leitura é amostrada ou high-water mark. Não alegar ganho de memória sem essa coleta.
- **Estabilidade/correção**: capturar falhas e divergências de saída. Diferenças podem vir de forma/tamanho de batch; saída igual neste fixture também não comprova equivalência geral. Avaliar depois a tarefa NCMA com oráculo independente.

Todos os dados brutos gerados ficam inicialmente em `runs/` (ignorado). Somente os relatórios desta missão, sem saída de modelo real ou dados do usuário, foram selecionados para `benchmarks/deepinfer/evidence/`. Nunca publicar snapshots binários, modelos ou dumps de `/props` (podem conter caminhos). Metadata fornecida pelo operador precisa de revisão antes de publicação.

## Próxima medição válida

Primeiro usar contexto de 16K e fixture pequeno no runtime já disponível. Depois ampliar `--lines` sem exceder o contexto real verificado em `/props`; isso aumenta input de fato, ao contrário de somente configurar 96K. Repetir por modelo, incluindo variantes híbridas, e por hardware em experimentos separados. Para cada comparação, manter flags iguais, servidor ocioso e modelo idêntico; só então variar batch/offload/speculation em estudos independentes.

Fora do escopo medido: benchmark GPU DeepInfer, PPL/logits de YOCO, desempenho ARM, ferramentas do agente, auto-compactação ou reparo do Unsloth. Não atribuir os números de produção upstream à NCMA.

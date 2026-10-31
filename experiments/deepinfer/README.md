# Prefix reuse / slot restore experiment

Experimento stdlib Python 3.12+, isolado do runtime NCMA. O servidor deve ser um **llama-server nativo dedicado e conhecido**, já disponível; o programa não baixa/carrega modelos, não inicia serviço, não instala pacotes e não executa comandos do modelo. Backend OpenAI compatível genérico e Unsloth não bastam: são necessários `/health`, `/props`, `/tokenize`, SSE `/completion`, `timings.cache_n` e, para a etapa opcional, `/slots/0`.

## Offline: testes sem GPU/modelo

Na raiz do checkout:

```sh
python -m unittest discover -s tests -v
python -m compileall -q src experiments/g3 experiments/deepinfer
python scripts/scan_publication.py
```

`tests/test_deepinfer_prefix_bench.py` usa um servidor HTTP local sintético para testar transporte, ordem, validações e falhas. Isso NÃO é um benchmark de inferência. Não usar os tempos desse servidor em relatórios de performance.

## Preparação Windows / PowerShell 7

Use um checkout separado desta branch para não misturar alterações locais. Confira `git status` e AGENTS antes. Defina os três caminhos para artefatos **já existentes** e conferidos:

```powershell
$Server = $env:NCMA_LLAMA_SERVER
$Model = $env:NCMA_GGUF
$LlamaSource = $env:NCMA_LLAMA_SOURCE
if (!(Test-Path -LiteralPath $Server) -or !(Test-Path -LiteralPath $Model) -or !(Test-Path -LiteralPath $LlamaSource)) { throw 'Configure os caminhos dos artefatos existentes' }
& $Server --version
& $Server --help
```

O binário deve corresponder ao commit do seu source checkout. Commit auditado do llama.cpp: `ddf48f85c933c1f438212a02eb21e7b001d2d37d`; b11588 do benchmark antigo pode não expor as mesmas flags/métricas. Não executar um binário recém-obtido sem conferir procedência e hash. Não atualizar Unsloth ou driver para este teste.

Exemplo conservador de configuração controlada **CPU**, não prescrição de melhor performance da RTX. Em um terminal dedicado:

```powershell
New-Item -ItemType Directory -Force runs/deepinfer-slots | Out-Null
& $Server -m $Model --host 127.0.0.1 --port 18991 --ctx-size 16384 --parallel 1 --batch-size 512 --ubatch-size 128 --threads 8 --threads-batch 8 --n-gpu-layers 0 --flash-attn off --cache-type-k f16 --cache-type-v f16 --cache-ram 0 --no-cache-idle-slots --no-context-shift --spec-type none --slots --slot-save-path runs/deepinfer-slots
```

Se quiser testar CUDA, use a configuração de offload já comprovada para esse GGUF/VRAM e atualize a metadata. Mantenha-a idêntica nos dois braços. Não aumente o contexto/VRAM só para alcançar 96K. Preserve a margem de RAM exigida pelas instruções do lab e interrompa o processo de benchmark se a máquina entrar em pressão de memória. Nada aqui deve tomar o slot de uma sessão ativa de agente.

Em outro terminal, gere metadata real (hash do tokenizer pode ser o do GGUF inteiro quando ele é o container que incorpora o tokenizer; registrar artefatos externos separadamente, se usados):

```powershell
New-Item -ItemType Directory -Force runs | Out-Null
$meta = Get-Content experiments/deepinfer/metadata.example.json -Raw | ConvertFrom-Json
$meta.runtime_commit = (git -C $LlamaSource rev-parse HEAD).Trim()
$meta.runtime_binary_sha256 = (Get-FileHash -LiteralPath $Server -Algorithm SHA256).Hash.ToLowerInvariant()
$meta.model_sha256 = (Get-FileHash -LiteralPath $Model -Algorithm SHA256).Hash.ToLowerInvariant()
$meta.tokenizer_sha256 = $meta.model_sha256
$meta.quantization = 'PREENCHER_QUANTIZACAO_REAL_DO_GGUF'
$meta.hardware.cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$meta.hardware.ram_gib = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
$meta | ConvertTo-Json -Depth 4 | Set-Content runs/deepinfer-metadata.json -Encoding utf8
```

Preencha quantização, GPU real e quaisquer flags modificadas antes da execução; o exemplo original contém placeholders e é deliberadamente inválido. Metadata é declaração do operador, não atestado automático do host. O harness confirma slots/contexto por `/props`, não todos os demais campos.

## Executar o A/B

```powershell
python experiments/deepinfer/prefix_bench.py --probe --out runs/deepinfer-probe
python experiments/deepinfer/prefix_bench.py --exclusive-server --metadata runs/deepinfer-metadata.json --out runs/deepinfer-ab --warmups 1 --repetitions 5 --lines 512 --n-predict 32
```

Para o ensaio opcional de reidratação (novo diretório de saída):

```powershell
python experiments/deepinfer/prefix_bench.py --exclusive-server --metadata runs/deepinfer-metadata.json --out runs/deepinfer-restore --warmups 1 --repetitions 5 --lines 512 --n-predict 32 --snapshot
```

Servidor e experimento em Linux/WSL/ARM: os mesmos comandos Python funcionam via `python3`. Configure o **servidor local dessa máquina** com os mesmos flags aplicáveis; em OCI CPU use `--n-gpu-layers 0` e threads adequadas às OCPUs realmente disponíveis. Não reaproveite a metadata Windows. Não é necessário abrir portas, SSH ou expor serviços externos; o harness aceita apenas endereços IP literais de loopback HTTP, sem redirects/proxies.

## Dados e limites

`report.json` contém identidade/configuração, resumo e comparações; `trials.jsonl` é anexado e fechado após cada observação, com prime, continuação, cache, métricas individuais e falhas de condição. Diretório de saída preexistente gera erro; nada é sobrescrito. Erros HTTP/protocolo geram exit 2 e relatório com etapa/tipo da falha, sem corpo de erro, URL ou caminhos pessoais. Não retomar anexando ao mesmo diretório: uma nova execução é outro experimento.

Só streams com evento final, métricas de cache e orçamento de geração iguais são aceitos. O baseline e as variantes recebem exatamente os mesmos token IDs. A tokenização do setup não entra no TTFT; SSE conta primeiro token, inclusive especial/reasoning, e não primeiro texto exibido pelo frontend. A geração ignora EOS e é limitada por n_predict para controlar o trabalho; isso não é uma avaliação semântica de resposta final. A comparação registra divergência de outputs em vez de presumir determinismo entre formas de batch.

Snapshot faz save/erase/restore **no mesmo processo servidor**. Um arquivo com nome aleatório fica no `--slot-save-path`; reutilizado entre repetições, nunca publicado. Ao terminar, encerre somente o servidor dedicado e remova apenas os arquivos `ncma-prefix-*.bin` criados nesse diretório experimental. Não apague caches/estado de outros serviços. O harness não tem autorização HTTP de deleção de arquivo e não tenta contorná-la. RAM/VRAM máximas ficam null até existir coleta real do processo servidor.

Veja a [metodologia](../../research/deepinfer/BENCHMARKS.md) antes de interpretar ratios; tempos de prime e restore podem eliminar um aparente ganho de continuação. Primeiro caracterize 16K; para contexto longo aumente o fixture, confira tokens reais e ajuste capacidade sem mudar os braços entre si.

## Revalidar fontes externas (sem executar código upstream)

Usar diretórios temporários **fora da NCMA**. Exemplo Bash, com git já instalado:

```sh
AUDIT_ROOT=$(mktemp -d)
git clone --no-checkout https://github.com/deepseek-ai/DeepInfer.git "$AUDIT_ROOT/DeepInfer"
git -C "$AUDIT_ROOT/DeepInfer" checkout --detach 553741557a57df44a46fb3ab72b6aafeaf945337
git -C "$AUDIT_ROOT/DeepInfer" submodule update --init --depth 1 vendor/DeepGEMM vendor/FlashMLA vendor/DeepEP vendor/DeepSelect
git clone --no-checkout https://github.com/ggml-org/llama.cpp.git "$AUDIT_ROOT/llama.cpp"
git -C "$AUDIT_ROOT/llama.cpp" checkout --detach ddf48f85c933c1f438212a02eb21e7b001d2d37d
git clone --no-checkout https://github.com/deepseek-ai/deepseek-recipe.git "$AUDIT_ROOT/recipe"
git -C "$AUDIT_ROOT/recipe" checkout --detach 935817c66f5d6e64838f419692545f06787e485f
python experiments/deepinfer/verify_sources.py --deepinfer "$AUDIT_ROOT/DeepInfer" --llama "$AUDIT_ROOT/llama.cpp" --recipe "$AUDIT_ROOT/recipe" --out runs/deepinfer-source-verification.json
```

Este comando confere blobs fixados no Git, mesmo se o working tree tiver sido editado. Não executa builds, imports, hooks de inferência ou testes upstream. O lock também identifica licenças e links permanentes. Não copie árvores externas para o repositório NCMA.

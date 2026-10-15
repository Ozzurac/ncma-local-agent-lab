# GPT-OSS 20B MXFP4 - reasoning effort medium versus high at 32K

Framework V1 unchanged. Model GGML-org MXFP4. llama.cpp b11588, OpenAI Agents SDK 0.20.0.

| Experiment | Context | Output cap | Real file reads | Submitted sources | Independent tests |
|---|---:|---:|---:|---:|---|
| medium | 32768 | 8192 | 3/3 | 2 | 11/11 PASS |
| high matched | 32768 | 8192 | 3/3 | 0 | Not run, no patch |
| high expanded | 32768 | 12288 | 3/3 | 0 | Not run, no patch |

Both high runs verified reasoning: high in rendered llama.cpp /apply-template prompt. No medium header in either render.

## Grounded generation data

High 8K: server generated exactly 8192 tokens in the failed completion, generation time 126352 ms.
High 12K: server generated exactly 12288 tokens in the failed completion, generation time 187024 ms.
Both returned ModelBehaviorError with finish_reason length and no valid final text/tool call at the failed turn.

Minimum RAM free: medium 8.379 GiB; high 8K 8.033 GiB; high 12K 8.505 GiB.
No agent-authored high patch existed for independent execution.

## Evidence paths

- Medium stage: bench/gptoss-g2/stage-logs/mx-nested_config-b713e92f-458.json
- Medium verified patch: bench/gptoss-g2/verified_runs/mx-nested_config-b713e92f-458-review2.json
- High matched: bench/gptoss-g2/stage-logs/mx-nested_config-032f7670-107.json
- High expanded: bench/gptoss-g2/stage-logs/mx-nested_config-ad821c8a-8cc.json
- High template proofs: bench/gptoss-g2/effort32/high-template-20261014-181640.json and high-template-20261014-182025.json
- Server stderr timing logs: logs/g2nested32-high*-mx-nested_config-*-llama-stderr.log

## Interpretation and limits

The paired 8K run changes the effort setting while holding model/fixture/framework/context and output cap fixed. The 12K follow-up is a separate diagnostic, not the same comparison.
This result does not prove high inferior on all tasks, only that it failed to produce verifiable code on this task under tested constraints.
32K context was allocated, not actually filled. Memory remained safe.

Decision: retain medium as the operational candidate at 32K. Do not promote high without evidence of patch completion and passing tests.

Integrity: 10/10 original fixture files unchanged; frozen V1 hashes match; no llama-server processes remaining.

# NCMA Local Agent Lab - Round 1 verified

Checked: 2026-10-13 17:28:45 UTC

Environment: RTX 5070 12 GB, Ryzen 5800X3D, 32 GB RAM, llama.cpp b11588 CUDA 13.4, Windows.
All tests were sequential, isolated in <LOCAL_LAB_ROOT>, with each server bound to 127.0.0.1 and unloaded after its run.

| Model | Agent loop | Inference seconds | Load seconds | VRAM ready MiB | Free RAM ready GiB |
|---|---|---:|---:|---:|---:|
| GPT-OSS 20B MXFP4 | PASS (6/6 tests) | 5 | 15 | 10597 | 8.79 |
| GLM-4.7-Flash Q5_K_M | PASS (6/6 tests) | 52.53 | 29 | 10568 | 7.14 |
| Qwen3.6-35B-A3B IQ4_XS | PASS (6/6 tests) | 37.21 | 28 | 10436 | 7.55 |
| Devstral Small 2 Q4_K_M | PASS (6/6 tests) | 46.74 | 13 | 10453 | 4.24 |

Task: inspect real src/order_totals.py using read_file; correct duplicated discount by apply_patch; request and execute unittest; report results. Exactly 2 failing baseline tests; all 6 passing after edit.

Interpretation: 4/4 models passed this small synthetic agent loop. Latency rankings DO NOT establish relative correctness on large real-world programming workloads.
Memory numbers are snapshots of system-wide RAM/VRAM, not peak per-process measurements.
Corpus, tool contracts, input context, runtime and 4096-token server context are pinned; GPT-OSS used medium reasoning effort, other models used their default reasoning settings, so reasoning budgets were not identical.

Detailed JSON receipts:
- GPT-OSS 20B MXFP4: <LOCAL_LAB_ROOT>\bench\agent_loop_runs\ncma_loop__1g1wrmi\result.json
- GLM-4.7-Flash Q5_K_M: <LOCAL_LAB_ROOT>\bench\agent_loop_runs\ncma_loop_pv778ala\result.json
- Qwen3.6-35B-A3B IQ4_XS: <LOCAL_LAB_ROOT>\bench\agent_loop_runs\ncma_loop__s62hony\result.json
- Devstral Small 2 Q4_K_M: <LOCAL_LAB_ROOT>\bench\agent_loop_runs\ncma_loop_wkiulv1w\result.json

Not yet evaluated: complex refactors, multi-file changes, security prompts, long contexts, recovery loops, statistical repeatability, multi-turn context retention under load.

Safety: no Jarvis workspace changes, no scripts invoked outside the local disposable source sandbox, no public inference service, no unnecessary app termination.

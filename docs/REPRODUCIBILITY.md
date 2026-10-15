# Reproduction and provenance

Original Windows host: Ryzen 7 5800X3D, NVIDIA RTX 5070 12 GB, ~64 GiB usable DDR4. Reference runtime: llama.cpp b11588 CUDA, GPT-OSS 20B MXFP4 GGUF, loopback Chat Completions endpoint, single slot, Jinja, Flash Attention and 98,304-token configured context.

## Offline tests, no network and no LLM

```bash
python -m unittest discover -s tests -v
```

Synthetic oracle is published for transparency, but was not supplied during original inference. Its SHA-256 is recorded with the original corpus, checkpoint and final answer. Original dataset remains byte-exact.

Regenerate into ignored `experiments/g3/generated` without overwriting public evidence:

```bash
python experiments/g3/generate_case.py --events 176
```

## Live run

1. Run a verified-compatible local Chat Completions server.
2. Confirm that its template **actually applies** per-request high versus medium reasoning.
3. Launch `scripts/run-g4h.ps1` (PowerShell 7 recommended). It sets a scoped output directory `runs/g4h` and never downloads or launches model weights.
4. Pause/resume deliberately using `-Resume`. The checkpoint is an atomic JSON snapshot; protect host filesystem permissions.
5. Compare produced results using offline reference tests. Changing model, tokenizer, build, hardware or prompt template may change outcomes.

## Published evidence

The dataset comprises 760 NODE, 563 PATCH and 240 TEAM records, 12 cases and noisy EVENT/NOTE records. Final correctness was checked independently against the synthetic oracle: 12/12 incident records, including full paths and team seals.

The published G4H has 22 JSON round reports, a compact checkpoint, final results and an independent audit. Raw model reasoning, GPU binary bundles, caches and raw machine logs are excluded.

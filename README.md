# NCMA Local Agent Lab

**Local LLMs, durable checkpoints, modular retrieval, bounded inference and independently validated agent decisions.**

This repository preserves the reproducible October 2026 experiments with **GPT-OSS 20B MXFP4**, a **12 GB NVIDIA RTX 5070** and **64 GB DDR4**. The project evolved from single-call prompting into a modular, resumable agent runtime.

## Results at a glance

| Experiment | Configuration | Independently observed result |
|---|---|---|
| G2 coding task | 32K context, medium | 11/11 unit tests PASS |
| G2 coding task | 32K, high | 8K and 12K output exhausted, no final patch |
| G3 route audit | 96K window, high | 77,103 input tokens + 16,384 output; **no final answer** |
| **G4H route audit** | **96K window configured; focused retrieval; high draft + medium finalizer** | **12/12 incidents, 60/60 fields correct** |

G4H accepted **78 verified graph hops** across **22 checkpoint rounds and 44 model calls**. It rejected 28 proposed steps without losing prior validated progress. A new Python process recovered the checkpoint and continued successfully.

**Important distinction:** G4H did **not** process 96K of input in one inference. It used much smaller, targeted evidence retrieval from a corpus previously tested in the monolithic G3 run. These results demonstrate the hybrid *agent runtime*, not independent high-only model reasoning or broad real-world model accuracy.

## Architecture

```text
Task
  |  Modular KB + selective source retrieval
  v
High-effort draft (bounded, untrusted)
  |  Compact preliminary output
  v
Medium-effort JSON finalizer
  |  Model candidate next hops
  v
Independent source validator
  +-- REJECT: keep last verified checkpoint
  +-- ACCEPT: commit hop with source evidence
  |
Atomic JSON checkpoint
  |
Restart / continue / finish
  |
Independent end-to-end synthetic oracle
```

The model does **not** execute shell commands in G4H. This application is **not an operating-system sandbox**.

## Quick start: offline (no GPU or model needed)

Python 3.12+ using only the standard library:

```bash
python -m unittest discover -s tests -v
```

Tests verify the real synthetic G3 corpus checksum, the 12-case result against the oracle, each routing transition, published checkpoints and reports. To regenerate the dataset into a separate ignored directory:

```bash
python experiments/g3/generate_case.py --events 176
```

## Live model run

Start your own verified-compatible OpenAI Chat Completions server on `127.0.0.1:18991`, then on PowerShell:

```powershell
./scripts/run-g4h.ps1
# After a checkpointed pause:
./scripts/run-g4h.ps1 -Resume
```

The runner never installs models, starts services, or executes model-authored code. Live G4H requires a backend that honors `chat_template_kwargs.reasoning_effort` as high and medium; compatibility should be confirmed, not assumed.

## Project map

- [Portable Python coordinator](src/ncma_lab): Source indexing, strict graph validator, checkpoint persistence, bounded high/medium inference.
- [G3 synthetic corpus and oracle](benchmarks/g3): 96K-window failure evidence and deterministic fixture.
- [G4H final results, 22 rounds and checkpoint](benchmarks/g4h/evidence): Independent 12/12, 60/60 validation.
- [G2 coding benchmarks](benchmarks/g2): Fixtures, tests, results, negative evidence.
- [Agent Skills](skills) and [modular knowledge base](knowledge): Targeted reference modules.
- [Historical SDK and test scripts](experiments): Some scripts are for investigation, not release entrypoints.
- [Architecture](docs/ARCHITECTURE.md), [reproduction](docs/REPRODUCIBILITY.md), [results](docs/RESULTS.md), [backend contracts](docs/BACKENDS.md).

The Unsloth Desktop, Codex and Claude runtimes are **future backend or harness integrations**. Their compatibility with G4H has **not** been proven in this repo. Tool ownership belongs to exactly one harness at a time.

This is an explicit, sanitized publication: no model weights, GGUF, credentials, host binaries, private runtime caches or raw machine logs. The synthetic oracle is published to reproduce the evaluation but was not available to the model during the original experiment.

See the [original source provenance](docs/PROVENANCE.md) and [canonical Git-object manifest](PUBLICATION_MANIFEST.json) for reproducible publication integrity.

License: MIT.

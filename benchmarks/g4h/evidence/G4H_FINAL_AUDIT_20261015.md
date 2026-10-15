# G4H independent verification | 2026-10-15

**PASS: 12/12 synthetic incidents and 60/60 exact fields** matched the independent oracle after final inference.

| Metric | Observed |
|---|---:|
| Configured context | 98,304 tokens |
| Successful request topology | Selective per-hop retrieval (NOT full 96K input) |
| Reasoning modes | HIGH draft + MEDIUM finalizer |
| Python checkpoint rounds | 22 |
| Model calls | 44 |
| Accepted, source-verified hops | 78 |
| Rejected candidates | 28 |
| HIGH generated tokens, cumulative | 18,700 |
| MEDIUM generated tokens, cumulative | 32,529 |
| Combined model-call execution time | 1,531.6 s |
| Minimum observed system RAM free | 39.049 GiB |
| llama-server processes after test | 0 |

## What worked

The test used deterministic source retrieval, per-hop evidence checks, atomic checkpoints, a fresh Python process to resume, and an independently sealed synthetic oracle. The model had no access to the oracle during the original run. All recorded full paths, terminal services, team identifiers and seals matched.

## What was NOT proved

- HIGH-only reasoning had already failed in the monolithic G3 trial.
- G4H did not consume 96K of input per request. The server merely reserved a 96K window.
- This is one synthetic workload; not a general model benchmark.
- No model-authored code was executed and no OS sandbox was tested.

Machine-readable details are in the adjacent audit JSON, checkpoint, final results and individual round records.

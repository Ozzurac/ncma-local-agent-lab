# Experiment chronology and evidence

| Gate | Setup | Finding |
|---|---|---|
| G2 medium | 32,768 context; 8,192 output cap | Independently executed 11/11 unit tests PASS |
| G2 low | Same fixture and cap | Submitted malformed replacement files; syntax rejected before tests |
| G2 high | 8,192 / 12,288 output caps | No final actionable patch |
| G3 monolith | 98,304 configured; 77,103 prompt tokens; high | 16,384 generated, `finish_reason=length`, **zero final text** |
| G4H hybrid | 98,304 configured; focused evidence; high draft + medium final | 12/12 incidents and 60/60 fields matched independent oracle |

G3 prefill: 162.4 seconds (~475 input tokens/s); generation: 474.7 seconds (~34.5 tokens/s). Total: 93,487 tokens across prompt and completion. The model consumed only part of installed RAM, but output finalization failed.

G4H: 22 rounds, 44 calls, 78 accepted hops, 28 rejected candidates. Generated **18,700 high-draft tokens** and **32,529 medium-finalizer tokens**. Approximate accumulated model-call time: **1,531.6 seconds**, excluding host overhead. One round produced no final JSON; its invalid output was rejected and the run recovered.

The result belongs to the *hybrid system* and one synthetic deterministic fixture. It does not demonstrate high-only success, general ranking, or a 96K input per G4H call.

Evidence: [G2](../benchmarks/g2/reports), [G3](../benchmarks/g3/reports), [G4H audit](../benchmarks/g4h/evidence/G4H_FINAL_AUDIT_20261015.md), [individual rounds](../benchmarks/g4h/evidence/rounds).

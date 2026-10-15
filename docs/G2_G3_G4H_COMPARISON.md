# G2 → G3 → G4H | What changed, what was measured

A comparison of three **different experimental gates** on the October 2026 GPT-OSS 20B MXFP4 local stack. The coding checks in G2 are not statistically comparable to the route-audit oracle in G3/G4H. These are engineering observations, not a model leaderboard.

## At a glance

| Criterion | G2: coding and repair | G3: monolithic route audit | G4H: checkpointed route audit |
|---|---|---|---|
| Task | Small Python coding fixtures and a separate iterative-repair fixture | 12-incident synthetic graph-audit corpus | **Same** 12-incident synthetic graph-audit corpus as G3 |
| Context configured | 32,768 tokens for the effort comparison; 16K for a distinct iterative repair | 98,304 tokens | 98,304 tokens reserved; **focused retrieval per call** |
| Reasoning route | LOW / MEDIUM / HIGH comparison | HIGH only | HIGH draft, then MEDIUM JSON finalizer |
| Model work | Code proposal and fixed independent tests | One long input and one long generation | Bounded next-hop proposals across checkpoint rounds |
| Positive result | MEDIUM: **11/11 tests** in the 32K comparison; separately, iterative repair **10/10** | No final JSON; **0/12 cases returned** | **12/12 cases, 60/60 fields** matched independent oracle |
| Negative evidence | LOW: two syntax rejections. HIGH: output budgets 8,192 and 12,288 exhausted without a final patch | 77,103 input + 16,384 completion tokens; finish_reason=length, final text **0 bytes** | **28 invalid candidates rejected** without losing accepted progress |
| Completion / progression | Fix accepted only after deterministic unit tests | Could not finish the task | 22 rounds, 44 model calls; 78 accepted source-verified hops |
| Independent check | AST/static check and fixed unit test suites | No final answer to score; failure recorded | Hop-by-hop source validator **and** end-of-run independent oracle |
| Main finding | Structured outputs and tests matter more than raw reasoning setting | Reserving 96K context does not guarantee completion | Source-controlled decomposition and resumability recovered the **synthetic** task |

## Historical measurements

| Measurement | G2 effort32 | G3 | G4H |
|---|---:|---:|---:|
| Verified work | MEDIUM 11/11 tests | 0/12 returned cases | 12/12 cases; 60/60 exact fields |
| Prompt tokens in the documented run | Not a shared measurement across five trials | **77,103** | Focused per-hop retrieval, not a single 96K prompt |
| Completion tokens | LOW/HIGH caps: 8,192; HIGH retest: 12,288 | **16,384** | **18,700 HIGH + 32,529 MEDIUM**, accumulated |
| Time | Not comparable across distinct G2 trials | **637.18 s** | **1,531.6 s** accumulated model-call time; host overhead excluded |
| Validated transitions | Not a graph traversal | None completed | **78** |
| Rejected candidate transitions | Not a graph traversal | Not measured | **28** |

The G4H numbers mean **the full system solved the published synthetic fixture**, not that the HIGH model suddenly became better at unaided end-to-end reasoning. G4H never submitted the full G3 prompt to every inference.

## Engineering progression

1. **G2: trusted evaluation boundary.** Coding proposals could be accepted or rejected by static review and independent tests. LOW and HIGH failures were kept, not filtered out.
2. **G3: context is not completion.** A large context allocation allowed input ingestion but HIGH-only generation consumed its output budget before producing an answer.
3. **G4H: verified work units.** Index and retrieve only the current authoritative graph rows, ask for one step, validate it deterministically, persist accepted progress, and recover after interruption.

Do not combine the G2 coding pass fraction with G4H incident accuracy, compare wall time as if the workload were identical, or describe G4H as a 96K single-inference success.

## Source evidence

- [G2 LOW / MEDIUM / HIGH 32K](../benchmarks/g2/reports/EFFORT_32K_COMPARISON_20261014.md)
- [G2 independently validated iterative repair](../benchmarks/g2/reports/G2_MXFP4_ITERATIVE_AUDIT_20261014.md)
- [G3 negative result](../benchmarks/g3/reports/G3_96K_HIGH_AUDIT_20261015.md)
- [G4H final independent audit](../benchmarks/g4h/evidence/G4H_FINAL_AUDIT_20261015.md)
- [G4H round records](../benchmarks/g4h/evidence/rounds)
- [Sequence and source ownership](G4H_SEQUENCE.md)

The positive and negative outcomes are published as engineering evidence, not a general-purpose certification of agent autonomy.

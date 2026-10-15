# G4H | Verified-hop sequence and recovery boundary

The following describes the **implemented** G4H execution in [g4_hybrid.py](../src/ncma_lab/g4_hybrid.py) and [g4_checkpoint.py](../src/ncma_lab/g4_checkpoint.py). It is not a proposal for an autonomous tool-use agent.

## Runtime sequence

~~~mermaid
sequenceDiagram
    participant Operator
    participant Coordinator
    participant Corpus
    participant Model
    participant Validator
    participant Checkpoint

    Operator->>Coordinator: Start or resume run
    Coordinator->>Corpus: Verify SHA and index synthetic records
    Corpus-->>Coordinator: NODE, PATCH, TEAM, CASE and untrusted rows
    Coordinator->>Checkpoint: Initialize or verify saved state
    Checkpoint-->>Coordinator: Active cases and verified cursors

    loop Bounded rounds, up to six active cases per round
        Coordinator->>Corpus: Retrieve rows for current cursors
        Corpus-->>Coordinator: Focused NODE/PATCH/TEAM evidence
        Coordinator->>Model: HIGH draft with output budget
        Model-->>Coordinator: Preliminary untrusted draft
        Coordinator->>Model: MEDIUM finalizer with evidence and draft
        Model-->>Coordinator: Proposed JSON decisions
        Coordinator->>Validator: Check each proposed next hop
        Validator-->>Coordinator: Accept or reject each candidate
        alt Candidate matches authoritative records
            Coordinator->>Checkpoint: Commit verified path and evidence hash
        else Candidate malformed or unsupported
            Coordinator->>Checkpoint: Keep path, record error and feedback
        end
        Checkpoint-->>Coordinator: Atomic durable state
    end

    Coordinator-->>Operator: Final result or resumable pause
~~~

**Reading the diagram:** Corpus and validator are deterministic Python logic, not model tools. The HIGH stage proposes analysis; the MEDIUM stage proposes JSON. Neither output is an authority. Every candidate is validated against source rows before progress is accepted. When a proposal is invalid, accepted paths remain intact and the error becomes compact feedback for a later round.

The runtime stores a checkpoint with accepted paths, cursors, source-evidence digests and bounded error summaries. Persisting uses a temporary JSON file followed by atomic replacement. The checkpoint checksum detects accidental corruption, **not** hostile tampering or unauthorized modification.

## End-of-run verification is separate

~~~mermaid
sequenceDiagram
    participant Researcher
    participant Runtime
    participant Result
    participant OfflineTests
    participant PublishedOracle

    Researcher->>Runtime: Start reproducible synthetic run
    Runtime->>Result: Write final_results.json on completion
    Result-->>OfflineTests: Supply completed run artifact
    OfflineTests->>PublishedOracle: Load independent expected cases
    PublishedOracle-->>OfflineTests: Exact paths, terminals, teams and seals
    OfflineTests-->>Researcher: PASS or mismatch details
~~~

The oracle was withheld from the model during the original run. It is published **after the experiment** for transparency. The runtime does not call the oracle to choose a hop. For independent comparison of a fresh backend run, use [verify_backend_result.py](../scripts/verify_backend_result.py) after generating the final result.

## Boundaries grounded in implementation

- **Corpus authority:** NODE baseline, overridden by the highest numeric PATCH revision; TEAM supplies terminal seal.
- **Untrusted:** EVENT, NOTE, high draft, medium response and malformed JSON.
- **Hard stop:** no progression without successful independent hop validation; depth and total call limits apply.
- **Resume:** only from an existing, checksum-matching checkpoint bound to the expected corpus.
- **No shell tool:** model output is never executed as a command; this is not an OS sandbox.
- **Outcome:** the archived October 2026 G4H fixture completed 12/12 synthetic incidents, with 60/60 exact evaluated fields, 78 accepted hops, 28 rejected proposals, 22 rounds and 44 model calls. This is **fixture-specific**, not a general accuracy estimate.

See [comparison](G2_G3_G4H_COMPARISON.md), [backend portability](BACKEND_PORTABILITY.md) and [historical audit](../benchmarks/g4h/evidence/G4H_FINAL_AUDIT_20261015.md).

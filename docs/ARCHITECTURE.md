# Architecture: building durable agents around fallible model calls

The core innovation is to treat a **verified unit of progress** as the atomic work product, not a single giant answer.

**Invariants:**
1. Source records, knowledge documents, comments, logs and model thoughts are *data*, never higher-priority instructions.
2. A model draft is not validated work. The runtime chooses sources, cursors, budgets, tools and durable state.
3. Each proposed hop must match the highest numeric PATCH revision, or NODE baseline when no PATCH applies.
4. Invalid or incomplete model responses never overwrite the previously accepted path.
5. Checkpoint snapshots persist compact verified progress, not the full conversation or private reasoning stream.
6. Atomic JSON replacement prevents partial checkpoint writes. A SHA-256 checksum detects corruption, not malicious tampering.
7. Finishing requires a final artifact plus independent oracle verification. HTTP success alone proves nothing.

**G3** loaded 98,304 tokens of context, sent 77,103 prompt tokens and generated 16,384 tokens in high reasoning, but emitted no final answer.

**G4H** extracted only relevant source rows per current cursor, ran a high-effort draft, ran a medium-effort finalizer, independently validated the proposed decisions and advanced a durable checkpoint. A failed round did not discard earlier verified work.

A 96K context was configured but **G4H was not a 96K single-call reasoning benchmark**.

Reusable pieces: deterministic generator, indexed retrieval, validation contract, checkpoint, compacted continuation and high/medium orchestration. Not implemented: OS-sandboxed code execution, general tool access, multimodal-any-to-any capability or a full Codex/Claude adapter.

See [Backend contract](BACKENDS.md) and [Safety policy](../SECURITY.md).

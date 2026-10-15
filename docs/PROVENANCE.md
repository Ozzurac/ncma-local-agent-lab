# Provenance and public export policy

Publication date: 2026-10-15.

The source paths below are **relative to the original offline laboratory**, not public machine locations.
Files with modified paths or redacted host references are in the public repository as portable or historical derivatives.
Model weights, CUDA binaries, model caches, raw runtime logs, private tool connectors and credentials were **never copied** into the public export.

## Original evidence digests

| Original offline source | SHA-256 |
|---|---|
|bench/gptoss-g3-96k/task_corpus.txt | 824F516C6916E62ABBA573DF352F0145B66DC81765D8760B07093F389BAC2591 |
|bench/gptoss-g3-96k/generate_case.py | 9C5D086F4944F97F36F18AAA0CA91EA840C3B4BDDD058ECA318A23E760F302F2 |
|bench/gptoss-g3-96k/continuation-g4/g4_checkpoint.py | DAA0E084C7CCBCC48DBB3BFF34B7562DF82EE7A843698F5E115131FF281933AB |
|bench/gptoss-g3-96k/continuation-g4-hybrid/g4_hybrid.py | E84A6AD21DF975BBDCFD92A4277E8B1FE3EDFAD6CB71EBF195242E1D44608A9E |
|bench/gptoss-g3-96k/continuation-g4-hybrid/final_results.json | 9B62CD5D77EEA91B1423FF3D8FFAD5336808EB4E43D78FE53702B8D22AD78148 |
|bench/gptoss-g3-96k/continuation-g4-hybrid/G4H_FINAL_AUDIT_20261015.json | 721C3F4E46C8DE947BC8087637AB7B91DCEB8EE67A5FEB9387C95A3ED6D8B853 |

## Important hash semantics

- The G3 corpus saved on Windows contains CRLF line endings and has its own byte-for-byte SHA-256.
- The original G3 generator manifest hashed the semantic LF text before saving. The published generator now writes CRLF bytes explicitly on all platforms; this does not change the historical fixture or oracle.
- Ported G4/G4H Python source files have different hashes from their original machine-bound scripts. The published 12-case answer, 22 round artifacts, corpus, and oracle preserve their substantive original evidence.
- The independent oracle was sealed outside the model input during the historical G4H run; it is now published solely for auditability.
- The configured 96K model context is not the token count of each G4H inference. G4H used selective record retrieval.

## Verification

Execute: python -m unittest discover -s tests -v

The entire publication copy is scanned by scripts/scan_publication.py before Git creation. No private real-data benchmark was published.

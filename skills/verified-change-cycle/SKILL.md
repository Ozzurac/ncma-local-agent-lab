---
name: verified-change-cycle
description: Use whenever the user requests a code fix, a changed artifact, validation of a final patch, or a code-editing agent run in isolated NCMA fixtures.
---
# Verified change cycle

1. Confirm precisely authorized workspace and independent OS confinement BEFORE code execution.
2. Inspect source and test evidence; state the intended change.
3. Minimize patch scope, independent path checks and allowlists. Never accept a model-provided arbitrary command or unrestricted path.
4. If execution boundary unavailable, stop at a patch proposal or deterministic non-executing validation; mark NOT_PROVEN.
5. When execution IS authorized and confined, run the real test suite AFTER the final patch. Capture exit code and test count; if any later edit occurs, run again.
6. Ground the final report in independently collected test and integrity evidence. Never declare PASS from a plausible-looking answer or a tool exit code alone.

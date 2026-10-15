# NCMA GPT-OSS 20B MXFP4 - G2 Iterative Repair Audit

**Status: PASS_FIXTURE_ONLY**
Date: 2026-10-14

## Grounded results

- Original 10 trusted tests: 2 pass, 7 fail, 1 error.
- First agent proposal: code 10/10 PASS, but required KB reading skipped; protocol FAIL.
- Second independent proposal: protocol PASS (fixed policy + Skill + indexed KB + 3 real file reads + 2 staged files), but code 9/10 tests.
- Independent test failure: after retry, last_error remained "network" rather than None.
- The model read its own previous sources and the real test failure, revised dispatch.py only.
- Final independently executed suite: **10/10 PASS, exit code 0**.
- ledger.py SHA256 unchanged between second proposal and revision.
- Framework V1 unchanged; hashes of runner, adapter, helper verified.
- Original fixtures remain unchanged (10/10 integrity proof).

## Tools and containment

- OpenAI Agents SDK on llama.cpp 16K, medium reasoning, RTX 5070 12GB, 32GB system RAM.
- Permanent instructions: AGENTS.md, specialised idempotency Skill, indexed local KB.
- Agent tools: controlled read_file and submit_patch for allowlisted staging files; no agent shell.
- Independent local gate: scripts/gptoss-g2-fixed-gate.py (restricted Python AST and fixed unittest command).
- This is NOT an OS-isolated sandbox. Tests ran on Windows after structural/static review; do not execute arbitrary agent code with this approach.

## Evidence

- JSON audit: bench/gptoss-g2/G2_MXFP4_ITERATIVE_AUDIT_20261014.json
- Final test report:
<LOCAL_LAB_ROOT>\bench\gptoss-g2\verified_runs\mx-workflow_retry-fix-d41e1cad-9a5.json
- Final test log:
<LOCAL_LAB_ROOT>\bench\gptoss-g2\verified_runs\mx-workflow_retry-fix-d41e1cad-9a5.tests.log
- Final revised code:
<LOCAL_LAB_ROOT>\bench\gptoss-g2\verified_runs\mx-workflow_retry-fix-d41e1cad-9a5
- Final dispatch SHA256:
4007732545251360FCE6611507769AFDC814BA126798D20F1DAD10CA72302DB7
- Final ledger SHA256:
F7B1C252CC36462E974EE67BEBAB8734A79809A9C700F109449B14D0E6186985
- SDK evidence: bench/gptoss-g2/stage-logs/mx-workflow_retry-*.jsonl
- Test runner: scripts/gptoss-g2-fixed-gate.py

## Not proven

- Generic software-engineering autonomy, network or production code changes.
- Nested_config and Unsloth code-edit gates.
- Strong OS process isolation / adversarial code execution.
- Long-horizon multi-cycle memory/compaction in this G2 workflow.

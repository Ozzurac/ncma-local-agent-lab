# NCMA GPT-OSS 20B MXFP4: Low vs Medium vs High (32K)

Date: 2026-10-14
Framework V1 unchanged, Agents SDK, llama.cpp b11588.

| Mode | Output cap | Agent delivered patch | Independent gate |
|---|---:|---|---|
| medium | 8192 | yes | 11/11 PASS |
| low | 8192 | yes | REJECTED_SYNTAX |
| low | 8192 | yes | REJECTED_SYNTAX |
| high | 8192 | no | OUTPUT_EXHAUSTED |
| high | 12288 | no | OUTPUT_EXHAUSTED |

## Findings

- MEDIUM completed the coding task and the independently run 11/11 tests.
- LOW generated patches in both attempts, but both were rejected before test execution due to invalid Python syntax.
- LOW source files included literal diff + prefixes and End Patch markers; first settings.py also contained malformed text.
- AST-only diagnostic after removing diff markers made both sources from the SECOND low run syntactically valid. No unit tests were run on these modified sources.
- HIGH exhausted 8192 and 12288 output tokens respectively without a complete actionable tool call.
- Four low/high template probes confirmed the intended reasoning setting in rendered Harmony headers.
- Note: low raw proof files retain a mislabeled boolean field renderedTemplateHasHigh; the promptHeader unmistakably says Reasoning: low.
- Memory minimum remained above 8 GiB free in all agent runs.
- All original fixtures were unchanged:
CASE=workflow_retry EXPECTED=5 UNCHANGED=5 MISSING=0 CHANGED=0
CASE=nested_config EXPECTED=5 UNCHANGED=5 MISSING=0 CHANGED=0
UNCHANGED_TOTAL=10 RESULT=PASS
- Active llama-server processes:
0

## Decision

Keep medium + 32768 context + 8192 max output as provisional baseline for this fixture. Low needs structured full-file submission checks or safe patch-tool format. High needs reasoning-budget/tool-call diagnostics before trying larger output caps. No claim of global ranking from five runs.

## Evidence

- Structured report:
<LOCAL_LAB_ROOT>\bench\gptoss-g2\effort32\EFFORT_32K_COMPARISON_20261014.json
- Syntax-only diagnostic:
<LOCAL_LAB_ROOT>\bench\gptoss-g2\effort32\LOW_FORMAT_DIAG_20261014.json
- Medium independently executed tests:
<LOCAL_LAB_ROOT>\bench\gptoss-g2\verified_runs\mx-nested_config-b713e92f-458-review2.tests.log
- Per-trial stage reports:
<LOCAL_LAB_ROOT>\bench\gptoss-g2\stage-logs
- Harmony template proof files:
<LOCAL_LAB_ROOT>\bench\gptoss-g2\effort32

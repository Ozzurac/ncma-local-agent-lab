# Reproducing G4H with another inference backend

This is a **controlled compatibility experiment** for a local, OpenAI Chat Completions-like backend. It does not assert parity with Unsloth Desktop, Ollama, Codex, Claude Code or a remote provider. The only reference execution in this repository used GPT-OSS 20B MXFP4 on a compatible llama.cpp server.

## 0. Contract and safety boundaries

Read [BACKENDS.md](BACKENDS.md) first. The Python coordinator sends non-streaming JSON POST requests to a complete **/v1/chat/completions** URL. Requests include:

~~~json
{
  "model": "MODEL_ALIAS",
  "messages": [
    {"role": "system", "content": "Instruction"},
    {"role": "user", "content": "Serialized focused evidence"}
  ],
  "chat_template_kwargs": {"reasoning_effort": "high"},
  "temperature": 0,
  "seed": 967215,
  "max_tokens": 850,
  "stream": false
}
~~~

A second request uses **medium** effort and a separate final-output budget. The runner reads the first entry of **choices**, **message.content**, optional **message.reasoning_content**, **finish_reason** and **usage**. The HIGH response can supply a compact non-authoritative excerpt from content or reasoning_content; the MEDIUM response must produce parseable JSON decisions.

**Compatibility is more than HTTP 200.** Prove that the server applies the per-request HIGH/MEDIUM template change, accepts seed/temperature and budget semantics, and returns those response fields. A server that silently ignores reasoning_effort **does not reproduce** the original intervention. A server exposing only Responses API, proprietary SDK calls or a tool-executing agent requires a separately reviewed adapter.

Keep the endpoint on **127.0.0.1**. The Python client has no authentication-header support. The PowerShell wrapper can allow a remote URL with an opt-in flag, but that does **not** implement authentication or make the endpoint secure. Do not put a public or authenticated-remote endpoint into this runner without a reviewed transport adapter.

## 1. Clone and verify evidence offline first

Python 3.12+ is sufficient for the evidence checks; **no GPU or model download** is needed.

~~~powershell
git clone https://github.com/Ozzurac/ncma-local-agent-lab.git
Set-Location ncma-local-agent-lab
python -m unittest discover -s tests -v
python scripts/scan_publication.py
python -m compileall -q src experiments/g3
~~~

The tests check the published corpus checksum, 12-case synthetic fixture, source authority, round artifacts, and manifest. These are checks of the **published reference**, not a new backend run.

## 2. Preflight the backend independently

Start a compatible model server **yourself** on loopback. Confirm that the served model alias, tokenizer, chat template and max context are actually the ones intended for the trial.

~~~powershell
# Adjust port to the local server. This is only an HTTP reachability / model-list check.
Invoke-RestMethod -Uri 'http://127.0.0.1:18991/v1/models' -Method Get
~~~

Do **not** treat a successful /v1/models reply as proof of reasoning-effort support. Inspect the server's rendered prompt or documented template trace for separate HIGH and MEDIUM test requests. G4H uses **chat_template_kwargs.reasoning_effort**, which many superficially compatible servers do not interpret. If that proof is unavailable, record the run as **UNVERIFIED_BACKEND_SEMANTICS**, not as a reference-equivalent experiment.

The original host used llama.cpp b11588, RTX 5070 12 GB, and roughly 64 GiB system RAM. Other backends and devices may use different memory and token budgets. Never present a new backend run as an identical hardware comparison without recording the full conditions.

## 3. Run in a new isolated output directory

Work from the checkout root in PowerShell. Change the **model alias** to the actual name returned by your server. The unique run directory prevents overwriting earlier evidence.

~~~powershell
$env:PYTHONPATH = (Resolve-Path './src').Path
$env:NCMA_MODEL_API = 'http://127.0.0.1:18991/v1/chat/completions'
$env:NCMA_MODEL_ALIAS = 'YOUR_LOCAL_MODEL_ID'
$env:NCMA_RUN_DIR = (Join-Path (Get-Location) 'runs/backend-trial-01')

# Optional, bounded generation caps (defaults shown).
$env:NCMA_HIGH_OUTPUT_CAP = '850'
$env:NCMA_FINAL_OUTPUT_CAP = '3100'

# Local corpus/checkpoint prerequisites only. Does NOT contact the model.
python -m ncma_lab.g4_hybrid --check-only

# Requires the compatible model server to be running.
python -m ncma_lab.g4_hybrid --max-rounds 18
~~~

Exit **0** indicates that the runtime assembled a complete final artifact; exit **10** is a deliberate checkpointed pause; exit **3** indicates an error. A complete runtime artifact is **not** equivalent to independent correctness. Run the verifier in step 4.

For a paused run with the same model, template, endpoint and run directory:

~~~powershell
python -m ncma_lab.g4_hybrid --resume --max-rounds 18
~~~

An existing checkpoint intentionally blocks a non-resume run. **Never delete or edit the checkpoint to force a PASS.** Keep the run's evidence directory private until reviewed for secrets, system paths and private server logs.

On the **first backend trial**, do not change the model, template, reasoning settings or corpus between pauses and resumes. The checkpoint checksum detects corruption but does not securely attest to all runtime or backend parameters.

## 4. Verify the newly produced answer

After a completed run, compare **that run's** final result against the **published post-experiment** synthetic oracle:

~~~powershell
python scripts/verify_backend_result.py --result runs/backend-trial-01/final_results.json
~~~

The verifier returns a nonzero exit code on missing files, malformed results, missing/extra/duplicate cases or incorrect fields. It checks 12 case records and 60 fields, including each full graph path. It does **not** verify that a new model independently produced the work under the claimed HIGH/MEDIUM conditions. Keep backend template proof and run logs separate.

If the run pauses without a final result, report **INCOMPLETE**, not 0/12 or PASS. If it completes but differs from the oracle, report the mismatch and preserve negative evidence.

## 5. Capture a comparison record before publishing

Record the following, without publishing private machine paths or endpoint credentials:

| Field | Required evidence |
|---|---|
| Backend / build | Product, exact version/build, model identifier and quantization |
| Environment | CPU, GPU, VRAM/RAM, OS, runtime process count |
| Prompt semantics | HIGH and MEDIUM rendered-template evidence, plus tokenizer |
| Limits | Context configured, per-request output caps, seed, temperature |
| Result | COMPLETED / PAUSED / ERROR / UNVERIFIED_BACKEND_SEMANTICS |
| Verification | 12-case and 60-field exact match, or the observed mismatches |
| Cost | Wall-clock time, model-call time and token usage when exposed |
| Safety | Loopback bind, no model-authored shell execution, log-sanitization review |

**Not implemented:** transparent compatibility with remote provider SDKs, automatic backend model installation, automatic restart of inference servers, or OS sandboxing. The Codex and Claude runtimes are agent harnesses, not drop-in inference backends for this script. Unsloth Desktop is a candidate to test, not a proven replacement.

See [sequence](G4H_SEQUENCE.md), [gate comparison](G2_G3_G4H_COMPARISON.md) and [reproducibility](REPRODUCIBILITY.md).

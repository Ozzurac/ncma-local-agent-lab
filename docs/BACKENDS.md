# Model backend contract

G4H uses OpenAI-compatible `/v1/chat/completions` requests. Defaults: loopback `http://127.0.0.1:18991/v1/chat/completions` and model alias `ncma-gptoss`.

| Environment option | Purpose |
|---|---|
| `NCMA_MODEL_API` | Complete HTTP(S) chat-completions URL |
| `NCMA_MODEL_ALIAS` | Model name advertised by the server |
| `NCMA_RUN_DIR` | Directory for new checkpoint and result |
| `NCMA_HIGH_OUTPUT_CAP` | HIGH draft completion budget; default 850 |
| `NCMA_FINAL_OUTPUT_CAP` | MEDIUM final completion budget; default 3100 |

Per-call reasoning levels use `chat_template_kwargs.reasoning_effort` (`high` then `medium`). A server calling itself OpenAI-compatible does **not** guarantee support for this extension or for tools/Responses API. Validate template rendering on each backend.

**Unsloth Desktop** is a promising GGUF inference/training environment with an OpenAI-compatible endpoint, but no G4H end-to-end compatibility test is claimed. **Codex and Claude Code** are agent/harness systems; connecting them is a separate adapter and tool semantics problem. Avoid multiple independent executors handling the same model tool call.

High draft content is deliberately not trusted. Every medium-finalized decision must be checked against retrieved authoritative NODE/PATCH/TEAM rows. No model-generated code runs in this benchmark.

The 96K context is a server allocation and not the amount of input used by every call.


For step-by-step compatibility checks and isolated new-run scoring, see [BACKEND_PORTABILITY.md](BACKEND_PORTABILITY.md).

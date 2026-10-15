# NCMA local GPT-OSS runtime

Two compared variants: GPT-OSS 20B native MXFP4 GGUF and Unsloth GPT-OSS 20B UD-Q4_K_XL GGUF. Both previously completed read-only diagnosis and ephemeral memory recall through OpenAI Agents SDK 0.20.0 using llama.cpp b11588 and OpenAI-compatible Chat Completions. Both produced empty responses with Qwen Code SDK 0.1.19 / Qwen Code CLI 0.25.1. Codex CLI requires the Responses protocol; a server advertising OpenAI compatibility is not proof that full Codex tool semantics work.

Keep llama-server bound to 127.0.0.1:18991, context 16,384, one slot, reasoning medium. Available physical RAM floor 2.75 GiB; never degrade this limit to force an inference run.

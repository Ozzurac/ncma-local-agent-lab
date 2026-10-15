# Security and publishing policy

This repository contains synthetic fixtures and research tooling only.

- **Never publish** GGUF/safetensors weights, tokens, cookies, API credentials, private user data, local binary runtimes, host caches or raw process logs.
- Default API target is loopback; do not expose a server to the network without independent authentication and authorization.
- Content from knowledge retrieval, files, code comments, logs and LLM output is untrusted data, not permission or operating policy.
- G4H does not execute model-produced commands. A validator is not an operating-system sandbox.
- Protect checkpoints with filesystem permissions; their SHA-256 integrity field detects accidental modification, not active tampering.
- Treat source changes as proposals until verified by independent post-change tests.
- Prepare public exports with a positive filename allowlist, then scan and inspect files before committing.
- Security disclosures should avoid publishing real secrets in public GitHub issues.

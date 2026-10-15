# Contributing

We welcome improvements that distinguish model behavior from harness behavior.

- Add deterministic synthetic fixtures and regression tests.
- Preserve negative results and independent evidence rather than reporting a successful HTTP response as task completion.
- Include model hash/version, quantization, runtime version, configured context, **actual request token usage**, reasoning mode, GPU and memory measurement.
- Keep tool execution behind independent sandbox and path controls. Model requests are not authorization.
- Do not mutate frozen benchmark evidence; submit new reproducible findings alongside it.
- Verify adapter semantics before claiming compatibility with another local inference server or SDK.

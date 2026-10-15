---
name: idempotency-retry-analysis
description: Use for event dispatch, delivery retries, duplicate suppression, payload identity, delivery attempts, and durable status tracking.
---
# Idempotency and retries

Investigate how an event key and payload are validated, persisted, sent, acknowledged and retried. A completed event should not be delivered twice. A retry should preserve original identity and not erase diagnostic state. Distinguish pending/failed/done and explicit attempt count. Consult the knowledge index for the idempotency module before recommending state changes. Do not infer that external delivery is atomic.

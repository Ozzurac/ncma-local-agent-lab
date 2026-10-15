# Reliable event delivery principles

Status transitions should be explicit (pending, failed, done) and independent of the external side effect. For an event key, verify that later payloads match its registered payload. Track delivery attempts and last failure without silently resetting the history on retries. Distinguish deduplication after acknowledged completion from uncertainty after timeouts: exactly-once external side effects require cooperation from the recipient or a durable idempotency key.

Source category: general software engineering reference. NOT the answer key to any fixture.

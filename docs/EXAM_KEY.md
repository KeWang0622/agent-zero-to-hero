# Exam answer key

These are minimum points a good answer should cover. Examples and wording may vary. See [the syllabus](../SYLLABUS.md).

1. The stateless Messages lab resends application-held history. A managed continuation service can retain provider conversation state; the application still needs its own task identity, permissions, and recovery records.
2. Pairing preserves which observation answers which request. Cutting a call from its results creates an invalid or semantically incomplete history. Preserve the whole exchange or use the provider's supported compaction contract.
3. A schema checks representation. It does not prove user authorization, resource ownership, factual correctness, or safe effects. The executor checks those independently.
4. Use `call_id`, not the item's separate `id`. Reasoning and other provider-native state may be necessary for correct continuation; use supported chaining or preserve required items.
5. Final termination/completion state, complete parseable arguments, tool identity/schema, permission, and budget. In this update, the whole batch is validated before dispatch.
6. The body can remain in future requests. Caching may discount eligible repeated input; it does not imply zero future cost.
7. Better measured task success, latency, or total cost on representative cases, with adequate evidence returned to the parent. Include every child's usage and coordination failures.
8. The lab is a small `2024-11-05` stdio example. The current stable `2026-07-28` revision changes lifecycle and metadata/discovery semantics. Changing the version string alone does not migrate it.
9. Fixtures test deterministic harness contracts. Task evaluations assess whether a configuration accomplishes representative work. Passing fixtures cannot establish live-model quality.
10. At-least-one success rewards trying multiple times; all-attempt success measures consistency. State exactly how many trials and tasks were run and how the metric was computed.
11. The service may have committed before the receipt was lost. Record an unknown outcome, reconcile or use receiver-enforced idempotency, and avoid inventing success or failure.
12. The outbox atomically records local state and pending work. Delivery and external effects can still repeat; the receiver needs deduplication or the caller needs reconciliation.

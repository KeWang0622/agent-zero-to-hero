# October 2026 update

**Source review: 2026-10-26.** Baseline commit: `179d6b38f137a46e33328958a014e60cb6038b2a` (2026-06-02).

## what this revision delivers

The original twenty-lesson progression remains. A new executable chapter 17b demonstrates OpenAI Responses with bounded arithmetic and offline protocol fixtures. Three reading labs add evaluation, permissions, and durable execution, including local examples and assessable homework.

The new field guide and source ledger explain current provider state, context engineering, tool discovery, skill/protocol boundaries, and optional runtime comparisons. The MCP byte-level lab remains pinned to its original 2024-11-05 revision, with a separate current-specification comparison. Anthropic raw HTTP versus SDK API-version defaults are documented rather than silently conflated.

## corrections to the existing course

- Replace product-clone and six-line completeness claims with an explicit harness learning objective.
- Distinguish model context, transcript, provider sessions, external knowledge, and durable task state.
- Correct same-role Messages behavior, caching prefix order and the course model's threshold.
- Remove unsubstantiated fixed-cost and savings guarantees; explain repeated skill-input billing.
- Separate public commentary from internal reasoning and remove speculative training claims.
- Label the old provider adapters' metadata/termination limitations.
- Fix attribution errors and replace missing exam/wishlist references with useful documents.
- Publish an implementation map so standalone Skills, MCP, subagents, and multi-provider lessons are not mistaken for integrated capstone features.

## bounded code repairs

`agent.py` now saves full new-format compaction snapshots and replays them. Legacy count-only records remain readable but cannot recover summaries that were never recorded.

Both the capstone and chapter 16 buffer streamed tool arguments until the final stop reason is known. The entire batch is checked for valid JSON/object arguments before tools execute. Truncation and unsupported/invalid termination states are reported explicitly instead of being mistaken for successful completion.

The new Responses example uses `call_id`, retains server continuation, resends instructions, checks HTTP/completion state, and limits requests and tool calls. Its arithmetic executor validates inputs without `eval`.

## validation and remaining scope

The baseline had 42 passing tests. This revision has **78 passing offline tests**, including 36 additional cases; Ruff passes. See [VALIDATION.md](VALIDATION.md) for environment and exact checks. There was no paid model run or current remote MCP/A2A interop test.

This remains a teaching harness. It does not add a sandbox, transactional external writes, current MCP wire implementation, complete provider adapters, or an integrated live-model evaluation service. Those boundaries are documented in the lessons and [WISHLIST.md](WISHLIST.md). Existing media assets are retained and may show historical slogans.

Read [the field guide](FIELD_GUIDE_2026.md) for the conceptual update, [the syllabus](../SYLLABUS.md) for the learning sequence, and [SOURCES.md](SOURCES.md) for evidence.

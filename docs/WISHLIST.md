# Remaining engineering work

This edition fixes concrete teaching failures while keeping the harness inspectable. The following are **not implemented guarantees**. They are useful focused contributions, not a promise that the CLI is production-ready.

| Priority | Gap | Useful acceptance test |
|---|---|---|
| High | Pending tools after a crash are not reconciled | Crash between two tool effects; recovery distinguishes completed, pending, and unknown |
| High | Filesystem/shell access is not confined | Symlink escape and unauthorized network effect are rejected by an enforced boundary |
| High | Original calculator lessons use restricted `eval`, which is not a sandbox | A bounded arithmetic parser rejects attribute access, calls, and resource-exhausting expressions |
| High | Bash and some tool handlers lose structured failure/exit information | Nonzero exit and empty stdout remain distinguishable from successful empty output |
| Medium | Original provider adapters flatten native state and incompletely map termination | Round-trip fixtures preserve metadata, call identity, blocking, and truncation |
| Medium | Legacy MCP client has limited lifecycle, deadlines, negotiation, and cleanup | Unsupported revision/timeout/failed init produces an explicit error and no orphan process |
| Medium | Token accounting and compaction triggering are heuristic; cost state is in-process | Repeated short turns check context budget; restart does not claim a fresh billing total is lifetime cost |
| Medium | Skill frontmatter parser supports only a small subset | Multiline YAML, duplicate names, and invalid metadata have documented behavior |
| Medium | Standalone compaction demo does not share every capstone boundary check | Summarization never leaves an orphan tool result and preserves updated constraints |
| Optional | A current MCP implementation, Gemini Interactions lab, and live evaluation runner | Separate versioned examples with contract tests and opt-in credentials |

Do not implement all of this at once. Pick one misconception, demonstrate a failure, and add the smallest correct lesson. The [validation record](VALIDATION.md) distinguishes what was actually checked from these future extensions.

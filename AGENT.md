# agent-zero-to-hero

This file is loaded by the educational `agent.py` when working in this repository. It describes the project; executor permissions still apply independently.

## purpose and navigation

A source-first course in building and assessing an agent harness. The foundation has 20 paired Python/Markdown lessons. Chapter 17b adds a Responses API lab. Chapters 18–20 are conceptual reading labs with inline local examples, not matching Python modules.

- `chapters/`: small examples and learning pages.
- `agent.py`: integrates core Anthropic/local-tool/stream/session/compaction primitives. It does not integrate every separate lesson.
- `skills/`, `mcp_servers/`: inspectable teaching examples; see their trust/version boundaries.
- `tests/`: offline pytest fixtures and local subprocess tests.
- `docs/`: current field guide, compatibility notes, sources, limitations, validation.
- `SYLLABUS.md`: seven-week core plus optional reliability extension.

## conventions

Keep one concept per lesson. Preserve provider-specific semantics. Explain why in comments. State whether an example is runnable, conceptual, historical, or live-tested. Do not claim mocked tests measure model quality. Keep external writes and paid model calls opt-in for teaching scripts.

See `CONTRIBUTING.md` before changing course structure.

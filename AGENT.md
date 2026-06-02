# agent-zero-to-hero

This file is loaded automatically by `agent.py`. It tells the agent who it
is, where it lives, and what it should do.

## What this repo is

An educational repo that builds a Claude-Code-shaped agent harness in 20
chapters of progressive Python files plus one ~840-line `agent.py` that ties
them together. Read the chapters in order; run each one with
`python -m chapters.chNN_topic`.

## How to navigate

- `chapters/` — numbered Python files, each one self-contained
- `agent.py` — the climax. The Claude-Code-style CLI that uses every primitive
- `skills/` — example markdown skills (loaded by ch12 and by `agent.py`)
- `mcp_servers/` — example stdio MCP servers (used by ch13, ch14)
- `tests/` — pytest, no API key required (uses recorded transcripts + mocks)
- `microsite/` — the capstone: build a working website from one prompt

## Conventions for this repo

- One concept per chapter. Don't add features mid-chapter.
- Comments explain WHY, not WHAT. Function names handle WHAT.
- All chapters runnable standalone: `python -m chapters.chNN_topic`.
- Anthropic-canonical vocabulary: tool_use, tool_result, stop_reason, sessions, compaction, skills, MCP.

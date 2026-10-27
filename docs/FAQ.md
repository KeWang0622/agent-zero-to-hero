# Common questions

## is this a framework?

No. It is a source-first textbook: inspect a protocol, run a small example, break an invariant, and explain the failure. Frameworks and managed runtimes can supply orchestration and operations; knowing the primitives helps you evaluate them.

## why keep Anthropic in the foundation chapters?

The course uses one concrete vocabulary consistently: `messages`, `tool_use`, `tool_result`, and `stop_reason`. That is a teaching choice, not a ranking of providers. Chapter 17 compares historical wire formats; chapter 17b adds a current OpenAI Responses example. See [ADAPTING.md](ADAPTING.md) for the compatibility boundary.

## what works without an API key?

Installation checks and `python -m pytest tests/` run offline with mocks and a real local MCP subprocess. Model-backed chapter demos and the capstone need credentials and may incur charges. Offline tests do not certify model behavior, current endpoint availability, or model pricing.

## is agent.py production-ready?

It is an educational CLI. It can read local files and invoke a shell with your process's access. Its Write/Edit/Bash confirmation is not a sandbox, and read tools can expose sensitive data. Inspect the code and use a disposable workspace. [Chapter 19](../chapters/ch19_permissions.md) explains the engineering boundary.

The update persists new compaction snapshots and stops invalid model turns before executing tools. It still lacks transactional tool execution, durable approval state, replay-safe external writes, complete metadata-preserving provider adapters, and comprehensive budgets. [Chapter 20](../chapters/ch20_durable_execution.md) develops those designs.

## does the six-line loop explain an entire commercial coding agent?

It explains a useful control-flow skeleton. It does not reproduce a commercial product's planner, permissions, tool scheduler, state management, evaluation system, or deployment infrastructure. Study actual public implementations such as [Codex CLI](https://github.com/openai/codex) and [Aider](https://github.com/Aider-AI/aider), reading their own licenses and documentation.

## how long and how much will it take?

Use the original seven-week schedule for the foundation, then the optional reliability extension. Time and API spend depend on how many exercises you run, the chosen model, retries, and output size. No fixed cost or completion time is guaranteed. Start offline and measure one live task before budgeting a class.

## are the new chapters all executable?

Chapter 17b has Python and offline tests. Chapters 18–20 are design lessons with concrete exercises and acceptance criteria; they do not claim to add production subsystems to `agent.py`. The README distinguishes these two tracks.

## which parts can age?

Model IDs, prices, protocol versions, feature availability, and API examples. The evidence ledger records the date checked and links to primary sources. A linked page may change after this edition. Keep protocol fixtures pinned and rerun a live smoke test when changing a provider or model.

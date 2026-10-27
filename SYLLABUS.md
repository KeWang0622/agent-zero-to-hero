# Syllabus — from agent primitives to reliable outcomes

**October 2026 edition.** Prerequisite: Python 3.10+ and comfort with functions, dictionaries, loops, and exceptions. The core remains seven weeks; add two optional reliability weeks. Time estimates are planning suggestions, not measured completion guarantees.

## learning outcomes

By the end, a learner can trace a tool call across the API boundary; preserve conversation state; identify incomplete output; explain context, transcript, task state, and receipts; assess tool permissions; and evaluate an artifact independently of the model's final claim.

Use the [README chapter map](README.md) for links to each lesson. Foundation chapters and 17b have Python companions. Chapters 18–20 are reading labs containing local demonstrations and design exercises.

## seven-week core

| Week | Lessons | Lab | Acceptance evidence |
|---|---|---|---|
| 1 — the loop | 00–05 | Build a calculator loop and inject a truncated response fixture | Correct answer on the normal fixture; no tool execution on truncation |
| 2 — tools and instructions | 06–08 | Add two independent read tools and a structured error | Correlate every result with its call; distinguish failure from empty success |
| 3 — context and cost | 08b, 08c, 10 | Compare a stable prefix and an invalidated prefix; test a small compaction threshold | Usage categories and retained constraints; no assumed savings ratio |
| 4 — state and delegation | 09, 11 | Reload a saved conversation; compare one agent with a focused child | Reload assertions; total parent+child usage and evidence quality |
| 5 — extension interfaces | 12–14 | Add a skill and a local MCP tool to the pinned lab | Valid skill metadata; wire trace with exact protocol version |
| 6 — streaming and adapters | 15–17b | Feed partial JSON and implement Responses continuation | No dispatch before validation; matching call IDs and preserved state |
| 7 — capstone | `agent.py`, `microsite/` | Repair a local documentation example or build a small artifact | Reviewed diff, artifact checks, configuration and limitations report |

Each week: read the Markdown, inspect the Python, run offline tests, then opt into live calls if useful. Do not start by running the entire speedrun against an unreviewed model configuration.

## reliability extension

| Week | Reading | Lab | Acceptance evidence |
|---|---|---|---|
| 8 — quality and authority | [18 evaluation](chapters/ch18_evaluation.md), [19 permissions](chapters/ch19_permissions.md) | Build a small outcome dataset; inject an instruction into an untrusted file | Grader checks resulting artifacts; unauthorized effect is rejected |
| 9 — recovery | [20 durable execution](chapters/ch20_durable_execution.md) | Crash after a fake service commits and before the caller saves its receipt | Stable operation ID, reconciliation, exactly one effect in the local fake |

These labs extend the course; their production subsystems are not already implemented in the CLI. Exercise-only code should stay small enough to inspect.

## final assessment

Choose a local task with a clear artifact outcome. Submit the request, allowed actions, starting fixture, final artifact/diff, checks, trace, model/configuration if used, and failure analysis. Include at least one negative case and one interrupted-execution case. A mock-only submission is acceptable if it explicitly makes no claims about live-model quality.

Suggested rubric:

- 35% correct observable outcome and meaningful evaluation.
- 25% correct protocol/state handling, including failure cases.
- 20% clear authorization and recovery boundaries.
- 20% explanation, evidence, reproducibility, and limitations.

No hidden bug is required for the assessment. A well-evidenced explanation of an existing limitation is a valid result.

## exam questions

1. In the Messages API lab, who supplies conversation history? How does that differ from provider-managed continuation?
2. Why must each tool result match a specific call? What happens if compaction splits that pair?
3. Why can valid structured output still request an unauthorized action?
4. In Responses, which identifier links `function_call_output` to the call, and why preserve more than visible text?
5. What must a streaming executor check before running a tool?
6. Why does loading a skill once not mean paying for it only once?
7. What evidence would justify adding a subagent?
8. What is the difference between the course's pinned MCP lab and the current specification?
9. How do mocked harness tests differ from task outcome evaluations?
10. Distinguish success at least once in repeated attempts from success consistently across attempts.
11. A remote write times out. Why is blindly retrying or recording failure unsafe?
12. What does a transactional outbox solve, and what does it leave unsolved?

A concise [answer key](docs/EXAM_KEY.md) is provided for self-review.

## instructor notes

Use fresh workspaces and synthetic data. Start with offline fixtures, budget live calls per task, and record the selected model and rates on the teaching date. The project does not promise a fixed dollar cost for a class. Original visual assets may contain historical counts and pricing slogans; use the current Markdown as the authority.

For optional reading, use [the field guide](docs/FIELD_GUIDE_2026.md) and [primary-source ledger](docs/SOURCES.md). Keep framework and hosted-runtime comparisons optional so students can still see the mechanisms they are learning.

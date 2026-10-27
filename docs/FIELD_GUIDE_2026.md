# Agent Engineering: the October 2026 Field Guide

**Checked 2026-10-26.** This guide connects the original course to current primary documentation. It separates observed API/protocol changes from our design recommendations. It is a dated reference, not a claim that every implementation below has been run live.

## what changed, and what still matters

The original course asks an excellent question: what happens between a model deciding to use a tool and the next model call? That remains worth learning. The next question is whether the entire system can finish the intended task, preserve its constraints, and recover without repeating an effect.

The course baseline reviewed here is commit `179d6b38f137a46e33328958a014e60cb6038b2a`, dated June 2, 2026. Some resources below predate that commit but fill missing material. Others document later changes. “Checked today” is not a publication date.

| Area | Observation from primary sources | What this edition does |
|---|---|---|
| OpenAI integration | Responses is the recommended new-project path; managed Agents API and application-hosted Agents SDK have distinct responsibilities | Adds a raw HTTP Responses lab; preserves the old adapter as a comparison |
| Gemini integration | Current docs present Interactions and explicit thought-state handling | Marks the old `generateContent` adapter's limitations and links migration guidance |
| MCP | Stable 2026-07-28 changes lifecycle semantics; the course pins 2024-11-05 | Keeps the historical byte-level lab and adds a version boundary document |
| Agent Skills | A portable format specification describes metadata and supporting resources | Links the standard and labels the tiny loader's parsing limits |
| Reliability | Engineering literature emphasizes outcomes, context management, and recovery | Adds three design lessons with locally executable demonstrations |

Sources: [OpenAI runtimes](https://developers.openai.com/api/docs/guides/agents), [Gemini Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview), [MCP stable release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28), [Agent Skills](https://agentskills.io/specification). Detailed status and dates are in [SOURCES.md](SOURCES.md).

One time-sensitive teaching choice matters: the OpenAI deprecations page lists the Assistants API shutdown date as August 26, 2026. It also schedules existing Evals to become read-only October 31 and the Evals dashboard/API and Agent Builder to shut down November 30, 2026. Those are product lifecycle notices, not a reason to stop evaluating agents. The new evaluation lesson teaches portable methods and local graders rather than making that service a course dependency. [Official deprecations](https://developers.openai.com/api/docs/deprecations).

## 1. decide where control belongs

Start with a deterministic workflow when the steps and branching rules are already known. Use a model to interpret an ambiguous request or select an action when that judgment is useful. Give the model a bounded loop when it must explore an uncertain environment. Add multiple agents only when independent work or separate context makes a measurable difference.

For a documentation update, a deterministic workflow can check links and render pages. A model can compare explanations and draft a revision. An agent can investigate a broken example whose cause is unknown. Independent reviewers can inspect sources or run isolated checks in parallel. None of those choices requires turning every function into an agent.

A useful architecture names five owners:

| Owner | Responsibility | Failure if omitted |
|---|---|---|
| Application | User intent, acceptance criteria, persistent job identity | Agent optimizes a plausible but wrong objective |
| Model integration | Provider-native messages/items, tool pairing, termination states | Lost reasoning state, invalid continuation, false completion |
| Executor | Argument checks, access policy, tool timeouts, effects | Valid JSON causes an unauthorized action |
| State/recovery layer | Checkpoints, operation identity, receipts, reconciliation | Restart repeats a successful external write |
| Evaluator | Outcome checks, representative tasks, regression comparisons | A polished answer hides an incorrect artifact |

This is a design decomposition for the course. A particular SDK or managed service may combine these owners. Read its contract to see which responsibilities still belong to your application. The [original effective-agents article](https://www.anthropic.com/research/building-effective-agents) provides useful workflow patterns; [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) provides one implementation reference for state.

## 2. stop using memory as one undifferentiated word

A conversation can be remembered in several places, with different lifetimes and authority:

| State | Example | Who owns correctness? |
|---|---|---|
| Active model context | Current prompt, tool definitions, selected history | Harness builds it; provider processes it |
| Conversation transcript | Original user, assistant, and tool events | Application or provider session store |
| Task state | Pending steps, acceptance criteria, approved destination | Application |
| Retrieved knowledge | Source documents, search results, database rows | Source system; retain provenance |
| Long-lived notes | User-approved preferences, project facts | Application, with scope and update policy |
| Operation receipts | Publication revision ID, completed tool result | Executor and external service |

The course's Messages API examples supply history explicitly. That is not evidence that every API is stateless or that a messages list is the only possible memory. The new Responses lab uses provider continuation, but still needs application state to survive its own process restarting.

Compaction is a lossy transformation of working context. Preserve goals, constraints, identifiers, decisions, evidence pointers, and unfinished work. Keep authoritative operation records outside the summary. Test a case where the last user turn changes a constraint: a compacted agent must honor the correction instead of reverting to an older summary.

Anthropic's [context engineering article](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) discusses retrieval, structured notes, compaction, and focused subagents. Provider compaction has its own state format and replay rules. OpenAI uses opaque compaction items; Claude's documented beta modes use their own blocks and signature requirements; see [Claude compaction](https://platform.claude.com/docs/en/build-with-claude/compaction) and [OpenAI compaction](https://developers.openai.com/api/docs/guides/compaction). The hand-written summary in chapter 10 remains an inspectable teaching mechanism.

## 3. design a tool contract before writing its prompt

A good tool contract makes both success and failure useful to its caller. For a local file-edit tool, specify the allowed root, expected old content or version, new content, maximum size, and a structured result. A response such as `{"ok": false, "kind": "version_conflict"}` is easier to recover from than a traceback pasted into a success-shaped string.

Treat these as separate checks:

1. **Shape:** can the arguments be parsed and validated?
2. **Meaning:** does the requested resource exist, and are units/ranges sensible?
3. **Authority:** does the user's request authorize this effect on this resource?
4. **Execution:** did the operation complete, fail, or leave an unknown outcome?
5. **Evidence:** what receipt or artifact proves the result?

Strict structured generation can help with the first check. It does not establish the others. A valid path can point to a secret; a valid recipient can be the wrong recipient. The executor, not a model-generated `safe` field, must make the decision.

Keep outputs bounded and useful: a summary with a stable artifact reference can be better than repeatedly injecting a megabyte of logs. Retain original evidence for verification. [Anthropic tool-design guidance](https://www.anthropic.com/research/writing-tools-for-agents) motivates testing tool names, descriptions, and result formats against actual tasks.

As tool catalogs grow, on-demand tool discovery can avoid injecting every schema. Programmatic tool calling can compose related calls and reduce intermediate results in a runtime. These are optional optimizations: apply them only after measuring the simpler baseline, and preserve per-tool authorization, budgets, and failure handling. [OpenAI tool search](https://developers.openai.com/api/docs/guides/tools-tool-search), [programmatic tool calling](https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling).

## 4. separate instructions, integration, and delegation

| Mechanism | Carries | Typical use | Does not automatically provide |
|---|---|---|---|
| Tool | An executable capability with an input/output contract | Read a file; query a service | Permission, correct arguments, recovery |
| Skill | A reusable procedure and optional resources | A style guide or review process | A sandbox or permission grant |
| MCP | A protocol for tool/context integration | Connect a client to a server | A complete runtime or trusted tool content |
| Local subagent | A delegated task with separate context | Independent investigation | Durable cross-service delivery |
| A2A | Interactions between independent agents | Discover a remote agent and track a task | A need for it in every local multi-agent app |

The original custom `read_skill` tool remains a useful demonstration of deferred loading. Its body remains in context until the harness changes that context. Reading once is not billing once. Scripts in a skill can have real effects; review and authorize them like other executable inputs.

For MCP, read [the version comparison](MCP_VERSIONS.md) before adapting the lab. A historical `initialize` exchange should not be presented as current protocol behavior merely because the acronym is the same. Protocol revision, transport, SDK version, and actual peer support are four different facts to record.

A2A belongs in optional reading when the project crosses agent-service boundaries. Its [specification](https://a2a-protocol.org/latest/specification/) and [MCP comparison](https://a2a-protocol.org/latest/topics/a2a-and-mcp/) describe different integration responsibilities. They are not competing names for spawning a local child function.

## 5. evaluate one complete task before adding more agents

Use a small fixed set of tasks drawn from the actual product. Each case should identify inputs, allowed actions, an observable target state, and a budget. Record the model/configuration and repeat runs when nondeterminism matters. Do not judge a file-edit task only by whether the final answer says “done.”

For this tutorial, a useful first task is: update a heading while preserving a code example. The grader reads the resulting file, checks the required heading, runs the example, and rejects edits outside the allowed set. That can be evaluated without a second model. Subjective prose quality can use a rubric and human review; model grading needs calibration.

Keep three forms of evidence separate:

- **Harness tests:** fixtures test parsing, state transitions, tool IDs, and failure paths.
- **Task evaluation:** live or recorded trials test whether a configuration accomplishes the intended work.
- **Operational evidence:** real deployments reveal latency tails, interrupted operations, cost, and failure recovery.

Chapter 18 develops the task/trial/grader distinction, repeated-trial metrics, and leakage precautions. [Anthropic's evals article](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) and the [SWE-bench evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/) provide primary references.

Then perform an ablation: run the same cases with a single agent, one focused reviewer, and a larger team. Measure success, elapsed time, total tokens across all children, and coordination failures. More agents can repeat work or create conflicting edits. A fresh context is valuable only if the handoff returns sufficient evidence. Anthropic's [March 2026 harness study](https://www.anthropic.com/research/harness-design-long-running-apps) is a useful reminder that scaffolding should be reevaluated as models improve.

## 6. make the hard failure a lesson

The most educational recovery case is not a dropped model request. It is an external write that succeeded before the receipt was saved. A retry may duplicate the effect, while refusing every retry may leave the job unfinished.

Teach explicit operation identity, a persisted intent, receiver-enforced deduplication when available, and an `unknown` state requiring reconciliation. A conversation log, an outbox, and a remote service transaction are different mechanisms. Chapter 20 provides a local SQLite example so students can inspect the guarantee without opening external accounts. [AWS safe retries](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) and [transactional outbox guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) explain the underlying distributed-systems problem.

The concrete repairs in this edition are intentionally smaller: new compaction snapshots replay, and invalid streamed tool inputs stop before any tool runs. They do not make arbitrary shell commands or external actions transactional.

## 7. an assessed capstone

Use a disposable local copy of a small documentation project. The task is to repair one stale code example and produce a cited migration note. Do not add publication until the local acceptance checks pass.

| Case | Expected outcome | Evidence |
|---|---|---|
| Ordinary update | Correct explanation and runnable example | Diff and execution result |
| Ambiguous model/API choice | Explicit supported configuration or clear uncertainty | Source URL and model/API declaration |
| Injected instruction in a source file | No unauthorized export or execution | Rejected action and unchanged scope |
| Truncated tool arguments | No tool executes | Dispatcher trace and test assertion |
| Crash after compaction | New-format snapshot restores the same working history | Reload assertion |
| Unknown external write, local fake | Reconcile or deduplicate instead of duplicate effect | Operation record and single receipt |

Require a brief report: task, configuration, outcome checks, failures, cost/latency if measured, and limitations. A task can be incomplete even when its answer is articulate. A correct result can have several valid tool sequences.

## maintain this as a living textbook

When updating again, preserve the old tested baseline, check official migration and deprecation pages, and review the claims most likely to age. Add a dated evidence entry and a focused regression fixture for each changed behavior. Do not replace every model ID with the newest alias and call that a migration.

Keep frameworks as optional implementation comparisons. [LangGraph](https://docs.langchain.com/oss/python/langgraph/persistence) emphasizes explicit graph state and checkpoints; current [Google ADK](https://adk.dev/2.0/) documentation describes a graph workflow runtime. Managed agent services can take over parts of the harness. The educational outcome is knowing which responsibilities move—and which still belong to your application.

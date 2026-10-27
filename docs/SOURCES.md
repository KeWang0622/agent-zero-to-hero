# Primary-source ledger

**Checked 2026-10-26 (America/Los_Angeles).** Sources were searched and opened, not cited solely from search snippets. This is a targeted cross-ecosystem survey, not an exhaustive census of the web. Living documentation can change after this date. “Published” dates below come from the source; “checked” dates describe this review. Tutorial recommendations are editorial judgments.

## APIs and provider state

| Source | Date / status | Supports |
|---|---|---|
| [OpenAI agent runtimes](https://developers.openai.com/api/docs/guides/agents) | Living docs, checked 2026-10-26 | Agents API, Agents SDK, and Responses have different state/orchestration ownership |
| [Responses migration](https://developers.openai.com/api/docs/guides/migrate-to-responses) | Living docs | Recommended new-project API; Chat Completions still supported |
| [Function calling](https://developers.openai.com/api/docs/guides/function-calling) | Living docs | Function-call/output items, call IDs, strict schemas, model-specific endpoint constraints |
| [Reasoning](https://developers.openai.com/api/docs/guides/reasoning) | Living docs | Preserve required reasoning state across tool turns |
| [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) | Living docs | Manual history and managed continuation patterns |
| [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data) | Living docs | Review storage mode before adapting the demonstration to private inputs |
| [OpenAI deprecations](https://developers.openai.com/api/docs/deprecations) | Evals/Agent Builder notice 2026-06-03; checked 2026-10-26 | Assistants shutdown 2026-08-26; Evals read-only scheduled 2026-10-31; Evals and Agent Builder shutdown scheduled 2026-11-30 |
| [Gemini Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview) | Living docs | Current interaction API model |
| [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling) | Living docs | Current tool exchange examples |
| [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking) | Living docs | Thought blocks/signatures and stateful/manual continuation differ |
| [Claude Messages](https://platform.claude.com/docs/en/api/messages/create) | Living docs | Stateless Messages history and same-role combination |
| [Claude API versioning](https://platform.claude.com/docs/en/api/versioning) / [migration](https://platform.claude.com/docs/en/api/migration-2026-10-21) | Version 2026-10-21; checked 2026-10-26 | SDK-major defaults differ from pinned raw HTTP; older version remains documented |
| [Claude caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) | Living docs | Prefix order, model thresholds, automatic/explicit modes |
| [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing) | Living docs | Cache multipliers; prices require rechecking |
| [Claude compaction](https://platform.claude.com/docs/en/build-with-claude/compaction) | Living docs; compaction modes documented as beta | Provider context-management options |
| [OpenAI compaction](https://developers.openai.com/api/docs/guides/compaction) | Living docs | Opaque compaction state and replay rules |
| [Tool search](https://developers.openai.com/api/docs/guides/tools-tool-search) | Living docs | Deferred tool discovery |
| [Programmatic tool calling](https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling) | Living docs | Runtime composition of eligible tools |
| [OpenAI Skills](https://developers.openai.com/api/docs/guides/tools-skills) | Living docs | Provider-specific integration of reusable procedures |

## Harness design and evaluation

| Source | Published / status | Supports |
|---|---|---|
| [Effective context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) | 2025-09-29 | Context selection, retrieval, compaction, notes, focused subagents |
| [Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) | 2025-11-26 | Progress artifacts and verification across sessions |
| [Demystifying evals](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) | 2026-01-09 | Task/trial/grader/outcome distinction and repeatability |
| [Harness design for long-running apps](https://www.anthropic.com/research/harness-design-long-running-apps) | 2026-03-24 | Reevaluate scaffolding through ablations as capability changes |
| [Scaling Managed Agents](https://www.anthropic.com/research/managed-agents) | 2026-04-08 | Context and session infrastructure have separate responsibilities |
| [Writing effective tools](https://www.anthropic.com/research/writing-tools-for-agents) | 2025-09-11 | Evaluate tool interfaces and token-efficient results |
| [SWE-bench evaluation](https://www.swebench.com/SWE-bench/guides/evaluation/) | Living project docs | Controlled environments and outcome checks |
| [tau-bench paper](https://arxiv.org/abs/2406.12045) | 2024-06-17 | Repeated-trial reliability and final state checks |
| [Eval awareness on BrowseComp](https://www.anthropic.com/research/eval-awareness-browsecomp) | 2026-03-06 | Retrieval can leak evaluation answers |

Vendor case studies are design evidence, not independent proof of a universal cost or quality improvement. This edition imports no leaderboard score or guaranteed savings multiplier.

## Standards and runtime comparisons

| Source | Version / status | Supports |
|---|---|---|
| [Agent Skills specification](https://agentskills.io/specification) | Living specification | Required metadata, directory layout, optional resources |
| [Skills client implementation](https://agentskills.io/client-implementation/adding-skills-support) | Living guide | Activation mechanisms, trust, parsing, lifecycle |
| [MCP release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28) | Stable, released 2026-07-28 | Current revision verified independently of a moving latest URL |
| [MCP versioning](https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning) | Versioned docs | Current versus draft/final status |
| [MCP changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog) | Stable revision | Lifecycle, discovery, metadata, and result changes |
| [MCP transports](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports) | Stable revision | stdio and Streamable HTTP boundaries |
| [MCP authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) | Stable revision | Remote auth and local credentials are different concerns |
| [A2A specification](https://a2a-protocol.org/latest/specification/) / [release v1.0.1](https://github.com/a2aproject/A2A/releases/tag/v1.0.1) | Release notes 2026-05-26; GitHub release 2026-05-28 | Independent-agent discovery/task interactions; optional comparison |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) / [Functional API](https://docs.langchain.com/oss/python/langgraph/functional-api) | Living docs | Checkpoints, stores, replay boundaries, side-effect handling |
| [Google ADK 2.0](https://adk.dev/2.0/) | Living docs | Current graph workflow runtime; no SDK compatibility run claimed |

## Permissions and durable effects

| Source | Status | Supports |
|---|---|---|
| [OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | LLM01:2025 | Indirect injection and limiting privilege |
| [MCP security guidance](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices) | Explicit historical 2025-11-25 reference | OAuth proxy confused-deputy example, not current protocol wire semantics |
| [Claude Code sandboxing](https://www.anthropic.com/research/claude-code-sandboxing) | 2025-10-20 | OS-enforced filesystem/network boundaries |
| [AWS safe retries](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) | Builders' Library | Receiver-enforced request identity |
| [AWS transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) | Living architecture guidance | Local atomicity does not eliminate duplicate delivery |
| [Temporal Activity definitions](https://docs.temporal.io/activity-definition) | Living docs | Completed-result replay versus retries when completion is unrecorded |

## Verification limits

The review used primary documents, published specifications, original research, repository source inspection, and offline tests. It did not execute paid model calls, benchmark current models, install every referenced framework, or test interoperability with current remote MCP/A2A services. See [VALIDATION.md](VALIDATION.md) for exact local evidence.

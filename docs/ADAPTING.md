# Adapting the harness across providers

**Checked 2026-10-26.** The existing chapter 17 demonstrates a deliberately small adapter. It is not a full compatibility layer for current reasoning, multimodal, or hosted-agent APIs.

## choose an API before choosing an adapter

| Path | State and tool exchange | Where to learn it |
|---|---|---|
| Anthropic Messages, original course | Application supplies messages; `tool_use` / `tool_result` content blocks | Chapters 00–16 |
| OpenAI Chat Completions, original adapter | `messages`, assistant `tool_calls`, tool-role replies | Chapter 17; compatibility exercise |
| OpenAI Responses | Typed output items; `function_call_output` linked by `call_id`; optional managed continuation | [New runnable chapter 17b](../chapters/ch17b_responses.md) |
| Gemini `generateContent`, original adapter | `model` content, `functionCall` / `functionResponse` parts | Chapter 17; inspect its limitations below |
| Gemini Interactions | Structured steps and interaction continuation | [Current official overview](https://ai.google.dev/gemini-api/docs/interactions-overview) |

OpenAI recommends Responses for new projects. Its managed Agents API, application-hosted Agents SDK, and low-level Responses API have different orchestration and state ownership. Our raw HTTP lesson teaches the last of these; it does not implement the managed harness. [OpenAI runtime guide](https://developers.openai.com/api/docs/guides/agents).

Gemini's current function-calling documentation uses Interactions. Its thinking guide explains stateful continuation and preservation of thought blocks for manual histories. The old adapter rebuilds parts from normalized text and calls, so it can lose metadata. Do not infer support for every new Gemini model from a passing fixture. [Function calling](https://ai.google.dev/gemini-api/docs/function-calling), [thinking](https://ai.google.dev/gemini-api/docs/thinking).

## pin the API version as well as the SDK

The raw Anthropic HTTP lessons explicitly send `anthropic-version: 2023-06-01`. That remains a documented compatibility option. Python SDK 2.x selects `2026-10-21` by default; the open-ended dependency range therefore does not guarantee the same API version as every raw HTTP lesson. Consult [versioning](https://platform.claude.com/docs/en/api/versioning) and the [October 2026 migration guide](https://platform.claude.com/docs/en/api/migration-2026-10-21) before upgrading.

The new API version removes sampling parameters and changes some document/citation input rules. This course's simple dict messages and positive `max_tokens` calls do not use those removed forms. The displayed reference version is not a promise about a request that omits its version header. The [validation record](VALIDATION.md) names the SDK tested offline; it is not a live compatibility certification.

## what the original adapter deliberately omits

`AgentMessage` keeps text, tool calls, and a small stop flag. It omits full provider output, usage, opaque reasoning state, safety details, and multimodal parts. The original Gemini code synthesizes call IDs from the tool name; repeated same-name calls need richer correlation. The original Anthropic conversion emits tool results as separate normalized messages; production code should preserve the provider's required tool-result grouping.

The old parsers also do not exhaustively distinguish truncation, blocking, empty candidates, and successful completion. Their HTTP paths parse JSON before raising status errors. The calculator uses `eval` with empty builtins, which is **not a security sandbox**. Use it only as an inspected teaching example; the new chapter 17b uses a bounded operation tool.

## build an adapter by preserving meaning

1. Keep the provider-native assistant payload alongside any normalized display text.
2. Preserve call IDs, ordering, reasoning metadata, and tool-result grouping.
3. Map every termination state explicitly; fail visibly on unknown states.
4. Check HTTP status before parsing a success response.
5. Validate arguments and authorization in the executor, independently of schema generation.
6. Run provider-specific fixtures, then an opt-in live smoke test using the selected model.

An adapter abstraction is useful only when it makes these differences visible enough to test. “Same loop” means the control-flow idea is shared; it does not mean every provider has interchangeable wire semantics.

## models and cost

The original demos retain historical model IDs so the teaching baseline is inspectable. Check availability before running them; passing offline tests proves no live availability. The new Responses demo requires `OPENAI_MODEL` explicitly. Model selection should follow your task's measured success, latency, and cost rather than a universal vendor ranking.

We removed the old cross-provider price table because its dated entries mixed models and rates. Record model ID, date, token categories, cache policy, and measured usage for each experiment. Check [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing), [OpenAI pricing](https://developers.openai.com/api/docs/pricing), and [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) when preparing a live run. A model alias and its price are not permanent course constants.

See [the evidence ledger](SOURCES.md) and [the 2026 field guide](FIELD_GUIDE_2026.md) for migration context.

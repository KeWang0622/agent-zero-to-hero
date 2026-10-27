# Chapter 17b — Preserve the Conversation, Not Just the Text 🐢

> A provider adapter can be syntactically correct and still discard state the model needs.

**Updated 2026-10-26.** Runnable companion: [ch17b_responses.py](ch17b_responses.py). This is a separate HTTP implementation, not an extra adapter silently added to chapter 17.

## the misconception

“OpenAI support means rename `messages` and parse `tool_calls`.” That describes the older Chat Completions example in chapter 17. Responses uses typed output items, including function calls and reasoning items. The original `AgentMessage` intentionally has no place for all of those fields.

The official migration guide recommends Responses for new projects while still supporting Chat Completions. The function-calling guide also documents model-specific endpoint requirements; changing only the model name is not a migration. [Migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses), [function calling](https://developers.openai.com/api/docs/guides/function-calling).

## trace one round trip

```text
application -> POST /v1/responses
  instructions + user input + arithmetic schema

model -> output[]
  reasoning item (when present)
  function_call { id: fc_..., call_id: call_..., arguments: JSON string }

application -> validate -> execute bounded arithmetic

application -> POST /v1/responses
  previous_response_id: resp_...
  instructions: resend application policy
  input: [{ type: function_call_output, call_id: call_..., output: JSON string }]

model -> message containing output_text
```

The item ID and `call_id` are different identifiers. A result answers the **call ID**. Parallel calls require a matching result for each call.

Our example uses server-managed continuation: `store=True` plus `previous_response_id`. That preserves earlier output, including provider reasoning state. We send instructions on each request. If you instead manage the full input yourself, preserve the required output items rather than flattening them into text; consult the reasoning guide for your storage mode. [Reasoning state](https://developers.openai.com/api/docs/guides/reasoning), [conversation state](https://developers.openai.com/api/docs/guides/conversation-state).

Server-managed history does not make earlier tokens free. It also does not make this application durable: the Python process still holds the continuation ID. For recovery, persist application progress separately; see [chapter 20](ch20_durable_execution.md).

## run without a key first

From the repository root, after installing the test extra:

```bash
python -m pytest tests/test_responses.py -q
```

The tests use `httpx.MockTransport`. They exercise a real request/response-shaped loop without network access. They verify continuation, two tool results in one batch, malformed arguments, refusal, incomplete responses, HTTP failure, and budgets. Fixtures demonstrate protocol handling; they do not measure a live model's intelligence or establish current account access.

For a paid live run, select a model your account can use with Responses and function calling:

```bash
export OPENAI_API_KEY='your-key'
export OPENAI_MODEL='your-supported-model-id'
python -m chapters.ch17b_responses
```

The arithmetic task should resolve to **491**. Wording and tool sequence may differ. The example explicitly stores response state with the provider; use synthetic inputs and review [data controls](https://developers.openai.com/api/docs/guides/your-data) before adapting it to private data. No live API run is claimed by this documentation update.

## why the executor stays boring

The only tool adds or multiplies two bounded finite numbers. It does not use Python `eval`. The schema is strict, but the executor still rejects unexpected keys, booleans masquerading as numbers, non-finite values, unknown operations, and unknown tools. A generation schema is not an authorization boundary.

The loop checks response completion **before** dispatch. A truncated response cannot become a tool execution just because it happens to contain a `function_call` item. Malformed arguments return a tool error; the model may repair them within the turn budget. HTTP errors surface to the caller instead of being mistaken for successful model output.

Eight requests and eight tool calls are ceilings, not a dollar guarantee. Each request also has a token cap and a network timeout. A production application needs a monetary budget, cancellation, accounting, and recovery as well.

## homework

1. Add a fixture with a reasoning item and two function calls. Assert that continuation uses the previous response ID and returns both call IDs, without reconstructing the earlier reasoning item.
2. Add a subtraction operation. Acceptance: an extra argument, infinity, and an unknown operation still return errors.
3. Make the model emit a tool call forever in a fixture. Acceptance: the harness stops at the configured budget and reports failure.
4. Explain why persisting `previous_response_id` alone cannot prove that an external payment succeeded.

## summary

Preserve the provider's conversation contract. Validate before execution. Count model requests and tool calls separately. Treat provider state, application state, and external side effects as different things.

Next: [chapter 18 — evaluation](ch18_evaluation.md).

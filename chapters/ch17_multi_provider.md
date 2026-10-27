# Chapter 17 — Same Loop, Three Wires 🐢

> **The agent loop is universal. The wire format is provider-specific. A 30-line adapter is the difference.**

## 🐢 GuiGui says

We've used Anthropic everywhere because its tool-use shape is the cleanest. But every primitive maps to OpenAI and Gemini. This is the chapter that proves the loop is provider-independent. After it, swap providers with a constructor argument.

## The 4 foot-guns

| | Anthropic | OpenAI | Gemini |
|---|---|---|---|
| Tool args type | parsed object | **JSON STRING** | parsed object |
| Tool stop reason | `"tool_use"` | `"tool_calls"` | **none — scan parts** |
| System prompt | top-level field | first message, `role: "system"` (`"developer"` on o-series / GPT-5+); Responses API uses top-level `instructions` | `system_instruction` |
| Assistant role string | `"assistant"` | `"assistant"` | **`"model"` (rejects `"assistant"`)** |

**Compatibility note (2026-10-26):** this chapter preserves the original Chat Completions and Gemini `generateContent` adapters for comparison. They are intentionally lossy teaching adapters, not complete support for all current models. For a new OpenAI implementation, continue to [chapter 17b — Responses](ch17b_responses.md). See [ADAPTING.md](../docs/ADAPTING.md) for current API choices and limitations.

## Show me the code

```python
@dataclass
class AgentMessage:
    role: str
    text: str = ""
    tool_calls: list = field(default_factory=list)
    stop: str = ""        # normalized: "end" | "tool_use" | "max_tokens"

class Provider(Protocol):
    def complete(self, messages, tools, system) -> AgentMessage: ...

# the loop is provider-agnostic
def run_agent(provider, system, prompt, tools, dispatch):
    messages = [AgentMessage("user", text=prompt)]
    for _ in range(10):
        resp = provider.complete(messages, tools, system)
        messages.append(resp)
        if resp.stop != "tool_use":
            return resp.text
        for tc in resp.tool_calls:
            messages.append(AgentMessage("tool",
                text=dispatch(tc.name, tc.args), tool_call_id=tc.id))
```

Three providers × ~30 lines each = ~100 LOC of adapter. The loop never changes.

## ⚠️ Watch out for

**OpenAI's JSON string args.** `tool_call.function.arguments` is a STRING. `json.loads` it before use. **Gemini tool detection.** In this `generateContent` example, inspect `parts` for `functionCall`; also handle non-success finish reasons and missing candidates. `finishReason` is not always `STOP`. Preserve the original content and required reasoning metadata when extending the adapter.

## ✅ Summary

- Loop is provider-independent.
- Three foot-guns to know (string args, missing stop reason, system placement).
- ~30 LOC per provider adapter.

## 📝 Homework

```bash
python -m chapters.ch17_multi_provider
```

1. Run against all 3 providers. Compare wall-clock + tokens for the same task.
2. Add a 4th provider (Mistral, DeepSeek, or Cohere). ~50 LOC.
3. **Build:** Make `agent.py` multi-provider via a `--provider` flag.

## 📚 References

- [docs/ADAPTING.md](../docs/ADAPTING.md) — porting guide with provider-specific gotchas (in this repo)
- [Anthropic vs OpenAI vs Gemini — tool use comparison](https://www.glukhov.org/post/2025/10/structured-output-comparison-popular-llm-providers/) — side-by-side
- [OpenAI — Migrate to the Responses API](https://platform.openai.com/docs/guides/migrate-to-responses) — recommended for new projects; Chat Completions remains supported
- [Gemini — Function calling docs](https://ai.google.dev/gemini-api/docs/function-calling) — official spec
- [LiteLLM](https://github.com/BerriAI/litellm) — production-grade multi-provider adapter (compare to ours)

## 🚀 Next

Continue to [chapter 17b](ch17b_responses.md), then the reliability lessons [18](ch18_evaluation.md), [19](ch19_permissions.md), and [20](ch20_durable_execution.md). For the original capstone, read [`agent.py`](../agent.py) — read it cover-to-cover. Then [`microsite/`](../microsite/) — use what you built.

# Chapter 08 — System Prompts 🐢

> **The system prompt is what the model IS. Messages are what it just DID. Tools are what it CAN do. Don't mix them up.**

## 🐢 GuiGui says

Beginners stuff instructions into the first user message. Works for one-shot. Fails for agents — instructions scroll off, prompt cache misses, persona drifts. Persistent instructions go in `system`.

## The idea

| Where | What goes here | Cacheable? |
|---|---|---|
| `system` | Persona, policies, AGENT.md | ✅ |
| `messages` | The conversation | Stable prefixes may be cached |
| `tools` | Capabilities + JSON Schema | ✅ |

## Show me the code

```python
SYSTEM = "You are a careful coding agent. Read files before editing them."

# basic
r = client.messages.create(
    model=M, system=SYSTEM,
    messages=msgs, tools=TOOLS, max_tokens=1024,
)

# explicit caching marker (requires enough eligible, reusable input)
system_cached = [{"type": "text", "text": SYSTEM,
                  "cache_control": {"type": "ephemeral"}}]
```

This illustrates the top-level system field used by the course. The short example prompt is below the caching threshold; a marker alone does not produce a hit. See [chapter 08c](ch08c_prompt_caching.md).

## ⚠️ Watch out for

**The persona drift.** Persona in the first user message gets compacted away by [ch10](ch10_compaction.md). The client-side compactor in this course leaves the separately supplied `system` unchanged. That is an application policy, not a universal lifetime guarantee.

## ✅ Summary

- `system` is persistent identity. Use it.
- Check eligibility and measured cache usage; savings depend on the workload.
- `system` survives compaction; user messages don't.

## 📝 Homework

```bash
python -m chapters.ch08_system_prompts
```

1. Same question, three system prompts. Compare voices.
2. Wrap `system` with `cache_control`. Predict whether this short prompt clears the model threshold, then inspect usage in an opt-in live run.
3. Find one place in `agent.py` where changing the system prompt would alter behavior.

## 📚 References

- [Anthropic — System prompts](https://docs.anthropic.com/en/docs/build-with-claude/system-prompts) — official guide
- [Anthropic — Prompt engineering overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) — the canonical prompt techniques
- [OpenAI — text generation guide](https://platform.openai.com/docs/guides/text-generation) — note the `developer` role replacing `system` for o-series / GPT-5+ models

## 🚀 Next

[Chapter 08b — The dollar ticker](ch08b_observability.md): what does each turn actually cost?

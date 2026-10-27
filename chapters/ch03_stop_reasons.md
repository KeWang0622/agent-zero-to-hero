# Chapter 03 — Stop Reasons 🐢

> **The loop is `while True`. The way OUT is `stop_reason`. This foundation lesson covers seven values in its original API scope. Handle unexpected values explicitly.**

## 🐢 GuiGui says

Most beginners write `while stop_reason == "tool_use": ...` and get bitten when `max_tokens` truncates a reply. The loop quietly exits with corrupt state. Don't be that person — handle every value.

> **Heads up:** one of the seven values is `tool_use`. We haven't introduced tools yet (that's [ch04](ch04_one_tool.md)). For this chapter, just know that `tool_use` is one of the values — we'll cover what it *means* in the next chapter.

## the foundation stop reasons

Provider features can add variants. Claude's current on-demand compaction beta, for example, documents `compaction`; it is outside this lesson and the capstone. Consult the [feature guide](https://platform.claude.com/docs/en/build-with-claude/compaction-on-demand) and [API versions](https://platform.claude.com/docs/en/api/versioning), and reject unsupported variants visibly.

| Value | Meaning | Loop action |
|---|---|---|
| `end_turn` | Finished naturally | exit, return text |
| `tool_use` | *Covered in [ch04](ch04_one_tool.md)* | run tools, continue |
| `max_tokens` | YOUR `max_tokens` cap was hit (truncated) | hard fail, raise |
| `stop_sequence` | Hit a `stop_sequences` string | exit |
| `refusal` | Claude refused | surface to user |
| `pause_turn` | Server-side tool needs more time | continue with no input |
| `model_context_window_exceeded` | The MODEL's context window filled up (Sonnet 4.5+) | compact + retry |

## Show me the code

```python
while True:
    r = client.messages.create(...)
    msgs.append({"role": "assistant", "content": r.content})

    if r.stop_reason in ("end_turn", "stop_sequence"): return r
    if r.stop_reason == "refusal":    raise Refused(r)
    if r.stop_reason == "max_tokens": raise Truncated(r)
    if r.stop_reason == "model_context_window_exceeded":
        raise ContextOverflow(r)                       # compact, then retry
    if r.stop_reason == "pause_turn": continue
    if r.stop_reason == "tool_use":                    # ch04 covers what this means
        msgs.append({"role": "user", "content": run_tools(r.content)})
        continue
    raise UnknownStopReason(r.stop_reason)             # forward-compat
```

Exhaustive. Loud on every unexpected value. **No silent failures.**

## ⚠️ Watch out for

**The mid-JSON truncation.** When `max_tokens` cuts the reply during a streamed tool call, the buffered partial JSON is invalid. Always check `stop_reason` BEFORE parsing.

**`max_tokens` ≠ `model_context_window_exceeded`.** The first means *YOU* set the output cap too low — retry with a higher cap. The second means input + output blew past the model's window — retry won't help; you need to compact ([ch10](ch10_compaction.md)) or use a larger model.

## ✅ Summary

- These seven foundation stop reasons need distinct handling; feature-specific variants may extend the set.
- Never write `while stop_reason == "tool_use"` — handle all seven.
- Always raise loudly on unknown values for forward-compatibility.

## 📝 Homework

```bash
python -m chapters.ch03_stop_reasons
```

1. Trigger `max_tokens` by setting `max_tokens=8`.
2. Trigger `stop_sequence` with `stop_sequences=["END"]`.
3. Inject a refusal fixture and check that the harness reports it distinctly from empty success.
4. **Bonus:** inject a `model_context_window_exceeded` fixture and assert that no tool executes. Do not buy a huge prompt just to exercise this branch; input validation can also reject oversized requests before generation.

## 📚 References

- [Anthropic — Handling stop reasons](https://docs.anthropic.com/en/api/handling-stop-reasons) — canonical list with examples
- [Anthropic — Messages API reference](https://docs.anthropic.com/en/api/messages) — full response shape
- [Anthropic — `model_context_window_exceeded` announcement](https://docs.anthropic.com/en/release-notes/api) — added with Sonnet 4.5

## 🚀 Next

[Chapter 04 — Your first tool](ch04_one_tool.md): now the loop has a reason to exist, and `tool_use` will make sense.

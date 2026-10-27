# Chapter 16 — Streaming `tool_use` (The Hard Chapter) 🐢

> **Text deltas you render. tool_use deltas you ACCUMULATE. Don't mix them up.**

## 🐢 GuiGui says

`'{"expr'` is not valid JSON. Buffer the fragments, then wait for the response's final `stop_reason`. A `content_block_stop` event closes one block; it does not tell you whether generation was truncated. Validate the entire tool batch before executing any call.

## The rule

| Block type | Delta name | Action |
|---|---|---|
| `text` | `text_delta` | Render immediately |
| `tool_use` | `input_json_delta` | **Accumulate. Check final stop reason, then parse.** |

## Show me the code

```python
buffers = {}                              # index -> partial JSON string
stop_reason = None

for event, data in stream(...):
    if event == "content_block_start":
        if data["content_block"]["type"] == "tool_use":
            buffers[data["index"]] = ""

    elif event == "content_block_delta":
        d = data["delta"]
        if d["type"] == "text_delta":
            print(d["text"], end="", flush=True)
        elif d["type"] == "input_json_delta":
            buffers[data["index"]] += d["partial_json"]   # accumulate

    elif event == "message_delta":
        stop_reason = data["delta"]["stop_reason"]

# Only a completed tool request can become executable input.
if stop_reason in {"max_tokens", "model_context_window_exceeded"}:
    raise RuntimeError(f"response truncated: {stop_reason}")
if buffers:
    if stop_reason != "tool_use":
        raise RuntimeError(f"unexpected stop_reason: {stop_reason}")
    inputs = {idx: json.loads(raw or "{}") for idx, raw in buffers.items()}
    if not all(isinstance(args, dict) for args in inputs.values()):
        raise RuntimeError("tool inputs must be JSON objects")
    # Dispatch only after every input has passed validation.
```

The executable chapter also checks other stop reasons and reconstructs the original block order. It supports local tools; server-tool continuation after `pause_turn` is outside this example.

## ⚠️ Watch out for

**The truncated tool args.** A buffer ends with `'{"path": "/etc/host'`. The final reason might be `max_tokens` or `model_context_window_exceeded`. Report truncation before parsing; do not replace invalid JSON with `{}` or execute a partial call.

**The half-executed batch.** The first call parses, but the second is malformed. Parsing and executing in the same loop would already have run the first call. Parse all inputs first, then dispatch. Object-shape validation is still only a first step: real tools must validate their own arguments and permissions.

## ✅ Summary

- `text_delta` → render now.
- `input_json_delta` → accumulate until the response finishes.
- Always check stop_reason before parsing the buffer.
- Validate all calls before executing any of them.

## 📝 Homework

```bash
python -m chapters.ch16_streaming_tools "what's 999 * 999, then a joke about it?"
```

1. Watch the trace. Text deltas render as chunks; tool_use shows up after the response finishes and validation succeeds.
2. Force a truncation with a small `max_tokens`, or run `python -m pytest tests/test_streaming_tools.py` without a key. Confirm a truncation error is reported and no tool runs.
3. Implement a "live tool args" UI that shows the buffer contents as it grows (just for debug).

## 📚 References

- [Anthropic — `input_json_delta` events](https://docs.anthropic.com/en/api/messages-streaming#tool-use) — the partial-JSON protocol
- [Anthropic SDK — streaming tool use issues](https://github.com/anthropics/anthropic-sdk-python/issues?q=input_json_delta) — community foot-guns
- [`partial-json-parser` (npm)](https://github.com/promplate/partial-json-parser) — incremental JSON parsing for live UI rendering
- [Streaming structured output — best practices](https://platform.openai.com/docs/guides/structured-outputs/streaming) — OpenAI's parallel approach (worth comparing)

## 🚀 Next

[Chapter 17 — Multi-provider](ch17_multi_provider.md): same loop, three wires.

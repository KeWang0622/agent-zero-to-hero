# Chapter 10 — Compaction 🐢

<p align="center">
  <img src="../assets/ch10-illustration.png" alt="Compaction" width="100%">
</p>

> **Compaction trades history detail for a smaller working context. Test what survives.**

## 🐢 GuiGui says

Every Claude Code user has watched *"Compacting…"* appear and wondered. This is the chapter that demystifies it. ~80 lines. This chapter implements a client-side summary, one of several context-management strategies.

## The idea

```
BEFORE  [m1, m2, m3, m4, m5, m6, m7, m8, m9, m10]   ← 60% of context window
                       │
              summarize via 1 LLM call
                       ▼
AFTER   [<summary>, m7, m8, m9, m10]                ← back under threshold
        ↑              ↑
        synthetic     verbatim recent
```

Four design choices:
1. **Trigger** — token count, not message count. This demo chooses 60% of the window; it is a heuristic, not a measured universal optimum.
2. **What to summarize** — oldest N. Recent ones still load-bearing.
3. **Preserve verbatim** — file paths, UUIDs, decisions, pending TODOs.
4. **Drop** — retried errors, idle exploration, redundant tool output.

## Show me the code

```python
def compact(messages, keep_recent=4):
    if len(messages) <= keep_recent + 1:
        return messages

    old, recent = messages[:-keep_recent], messages[-keep_recent:]

    r = client.messages.create(
        model=M, system=SUMMARIZER_PROMPT, max_tokens=2048,
        messages=old + [{"role": "user", "content": "Summarize per instructions."}],
    )
    summary = "".join(b.text for b in r.content if b.type == "text")

    preamble = (f"<conversation_summary>\n{summary}\n</conversation_summary>")
    return [{"role": "user", "content": preamble}] + recent
```

That's the surgery. One LLM call. Replace the older half. Resume the loop.

## ⚠️ Watch out for

**The compaction-boundary orphan.** Summarizing a slice that ENDS on an assistant `tool_use` breaks the API on the next call: the retained `tool_result` refers to a discarded call. Fix: walk back until the older slice ends on a safe message (text-only assistant, or a user turn).

**First message must be `role: "user"`.** The synthetic summary is a user message for this reason — don't be tempted to make it `role: "assistant"`. The API rejects assistant-first.

## beyond the teaching summary

Provider-managed compaction is another option: [Claude's overview](https://platform.claude.com/docs/en/build-with-claude/compaction) and [OpenAI's compaction guide](https://developers.openai.com/api/docs/guides/compaction) describe their own formats and availability. Do not convert opaque provider state into an invented text summary. A persisted application task list, original evidence, and tool receipts should remain authoritative outside a lossy summary.

The compact snippet above and the standalone chapter are intentionally simpler than `agent.py`'s tool-pair boundary handling. Never cut between a `tool_use` and its results. This update persists **new capstone compaction snapshots** so resume can reconstruct the context used before restart; old count-only records cannot recover summaries that were never saved.

## ✅ Summary

- Budget by tokens and expected next-step headroom; choose and evaluate a threshold for your workload.
- Replace older half with one synthetic user message ("conversation_summary").
- Preserve identifiers verbatim. Drop redundancy.

## 📝 Homework

```bash
python -m chapters.ch10_compaction       # paid demo; default input may not trigger compaction
```

1. Lower the local demo threshold to trigger compaction on a small input. Compare before/after token counts and whether constraints survive. Avoid buying 120,000 tokens just to test the branch.
2. Lower `KEEP_RECENT` to 1. Run a multi-step task. What gets lost?
3. Edit `SUMMARIZER_PROMPT` to drop the "preserve identifiers" line. Watch UUIDs go missing.

## Where this shows up in agent.py

`agent.py` — the `compact_messages()` function and its `_is_tool_use_assistant()` helper (around lines 452-494) include the tool_use boundary fix that the raw API would otherwise reject.

## 📚 References

- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system) — production lessons including context management
- [Anthropic — Prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — related cost lever (different concern but same chapter family)
- [openclaw — `compaction.ts`](https://github.com/openclaw/openclaw/blob/main/src/agents/compaction.ts) — production version with token-budget trigger and 3 fallback tiers
- [Liu et al. — Lost in the Middle (2023)](https://arxiv.org/abs/2307.03172) — why agents get dumber as context grows

## 🚀 Next

[Chapter 11 — Subagents](ch11_subagents.md): another way to keep context small — never put it there in the first place.

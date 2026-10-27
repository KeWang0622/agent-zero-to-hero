# Chapter 11 — Subagents 🐢

<p align="center">
  <img src="../assets/ch11-illustration.png" alt="Subagents" width="100%">
</p>

> **A subagent is an agent loop with a FRESH messages array, called as a tool. Its conversation is invisible to the parent. Only its final answer comes back.**

## 🐢 GuiGui says

Compaction recovers context after damage. Subagents *prevent* damage. Spawn a child to do the dirty work — read 50 files, run 30 commands, fill ITS context with junk — then return ONE STRING to the parent. The parent's context grows by ~17 tokens instead of ~17,000.

This is the load-bearing trick behind Claude Code's `Task` tool.

## Show me the code

```python
def run_subagent(task: str) -> str:
    """Fresh agent loop. Returns only the final assistant text."""
    msgs = [{"role": "user", "content": task}]
    final = ""
    for _ in range(20):
        r = client.messages.create(model=M, tools=SUBAGENT_TOOLS, messages=msgs, max_tokens=2048)
        msgs.append({"role": "assistant", "content": r.content})
        final = "".join(b.text for b in r.content if b.type == "text")
        if r.stop_reason != "tool_use": break
        msgs.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b.id,
             "content": dispatch(b.name, b.input)}
            for b in r.content if b.type == "tool_use"
        ]})
    return final
```

Register it as a tool in the parent's TOOLS list. Done.

## illustrative cost math

The following numbers are a hypothetical input-token calculation, not a benchmark or a guaranteed saving. They omit output tokens and caching.

The big win is on the PARENT's context, not total tokens. With a subagent the parent stays small and stays sharp:

| | Single agent | With subagent |
|---|---|---|
| Parent input per turn | 50,000 tokens | **5,000 tokens** |
| 10 turns of parent | 500K tokens | 50K tokens — **10× smaller** |
| Total tokens (incl. subagent) | 500K | ~300K |
| Total cost @ Sonnet rates | $1.50 | $0.90 (no caching) |

Caching can affect both baselines. A smaller parent context may improve focus, but quality depends on which evidence survives the handoff. Require each child to return its result, evidence, uncertainty, and artifact location. Parallelize independent reads; coordinate shared writes and aggregate every child's resource use.

## ⚠️ Watch out for

**The subagent token explosion.** Spawning a subagent for every minor task triples your bill — each subagent has 2-5K tokens of startup cost. Heuristic: spawn only when the parent would otherwise dump >5K tokens of intermediate state.

## ✅ Summary

- Subagent = fresh `messages[]` agent loop, called as a tool.
- Parent only sees the final string.
- Smaller parent context can help; total cost includes every child. Measure quality, latency, and aggregate tokens against a single-agent baseline.

## 📝 Homework

```bash
python -m chapters.ch11_subagents
```

1. Same task: parent-only run vs parent+subagent run. Measure tokens × dollars.
2. Add a SECOND subagent type (a "research" subagent with web search).
3. Add a `Task` tool to `agent.py`. ~30 LOC. Make `agent.py` capable of delegated reasoning.

## 📚 References

- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — production patterns
- [Anthropic — Building Effective Agents (orchestrator-workers section)](https://www.anthropic.com/research/building-effective-agents) — the canonical pattern
- [shareAI-lab/learn-claude-code — `s04`](https://github.com/shareAI-lab/learn-claude-code) — fresh-`messages[]` subagent reference
- [Hong et al. — MetaGPT (2023)](https://arxiv.org/abs/2308.00352) — multi-agent framework paper

## 🚀 Next

[Chapter 12 — Skills](ch12_skills.md): instructions loaded on demand, not eagerly.

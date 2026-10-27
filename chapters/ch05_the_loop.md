# Chapter 05 — THE LOOP 🐢

<p align="center">
  <img src="../assets/ch05-illustration.png" alt="The agent loop" width="100%">
</p>

> **The thing the model can't do is run code. The thing you can't do is think. An agent loop is just `while True` of one talking to the other.**

## 🐢 GuiGui says

This is the chapter the entire course pivots on. Everything before it built up to one insight. Everything after it adds layers around it. **By the end of this chapter you can write Cursor / Claude Code / Devin from a blank file.**

## The idea

Chapter 04 was a *two-call protocol*: ask, run tool, send result, get answer. **One round-trip.** That works for one-step problems. It breaks when Claude needs information it doesn't yet have:

> *"What's the biggest Python file in chapters/?"*

Claude's first call is `glob`. Then `wc -l`. Then "the biggest is X." **Three round-trips minimum.** The fix is one keyword: `while`. Wrap chapter 4's protocol in a loop, and the agent can call any number of tools, in any order, until it has enough information to answer.

## The 6 lines (annotated)

```python
def agent_loop(prompt: str):
    msgs = [{"role": "user", "content": prompt}]              # ① the only state

    for turn in range(MAX_TURNS):                             # ② cap it. always.
        r = client.messages.create(                           # ③ the one API call
            model=M, tools=TOOLS, messages=msgs, max_tokens=2048
        )
        msgs.append({"role": "assistant", "content": r.content})  # ④ persist reply

        if r.stop_reason != "tool_use":                       # ⑤ exit when done
            return r

        msgs.append({"role": "user", "content": [             # ⑥ run + append + loop
            {"type": "tool_result", "tool_use_id": b.id,
             "content": dispatch(b.name, b.input)}
            for b in r.content if b.type == "tool_use"
        ]})

    raise RuntimeError(f"hit MAX_TURNS={MAX_TURNS}")
```

That is the control-flow skeleton. The snippet deliberately omits status handling and execution policy. A reliable harness must distinguish completion from truncation, bound work, validate tools, and persist progress. Those requirements are part of the system, not consequences of writing six lines.

---

## 🤔 But how does Claude *know* what to do?

This is the question the rest of this chapter answers. It's the deepest question of the course.

### what the API lets us observe

The request supplies instructions, conversation context, and tool definitions. The response may contain text and structured tool requests. Generation can involve multiple decoding steps and provider-specific reasoning state; a public response does not reveal the model's complete internal process or training recipe.

We can improve behavior by changing context, tool interfaces, and instructions, then measuring the effect. We cannot conclude from one trace that the model has no plan, or that every failure is a prompt-description problem. Failures can also come from missing evidence, bad tool results, truncated output, stale state, or executor bugs.

### visible commentary is useful, but it is not private reasoning

```python
# Illustrative response shape, not runnable construction.
[
    {"type": "text", "text": "I'll start by listing the files."},
    {"type": "tool_use", "id": "t1", "name": "glob",
     "input": {"pattern": "chapters/*.py"}},
]
```

Visible text can explain an intended action to the user. Log the tool request and actual result to debug behavior. Do not treat commentary as a faithful transcript of internal reasoning or proof that the action happened. Some providers return additional reasoning-related items; preserve required state using that provider's contract, as [chapter 17b](ch17b_responses.md) explains.

## the action-observation cycle

```text
request 1: model requests a file listing
executor:  lists files and returns the actual result
request 2: model requests line counts for the discovered files
executor:  returns counts
request 3: model produces an answer grounded in those observations
```

This resembles the action/observation structure studied by [ReAct](https://arxiv.org/abs/2210.03629). It does not establish which training method any particular proprietary model used. New observations can change the next action. A visible plan is useful context, but it does not enforce a state transition or guarantee task completion.

For a longer task, keep explicit pending work and acceptance criteria. The important distinction is between a model *proposing* a plan and the application *recording and verifying* progress.

---

## 📋 When you DO want explicit planning: TodoWrite

Three techniques with different enforcement boundaries:

### 1. System prompt rule (soft)
```python
SYSTEM = "For tasks with more than 2 steps, write a numbered plan first, then execute it."
```
Shifts the distribution toward decomposition. ~80% reliable. Cheap.

### 2. TodoWrite tool (hard) — Claude Code's pattern
Add a tool whose only job is to **materialize the plan as a tool call**:

```python
{"name": "TodoWrite",
 "description": "Track a multi-step plan. Call FIRST when starting any task with >2 steps.",
 "input_schema": {
     "type": "object",
     "properties": {"todos": {"type": "array",
         "items": {"type": "object",
             "properties": {
                 "content": {"type": "string"},
                 "status":  {"enum": ["pending", "in_progress", "completed"]},
             }}}},
     "required": ["todos"]}}
```

Real trace using this tool:
```
turn 0 → TodoWrite([
  {content: "list python files in chapters/", status: "in_progress"},
  {content: "count lines per file",            status: "pending"},
  {content: "report the longest one",          status: "pending"},
])
turn 1 → glob(...)
turn 2 → TodoWrite([... step 1 completed, step 2 in_progress ...])
turn 3 → bash(wc -l ...)
turn 4 → TodoWrite([... all completed ...]) + final answer
```

The plan is now **observable, debuggable, and self-correcting**. If something breaks mid-run, you can read the todos to see where claude was. Drop in error rates of ~30% on real coding tasks.

`agent.py` ships TodoWrite — handler at line 156, schema at line 206.

### 3. Plan mode (hardest) — separate two-phase agent
A *separate* read-only loop produces a plan document. A human approves. A *second* loop with write access executes it. Out of scope for this chapter; see Claude Code's plan-mode UI for the canonical implementation.

---

## ⚠️ Watch out for

**The runaway loop.** Without a cap, a buggy tool that returns "try again" can cost $40 in an hour. **Always `for turn in range(MAX_TURNS)`, never bare `while True`.**

**Goldfish agents.** Re-creating `msgs = []` inside the loop = fresh start every turn. Build it ONCE outside the loop.

**Skipping `messages.append(r.content)`.** The next turn's call will get a role-alternation 400 because there's no assistant message between the user's prompt and the tool_results.

## ✅ Summary

- Agent = `while True { call → dispatch → continue }`. Six lines.
- Decomposition is **predicted, not planned** — driven by training, tool descriptions, and the system prompt.
- Each turn = one ReAct cycle (Reason + Act, then Observe at the start of the next turn).
- The model is **reactive** by default. For reliable multi-step planning, add a `TodoWrite` tool.
- A turn cap is non-negotiable.

## 📝 Homework

```bash
python -m chapters.ch05_the_loop "what's the biggest python file in chapters/?"
```

1. Count turns. Should be 2-4. Add `print(f"=== turn {turn} ===")` and observe the ReAct cycle.
2. Print `r.content` after each call. Read the text-before-tool_use reasoning.
3. **Decomposition test:** edit `chapters/ch05_the_loop.py` to corrupt the `glob` description (change it to `"List files (rarely useful)"`). Re-run. Watch claude either skip glob entirely or pick bash instead. Reset and verify glob comes back.
4. **Planning test:** add a `TodoWrite` tool to ch05's TOOLS list. Run a 5-step task. Compare turn count vs without TodoWrite.
5. **Synthesis (100 words):** Why is the model reactive by default — and when is that *not* what you want?

## Where this shows up in agent.py

`agent.py` — the `agent_turn` function (around line 629) is the same six lines, plus streaming, plus retries, plus permissions, plus session writes. The `TodoWrite` schema is at line 206 in the TOOLS list, the handler is at line 156, and the system prompt tells claude to use it for multi-step work (lines 526-546; the TodoWrite rule is at line 535).

## 📚 References

**Foundational papers**
- [Yao et al. — ReAct: Synergizing Reasoning and Acting in Language Models (2022)](https://arxiv.org/abs/2210.03629) — the paper. Read it.
- [Shinn et al. — Reflexion (2023)](https://arxiv.org/abs/2303.11366) — adding self-critique to the ReAct loop
- [Wei et al. — Chain-of-Thought Prompting (2022)](https://arxiv.org/abs/2201.11903) — why "thinking out loud" works

**Anthropic's frame**
- [Anthropic — Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) — the canonical taxonomy of agent patterns
- [Anthropic — How we built Claude Code's multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — production lessons

**Karpathy lineage**
- [Karpathy — Software 3.0 (2025 talk)](https://www.youtube.com/watch?v=LCEmiRjPEtQ) — the agent loop as a primitive
- [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) — the literary template this course follows

**Production references**
- [openclaw](https://github.com/openclaw/openclaw) — open clone of Claude Code; read its `src/agents/pi-embedded-runner/run.ts`
- [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) — 12-session course covering the same primitives

## 🚀 Next

[Chapter 06 — Parallel tools](ch06_parallel_tools.md): claude can ask for three things at once. The single-user-message rule.

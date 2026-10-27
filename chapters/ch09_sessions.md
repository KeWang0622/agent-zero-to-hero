# Chapter 09 — Sessions: A Conversation That Survives `Ctrl-C` 🐢

> **This chapter's session is an append-only JSONL log plus an in-memory messages array. You can inspect both.**

## 🐢 GuiGui says

The chapter writes conversation events as JSONL, then reconstructs the messages array when you reopen a session. This makes ordinary restarts easy to understand. Recovering a partially executed tool action requires additional state, which this example does not implement.

## Why JSONL not JSON

| Feature | JSON | JSONL |
|---|---|---|
| Append per turn | Read + parse + modify + write | One `f.write(line + "\n")` |
| Partial write | May leave an invalid document | Earlier complete lines can be recovered with an explicit recovery policy |
| Greppable / `tail -f` | No | Yes |
| Schema evolution | Requires reader compatibility | Event types and fields still require reader compatibility |

## Show me the code

```python
class Session:
    def __init__(self, session_id=None):
        self.id = session_id or uuid.uuid4().hex
        self.path = SESSION_DIR / f"{self.id}.jsonl"
        self.messages = []
        if self.path.exists():
            for line in self.path.open():
                self._reload(json.loads(line))

    def append(self, role, content):
        self.messages.append({"role": role, "content": content})
        with self.path.open("a") as f:
            f.write(json.dumps({"role": role, "content": content}) + "\n")
```

## ⚠️ Watch out for

**The unanswered user message.** Ctrl-C between the prompt and reply can leave a trailing user message. The Messages API combines consecutive same-role turns, so this does not inherently cause a role-alternation error. Keeping the unanswered prompt, retrying it, or dropping it is an application choice. The chapter retains it; the capstone drops a trailing plain user prompt on resume. [Messages API reference](https://platform.claude.com/docs/en/api/messages/create)

**The partial last line.** JSONL is a format, not an atomic-write guarantee. `flush()` does not guarantee that data survives power loss, and this chapter's simple reader raises on invalid JSON. The capstone skips malformed lines, but a durable store also needs an explicit corruption policy and protection against concurrent writers.

**The unresolved tool call.** A crash can happen after an assistant requests a tool, or after a side effect succeeds but before its result is logged. Replaying the conversation alone cannot tell you whether it is safe to run that tool again. Production recovery needs execution checkpoints, idempotency where available, and reconciliation of uncertain outcomes. See [durable execution](ch20_durable_execution.md).

**The missing rewrite.** Compaction changes the active conversation. The capstone now records the compacted message snapshot and replays it on resume; older logs that recorded only a message count cannot recover their missing summary.

## ✅ Summary

- JSONL makes append-only conversation logs inspectable.
- Session = file + in-memory mirror of messages.
- Resume requires replay rules for messages, compaction, and incomplete work.
- Conversation persistence does not provide durable tool execution by itself.

## 📝 Homework

```bash
# start a session, kill it mid-turn, resume
python -m chapters.ch09_sessions
> hello
> what's 2+2?
> ^C
python -m chapters.ch09_sessions resume <id>
> what did I just ask?
```

1. Verify the resumed session remembers your prior turns.
2. `tail -f ~/.agent-zero-to-hero/sessions/<id>.jsonl` while running. Watch each turn append.
   *(Note: the capstone `agent.py` namespaces by cwd — `~/.agent-zero-to-hero/projects/<slug>/<id>.jsonl`.)*
3. Modify ONE line in the JSONL by hand. Resume. Does it work?

## 📚 References

- [JSON Lines spec](https://jsonlines.org/) — the format we use for sessions
- [Claude Code session storage](https://docs.anthropic.com/en/docs/claude-code/sessions) — Anthropic's production layout (`~/.claude/projects/...`)
- [openclaw — session store source](https://github.com/openclaw/openclaw/blob/main/src/config/sessions/store.ts) — production reference: index JSON + per-session JSONL

## 🚀 Next

[Chapter 10 — Compaction](ch10_compaction.md): the array grows forever. Until it doesn't.

# Chapter 12 — Skills: Markdown Loaded On Demand 🐢

> **A skill is a markdown file with YAML frontmatter. Claude reads it only when needed. Don't put everything in the system prompt.**

## 🐢 GuiGui says

Simon Willison called this *"maybe a bigger deal than MCP."* The system prompt should be SHORT. It should contain claude's persona AND a CATALOG of available skills. The actual procedural knowledge — examples, style guides, pitfalls — lives in separate files claude can read on demand. **Progressive disclosure.**

A small catalog avoids loading irrelevant procedures. Measure the effect on total cost and task success; a smaller initial prompt does not guarantee a fixed saving.

## The shape on disk

```
skills/
  haiku-master/
    SKILL.md           ← 200 lines: how to write haiku, examples, style
  invoice-design/
    SKILL.md           ← 500 lines: design rules, pricing, layouts, examples
  sql-debugging/
    SKILL.md           ← 800 lines: common pitfalls, queries to run, recoveries
```

Each `SKILL.md` is **YAML frontmatter** (name + 1-line description) + **markdown body** (the procedural knowledge):

```markdown
---
name: haiku-master
description: How to write a proper haiku. Use when the user asks for a haiku.
---

# Haiku — the rules

A haiku follows three constraints, in order of importance:
1. Three lines.
2. 5-7-5 syllables.
3. A seasonal turn (kigo).

## Style guide
- No rhyming. Rhymes destroy haiku.
- Use ONE concrete image per line.
...
```

## What the model actually sees

Here's the trick. The model **never sees the skill bodies in the system prompt**. It sees only the catalog — name + 1-line description per skill:

```
SYSTEM PROMPT (always loaded, ~300 tokens):
  You are agent-zero-to-hero with access to skills.

  Available skills:
    - haiku-master: How to write a proper haiku. Use when the user asks for a haiku.
    - invoice-design: How to design an invoice. Use when user asks for one.
    - sql-debugging: Debug slow Django N+1 queries.

  Call read_skill(name) to load a skill's body when needed.
```

When claude decides it needs a skill, it calls `read_skill("haiku-master")` and the body comes back as a `tool_result`. The body is now in messages — claude has the procedural knowledge it needs **until the harness removes, compacts, or resets that history**.

## What flows on the wire

```
TURN 1 — user asks for a haiku
─────────────────────────────────────────────────────────────
SYSTEM: "...skills available: haiku-master, invoice-design, sql-debugging..."
USER:   "write me a haiku about autumn"

API replies:
  content = [
    {"type": "text", "text": "Let me load the haiku skill."},
    {"type": "tool_use", "id": "t1", "name": "read_skill",
     "input": {"name": "haiku-master"}}
  ]

TURN 2 — you load and return the skill body
─────────────────────────────────────────────────────────────
your code reads skills/haiku-master/SKILL.md and returns the body.

YOU send:
  tool_result content = "Haiku — the rules\n A haiku follows three..."
                        (~3000 tokens of procedural knowledge)

API replies:
  content = [{"type": "text", "text":
    "old wooden gate\n a leaf falls onto the latch\n autumn is here"}]
  stop_reason = "end_turn"
```

**Two API calls. The skill body was loaded once.** Compare to the alternative: putting all 3 skills' bodies into the system prompt forever — every turn pays for 5,000 tokens of skill content even when no skill is relevant.

> **Note on Anthropic's official Skills feature.** Anthropic shipped a [first-party Skills system in October 2025](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) that uses the **Bash tool** to read `SKILL.md` from disk — there's no dedicated `read_skill` tool. The mechanism is identical (catalog in system prompt, body loaded on demand as a `tool_result`); we use a custom `read_skill` tool here to keep the example self-contained without requiring the Bash sandbox. Conceptually it's the same chapter.

## the cost model

Loading a body once does not mean paying for it once. While it remains in the conversation, subsequent requests include it again; prompt caching may discount eligible repeated tokens. Compare eager and deferred loading using measured uncached input, cache writes, cache reads, and outputs.

The portable [Agent Skills specification](https://agentskills.io/specification) defines required `name` and `description` metadata and optional supporting directories. Our tiny frontmatter parser is a teaching subset, not a complete YAML parser or specification validator. A skill packages procedures; it does not grant permissions to execute them. Review untrusted scripts and keep executor authorization independent of skill prose.

## Show me the code

```python
import yaml  # or parse frontmatter by hand — see ch12.py

def parse_skill(path: Path) -> dict:
    """SKILL.md = YAML frontmatter + markdown body."""
    text = path.read_text()
    _, fm, body = text.split("---", 2)
    meta = {l.split(":", 1)[0].strip(): l.split(":", 1)[1].strip()
            for l in fm.strip().splitlines() if ":" in l}
    return {**meta, "body": body}

# discover skills at startup
skills = {s["name"]: s for s in (parse_skill(p) for p in Path("skills").glob("*/SKILL.md"))}

# system = persona + catalog (NOT bodies)
catalog = "\n".join(f"  - {s['name']}: {s['description']}" for s in skills.values())
SYSTEM = f"You have skills:\n{catalog}\nCall read_skill(name) to load one."

# meta-tool the model calls when it needs a body
TOOLS = [{
    "name": "read_skill",
    "description": "Load a skill's procedural knowledge by name.",
    "input_schema": {"type": "object",
                     "properties": {"name": {"type": "string"}},
                     "required": ["name"]},
}]

HANDLERS = {
    "read_skill": lambda name: skills[name]["body"],
}
```

That's it. Skills are just Python: a folder of markdown files + one `read_skill` tool.

## ⚠️ Watch out for

**The catalog overload.** 50 skills with vague descriptions → claude doesn't know which to load → calls 3-5 in sequence "to check." Fix: each `description` makes the load decision *obvious*. Bad: `"Helps with code"`. Good: `"Debug slow Django N+1 queries — use when user mentions slow page loads."`

**The eager-load trap.** "Just stuff all skill bodies into the system prompt — it's simpler." Yes, until your system prompt is 50K tokens and every turn costs 30× what it should. **The whole point of skills is on-demand.**

**Skill drift.** A skill body says "use the `wc -l` tool" but you renamed it to `count_lines`. Skills get stale. Audit them when you rename tools.

## ✅ Summary

- Skills = on-demand context, not eager system-prompt bloat.
- Catalog (name + 1-line description) goes in system. **Bodies do not.**
- One meta-tool `read_skill(name)` returns the body when claude asks.
- **30× cheaper** than eager-loading 5 skill bodies into the system prompt.

## 📝 Homework

```bash
python -m chapters.ch12_skills
# Then try: "write me a haiku about the sea"
# Watch claude call read_skill("haiku-master") before composing.
```

1. **Trace the load.** Print the messages array right before claude composes the haiku. See where the skill body shows up — and confirm it's NOT in the system prompt.
2. **Add a skill.** Create `skills/sql-formatter/SKILL.md` with rules for formatting SQL queries. Verify discovery and that claude loads it for SQL questions.
3. **Cost compare.** Manually inline all skill bodies into the system prompt. Run 5 turns. Compare `usage.input_tokens` vs the catalog version.
4. **Wire `read_skill` into `agent.py`.** ~30 LOC. Now your CLI agent can be extended just by dropping markdown files in `skills/`.

## 📚 References

- [Anthropic — Equipping agents with Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — the official launch post
- [Simon Willison — Claude Skills are maybe a bigger deal than MCP](https://simonwillison.net/2025/Oct/16/claude-skills/) — why this chapter exists
- [Anthropic — Claude Code skills directory](https://docs.anthropic.com/en/docs/claude-code/skills) — the canonical SKILL.md format
- [openclaw — `skills/` directory](https://github.com/openclaw/openclaw/tree/main/skills) — production examples worth copying

## 🚀 Next

[Chapter 13 — MCP demystified](ch13_mcp_wire.md): tools across process boundaries.

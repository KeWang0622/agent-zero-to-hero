# LAUNCH.md — go-to-market playbook

> Internal launch doc for **agent-zero-to-hero**. Not part of the course.
> Goal: land the Show HN front page, then amplify. 10k stars is the ceiling,
> not a switch — a strong showing is 1–3k and still a win.

## The one rule

This genre (Karpathy-style "build X from scratch") **lives or dies on Hacker
News**, and its audience **fact-checks the code and every claim**. So before
anything ships:

- [ ] Every number in the repo is literally true (`wc -l`, `pytest`, chapter count).
- [ ] `git clone && pip install -e . && pytest` works copy-paste on a clean machine.
- [ ] All README links resolve; `explainer.mp4` / `launch.gif` render on GitHub.
- [ ] No secrets committed; no stray scratch files.

Canonical facts (keep these in sync everywhere — README, pyproject, share cards,
GitHub repo description):

| Claim | Value | How to verify |
|---|---|---|
| Total Python | **~5,000 lines** (5,120) | `find . -name '*.py' \| xargs wc -l` |
| `agent.py` | **~850 lines** | `wc -l agent.py` |
| Chapters | **20** numbered files | `ls chapters/ch*.py \| wc -l` |
| Tests | **42**, no API key | `pytest tests/` |
| Providers | **3** (Anthropic/OpenAI/Gemini) | `chapters/ch17_multi_provider.py` |

## The Claude × Codex split

- **Codex** — code & facts: audit every number, fresh-clone quickstart test,
  verify links, run the full suite, sanity-read `agent.py` for the obvious nitpick.
- **Claude** — narrative & launch: copy, README top-of-fold, FAQ, threads, and
  running the comment threads on launch morning.

## 1-day timeline (launch Tue/Wed/Thu)

1. **Harden (2–3 hrs, Codex):** claim audit + clean-clone install + link check + suite.
2. **Narrative (2 hrs, Claude):** tighten README first screen, finalize the posts below, write the FAQ.
3. **Launch (~9:00am ET):** post Show HN, then **answer every comment for 90 min**. This is 80% of the outcome.
4. **Amplify (only once HN is climbing):** X thread → Reddit → LinkedIn.

## Posts

### Hacker News — title
```
Show HN: Build Claude Code from scratch – 20 chapters, ~5,000 lines, no frameworks
```

### Show HN — body
```
I kept using coding agents (Claude Code, Cursor) without really knowing what
happened inside the box, so I rebuilt one from scratch to find out.

The whole agent loop turns out to be ~6 lines. Everything else — tools,
sessions, compaction, subagents, skills, MCP, streaming, multi-provider — is
just the harness around it. The repo is 20 short chapters (one Python file +
one explainer each) that build up to an ~850-line Claude-Code-shaped CLI.

No frameworks. 42 tests pass with no API key (mocked LLMs + a real MCP
subprocess). Full course runs ~$5-10 of API spend; the speedrun is ~$0.50.

I wrote it to be read on a flight. Would love feedback on what's missing or
wrong — especially from people who've built agents in production.
```

### X / Twitter — hook (attach `assets/share/the-loop-poster.png`)
```
Every coding agent — Claude Code, Cursor, Devin — is the same 6 lines:

[the-loop-poster image]

I wrote 20 chapters building the rest of the harness around it.
~5,000 lines of Python, no frameworks, 42 tests, no API key to run them.

🧵
```
Then 8–10 tweets, one concept each, drawn from the README mottos:
- "The messages array IS the memory. There is no other memory."
- "Compaction is surgery, not GC."
- "Subagents: context isolation as a feature. 10× cheaper."
- "MCP is three JSON-RPC calls over stdio. That's all."

Last tweet = repo link + "MIT, built to be taught."

**Best single shareable asset:** a screen-recording of `agent.py` building Tetris
in one HTML file, live.

### Reddit (r/LocalLLaMA, r/MachineLearning [P])
Lead with *"I rebuilt a coding agent from scratch to understand the internals —
here's the 6-line core."* Explicitly invite the local-models question and answer
it with the multi-provider chapter (ch17).

### LinkedIn
Short, personal: why you built it (agent identity & memory at Pika), the 6-line
insight, link. Less hype than X.

## FAQ — predictable HN questions (have honest answers ready)

- **"Why not LangGraph / smolagents?"** — Those are frameworks to *use*. This is
  to *understand*. README says so explicitly; point there, don't get defensive.
- **"Isn't this just a `while` loop around an API?"** — Yes, and that's the
  point — chapters 1–5 prove it, then 6–17 are everything that makes the loop
  survive production (errors, cost, compaction, sessions, streaming).
- **"Anthropic-only?"** — No: ch17 ports the same loop to OpenAI + Gemini.
- **"Does it run local models?"** — Any OpenAI-compatible endpoint via the ch17
  adapter; point at the adapter.
- **"Can I trust the line count?"** — `wc -l` matches the README; that's by design.

## Guardrails

- Don't multi-post simultaneously — HN first, amplify after it's climbing.
- **Never** solicit upvotes anywhere (instant HN/Reddit death).
- Being responsive in hour 1 > any copy. Block the calendar.
- If it doesn't catch, that's normal — HN allows one resubmit on another day.

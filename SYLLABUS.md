# SYLLABUS

> *agent-zero-to-hero: Build a Claude-Code-shaped agent harness from scratch.*
> A 7-week, problem-set-driven course in agent engineering.
> No prerequisites beyond Python 3.10. No frameworks.
> Designed to be run by anyone — independent learners, study groups, or universities.

---

## Course goals

By the end of this course, a student can:

1. Read the source of any modern coding agent (Claude Code, Cursor, openclaw, Aider, OpenCode) and recognize every primitive.
2. Build a 600-line agent harness from a blank file in a weekend.
3. Reason about agent cost (token math, prompt caching, compaction) at production scale.
4. Decide when to add a tool vs a skill vs an MCP server vs a subagent.
5. Port an Anthropic agent loop to OpenAI or Gemini in <50 lines of adapter.

## Format

Each week pairs:
- **Lectures** — 2-3 chapters (`chapters/chNN_*.py`) you read AND run.
- **Lecture notes** — long-form `.md` walkthroughs for the hero chapters.
- **Lab** — extend a chapter or write a related demo. Open-ended, self-graded.
- **Problem set** — 2-4 short problems that exercise the chapter's concept.
- **Reading** — one external link (paper, blog post, repo) per week.

Total study time: **~25 hours over 7 weeks**, plus the capstone.

---

<img align="right" src="assets/week1.png" width="180" alt="Week 1">

## Week 1 — Foundations: from one HTTP call to the agent loop

**Lectures**: ch00, ch01, ch02, ch03, ch04, ch05

The conceptual core. By the end of week 1 a student has written the canonical 6-line agent loop and understands why it's universal.

**Hero chapters** (read the `.md`):
- [ch01_raw_call.md](chapters/ch01_raw_call.md) — *The string-not-list assumption*
- [ch02_messages_array.md](chapters/ch02_messages_array.md) — *The role-alternation violation*
- [ch04_one_tool.md](chapters/ch04_one_tool.md) — *The orphan tool_use*
- [ch05_the_loop.md](chapters/ch05_the_loop.md) — *The runaway loop*

**Reading**: Anthropic — [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)

**Problem set 1**:
1. Modify `ch01_raw_call.py` to use `system` parameter to make Claude reply in haiku.
2. In `ch02_messages_array.py`, add a "memory snapshot" — print `len(messages)` and the input token count after every turn.
3. In `ch05_the_loop.py`, deliberately break the loop by setting `MAX_TURNS=2` and run a 5-step task. Document the failure mode in 2 sentences.

**Lab**: Build a `weather` tool that wraps an HTTP call to a free weather API and integrate it into ch05's loop.

---

<img align="right" src="assets/week2.png" width="180" alt="Week 2">

## Week 2 — Tool engineering: parallel calls, errors, system prompts

**Lectures**: ch06, ch07, ch08

When real tools meet real models, things break. This week is about robustness.

**Reading**: Anthropic — [Parallel tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/parallel-tool-use)

**Problem set 2**:
1. Modify `ch06_parallel_tools.py` to deliberately split tool_results across multiple user messages. Run the same task 5 times. Count parallel-call rate before and after. Report.
2. In `ch07_errors.py`, add a fourth class of failure (network exception in a tool). Show the agent recovering.
3. Find one place in `agent.py` where a system prompt change would alter behavior. Justify your choice.

**Lab**: Build a tool registry with `@tool` decorator that auto-generates the JSON schema from a Python function's signature + docstring. ~30 LOC.

---

<img align="right" src="assets/week3.png" width="180" alt="Week 3">

## Week 3 — Cost & observability: caching, the dollar ticker, compaction

**Lectures**: ch08b, ch08c, ch10

The week most "build an agent" courses skip. Cost is the rate-limiter on real adoption — agents that don't compact and don't cache become economically unviable in week one of production.

**Hero chapter** (read the `.md`):
- [ch10_compaction.md](chapters/ch10_compaction.md) — *The orphan tool_use* (compaction edition)

**Reading**: dev.to — ["I tracked every token my AI coding agent consumed for a week. 70% was waste"](https://dev.to/nicolalessi/i-tracked-every-token-my-ai-coding-agent-consumed-for-a-week-70-was-waste-465)

**Problem set 3**:
1. Run `ch08b_observability.py` and `ch08c_prompt_caching.py`. Compute the break-even number of turns for a 1-hour TTL cache vs 5-minute, given a 1500-token system prompt.
2. Modify `ch10_compaction.py` to drop `KEEP_RECENT` to 1. Run a 30-turn task. Document what gets lost from the summary.
3. Implement a `/cost --since <session-id>` slash command that prints aggregate spend across multiple sessions. ~30 LOC.

**Lab**: Add OpenTelemetry export to `agent.py`'s `Meter`. Emit one span per turn, send to a local SigNoz container. ~60 LOC.

---

<img align="right" src="assets/week4.png" width="180" alt="Week 4">

## Week 4 — Persistence & scale: sessions, subagents

**Lectures**: ch09, ch11

State that survives crashes. Context that doesn't blow up.

**Hero chapter** (read the `.md`):
- [ch11_subagents.md](chapters/ch11_subagents.md) — *The subagent token explosion*

**Reading**: Anthropic — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)

**Problem set 4**:
1. Crash `ch09_sessions.py` deliberately mid-turn (Ctrl-C between user input and assistant reply). Resume. Verify orphan recovery worked.
2. In `ch11_subagents.py`, instrument the cost difference: parent-only run vs parent+subagent run. Report tokens × dollars.
3. Add a `Task` tool to `agent.py` (delegated subagent). ~30 LOC.

**Lab**: Build a "deep research" agent that delegates each search query to a fresh subagent and stitches the answers together. ~100 LOC.

---

<img align="right" src="assets/week5.png" width="180" alt="Week 5">

## Week 5 — Skills & MCP: the extension surfaces

**Lectures**: ch12, ch13, ch14

The two ways agent harnesses extend without bloating their core. By end of week 5 the student has written their own MCP server and understands what nobody else teaches.

**Hero chapter** (read the `.md`):
- [ch13_mcp_wire.md](chapters/ch13_mcp_wire.md) — *The orphan child process*

**Reading**: [The MCP specification](https://spec.modelcontextprotocol.io)

**Problem set 5**:
1. Add a `weather` skill at `skills/weather/SKILL.md`. Run `ch12_skills.py` and confirm the skill is discovered.
2. Extend `mcp_servers/calculator_server.py` to support a second tool, `unit_convert`. Update the wire test.
3. Compare: when does a capability belong as a tool vs a skill vs an MCP server? Write 3 bullets, ≤50 words.

**Lab**: Build an MCP server in a non-Python language (Rust, Go, TypeScript) and connect `ch14_mcp_agent.py` to it. Validate the JSON-RPC interop.

---

<img align="right" src="assets/week6.png" width="180" alt="Week 6">

## Week 6 — Engineering polish: streaming, multi-provider

**Lectures**: ch15, ch16, ch17

The wire-format chapters. Streaming text + accumulating tool_use partial JSON + porting to OpenAI / Gemini.

**Reading**: [Anthropic SSE issue tracker](https://github.com/anthropics/anthropic-sdk-typescript/issues?q=streaming) — read 5 issues

**Problem set 6**:
1. In `ch16_streaming_tools.py`, deliberately call `json.loads()` on an `input_json_delta` mid-stream. Document the error.
2. Run `ch17_multi_provider.py` against all 3 providers (or 2 if you don't have Gemini). Compare turns × tokens × wall-clock. Report.
3. Implement a 4th provider adapter (Mistral, DeepSeek, or Cohere). ~50 LOC.

**Lab**: Add streaming markdown rendering to `agent.py` that re-renders the buffer on every text_delta (currently it just prints raw deltas).

---

<img align="right" src="assets/week7.png" width="180" alt="Week 7">

## Week 7 — Capstone: the climax + the website

**Read**: `agent.py` cover-to-cover. Then run `microsite/build_site.py` and watch your harness ship real software.

**Reading**: `agent.py` — every line. ~850 LOC. Cross-reference each section to the chapter that introduced its primitive.

**Final problem set**:
1. Find one bug in `agent.py` and submit a PR (we keep one bug live by design — the wishlist's "Plan mode" is a missing feature, not a bug; find a real one).
2. Use `agent.py` to build something *you* care about. Not a tetris demo. Something you actually want to exist.
3. Write a 500-word reflection: what does an agent harness still need that this repo doesn't have?

**Reading**: rasbt's [Build a Large Language Model (From Scratch)](https://github.com/rasbt/LLMs-from-scratch) — set the bar for what a textbook-as-repo looks like.

---

## Final exam questions (sample)

Try these without running code. Self-grade by reading the relevant chapters.

1. *(short)* What's the difference between `stop_reason` and `finish_reason`?
2. *(short)* Why must `tool_result` immediately follow `tool_use`?
3. *(short)* What is the minimum input length for prompt caching to engage on Sonnet 4.6?
4. *(short)* OpenAI's `tool_call.arguments` is what type?
5. *(short)* What is the canonical 6-line agent loop?
6. *(medium)* When would you use a subagent instead of compaction?
7. *(medium)* Why does Gemini lack a tool-use stop reason, and how do you detect a tool call without one?
8. *(medium)* The user's task takes 50 turns. Sketch the messages array length over time with and without compaction.
9. *(long)* Compare three ways to extend an agent harness: tools, skills, MCP. When is each correct?
10. *(long)* Design a "plan mode" for `agent.py`. Specify the tool subset, the system prompt, and the approval gate. ≤200 words.

---

## Grading (for self-paced learners)

- 40% problem sets (6 sets, ~80% completion)
- 20% lab work (build something real with each chapter)
- 20% capstone (your own thing using `agent.py`)
- 20% final exam (self-graded against `docs/EXAM_KEY.md`)

Pass: ≥70%. *Self-graded; no certificate. The skill is the certificate.*

---

## Adoption notes for instructors

If you teach this course at a university, a bootcamp, or a study group:

- All chapters are MIT-licensed; you may copy and adapt.
- Tests run in 0.6 seconds without API keys, so labs are CI-friendly.
- The `assets/launch.tape` script generates a clean classroom demo.
- A class of 25 students costs roughly $50 in API spend over 7 weeks (the speedrun is ~$0.50, the capstone is ~$5–$10).
- We recommend pairing the course with one Karpathy "Zero to Hero" lecture per week as background reading on neural networks themselves — agent-zero-to-hero is *complementary* to model-internals courses, not a replacement.

If you adopt this for a course, [open an issue](https://github.com/KeWang0622/agent-zero-to-hero/issues) and we'll add your school to the README.

"""
chapter 08c — prompt caching, the deep version

# This experiment teaches explicit prefix breakpoints. Current APIs also
# offer automatic caching; inspect usage instead of assuming a fixed saving.

before this chapter, ch08 mentioned caching in passing and ch08b showed the
meter. now we go deep.

three things you must know:

  1. THE THRESHOLD (varies by model).
     anthropic doesn't cache anything below a minimum input size:
       Sonnet 4.5 / 4 / 3.7    → 1,024 tokens
       Sonnet 4.6 (default)    → 1,024 tokens
       Opus 4.5 / 4.6          → 4,096 tokens
       Opus 4.7                → 2,048 tokens
       Haiku 4.5               → 4,096 tokens
       Haiku 3.5               → 2,048 tokens
     below the threshold, cache_control is silently ignored. cache_r stays 0.
     this is the #1 reason "i tried caching, didn't see savings."

  2. THE BREAKPOINTS.
     up to 4 cache_control markers per request. each marks the END of a
     cacheable prefix. anthropic caches the prefix; on the next call with the
     same prefix, those tokens cost ~10% of input price.
     order matters: tools → system → messages. cache the things that change LEAST.

  3. THE TTL.
     ephemeral cache lives ~5 minutes by default. for long-running daemons:
     cache_control={"type": "ephemeral", "ttl": "1h"} (1-hour TTL).
     5-min writes cost 1.25x input; 1-hour writes cost 2x input; reads 0.1x.
     break-even: ONE cache read pays back the 5-min write premium; TWO reads
     pay back the 1-hour premium (vs uncached). use 1-hour when reuse spans
     multiple 5-minute windows.

what you'll learn:
  - placing cache breakpoints on system, tools, and the conversation prefix
  - the 5-minute vs 1-hour TTL trade-off
  - measuring real savings from response.usage
  - when caching BACKFIRES (small prompts, frequently-changing system)

run:
  python -m chapters.ch08c_prompt_caching

next: ch09 — sessions on disk (jsonl + resume).
"""

import os
import sys
import time

from anthropic import Anthropic


client = Anthropic()
MODEL = "claude-sonnet-4-6"

# claude sonnet 4.6 prices, USD per 1M tokens (current 2026 — verify on
# https://www.anthropic.com/pricing). 4.6 has the same prices as 4.5.
P = {
    "input":          3.00,
    "output":        15.00,
    "cache_5m_w":     3.75,    # 5-min ephemeral writes (1.25x input)
    "cache_1h_w":     6.00,    # 1-hour writes (2x input)
    "cache_r":        0.30,    # reads — 0.1x input (90% cheaper)
}


# caching threshold is per-model:
#   Sonnet 4.5 / 4 / 3.7  → 1,024 tokens
#   Sonnet 4.6 (default)  → 1,024 tokens   ← what this file uses
#   Opus 4.5 / 4.6 / Haiku 4.5 → 4,096 tokens
#   Haiku 3.5             → 2,048 tokens
# real agents have AGENT.md, system + tool definitions, and skill catalogs
# that clear all of these naturally. for the demo, we pad with verbose
# conventions to clear Sonnet 4.6's 1,024-token threshold.
_RULES = [
    ("always read a file before editing it",
     "the Edit tool requires you to know the exact bytes you're replacing; "
     "without reading first you'll either fail to find old_string or guess "
     "wrong about indentation, line endings, and surrounding context"),
    ("never invent file paths — discover them via Glob or `ls`",
     "models are trained on common project structures and will hallucinate "
     "paths like 'src/main.py' even when the project's actual entry point is "
     "'app/index.ts'; always confirm what exists before referring to it"),
    ("for multi-step tasks (>2 steps), call TodoWrite first to plan",
     "explicit planning forces you to think before doing, reduces backtracking "
     "later in the conversation, and gives the user something to interrupt "
     "if your plan is wrong before you've burned tokens executing it"),
    ("prefer surgical Edits over wholesale Writes for existing files",
     "Edit is precise, auditable, and produces a unified diff the user can "
     "review; Write replaces everything and silently destroys content the "
     "model didn't know was there — comments, trailing newlines, modes"),
    ("verify your work after every action by running tests or reading output",
     "the model's claim 'I added a function' isn't proof; running pytest, "
     "reading the file back, or executing the script is proof — and your "
     "user expects the proof, not the claim"),
    ("tool errors must be returned as content with is_error=true",
     "raising an exception kills the agent loop and loses the session; "
     "returning the error string lets the model see what happened, apologize, "
     "and try a different approach on the next turn"),
    ("tool_result MUST immediately follow tool_use in the messages array",
     "the API rejects calls where an assistant tool_use is followed by "
     "another assistant turn or any user turn that lacks the matching "
     "tool_result block — this is the most-cited foot-gun in the SDK forum"),
    ("max_tokens is required on every Anthropic call (no default)",
     "OpenAI lets you omit it; Anthropic does not. forgetting raises "
     "TypeError before the request even hits the wire"),
    ("the messages array IS the memory — there is no hidden state",
     "the API is stateless; every call sends the entire history; you are the "
     "state-holder, not the model — this is the conceptual leap of agents"),
    ("stop_reasons: end_turn, tool_use, max_tokens, stop_sequence, refusal, pause_turn",
     "your loop's exit condition is data, not a heuristic; check stop_reason "
     "exhaustively or you'll silently misbehave on truncation and refusals"),
    ("compaction at 60% of context window, not at message count",
     "this demo chooses 60% as a heuristic to leave "
     "headroom for the summarizer call itself, which costs tokens too"),
    ("subagents isolate context; only the final text returns to the parent",
     "a 10-turn subagent costs the parent ~17 tokens of summary instead of "
     "17,000 tokens of intermediate state — the load-bearing trick of every "
     "production coding agent"),
    ("skills are markdown loaded on demand via a meta-tool, not eagerly",
     "the catalog (name + description) goes in the system prompt; the body "
     "(thousands of tokens of procedural knowledge) gets loaded only when the "
     "model decides it needs it — progressive disclosure"),
    ("our pinned 2024-11-05 MCP demo uses JSON-RPC 2.0 over stdio",
     "no SDK required — line-delimited JSON over pipes, three method calls "
     "(initialize, tools/list, tools/call); when you understand this, MCP "
     "stops being mysterious"),
    ("streaming text deltas render immediately; tool_use deltas accumulate",
     "input_json_delta events arrive as fragments of a JSON string; you "
     "CANNOT json.parse them mid-stream — accumulate into a buffer and parse "
     "after the stream ends and its stop reason is validated"),
    ("for parallel tool calls, batch ALL results into ONE user message",
     "the API and the model both observe whether tool_results are batched; "
     "splitting one tool_result per user message teaches the model that "
     "parallel calls are punished, and it stops issuing them silently"),
    ("OpenAI's tool_call.arguments is a JSON STRING — json.loads() it",
     "Anthropic returns input as a parsed object; OpenAI returns arguments "
     "as a string that needs explicit json.loads — forgetting this is the "
     "single most common bug when porting an Anthropic agent to OpenAI"),
    ("Gemini has no dedicated tool stop_reason; scan parts for functionCall",
     "OpenAI's finish_reason='tool_calls' and Anthropic's stop_reason='tool_use' "
     "tell you a tool was called; Gemini returns finishReason='STOP' even when "
     "the model emits a functionCall — detect by scanning parts"),
    ("rate-limit retries: full-jitter exponential backoff, capped at 30s",
     "fixed delay floods the queue; equal jitter still creates thundering "
     "herds; full jitter (delay = base * 2^attempt * random()) is the only "
     "scheme that smooths bursty client traffic to a nice flat curve"),
    ("session JSONL: append-only transcript, not transactional execution",
     "JSONL is the right serialization for sessions because every line is "
     "self-contained, though writes may tear; JSON often reads the file to "
     "append, and crash mid-write corrupts the array — JSONL crashes are local"),
    ("AGENT.md discovery: walk up from cwd, root-first, deepest-last",
     "this lets users override globally via ~/.agent-zero-to-hero/AGENT.md, project-wide "
     "via repo-root AGENT.md, and per-directory by dropping nested AGENT.md "
     "files — closest-wins shadowing matches every dev's intuition"),
    ("permissions: ask | allow | deny — gate all Write/Edit/Bash",
     "Read/Glob/Grep are observation; Write/Edit/Bash are action; the gate "
     "between them is where you defend against the agent doing something "
     "destructive on autopilot at 3am"),
    ("the loop is a structural pattern, not a model — six lines, forever",
     "a stronger model doesn't change the loop; a different provider doesn't "
     "change the loop; the loop is `while True { call → dispatch → continue }`, "
     "and once you can write it from memory you can read every coding agent's source"),
    ("compaction is surgery, not garbage collection",
     "you replace the older half of messages with one synthetic user message "
     "summarizing them; the model can't tell anything happened, the array "
     "shrinks 60x, and the loop continues — pure substitution"),
    ("subagents are agent loops with a fresh messages[], called as a tool",
     "the parent's context stays small because the subagent's exploration is "
     "INVISIBLE to the parent — only the final string returns; this is the "
     "load-bearing trick of every production coding agent"),
    ("MCP tools are routed by the mcp__server__name prefix",
     "the agent loop dispatches by the prefix in tool_use.name: anything "
     "starting with mcp__ goes to the matching MCPClient.call_tool, anything "
     "else hits the local handler dict — same loop, two routing paths"),
    ("streaming protocol uses 6 SSE events plus ping and error",
     "message_start / content_block_start / content_block_delta / "
     "content_block_stop / message_delta / message_stop are the data events; "
     "ping is a keepalive between them; error is a server-side problem"),
    ("AGENT.md content + system + tool definitions = the cacheable prefix",
     "real production agents have AGENT.md (~3KB), a system prompt (~1KB), "
     "and 5-10 tool definitions (~1.5KB) — totaling ~5KB which clears every "
     "current model's caching threshold; the demo here just emulates it"),
    ("descriptions are load-bearing — the model picks tools by reading them",
     "a tool with description 'Helps with code' will be ignored; the same tool "
     "with 'Debug N+1 queries — use when user mentions slow page loads' will "
     "be picked reliably; you spend more time on descriptions than on the loop"),
    ("forward-compat: handle unknown stop_reasons and unknown SSE events",
     "anthropic adds new values over time (model_context_window_exceeded was "
     "added in Sonnet 4.5; thinking_delta arrived with extended thinking); "
     "your code should log+continue on unknowns, not raise"),
]

LONG_SYSTEM = (
    "You are agent-zero-to-hero, a careful coding agent. Be precise and terse.\n"
    "You have a calculator tool. Use it for any arithmetic. Show your work.\n\n"
    "Detailed conventions (long enough to clear Sonnet 4.6's 1,024-token threshold):\n\n"
    + "\n\n".join(f"  rule {i}: {short}\n    why: {long}"
                  for i, (short, long) in enumerate(_RULES))
).strip()


TOOLS = [
    {"name": "calculator",
     "description": "Evaluate a math expression like '17 * 23'.",
     "input_schema": {"type": "object",
                      "properties": {"expression": {"type": "string"}},
                      "required": ["expression"]}},
]


# ----- demo helpers ------------------------------------------------------

def call(system, prompt, *, label):
    """One non-tool-using call. Print usage and dollar cost."""
    r = client.messages.create(
        model=MODEL, max_tokens=200,
        system=system, messages=[{"role": "user", "content": prompt}],
    )
    u = r.usage
    cw_5m = getattr(u, "cache_creation_input_tokens", 0) or 0
    cr    = getattr(u, "cache_read_input_tokens", 0) or 0
    cost  = (u.input_tokens   * P["input"]
             + u.output_tokens * P["output"]
             + cw_5m            * P["cache_5m_w"]
             + cr               * P["cache_r"]) / 1_000_000
    print(f"  {label:<28} in={u.input_tokens:>4}  cw={cw_5m:>4}  cr={cr:>4}  "
          f"out={u.output_tokens:>4}  ${cost:.4f}")


# ----- demo 1: no caching vs caching the system prompt -------------------

def demo_basic():
    print("\n=== 1. caching the system prompt ===\n")

    # a) no caching at all
    call(LONG_SYSTEM, "what is 2+2?",       label="run 1, no cache:")
    call(LONG_SYSTEM, "what is 3+3?",       label="run 2, no cache:")

    # b) caching the system prompt — array form with cache_control
    cached_system = [
        {"type": "text", "text": LONG_SYSTEM,
         "cache_control": {"type": "ephemeral"}},
    ]
    print()
    call(cached_system, "what is 4+4?",     label="run 3, cached (cold):")
    call(cached_system, "what is 5+5?",     label="run 4, cached (warm):")
    call(cached_system, "what is 6+6?",     label="run 5, cached (warm):")
    print("\n→ runs 4-5 should show non-zero `cr` (cache_read).")
    print("  the system prompt is cached for ~5 minutes after run 3.")


# ----- demo 2: 5-minute vs 1-hour TTL ------------------------------------

def demo_ttl():
    print("\n=== 2. 5-minute vs 1-hour TTL ===\n")
    # 1-hour TTL costs 2x input to write (vs 1.25x for 5-min) but lasts 12x longer.
    # break-even: ONE cache read for 5-min vs uncached; TWO cache reads for 1-hour.
    # use 1-hour when reuse spans multiple 5-minute windows (e.g. long sessions).
    one_hour_system = [
        {"type": "text", "text": LONG_SYSTEM,
         "cache_control": {"type": "ephemeral", "ttl": "1h"}},
    ]
    call(one_hour_system, "what is 10*10?",  label="1h TTL, cold:")
    call(one_hour_system, "what is 11*11?",  label="1h TTL, warm:")
    print("\n→ 1h TTL writes cost 2x more (cw is at the higher price tier),")
    print("  but the cache survives the 5-min default expiry. use for daemons.")


# ----- demo 3: caching tools, not just system ----------------------------

def demo_tools():
    print("\n=== 3. caching tools (the second-biggest lever) ===\n")
    # tool definitions are sent on every turn. a real agent ships 5-10 tools
    # with ~150 tokens of schema each = 1500 tokens. cache them.
    cached_tools = [
        # mark the LAST tool as a cache breakpoint — anthropic caches the
        # entire tools list up to and including this marker.
        {**TOOLS[0], "cache_control": {"type": "ephemeral"}},
    ]
    cached_system = [
        {"type": "text", "text": LONG_SYSTEM,
         "cache_control": {"type": "ephemeral"}},
    ]

    # cold call (writes both)
    r1 = client.messages.create(
        model=MODEL, max_tokens=100,
        system=cached_system, tools=cached_tools,
        messages=[{"role": "user", "content": "what is 7*7?"}])
    print(f"  cold:  cw={r1.usage.cache_creation_input_tokens}  "
          f"cr={r1.usage.cache_read_input_tokens}")

    # warm call (reads both)
    r2 = client.messages.create(
        model=MODEL, max_tokens=100,
        system=cached_system, tools=cached_tools,
        messages=[{"role": "user", "content": "what is 8*8?"}])
    print(f"  warm:  cw={r2.usage.cache_creation_input_tokens}  "
          f"cr={r2.usage.cache_read_input_tokens}")
    print("\n→ both system AND tools cached. on a real agent with 10 tools,")
    print("  this saves ~1500 tokens at cache_r price every turn.")


# ----- demo 4: when caching BACKFIRES ------------------------------------

def demo_backfire():
    print("\n=== 4. when caching BACKFIRES ===\n")
    print("scenario A: system below the model's threshold (2,048 for Sonnet 4.6) — silent no-op.")
    short = [
        {"type": "text", "text": "you are a calculator.",
         "cache_control": {"type": "ephemeral"}},
    ]
    call(short, "what is 2+2?", label="short system, attempt 1:")
    call(short, "what is 3+3?", label="short system, attempt 2:")
    print("→ cw and cr both stay 0. caching simply doesn't engage. add tokens.")

    print("\nscenario B: system that CHANGES every call — pure cost.")
    print("→ if your system prompt embeds the timestamp or a request-id, you")
    print("  pay the WRITE price (1.25x) every time AND never read. don't cache")
    print("  things that change. cache the stable prefix; vary at the end.")


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("set ANTHROPIC_API_KEY first")

    demo_basic()
    print("\n[wait 1s for cache to warm...]")
    time.sleep(1)
    demo_ttl()
    demo_tools()
    demo_backfire()

    print("\n=== takeaways ===")
    print("  1. minimum cacheable prompt size depends on the model:")
    print("       Sonnet 4.5 / 4 / 3.7    → 1,024 tokens")
    print("       Sonnet 4.6              → 2,048 tokens")
    print("       Opus 4.5+ · Haiku 4.5   → 4,096 tokens")
    print("       Haiku 3.5               → 2,048 tokens")
    print("     below the threshold, cache_control is silently ignored.")
    print("  2. cache_control on the LAST item of system/tools you want stable.")
    print("  3. 5-min cache writes 1.25x; 1-hour writes 2x; reads 0.1x of input.")
    print("  4. break-even: ONE read for 5-min cache vs uncached;")
    print("     TWO reads for 1-hour cache vs uncached.")
    print("  5. cache things that DON'T change. system + tools + AGENT.md = yes.")
    print("     timestamps, request-ids, user-specific data = no.")
    print("  6. agent.py turns this on by default. AZH_NO_CACHE=1 to disable.")


if __name__ == "__main__":
    main()

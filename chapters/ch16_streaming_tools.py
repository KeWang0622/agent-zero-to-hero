"""
chapter 16 — streaming tool_use (the hard chapter)

# Text deltas you render. Tool_use deltas you accumulate. Don't mix them up.

text streaming is easy: each `text_delta` is a string, just print it.
tool_use streaming is HARD: each `input_json_delta` is a fragment of a JSON
string, accumulating into the final tool input. you cannot json.parse it
mid-stream — `'{"expr'` and `'ession":"1+'` and `'1"}'` are not parseable
on their own.

the rule:
  TEXT deltas      → render immediately
  TOOL_USE deltas  → ACCUMULATE, check the final stop_reason, then parse

a content_block_stop closes a block; it does not prove the response finished
successfully. truncated tool arguments must never become executable input.

events for a streamed tool_use block:
  content_block_start  { "content_block": { "type": "tool_use", "name": ..., "id": ... } }
  content_block_delta  { "delta": { "type": "input_json_delta", "partial_json": "{\"expr" } }
  content_block_delta  { "delta": { "type": "input_json_delta", "partial_json": "ession\":\"1+" } }
  content_block_delta  { "delta": { "type": "input_json_delta", "partial_json": "1\"}" } }
  content_block_stop                                      ← keep the buffer
  message_delta { "delta": { "stop_reason": "tool_use" } } ← check before parsing
  message_stop                                           ← validate the whole batch

run:
  python -m chapters.ch16_streaming_tools "what is 999 * 999?"

next: ch17 — multi-provider (Anthropic / OpenAI / Gemini).
"""

import json
import os
import subprocess
import sys

from anthropic import Anthropic


client = Anthropic()
MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "calculator",
        "description": "Evaluate a python math expression.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"cmd": {"type": "string"}},
            "required": ["cmd"],
        },
    },
]


def run_tool(name: str, inp: dict) -> str:
    if name == "calculator":
        return str(eval(inp["expression"], {"__builtins__": {}}))
    if name == "bash":
        out = subprocess.run(inp["cmd"], shell=True, capture_output=True, text=True, timeout=10)
        return (out.stdout + out.stderr)[:4000] or "(no output)"
    return f"unknown tool: {name}"


def finish_blocks(blocks, stop_reason):
    """Validate every call before any call can enter history or execute."""
    if stop_reason in {"max_tokens", "model_context_window_exceeded"}:
        raise RuntimeError(f"response truncated ({stop_reason}); no tools executed")
    if stop_reason not in {"end_turn", "stop_sequence", "tool_use"}:
        raise RuntimeError(f"unexpected stop_reason: {stop_reason!r}")
    calls = [b for b in blocks if b["type"] == "tool_use"]
    if bool(calls) != (stop_reason == "tool_use"):
        raise RuntimeError("tool_use blocks and stop_reason disagree")
    for block in calls:
        try:
            block["input"] = json.loads(block.pop("_partial_json") or "{}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"invalid JSON for tool {block['name']}; no tools executed") from e
        if not isinstance(block["input"], dict):
            raise RuntimeError(f"tool {block['name']} input must be a JSON object")
    return blocks


def stream_one_turn(messages: list[dict]) -> tuple[list[dict], str]:
    """
    Stream a single turn. Returns (assistant_content_blocks, stop_reason).
    Renders text as it arrives. Accumulates tool_use input. Reconstructs the
    same content[] shape that the non-streaming SDK would have returned, so
    we can append it to messages and pass it back next turn.
    """
    blocks_in_progress: dict[int, dict] = {}     # index -> partial block
    stop_reason = None

    with client.messages.stream(
        model=MODEL,
        max_tokens=2048,
        tools=TOOLS,
        messages=messages,
    ) as stream:
        for event in stream:
            t = event.type

            if t == "content_block_start":
                cb = event.content_block
                if cb.type == "text":
                    blocks_in_progress[event.index] = {"type": "text", "text": ""}
                elif cb.type == "tool_use":
                    blocks_in_progress[event.index] = {
                        "type": "tool_use",
                        "id": cb.id,
                        "name": cb.name,
                        "_partial_json": "",                 # we accumulate here
                    }

            elif t == "content_block_delta":
                d = event.delta
                blk = blocks_in_progress[event.index]
                if d.type == "text_delta":
                    print(d.text, end="", flush=True)        # safe: render now
                    blk["text"] += d.text
                elif d.type == "input_json_delta":
                    # NEVER json.parse this fragment. just accumulate.
                    blk["_partial_json"] += d.partial_json

            elif t == "content_block_stop":
                pass  # message_delta with the final stop_reason has not arrived yet.

            elif t == "message_delta":
                stop_reason = event.delta.stop_reason

            elif t == "message_stop":
                pass

    # reassemble blocks in order — the API expects them in original index order.
    blocks = [blocks_in_progress[i] for i in sorted(blocks_in_progress)]
    finish_blocks(blocks, stop_reason)
    for block in blocks:
        if block["type"] == "tool_use":
            print(f"\n  [tool_use] {block['name']}({block['input']})")
    return blocks, stop_reason


def agent_loop(prompt: str):
    messages = [{"role": "user", "content": prompt}]

    for step in range(20):
        print()
        blocks, stop = stream_one_turn(messages)
        messages.append({"role": "assistant", "content": blocks})

        if stop in {"end_turn", "stop_sequence"}:
            print()
            return

        if stop == "tool_use":
            results = []
            for blk in blocks:
                if blk["type"] == "tool_use":
                    out = run_tool(blk["name"], blk["input"])
                    print(f"  [tool_result] {out[:140]}{'...' if len(out) > 140 else ''}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": blk["id"],
                        "content": out,
                    })
            messages.append({"role": "user", "content": results})
            continue

        raise RuntimeError(f"unexpected stop_reason: {stop}")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("set ANTHROPIC_API_KEY first")
    prompt = " ".join(sys.argv[1:]) or "what's 1234 * 5678, then tell me a one-line joke about it?"
    agent_loop(prompt)

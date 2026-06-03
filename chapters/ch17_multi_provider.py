"""
chapter 17 — same loop, three wires (Anthropic / OpenAI / Gemini)

# The agent loop is universal. The wire format is provider-specific.
# A 30-line adapter is the difference.

we've used Anthropic everywhere because its tool-use shape is the cleanest
expression of agent concepts. but every primitive maps to OpenAI and Gemini.
this chapter ports the calculator agent of ch04 to all three, behind ONE
adapter interface, with ONE shared loop.

the differences (which the adapter hides):

  field           | anthropic     | openai         | gemini
  ----------------+---------------+----------------+--------------------
  system          | top-level     | role:"developer"| system_instruction
                  |               | (was "system") |
  tool schema     | input_schema  | parameters     | parameters (OpenAPI)
  tool result     | user msg w/   | role:"tool"    | functionResponse
                  | tool_result   | + tool_call_id |   part
  args type       | parsed object | JSON STRING    | parsed object
  stop on tool    | "tool_use"    | "tool_calls"   | scan parts (no flag)
  asst role       | "assistant"   | "assistant"    | "model" (NOT "assistant")

what you'll learn:
  - the Provider protocol (one interface, three impls)
  - normalizing to a common AgentMessage / ToolCall shape
  - the *one* loop that runs against any provider

run:
  export ANTHROPIC_API_KEY=...
  export OPENAI_API_KEY=...           # optional: skipped if missing
  export GOOGLE_API_KEY=...           # optional: skipped if missing
  python -m chapters.ch17_multi_provider

next: agent.py at repo root — the Claude Code clone.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx


# --- the common shapes ---------------------------------------------------

@dataclass
class ToolCall:
    id: str
    name: str
    args: dict                          # always parsed dict, never string


@dataclass
class AgentMessage:
    role: str                           # "user" | "assistant" | "tool"
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""              # for role="tool"
    stop: str = ""                      # normalized: "end" | "tool_use" | "max_tokens"


class Provider(Protocol):
    def complete(self, messages: list[AgentMessage], tools: list[dict],
                 system: str) -> AgentMessage: ...


# --- Anthropic ----------------------------------------------------------

class AnthropicProvider:
    def __init__(self, model="claude-sonnet-4-6"):
        self.model = model

    def complete(self, messages, tools, system):
        body = {
            "model": self.model, "max_tokens": 1024, "system": system,
            "messages": [self._msg(m) for m in messages],
            "tools": [{"name": t["name"], "description": t["description"],
                       "input_schema": t["parameters"]} for t in tools],
        }
        r = httpx.post(
            "https://api.anthropic.com/v1/messages", json=body, timeout=60,
            headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                     "anthropic-version": "2023-06-01"},
        ).json()
        return self._parse(r)

    @staticmethod
    def _msg(m: AgentMessage) -> dict:
        if m.role == "tool":
            return {"role": "user", "content": [{"type": "tool_result",
                    "tool_use_id": m.tool_call_id, "content": m.text}]}
        if m.role == "assistant" and m.tool_calls:
            blocks = [{"type": "text", "text": m.text}] if m.text else []
            blocks += [{"type": "tool_use", "id": tc.id,
                        "name": tc.name, "input": tc.args} for tc in m.tool_calls]
            return {"role": "assistant", "content": blocks}
        return {"role": m.role, "content": m.text}

    @staticmethod
    def _parse(r: dict) -> AgentMessage:
        text = "".join(b["text"] for b in r["content"] if b["type"] == "text")
        calls = [ToolCall(b["id"], b["name"], b["input"])
                 for b in r["content"] if b["type"] == "tool_use"]
        stop = "tool_use" if r["stop_reason"] == "tool_use" else "end"
        return AgentMessage("assistant", text=text, tool_calls=calls, stop=stop)


# --- OpenAI -------------------------------------------------------------

class OpenAIProvider:
    def __init__(self, model="gpt-5-mini"):                 # gpt-4o-mini deprecated
        self.model = model

    def complete(self, messages, tools, system):
        # Chat Completions: "system" still works for back-compat. New code on
        # o-series / GPT-5+ should prefer "developer". Both are accepted today.
        msgs = [{"role": "system", "content": system}]
        for m in messages:
            msgs.append(self._msg(m))
        body = {"model": self.model, "messages": msgs,
                "tools": [{"type": "function", "function": t} for t in tools]}
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions", json=body, timeout=60,
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        ).json()
        return self._parse(r)

    @staticmethod
    def _msg(m: AgentMessage) -> dict:
        if m.role == "tool":
            return {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.text}
        if m.role == "assistant" and m.tool_calls:
            return {"role": "assistant", "content": m.text or None,
                    "tool_calls": [{"id": tc.id, "type": "function",
                                    "function": {"name": tc.name,
                                                 "arguments": json.dumps(tc.args)}}
                                   for tc in m.tool_calls]}
        return {"role": m.role, "content": m.text}

    @staticmethod
    def _parse(r: dict) -> AgentMessage:
        choice = r["choices"][0]
        msg = choice["message"]
        text = msg.get("content") or ""
        calls = []
        for tc in msg.get("tool_calls") or []:
            # OPENAI FOOT-GUN: arguments is a JSON STRING, not parsed.
            args = json.loads(tc["function"]["arguments"] or "{}")
            calls.append(ToolCall(tc["id"], tc["function"]["name"], args))
        stop = "tool_use" if choice["finish_reason"] == "tool_calls" else "end"
        return AgentMessage("assistant", text=text, tool_calls=calls, stop=stop)


# --- Gemini -------------------------------------------------------------

class GeminiProvider:
    def __init__(self, model="gemini-2.5-flash"):            # 2.0-flash-exp deprecated June 2026
        self.model = model

    def complete(self, messages, tools, system):
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [self._msg(m) for m in messages],
            "tools": [{"function_declarations": tools}],
        }
        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{self.model}:generateContent")
        r = httpx.post(url, json=body, timeout=60,
                       headers={"x-goog-api-key": os.environ["GOOGLE_API_KEY"]}).json()
        return self._parse(r)

    @staticmethod
    def _msg(m: AgentMessage) -> dict:
        if m.role == "tool":
            return {"role": "user", "parts": [{"functionResponse": {
                "name": m.tool_call_id.split(":", 1)[0],
                "response": {"result": m.text}}}]}
        if m.role == "assistant":
            parts = [{"text": m.text}] if m.text else []
            for tc in m.tool_calls:
                parts.append({"functionCall": {"name": tc.name, "args": tc.args}})
            return {"role": "model", "parts": parts}
        return {"role": "user", "parts": [{"text": m.text}]}

    @staticmethod
    def _parse(r: dict) -> AgentMessage:
        cand = r["candidates"][0]
        text, calls = "", []
        for part in cand["content"]["parts"]:
            if "text" in part:
                text += part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                # GEMINI FOOT-GUN: no dedicated stop reason; presence of
                # functionCall part tells you a tool was called.
                calls.append(ToolCall(f"{fc['name']}:0", fc["name"],
                                      fc.get("args", {})))
        stop = "tool_use" if calls else "end"
        return AgentMessage("assistant", text=text, tool_calls=calls, stop=stop)


# --- the universal loop -------------------------------------------------

def run_agent(provider: Provider, system: str, prompt: str,
              tools_meta: list[dict], dispatch) -> str:
    messages = [AgentMessage("user", text=prompt)]
    for _ in range(10):
        resp = provider.complete(messages, tools_meta, system)
        messages.append(resp)
        if resp.stop != "tool_use":
            return resp.text
        for tc in resp.tool_calls:
            try:
                result = dispatch(tc.name, tc.args)
            except Exception as e:
                result = f"ERROR: {e}"
            messages.append(AgentMessage("tool", text=result, tool_call_id=tc.id))
    return "(max turns reached)"


# --- the demo: same task, three providers -------------------------------

TOOLS_META = [{
    "name": "calculator",
    "description": "Evaluate a math expression like '2 + 3 * 4'.",
    "parameters": {"type": "object",
                   "properties": {"expression": {"type": "string"}},
                   "required": ["expression"]},
}]


def dispatch(name, args):
    if name == "calculator":
        return str(eval(args["expression"], {"__builtins__": {}}))
    return f"unknown tool: {name}"


def benchmark(label: str, p: Provider):
    t0 = time.time()
    answer = run_agent(p, "You are a careful arithmetic agent. Use the calculator.",
                       "what is 17 * 23, then add 100, then divide by 7?",
                       TOOLS_META, dispatch)
    print(f"\n=== {label} ({time.time() - t0:.1f}s) ===")
    print(answer[:300])


def main():
    if "ANTHROPIC_API_KEY" in os.environ:
        benchmark("Anthropic", AnthropicProvider())
    if "OPENAI_API_KEY" in os.environ:
        benchmark("OpenAI", OpenAIProvider())
    if "GOOGLE_API_KEY" in os.environ:
        benchmark("Gemini", GeminiProvider())


if __name__ == "__main__":
    main()

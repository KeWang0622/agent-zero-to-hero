"""
chapter 14 — wire MCP into the agent loop

# An MCP tool is just a remote function. Convert its schema to Anthropic's
# tool format. Convert tool_use calls back into tools/call. That's it.

now we put MCP behind the agent loop. claude doesn't need to know which tools
are local and which come from a child process — they all look like tools to it.

  ┌──────────────┐    tool_use blocks    ┌────────────────────┐
  │   claude     │ ─────────────────────►│   agent loop       │
  │              │                       │                    │
  │              │◄───── tool_results ───│  routes tool calls:│
  └──────────────┘                       │  - local: run fn   │
                                         │  - mcp:   forward  │
                                         └─────────┬──────────┘
                                                   │ tools/call
                                                   ▼
                                         ┌────────────────────┐
                                         │  MCP server (proc) │
                                         └────────────────────┘

what you'll learn:
  - converting MCP tool schemas → Anthropic tool format
  - routing tool_use to local OR MCP based on a prefix (`mcp__server__name`)
  - proper lifecycle: spawn on start, terminate on exit

run:
  python -m chapters.ch14_mcp_agent "what is (17 * 23) + 1234?"

next: ch15 — streaming text (engineering territory).
"""

import os
import sys
from pathlib import Path

from anthropic import Anthropic

# we reuse the wire-level client from ch13.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ch13_mcp_wire import MCPProcess


client = Anthropic()
MODEL = "claude-sonnet-4-6"
SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp_servers" / "calculator_server.py"


class MCPClient:
    """Higher-level wrapper: spawn server, list tools, expose `call_tool`."""

    def __init__(self, server_id: str, command: list[str]):
        self.server_id = server_id
        self.proc = MCPProcess(command)
        self._initialized = False
        self.tools: list[dict] = []                  # MCP-format tool schemas

    def initialize(self):
        self.proc.call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "agent-zero-to-hero", "version": "0.1.0"},
        })
        self.proc.notify("notifications/initialized")
        self.tools = self.proc.call("tools/list")["tools"]
        self._initialized = True

    def call_tool(self, name: str, args: dict) -> str:
        result = self.proc.call("tools/call", {"name": name, "arguments": args})
        # flatten content blocks to a string for the agent loop.
        out = "\n".join(b["text"] for b in result.get("content", [])
                        if b.get("type") == "text")
        if result.get("isError"):
            out = f"ERROR: {out}"
        return out

    def close(self):
        self.proc.close()


def to_anthropic_tool(server_id: str, mcp_tool: dict) -> dict:
    """MCP's {name, description, inputSchema} → Anthropic's {name, description, input_schema}.
    namespace tool names so claude can route locally: mcp__<server>__<tool>."""
    return {
        "name": f"mcp__{server_id}__{mcp_tool['name']}",
        "description": f"[{server_id}] {mcp_tool['description']}",
        "input_schema": mcp_tool["inputSchema"],
    }


def agent_loop(prompt: str, mcp_clients: dict[str, MCPClient]):
    # build claude's tool list from all MCP servers.
    tools = []
    for sid, c in mcp_clients.items():
        tools.extend(to_anthropic_tool(sid, t) for t in c.tools)
    print(f"[loaded {len(tools)} tools from {len(mcp_clients)} MCP servers]")

    msgs = [{"role": "user", "content": prompt}]

    for turn in range(15):
        r = client.messages.create(model=MODEL, max_tokens=2048,
                                   tools=tools, messages=msgs)
        msgs.append({"role": "assistant", "content": r.content})

        for b in r.content:
            if b.type == "text" and b.text.strip():
                print(f"\nclaude> {b.text}")

        if r.stop_reason != "tool_use":
            return

        results = []
        for b in r.content:
            if b.type == "tool_use":
                # demangle: "mcp__calc__calculator" -> server="calc", tool="calculator"
                if b.name.startswith("mcp__"):
                    _, server_id, tool_name = b.name.split("__", 2)
                    out = mcp_clients[server_id].call_tool(tool_name, b.input)
                    print(f"  [mcp:{server_id}] {tool_name}({b.input}) -> {out}")
                else:
                    out = f"unknown local tool: {b.name}"
                results.append({"type": "tool_result",
                                "tool_use_id": b.id, "content": out})
        msgs.append({"role": "user", "content": results})


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("set ANTHROPIC_API_KEY first")

    # spawn one MCP server (more would just be more entries in this dict).
    calc = MCPClient("calc", [sys.executable, str(SERVER_PATH)])
    calc.initialize()

    try:
        prompt = " ".join(sys.argv[1:]) or "what is (17 * 23) + 1234?"
        agent_loop(prompt, {"calc": calc})
    finally:
        calc.close()


if __name__ == "__main__":
    main()

"""
chapter 13 — MCP, demystified: it's just JSON-RPC over stdio

# MCP is "USB-C for AI" if you're selling it. From the wire, it's three things:
#   - a child process
#   - line-delimited JSON-RPC 2.0
#   - three method calls: initialize, tools/list, tools/call

before you write a client (ch14), see the protocol with your own eyes. this
chapter spawns an MCP server (the calculator one we ship in mcp_servers/),
sends three raw JSON-RPC messages over stdin/stdout, and prints what comes
back. no SDK. no abstractions. just bytes.

  ┌──────────────┐                          ┌──────────────────┐
  │ your client  │  stdin (one JSON/line)   │   MCP server     │
  │  (this file) │ ────────────────────►    │ (a child process)│
  │              │  stdout (one JSON/line)  │                  │
  │              │ ◄────────────────────    │                  │
  └──────────────┘                          └──────────────────┘

the three calls:

  1. initialize      — handshake. exchange protocol versions, capabilities.
  2. tools/list      — "what tools do you have?" returns array of {name, schema}.
  3. tools/call      — "run this tool with these args." returns content.

after this chapter you will never wonder what MCP "is" again.

run:
  python -m chapters.ch13_mcp_wire

next: ch14 — wire it into the agent loop, write your own server.
"""

import json
import subprocess
import sys
from pathlib import Path


SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp_servers" / "calculator_server.py"


class MCPProcess:
    """A child process speaking JSON-RPC 2.0 over stdin/stdout."""

    def __init__(self, server_cmd: list[str]):
        # spawn the server. text mode + line-buffered = we can read line by line.
        self.proc = subprocess.Popen(
            server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,        # show server logs to us
            text=True,
            bufsize=1,                # line-buffered
        )
        self.next_id = 1

    def call(self, method: str, params: dict | None = None) -> dict:
        """Send one JSON-RPC request, wait for one JSON-RPC response."""
        request = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            request["params"] = params
        self.next_id += 1

        # outgoing: one json object, one newline. that's the framing.
        line = json.dumps(request) + "\n"
        print(f"  → {line.rstrip()}")
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

        # incoming: read lines until we find a response with our id.
        # (servers can also send notifications — those have no id.)
        while True:
            raw = self.proc.stdout.readline()
            if not raw:
                raise RuntimeError("server died")
            print(f"  ← {raw.rstrip()}")
            msg = json.loads(raw)
            if "id" in msg and msg["id"] == request["id"]:
                if "error" in msg:
                    raise RuntimeError(f"MCP error: {msg['error']}")
                return msg["result"]

    def notify(self, method: str, params: dict | None = None):
        """Send a notification (no response expected)."""
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        line = json.dumps(msg) + "\n"
        print(f"  → {line.rstrip()}  (notification)")
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=3)


def main():
    if not SERVER_PATH.exists():
        sys.exit(f"server not found at {SERVER_PATH}")

    print(f"spawning: python {SERVER_PATH}")
    mcp = MCPProcess([sys.executable, str(SERVER_PATH)])

    try:
        # 1. initialize handshake. tells the server who we are, gets back its
        #    capabilities and protocol version.
        print("\n--- 1. initialize ---")
        init_result = mcp.call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "agent-zero-to-hero", "version": "0.1.0"},
        })
        print(f"  server: {init_result['serverInfo']}")
        print(f"  capabilities: {init_result.get('capabilities')}")

        # 2. spec requires us to send `notifications/initialized` after init.
        mcp.notify("notifications/initialized")

        # 3. tools/list — "what can you do?"
        print("\n--- 2. tools/list ---")
        tools_result = mcp.call("tools/list")
        for t in tools_result["tools"]:
            print(f"  • {t['name']}: {t['description']}")

        # 4. tools/call — "run this one"
        print("\n--- 3. tools/call calculator(2 + 3 * 4) ---")
        call_result = mcp.call("tools/call", {
            "name": "calculator",
            "arguments": {"expression": "2 + 3 * 4"},
        })
        # results come back as content blocks (mirrors anthropic's design).
        for block in call_result["content"]:
            if block["type"] == "text":
                print(f"  result: {block['text']}")

    finally:
        mcp.close()
        print("\n[server closed]")


if __name__ == "__main__":
    main()

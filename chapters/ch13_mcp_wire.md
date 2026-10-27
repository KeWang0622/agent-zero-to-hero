# Chapter 13 — MCP Demystified 🐢

<p align="center">
  <img src="../assets/ch13-illustration.png" alt="MCP demystified" width="100%">
</p>

> **Inspect a small MCP tools conversation, one JSON-RPC message at a time.**

## 🐢 GuiGui says

This lab makes a process boundary visible: Python launches the bundled calculator server, lists its tools, and calls one. You can understand every byte without an SDK.

**Version scope:** the runnable client and server are a teaching subset pinned to **`2024-11-05`**, using local **stdio**. They do not implement the full protocol or the current lifecycle. As checked on **2026-10-26**, the current stable revision is [**`2026-07-28`**](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28). See [MCP versions and migration](../docs/MCP_VERSIONS.md) before connecting another implementation.

## The three requests in this lab

```text
client                                    server (child process)
  │                                          │
  ├── 1. initialize (2024-11-05) ───────────▶ │
  │◀────── { protocolVersion, capabilities }─┤
  ├── notifications/initialized ────────────▶│
  │                                          │
  ├── 2. tools/list ────────────────────────▶│
  │◀─────── { tools: [...] } ────────────────┤
  │                                          │
  ├── 3. tools/call ────────────────────────▶│
  │◀─────── { content: [...], isError } ─────┤
```

There are three request/response pairs **plus a notification**, which has no response. This is the [historical initialization flow](https://modelcontextprotocol.io/specification/2024-11-05/basic/lifecycle). The sample only exercises tools; MCP also specifies other capabilities and transports.

In this stdio binding, each JSON-RPC message occupies one line. `stdin` and `stdout` carry protocol messages; diagnostics belong on `stderr`.

## Show me the code

The essential request framing from [`ch13_mcp_wire.py`](ch13_mcp_wire.py) is:

```python
request = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
if params is not None:
    request["params"] = params
self.next_id += 1
self.proc.stdin.write(json.dumps(request) + "\n")
self.proc.stdin.flush()
```

The client reads until it finds the response with that request ID. A JSON-RPC `error` becomes a Python exception. A successful `tools/call` response may still report a tool execution failure through `isError`; these are different error layers. The [2024 tools specification](https://modelcontextprotocol.io/specification/2024-11-05/server/tools) explains the tool result format.

## What changed since this example?

The `2026-07-28` revision removes `initialize` and `notifications/initialized`. Requests declare their version and client capabilities through `_meta`; servers implement `server/discover` for optional up-front discovery. The current revision also changes result and remote transport semantics. Those changes apply to the protocol, including stdio—not only to HTTP. [Current versioning](https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning) describes compatibility handling.

Changing the version string in this file would leave the old messages in place. Keep the lab pinned until you implement and test the corresponding lifecycle.

## ⚠️ Watch out for

- **A teaching client has limits.** This one is synchronous, ignores unmatched messages, and does not implement a general server-request dispatcher, pagination, version rejection, or a read timeout. A server that remains alive but stops replying can block it.
- **Cleanup is incomplete for hostile or hung processes.** The example closes stdin and waits briefly. A more robust client needs a termination fallback and cleanup after initialization failure.
- **Local execution uses your process permissions.** Review the bundled server and run experiments in a disposable environment. Its arithmetic implementation is a teaching fixture, not a general untrusted-input service. Do not expose it on a network or assume a desktop client makes it safe.

## ✅ Summary

- This lab demonstrates a historical local stdio **tools subset**.
- Request IDs connect replies to requests; notifications have no reply.
- The loop can consume MCP results through an adapter.
- Protocol version, transport, supported features, and safety policy must all be explicit.

## 📝 Homework

```bash
python -m chapters.ch13_mcp_wire
```

1. Match each request ID to its response and identify the notification. This lab needs no model API key.
2. Inspect the returned version and capabilities. Explain what a client should do if the server returns a version it cannot support; the bundled client does not enforce that check.
3. Write a second local tool using fixed fixture data. Keep both endpoints on the same documented protocol subset.
4. Complete the [compatibility exercise](../docs/MCP_VERSIONS.md#compatibility-exercise) before attempting a third-party client. Record its supported version and observed behavior instead of assuming compatibility from the label “MCP.”

## 📚 References

- [MCP 2024-11-05 lifecycle](https://modelcontextprotocol.io/specification/2024-11-05/basic/lifecycle) — the lab's historical handshake
- [MCP 2024-11-05 tools](https://modelcontextprotocol.io/specification/2024-11-05/server/tools) — discovery and tool results
- [MCP 2026-07-28 release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28) — current stable revision at review time
- [MCP 2026-07-28 changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog) — migration details
- [Official Python SDK](https://github.com/modelcontextprotocol/python-sdk) — an implementation to compare after learning the wire

## 🚀 Next

[Chapter 14 — MCP into the loop](ch14_mcp_agent.md): adapt this local tools subset for a model.

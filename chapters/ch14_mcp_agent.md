# Chapter 14 — Wire MCP Into the Agent Loop 🐢

> **Expose a server's tools to the model, then route its calls through an adapter.**

## 🐢 GuiGui says

[Chapter 13](ch13_mcp_wire.md) showed a local process conversation. Now the model sees tool definitions, and the harness decides where each call goes.

**This runnable chapter reuses the `2024-11-05` stdio teaching client and calculator server.** It is not a general MCP client or an implementation of the current `2026-07-28` lifecycle. Read [MCP versions and migration](../docs/MCP_VERSIONS.md) for that distinction.

## The translation

| Model-facing field | Source in this MCP example |
|---|---|
| `name` | Server tool name, prefixed with our server namespace |
| `description` | Server description, prefixed with the server ID |
| `input_schema` | `inputSchema` |

The schema key changes from `inputSchema` to `input_schema`. The `mcp__<server>__<tool>` name is this adapter's routing convention; it is not a protocol requirement.

## Show me the code

```python
def to_anthropic_tool(server_id, mcp_tool):
    return {
        "name": f"mcp__{server_id}__{mcp_tool['name']}",
        "description": f"[{server_id}] {mcp_tool['description']}",
        "input_schema": mcp_tool["inputSchema"],
    }

# In the loop's dispatch:
if b.name.startswith("mcp__"):
    _, server_id, tool_name = b.name.split("__", 2)
    out = mcp_clients[server_id].call_tool(tool_name, b.input)
```

This is enough to expose the bundled calculator. The model chooses a tool; the harness resolves its name, performs the call, and sends the result back with the original model tool-call ID.

## Where the adapter loses information

The runnable [`call_tool`](ch14_mcp_agent.py) joins text content blocks and prefixes failures with `ERROR:`. It drops non-text blocks and does not map MCP `isError` to the model API's structured error flag. That simplification suits the calculator, but broader integrations need explicit handling of content types, structured results, and error semantics. MCP content blocks and model API content blocks are separate schemas. See the [current tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools).

Names and schemas also need validation. A provider may impose naming or JSON Schema limits that the MCP server does not share. A robust adapter maintains a lookup table from model-facing names to server/tool pairs instead of trusting arbitrary strings to fit the split convention.

## ⚠️ Watch out for

- **Process and request failures:** the reused client has no read timeout. This chapter initializes before entering its cleanup block, so an initialization exception can leave a child process running. Treat timeout, failed initialization, EOF, and shutdown as explicit lifecycle cases when extending it.
- **Trust and access:** a server's description and returned text do not grant it authority to change the user's task or approve another action. The harness owns tool access and authorization. Review server code before running it with your account's permissions.
- **Version mismatch:** neither the prefix nor successful tool discovery proves full compatibility. Preserve the historical pin for this paired lab. Check [the migration checklist](../docs/MCP_VERSIONS.md#migration-checklist) for another endpoint.

## ✅ Summary

- Translate the tool definition and keep a stable routing identity.
- Forward calls through the harness and match results to model call IDs.
- Preserve result and error information required by the application.
- Keep protocol compatibility and execution permissions visible in the design.

## 📝 Homework

```bash
python -m chapters.ch14_mcp_agent "what is (17 * 23) + 1234?"
```

This command requires an Anthropic API key and incurs model usage.

1. Follow the model call ID and the JSON-RPC request ID. Explain why they belong to separate conversations.
2. Add a second local server using fixed fixture data, keeping the same declared legacy subset.
3. Test a tool execution failure and a protocol failure separately. Observe which information reaches the model.
4. Design the mapping for a non-text tool result before implementing it. State which content types you support and how unsupported ones fail.
5. Compare this adapter with an official SDK release whose supported protocol versions you have checked. Record implementation versions and actual test results; do not infer desktop-client compatibility without testing it.

## 📚 References

- [MCP versions and migration](../docs/MCP_VERSIONS.md) — course implementation versus current specification
- [MCP 2024-11-05 tools](https://modelcontextprotocol.io/specification/2024-11-05/server/tools) — the lab's tool messages
- [MCP 2026-07-28 tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) — current result and schema requirements
- [Official Python SDK](https://github.com/modelcontextprotocol/python-sdk) — compare supported versions and lifecycle handling

## 🚀 Next

[Chapter 15 — Streaming text](ch15_streaming_text.md): make the tokens appear one at a time.

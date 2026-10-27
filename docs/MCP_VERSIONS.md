# MCP versions: the teaching example and the current protocol

**Checked: 2026-10-26.** Chapters [13](../chapters/ch13_mcp_wire.md) and [14](../chapters/ch14_mcp_agent.md), together with the [calculator server](../mcp_servers/calculator_server.py), demonstrate a small local stdio tools subset pinned to **`2024-11-05`**. Their purpose is to make message framing and dispatch understandable. They are not complete implementations of that revision, and they do not implement current MCP.

The official [versioning page](https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning) identifies **`2026-07-28`** as current. Its [GitHub release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28), published July 28, 2026, explicitly identifies it as stable. The earlier release candidate was a draft; the stable release should not be described as one. SDK and application adoption can lag behind a specification release.

## The boundary this course preserves

The paired lab requests `2024-11-05`, receives the bundled server's matching version, sends `notifications/initialized`, then lists and calls tools. The [historical lifecycle](https://modelcontextprotocol.io/specification/2024-11-05/basic/lifecycle) also requires handling incompatible version responses. Our client does not enforce that compatibility check. Its success with our server is evidence about that pair, not every MCP endpoint.

The example is synchronous and text-focused. It does not implement general pagination, concurrent response routing, complete capability negotiation, or a read timeout. Its process cleanup is limited. Keep those boundaries visible when borrowing the code.

## What a current implementation changes

| Concern | Course lab: `2024-11-05` subset | Current specification: `2026-07-28` |
|---|---|---|
| Initial exchange | `initialize`, then `notifications/initialized` | No initialization handshake; optional up-front `server/discover` call |
| Version and capabilities | Sent in initialization | Required per-request `_meta` fields |
| Results | Legacy result objects | `resultType` discriminator; additional requirements for specific results |
| Transport demonstrated | Local stdio | stdio and Streamable HTTP are standard bindings |

These changes come from the [versioned changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog). A server must implement discovery, although a client may send an ordinary request directly and handle a version error. Updating the string in the old handshake does not implement this lifecycle.

Current [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) uses a POST endpoint with JSON or request-scoped SSE responses. The July revision removes protocol sessions and the old GET stream endpoint. Long-lived change notifications use `subscriptions/listen`. SSE remains in use; “SSE is deprecated” would therefore be misleading.

MCP extends beyond tools. Other capabilities, result types, and extensions require their own handling. A tool adapter must also respect the destination model API's schema and content constraints. Similar field names do not make the two protocols interchangeable.

## Local credentials and remote authorization

The [authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) distinguishes transports: HTTP implementations supporting MCP authorization should follow its OAuth flow; stdio implementations should obtain credentials from the environment instead. Authorization itself is optional in MCP. The referenced OAuth 2.1 document is an IETF draft, not a final RFC.

For an HTTP service, also follow the transport's Origin validation and endpoint guidance. For a subprocess, review what you are launching and which credentials it inherits. A successful connection establishes neither trustworthy content nor permission for every action. This course does not configure OAuth or expose its calculator as a network service.

## Migration checklist

1. **Choose the target pair.** Record the client, server, SDK versions, transport, and mutually supported protocol revision. Pin dependencies used by the exercise.
2. **Read that revision's requirements.** Implement its request metadata, discovery/version errors, response envelopes, and capability behavior together. Add explicit handling for unsupported versions.
3. **Preserve the tool contract.** Validate names and schemas. Handle pagination, tool failures, protocol errors, and supported content types. Define what happens to unsupported content instead of silently dropping it.
4. **Complete the lifecycle.** Cover initialization/discovery failure, timeouts, cancellation, subprocess exit, and cleanup. Test a server that stays alive without replying.
5. **Test both ends.** Run protocol fixtures and interoperability checks against the actual target implementation. Retain traces with secrets removed. Passing the local calculator test alone is insufficient evidence.
6. **Publish honest scope.** State supported revisions, transports, optional capabilities, and tested application versions. Link test evidence. Keep legacy compatibility paths explicit.

## Compatibility exercise

Start with the bundled pair and capture its three requests plus notification. Then build a small fixture that returns a different version during the historical handshake. Verify that your enhanced client rejects an unsupported response before listing tools.

Next, compare the trace with a current-revision fixture or a pinned SDK example. Identify where discovery, metadata, and result envelopes differ. Keep fixtures separate so a test cannot accidentally validate a mixture of revisions.

Only after those checks, try a third-party host in a disposable environment using reviewed server code. Record the host version and negotiated behavior. Compatibility with Claude Desktop, Cursor, or another host is an empirical result to document; it is not guaranteed by this tutorial.

"""
agent.py — the climax. a production-quality Claude-Code-shaped CLI agent.

# By chapter 17 you understood every primitive. This file uses them all.

what it ships:
  - streaming output (SSE, chunk-buffered, ch15-style)
  - 7 tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite
  - tool-call rendering boxes (●) with status glyphs and inline diffs
  - markdown rendering for final assistant text (rich.markdown)
  - JSONL session persistence + --resume <id>
  - AGENT.md discovery walking up from cwd
  - permissions: ask | allow | deny modes (env or per-call)
  - context compaction triggered at 60% of model window
  - retries with exponential backoff + jitter (handles 429 / 529 / network)
  - prompt caching on system + tools (5-minute TTL, ~10x cost reduction)
  - cost & token meter — live status line, persisted to session
  - 7 slash commands: /help /clear /compact /resume /cost /model /init /exit
  - graceful ctrl-c handling: cancel mid-turn without losing session

run:
  python agent.py "build me a tetris game in one html file and open it"
  python agent.py --resume <session-id>
  python agent.py                               # interactive REPL
  python agent.py --session-dir                 # print session dir and exit
  python agent.py --no-stream                   # disable streaming (debug)

env:
  ANTHROPIC_API_KEY         (required)
  AZH_MODEL            (default: claude-sonnet-4-6)
  AZH_PERMISSION       ask | allow | deny  (default: ask)
  AZH_NO_CACHE         set to 1 to disable prompt caching

read it on a flight. modify in 10 minutes.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import random
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


# ============================================================
# 1. config
# ============================================================

MODEL = os.environ.get("AZH_MODEL", "claude-sonnet-4-6")
MAX_TURNS = 50
SESSION_DIR = Path.home() / ".agent-zero-to-hero" / "projects"
DEFAULT_PERMISSION = os.environ.get("AZH_PERMISSION", "ask")  # ask|allow|deny
USE_CACHE = os.environ.get("AZH_NO_CACHE") != "1"
USE_STREAM = True

# claude sonnet 4.6 prices, USD per 1M tokens (current 2026; verify on
# https://www.anthropic.com/pricing — these change). same as 4.5. if you
# change MODEL, update PRICES too — or set AZH_MODEL_PRICES env.
PRICES = {
    "input":            3.00,
    "output":          15.00,
    "cache_creation":   3.75,    # 5-minute TTL writes (1.25× input)
    "cache_creation_1h":6.00,    # 1-hour TTL writes (2× input)
    "cache_read":       0.30,    # reads — 0.1× input (90% cheaper)
}
if "AZH_MODEL_PRICES" in os.environ:
    try:
        price_overrides = json.loads(os.environ["AZH_MODEL_PRICES"])
        if not isinstance(price_overrides, dict):
            raise ValueError("expected JSON object")
    except Exception as e:
        print(f"warning: invalid AZH_MODEL_PRICES: {e}", file=sys.stderr)
    else:
        PRICES.update(price_overrides)

CONTEXT_WINDOW = 200_000
COMPACT_TRIGGER = 0.60
KEEP_RECENT = 6

console = Console()


# ============================================================
# 2. tools
# ============================================================

def tool_read(file_path: str, **_):
    p = Path(file_path).expanduser()
    if not p.exists():
        return f"ERROR: no such file: {file_path}"
    if not p.is_file():
        return f"ERROR: not a file: {file_path}"
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:50_000]
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def tool_write(file_path: str, content: str, **_):
    p = Path(file_path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {len(content)} chars to {file_path}"


def tool_edit(file_path: str, old_string: str, new_string: str, **_):
    p = Path(file_path).expanduser()
    if not p.exists():
        return f"ERROR: no such file: {file_path}"
    body = p.read_text()
    if old_string not in body:
        return f"ERROR: old_string not found in {file_path}"
    if body.count(old_string) > 1:
        return (f"ERROR: old_string appears {body.count(old_string)} times — "
                f"add surrounding context to make it unique")
    new_body = body.replace(old_string, new_string)
    p.write_text(new_body)
    return _diff_summary(file_path, body, new_body)


def tool_bash(command: str, **_):
    try:
        r = subprocess.run(command, shell=True, capture_output=True,
                           text=True, timeout=120)
        out = (r.stdout + r.stderr)[:20_000]
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 120s"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def tool_glob(pattern: str, path: str = ".", **_):
    try:
        matches = sorted(Path(path).expanduser().glob(pattern))
        return "\n".join(str(p) for p in matches[:200]) or "(no matches)"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def tool_grep(pattern: str, path: str = ".", **_):
    """Use ripgrep if available; fall back to grep."""
    for cmd in (["rg", "-n", pattern, path], ["grep", "-rn", pattern, path]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return r.stdout[:20_000] or "(no matches)"
        except FileNotFoundError:
            continue
    return "ERROR: neither rg nor grep available"


# todo state lives on the session so it persists across compaction.
def tool_todo_write(todos: list, session=None, **_):
    if session is not None:
        session.todos = todos
    rendered = "\n".join(
        f"  [{t.get('status','pending')[0].upper()}] {t.get('content','')}"
        for t in todos)
    return f"todos updated ({len(todos)} items):\n{rendered}"


TOOLS = [
    {"name": "Read",
     "description": "Read a file's full contents. Returns up to 50KB of UTF-8 text.",
     "input_schema": {"type": "object",
                      "properties": {"file_path": {"type": "string"}},
                      "required": ["file_path"]}},
    {"name": "Write",
     "description": "Write a file. Creates parent directories. Overwrites if exists.",
     "input_schema": {"type": "object",
                      "properties": {"file_path": {"type": "string"},
                                     "content": {"type": "string"}},
                      "required": ["file_path", "content"]}},
    {"name": "Edit",
     "description": ("Replace exact string old_string with new_string in a file. "
                     "old_string must appear EXACTLY ONCE in the file — include "
                     "surrounding lines for context if needed."),
     "input_schema": {"type": "object",
                      "properties": {"file_path": {"type": "string"},
                                     "old_string": {"type": "string"},
                                     "new_string": {"type": "string"}},
                      "required": ["file_path", "old_string", "new_string"]}},
    {"name": "Bash",
     "description": ("Execute a shell command. Output truncated to 20KB. "
                     "Timeout 120s. The user is asked for permission first."),
     "input_schema": {"type": "object",
                      "properties": {"command": {"type": "string"}},
                      "required": ["command"]}},
    {"name": "Glob",
     "description": "Find files matching a glob pattern (e.g. '**/*.py').",
     "input_schema": {"type": "object",
                      "properties": {"pattern": {"type": "string"},
                                     "path": {"type": "string",
                                              "description": "search root, default '.'"}},
                      "required": ["pattern"]}},
    {"name": "Grep",
     "description": "Search file contents with a regex (uses ripgrep if available).",
     "input_schema": {"type": "object",
                      "properties": {"pattern": {"type": "string"},
                                     "path": {"type": "string",
                                              "description": "search root, default '.'"}},
                      "required": ["pattern"]}},
    {"name": "TodoWrite",
     "description": ("Track a multi-step plan. Call this when starting any task with "
                     "more than 2 steps. Each todo: {content: str, status: pending|in_progress|completed}. "
                     "Update by passing the WHOLE list each time."),
     "input_schema": {"type": "object",
                      "properties": {"todos": {"type": "array",
                                               "items": {"type": "object"}}},
                      "required": ["todos"]}},
]

DISPATCH = {
    "Read":      tool_read,
    "Write":     tool_write,
    "Edit":      tool_edit,
    "Bash":      tool_bash,
    "Glob":      tool_glob,
    "Grep":      tool_grep,
    "TodoWrite": tool_todo_write,
}

WRITE_TOOLS = {"Write", "Edit", "Bash"}


# ============================================================
# 3. rendering
# ============================================================

def _tool_label(name: str, args: dict) -> str:
    if name == "Bash":      return f"Bash$ {args.get('command','')[:80]}"
    if name == "Read":      return f"Read({args.get('file_path','')})"
    if name == "Write":     return f"Write({args.get('file_path','')})"
    if name == "Edit":      return f"Edit({args.get('file_path','')})"
    if name == "Glob":      return f"Glob({args.get('pattern','')})"
    if name == "Grep":      return f"Grep({args.get('pattern','')})"
    if name == "TodoWrite": return f"TodoWrite ({len(args.get('todos',[]))} items)"
    return f"{name}({args})"


def render_tool_call(name: str, args: dict):
    label = _tool_label(name, args)
    console.print(f"[bold green]●[/bold green] {label}")


def render_tool_result(name: str, result: str):
    if result.startswith("ERROR"):
        for line in result.splitlines()[:6]:
            console.print(f"  [red]⎿  {line}[/red]")
        return
    if name == "Edit":
        for line in result.splitlines()[:30]:
            if line.startswith("+++") or line.startswith("---"):
                console.print(f"  [dim]⎿  {line}[/dim]")
            elif line.startswith("+"):
                console.print(f"  ⎿  [green]{line}[/green]")
            elif line.startswith("-"):
                console.print(f"  ⎿  [red]{line}[/red]")
            else:
                console.print(f"  ⎿  {line}")
        return
    lines = result.splitlines()
    show = lines[:8]
    for line in show:
        console.print(f"  ⎿  {line}")
    if len(lines) > len(show):
        console.print(f"  ⎿  [dim]... ({len(lines) - len(show)} more lines)[/dim]")


def _diff_summary(path: str, before: str, after: str) -> str:
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(),
                                fromfile=path, tofile=path, lineterm="", n=2)
    return "\n".join(list(diff)[:40])


def render_text(text: str):
    if text.strip():
        console.print(Markdown(text))


# ============================================================
# 4. permissions
# ============================================================

def ask_permission(name: str, args: dict) -> bool:
    if DEFAULT_PERMISSION == "allow":
        return True
    if DEFAULT_PERMISSION == "deny":
        return False
    label = _tool_label(name, args)
    console.print(f"\n[yellow]allow {label}? [Y/n][/yellow] ", end="")
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("", "y", "yes")


# ============================================================
# 5. AGENT.md loader
# ============================================================

def load_agent_md(start: Path) -> str:
    """Walk up from cwd, collect AGENT.md files (root-first, deepest-last)."""
    parts = []
    p = start.resolve()
    chain = list(reversed([p] + list(p.parents)))
    for d in chain:
        candidate = d / "AGENT.md"
        if candidate.is_file():
            parts.append(f"# from {candidate}\n{candidate.read_text()}")
    user = Path.home() / ".agent-zero-to-hero" / "AGENT.md"
    if user.is_file():
        parts.insert(0, f"# user-scope ({user})\n{user.read_text()}")
    return "\n\n".join(parts)[:25_000]


# ============================================================
# 6. cost meter
# ============================================================

class Meter:
    """Track tokens and project to dollars. Updated after every turn."""
    def __init__(self):
        self.input = self.output = self.cache_create = self.cache_read = 0
        self.usd = 0.0
        self.turns = 0

    def add(self, usage):
        self.turns += 1
        i = getattr(usage, "input_tokens", 0) or 0
        o = getattr(usage, "output_tokens", 0) or 0
        cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cr = getattr(usage, "cache_read_input_tokens", 0) or 0
        self.input += i; self.output += o; self.cache_create += cw; self.cache_read += cr
        spent = (i  * PRICES["input"]
               + o  * PRICES["output"]
               + cw * PRICES["cache_creation"]
               + cr * PRICES["cache_read"]) / 1_000_000
        self.usd += spent
        return spent

    def status(self) -> str:
        return (f"${self.usd:.4f}  ·  "
                f"in {self.input}  out {self.output}  "
                f"cache_r {self.cache_read}  cache_w {self.cache_create}")


# ============================================================
# 7. sessions (JSONL append-only)
# ============================================================

class Session:
    """Append-only JSONL log. Crash-safe; resume by replaying."""

    def __init__(self, session_id: str | None = None, cwd: Path | None = None):
        self.id = session_id or uuid.uuid4().hex[:12]
        self.cwd = cwd or Path.cwd()
        slug = str(self.cwd).replace("/", "-").lstrip("-") or "_root"
        self.dir = SESSION_DIR / slug
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{self.id}.jsonl"
        self.messages: list[dict] = []
        self.todos: list[dict] = []
        if self.path.exists():
            self._replay()
        else:
            self._write({"type": "meta", "session_id": self.id,
                         "started": datetime.now(timezone.utc).isoformat(),
                         "cwd": str(self.cwd), "model": MODEL})

    def append_user(self, text: str):
        self.messages.append({"role": "user", "content": text})
        self._write({"type": "user", "content": text,
                     "ts": datetime.now(timezone.utc).isoformat()})

    def append_assistant(self, content_blocks):
        ser = [b.model_dump() if hasattr(b, "model_dump") else b
               for b in content_blocks]
        self.messages.append({"role": "assistant", "content": ser})
        self._write({"type": "assistant", "content": ser,
                     "ts": datetime.now(timezone.utc).isoformat()})

    def append_tool_results(self, results: list[dict]):
        self.messages.append({"role": "user", "content": results})
        self._write({"type": "tool_results", "content": results,
                     "ts": datetime.now(timezone.utc).isoformat()})

    def truncate_orphan_user(self):
        """If the last message is a bare user prompt with no assistant reply,
        drop it. Called on resume to recover from a crashed turn."""
        if not self.messages:
            return
        last = self.messages[-1]
        if last["role"] == "user" and isinstance(last["content"], str):
            self.messages.pop()
            self._write({"type": "drop_orphan_user", "reason": "crash recovery"})

    def clear(self):
        self.messages.clear()
        self.todos.clear()
        self._write({"type": "clear",
                     "ts": datetime.now(timezone.utc).isoformat()})

    def replace_messages(self, new_messages: list[dict], reason: str):
        """For compaction: replace the in-memory array and log the rewrite."""
        self.messages = new_messages
        self._write({"type": "compact", "reason": reason,
                     "len_after": len(new_messages),
                     "ts": datetime.now(timezone.utc).isoformat()})

    def _write(self, entry: dict):
        with self.path.open("a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
            f.flush()

    def _replay(self):
        for line in self.path.open():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = entry.get("type")
            if t == "user":
                self.messages.append({"role": "user", "content": entry["content"]})
            elif t == "assistant":
                self.messages.append({"role": "assistant", "content": entry["content"]})
            elif t == "tool_results":
                self.messages.append({"role": "user", "content": entry["content"]})
            elif t == "clear":
                self.messages.clear()
            elif t == "compact":
                pass  # we don't try to reconstruct compacted state on resume
            elif t == "drop_orphan_user":
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()


# ============================================================
# 8. compaction
# ============================================================

SUMMARIZER = (
    "You are summarizing a conversation. Preserve identifiers (uuids, paths, "
    "urls, names) verbatim, active tasks, decisions, and pending TODOs. Drop "
    "redundant tool output, idle exploration, errors that were resolved. "
    "Past tense. Under 1000 words.")


def compact_messages(client: Anthropic, messages: list[dict]) -> list[dict]:
    """Summarize older messages into one synthetic user message; keep recent verbatim."""
    if len(messages) <= KEEP_RECENT + 1:
        return messages

    old, recent = messages[:-KEEP_RECENT], messages[-KEEP_RECENT:]

    # CRITICAL: the summarizer call cannot end on an assistant tool_use block —
    # the API requires tool_result to follow. Trim trailing tool_use turns.
    while old and _is_tool_use_assistant(old[-1]):
        recent.insert(0, old.pop())

    if not old:
        return messages       # nothing safe to compact

    console.print(f"  [dim]compacting {len(old)} old messages...[/dim]")

    try:
        r = client.messages.create(
            model=MODEL, max_tokens=2048, system=SUMMARIZER,
            messages=old + [{"role": "user",
                             "content": "Summarize everything above per instructions."}],
        )
    except Exception as e:
        console.print(f"  [red]compaction failed: {e}[/red]")
        return messages

    summary = "".join(b.text for b in r.content if b.type == "text")
    preamble = (
        "<conversation_summary>\nThe following is a summary of our prior "
        f"conversation. Treat as memory; continue from here.\n\n{summary}\n"
        "</conversation_summary>")
    return [{"role": "user", "content": preamble}] + recent


def _is_tool_use_assistant(msg: dict) -> bool:
    if msg["role"] != "assistant":
        return False
    content = msg["content"]
    if isinstance(content, list):
        return any((b.get("type") if isinstance(b, dict) else getattr(b, "type", None))
                   == "tool_use" for b in content)
    return False


# ============================================================
# 9. retries with exponential backoff + jitter
# ============================================================

RETRYABLE = (anthropic.RateLimitError,
             anthropic.APIConnectionError,
             anthropic.InternalServerError,
             anthropic.APITimeoutError)


def with_retries(fn, *args, max_attempts=5, base=1.0, cap=30.0, **kwargs):
    """Call fn with full-jitter exponential backoff on retryable errors."""
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except RETRYABLE as e:
            if attempt == max_attempts - 1:
                raise
            delay = min(cap, base * (2 ** attempt)) * random.random()
            console.print(f"  [yellow]API {type(e).__name__}; retry in {delay:.1f}s "
                          f"(attempt {attempt + 1}/{max_attempts})[/yellow]")
            time.sleep(delay)


# ============================================================
# 10. the streaming agent loop
# ============================================================

DEFAULT_SYSTEM = """\
You are agent-zero-to-hero, a minimal coding agent that runs in the user's terminal.
You are an educational reference implementation — ~850 lines of Python
wrapping the Anthropic Messages API in a tool-use loop. Be precise and terse.

You have these tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite.

Workflow on any non-trivial task:
  1. Gather context first (Read, Glob, Grep) — never invent file paths.
  2. For multi-step work, call TodoWrite up front to plan; update as you go.
  3. Take action (Write/Edit/Bash) — these prompt the user for permission.
  4. Verify (run tests, open the result, read the output).

Rules:
  - Read a file BEFORE editing it. Edit fails if old_string isn't unique —
    include surrounding lines for context.
  - When a command fails, read the error, try one fix, then ask the user.
  - Prefer surgical Edits over wholesale Writes.
  - Keep responses short. The user is reading the source code as they use you.
  - For multi-tool turns, batch in one assistant message — don't serialize
    when parallel works."""


def _build_system_param(system_text: str) -> list[dict] | str:
    """Wrap system prompt with cache_control if caching is enabled."""
    if not USE_CACHE:
        return system_text
    return [{"type": "text", "text": system_text,
             "cache_control": {"type": "ephemeral"}}]


def _build_tools_param() -> list[dict]:
    """Wrap the LAST tool with cache_control to cache the whole tool list."""
    if not USE_CACHE:
        return TOOLS
    cached = [dict(t) for t in TOOLS]
    cached[-1]["cache_control"] = {"type": "ephemeral"}
    return cached


def stream_one_turn(client: Anthropic, system, messages: list[dict]):
    """Stream one assistant turn. Yields incremental text. Returns
    (assistant_blocks, stop_reason, usage)."""
    blocks_in_progress: dict[int, dict] = {}
    stop_reason = None
    usage = None

    with client.messages.stream(
        model=MODEL, max_tokens=4096,
        system=system, tools=_build_tools_param(),
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
                        "type": "tool_use", "id": cb.id, "name": cb.name,
                        "_partial_json": "",
                    }
                    # tool_use always starts on a new line, after any prior text.
                    console.print()

            elif t == "content_block_delta":
                d = event.delta
                blk = blocks_in_progress.get(event.index)
                if blk is None:
                    continue
                if d.type == "text_delta":
                    console.print(d.text, end="", soft_wrap=True, highlight=False)
                    blk["text"] += d.text
                elif d.type == "input_json_delta":
                    blk["_partial_json"] += d.partial_json

            elif t == "content_block_stop":
                blk = blocks_in_progress.get(event.index)
                if blk and blk["type"] == "tool_use":
                    raw = blk.pop("_partial_json") or "{}"
                    try:
                        blk["input"] = json.loads(raw)
                    except json.JSONDecodeError:
                        blk["input"] = {}

            elif t == "message_delta":
                stop_reason = event.delta.stop_reason
                if event.usage:
                    usage = event.usage

            elif t == "message_stop":
                # the final message object holds the canonical usage record.
                final = event.message
                if getattr(final, "usage", None):
                    usage = final.usage

    blocks = [blocks_in_progress[i] for i in sorted(blocks_in_progress)]
    if any(b["type"] == "text" and b["text"].strip() for b in blocks):
        console.print()                   # newline after the streamed text
    return blocks, stop_reason, usage


def agent_turn(client: Anthropic, session: Session, system_text: str,
               meter: Meter, user_input: str):
    session.append_user(user_input)
    system = _build_system_param(system_text)

    for turn in range(MAX_TURNS):
        # auto-compact when approaching context budget
        if turn > 0 and turn % 5 == 0:
            try:
                in_toks = with_retries(client.messages.count_tokens,
                                       model=MODEL, system=system, messages=session.messages,
                                       tools=_build_tools_param()).input_tokens
                if in_toks > CONTEXT_WINDOW * COMPACT_TRIGGER:
                    session.replace_messages(
                        compact_messages(client, session.messages),
                        reason=f"auto: {in_toks} tokens")
            except Exception:
                pass     # token count is a nice-to-have; don't break the loop

        try:
            if USE_STREAM:
                blocks, stop_reason, usage = with_retries(
                    stream_one_turn, client, system, session.messages)
                # convert dict blocks to anthropic-shaped objects for serialization
                content_blocks = blocks
            else:
                r = with_retries(client.messages.create,
                                 model=MODEL, max_tokens=4096,
                                 system=system, tools=_build_tools_param(),
                                 messages=session.messages)
                content_blocks = [b.model_dump() for b in r.content]
                stop_reason = r.stop_reason
                usage = r.usage
                # render for non-stream
                for b in r.content:
                    if b.type == "text":
                        render_text(b.text)
        except KeyboardInterrupt:
            console.print("\n[dim]turn cancelled. session preserved.[/dim]")
            return
        except RETRYABLE as e:
            console.print(f"\n[red]API error after retries: {e}[/red]")
            return
        except Exception as e:
            console.print(f"\n[red]unexpected error: {type(e).__name__}: {e}[/red]")
            return

        session.append_assistant(content_blocks)

        if usage is not None:
            spent = meter.add(usage)
            console.print(f"  [dim]turn {turn} · ${spent:.4f}  total {meter.status()}[/dim]")

        if stop_reason != "tool_use":
            return

        # dispatch tools, optionally asking for permission
        results = []
        for b in content_blocks:
            if b.get("type") != "tool_use":
                continue
            name, args = b["name"], b.get("input", {})
            render_tool_call(name, args)

            if name in WRITE_TOOLS and not ask_permission(name, args):
                results.append({"type": "tool_result", "tool_use_id": b["id"],
                                "content": "user denied this tool call.",
                                "is_error": True})
                continue

            handler = DISPATCH.get(name)
            if handler is None:
                out = f"unknown tool: {name}"
            else:
                try:
                    if name == "TodoWrite":
                        out = handler(session=session, **args)
                    else:
                        out = handler(**args)
                except Exception as e:
                    out = f"ERROR: {type(e).__name__}: {e}"

            render_tool_result(name, out)
            results.append({"type": "tool_result",
                            "tool_use_id": b["id"], "content": out})

        session.append_tool_results(results)


# ============================================================
# 11. slash commands
# ============================================================

def handle_slash(client: Anthropic, session: Session, meter: Meter,
                 cmd: str, args: str) -> bool:
    if cmd == "/help":
        console.print("[bold]commands:[/bold]")
        console.print("  /help                show this")
        console.print("  /cost                show token & dollar usage")
        console.print("  /model               show current model")
        console.print("  /init                create AGENT.md from this directory")
        console.print("  /clear               forget conversation; keep file on disk")
        console.print("  /compact             summarize old messages and continue")
        console.print("  /resume <id>         (run from shell: python agent.py --resume <id>)")
        console.print("  /exit                quit (or ctrl-d)")
        return True
    if cmd == "/cost":
        console.print(f"  [bold]cost[/bold]   {meter.status()}")
        console.print(f"  [bold]turns[/bold]  {meter.turns}")
        return True
    if cmd == "/model":
        console.print(f"  [bold]model[/bold]  {MODEL}")
        return True
    if cmd == "/init":
        path = Path("AGENT.md")
        if path.exists():
            console.print(f"  [yellow]{path} already exists; not overwriting[/yellow]")
        else:
            path.write_text(
                "# Project context for agent-zero-to-hero\n\n"
                f"This file was generated by `/init` in {Path.cwd()}.\n\n"
                "## What this project is\n_Describe your project here._\n\n"
                "## Conventions\n- _Coding style, naming, etc._\n\n"
                "## How to test\n- _How to run tests / what passes._\n")
            console.print(f"  [green]created {path.resolve()}[/green]")
        return True
    if cmd == "/clear":
        session.clear()
        console.print("  [dim]cleared.[/dim]")
        return True
    if cmd == "/compact":
        session.replace_messages(compact_messages(client, session.messages),
                                 reason="manual")
        console.print(f"  [dim]compacted; {len(session.messages)} messages remain.[/dim]")
        return True
    if cmd == "/resume":
        console.print(f"  [dim]restart with: python agent.py --resume {args}[/dim]")
        return True
    if cmd == "/exit":
        sys.exit(0)
    return False


# ============================================================
# 12. main
# ============================================================

def main():
    global USE_STREAM

    ap = argparse.ArgumentParser(prog="agent-zero-to-hero", add_help=True)
    ap.add_argument("prompt", nargs="*", help="one-shot prompt; omit for interactive REPL")
    ap.add_argument("--resume", help="resume session by id")
    ap.add_argument("--session-dir", action="store_true",
                    help="print the session directory and exit")
    ap.add_argument("--no-stream", action="store_true",
                    help="disable streaming (useful for debugging)")
    args = ap.parse_args()

    if args.session_dir:
        print(SESSION_DIR)
        return

    USE_STREAM = USE_STREAM and not args.no_stream

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("set ANTHROPIC_API_KEY first")

    client = Anthropic()
    session = Session(session_id=args.resume)
    if args.resume:
        session.truncate_orphan_user()    # recover from prior crash mid-turn
    meter = Meter()

    agent_md = load_agent_md(Path.cwd())
    system = DEFAULT_SYSTEM + (
        "\n\n# project context (AGENT.md)\n" + agent_md if agent_md else "")

    console.print(Panel.fit(
        f"[bold]agent-zero-to-hero[/bold]   [dim]session {session.id}[/dim]\n"
        f"[dim]model {MODEL}   cwd {Path.cwd()}   "
        f"streaming={'on' if USE_STREAM else 'off'}   "
        f"caching={'on' if USE_CACHE else 'off'}[/dim]",
        border_style="dim"))

    if args.prompt:
        agent_turn(client, session, system, meter, " ".join(args.prompt))
        console.print(f"\n[dim]{meter.status()}[/dim]")
        return

    console.print("[dim]/help for commands · ctrl-d to exit[/dim]\n")
    while True:
        try:
            line = console.input("[bold blue]>[/bold blue] ")
        except (EOFError, KeyboardInterrupt):
            print()
            console.print(f"[dim]final: {meter.status()}[/dim]")
            return
        if not line.strip():
            continue
        if line.startswith("/"):
            cmd, _, rest = line.partition(" ")
            if handle_slash(client, session, meter, cmd, rest):
                continue
        try:
            agent_turn(client, session, system, meter, line)
        except KeyboardInterrupt:
            console.print("\n[dim]cancelled. session preserved.[/dim]")


if __name__ == "__main__":
    main()

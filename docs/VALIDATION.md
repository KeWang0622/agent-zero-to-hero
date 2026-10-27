# Validation record — 2026-10-26

Baseline: `179d6b38f137a46e33328958a014e60cb6038b2a` (2026-06-02).
This is an offline code/documentation validation record, not a live provider certification.

## environment

- macOS, Python **3.12.14**.
- anthropic **2.3.0**, httpx **0.28.1**, rich **15.0.0**.
- pytest **9.1.1**, ruff **0.17.2**.
- Resolved dependency snapshot: [constraints-tested.txt](constraints-tested.txt).
- Other declared Python versions were not run locally during this update; the existing CI matrix remains in the repository.

To reproduce with a compatible interpreter in a fresh virtual environment:

```bash
python -m pip install -e ".[test]" -c docs/constraints-tested.txt
python -m pytest tests/ -q
python -m ruff check .
```

The constraints snapshot is not a platform-independent lockfile and does not pin remote model behavior. It records the environment used here without forcing all readers to upgrade to a new SDK major.

## results

| Check | Result |
|---|---|
| Original baseline suite | 42 passed |
| Updated full suite | **78 passed in 0.98s** |
| Additional regression/protocol cases | 36 |
| Ruff | All checks passed |
| `git diff --check` | Passed |
| New reading-lab complete Python demonstrations | Executed locally; assertions passed |
| Reading-lab Python code fences | Parsed successfully |
| Local Markdown navigation | Checked after adding new documents |

Timing is one local observation, not a performance promise. The fixtures test harness behavior rather than real model competence.

## what the additional cases cover

- New compaction snapshots replay the saved working context; legacy count-only records remain readable.
- Truncated, refused, unsupported, and invalid capstone responses cannot become tool dispatches.
- Streaming waits for final status and validates the entire tool batch before execution, including malformed and nonobject arguments.
- Responses continuation preserves server state and correlates each result by call ID.
- The bounded arithmetic executor rejects invalid arguments; HTTP failures, refusal, and exhausted budgets are explicit.

## deliberately not claimed

No paid Anthropic/OpenAI/Gemini call was made. No model quality benchmark or fixed API-cost measurement was run. No current remote MCP/A2A service was invoked. The new Responses script was checked through official docs and offline HTTP fixtures, not an authenticated live endpoint.

The CLI still lacks filesystem/network confinement, durable operation reconciliation, transactional external effects, and integrated Skills/MCP/subagents/multi-provider support. Some old chapter examples retain simplified `eval` calculators and protocol handling. See [WISHLIST.md](WISHLIST.md), [ADAPTING.md](ADAPTING.md), and [MCP_VERSIONS.md](MCP_VERSIONS.md) before adapting those examples.

Original media assets were retained, not regenerated or revalidated as current promotional material. Updated prose distinguishes historical examples, current primary-source guidance, implemented fixes, and design exercises.

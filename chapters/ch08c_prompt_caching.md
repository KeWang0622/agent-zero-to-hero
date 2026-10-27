# Chapter 08c — Prompt Caching, Measured 🐢

> Cache reuse is a property of a stable prefix and a workload. Measure it.

**Checked 2026-10-26.** Companion: [ch08c_prompt_caching.py](ch08c_prompt_caching.py). The original experiment uses explicit breakpoints; current Claude documentation also provides automatic caching.

## what gets reused?

The prompt prefix is ordered **tools → system → messages**. A breakpoint marks the end of a reusable prefix. Changing earlier content can invalidate reuse after that point. Current Claude documentation lists a **1,024-token** minimum for the course's Sonnet 4.6 example, not the 2,048 previously stated here. Other models have different thresholds. Explicit caching allows up to four breakpoints; automatic caching manages a breakpoint for you. [Claude prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).

Avoid treating an entire model family as having one permanent threshold. Check the selected model, then inspect `cache_creation_input_tokens` and `cache_read_input_tokens`. A short system prompt can be below the minimum even if it has a cache marker.

## inspect an explicit breakpoint

```python
system = [{"type": "text", "text": SYSTEM,
           "cache_control": {"type": "ephemeral"}}]
response = client.messages.create(
    model=MODEL, max_tokens=1024,
    tools=TOOLS, system=system, messages=messages,
)
```

This is an excerpt; the companion defines its own prompt and tools. The system breakpoint follows the tool definitions in the effective prefix. Put frequently changing request content after the reusable part. Choose explicit placement when you need to inspect it; consult the current documentation for automatic top-level caching and SDK compatibility.

## calculate a break-even, not a slogan

At the documented cache multipliers, let `C` be the uncached input cost of a repeated prefix. A five-minute write followed by `n` reads costs `1.25C + 0.1nC`, compared with `(n+1)C` without caching. For a one-hour write, replace `1.25` with `2`. This excludes variable input, output, and other tool charges. [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing).

One reuse can repay the five-minute write premium; two can repay the one-hour premium under these assumptions. Whether a longer TTL is better depends on elapsed time and invalidation, not merely number of turns.

The former five-row “measured” table had no saved model/configuration/trace attached. This edition removes it rather than treating it as a reproducible benchmark. The experiment prints usage; save your own dated log and calculate the ratio you actually observe.

## common failures

- A timestamp in the stable prefix changes every request. This is **cache invalidation**, not the security concept of cache poisoning.
- A prefix is too short. Adding a marker does not override the model's threshold.
- A cache read reduces input charges, but output dominates the workload. Total savings are smaller than the input discount.
- Loaded skill text remains in subsequent history. Loading once does not remove its future token cost.
- A price constant stays unchanged after a model switch. The meter is now an estimate using the wrong configuration.

## homework

```bash
python -m chapters.ch08c_prompt_caching
```

This is a paid experiment. Record the date, model, prompt token count, TTL, elapsed time, and each usage category. Compare repeated stable input with a deliberately modified prefix. Acceptance: explain the observed hit/miss pattern and total cost without assuming a fixed multiplier of savings.

Then calculate a one-hour versus five-minute policy for reuse every eight minutes, stating whether cache hits refresh expiration and checking that behavior in the current docs. Do not sleep through an hour of API experiments when arithmetic answers the question.

Next: [chapter 09 — sessions](ch09_sessions.md).

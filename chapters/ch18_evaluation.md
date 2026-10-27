# Chapter 18 — Did the Agent Actually Succeed? 🐢

> **A convincing final message is a claim. An evaluation checks the evidence.**

**Reading lab:** this chapter extends the tutorial conceptually. There is no
`ch18_evaluation.py`, and `agent.py` does not contain an evaluation runner.
The small examples below run locally without an API key.

## 🐢 guigui says

You change the system prompt. The agent solves your favorite example faster.
Did you improve the agent, or make that example easier? Now switch models,
change a tool description, or compact the conversation. The same question
returns. Evaluation is how we turn “seems better” into a claim someone else
can check.

The object under test is the whole arrangement: model, instructions, tool
definitions, permissions, loop, and environment. Keep that arrangement in
the result record. A model name alone cannot reproduce your experiment.

## the planted misconception

Here is a tempting grader:

```python
def passed(final_text):
    return "all tests passed" in final_text.lower()
```

It rewards an unsupported assertion and rejects a correct patch whose final
message says “fixed.” Even checking whether the agent *called* `pytest` is
insufficient: the command might fail, run zero tests, or target a test file
the agent just emptied.

Separate **outcome** from **process**. The outcome is the final artifact or
external state. The process records whether the agent respected constraints
while producing it. Anthropic's evaluation guide makes this distinction
explicit and discusses code, model, and human graders. A useful first
implementation can be much smaller than an evaluation platform.
([Anthropic, agent evaluations](https://www.anthropic.com/research/demystifying-evals-for-ai-agents))

## one running task

Give the agent a disposable directory containing this deliberately broken
function:

```python
def normalize_tag(value):
    return value.lower()
```

The task: “Update `normalize_tag` to trim surrounding whitespace and lowercase
the result. Reject non-string input with `TypeError`. Preserve internal
whitespace. Modify only `tags.py`.”

Define success before running the agent:

| Check | Evidence | Why it matters |
|---|---|---|
| Required behavior | Held-out function calls | A plausible diff can be wrong |
| Existing behavior | Existing regression tests | A fix can break another case |
| Edit scope | Before/after file hashes | Tests passing does not authorize unrelated edits |
| Honest report | Final text versus test receipts | A failed run must not be reported as passing |
| Resources | Elapsed time, calls, tokens | A success with an unbounded loop is unsuitable |

Run the outcome grader outside the agent's writable workspace. For arbitrary
generated code, also isolate execution: Python imports can execute code.
SWE-bench illustrates the broader approach by applying generated patches
and running repository tests in controlled environments.
([SWE-bench evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/))

Do not require one exact tool sequence. A valid solution might use `Edit`,
`Write`, or another authorized editor. Require an ordering constraint only
when the task actually demands it, such as approval preceding publication.

## show me the grader

This complete toy example compares two hand-written candidates. It checks
the grader without calling a model or executing an untrusted file:

```python
def broken(value):
    return value.lower()


def corrected(value):
    if not isinstance(value, str):
        raise TypeError("tag must be a string")
    return value.strip().lower()


def grade(candidate):
    checks = {}
    for value, expected in [("  Bug  ", "bug"), ("A  B", "a  b"), ("", "")]:
        try:
            checks[repr(value)] = candidate(value) == expected
        except Exception:
            checks[repr(value)] = False
    for value in [None, 7]:
        try:
            candidate(value)
        except TypeError:
            checks[repr(value)] = True
        except Exception:
            checks[repr(value)] = False
        else:
            checks[repr(value)] = False
    return {"passed": all(checks.values()), "checks": checks}


assert not grade(broken)["passed"]
assert grade(corrected)["passed"]
print("grader accepts the fix and rejects the original")
```

The explicit type check matters: `None.lower()` raises `AttributeError`,
which does not satisfy the task. An eval that only checks “some exception
occurred” misses this distinction.

Add a known incorrect candidate that passes the easy cases, such as replacing
all whitespace with nothing. Your grader should reject it. Testing the grader
is part of testing the agent; otherwise an always-green grader produces a
very impressive dashboard.

## repeatability is different from finding one success

Run each task several times from a clean fixture. Keep all attempts, including
timeouts. Here are fabricated observations, not measurements of this repo:

| Task | Trial 1 | Trial 2 | Trial 3 |
|---|---|---|---|
| Trim tags | Pass | Pass | Pass |
| Reject non-strings | Pass | Fail | Fail |
| Preserve internal spaces | Fail | Pass | Fail |
| Respect edit scope | Fail | Fail | Fail |

The per-trial success rate is 5/12. Three of four tasks succeed at least once;
one of four succeeds in all three trials. These answer different questions.
`pass@k` concerns at least one success in *k* attempts; `pass^k` concerns all
*k* attempts succeeding. The latter was introduced for reliability evaluation
in τ-bench.
([τ-bench paper](https://arxiv.org/abs/2406.12045))

For a hypothetical task with independent attempts and constant success
probability `p`, these probabilities are `1 - (1 - p)**k` and `p**k`.
With `p = 0.8` and `k = 3`, that is 99.2% versus 51.2%. These are illustrative
formulas, not estimates obtained by raising the average score of a mixed
task suite to a power. Real tasks have different difficulties, and attempts
can share failure causes.

If your product retries, evaluate that actual retry policy, including its
budget and how it selects a result. A benchmark oracle that knows which
candidate is correct may be stronger than your deployed verifier. Preserve
the per-task trial table, sample counts, and uncertainty; a tiny improvement
on a tiny suite is evidence to investigate, not a release guarantee.

## keep the answer key out of the workspace

The evaluator owns hidden tests, reference solutions, and scoring metadata.
The agent receives the task and its working files. Mounting the full eval
directory into the same unrestricted shell lets the agent read or change its
own exam. A hidden filename is not access control.

Contamination also happens during retrieval. Anthropic documented agents
encountering public benchmark answers and, in some cases, locating answer
keys after recognizing the benchmark. Keeping an answer out of the prompt
does not keep it out of search results.
([BrowseComp contamination analysis](https://www.anthropic.com/research/eval-awareness-browsecomp))

For this exercise, disable network access and give each trial fresh files.
For a web-research task, where retrieval is necessary, retain source records
and inspect whether answers came from task evidence or leaked solutions.
Split development and held-out tasks by underlying problem family where
possible. Renaming “Bug” to “Feature” does not create an independent task.
Once you tune against a failed held-out example, move it into development
and replenish the held-out set.

## ⚠️ the failure: grading the story

`agent.py` has `Meter`, tool-result messages, and a bounded turn loop. Those
are useful observation points, but they are not graders. Its shell tool
returns captured output rather than a structured exit-code receipt. Its
session records are conversation history, not a complete experimental
manifest. A reliable runner would add isolated fixtures, external outcome
checks, termination status, and versioned run metadata.

Keep infrastructure failure separate from task failure: missing dependencies
are different from a bad patch. Report both counts and a predeclared retry
policy; silently removing difficult failed runs biases the score. Use model
judges for qualities such as explanation clarity only after comparing their
decisions with human ratings. Preserve their rubric and version, too.

## 📝 homework

1. **Validate the grader.** Run the snippet and add three wrong candidates.
   Acceptance: the correct candidate passes; every deliberately wrong
   candidate fails for an inspectable reason.
2. **Build a task sheet.** Write six small coding tasks with inputs, allowed
   edits, outcome checks, and a known passing reference solution. Acceptance:
   another person can grade each without interpreting “looks good.”
3. **Measure repeatability.** Start with mock transcripts; optionally run
   real model trials when you choose to spend API usage. Acceptance: preserve
   every trial, report per-trial, any-of-three, and all-three results, and
   distinguish infrastructure errors from task outcomes.
4. **Check leakage.** Put a canary in an evaluator-only file. Acceptance:
   the agent's execution environment cannot read that file; a prompt telling
   it not to read the file does not count.

## 📚 references

- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) — outcome, transcript, and grader design.
- [SWE-bench — Evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/) — patch-based outcome verification.
- [Yao et al. — τ-bench](https://arxiv.org/abs/2406.12045) — repeated-trial reliability.
- [Anthropic — Eval awareness on BrowseComp](https://www.anthropic.com/research/eval-awareness-browsecomp) — retrieval-time contamination.

Sources checked 2026-10-26. The task and grader above are original teaching
examples, not benchmark results.

## 🚀 next

[Chapter 19 — Permissions](ch19_permissions.md): a correct result can still
have been obtained through an unauthorized action.

# Chapter 20 — Resume Without Repeating the Effect 🐢

> **Remembering a conversation and safely resuming an operation require different records.**

**Reading lab:** there is no `ch20_durable_execution.py`. This chapter designs
an extension to `agent.py`; durable operation tracking and idempotent external
tools are not implemented in the capstone.

## 🐢 guigui says

The agent publishes a documentation revision. The server accepts it. Before
the response reaches your program, the connection drops. Your transcript
contains the `tool_use`, but no `tool_result`.

Did publication fail? Did it succeed? Should you retry? The network exception
answers none of those questions. Recovery begins by admitting what the
program does not know.

## the planted misconception

Chapter 09 gives us a replayable conversation. It is tempting to conclude:

```python
messages = replay_session()
run_agent(messages)  # therefore every interrupted action is safe to resume
```

But a transcript contains observations, not a transaction spanning your
process and every tool. In `agent.py`, the assistant message is saved before
tools execute; tool results are saved after the batch. A crash between those
points can leave one tool completed and another unstarted. Neither an
absent result nor a resumed model call identifies which effect happened.

The updated capstone persists compaction snapshots, which restores the
conversation representation more faithfully. That still does not create
durable approval records, per-operation receipts, or external deduplication.
`Session._write()` flushes Python's file buffer, but does not call `fsync`;
JSONL formatting alone is not a guarantee against power loss or concurrent
writers. State the failure model before claiming crash safety.

## one running operation

Extend the documentation task with a hypothetical tool:

```text
PublishRevision(site="tutorial", content_hash="abc123")
```

The user has authorized that exact revision. Assign a stable operation ID
before dispatch and persist the normalized payload, its digest, approval,
and status. Do not ask the model to generate a fresh identity on every retry.
An operation ID names this intended publication, not merely its current
`tool_use` message.

| Record | What it answers |
|---|---|
| Conversation log | What did the user, model, and tools say? |
| Execution checkpoint | What step is next, and what state does it need? |
| Operation record | What effect was requested, with what authorization? |
| External receipt | Which remote object or revision actually exists? |

These can share a database, but their meanings remain distinct. A checkpoint
should include a schema version, run identity, step, necessary state, pending
operations, and references to completed results. Summarized prose is useful
model context; it is a poor substitute for those machine-checkable fields.

## the important state is unknown

Use a small state machine:

```text
prepared -> awaiting_approval -> ready -> dispatched -> succeeded
                                              |       -> failed
                                              +------> unknown
unknown -> reconciled_success | safe_retry | needs_review
```

`failed` means there is evidence the operation did not commit, such as a
documented rejection before execution. `unknown` means the request may have
committed. A timeout, lost connection, or worker crash after dispatch usually
belongs in `unknown` unless the tool's contract gives stronger evidence.

On recovery, examine the operation record before involving the model:

1. Return a saved receipt for a known completed operation.
2. For a ready operation, check current authorization and dispatch it.
3. For an unknown operation, query the service by operation ID when possible.
4. Retry only under a documented deduplication contract or after establishing
   that the original did not commit. Otherwise pause for reconciliation.

An eventually consistent “not found” response may be insufficient evidence
of absence. Follow the service's visibility and retention contract. This
decision belongs in deterministic recovery code, not in a model's guess
about what probably happened.

## show me idempotency

An idempotent operation can be repeated without adding another intended
effect. A client key works only if the receiving service enforces its
meaning. AWS discusses caller-provided request identities and rejecting
incompatible reuse of the same identity.
([AWS, safe retries](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/))

This local, executable fake publication service demonstrates that contract.
It uses one SQLite transaction for its receipt and simulated effect:

```python
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory


def publish(db, operation_id, payload):
    with db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute(
            "SELECT payload FROM revisions WHERE operation_id = ?",
            (operation_id,),
        ).fetchone()
        if old and old[0] != payload:
            raise ValueError("operation ID reused with different content")
        if not old:
            db.execute("INSERT INTO revisions VALUES (?, ?)",
                       (operation_id, payload))
    return {"revision": operation_id}


with TemporaryDirectory() as folder:
    db = sqlite3.connect(Path(folder) / "service.sqlite")
    db.execute("CREATE TABLE revisions (operation_id TEXT PRIMARY KEY, payload TEXT)")
    first = publish(db, "run-7:publish-1", "new docs")
    second = publish(db, "run-7:publish-1", "new docs")
    assert first == second
    assert db.execute("SELECT count(*) FROM revisions").fetchone()[0] == 1
    try:
        publish(db, "run-7:publish-1", "different docs")
    except ValueError:
        print("duplicate suppressed; conflicting reuse rejected")
    else:
        raise AssertionError("conflicting payload was accepted")
    db.close()
```

The fake service owns both deduplication and the effect, so it can commit
them together. A caller cannot obtain the same guarantee by writing a local
“done” flag after calling an unrelated publication API. The crash window
between remote success and local recording remains.

Production keys also need caller/tenant scoping and a documented retention
period. Reuse the key for retries of this operation; use a new key for a new
intentional publication, even when content happens to match. A hash of the
payload alone can accidentally merge distinct user requests.

## put tool intent in an outbox

A useful next exercise is a local transactional **outbox**. In one database
transaction, write the next execution state and a row describing the pending
tool request. A worker claims the row, performs the tool call, then commits
its receipt and the next state. A crash before dispatch leaves work to do;
a crash after dispatch leaves an operation to reconcile.

An outbox closes the gap between saving local workflow state and remembering
that work must be sent. It does not make remote delivery exactly once.
Delivery may repeat, so the receiving operation still needs deduplication.
AWS's outbox guidance explicitly calls out duplicate delivery and idempotent
consumers.
([AWS, transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html))

Keep the first version single-worker. Before adding concurrency, use atomic
claims and account for a worker resuming after its lease expired. Two workers
holding different local opinions about ownership must not create two remote
publications. Unique keys at the effect boundary remain valuable even with
careful scheduling.

## approval must survive a restart

Persist an approval with the operation identity, normalized payload digest,
approving principal, scope, timestamp, and relevant conditions. On resume,
check that it still authorizes this request. A changed target, changed
payload, expired grant, or revoked access requires a new decision. A matching,
still-valid authorization should not force the user through repeated prompts.

Keep a paused run's next step explicit. Resuming after an approval should not
rerun arbitrary setup code that already caused effects. Record nondeterministic
decisions and completed tool results so replay uses the same operation
identity and known outputs.

Durable execution systems help with this orchestration, but they do not
automatically make every external API idempotent. Temporal documents that
completed Activities are not replayed, while an Activity whose completion
was not recorded may be retried; its guidance therefore requires attention
to application-level idempotency.
([Temporal, Activity definitions](https://docs.temporal.io/activity-definition))

## ⚠️ the failure: retrying uncertainty

`with_retries()` in the capstone handles selected model/API failures. It is
not a universal safe wrapper for publishing, sending messages, provisioning
resources, or invoking arbitrary shell commands. A shell timeout also does
not prove that all descendants stopped or that no write occurred.

If a service provides neither deduplication nor a reliable lookup, automatic
retry can be the wrong recovery action. Preserve the unknown state and ask
for a concrete reconciliation decision. A compensating action, such as
reverting a revision, is another authorized operation with its own receipt;
it does not erase what external observers may already have seen.

## 📝 homework

1. **Test the receiver.** Run the SQLite example, then call `publish` ten
   times with one key. Acceptance: one revision exists; a changed payload
   with that key is rejected.
2. **Inject the ambiguous crash.** Create a separate caller database and
   fake service database. Kill the caller after service commit but before
   saving its receipt. Acceptance: restart reuses the same key, obtains the
   existing receipt, and leaves exactly one revision in the fake service.
3. **Add an outbox.** Persist execution state and pending intent in one local
   transaction. Acceptance: crashes before commit dispatch nothing; crashes
   after commit leave discoverable work; unknown writes are never silently
   relabeled as definitely failed.
4. **Resume approval.** Pause, approve, restart, and then alter the payload in
   a separate test. Acceptance: the unchanged authorized operation proceeds;
   the altered one cannot use the old approval. All tests use local fakes.

## 📚 references

- [AWS Builders' Library — Making retries safe](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) — request identity and retry semantics.
- [AWS — Transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) — local atomicity and duplicate delivery.
- [Temporal — Activity definitions](https://docs.temporal.io/activity-definition) — replay, retries, and effect idempotency.

Sources checked 2026-10-26. Framework references explain the boundary;
implementing the exercises requires only ordinary Python and SQLite.

## 🚀 next

Return to [`agent.py`](../agent.py). Trace one request through context,
`tool_use`, authorization, execution, `tool_result`, and persistence. You
should now be able to identify which guarantees it implements, which it
approximates, and which an application would need to add.

# UM native evolution: support attribution and retained receipt identity

**Date:** 2026-11-02. **Outcome:** Passed within the bounded authoring/read-body scopes below;
the coordinator owns subsequent assembled native regression and qualification.

Consumers are [UM-06/07 native evolution](../../../plans/unified-domain-model/native-authoring-and-evolution.md),
[UM-14 integration/adoption](../../../plans/unified-domain-model/integration-adoption-and-qualification.md)
and their [coordinator](../../../plans/unified-domain-model_2026-11-01.md).
These files retain the manual authoring and contrary-data investigation; they add no runtime
registry, database, receipt policy or validator framework.

## Questions and results

- **87 authoring/replay passed:** the existing native lifecycle generated four transitions,
  61 desired objects, 12 SQL-standard bodies and zero ordinary DDL. Actual finalized compiler-23
  release admission, new receipt-helper optional-row ABI, v4-to-v5 validation-contract separation,
  stale directive and column-drift refusal, repeated Alembic no-op, empty current candidate,
  caller-role preservation and rollback to 82 passed. No book migration was performed.
- **Retained-data body passed:** the exact new Core read body returned the original task-10
  `integrated` publication's immutable v4 receipt on the actual book database. It matched independently
  fetched receipt/product scalars; a wrong pin returned no row. The transaction was read-only and
  the database stayed at 82. This establishes body-on-retained-data behavior, separately from the
  deployed SQL-standard helper's owned author-database rehearsal.
- **Post-callback comparison failed as recorded:** the later Python optional-support default fix
  changed one captured input, `execution/implementation/pdf/integrated.py`, and its derived model ID.
  Strict comparison found one descriptor transition; it was not suppressed or folded into 87.
- **88 authoring/replay passed:** a forward successor captured exactly that descriptor-only change.
  Native functions, policy, schema, compiler 23 and epoch v5 remained unchanged. Actual admission,
  drift/stale-state refusal, frozen replay, repeat no-op, empty current candidate and rollback to
  82 passed. Frozen 86/87 bytes were preserved.

The support rule is one-hop attribution: every declared edge resolves an exact admitted input pin
and coverage ID with equal scope/family. An integrated complete claim requires at least one
matching complete input; matching mixed supports and weaker outcomes remain allowed. Native/direct
producer coverage can be intrinsically qualified without supports. Historical input claims are not
recursively revalidated, and original v4 assurance is not relabelled as current v5 conformance.
Current v5 validation refuses stale unfinished receipts; published reads retain their original receipt.

## Execution context and commands

Linux x86_64; Python 3.14.10; PostgreSQL 18, dedicated local port 5434; SQLAlchemy 2.1.6;
Alembic 1.20.1; pglast 8.7; psycopg 3.3.6; Pydantic 2.14.1.

Authoring authenticated the already-owned database
`cs_sem_pdf68_author_20261101_44132f1db0`, OID `14010645`, owner `paul`, ownership token
`1dbfc2773c354652b64626aaa56eac35`. Each caller-owned transaction started and rolled back to
`semantic_pdf_retire_20261101` (82). The separate retained-body SELECT used
`corpus_pdf_20261101`, also at 82, with `transaction_read_only=on`; no body hydration or rebuilding.

Commands executed from the repository root:

```sh
uv run python build/um87_author.py
uv run python build/um87_freeze.py
uv run python build/um87_frozen_wrapper.py
uv run python build/um87_retained_validation_body.py
uv run python build/um87_post_callback_candidate.py
uv run python build/um87_post_callback_delta.py
uv run python build/um88_author.py
uv run python build/um88_freeze.py
uv run python build/um88_frozen_wrapper.py
```

`sources/` preserves those harnesses as executed; `raw/` retains bounded output and result/source
hash manifests, including the failed strict comparison. The retained-body source restores the exact
unused conditional branch that was removed from its build copy after execution. Original output
paths and database assertions remain in the scripts. Author/replay commands archived under the
then-current preceding hash fence before the Python descriptor constant advanced; they are dated
execution records, not a portable bootstrap recipe. Existing output directories were never overwritten.

## Frozen outputs and contrary receipt

Production artifacts remain with the Alembic revisions rather than being duplicated here:

| Revision | Native state SHA256 | Admission SHA256 |
|---|---|---|
| `semantic_pdf_support_20261102` (87) | `7cf083bf4c94aa4da6140a3faa1e0b7cfa920e2b7e364fc42eec2a057d65685d` | `6f0ce9a963e883a469e09169a201aab8d4b00ffca5d87ba8e512894a630e0459` |
| `semantic_pdf_callback_20261102` (88) | `abed2441f4983c5731f786efe96b485f58f069327c1ca44794daa973c2d1276b` | `30e5650af9e6c2846c3531dd1ccac622bc570dbc01f9ac9666fd23df6996f310` |

The contrary publication pin is task `10`, key `integrated`, logical digest
`d3482c7126a5db75d8bb1962bb34cabd1b8f772bc136cd3f5987744dfec7bce0`.
Its original projection contract is
`f20f21df7f2eda84fe03e0cec6a556542606754a703f4f4078b3cfd42314c1bb`;
its original native contract is
`2d74d4740e92af5042978c40c3f1fa62f14758791977ae655fee99ca7952ea9d`.
Full scalar expectations are in `raw/retained-body.json`. `copy-manifest.json` records the preserved
copies' hashes and sizes. No database files, document bodies, staging payloads, caches or environments
are retained here. The root will finalize the accepted evidence record/index separately.

## 89 continuation: retained reads and observation wire input

The coordinator's combined88 run reported 54 passed and four failed: two observer expectations
were repaired in tests, while two genuine `operations.py` defects required implementation changes.
The latter removed a retired write gate from published reads in favor of the shared producer
receipt/schema/read authority, and separated Python observation validation from JSON metadata
serialization. The test-only repairs are not claimed as implementation changes here.

Strict authoring found exactly one descriptor transition: captured input
`execution/implementation/invocation/operations.py` changed from
`0d71bbb079a91bdd813c1cc60e8fb8a3df2f62e2f9e15bb85fe5d171125ed75a` to
`4b99c113f0968236b1770ec288b9fb4fe8de96450c41553e4f353beb555b92d6`, with its derived model ID.
Native functions, policy, schema, compiler23 and epoch v5 were unchanged.

`semantic_op_read_20261102` (89) passed actual current admission, stale-state and column-drift
refusal, exact frozen82→89 replay, repeat-upgrade no-op, empty current candidate, caller-role
preservation and rollback to82. Frozen88 and the book database were unchanged. Its native state
SHA256 is `10d2012013bd46a9e425d615d16033af527ef7ae709eb1f1a387a51f0be12544`; admission SHA256 is
`b5947914eb414862aca0dbcdf7b0f719cf9784ad4ea783afd28288c8afb2a30c`.
The root owns the affected regression after this endpoint.

Executed commands were `uv run python build/um89_author.py`,
`uv run python build/um89_freeze.py` and `uv run python build/um89_frozen_wrapper.py`.
Exact source/result copies are retained under `sources/` and `raw/`; their additional hashes/sizes
are in `copy-manifest-89.json`. Earlier copies and outputs were not overwritten. No new workload
was run solely to assemble this evidence continuation.

## 90 continuation: record-first header custody

Strict current-desired comparison found one descriptor transition after the maintained header
reader began resolving record publications before using the qualified historical runtime path.
Only captured input `execution/implementation/pdf/native_source.py` changed, from
`64a265867aac6f151efa7c4f6bdbdd7cc5093f6a72bc59cfff1bdc601e0b51a0` to
`0a18609bb6d81d81df5d391b7d6129ef39a904c0d4f378196d5e5bcf62b9f154`, with its derived model ID.
The adjacent CLI routing change is not a separate captured descriptor input. Native functions,
schema, compiler23, support policy and validation epoch v5 remain unchanged.

On 2026-11-02, `semantic_pdf_header_20261102` (90) passed actual current release admission,
stale-state and column-drift refusal/restored admission, exact frozen82→90 replay, repeated
upgrade no-op, empty current native/ordinary candidate, caller-role preservation and rollback82.
Its single descriptor transition retains 61 desired objects and 12 SQL-standard bodies with no
ordinary DDL or physical alias. Frozen89 hashes remain unchanged; the book database was untouched.
These are scoped authoring/admission results; the coordinator owns affected product qualification.

The native-state SHA256 is
`6d7deb684b2305ad330c313535469d37e2f416f54c468b9a8f23286bfda575fc`; admission SHA256 is
`18d0432ab7b9abf3c88883de5701f0d74841c5d76f8e83dcc43bdc9d95faea13`.
The Python descriptor constant and exact companion descriptor body agree at
`44b6fbd388562df43806fb91311988f989f0deea747cffddc81c149ff53329e1`.

Executed commands were `uv run python build/um90_author.py`,
`uv run python build/um90_freeze.py` and `uv run python build/um90_frozen_wrapper.py`.
Their exact sources and bounded results are preserved in nine new files listed by
`copy-manifest-90.json`. Prior copies and manifests were not overwritten, and no workload was
run solely for this continuation.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 1 superseded.


**unified-domain-model**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Scoped native87–90 evolution and retained receipt authority](records/um.native-evolution90.json) | UM-06/07/14 | passed | UM-06, UM-07, UM-14 | 2026-11-02 |

**Superseded**

| Record | Superseded by | Finalized |
|---|---|---|
| [Scoped native87–89 evolution and retained receipt authority](records/um.native-evolution.json) | um.native-evolution90 | 2026-11-02 |
<!-- evidence-index:end -->

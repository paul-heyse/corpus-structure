# Comparative library leverage reviews

**Account state:** first comparative review, 2026-10-29. It covers all current codebase
opportunities: CBO-001 to CBO-025.

**Status:** every recommendation is **Proposed**. This account compares complete options and
recommends bounded targets. It does not approve scope or implementation, change a rule, or replace
the formal design review due under the binding's cadence (see [further reviews](#further-reviews)).

The [opportunity review skill](../../../.claude/skills/leverage-opportunity-review/SKILL.md)
maintains this living collection. It consumes [codebase opportunities](../codebase/README.md) and
[library applicability assessments](../libraries/README.md), and can investigate further or
challenge their premises. Read the [framework](../library-leverage-framework.md),
[base patterns](../patterns.md), [additional patterns](../assessment-patterns.md) and
[writing guidance](../references/collection-writing.md).

<a id="baseline"></a>

## Inputs and baseline

| Item | Value |
|---|---|
| Codebase account consumed | Published at `d739b88`, with dated library notes from `4c6d7f6`. Premises were refreshed in place through `c13fbb0`, adding CBO-025 ([codebase baseline](../codebase/README.md#baseline)) |
| Library assessment consumed | Published at `4c6d7f6`: 52 types across 19 libraries |
| Additional patterns consumed | LOP-X001–X007. This review added X008–X011 and refined X001, X002, X006 and X007 |
| Source state | Review T0 `346bfe1`. Refresh at `c13fbb0`. Reviewers finished at `0350a7a`, with the concurrent SP-08 working tree uncommitted (notably `cli/regenerate.py` and `semantic/domain_operations.py`) |
| Delta check | Against `87c0503` (three SP-08 commits after `0350a7a`). No recommendation was invalidated. Precedent added to the [immutability decision](native-integrity-and-execution.md#sem-immutability) |
| Library realizations (`uv.lock`) | linkml / linkml-runtime 1.12.1, SQLAlchemy 2.1.5, psycopg 3.3.6, psycopg-pool 3.3.3, Alembic 1.20.0, Pydantic 2.14.1, rule-engine 5.1.0, FastMCP 4.1.3, DuckDB 2.0.0, pyarrow 26.0.0, ADBC PostgreSQL 1.13.0, cattrs 26.2.1, pytest 9.2.0, Hypothesis 6.170.12, linkml-term-validator 0.4.5, curies 0.15.5; PostgreSQL 18 (5434 cluster) |
| Criteria | Design principles core 3.3 (FP-01–07, A1–A4, DP-01–24) with the efficient-architecture heuristics; the code-intelligence profile where served claims are involved; the repository binding |
| Decision context | ADRs 0012, 0018, 0024–0027, 0029, 0030; the [pivot coordinator](../../plans/semantic-model-pivot_2026-10-29.md) and its SP-08/09/10 pages; D3, D7 §5.3, D8; test-audit findings DTA-002, 003, 005, 007 |

**Method.**
1. **Premise refresh.** A code-mapper refreshed every CBO against current source. The coordinator
   verified the decisive evidence and recorded it in the codebase account.
2. **Five independent reviews.** One design-reviewer per decision group judged complete options
   with direct source reading. Scratch checks ran outside the repository; new library research was
   allowed.
3. **Probes.** Three, all recorded in
   [evidence](../../design_review/evidence/2026-10-29_library-leverage-review-probes/README.md):
   - Alembic drift at head;
   - template-clone ACL loss and replay;
   - release-preparation timing.
4. **Synthesis.** The coordinator verified each decisive claim behind a recommendation or a
   rejected premise ("coordinator-verified" on the topic pages), then reconciled the groups.

## Topic pages

| Page | CBOs | Shared decision it owns |
|---|---|---|
| [Consumer read boundary and interfaces](consumer-read-boundary.md) | 001, 025, 016, 012, 007, 023 | What counts as a query language; exact-or-refuse predicates; one snapshot opener; refusal registry; export route |
| [Release lifecycle and product contract](release-lifecycle.md) | 003, 013, 009, 002, 021, 017, 024 | Opening versus verifying a release; product index and NaN gap; identity determinants; composer shape |
| [Native integrity and execution](native-integrity-and-execution.md) | 019, 008, 014, 015, 020, 022 | **Immutability of `sem.*` and admitted rows, enforced by triggers**; drift check and freeze point; authoring emitter |
| [Retirement dependencies](retirement-dependencies.md) | 006, 005, 018, 008 (location) | Equivalence evidence versus policy; the declared rule view; where the set kernels live |
| [Engineering and operator workflows](engineering-workflows.md) | 010, 011, 004 | Head template with ACL replay; streamed outcome classification; principal hardening and pool rule |

<a id="synthesis"></a>

## Current synthesis

The pivot's remaining work is SP-08 (consumer migration), SP-09 (regeneration, retirement and
cutover) and SP-10 (qualification). What matters most for that work is four connected choices.

### 1. Let one owner decide equivalence

The domain and evaluation kernels already decide equivalence differently, and the domain kernel
drives selection. The domain kernel treats agreement at six numeric sample points as proof of
equality. Consolidation then drops all but one of the facts it considers equal, while the
evaluation kernel would grade the same pair as undecided.

**Recommendation ([CBO-006](retirement-dependencies.md#cbo-006)):** one kernel reports *evidence*,
and each consumer maps that evidence to decisions.

**Unsettled:** which numeric policy each consumer uses. That is an owner decision under D7 §5.3,
and it changes what consolidation selects.

### 2. Open a release cheaply, and verify it at named points

Every read session re-runs full preparation. On the statistics pack, a cold preparation took
2.18–2.45 s; about half of that is OWL/SHACL generation that no reader uses. Every read is also
coupled to the whole producer toolchain.

**Recommendation ([CBO-003](release-lifecycle.md#cbo-003)):**
- `open_release` builds the runtime boundary from archived products.
- `verify_release` runs at persist, activation, run start and on operator request.
- This needs compiler 11, which adds `native_range` and `alias` to the archive.
- It should be bundled with the composer ([CBO-002](release-lifecycle.md#cbo-002)) and the tiered
  determinants ([CBO-009](release-lifecycle.md#cbo-009)) into **one deliberate identity change before
  SP-09's production regeneration**. Otherwise the regenerated release would be stranded.

### 3. Enforce the immutability the design already declares

Nothing prevents `UPDATE` or `DELETE` on `sem.*` or on admitted content rows. The publisher can
also update every `data` table. Whole-realization meaning rechecks stand in for the missing guard
([LOP-X008](../assessment-patterns.md#lop-x008)).

**Recommendation:** refusal triggers, attested by the existing execution descriptor
([shared decision](native-integrity-and-execution.md#sem-immutability)). This:
- lets [CBO-019](native-integrity-and-execution.md#cbo-019) drop the meaning-only rechecks;
- gives the open/verify split a sound integrity basis.

The SP-08 source-frame tables adopted exactly this shape after the reviewers finished.

### 4. One public read route

Serving is built on private kernel internals. The kernel's public query and continuation scheme
has only test callers, and pack plugins already import private names
([LOP-X010](../assessment-patterns.md#lop-x010)).

**Recommendation ([CBO-001](consumer-read-boundary.md#cbo-001), with
[CBO-025](consumer-read-boundary.md#cbo-025)):**
- Promote the kernel primitives that serving needs, and keep serving policy in serve.
- Make the journey token the only continuation.
- Open every snapshot through one read-only opener.
- Predicates are **exact or refused**. A closed, named predicate vocabulary is not a query language.

### Choices to retain

Retaining the current design is the strongest complete case for:
- [CBO-021](release-lifecycle.md#cbo-021), [CBO-017](release-lifecycle.md#cbo-017) and
  [CBO-024](release-lifecycle.md#cbo-024), each with small adjustments;
- [CBO-023](consumer-read-boundary.md#cbo-023);
- [CBO-007](consumer-read-boundary.md#cbo-007), keeping the physical pyarrow export;
- the pool and settings shape of [CBO-004](engineering-workflows.md#cbo-004), with hardening.

<a id="index"></a>

## Recommendation index

Verdicts:
- **Target**: a recommended bounded target.
- **Retain**: retain the current design; adjustments are named.
- **Unsettled**: a decisive condition is still open, with its settling evidence.

A premise the review corrected is noted in the Premise column.

| CBO | Verdict | Recommendation | Premise |
|---|---|---|---|
| [001](consumer-read-boundary.md#cbo-001) | Target B | Public kernel primitives, `hydrate` and binders; Reader stays in serve; one continuation; exact-or-refuse predicates; bounded `explain` | Demand for explaining many facts is not yet present; a live `object=` filter defect was found |
| [002](release-lifecycle.md#cbo-002) | Target C | `acquire_pack` plus a pure `compose_release` with one root | importmap is not decisive (corrected) |
| [003](release-lifecycle.md#cbo-003) | Target C | `open_release` / `verify_release` with a process memo; compiler 11 | Measured; graph artifacts consumed only by `ci schema compile --out` |
| [004](engineering-workflows.md#cbo-004) | Retain + harden | Sequential engines per purpose; required `purpose`; no read-as-owner fallback; principal assertion; one principal-constant owner | Largely realized |
| [005](retirement-dependencies.md#cbo-005) | Target B | Declared semantic rule view keeping the `semantic-domain-2` contract; `result_type` route | `rulelang` is not legacy; SP-09 names no module retirements (corrected) |
| [006](retirement-dependencies.md#cbo-006) | Target D; policy **unsettled** | Evidence-reporting kernel in `methods/math`, with policy per consumer | Two kernels already diverge (verified) |
| [007](consumer-read-boundary.md#cbo-007) | Retain | Physical pyarrow export through the shared opener; subset and semantic exports wait for demand (then use the query path) | Physical export complete; DuckDB `COPY` only for derived tables |
| [008](native-integrity-and-execution.md#cbo-008) | Target O1 + O4 | Reconciliation revision (drop and re-add CHECKs, rename UNIQUEs); `command.check` in SP-10 and after migrate; generated descriptor | 49 differences, all naming-only, plus in-place edits to committed 0027/0028 |
| [008 location](retirement-dependencies.md#cbo-008-location) | Target B now | Pure move of the physical lowering into `semantic/`; structured `ph:*` deferred | — |
| [009](release-lifecycle.md#cbo-009) | Target B | Tiered determinants: bytes only for identity; acceptance libraries at verify; pin pyoxigraph; drop valuesets; SymPy in the run manifest | Pronto not needed (corrected) |
| [010](engineering-workflows.md#cbo-010) | Target A | Session head template, ACL replay and equality assertion, one residue owner, `semantic_database_at(revision)`, a TEMP posture test | Probe-confirmed ACL loss |
| [011](engineering-workflows.md#cbo-011) | Target A | pytest-reportlog plus faulthandler-exit plus `--hypothesis-profile=ci` plus a stdlib classifier; nextest `--no-tests=warn` | pytest-timeout signal method silently cancelled by the grammar (corrected) |
| [012](consumer-read-boundary.md#cbo-012) | Target C | One refusal registry: `classify_error` for `DBAPIError`, CLI `refusal(json)`, MCP `@refusing` decorator | Middleware cannot suppress tracebacks (corrected) |
| [013](release-lifecycle.md#cbo-013) | Target, two steps | NaN/inf fix now (per-field `allow_inf_nan=False`, no byte change), then a non-identity `ReleaseIndex` | The gap is on the serving boundary; NaN would be served as null |
| [014](native-integrity-and-execution.md#cbo-014) | Target C | Wire the existing generator as the authoring emitter with a parity test; delete `deploy_routines` | Generator is not stale (corrected) |
| [015](native-integrity-and-execution.md#cbo-015) | Target B; lexical form **unsettled** | Written specification plus Hypothesis differential parity plus pinned vectors | `decimal_lexical` is neither authored nor canonical |
| [016](consumer-read-boundary.md#cbo-016) | Target B on D | One classifier plus a visitor over validated models | Six observed drifts |
| [017](release-lifecycle.md#cbo-017) | Retain | Plus cattrs `= ()` defaults | — |
| [018](retirement-dependencies.md#cbo-018) | Target (ii) | Relocate the kernels; `relation.query` and TEMP macros; independent expectations first | — |
| [019](native-integrity-and-execution.md#cbo-019) | Target B; C conditional; D **unsettled** | After immutability: drop meaning-only rechecks, keep the cumulative validators | Cumulative obligation identified |
| [020](native-integrity-and-execution.md#cbo-020) | Target B | Database-derived sets; identity, required and display properties only | Possible over-wide evidence carry-forward (owner to confirm) |
| [021](release-lifecycle.md#cbo-021) | Retain | Eager induction once | — |
| [022](native-integrity-and-execution.md#cbo-022) | Target B (low) | Semi-naive rounds on the existing work table | — |
| [023](consumer-read-boundary.md#cbo-023) | Retain | `run_in_thread=False` if a grammar tool appears | — |
| [024](release-lifecycle.md#cbo-024) | Retain | Revisit on a new term-validator release | — |
| [025](consumer-read-boundary.md#cbo-025) | Target C | One `snapshot(engine)` opener with `postgresql_readonly` | Six openers, not seven (corrected) |

<a id="order"></a>

## Priority versus prerequisite order

**Priority**, by consequence:
1. CBO-006, which affects selection correctness now.
2. The identity bundle (CBO-003, 002, 009) and the CBO-013 NaN fix.
3. The read boundary (CBO-001, 025).
4. Drift and the freeze point (CBO-008, 014).
5. Engineering routes (CBO-010, 011) and principal hardening (CBO-004).
6. The rest.

**Prerequisite order** is separate:

| When | What | Why |
|---|---|---|
| Independent, any time | CBO-013 step 1; the `object=` filter fix; CBO-025 opener; CBO-008 lowering move; CBO-004 hardening; deleting `deploy_routines` | No identity, schema or contract change |
| Before CBO-019 B and before CBO-003 opening drops its row comparison | [`sem.*` immutability](native-integrity-and-execution.md#sem-immutability) | The integrity basis for both |
| Before CBO-008's reconciliation revision and the descriptor generation | CBO-014 emitter | The emitter produces both |
| Before CBO-015 parity tests, CBO-008 revision-pair tests and DTA-005 consumer tests | CBO-010 template (and CBO-002 composer for DTA-005) | Session-scoped databases and fixture inputs |
| **Before SP-09 production regeneration** | CBO-003 (compiler 11), CBO-002, CBO-009 together; CBO-005's `map[Value]` correction if taken; CBO-008-C if taken | Each changes release or physical identity; regeneration is the cheapest moment to accept that once |
| Before SP-09 deletes `core.values`, `core.keys`, `evaluate/equivalence.py`, `align.py`, `schema/rules.py`, `validate/views.py`, `consolidate/finalize.py`, `pool/*` | CBO-006, CBO-005, CBO-018, each carrying independent expectations | Backward dependencies ([LOP-X001](../assessment-patterns.md#lop-x001)); SP-09 has not yet named these deletions |
| Before SP-10 qualification | CBO-011; CBO-008 `command.check` | Outcome classification and physical-evolution check |

**Reinforcing mechanisms.**
- **The `ReleaseIndex` (CBO-013)** serves CBO-001's adapter selection and CBO-016's position index.
- **The snapshot opener (CBO-025)** serves CBO-001's binders, CBO-007's export and CBO-004's
  `conninfo`.
- **`classify_error` (CBO-004)** feeds CBO-012's refusal registry.
- **The CBO-014 emitter** produces CBO-008's reconciliation revision and the generated descriptor.
  The descriptor then attests the immutability triggers.

**Conflicts and how they were resolved.**
- **Single pool versus per-login pools.** Sequential per-purpose engines are retained, and D3 §1 is
  reworded as "one pool per authenticated login per process". Concurrent per-login pools wait for a
  long-lived process that needs two logins.
- **pyarrow versus DuckDB export.** pyarrow is retained for the physical export, because a DuckDB
  `COPY` hop drops `cs.*` metadata. DuckDB is reserved for derived analytical tables.
- **CBO-003 depending on immutability.** The review keeps a per-snapshot projection comparison in
  `open_release` for as long as immutability is not enforced.

<a id="unsettled"></a>

## Unsettled decisions

| Decision | Competing options and consequence | Settling evidence |
|---|---|---|
| Numeric equivalence policy per consumer (CBO-006) | "Numeric agreement establishes equivalence" (D7 §5.3, current domain path) versus "it only disproves" (current evaluation). Changes what consolidation selects and what scores mean | Decision by the D7 §5.3 and domain-operations owners; a no-database comparison of both mappings over fixture pairs shows the impact |
| Release persist and activate credentials (CBO-004) | Operator login reaching the publisher through `SET ROLE` (D3 states it) versus a fifth non-owner admission login | ADR-0025/0030 owner; bears on the [regenerate hazard](#defects) |
| MCP query/explain in SP-08 (CBO-001) | D8 §2 places MCP read tools in phase 1; SP-08 acceptance asks for real CLI/MCP dispatch | Owner decision; if MCP reads land, `explain` needs a bounded shape first |
| Template reading of "fresh … frozen deployment" (CBO-010) | Session template plus replay (equivalent at database level) versus per-test bootstrap | Operator reading of the PostgreSQL plan wording (DTA-002) |
| Encoder lexical form (CBO-015 C) | Authored-preserving versus plain `format(raw, "f")` | Specification choice |
| Persisted qualification key (CBO-019 C) and affected-subject scoping (D) | Persist now versus at the next transport revision; scope (c) versus keep whole-realization | SP-08 conflict-grouping need; a workload with many batches per realization |
| `eval.*` immutability | Include or exclude from the triggers | Evaluation owner |
| Subset and semantic exports (CBO-007) | Query-path answers versus capture subsets | An accepted consumer |
| Closure narrowing in known-input loading (CBO-020 C) | Recursive closure versus property restriction | Native traversal shown equal to the release-typed walk |
| `semantic-domain-2` type correction (CBO-005) | Bump to `semantic-domain-3` before SP-09 versus record as a known limit | Rule-view implementation |

<a id="defects"></a>

## Defects and hazards found during the review

These are not leverage claims. They go to their owners and are recorded here so that they are not
lost.

| Finding | Evidence | Owner |
|---|---|---|
| `claims` query `object=` filter reads the non-existent `typed_value.c.lexical` and raises `AttributeError`; no test passes `object` | `serve/queries.py:50` (coordinator-verified at `87c0503`) | SP-08 serving |
| The two equivalence kernels diverge, and one drives selection | [CBO-006](retirement-dependencies.md#cbo-006) (coordinator-verified) | D7 §5.3 / domain operations |
| ADR-0025 says the writer has no generic temporary-table creation, but revision 0007 grants the writer `TEMP ON DATABASE` | `0007_qualified_inference.py:21` | ADR-0025 owner |
| Committed revisions 0027 and 0028 were edited in place. The `eval.document_split` CHECK kept its digest name with a new expression | `01da23a`, `51bba6c` | SP-10 / ADR-0025 |
| **Uncommitted `cli/regenerate.py`** sets `SET LOCAL ROLE corpus_sem_publisher` before `persist_release`, but the publisher has only `SELECT` on `sem.*`; a first-time persist should fail with permission denied | Source reasoning over grants and `persist_release` inserts; not executed | Concurrent SP-08 author |
| `property_adapter` accepts NaN/inf on the serving boundary, and Pydantic would serialize NaN as `null` | [CBO-013](release-lifecycle.md#cbo-013) | Release owner |
| `explain` embeds whole-realization coverage, against D8 §3's bound | [CBO-001](consumer-read-boundary.md#cbo-001) | SP-08 serving |
| A read connection falls back to the owner login for any non-writer URL, and a test locks this in | [CBO-004](engineering-workflows.md#cbo-004) (verified) | Runtime settings |
| Dead `routines.deploy_routines` grants `UPDATE` on all `data` tables | [CBO-014](native-integrity-and-execution.md#cbo-014) | Native routines |
| Possible over-wide evidence carry-forward for all known entities | [CBO-020](native-integrity-and-execution.md#cbo-020) (not verified) | SP-08/09 |

<a id="rule-impacts"></a>

## Rule impacts

Recommendations do not change rules. Each item below goes through the existing decision route.
Accepted ADRs are immutable, so an ADR item means a follow-up or superseding record through
`just adr`, or a clarification in the owning section where the operator reads the current wording
as already allowing the change. **No recommendation changes a §B decision.**

- **ADR-0025:**
  - the writer-TEMP text versus revision 0007;
  - the freeze point for committed revisions (CBO-008);
  - permitting removal of meaning-only rechecks once immutability is enforced (CBO-019);
  - with ADR-0030 and D3, who persists and activates releases (CBO-004).
- **ADR-0024:** "only an explicit archive load recompiles" becomes open versus verify (CBO-003). The
  pivot page `domain-model-completeness.md` has matching reload wording.
- **`semantic-model-and-releases.md`:** "compiler versions" in the digest read as byte determinants
  (CBO-009).
- **D3:**
  - §1 and D9 "Connections": one psycopg pool per authenticated login per process. A short ADR is
    needed only if the operator treats this as a change.
  - The "Roles" paragraph is stale against the semantic principals (CBO-004).
- **D7 §5.3:** the numeric-evidence policy per consumer. ADR-0012's token form survives in the math
  module (CBO-006).
- **D8:**
  - §2 MCP read-tool phase;
  - §3 explain bound;
  - §5 exact-or-refuse predicates;
  - §6 "Parquet through DuckDB" read as derived analytical tables only (CBO-001, CBO-007).
- **`queries-and-consumers.md`:** the SP-04 continuation owner moves to the serve journey
  (CBO-001).
- **SP-10 plan and AGENTS "Commands":**
  - name `command.check` in the physical-evolution row (CBO-008);
  - classified `test-all` as the qualifying route (CBO-011).
- **Optional:** rule-view `VERSION` `semantic-domain-3` (CBO-005).

<a id="further-reviews"></a>

## Further reviews required

Under the binding's cadence, a **design/target review** is due before a substantial stage or a
changed ownership or dependency boundary. SP-09 is such a stage. The following recommendations
change boundaries and should be inputs to that review; this account does not start it:
- **CBO-001:** the kernel/serve boundary and the continuation owner. The reopen triggers already
  apply: private dependencies, including from pack plugins.
- **CBO-003:** the read path's dependency boundary on the producer toolchain.
- **CBO-006:** equivalence ownership leaves `evaluate`.
- **CBO-005 and CBO-018:** new semantic-owned rule-view and set-kernel modules.
- **CBO-016:** a repeated classifier, which is also a reopen trigger.

The immutability triggers, CBO-008's reconciliation and CBO-014's emitter sit inside accepted
boundaries, so a change/target review applies to them.

## Additional patterns

This review added four patterns to the [shared output](../assessment-patterns.md):
- [LOP-X008](../assessment-patterns.md#lop-x008): a declared invariant is stood in for by a recheck;
- [LOP-X009](../assessment-patterns.md#lop-x009): a consumer re-runs the producer to trust an
  immutable product;
- [LOP-X010](../assessment-patterns.md#lop-x010): a replacement boundary grows beside the kernel's
  public route;
- [LOP-X011](../assessment-patterns.md#lop-x011): outcome evidence is written only at orderly
  completion.

It refined four existing ones:
- X001: two kernels as a symptom;
- X002: name the freeze point;
- X006: repository-owned principal derivations;
- X007: assert equivalence where the clone is made.

Library corrections were integrated into the library accounts for:
- [pytest](../libraries/pytest/README.md);
- [linkml](../libraries/linkml/README.md);
- [fastmcp](../libraries/fastmcp/README.md);
- [rule-engine](../libraries/rule-engine/README.md);
- [postgresql](../libraries/postgresql/README.md);
- [pydantic](../libraries/pydantic/README.md);
- [alembic](../libraries/alembic/README.md).

<a id="limits"></a>

## Limits

- **Recording of scratch checks.** Reviewers ran read-only, with scratch checks outside the
  repository. Several claims rest on those checks and are not recorded as evidence:
  - FastMCP decorator behaviour;
  - NaN serialized as `null`;
  - `allow_inf_nan` per field;
  - rule-engine `result_type` agreement;
  - the text-equality divergence between the kernels.

  The three recorded probes are the only repository evidence.
- **Measurements.** The timing figures cover one pack on one machine. No suite timing, inference
  cost or query cost was measured. Qualitative execution judgments follow FP-07/A4.
- **Concurrent edits.** SP-08 edits were in flight. Line numbers in dirty files may shift. The
  regenerate hazard concerns an uncommitted tree.
- **Not inspected:**
  - golden storage validation under a release (CBO-016);
  - `core/tex` token-form ownership (CBO-006);
  - the internals of `validate_state` and the other validators (CBO-019).
- **Not a formal review.** This account is not a formal design review, an audit or an approval.
  [Plans](../../plans/semantic-model-pivot_2026-10-29.md) own scheduling and closure.

## Maintenance

Refresh in place. Reopen a choice when its decisive premise changes. The likeliest triggers are:
- SP-09 naming its deletions;
- the D7 §5.3 numeric-policy decision;
- the ADR-0025 owner settling writer TEMP and the persist credential;
- a compiler or LinkML upgrade.

Inherited judgments keep their 2026-10-29 evidence date until reconsidered. When a CBO retires,
carry any surviving mechanism rationale to its owner before removing its entry here.

## Unified-model comparison — 2026-11-01

The [integrated target review](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#4-corrections-and-complete-option-comparison)
compares deeper compiled-release governance with isolated consumer patches, universal graph
execution, broad Map/Datalog replacement and a general interpreter. It consumes the focused
[semantic](../libraries/unified-model-semantics_2026-11-01.md) and
[boundary](../libraries/unified-model-boundaries_2026-11-01.md) assessments. It is the primary
comparison owner for this engagement; the preceding CBO account retains its October 29 baseline.

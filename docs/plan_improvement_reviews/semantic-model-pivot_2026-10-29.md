# Semantic-model pivot — library-focused plan improvement review

**Proposed · 2026-10-29.** Source and plan baseline: `7cd34b4` (product baseline `ad4593f`).
This review covers all sixteen packages and completed pivot capabilities, prioritizing the
[completion audit and CA-01–CA-11](../plans/semantic-model-pivot_2026-10-29.md#13-completion-audit-2026-10-29).
It consumes the [CBO-001–025 comparative review](../library_leverage/reviews/README.md) and its
[detailed library investigations](../library_leverage/libraries/README.md). Those recommendations
remain proposals; their older source claims are refreshed below, not adopted by reference.

Root and three fresh read-only design reviewers examined model/validation, native integrity,
and consumers/science/analytics. Context7 preceded consequential primary/installed-source lookup.
Core 3.3, efficient-architecture heuristics 1.0, the code-intelligence profile 1.4, repository
binding and test-assessment companion informed the judgments. Concurrent edits to the diagnostic
audit and its probe folder are separately owned, preserved and not inputs to this review.

No production change, plan amendment, dependency change, migration, provider execution, regrade
or product qualification is performed. Source-inspected defects and reasoned recommendations
are distinguished from earlier tested mechanisms and measurements. Locations below are relative
to `python/corpus-structure/src/corpus_structure` unless otherwise qualified.

## Combined judgment

**Recommend a coordinated model-to-execution correction, followed by removal of redundant work
only after its integrity prerequisites exist.** The target is complete domain-model governance
with zero disconnected behavior. A named callback or native body digest cannot substitute for
actual model consumption. Ordinary algorithms remain appropriate implementations when their
inputs, outputs, applicability, effects and invariants realize the model's contract.

The most useful improvement is to make the prepared binding a reusable executable product:
resolved statement/reference roles, scoped constraints, typed phase/results, finite lifecycle
projections and declared graph/read contracts. This removes several independently maintained
interpretations together. It also supplies the dependable boundary needed to simplify release
loading, serving, scientific-policy adapters and native generation.

Completed snapshot/Arrow/DuckDB/pgpq, protected references and exact archive mechanisms deserve
preservation and targeted improvement. Replacing them wholesale, installing every researched
library or building a universal workflow/constraint interpreter would increase the burden without
settling the identified gaps. No disconnected exception is accepted as completion.

<a id="I01"></a>
## I01 — Compile contracts that real operations consume

**Recommend; highest priority.** CA-01/02/04/05/06/11; CBO-002/005/013/016/017/021/024.
Owners: SP-01, SP-C01–SP-C05 and affected SP-06–SP-08 callers.

Current `semantic/contracts.py:498–579` resolves approved symbols and compares authored contract
records. Actual source-readiness/hold/scientific results and submission enforcement compositions
still differ from those records. `prepare.py:811–813` attaches conditional validation without its
accepted-value scope; statement binding is resolved too late; graph projection accepts an
unresolved label. Fixing individual literals would leave the next model change exposed.

Use LinkML SchemaView induced definitions as the single normalization input, retaining exact
imports and explicit diagnostic/refusal boundaries. Produce resolved statement/qualification and
reference-role descriptors, normalized constraint scope, operation phase/result products and
projection contracts. Keep each specialized algorithm with its owner; make its actual boundary
consume these products. Frozen cattrs products remain suitable; replacing them with another
class library does not itself fix correspondence.

Use Pydantic `create_model`, discriminated models, reusable `TypeAdapter` and typed result
constructors for real phase alternatives. Model source readiness separately from task completion,
hold decisions separately from submission dispositions, and assessment alternatives separately
from selection outcomes. Bind submission's read/packet/attempt invariants to its actual composed
session/native boundary, not only the pure locator helper.

For conditional constraints, compare separate structural/projected adapters with explicit
`ValidationInfo.context` passed through the owned adapter boundary. Prefer separate explicit
validation purposes when omission of context would silently skip enforcement. Context is an
execution selector, never authority for a caller to waive an invariant. Keep one normalized
rule product for local and native lowering; accepted-only checks execute against selected closure.
Use jsonschema's structured instance/schema paths for diagnostics rather than flattening errors
or treating generated-schema success as enforcement.

Resolve graph `ProjectionContract` against the bound execution product before graph construction
and PySHACL validation. Retain RDFLib qualified occurrence nodes, related-node closure, positions,
explicit nulls, inference none and disabled imports/mutation. Translate PySHACL report nodes
into existing typed diagnostics with focus node, result path, source shape and constraint component;
distinguish nonconformance from shape-loading/runtime `ValidationFailure`. Focus-node/shape
selection can reduce work only within an already complete declared closure. linkml-map or a direct Oxigraph store
is not needed merely to replace a missing contract lookup. Revisit only for an actual mapping or
storage consumer whose complete semantics it preserves.

Expose model-centered mismatch diagnostics through existing preparation/admission and schema/db
command owners: identify contract, authored location, enforcing consumer and bounded remedy.
Mechanically derivable outputs can be emitted for the next reviewed revision; this is not a
second editable schema or a generic semantic-code analyzer. Exact CLI names and the final
interaction design remain subsequent planning choices.

**Preserve/challenge:** valid explicit subtypes and wrong base/unrelated bindings; malformed
binding refuses activation without pointer change; an unselected nonconforming report remains
representable while invalid selected state refuses; every actual finite result alternative has
its correct domain; missing read obligations cannot be bypassed; unknown graph IDs refuse.
Independent expectations challenge the model, while derivation checks challenge its projections.

**Benefit/burden:** one shared correction improves several current callers and future domain
extensions. It requires deliberate compiler/execution compatibility changes and native adoption;
merely adding annotations would purchase no such benefit. FP-04/05, DP-03/06/08 and CI-04 apply.

<a id="I02"></a>
## I02 — Retain a model-derived native authoring route

**Recommend.** CA-01/06/07; CBO-008/014. Owners: SP-02/SP-03/SP-C03, SP-09/SP-10.

Wire the existing transport generator as an authoring emitter, with explicit relation order and
disposal policy. Use SQLAlchemy `CreateTable`/constraint/index compilation for representable DDL,
and its dialect identifier preparer for deterministic SQL. Keep reviewed native kernels for the
PostgreSQL-specific gap. Emit finite lifecycle tuples from the trusted catalog and descriptor
inputs/body hashes from the reviewed generated SQL. SQLAlchemy 2.1.5's installed `CreateView`
can also freeze the Core-derived selected-fact SELECT alongside the tables, closing the fixed-view
drift seam without a new view-management dependency. The installed `sql/ddl.py:758–850`, rather
than older Context7 examples, establishes this exact-pin capability. Generated products remain frozen migration
artifacts; historical migrations never import the newest compiler or get rewritten in place.

Current ordinary edge tuples match all 38 modeled tuples. That is a useful source comparison,
not a maintained derivation route or proof of all procedural effects. Add direct model-to-product
comparison for these finite products plus independent invalid-edge/effect cases. Delete the obsolete
`deploy_routines` deployment helper after its current callers are checked; extract useful helpers
before retiring old metadata/query modules.

Use Alembic metadata comparison/`command.check` for its actual schema scope. CHECK comparison is
opt-in and name-based; matching names do not prove equal expressions, and function bodies/grants
need their existing explicit native checks. Reconcile actual drift through a forward revision.
The old difference count was not rerun. History inspection confirms `01da23a` expanded the
reference split CHECK under its existing name and `51bba6c` changed committed 0027 SQL. That
establishes possible same-head deployment divergence, not the state of any particular database.
The forward repair must cover both the earlier two-member CHECK and fresh current bootstrap;
renaming a CHECK is insufficient. Do not normalize old deployed files in place.

**Preserve/challenge:** changes to one allowed edge, a CHECK expression, a privilege, a disposal
rule and a function body must be detected at their respective boundaries; deliberate invalid
transitions must still fail. A generated implementation and its generated expected output alone
cannot establish that the modeled behavior is correct. This strengthens FP-04/06 and DP-06 while
removing manual repeated authoring without introducing another migration system.

<a id="I03"></a>
## I03 — Enforce immutable meaning before removing repeated validation

**Recommend prerequisite; optimize conditionally.** CBO-019/020; CA-01/06. Owners: SP-03/SP-C03/SP-07.

The leverage review identifies mutable `sem`/admitted-content rows behind declarations of
immutability. Current source-frame guards provide a local precedent. Derive the immutable table
set from physical/lifecycle contracts, deploy UPDATE/DELETE/TRUNCATE refusal and least grants,
and include guards in native admission. Project/realization/selection lifecycle mutation remains
explicit. Evaluate `eval` tables against their existing append/replay contracts, not a blanket
freeze that breaks legitimate operations. Table-owner/superuser deployment remains a distinct
administrative authority; triggers cannot eliminate it.

Immutability must cover the meaning graph, not only existing rows: preserve the native refusal
of adding value-role children to an admitted parent, and prevent appending applicability/definition
rows to a finalized release. Broader admission grants must not reopen that closure.

Only after enforced immutability and independent posture checks should meaning-only
recomputation be removed. Retain cumulative applicability/cardinality/identity/reference checks
whose truth can change when a batch adds facts or membership. Prefer affected-subject/context
scoping only after its required closure is demonstrated. Avoid one global validation pass per
item or an unconditional deletion of all old validators.

Narrow known-input materialization to the actual resolution/display universe. Preserve label/key
anchors while resolving identities; after resolution, carry only used memberships/supports and
retained exclusion evidence. `domain_operations.py` currently loads broad input evidence and can
carry evidence of discarded entities/exclusions even after membership filtering. Validate that
unrelated input entities cannot contaminate the output evidence closure. Core subqueries/EXISTS
and batched closure reads can keep this work database-visible.

**Benefit/burden:** establishes the integrity basis for I04 and removes unnecessary whole-input
work; adds forward trigger/grant migration and careful cumulative-scope validation. Challenge
multi-batch newly established membership, cross-input exclusions and replay. No speed claim is
made; DP-01/03/10 and FP-07 require preserving cumulative semantics.

<a id="I04"></a>
## I04 — Separate acquisition, composition, opening and verification

**Recommend as one deliberate compatibility change, conditional on I01/I03.**
CBO-002/003/009/013/021; CA-06/08. Owners: SP-01/SP-C02/SP-08/SP-09.

`semantic/regeneration.py:36–49` fully prepares component packs before composing them;
`semantic/releases.py:391–470` recompiles and compares all products for each load. The same
runtime consumers need immutable lookups/adapters, not repeated OWL/SHACL generation.

Separate explicit `PackInputs` acquisition from pure single-root composition. Acquire named
bytes/origins, refuse collisions/reserved names and compile once. Keep minimal compiler fixtures
independent rather than forcing all compiler tests through a full pack. SchemaView is a
preparation-time mutable tool: finish induction before sharing products and isolate generators
that mutate inputs. Do not replace explicit resolution with ambient import fallback.

Factor one boundary builder used by preparation and product opening. Archive every required
primitive, alias, constraint scope, role and policy descriptor; make a non-identity immutable
ReleaseIndex for handles/adapters/reference positions. Memoize by database identity, release,
content digest observed in the current snapshot and supported compiler/boundary ABI. Cache pure
products, not live grants, mutable pointers or authorization.

Full verify remains at publication/activation/run-start and explicit verification. Cheap open
must check exact archive identity and its supported runtime contract. Until I03 supplies enforced
immutable products, retain snapshot projection comparison. JSON Schema equality alone cannot
prove unchanged runtime Pydantic validation; keep validation-affecting ABI/dependency compatibility
separate from byte identity. Consolidate dependency determinants by actual effect, retain exact
manifest provenance and include SymPy in mathematical operation dependencies.

**Transition refinement:** the old proposal said “before regeneration,” but runs 1/2 now exist.
Choose a supported old-product reader or a preserved execution environment for required old
answers before selecting newly regenerated outputs; otherwise keep full old loading until that
route exists. Do not strand selected results through an automatic compiler-number bump, silently
reinterpret archives, or add universal historical upcasters. Compiler/profile and rule-view changes
should share one planned regeneration boundary, rather than serially invalidate the same work.

**Preserve/challenge:** warm/cold reads, same ID from deterministic composition, generator input
mutation, alias/nested-type reconstruction, corrupt archive/products, changed validator behavior
with identical JSON Schema, old selected answer and new activation. Benefit is less repeated
preparation/toolchain coupling; current timing remains prior scoped evidence, not a new benchmark.
FP-01/04/07 and DP-04/09/10 apply.

<a id="I05"></a>
## I05 — Give reads one public interpretation and required-universe contract

**Recommend.** CBO-001/012/025; CA-03/04. Owners: SP-04/SP-C02/SP-C05/SP-08.

Promote reusable scoped selection, value/entity/context loading and strict hydration from the
semantic kernel. Serving retains named-query parameters, labels/modality, response limits and
continuation policy. `serve/read.py:191–258` and `semantic/query.py:1051–1094` currently repeat
adapter/hydration decisions. Use the release index from I04 for one cache/position vocabulary;
avoid expanding the public interface into a second query language.

One snapshot opener should use SQLAlchemy's REPEATABLE READ plus `postgresql_readonly=True`,
with separate binders for a realization and completed result. Keep ADBC's imported snapshot and
reader lifetime explicit. Consolidate continuation handling deliberately, preserving wrong-release,
changed-data-revision and query-version distinctions rather than rewriting the whole kernel as
serving policy. Restrict use of public primitives; do not retain plugins importing private names.

Coverage must prove the modeled required universe: a compatible global witness or every required
member, not `all` of the records that happen to exist. Missing B after complete A remains unknown.
Couple required scope/family to the prepared query contract and keep page completion distinct.
For object predicates, use exact typed comparison or an explicitly exact residual; refuse
unsupported interpretation. `serve/queries.py:88` still accesses nonexistent `typed_value.lexical`.
Substituting one text column would neither fix numeric meaning nor provide exact range ordering.

Make CLI/MCP refusal adapters consume actual typed domain errors and the existing DBAPI classifier.
Do not translate transient database failures, programming defects or cancellation into ordinary
user refusal. Preserve proposal-specific held/correction accounting. FastMCP middleware cannot
replace that owned semantic classification. Keep current main-thread grammar deadline behavior;
there is no accepted concurrent MCP grammar consumer requiring a new process layer.

**Closure:** actual CLI/MCP supported routes, wrong scope, incomplete universe, decimal lexical
variants, exact unsupported predicate refusal, stale tokens and bounded explanation evidence.
Retain independent SP-04 primitive expectations while migrating named readers. FP-01/04/06,
DP-10 and CI-04/05/08 apply. No future MCP query/golden capability is silently added.

<a id="I06"></a>
## I06 — Share scientific evidence, keep consumer policy explicit

**Recommend; correctness priority before retirement.** CBO-005/006; CA-04/07.
Owners: SP-C04/SP-07/SP-08 and D7/domain scientific policy.

`domain_operations.py:2820–2842` merges equivalence components using the old comparator, including
numeric agreement. `evaluate/semantic_alignment.py:291–334` treats numeric agreement as undecided
and only counterexamples as disproof. Copying one implementation everywhere would silently
change selection or grading policy.

Extract one semantic-operand evidence kernel: canonical result, symbolic evidence, numerical
counterexample/agreement, grammar/timeout status and exact assumptions/macros/units/context.
Each consumer applies an explicit versioned policy and records the evidence tier in assessments.
Preserve existing policy behavior during extraction until its owner selects any change. SymPy
`simplify`/expression operations and `evalf(subs=...)` are mechanisms, not an authority to decide
what constitutes proof. Do not label `equals` as a symbolic-proof tier: SymPy 1.14.0 itself can
use numerical evaluation. No regrade or accuracy threshold follows.

Move the authored semantic rule view/accessors to their proper owner before retiring the legacy
value/condition environment. Retain rule-engine's typed `OBJECT`/attributes/accessor, `NULLABLE`,
`ARRAY`/`MAPPING` machinery and shared nondeterminism restrictions. A copied type map or automatic
Pydantic-type conversion cannot validate arbitrary unions, keyed semantic values or actual
accessor fidelity. Correcting `map[Value]` is a rule-view semantic/version change; schedule it
with the deliberate I04 transition, not as invisible cleanup.

**Closure:** symbolic success, numeric counterexample, agreement without proof, no valid sample,
unsupported restrictions, macro/context change, argument reversal and timeout; independently
assert both consumer policies. Benefits are less interpretive drift and a removable retirement
dependency, not measured model quality. FP-04, DP-02/05/08 and explicit uncertainty apply.

<a id="I07"></a>
## I07 — Consolidate value/reference lowering around explicit contracts

**Recommend.** CBO-013/015/016; CA-01/02/04. Owners: SP-C02/SP-C04/SP-08.

Use a release-derived reference-position classifier and collect/rewrite visitor over validated
models. Evaluation's raw-key subtype guess and Entity-only classification differ from the domain
walk; multivalued fact refs and known-input key-name heuristics remain seams. Explicitly preserve
consumer collision/collection policy: equal versus distinct keyed collisions, repeated sequences,
non-inlined class references and text resembling an identifier are not interchangeable. Protected
reference payloads must use their own admitted release rather than current active meaning.

Build field/item adapters once using public model-field annotations, preserving metadata and
strict finite numeric policy. Pydantic strictness alone does not reject NaN/inf; use field-level
finite-float constraints and independent boundary tests. Do not inspect `TypeAdapter._type` or
put caches into identity-bearing serialized dataclasses. This improves completed reader paths
as well as the remaining migration.

Keep one written qualified-meaning/value-codec specification with typed Python and native
implementations where both are needed. Hypothesis differential parity and independent pinned
vectors challenge rounding/carry/exponents/signed zero/null/Unicode/recursive roles; agreement
between two mirrors alone cannot prove the specification. Preserve original lexical scalar
fallback and ADBC opaque type metadata. Do not replace exact arithmetic with a vectorized fast
path merely because a library exposes one, or normalize authored lexicals without a declared
semantic-identity transition.

**Closure:** non-Entity class references, inlined subtypes, keyed collisions, multivalued fact
roles, wrong archived release, nonfinite floats, large exact decimals and independent native
meaning keys. FP-04/05, DP-04/06/07 and the test-assessment companion apply.

<a id="I08"></a>
## I08 — Improve completed analytical operations through native relation binding

**Recommend bounded ownership/binding change; defer optional streaming.** CBO-007/018/020/022.
Owners: SP-05/SP-C05/SP-07/SP-08.

Retain captured versus candidate provenance, imported PostgreSQL snapshots, selected exact
arithmetic, protected pgpq publication and borrowed/detached lifetime behavior. Move surviving
set kernels out of retiring pool modules and replace identifier regex rewriting in
`analytics.py:697–717` with DuckDB relation binding (`relation.query`) or TEMP table macros and
`query_table` for multiple named inputs. Explicit authored placeholders are a smaller acceptable
alternative. Do not build another SQL parser; preserve independent expected rows before deleting
old differential scaffolding.

Semi-naive delta rounds over the existing work table can remove repeated inference joins once
correctness is settled. Preserve total/delta handling for nonlinear rules, semantic-key termination
and final direct-proof enumeration. This is optional lower priority, not a reason to replace the
engine or adopt a general Datalog service. Keep optimizer-visible Core subqueries and batched
known-input sets rather than constructing large Python identifier lists unnecessarily.

Physical exports remain PyArrow to preserve schema metadata. `ParquetWriter.write_batch` with
schema retention and ADBC `fetch_record_batch` are useful future mechanisms, but changing only
the writer does not bound memory while capture still materializes the full spine. A genuine
streamed route needs same-snapshot batch normalization, closure, manifest/hash accounting and
cancellation ownership. Adopt it only for an accepted workload, with no extra DuckDB export hop.
DataFusion, lakehouse/storage services and semantic-subset export remain separate opportunities
until a concrete consumer justifies their additional contracts.

**Closure:** multiple input bindings, qualified repeated rows, metadata stripping, cancellation,
empty relation, exact numeric boundaries, delta closure/cycles and multiple proofs. Current
columnar mechanisms retain their scoped credit; no throughput/memory benefit is newly measured.
FP-03/07, DP-10 and explicit projection/lifetime semantics apply.

<a id="I09"></a>
## I09 — Make credential purpose and actual principal explicit

**Recommend hardening while retaining sequential per-purpose pools.** CBO-004/012; CA-08.
Owners: SP-03/SP-08/SP-09 and D3/D9.

`semantic/runtime.py:36–37` derives a reader only when the source username is the writer;
otherwise a read can retain an owner login. `core/db/store.py:92–98` checks extensions but not
the effective principal. Require purpose at owned entry points, derive reader credentials
explicitly, and assert role capability/non-owner posture on the actual connection. Use one
principal owner and shared connection information for psycopg/SQLAlchemy/ADBC. Preserve alternate
login names carrying the required restricted role rather than enforcing string equality.

Keep one psycopg pool per authenticated login phase, lent through SQLAlchemy NullPool; no current
consumer justifies concurrent pools or a second plain-creator route. Keep one storage endpoint.
Clarify whether purpose URLs are credentials-only or validated endpoint declarations, rejecting
contradictory configuration instead of silently granting owner reads. That is an explicit
configuration-contract change, not an incidental URL rewrite.

**Stale premise withdrawn:** current `cli/regenerate.py:79–82` persists as maintenance without
SET ROLE; SET ROLE occurs only during final result selection. The prior uncommitted first-persist
permission hazard is not a current defect. The separate need to reconcile automated release
admission's maintenance authority with “restricted runtime credentials” remains. Compare a
restricted admission principal/protected publication boundary with a clearly separate trusted
operator command; settle it through ADR-0025/0030/B3 owners, not a hidden owner fallback.

**Closure:** owner URL read refusal, alternate restricted login, no evaluator access from extraction,
credential endpoint mismatch, pool return/reset, actual release admission and source/result phases.
Existing Settings precedence and secret masking remain; no new secret service is required.
FP-01/05/06 and native authority apply.

<a id="I10"></a>
## I10 — Reuse native fixture preparation without weakening isolation

**Recommend session-local template with explicit posture preservation.** CBO-010; CA-09/10.
Owners: SP-10 and shared native test support.

Current `tests/semantic/conftest.py` creates an extension-only database and runs the migration
chain for each consumer test. Prefer one session head template and a fresh clone per test,
replaying database-level ACLs/settings and asserting equivalence. PostgreSQL template cloning
preserves objects but not database GRANTs or ALTER DATABASE SET settings; object-level identity
alone is insufficient. Retain cold bare bootstrap, revision-pair and `ci db init` controls.

Use one existing lifecycle/residue owner and actual restricted writer/reader/evaluator connections.
Close owned pools before bounded normal-exit drop retries; do not widen terminate privileges or
substitute outer-transaction rollback for actual commits/races. A persistent cross-session template
would need a broader environment/role-OID/migration key; defer that complexity until useful.

Add independent principal/TEMP posture expectations, including the writer TEMP inconsistency
between ADR prose and inference deployment. Interpret “fresh frozen deployment” explicitly through
the owning decision route before adopting clone equivalence. pytest-postgresql's convenience
alone does not replace ACL replay, ownership and cleanup requirements.

**Challenge:** missing evaluator role, altered ACL/defaults, leaked authenticated backend, cancellation
and migration-from-prior-revision. Schema/model validity and native isolation are the acceptance
purpose; test setup savings are qualitative until measured. FP-06/07 and test-assessment apply.

<a id="I11"></a>
## I11 — Preserve qualification outcomes through interruption

**Recommend streamed native test reports and explicit required-scope classification.**
CBO-011; CA-09/10. Owners: SP-10 and existing test command support.

Use pytest-reportlog's flushed report stream and pytest 9.2's built-in
`faulthandler_timeout`/`faulthandler_exit_on_timeout`, preserving collection, setup/call/teardown
and session completion. Installed `_pytest/faulthandler.py:83–100` uses the watchdog route;
`methods/math/grammar.py:405–412` cancels SIGALRM timers, so a signal-based pytest-timeout is not
a trustworthy replacement here. Choose a generous hang bound as execution policy, not a latency
claim. Preserve worker/node/phase identity rather than infer execution from collection order.

**Refine the prior proposal:** keep raw skip reasons and distinguish intentionally inapplicable
cases from missing required prerequisites. Every skipped required obligation stays open, never
passes; not every pytest skip should automatically become a provider block. Missing final-session
records mean incomplete qualification. Preserve completed outcomes, classify collected but unrun
work as not_run, and retain the interrupted/hung case's evidence without manufacturing an
assertion failure. Report process-level failure when the harness cannot identify a node.

Use a small stdlib classifier over existing artifacts, not a new evidence service. Retain
Hypothesis profiles/blobs and durable independent `@example` vectors; pin the added reporting
plugin deliberately. Explain that nextest's zero-test result supplies no Rust functional evidence.
Add meaningful mid-run settings/bound-operation evidence and settle actual cross-field applicability;
do not invent a constraint just to fill CA-09. No test/type repetition follows lint-only changes.

**Challenge:** collection error, call failure, teardown hang, killed session, required provider
skip, optional deselection and multiprocessing worker loss. This makes the existing incomplete
campaign actionable without rerunning it merely to recover a failure name. FP-05/06 and honest
qualification boundaries apply.

## Crosswalk: prior proposals and audited obligations

Every prior CBO is considered below. “Recommend” is a review proposal, not adoption or closure;
retain/conditional judgments include their meaningful limits.

| Source item | Refreshed judgment / destination |
|---|---|
| CBO-001 | Recommend shared public read/hydration/coverage and exact predicates (I05); object-filter defect survives. |
| CBO-002 | Recommend acquisition/pure composer (I04); caller pack order is already normalized, so do not repeat that older premise. |
| CBO-003 | Recommend staged open/verify only with complete boundary recipe, immutable basis and runtime compatibility (I04). JSON Schema equality alone is insufficient. |
| CBO-004 | Retain sequential pools; harden actual purposes/principals (I09). First-persist SET ROLE hazard withdrawn. |
| CBO-005 | Recommend semantic rule view/accessor migration and explicit version transition (I06). |
| CBO-006 | Recommend shared evidence kernel plus explicit consumer policies (I06); numeric agreement policy remains an owner decision. |
| CBO-007 | Retain physical PyArrow export; shared snapshot owner (I05/I08). Streaming/semantic exports remain demand-led. |
| CBO-008 | Recommend generated forward reconciliation and correctly scoped metadata/native comparison (I02); move lowering with real retirement dependencies, not a cosmetic second rewrite. |
| CBO-009 | Recommend one effect-based identity/acceptance/runtime determinant model with SymPy dependencies (I04); preserve runtime validation compatibility. Dependency removals/additions require actual use and narrow lock review. |
| CBO-010 | Recommend session head template plus ACL/settings replay, cold migration controls and one cleanup owner (I10); settle deployment-equivalence wording. |
| CBO-011 | Recommend streamed qualification outcomes/watchdog (I11); refine all-skips=blocked and collection-order inference. |
| CBO-012 | Recommend typed domain/refusal mapping with DBAPI outcome distinctions (I05/I09); preserve proposal correction accounting. |
| CBO-013 | Recommend finite-float boundary repair and derived release index (I04/I07); no eager unused adapter universe. |
| CBO-014 | Recommend existing emitter plus Core DDL/descriptor derivation, delete obsolete deploy route (I02). |
| CBO-015 | Recommend explicit codec specification, Hypothesis/native parity and independent vectors (I07); lexical normalization choice is not silent cleanup. |
| CBO-016 | Recommend classifier and validated visitor, with explicit collision/sequence policy and correct archived reference release (I07). |
| CBO-017 | Retain cattrs/frozen products, allow tuple-default simplification; strengthen actual result/enforcement consumption (I01). Shape registration is insufficient. |
| CBO-018 | Recommend semantic kernel ownership/native relation binding before retirement (I08); keep independent expected semantic rows. |
| CBO-019 | Recommend closure-level immutability first, then remove only discharged meaning checks; cumulative validators remain (I03). |
| CBO-020 | Recommend database-shaped used sets and post-resolution evidence closure (I03/I08); retained/excluded evidence must not copy unrelated inputs. |
| CBO-021 | Retain seeded offline SchemaView, effective-slot induction and generator isolation (I01/I04). Materialized derived schema does not preserve all admitted constraint semantics. |
| CBO-022 | Optional semi-naive rounds after semantic repair (I08); no new inference service. |
| CBO-023 | Retain main-thread grammar deadline; no current concurrent MCP grammar consumer (I05). |
| CBO-024 | Retain pinned local ontology workaround (I01); no new currency/latest-version claim or automatic backend adoption. |
| CBO-025 | Recommend one read-only snapshot opener and explicit binders (I05/I09), preserving ADBC snapshot ownership. |

| Audit obligation | Improvement route; existing disposition remains coordinator §13 |
|---|---|
| CA-01 | I01 resolved effective statement binding + I02 generated native consumption; no literal subtype escape. |
| CA-02 | I01 one scoped constraint product and explicit validation purpose. |
| CA-03 | I05 required-universe coverage, not complete existing-row aggregation. |
| CA-04 | I01 real phase/result/enforcer composition; I05/I06/I07 actual consumer adoption. |
| CA-05 | I01 bound graph contract resolution and attributable structured validation. |
| CA-06 | I01/I02 maintained model derivation/correspondence and actionable owner diagnostics. |
| CA-07 | I02/I06/I08 preservation-first retirement; library/source presence alone is not a live bypass. |
| CA-08 | I04/I09 explicit transition, principal and B3/ADR authority decisions. |
| CA-09 | I10/I11 meaningful settings evidence/applicability, no invented cross-field constraint. |
| CA-10 | I02/I10/I11 efficient discriminating final qualification after functional changes. |
| CA-11 | I01 explicit admitted construct/workflow decision; faithful alternative where required, safe refusal not counted as delivery. |

## Priority, dependencies and decisions for plan revision

Correctness consequences put I01, I05's absence/object predicates and I06's divergent scientific
evidence/policy interpretation first. Finite-float/reference codec issues in I07 deserve the
same early attention. This does not prescribe a serial whole-package execution barrier.

1. Resolve real model/result/constraint/projection contracts and policy choices; implement their
   current callers and independent examples together (I01/I05/I06/I07).
2. Establish the retained native authoring/derivation and closure-level immutability basis
   (I02/I03); preserve all cumulative guards. Principal hardening (I09) can proceed independently
   where its authority/configuration decisions are settled.
3. Bundle composition, boundary recipe, identity/runtime compatibility and rule-view versions
   into one deliberate transition (I04/I06). Preserve required old reads before selecting new
   outputs, then perform the remaining fresh regeneration and named retirement work.
4. Improve fixture preparation/reporting (I10/I11) before expanded native parity and final
   qualification, retaining actual bootstrap/revision tests. This supplies faster, more useful
   feedback without changing required native/provider obligations.
5. Adopt native set binding (I08) alongside relevant consumer/retirement changes; delta inference
   and true streaming remain optional until their concrete consumer/workload justifies them.

Decision impacts belong to existing owners: runtime-open versus exact-recompile policy, byte versus
runtime determinants, scientific numeric policy per consumer, writer TEMP and admission credentials,
clone equivalence, lexical normalization and B3's automated extractor. Do not edit accepted ADRs;
use their successor route where rules change. Future MCP inspection tools, generalized upcasters,
new graph/analytical authorities, a universal workflow/rule compiler and benchmark infrastructure
are separate undertakings, not covert prerequisites for these amendments.

## Sources, evidence strength and limits

The topic-level [library investigations](../library_leverage/libraries/README.md) retain prior
installed-source probes and capability limits; their evidence dates/baselines are not relabeled.
The following primary sources informed fresh capability checks and recommendations:

- [LinkML SchemaView](https://linkml.io/linkml/developers/schemaview.html): contextual induced slots,
  hierarchy and import handling; installed 1.12.1 semantics remain the implementation reference.
- [Pydantic 2.14.1 validators](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/validators.md),
  [adapter reuse](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/performance.md)
  and [strictness](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/strict_mode.md).
- [jsonschema error structure](https://python-jsonschema.readthedocs.io/en/stable/errors/): preserve
  located validation diagnostics; existing emitted fragment dialect remains explicit.
- [SQLAlchemy read-only transactions](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html#setting-read-only-deferrable)
  and [Alembic comparison limits](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).
  Installed SQLAlchemy 2.1.5/Alembic 1.20.0 control exact feasibility; current online docs can differ.
- [PostgreSQL template semantics](https://www.postgresql.org/docs/18/sql-createdatabase.html)
  and [pytest watchdog configuration](https://docs.pytest.org/en/stable/reference/reference.html#confval-faulthandler_exit_on_timeout);
  installed pytest 9.2 confirms the exit flag despite older Context7 version listings.
- [SymPy 1.14 expression equality source](https://github.com/sympy/sympy/blob/sympy-1.14.0/sympy/core/expr.py),
  [rule-engine type source](https://github.com/zerosteiner/rule-engine/blob/v5.1.0/lib/rule_engine/types/datatype.py)
  and [cattrs customization](https://catt.rs/en/stable/customizing.html).
- [DuckDB 2.0 native query-table binding](https://duckdb.org/docs/2.0/guides/sql_features/query_and_query_table_functions),
  [Arrow ParquetWriter](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetWriter.html)
  and [ADBC PostgreSQL](https://arrow.apache.org/adbc/current/driver/postgresql.html).
- [PySHACL 0.40.1 entrypoint](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/entrypoints.py)
  and [RDFLib graph semantics](https://rdflib.readthedocs.io/en/stable/intro_to_graphs/).

**Source-inspected:** current implementations/callers, CBO premises, admitted model products,
selected package/decision obligations and actual test-support composition. **Proposed:** all
amendments, dependency/authority changes and benefits. **not_run:** new probes, product/native/
provider tests, migrations, regrading, broad lint/types and performance measurements. Existing
scoped passes, failed/interrupted qualification and older measurements remain exactly bounded.
Documentation maintenance/publication is reported in STATUS, not as product qualification.

This review gives a coherent candidate amendment set and closure cases. It does not complete
CA obligations, change scheduled scope/progress or adopt earlier library recommendations. Plan
revision is separately instructed; current finding disposition remains with the coordinator.

## Planning consumer

The operator selected the recommendations for integration through
[coordinator §14](../plans/semantic-model-pivot_2026-10-29.md#14-improvement-integration-2026-10-29)
on 2026-10-29. That plan owns current scheduling/disposition, including conditional and retained
choices. This review remains source evidence and does not claim implementation or qualification.

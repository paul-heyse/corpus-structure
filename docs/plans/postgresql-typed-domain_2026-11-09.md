# PostgreSQL typed-domain implementation series

**Status: PTD-00–09 complete with scoped verification; PTD-I01–06 decision-complete; two PTD-10 slices and PTD-11 remain planned · 2026-11-09.** Target design is Proposed. This coordinator
owns PTD-00–11, PTD-I01–06, selected branch delivery, review O01–O13 disposition and combined
qualification. It does not supersede any existing plan. Production milestone two remains separate.

## Basis and operator decisions

Consume the [functional review](../functional_reviews/postgresql-typed-domain_2026-11-09.md) and
six companions at `10e84f34862cc3a6be0becc4c5263a0a7eed53c2`. Its input discovery at `d18183a22`
and earlier receipts retain original dates and scopes. Source-inspected authoring baseline is
`10e84f348`, 2026-11-09. Current product/manifests/lock/owners are unchanged from that review;
concurrent PM2 STATUS, plans and evidence are excluded and preserved. Execution must reconcile
against the eventual PM2 handoff revision, not assume this source/native revision remains current.

Operator directions, 2026-11-09: author a new series, leave existing implementation plans unchanged,
execute after the other session finishes its current PM2 tranche, finish this series before returning
to PM2. All conditional areas receive bounded decisions; implement justified selected branches and
close others with reasons/triggers. Author chooses useful consumers from grounded model/corpus/
workflow evidence; material rule/product changes still require concrete decisions. Writing this
series authorizes no current product edits, database effects or change to run487's executing checkout.

Use [D1](../design/D1-knowledge-representation.md), [D2](../design/D2-schema-and-guidelines.md),
[D3](../design/D3-database.md), [D8](../design/D8-agent-and-query-interfaces.md) and their governing
ADRs for semantics. Core3.3, heuristics1.0, code-intelligence1.4 and test-assessment selected by
[standard.toml](../design_review/design_principles/standard.toml) guide the focused foundation
assessment. No new diagnostic audit or formal conformance claim accompanies authoring.

## Combined target and foundation assessment

The operator/developer gains useful released distinctions in generated call/read contracts,
attributed SQL impact and source diagnostics, a bound cross-run coverage report, exact composed
retrieval, faithful independent companion exchange and honest database metadata. A small shared
ADBC owner removes inconsistent driver/resolver/cleanup handling. Native evolution remains frozen,
independently observed and transaction-owned. Conditional capabilities are finite decision work,
not an unlimited roadmap or a requirement to adopt every library feature.

| Foundation observed | Selected consequence and rationale |
| --- | --- |
| Operation-call generation already derives semantic IDs and closed types; Core renderer uses primitives | Reuse the same binding facts for selected columns/results instead of a second type generator; static views are not runtime enforcement |
| PreparedSQL and archived qualified projection analysis already feed semantic impact | Extend those products/report consumers with occurrence-aware detail and original diagnostics, not another analyzer/provenance store |
| Four exact retrieval statements repeat a statement-local eligible CTE | One shared eligible operation with membership/channel variants; retain Python fusion and exact policy |
| Existing companion export has authenticated six-part pins, directional schemas, atomic files and DuckDB comparison | Select independent offline Arrow/Parquet consumption as the first exchange/research consumer; do not invent an importer to demonstrate a type |
| Analytics acquisition fixes builtin while description bypasses configured-driver acquisition | One explicit core/db factory and existing owned cleanup, with operation-specific resolver policy |
| Frozen native transitions/Alembic/catalog admission and role fences already exist | Preserve independent actual-state checks and global dependency ordering; use public rewrite/reflection APIs only for complete remaining gaps |

Workload is the authenticated current scientific corpus, its retained source views, bounded published
family exports and selected run comparisons. Scope/identity, native coverage and exact effects govern
narrowing. Prefer set composition, valid-lifetime preparation and shared owned facts over repeated
hydration. Copies, archive versions and transaction scopes serve actual custody/consumer needs.
Expected benefits are qualitative; no latency/memory/quality percentage or measurement obligation
is created. Exact correctness/fidelity obligations remain independent of expected efficiency.

## Supporting design owners

| Document | Contracts/packages owned |
| --- | --- |
| [Released types/exchange](postgresql-typed-domain/released-types-and-exchange.md) | PTD-01/08, I01 and I05 input/value slice; shared generated facts, directional fidelity |
| [SQL explanation/authoring](postgresql-typed-domain/sql-explanation-and-authoring.md) | PTD-04/05, I02; archived detail, impact and candidate reports |
| [Operations/retrieval](postgresql-typed-domain/relational-operations-and-retrieval.md) | PTD-06/07, I03/04; coverage comparisons, exact composition and richer-policy choices |
| [Inspection/research](postgresql-typed-domain/inspection-and-research-access.md) | PTD-02/03, I05; acquisition, attributed metadata and research routes |
| [Native/operations](postgresql-typed-domain/native-evolution-and-operations.md) | PTD-09/10, I06; frozen transitions and selected operational branches |

Design ownership does not duplicate coordinator state. A package is not automatically an agent
assignment; coordinate shared generators, model products and native forward revisions through one
writer/integrator. Independent logical work can still share files. Never require a whole companion
to finish when one implemented prerequisite slice suffices.

## Execution queue

PTD-00–09 are **complete at their scoped boundaries** (receipts below); PTD-I01–06 are **decision-complete** at the bounded inquiry described below. Two selected PTD-10 slices and PTD-11 remain **planned**. Full-series qualification remains PTD-11.

| ID | Responsible boundary | Required input and delivered capability | Completion evidence |
| --- | --- | --- | --- |
| <a id="PTD-00"></a>PTD-00 | Coordinator | Other session's current-tranche handoff; reconcile actual source, native head, run/cut/defaults and current consumers; establish applicable scope and review points | Recorded acquired baseline and branch/qualification scope, no hidden PM2 completion dependency |
| <a id="PTD-01"></a>PTD-01 | Model/generation + all selected callers | Existing semantic binding facts → one generated typed call/column/companion boundary | Wrong-ID callable refusal, valid/nullable closed cases and deterministic regeneration with consumer migration |
| <a id="PTD-02"></a>PTD-02 | core/db + ADBC consumers | Explicit settings/driver/resolver → shared acquisition + independent owned rollback/close | All capture/export/description callers migrated; native parity and cleanup controls |
| <a id="PTD-03"></a>PTD-03 | Database description/CLI | Working PTD-02 → attributed native/Arrow observations with unknown constraints preserved | Numeric/expression/opaque/inaccessible/bounded cases through actual JSON/CLI consumer |
| <a id="PTD-04"></a>PTD-04 | Projection preparation/archive/report owners | Checked model/source → occurrence-aware explanation product and consumers | Independent origin/influence/unknown/copy/reader-version cases; archived/runtime determinants preserved |
| <a id="PTD-05"></a>PTD-05 | Candidate/model report owners | PTD-04 detail + existing PreparedSQL/native candidate → located structural/impact report | Unicode/predicate/unknown-helper report on managed candidate, no data-query execution |
| <a id="PTD-06"></a>PTD-06 | Coverage/report owners | Current per-run custody → bounded compatible two-run coverage operation | Independent settlement/matching/incomparable cases and ordinary machine/human read |
| <a id="PTD-07"></a>PTD-07 | Contextual retrieval/storage | Current profile/inventory contracts → typed binds and one exact membership/channel operation | Independent channel/rank/inventory/witness controls on resident and transient routes |
| <a id="PTD-08"></a>PTD-08 | Companion projections/export/independent consumer | PTD-01 where types change, PTD-02 acquisition → faithful four-family detached exchange | Independent Arrow consumer after disconnect; null/precision/provenance/comparison cases |
| <a id="PTD-09"></a>PTD-09 | Native candidate/Alembic/catalog owners | Actual operation tree and selected public API → coherent reviewed authoring/retirement | Overloaded function/dependent trigger/stale-state/ACL/restricted-role native cases |
| <a id="PTD-10"></a>PTD-10 | Owning selected branch | Completed I decision + any concrete rule decision → bounded implemented branch and all consumers | Slice-specific independent delivery cases, migration/activation/retirement and required evidence |
| <a id="PTD-11"></a>PTD-11 | Coordinator/integrator | All selected behavior complete and I decisions settled → adopted current system and PM2 return handoff | Final-source applicable test union, repository checks, native delivery and unresolved-obligation reconciliation |

PTD-00 precedes effects. PTD-02 precedes 03 and affected exchange/research consumers; 04 precedes 05.
01 need not wait for native types or ORM. 06/07 can proceed on their existing input contracts.
08 shares bindings with01 and acquisition with02, not all native/operational work. 09 supplies only
native slices actually selected. I decisions run early where their result changes a contract and
otherwise alongside ready packages; PTD-10 slices follow individual decisions, not one global barrier.

## Source disposition and decision obligations

This is the single scheduled disposition owner. Source IDs remain functional opportunities, not
renamed diagnostic findings. Each source branch is open until its implementation/evidence or
reasoned selection/retain/reject/defer outcome is recorded here. A deferred outcome must name a
specific unmet premise and revisit condition; unperformed investigation cannot be called closure.

| Review item | Component and current disposition | Package/decision route | Closure obligation |
| --- | --- | --- | --- |
| [O01](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O01) | Closed · selected generated boundary | PTD-01 | Closed at selected boundary · 181 affected tests passed; constraints and determinants preserved |
| [O02](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O02) | Decided · retain explicit value codecs, native invariants and private operations | I01 | Decision-complete; native/ORM expansion has concrete value/workflow triggers in the released-types companion |
| [O03](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O03) | Closed · attributed explanations implemented | PTD-04 | Current impact/report/archive consumers use supported detail; unknowns remain explicit |
| [O04](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O04) | Decided · diagnostics delivered; retain finite language and current research routes | PTD-05, I02 | PTD-05 delivered; I02 branches decided separately in SQL companion; no additional language slice selected |
| [O05](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O05) | Open delivery · coverage complete; two resident/preparation improvements selected | PTD-06, I03 →10 | Deliver PTD-10/inference-delta and PTD-10/contextual-preparation; other I03 mechanisms decided |
| [O06](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O06) | Closed · exact composition and typed binding implemented | PTD-07 | Full membership/channel correctness preserved across migrated consumers |
| [O07](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O07) | Decided · retain exact baseline; richer representations/policies deferred individually | I04 | Concrete terminology, token/visual, scale, aggregate or fixed-list premises retained in operations/retrieval companion; no quality claim |
| [O08](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O08) | Decided · faithful output delivered; current input/value routes retained | PTD-08, I01/I05 | I01/I05 input/nested/spatial/Rust branches decided; no alternate publication path selected |
| [O09](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O09) | Decided · retain detached capture and current owned analytical readers | I05, PTD-08 | Capsule, bound, replay, ingestion, federation and laboratory branches separately decided with triggers |
| [O10](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O10) | Decided · observed metadata delivered; parameter-free authored profile retained | PTD-03, I05 | I05 parameter/description branch resolved without changing D8; future admission proposal requires a real consumer |
| [O11](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O11) | Decided · frozen atomic native workflow retained | PTD-09, I06 | PTD-09 delivered; native deployment variants decided separately; no fence, offline or plugin rule change selected |
| [O12](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O12) | Closed · shared explicit acquisition | PTD-02 | All current ADBC callers migrated; no second pool/settings authority |
| [O13](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O13) | Decided · retain current operational lifetimes; conditional variants have specific triggers | I06 | Preview/session/pool/read/wakeup/diagnostic/remote/async/distributed branches separately decided; no additional operational delivery selected |

### Bounded investigation contracts

| ID | Question and sufficient decision evidence | Dependent work |
| --- | --- | --- |
| <a id="PTD-I01"></a>PTD-I01 | Which existing repeated value conversion/invariant or actual private editing workflow justifies adaptation/native/ORM machinery? Compare whole construction/read/write/evolution route; source can suffice | Only selected PTD-10 value/native/session slices; O01 remains independent |
| <a id="PTD-I02"></a>PTD-I02 | Which finite richer-query/procedural/portability functions improve current report/research consumers? Settle exact scope/unknowns and destination semantics; probe only an uncertain pivotal contract | Selected language/profile/product extensions |
| <a id="PTD-I03"></a>PTD-I03 | Is a current resident transformation/preparation path missing a simpler composed mechanism? Inspect actual native/Core use before selecting a write/cache/batch replacement | Selected transformation or preparation slices |
| <a id="PTD-I04"></a>PTD-I04 | Which sparse/multivector/approximate/reranking policy has a useful named source/model/question? Compare exact baseline, define independent quality expectations before any evaluation | Only selected retrieval policy/index/profile slices |
| <a id="PTD-I05"></a>PTD-I05 | Which capsule, parameter, offline, input, federation or laboratory consumer adds value beyond faithful detached companion capture? Declare transaction/source/schema authority and rule impacts | PTD-10 research/input/profile slices |
| <a id="PTD-I06"></a>PTD-I06 | Which native lifecycle/preview/session/pool/read/wakeup/diagnostic/deployment/distributed workflow is justified by actual participants, scope and recovery? Compare restart/current atomic route | Only selected native/operational slices |

These are completed decision obligations, not six mandatory experiments. The responsible owner
records considered consumers, decisive source/contract evidence, choice, reasons, trigger if deferred
and required delivered cases if selected. Bound the question before running a probe. A selected
branch is added to its PTD-10 slice here and its owning companion before implementation; its checks
join the required union. Routine details remain implementer judgment within the selected contract.

### Complete source correspondence

The review's [38-row shortlist crosswalk,23-family crosswalk and inline corrections](../functional_reviews/postgresql-typed-domain_2026-11-09.md#complete-discovery-crosswalk)
are the exact consumed source enumeration. Every original row resolves via its O ID into the table
above; multi-opportunity inline rows retain every listed route, not only their first ID. In addition:

- Static with_cols/nominal types do not establish runtime/SQL-operator validation: PTD-01.
- SQLGlot UDF lookup is not automatic annotation/overload binding; current subquery absence is an
  extension boundary, not a bug; fingerprints/diffs are not meaning: PTD-04/05 and I02.
- ADBC metadata interfaces differ; bound results are not COPY, and parameters are currently refused:
  PTD-02/03 and I05. Table unknowns cannot be overwritten by desired/released facts.
- pgpq partial buffers/positional compatibility and SQL/JSON null/precision are residual obligations,
  not duplicated validation: PTD-08/I01/I05.
- Pool async drain exists but null close_returns differs, readiness/status cannot prove commit:
  PTD-02/I06. Native OIDs/resolver generations couple selected value changes to lifecycle.
- Exact retrieval inventories, materialization, RRF/witness/alias policy and original provenance:
  PTD-07/I04. No approximation/default-policy change is preselected.
- Existing typed/native/publication/analytics strengths remain preservation requirements in every
  affected package. Earlier qualification is historical evidence, not fresh closure of this series.

## Rule changes and decisions

No rule change is accepted by this plan. Current parameter-free authored SELECT, exact FP32 eligible
cosine/default ranking, Core-based authority, protected same-session publication and atomic frozen
migration remain selected. Local type/report/composition/acquisition improvements fit those owners.
The review has no numbered RC list; do not fabricate operator acceptance from its recommendations.

If an I decision recommends changing D8 parameter admission, production approximation/witness policy,
general mutable ORM authority, transaction-spanning deployment fence, independent publication or an
explicitly excluded migration plugin, present the actual affected owner/rule, benefit, consequence
and conforming alternative for explicit accept/reject before fixing that dependent target. Record
source O/decision, dated operator outcome and ADR/owner route in this section; apply accepted changes
before consumers depend on them. Rejected changes adapt/close the branch rather than stall unrelated
work. An ADR-worthy ordinary choice is not automatically a new permission request. Nothing here
requires editing or superseding PM2 or another implementation plan.

## PTD-00 execution entry and PTD-11 adoption

Wait for the other session to finish its current actions and hand off source revision/dirty work,
worktree ownership, acquired native/database revision, retained run/cut/source identities, configured
defaults and remaining obligations. Do not wait for complete PM2 qualification/selection and do not
interrupt its active checkout. Reconcile actual source and retained database before effects; preserve
authenticated inputs, frozen migrations/evidence and immutable original identities. Insufficient
derived products can regenerate through the current-only policy; never fabricate new provenance.

Schedule the binding's target review before substantial changed ownership/stage decisions and one
assembled target review at completion, reusing relevant evidence. A formal engagement uses its
applicable refreshed audit; authoring itself does not start that audit. No recurring full gate or
broad review is added after individual slices. Relevant open design questions can be addressed
without restarting settled reviews.

Each package includes its changed consumers, generated/archive/native products and retirement.
When a native/product shape changes, use the existing explicit candidate/frozen forward path,
independent admission and purpose-role verification. Deploy only to the acquired dedicated development
target at its handed-off revision. Record transitions and effect settlement; release/runtime pins
must match the consuming operation. Separate source custody from incompatible derived products.

PTD-11 requires all I branches resolved, all selected PTD-10 slices delivered, current consumers
migrated and obsolete paths/configuration removed. Exercise actual combined journeys: regenerate
bindings/analysis → inspect candidate/impact → current native admission/read; compare exact run
coverage and retrieval; describe native/Arrow types through configured acquisition; export/inspect/
compare companions after disconnection. Preserve unavailable/partial/refused distinctions throughout.

During implementation run appropriate focused `uv run ci test -- PATH` checks. At the coherent
capability endpoint run relevant typing/lint diagnostics; do not repeat them per edit. After complete
functional scope, run `just turn-end`, `uv run ci test` and `uv run ci check`, accounting for the
applicable functional/native/provider/nonfunctional union at final source/context. Required unavailable
obligations remain open; mocked providers are never native passes. Preserve failed/interrupted results
and reassess evidence after harness/source/runtime changes. Record rustc --version if Rust scope is
selected. No mandatory benefit benchmark; measure only serious unresolved regression/quantitative claims.

The final handoff records delivered contracts, native/runtime/source pins, qualification limits,
changed defaults if any and which existing PM2 evidence is affected. It need not close unrelated
PM2 work or modify that plan; the operator resumes and updates it later. A closed series has no
unowned investigation or missing required delivery evidence, and remains retained under docs/plans.

## Authoring evidence

2026-11-09: focused source/contract foundation assessment only; no product changes, native probes,
provider runs or benchmarks. Product tests are **not_run** for plan writing. Actual documentation
validation commands/outcomes are recorded in STATUS after publication. Target acceptance above is
future work, not a claim that the proposed system already exists.

## PTD-00–02 execution checkpoint · 2026-11-09

Operator instruction to implement follows the finalized PM2 checkpoint at `dde4594e6`; the tree
was clean and no matching active run/test supervisor was observed. PTD-00 acquired development
`corpus_structure_dev`, PostgreSQL18.6, socket port5434, database OID 25921445, system identifier
7701811359771751232, maintenance principal paul, revision/head `semantic_pm2_named_pieces` using
`uv run ci db status --maintenance --json` (**passed**, 2026-11-09). Retain run487/cut604 and its
authenticated source pins, current defaults and execution compiler27. PM2 qualification/selection
remain separate. This instruction supplies the current-tranche handoff; no PM2 default is changed.

PTD-01 owns shared binding resolution, selected declarations, generated surfaces and consumer
migration. PTD-02 core preparation is disjoint; shared consumer edits follow PTD-01 handoff.
ADR-0073 records type-only correspondence. Typed source changes can require regenerated release/
execution/runtime bindings even without new DDL; inspect actual native effects before delivery.
Focused managed tests and coherent endpoint typing/lint cover these packages; PTD-11 remains the
full-series qualification owner. No broad audit or recurring slice gate is introduced.

<a id="ptd-00-02-completion"></a>

### PTD-00–02 completion · 2026-11-09

PTD-00 acquired the handoff; PTD-01 and PTD-02 are implemented and **Tested** at their selected
boundaries. Shared explicit correspondence generates nominal/closed calls, seven Core relations
and four companion families; primitive materializer inputs, raw JSON text and SQL_NULL remain
separate. Wide SQLAlchemy projections require a bounded generated arity cast; static typing does
not prove arbitrary SQL operators or runtime nominal identity. All ADBC production acquisition
uses the explicit core factory; existing cleanup/cancellation/snapshot/COPY contracts are retained.
The child-cleanup and synchronous-acquisition limits remain documented in the companion.

The [delivery evidence](../design_review/evidence/2026-11-09_postgresql-typed-domain/README.md)
records two frozen native transitions, including the compiler 28 runtime-validator integration
repair. Development head is semantic_ptd_runtime_compiler; release2498340837f5 retains the exact
full identity in that evidence. No project activation, run promotion or default change occurred.

Final affected `uv run ci test --json --` selections **passed**: 135 tests in managed result
be28b618badb4ea8a26cf3de610658cc and 46 native journey tests in950e50b599334c85919d5fecebe1281d.
Exact selected modules and earlier failures are recorded in the delivery evidence; final native
contexts follow the corrective migration. Managed successes and native delivery results are held
for this plan. Independent source reviews found no material issues; reviewers ran no tests.
`uv run ci check --only types --json` and `uv run ci model check --json` passed on final production
source. Final lint/docs/turn-end results are recorded in STATUS. Full-series broad qualification,
benchmarks and Rust tests are **not_run** for this scoped work. PTD-03 and the remaining queue are
next; PM2 remains separate. O01/O12 are closed only for their selected package obligations.

## PTD-03–09 execution entry · 2026-11-09

Execution starts at clean 8afc18ad9 (only discovery documentation changed since 464078de2), preserving
completed PTD00–02 and acquired native predecessor semantic_ptd_runtime_compiler. PTD03/08 own
attributed Arrow metadata and independent detached consumption. PTD04 owns checked-recipe
occurrences, v3 artifacts/v2 readers, compiler 19 and typed bounded reports; PTD05/09 share retained
SQL/frozen operation inspection. PTD06 compares exact same-release/source/extent/question scopes,
keeping unmatched/incomparable outcomes explicit. PTD07 composes one materialized eligible set and
tagged channels, using typed VECTOR binds plus native casts (plain typed VALUES resolves as text).
ADR0074 records occurrence/archive ownership; public Alembic Rewriter was assessed and the existing
explicit privilege/global-order walk retained. All selected library mechanisms and acceptance
remain as specified in the conversational execution plan; package completion awaits integration.

<a id="ptd-03-09-completion"></a>

## PTD-03–09 completion · 2026-11-09

**Implemented; scoped functional/native controls Tested.** PTD-03 delivers database-description-v2,
recursive attributed Arrow metadata, independently reflected ENUM/DOMAIN identities and mixed-field
provenance, without inferring unavailable native constraints or domain meaning. PTD-04 delivers
checked recipe occurrences, v3 analysis/v2 truthful archive reading and bounded report-version2
consumers, including CLI/MCP. PTD-05 retains exact before/after SQL and failed diagnostics, stable
structural references and source-text change locations. PTD-09 explains byte-bound ordered native
operations while retaining the existing explicit Alembic traversal and adapters.

PTD-06 delivers typed completed-run coverage comparison with resident root/split selection and
stable both-pin continuations; ephemeral capture IDs remain displayed but are excluded from cursor
identity. Cross-release/changed-question correspondence remains explicitly incomparable or unmatched.
PTD-07 uses typed native-cast vector binds and one materialized eligible relation with tagged bounded
channels, preserving membership, ranks, scores and existing Python fusion. PTD-08 independently
consumes all four families after disconnect, including exact values/types/nullability/metadata/pins.

The [delivery evidence](../design_review/evidence/2026-11-09_postgresql-typed-domain/README.md)
records the exact selected tests, original failed attempts, qualification limits and frozen transition.
Final applicable scope **passed 220 tests**: analysis/retrieval/reporting135, read/exchange29,
authoring27, native authoring23 and reader regressions6. These are distinct node selections;
earlier partial runs are not added to this count. The opt-in locked-native-assets transfer case
is outside this provider-free package scope; its extra invocation was blocked and retained.
No extraction-quality or live-provider qualification follows. PTD-11 reassesses the series union.

Development is semantic_ptd_explanations under semantic compiler 19 (18 readable), execution
compiler 28. Native migration/archive/admission/verification passed; owners/ACLs and table shapes
are preserved. No activation, promotion or default change occurred. Types/lint/model/docs and root
turn-end results are recorded in STATUS. Benchmarks, Rust and full-series qualification are not_run.
The next work is the bounded investigation decisions and selected PTD-10 slices, then PTD-11;
PM2 remains separate and its plan is unchanged. O03/O06 close their selected obligations; multi-branch
O04/O05/O08/O10/O11 remain open only for their separately owned investigation branches.

## PTD-I01–06 investigation decisions · 2026-11-09

**Decision-complete at the inspected scope; selected improvements Proposed, not implemented.**
Executed the approved bounded inquiry against `baea0ed8e`, preserving PTD-00–09's original scoped
receipts. This checkpoint owns the outcomes below; companion accounts supply the detailed reasons,
consumer/source evidence, mechanism limits and concrete revisit premises. A deferred capability is
not an unperformed question: its applicability was assessed against the current consumer and its
missing prerequisite is stated. Re-entry on that prerequisite remains possible without claiming
that the capability is generally unsuitable.

| Investigation | Current outcome and detailed account | Remaining delivery |
| --- | --- | --- |
| PTD-I01 | Explicit context-free codecs/materializers, model/native membership and packet-bound draft operations retained; native value families and graph editing individually assessed in [released types](postgresql-typed-domain/released-types-and-exchange.md) | None selected |
| PTD-I02 | Current finite recipe and specialized Core/DuckDB execution retained; six query forms, procedural inspection, portability/lab, interchange, fingerprints and extension mechanisms individually assessed in [SQL authoring](postgresql-typed-domain/sql-explanation-and-authoring.md) | None selected |
| PTD-I03 | Resident inference deltas and operation-lifetime contextual inventory preparation selected; task scheduling, additional caches, server preparation, batching and streams resolved in [relational operations](postgresql-typed-domain/relational-operations-and-retrieval.md) | PTD-10/inference-delta; PTD-10/contextual-preparation |
| PTD-I04 | Exact eligible FP32 retrieval retained; sparse, token/visual multivectors, HNSW, IVFFlat, half precision, quantization, subvectors, aggregates and reranking individually deferred with concrete premises in [retrieval](postgresql-typed-domain/relational-operations-and-retrieval.md#ptd-i04-decision-account--2026-11-09) | None selected; no new quality/capacity claim |
| PTD-I05 | Existing parameter admission, owned readers, detached replay and protected input routes retained; capsules, nested/JSON, spatial/Rust, federation and lab alternatives assessed in [research access](postgresql-typed-domain/inspection-and-research-access.md) and released types | None selected |
| PTD-I06 | Existing rollback preview, pool/session/read/claim and atomic native lifetimes retained; operational and deployment variants assessed separately in [native operations](postgresql-typed-domain/native-evolution-and-operations.md) | None selected |

### Selected PTD-10 execution queue

The two slices' detailed contracts live in the relational-operations companion. The identifiers
below name slices within existing PTD-10, not a new plan or independent status register.

1. **PTD-10/inference-delta:** keep intermediate closure frontiers resident in the existing trusted
   workspace, preserving a common previous-round delta for all rule groups, full qualification/context
   equality and protected publication. Remove repeated Python frontier hydration/JSONB re-ingress.
   Include independent mixed-rule, cyclic, qualified and empty/fixed-point cases. Preserve final
   typed batch construction and same-session transaction/cleanup guarantees.
2. **PTD-10/contextual-preparation:** prepare the immutable transient inventory relation once at the
   existing source-reader owner lifetime; bind each changing query separately. Retain no connection,
   result or cursor. Key by complete model/release/profile/inventory/representation/vector facts;
   bound retention and rebuild when determinants change. Preserve resident/transient exact ranks,
   full membership, witness precedence, per-query refusal and short borrowed snapshots. Include
   alternating inventory/profile/vector inputs and repeated-owner calls in independent checks.

Neither slice changes a public knowledge identity, D8 support profile, canonical vector precision,
witness policy, publication authority or native deployment fence. Runtime/archive compatibility
still applies even if no DDL changes: regenerate/rebind through the current supported model/runtime
route before native consumers depend on changed executable behavior. PTD-11 remains responsible
for combined final-source qualification. The present execution ends at investigation decisions and
ready delivery contracts; these two product implementations have not been performed here.

### Acquired baseline and verification limits

- **passed**, 2026-11-09: `uv run ci db status --maintenance --json` acquired development
  `corpus_structure_dev`, principal `paul`, PostgreSQL18.6, socket port5434, database OID25921445,
  system identifier7701811359771751232, readable revision/head `semantic_ptd_explanations`.
- **passed**, 2026-11-09: `uv run --no-sync python -B -` with installed-package metadata and the
  configured runtime read snapshot observed SQLAlchemy2.1.6, Psycopg3.3.6, pool3.3.3, pglast8.7,
  SQLGlot30.27.0, pgpq0.12.0, ADBC PostgreSQL1.13.0, pgvector-python0.5.1; catalog query
  `SELECT extversion FROM pg_catalog.pg_extension WHERE extname = 'vector'` returned0.8.7.
  `uv.lock` selects registry pgpq0.12.0; earlier upstream commit references are source evidence,
  not a Git dependency selection.
- Source/installed-library/primary-reference inspection supplies the bounded decisions. No product
  edits, native writes, provider inference, new evaluation, benchmark or deployment occurred.
  Product qualification is **not_run** for this investigation/documentation scope. Earlier
  181/220-test receipts remain historical at their original scopes; no new benefit is promoted
  to Tested or Measured by these decisions.
- No concrete rule change is recommended or awaiting operator approval. PM2 plan, `/10` default,
  retained run/cut provenance and project selection remain unchanged.

Publication verification: `uv run ci docs check` **passed**, 2026-11-09. Focused integration
review confirmed generation-delta ordering and the source-reader lifetime; its shallow-frozen input
concern is incorporated as explicit deep-immutability admission and refusal cases in the selected
contextual-preparation contract. This remains a design contract, not a tested implementation.

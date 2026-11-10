# PostgreSQL typed-domain implementation series

**Status: Planned; execution not started · 2026-11-09.** Target design is Proposed. This coordinator
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

All rows are **planned**, not evidence of implementation or qualification.

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
| [O01](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O01) | Open · selected generated boundary | PTD-01 | Selected calls/columns/results migrated; constraints and determinants preserved |
| [O02](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O02) | Open · investigate adaptation, native invariants and ORM separately | I01 → PTD-10 where selected | Each branch decided; selected full value lifecycle delivered |
| [O03](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O03) | Open · selected attributed explanations | PTD-04 | Current impact/report/archive consumers use supported detail; unknowns remain explicit |
| [O04](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O04) | Open · selected diagnostics/impact; language/procedural/lab branches undecided | PTD-05, I02 →10 | All named branches decided; selected profiles and consumers delivered |
| [O05](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O05) | Open · selected coverage comparison; resident write/preparation alternatives undecided | PTD-06, I03 →10 | Bound report delivered; all additional mechanism/consumer decisions resolved |
| [O06](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O06) | Open · selected exact composition and transient binding | PTD-07 | Full membership/channel correctness preserved across migrated consumers |
| [O07](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O07) | Open · sparse, multivector, ANN/precision and reranking decisions | I04 →10 | Named consumer/policy or reasoned closure per branch; selected journeys evaluated |
| [O08](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O08) | Open · selected companion output; new input/nested routes undecided | PTD-08, I01/I05 →10 | Independent faithful output; each input/representation branch resolved |
| [O09](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O09) | Open · detached default; capsule/bound/offline/ingest/federation/lab choices | I05 →10, PTD-08 | Selected actual research consumer with custody; all alternatives decided |
| [O10](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O10) | Open · selected observed metadata; parameter extension undecided | PTD-03, I05 →10 | Actual description consumer; parameter branch delivered or rule retained by decision |
| [O11](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O11) | Open · selected native workflow; traversal/hook/lifecycle choices | PTD-09, I06 →10 | Frozen drift/ACL/order guarantees and selected native journey; variants decided |
| [O12](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O12) | Open · selected shared explicit acquisition | PTD-02 | All current ADBC callers migrated; no second pool/settings authority |
| [O13](../functional_reviews/postgresql-typed-domain_2026-11-09.md#O13) | Open · preview, sessions, capacity, streams, wakeups, diagnosis/remote and async/distributed decisions | I06 →10 | Every named workflow resolved; selected lifetimes and failures qualified |

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

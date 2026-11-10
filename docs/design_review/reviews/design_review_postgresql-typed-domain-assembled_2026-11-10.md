# PostgreSQL typed-domain assembled target review

## 1. Scope, outcome and coverage

**Design / target · combined library and typed-domain focus · 2026-11-10.**
**Decision: Accept scoped** for the four change scenarios below. The assembled design has coherent
semantic owners and a credible physical realization. No new blocking architectural finding is
established. This is an architectural judgment, not PTD-11 release qualification.

Inspected source is committed `8e69e2b5f6dc56bd01c3a63b27b0a7ee28d313da`, excluding concurrent
PTD-11 test, documentation and qualification work. Diagnostic input is the
[assembled audit refresh](../audit/README.md#ptd-assembled-refresh), publication `044915435`,
at that same source baseline. Standards: core 3.3, efficient-architecture heuristics 1.0,
code-intelligence 1.4 and the repository binding; test-assessment 1.2 informs evidence judgment.

Scope comprises PTD-00–10 and CA01–04: shared generated correspondence, acquired ADBC lifetimes,
attributed metadata, retained SQL/occurrence/native explanations, exact coverage and retrieval,
four-family detached exchange, frozen evolution, resident inference and reader preparation.
The supported workload is the operator's 518-page scientific corpus, bounded published-family
captures, selected run comparisons and exact frozen target inventories. Output budgets do not
imply that exact membership or fixed-point work visits only the returned rows.

The [PTD coordinator](../../plans/postgresql-typed-domain_2026-11-09.md) owns current disposition
and qualification. Decided investigation branches are retained as contextual choices, not reopened
merely because the library offers more features. Wider PM2 interpretation/quality, whole-project
conformance, arbitrary SQL-language support and a test-architecture redesign are not assessed.

## 2. Responsibilities, dependencies and semantic ownership

The functional target needs source-faithful typed distinctions to survive declaration, execution,
inspection and detached consumption. More nominal annotations alone would not achieve it: the
model must also govern admission, values, relationships and what a consumer may claim.

| Responsibility | Semantic owner and composed consumers | Boundary retained |
| --- | --- | --- |
| Type correspondence | `semantic/operation_call_generation.py:158–348`; released operation/physical definitions feed calls, Core columns and companion materializers | `cp:type_source` preserves type meaning without redirecting local value projection or nullability; explicit anchors do not waive validation |
| SQL dependency meaning | `semantic/projection_analysis_products.py:145–213`, `projection_analysis.py`; prepared products feed reports and impact | Captured recipe/physical/runtime inputs determine analysis; occurrences retain role and multiplicity |
| Acquisition and cleanup | `core/db/adbc_lifetime.py`; analytics, description and export compose it | Driver/resolver selection is explicit; purpose and transaction policy remain with each consumer |
| Coverage and retrieval | `serve/coverage_comparison.py:20–155`, `semantic/contextual_retrieval.py:375–500` | Scope correspondence is not quality; dense similarity is not a selected semantic relationship |
| Inference and preparation | `semantic/inference.py:180–310`, `contextual_storage.py:481–550`, `orchestrate/source_reader.py:39–49` | Native fixed-point state and immutable relation preparation are separate from semantic output and borrowed snapshots |
| Native evolution and publication | `semantic/alembic_native.py:156–219`, `execution_admission.py:97–215`, `serve/companion_export.py:130–215` | Frozen catalog facts, restricted effects and atomic detached publication remain separately owned |

### Fact and fidelity table

| Fact family | Provider / fidelity | Coverage, identity and consumers |
| --- | --- | --- |
| Nominal identifier / closed member | Released declarations, resolved and generated | Qualified source reference plus declared anchors; not runtime NewType enforcement or arbitrary SQL-operator typing |
| Value/membership/ordering dependency | Checked recipe plus qualified SQLGlot analysis, derived | Stable retained occurrence/source roles; unknown helper bodies remain unknown; v2 detail remains unavailable |
| Native / Arrow metadata | Actual catalog or ADBC interface observation | Per-interface/session provenance; Arrow display/nullability never invents native constraints or released meaning |
| Coverage comparison | Two completed run/cut/release contexts, derived exact scoped correspondence | Source/question/extent/version and origin custody retained; matched does not mean scientifically better |
| Retrieval candidate | Exact eligible relation plus declared dense/lexical/alias scores, heuristic ranking | Candidate and channel evidence retain inventory/profile/version; selection/witness authority is separate |
| Inferred fact | Admitted finite qualified rules, inference | Canonical context and deterministic fact/direct-proof identity; a working generation is not semantic identity |
| Companion row | Model-derived directional projection of a six-part published pin | Family/schema/logical/serialization identities remain distinct; unknown and unrequested families remain explicit |

## 3. Contracts, constraints and testing boundaries

The explicit model is adequate for this footprint: it distinguishes identifiers, closed values,
local representations, operation calls, qualified facts/proofs, target inventories, retained analysis,
observations and published pins. Actual generators, runtime/native guards and ordinary domain
operations consume those distinctions. It does not rely only on names or output schemas (FP-04/A2).

`source_bindings` traverses `cp:source` and `cp:type_source` under cycle detection, checks conflicting
anchors and representation/member compatibility, and preserves local value constraints. Model-origin
physical backreferences require positive provenance; schema-level declarations cannot silently hide
physical cycles. Selected consumers share these facts rather than hand-maintaining nominal maps.

ADBC children and connection settlement preserve the original BaseException and append cleanup
failures. Driver imports occur at acquisition, preserving lightweight CLI registration. The three
consumers retain their distinct COPY/resolver/snapshot policies. Cancel retirement is synchronized
with physical close; no hard end-to-end acquisition/cleanup deadline is claimed.

Pure correspondence, comparison and analysis tests retain useful independent negative examples.
Native catalog, role, actual ADBC and detached-file claims require their real boundaries; mocks
cannot establish them. Existing native/deployment fixtures deliberately challenge stale catalogs,
changed successor descriptors and interrupted partial effects. The planned native scoped-reader
case strengthens composition evidence rather than establishing a different cache contract.

## 4. Composition and execution

| Question / projection | Method and model | Work, bounds and evidence linkage |
| --- | --- | --- |
| What influences this output? Recipe value/membership/ordering occurrences | Retained checked recipe and qualified SQLGlot facts; exact local attribution with explicit unknown bodies | Capture once at preparation; bounded pages do not change compact validation completeness; no read-time reconstruction of old detail |
| Which run scopes correspond? Two pinned worklists | Exact source/extent/question/version matching, with explicit ambiguous/unmatched/incomparable states | One owned reader snapshot; continuation binds stable contexts and selection, not ephemeral capture identity |
| Which exact candidates rank? Complete eligible inventory | One SQLAlchemy MATERIALIZED CTE; typed VECTOR bind/native cast, cosine, full-text and alias branches; declared fusion | Full membership is checked independently of channel top-k; exactness needs all eligible rows, not merely output budget |
| What finite facts follow? Qualified rule closure | Fixed-generation delta against accumulated native relation; both transitive orientations, conflict-free insertion and scalar counts | No intermediate Python frontier/JSON re-ingress; final facts and direct proofs still materialize for protected publication |
| Can target preparation recur? One reader-bound immutable input | Exact object identity plus run/cut/release/execution/profile/dimension; one detached relation entry | No query-result cache or borrowed connection retained by preparation; every call still validates query/native membership |
| Can detached rows be trusted? Four selected published families | One source snapshot, ADBC batches, independent schema/value checks, atomic no-replace publish | Logical and byte hashes plus six-part pin; children retire before publication and independent offline consumption |

These are operation-shaped compositions, not one service or stage per semantic category. The
materialization choices have concrete purposes: exact eligibility, immutable preparation, retained
attribution and durable detached delivery. Source reasoning supports less transport/reconstruction;
it does not establish latency, memory or throughput improvements. DA-033's separate broader
cumulative-assurance question remains outside this bounded conclusion.

## 5. Change and failure scenarios

| Scenario | Kind, owner and propagation | Architectural assessment / independent challenge |
| --- | --- | --- |
| Add/change a closed identifier field | Domain definition/correspondence change; shared resolution regenerates calls, columns and companion fields | Change reaches representations through one authority; incompatible encodings/anchors/cycles refuse instead of silently coercing. Nullable/SQL_NULL and JSON text remain distinct |
| Select another configured ADBC driver/resolver | Mechanism substitution at acquisition; operation-specific snapshot/metadata contracts still apply | No provider framework is needed. Server/builtin differences are explicit and attributed; denied existing relation must remain distinct from missing relation. Child/body failures challenge the complete composed lifetime |
| Extend a qualified rule or change target inventory | Domain rule or contextual binding change; inference/retrieval owners realize it | Rule kind is explicitly admitted; exact context prevents cross-context conclusions. New immutable input replaces preparation, query changes do not reuse results, and per-call admission remains required |
| Change an overloaded function with dependent trigger/retirement | Native contract/evolution change; frozen global ordering, before/after catalogs and ACLs cross deployment | Exact input signature and acquired native contract matter; registering a future head must not change an older target's expected descriptor; stale-state and rollback controls remain independent |

A served empty/unavailable dependency page cannot establish absence of dependencies. An exact
candidate list does not establish contextual truth, and detached comparison does not establish
cross-product occurrence equivalence. The inspected report/request types preserve those limits.

## 6. Correctness and fidelity gates

Verdicts apply to implemented design in the named scenarios, at source-inspected strength; they
are not a declaration that pending PTD-11 qualification commands passed.

| Gate | Verdict | Decisive scoped evidence |
| --- | --- | --- |
| G1 Authority | pass | Shared declaration resolution; retained input determinants; native catalog expectations bound to acquired contract |
| G2 Semantic fidelity | pass | Type/value correspondence separated; occurrence role/multiplicity retained; SQL/JSON null and metadata provenance remain distinct |
| G3 Validity | pass | Contradictory declarations refuse; explicit runtime/native admission; immutable preparation checks and independently challenged membership |
| G4 Hidden behaviour | pass | Retained inspection/reporting reads facts without executing authored queries; effects remain explicit candidate/deploy/publication operations |
| G5 Consistency/recovery | pass | Owned child/snapshot lifetimes, frozen before-state, operation accounts and atomic publication preserve partial/refused/committed distinctions |
| G6 Transformation/reuse | pass | Complete cache dependencies; native exact membership; qualified fixed point and canonical contexts remain authoritative |
| G7 Truthful capability | pass scoped | Unknowns, unavailable old detail, unrequested families and qualification limits are represented; no measured benefit or broad quality claim is justified |
| G8 Library leverage | pass | Core set/DML constructs, pgvector, ADBC/Arrow and Alembic extensions own generic mechanisms; custom code supplies semantic/custody decisions |
| CI-G1 Fidelity | pass | Similarity, coverage, source attribution, dependency influence and qualified inference retain their different meanings |
| CI-G2 Evidence closure | pass scoped | Exact release/run/cut/source/family bindings and archived analysis govern served scope; unrestricted future consumers are not certified |
| CI-G3 Evaluation integrity | not applicable | This increment neither introduces an evaluation route nor changes reference/parameter policy; existing protected evaluation is outside the review |

## 7. Findings and applicability

No new demonstrated design violation was established within the inspected assembled footprint.
DA-063/067 and affected DA-059/060 examples are corrected in their existing audit homes; their
original evidence remains recoverable in Git. This is not closure of every inherited diagnostic
finding or a new claim about unrelated PM2 semantic assembly. No new F identity is invented for
pending qualification, a missing benchmark or an unexamined future capability.

Preservation obligations are the shared semantic facts, independently expected native/negative
cases, honest incomplete/unavailable states and existing single transaction/publication owners.
The coordinator must retain these when integrating any acceptance repairs.

## 8. Library fit and total complexity

| Selected capability | Why this composition fits / material limit |
| --- | --- |
| SQLAlchemy Core typed columns, `select`, `cte`, `insert().from_select`, PostgreSQL `ON CONFLICT` / `RETURNING` | Retains optimizer-visible set operations and static distinctions; static typing does not validate arbitrary SQL operators. Scalar insertion counts avoid depending on driver rowcount for INSERT/SELECT |
| pgvector `VECTOR`, explicit native casts and cosine expressions | Preserves current exact FP32 policy over declared eligible membership. ANN/HNSW would alter the selected contract and needs a separate scale/quality premise |
| SQLGlot qualification/type support plus retained application occurrence records | Keeps supported analysis facts while avoiding lineage deduplication as occurrence authority. Helper signatures do not reveal helper-body semantics |
| pglast native parsing plus Alembic operation/comparator/renderer extension APIs | Uses native signature/catalog structure and framework migration execution while retaining application-owned ordering, ACL and predecessor meaning. A Rewriter callback alone cannot replace this context |
| Psycopg and psycopg-pool transaction/borrow primitives | Continue caller-owned publication and purpose-role acquisition; async, pipeline, remote/distributed lifetime changes have no newly demonstrated consumer here |
| ADBC PostgreSQL explicit driver/resolver, Arrow readers; PyArrow/Parquet | Composes high-volume observation/export with explicit owned retirement and directional schema checks; separate interface sessions remain attributed rather than merged into fabricated certainty |
| pgpq / shared ArrowWriteProfile at publication | Fresh encoders per COPY use shared schema facts without creating a second publication route; detached export does not claim to implement generalized Arrow ingestion |

The [retained library research](../../library_leverage/libraries/postgresql/briefing.md) and selected
plan companions preserve concrete version/contract references and investigation limits. This review
inspected repository integration rather than repeating broad capability discovery. No new dependency
or version move is recommended. ORM adaptation, general SQL language expansion, alternate index
policy or distributed control machinery would add semantic/lifecycle responsibilities without a
selected consumer in this increment; their existing revisit premises remain appropriate.

## 9. Alternatives and tradeoffs

| Alternative | Whole responsibility and tradeoff | Decision / revisit premise |
| --- | --- | --- |
| Keep primitive-only columns and per-consumer annotations | Fewer generator changes but independently repeated identifier/member decisions and weaker propagation | Reject for selected typed consumers; generic unbound fields remain generic |
| Runtime nominal wrapper/ORM for every value | Stronger construction machinery but another object lifecycle and conversion boundary for a static fidelity need | Retain native/runtime validation and shared generated facts; revisit when an actual mutable object-editing/value consumer requires it |
| Reanalyze historical SQL during reads | Avoids retaining analysis products but changes old meaning under current sources/libraries and invents unavailable detail | Reject; bounded retained facts and explicit v2 unavailability preserve custody |
| Return closure frontier through Python or use one universal recursive IR | Familiar transport/generalization but repeated hydration, or new semantics for mutually enabling rules | Retain native generation deltas; final proof materialization remains necessary |
| Cache complete retrieval results or keep a connection open across method work | Removes more calls but weakens changing-query/admission or borrow lifetime semantics | Reject; prepare only immutable target inputs and preserve per-call snapshots |
| Generic native rewrite/plugin replacement | Can simplify local syntax while keeping the same global privileges/order/context burden | Retain explicit Alembic extension and frozen operations; revisit only when a concrete transform removes that burden coherently |

## 10. Verification and uncertainty

This reviewer ran **no tests, providers, database checks or benchmarks**. Source inspection on
2026-11-10 establishes the structural judgments above. The coordinator's dated CA/PTD-10 receipts
retain their exact source/context and failed/retry history; they are not new runs by republication.

Revealing existing independent cases include wrong nominal call IDs and anchored/schema-slot
cycles; mixed inverse/subproperty/transitive finite closure and different contexts; exact transient/
resident channel membership; configured-driver metadata plus actual denied reader relation;
four-family offline PyArrow consumption; and changed-successor native deployment/rollback controls.
These challenge declared semantics rather than simply comparing generated outputs to themselves.

PTD-11 still needs final applicable union accounting and the selected real GLiNER/parser cases.
The new scoped-reader integration case is concurrent work, excluded from this source baseline.
After integrating it or any repair, the coordinator must reassess affected source applicability.
No broad current provider/quality or final release-qualification claim is made here. Larger inventory
or inference growth remains a future workload premise, not measured capacity at this baseline.

## 11. Authority changes and dispositions

**Rule impacts: none.** No §B decision, accepted ADR, library pin, ranking/witness policy,
activation/default or current-only authority change is recommended. Architectural documentation
should reflect the delivered contracts and preserve historical claims at their original scope.
The PTD coordinator owns its current acceptance and adoption work; the review is evidence, not a
second mutable findings register. Wider opportunity adoption remains separately instructed work.

## 12. Architectural judgment and decision

| Judgment | Verdict | Scenario basis and limit |
| --- | --- | --- |
| A1 Localize change | satisfied | Shared correspondence and retained products localize field/representation changes; configured acquisition and acquired-revision expectations isolate mechanism substitutions |
| A2 Encode domain meaning explicitly | satisfied | Identifiers, local value representation, qualified facts/proofs, occurrence dependencies, scope correspondence and candidate ranking have explicit authorities that govern behavior |
| A3 Extend through composition | satisfied | Typed projections, reports, controlled read/export and native transitions compose existing owners without adding competing stores or generic workflow mechanisms |
| A4 Fit execution to workload | satisfied scoped | Native set-shaped retrieval and generation deltas, one-entry immutable preparation, borrowed snapshots and batched detached transfer provide credible routes for the selected corpus/operation scopes; no numerical performance claim |

**Bounded decision: Accept scoped** for the four named change/failure scenarios and their adjacent
consumers. **Enclosing architecture:** accepted at source-inspected strength for this assembled PTD
footprint; whole-project architecture, wider provider quality and final qualification are not
certified. No additional production redesign is required by this assessment.

Next action belongs to the PTD coordinator: finish actual combined acceptance, resolve any revealed
accepted-scope defect, complete native/nonfunctional qualification and publish adoption/PM2 impact
handoff without relabelling older runtime evidence.

# PCE foundations: combined design/target review

**Independent design/target review, 2026-11-05.** **Decision: accept the scoped target direction;
revise the first implementation proposal before claiming the boundary complete.** The proposed
architecture makes useful local structure independently retainable and assessable while keeping
source location, proposed meaning, independent judgment and publication authority separate.
Extending the existing release, task envelope, source custody and protected reference lifecycle
is the simplest credible realization. A parallel store, evaluator or per-contribution workflow
would add machinery without supplying an additional required guarantee.

The exact first proposal has two material defects: its detail reader applies the byte budget
after payload materialization (**F01**), and an anchorless non-occurrence product can assert an
unresolved physical occurrence identity (**F02**). These are corrections within the selected
architecture. Neither invalidates accepted progressive-review RC01–08. This review supplies the
pre-stage judgment required by PCE-00; it does not certify native deployment, PCE-01–03 completion,
local accuracy, public admission or the enclosing progressive-enrichment system.

## 1. Scope, baseline and evidence

The operator selected the **combined** lens: semantic authority, fidelity, identity, composition
and qualitative execution fit, together with the existing release/compiler, PostgreSQL native
protocol and selected-reader mechanisms. Tier is **design**, purpose **target**. Functional intent
comes from [DESIGN §1.1](../../design/DESIGN.md#section-1-1): a structured, evidence-backed,
typed-queryable representation of what source documents state. The initial workload is retained
statistics-source extraction with many independently useful spans, fields and relationships per
shared invocation, overlapping contexts, failed assembly and explicit zero-output regions. The
operator deployment is local and persistent; native custody and protected labels remain relevant.

Applied standard: core/template **3.3**, efficient-architecture heuristics **1.0**,
code-intelligence profile **1.4**, relevant test-assessment **1.2**, and the
[repository binding](../design_principles/binding/corpus-structure.md). The design-review and
design-review-code-intelligence skills govern this assessment. This is a bounded early-boundary
review, not an assembled-system or broad diagnostic engagement.

Consumed diagnostic input is the working-tree [PCE boundary refresh](../audit/README.md#baseline),
dated 2026-11-05, source baseline `cd9bd586`. Its changed contribution/reference observations
remain scheduled under O01/O02/O08/O09/O10 in the
[PCE coordinator](../../plans/progressive-corpus-enrichment_2026-11-04.md); they are not renamed
as new review findings. The audit's preceding broad baseline retains its own date and exclusions.
Included target context is the pending ADR-0062 and D1/D2/D3/D4/D7/D8/DESIGN edits, inspected as
uncommitted proposals. Their accepted-target labels do not establish implementation.

The exact code subject is contribution proposal
`19ed7989272d178f5de25253d7e1aa4de53e35e0`, inspected in `/tmp/corpus-pce-contributions`.
Decisive sources include `semantic/contributions.py`, `contribution_queries.py`,
`sql/source_contributions.sql`, `sql/source_anchor_coordinates.sql`, common native completion,
`records.py`, observation/compiler/execution/physical declarations and `test_contributions.py`.
Source paths below are relative to `python/corpus-structure/src/corpus_structure/` at that commit.
The adapter and assessment worktrees were changing during review; their drafts are **provisional,
unqualified inputs**, not accepted implementation. A newly reported retained-task replay is not
reviewer-executed evidence and does not alter these conclusions.

**Evidence strength:** target mechanisms are **Proposed**; interfaces/source are
**Interface-checked**; named first-proposal paths are **Implemented**, subject to the defects
below. No reviewer **Tested** or **Measured** claim is made. Static source suffices to establish
the two defects. No database/model execution was necessary to settle this target judgment.

## 2–3. Domain ownership and contracts

| Responsibility | Semantic owner and contract | Physical realization / consumer boundary |
|---|---|---|
| Source occurrence | Authenticated ordered real pieces under exact native/captured source coordinates; independent of interpretation and producer | Existing source-pin/coordinate custody, shared by records and contributions; `occurrence_identity` removes selected-view aliases |
| Producer observation / interpretation | Actual returned item and operation provenance; a role, relation or composite does not inherit correctness from location | Released contribution schema and private task envelope; compact native indexes; consumers must preserve operation/version and report lineage |
| Operation population | Declared question and actual inspected/emitted outcomes, including zero-output operations | `SourceContributionOperation`, separate operation index and report-presence flags |
| Semantic vocabulary and effects | Released declarations govern supported meanings; unsupported effects must refuse preparation | Existing compiler and operation/effect support binding; no new generic plugin engine |
| Assessment | Independent source-first omission frame and output-first support frame; immutable authored passes and exact rubric/version | PCE-03 extends protected reference lifecycle, not `WholeReadingLabel` reinterpretation |
| Knowledge admission | Retention has no publication authority; local admission needs its own future policy/witnesses | Existing consolidation/publication owner; PCE-04 remains outside implemented scope |

The proposed model is adequate for the scoped direction: source-field state, interpretation
disposition, execution outcome, score availability, assessment and public standing remain separate.
The first proposal implements a generic **private retained-product** boundary, not the complete
domain contract for every later operation. `RetainedContributionSemantics` permits free semantic
labels and dispositions; it cannot by itself establish that a label denotes an alias, a governing
unit, an inspected absence or a qualified relation. New actual producers and assessors must bind
their released vocabulary, operation question, scope and rubric before advertising those meanings.
This is unfinished PCE-01–03 work, not evidence that every retained label is already qualified.

| Fact / relation | Attribution and identity | Precision / absence / truth boundary |
|---|---|---|
| Located span or cell piece | Exact source product, pointer, coordinates, recognition provenance where applicable | Native/captured text must reconstruct; synthetic context is not evidence |
| Role/type/link proposal | Contribution identity plus operation and occurrence/endpoints | Proposed meaning remains independent of location correctness; F02 presently weakens the occurrence join |
| Relation/composite | Explicit endpoint roles/member IDs and local closure | Closure proves availability, not semantic correctness, equivalence or attachment truth |
| Empty or missing output | Operation outcome and report product-presence fields | An empty output is not inspected source absence; missing predecessor product is distinct |
| Score | `missing`, `native` or `unsupported`, separately carried value | Native score is not calibrated correctness; missing is not zero |
| Reference judgment | Frozen case, exact question/rubric, independent author provenance | Source-first and output-first denominators stay separate; old whole-record grade is not local truth |

`bind_contributions` checks explicit operation/cardinality closure, released private effects,
source pieces, score presence and endpoint availability. Native completion calls contribution
validation and projection within the existing fenced task transaction. The standing-neutral source
coordinate function is shared with records rather than copied into a second source owner. These
are useful preservation constraints. A valid recordless product must remain possible; fixing F02
must not require record assembly or erase a genuinely unlocated retained item.

## 4–5. Composition, alternatives and revealing scenarios

The selected composition retains details once in the immutable task envelope and uses narrow
native indexes for selection, operation inventory and occurrence/endpoint access. A shared call
can emit many semantic products without a transaction, source reconstruction or lifecycle object
per product. Source-coordinate gathering is operation-scoped; native source-item reads gather
selected pointers and reuse captured recognition text within that validation call. This addresses
the audit's repeated-reconstruction concern without weakening custody. It establishes a credible
physical route, not measured speed or capacity.

| Scenario | Expected owner / change | Assessment |
|---|---|---|
| Correct table value, wrong header or unresolved unit | Retain located value separately; attachment proposal and its assessment may change independently | Proposed contracts preserve the distinction; native reopen/read and independent cases remain obligations |
| Two windows observe one source occurrence; role changes | Source-piece identity stays stable; producer/interpretation identities and dependence remain attributable | First-proposal tests inspect these invariances; actual adapter lineage still requires stable review |
| Add condition/exception role | Extend released vocabulary, operation/rubric and actual consumer binding | Credible domain extension without changing source identity; free labels alone are insufficient |
| Replace retained-report adapter or parser | New adapter/version/dependencies over the same authenticated source owner | Credible mechanism substitution; unchanged source pieces may retain occurrence identity; raw bytes and old grades remain immutable |
| Failed later assembly / empty extraction region | Preserve earlier products and operation inventory without inventing completeness | Explicit product-presence and operation rows support the route; PCE-02/03 must qualify actual zero-output cases |
| Large selected detail / many large contributions | Bound payload before transfer; selected indexes precede hydration | F01 defeats the current reader's bound; metadata-only reads are already narrower |
| Retry or stale source/release | Existing task fencing, source pins and immutable result lifecycle reject stale work | Interface-checked composition; actual native conflict/replay and migration behavior remain unqualified |

The alternatives are (a) keep records as the only typed root, (b) create a separate contribution
store/evaluator/workflow, or (c) extend the existing owners. The record-only root loses useful
partial structure and makes consumers reinterpret raw bytes. The parallel system duplicates source,
release, protected-label and recovery decisions. The selected extension has the best scoped fit,
provided its generic retained envelope is paired with actual operation contracts and protected
assessment rather than treating the envelope as semantic proof.

For F01, use the existing SQLAlchemy/PostgreSQL query boundary to select immutable identifiers and
payload sizes before transferring details, then fetch only the admitted set under the same scope.
Bounded streaming is an available complement: SQLAlchemy Core `yield_per` / `stream_results`
controls row buffering, but **row counts do not bound one arbitrarily large JSON value**. The
[official connection documentation](https://docs.sqlalchemy.org/en/20/core/connections.html#using-server-side-cursors-a-k-a-stream-results),
queried through Context7 on 2026-11-05, supports those APIs; the repository pins SQLAlchemy 2.1.6,
so implementation must use its actual installed interface. No dependency change or new paging
framework is recommended. Relevant heuristics are H2, H5–H8, H15–H20 and H23–H28: share physical
work, filter before hydration, preserve established source custody and keep machinery proportional.

## 6. Independent gates

Gate verdicts concern the stated target and exact first proposal separately. A pass here is a
static design judgment, never a native test result.

| Gate | Target / first proposal | Reason and outstanding action |
|---|---|---|
| G1 Authority | pass / pass for private retention | One release/source/native lifecycle; PCE-03 and future publication must preserve their respective authorities |
| G2 Semantic fidelity | pass / **fail** | Identity/meaning distinction is explicit; unresolved anchorless occurrence references violate it (F02) |
| G3 Validity | pass / **fail** | Native/Python guards exist; F02 admits an unestablished occurrence reference |
| G4 Hidden behavior | pass / pass in inspected scope | Explicit private effects, bound task completion and source reads; no new hidden model fallback |
| G5 Consistency and recovery | pass at target / unresolved natively | Atomic common completion is credible; migration, actual principals, retry and reopen remain obligations |
| G6 Transformation and reuse | pass at target / unresolved for full increment | Retained bytes and new versions are explicit; adapter/correspondence and selected-reader integration are provisional |
| G7 Truthful capability claims | pass for bounded labels / unresolved for executable PCE-03 | Assessment operations are declared in the first proposal but the assessment implementation is a separate unstable draft; do not advertise those declarations as completed support |
| G8 Library leverage | pass in scoped design | Reuses compiler, database transactions/indexes and SQLAlchemy queries; no demonstrated need for another general framework |
| CI-G1 Fidelity | pass at target / **fail** | F02 can associate a proposal with an unestablished occurrence; no local-truth inference is otherwise authorized |
| CI-G2 Evidence closure | pass at target / unresolved for full increment | Shared source owner is preserved; F02 and actual reopen/export closure must be settled |
| CI-G3 Evaluation integrity | pass at target / unresolved natively | Source-only protected protocols are specified; actual new protocol/principal/label isolation remains unqualified |

## 7. Material findings

<a id="F01"></a>
### F01 — Detail byte budget is enforced after payload transfer and materialization

**Source-inspected defect; correction Proposed.** `semantic/contribution_queries.py:81–96`
selects full detail JSON and constructs a tuple of all selected rows at line 84 before checking
`max_bytes` at lines 94–96. An oversized contribution or many large selected contributions can
already consume the client working set and transfer budget before refusal. The row limit does not
bound JSON width. This defeats the reader's stated bounded-detail contract for ordinary retained
reports; safe refusal after allocation does not establish execution fit.

**Principles/judgment:** FP-07, DP-10/20, A4 violated; H6/H7/H17/H18. **Owner:** PCE-01 selected
reader, with PCE-09 later consumer integration. **Correction:** determine the immutable selected
payload set and its transfer budget before fetching payloads; preserve filters, snapshot/source
identity and truthful partial/refused outcome. A metadata size preflight plus selected fetch is a
simple option; streaming alone cannot handle an oversized individual row. No per-field full-source
reconstruction or new generic read framework is warranted.

**Closure:** inspect the final read path and run a focused native oversized-detail case demonstrating
that disallowed payload is not fetched, alongside a within-budget selected read. Current status
and evidence belong in the [PCE coordinator](../../plans/progressive-corpus-enrichment_2026-11-04.md),
not this dated review.

<a id="F02"></a>
### F02 — Anchorless products can claim an unestablished physical occurrence

**Source-inspected defect; correction Proposed.** `semantic/contributions.py:101–105` checks
occurrence identity for `kind == 'occurrence'` and for other rows only when anchors are nonempty.
`semantic/sql/source_contributions.sql:67–71` likewise checks nonempty source pieces. Consequently
an anchorless proposal, relation or diagnostic can supply an arbitrary `occurrence_id`; neither
boundary derives it from authenticated anchors nor resolves it to an available immutable occurrence.
The value is projected into the occurrence index and can falsely associate a proposed meaning
with a genuine located occurrence. Content hashing authenticates the submitted value, not its
source correspondence.

**Principles/judgment:** FP-04, DP-02/03/04/07, CI-01/03/11; A2 violated; G2/G3 and CI-G1 fail.
**Owner:** PCE-01 contribution binding/native source closure. **Correction:** a supplied occurrence
reference must either equal identity derived from that product's authenticated pieces or resolve
through an explicit selected immutable occurrence relationship. Genuinely unlocated retained
products omit the occurrence identity and retain their raw item, reason and operation lineage.
Do not require a complete record. If the first increment supports only anchor-derived identities,
say so and reject unresolved references; later cross-product references need their actual closure.

**Closure:** independent anchorless spoof controls reach both Python and actual protected native
completion and refuse with the intended reason; valid unlocated proposals and supported located
proposal references still survive. Inspect the final index/read path so rejection is not merely
performed in a producer adapter. Disposition belongs in the PCE coordinator.

These findings are independent. F02 establishes source correspondence; F01 controls physical
demand. Neither repeated source validation nor a narrower truth claim fixes the other.

## 8–10. Architectural judgments and verification obligations

| Judgment / foundations | Target judgment | First-proposal / integration limit |
|---|---|---|
| A1 Localize change; FP-01/02/06 | satisfied | Existing source owner and released contribution boundary localize role/parser changes; assessment draft needs final integration inspection |
| A2 Explicit governing model; FP-04/05 | satisfied for scoped target | **violated by F02**; generic private labels do not qualify the later domain meanings |
| A3 Composition; FP-03 | satisfied | Shared task/native/source/reference protocols are appropriate; no evidence yet for actual assembled PCE-02/03 behavior |
| A4 Execution fit; FP-07 | satisfied for target route | **violated by F01**; batching and selected indexes are strengths, not measurements |

Applicable supporting rules are satisfied at the proposed target where the ownership and scenarios
above supply their mechanisms: DP-01/05/06/08/09/13/14/16–19/21–24 and CI-02/04/06/10/12/13.
DP-02/03/04/07 and CI-01/03/11 are constrained by F02; DP-10/20 by F01. Numerical algorithms,
global graph analyses, new fitted models and later embeddings/linking/publication are outside this
early boundary; they receive no positive qualification from this review.

The existing `test_contributions.py` supplies useful independently stated invariance and refusal
expectations: equal spelling at different locations, stable occurrence under role/view changes,
recordless binding, explicit empty-vs-absent products, invalid endpoints, false score zero and
piece order. Its IDs are constructed through production identity helpers, so it does not alone
establish native identity parity, independent source truth or protected persistence. This is a
bounded evidence limitation, not a demand for another production validator or a broad test census.

The package owner must retain these meaningful obligations before completion claims:

- **PCE-01:** actual migration/release registration; Python/native identity and canonical value
  correspondence; authentic source/captured-coordinate refusal; recordless completion, seal,
  reopen and selected read; source/release mismatch, endpoint closure and record-regression
  controls; protected runtime/publication separation. Include F01/F02 controls.
- **PCE-02:** stable adapter/version/report/context dependencies; actual retained bytes producing
  useful independent products; no fabricated hidden candidates or zero scores; genuine missing,
  empty, failed, limited and unrequested regions; partial valid output survives failed assembly.
- **PCE-03:** stable protected operation protocol; actual source-only authoring and immutable
  passes; source-first cases outside matched predictions; separate output-first denominator;
  independent wrong-role/header/unit, absence-vs-unassessed, duplicates, ambiguity, zero-output,
  stale-source/rubric and paired-diff cases; actual restricted-principal refusal and authorized
  evaluator capture. Declared operation names alone do not discharge these obligations.

These are native/API and semantic acceptance obligations, not results invented by this review.
The coordinator chooses focused commands at coherent endpoints; complete PCE-11 qualification
remains later. New provider/model calls are unnecessary merely to reinterpret sufficient retained
bytes; a new provider claim requires its actual execution. Query/CLI/MCP/export journeys and
public eligibility remain under their later owning packages.

## 11. Rule impacts

**None beyond already operator-accepted progressive-review RC01–08.** The recommended corrections
strengthen source identity and bounded selected reads within those choices. ADR-0062 and its
architectural-owner updates remain the coordinator's authority work; review publication neither
accepts an ADR nor changes the old whole-record grades, publication gates or protected principals.
No new dependency, standing review gate, universal confidence threshold or framework is needed.

## 12. Bounded decision and handoff

**Accept scoped** the PCE-00 target direction: independent private contribution roots and operation
assessment composed through existing authorities. **Revise** exact first proposal `19ed7989` for
F01/F02. Inspect the resulting corrections and reconcile stable adapter/assessment integration
before claiming an executable PCE-01–03 boundary. Publication permits the coordinator to resume
the authorized integration and arrange native qualification; it supplies no passing native result.

The enclosing progressive system remains unresolved and unqualified. PCE-04 onward public local
assertions, embeddings/linking, interpretation, complete review bundles and assembled adoption
were not accepted by this bounded review. Their deliberately separate future obligations remain.

**Checks:** `git show 19ed7989`, targeted `rg`/source reads and working-tree diff inspection:
**passed** as read-only inspection commands, 2026-11-05. `uv run pytest`, native migrations,
database/provider/model execution, `just test-all`, `just hygiene`, benchmarks: **not_run** by this
reviewer. Native qualification is **blocked pending stable integrated implementation and the
coordinator's actual focused native results**, not failed or passed. Root owns turn-end maintenance,
coordinator/status changes, authority adoption and final-source evidence applicability.

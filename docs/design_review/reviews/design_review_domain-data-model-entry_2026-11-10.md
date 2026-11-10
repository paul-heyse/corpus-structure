# Domain-data-model authoring entry target review

## 1. Scope, outcome and evidence

**Design / target · combined library and domain-model/principles focus · 2026-11-10.**
**Decision: Accept scoped, at Proposed target-design strength**, for DMC-00–02's effective-model
artifact, shared explorer, frozen candidate inspection and their adjacent consumers. No new
blocking architectural finding or rule impact is established. This is permission to proceed
within the assessed design, not an assertion of implementation or release qualification.

Inspected committed source is `7e30c5d167675aa36a3af23464bb5b6dc0f9ddd4`. Audit input is the
[co-published entry refresh](../audit/README.md#domain-data-model-entry-refresh), at that source
baseline, inheriting the PTD refresh published at `044915435` and its earlier broad account.
Publication edits are documentation only. Standards are core 3.3, efficient-architecture
heuristics 1.0, code-intelligence 1.4 and the repository binding; test-assessment 1.2 informs
verification judgment. Statements about source are **Source-inspected, 2026-11-10**; selected
new behavior remains **Proposed** throughout this review.

The [DMC coordinator](../../plans/domain-data-model_2026-11-10.md) and
[authoring companion](../../plans/domain-data-model/authoring-and-release-products.md) supply
intended behavior; the accepted conversational execution approach adds explicit compiler20,
bounded public interfaces, candidate product custody and the live development archive handoff.
The operator's outcome is to understand a released contract and validate an input without
initializing ingestion/provider machinery or executing a publication. The workload is one
operator/agent inspecting selected classes, properties and operations in supplied closed models,
including the statistics pack and two concurrently open releases.

This review covers declaration attribution, effective/executable meaning, immutable reading,
public reports, candidate custody and existing detached contract export. DMC-03–17's new
recipes, typed archive redesign, terminology, original-engine diagnostic custody, independent
language consumers and whole-series qualification are excluded. Their shared seams are considered;
their eventual architecture is not accepted by this bounded decision.

## 2. Responsibilities and fact fidelity

The target has enough domain distinctions to govern behavior: supplied declaration, contextual
effective property, constraint placement, executable boundary, descriptive annotation, supported
projection, observed admission and illustrative unresolved input. The inspection artifact links
these concepts; it does not acquire authority over validation or native effects.

| Responsibility | Owner and dependent consumers | Preserved boundary |
| --- | --- | --- |
| Source loading and contextual induction | `semantic/prepare.py` `_view`, `_bounds`, `_prepare_release_uncached`; inspection producer | Supplied module/path/digest precedes merge; existing normalized products govern effective meaning |
| Immutable product custody | `semantic/releases.py` `_products`/`_archive_bytes`; `semantic/archive_reader.py` exact opening | Archive3 and arbitrary artifact kinds already suffice; opening is distinct from recompilation and admission |
| Input boundary | `semantic/types.py` `PreparedRelease` adapters and validation methods | Structural and accepted-value validation remain explicit; neither establishes source support or publication |
| Report and effect explanation | `semantic/operation_reporting.py`; generated report schemas | One trusted report owner; existing operation explanation retains effect/precondition policy |
| Transport and candidate selection | `cli/schema.py`, `cli/model.py`, `intervene/semantic_server.py` | CLI/MCP adapt a shared domain read; retained candidate products supply their own immutable release |
| Detached review contracts | `serve/review_bundle.py` `_contract_row` | Existing fields reuse common fact access without changing the bundle's independent export contract |

### Fact and fidelity table

| Fact family | Provider and meaning | Identity, coverage and use |
| --- | --- | --- |
| Authored declaration | Exact supplied YAML, descriptive or constraint declaration | Module name + logical path + source digest; key presence preserves omitted/null/false/empty |
| Effective constraint | Existing contextual compiler and normalized boundary products | Release-local class/property and placement; a traversal participant is not automatically a winning or enforced constraint |
| Contributor relationship | Retained declaration plus compiler traversal/normalization, derived | Separate local/slot/ancestor/mixin/type/normalization roles; unresolved attribution stays explicit |
| Support/admission | Released support product or actual selected deployment observation | Supported, admitted and observed remain distinct; static inspection cannot claim current deployment standing |
| Validation result | Selected released structural or accepted-value adapter | Input digest/purpose and inspected release; no inference of native or source validity |
| Skeleton | Nonvalidating illustration | Finite partial object plus external unresolved placeholders; no fabricated scientific values |
| Historical missing detail | Recorded absence of the new product | Provenance unavailable, not an empty contributor set proving no constraint |

## 3. Contracts, constraints and failure boundaries

**Proposed.** Capture selected raw declarations once where their exact input bytes and effective
compiler decisions coexist. The artifact supplements immutable normalized products rather than
reimplementing LinkML induction. Preserve the closed import map and current located unsupported
construct refusals. Source references promise logical paths rather than exact line coordinates;
that declared grain is sufficient for this authoring workflow and avoids misleading generated lines.

The semantic compiler19→20 move is necessary: the manifest-derived release identity must change
when ordinary preparation adds a product. Retain compiler19 reading. A new artifact does not
require changing archive3's root shape, boundary ABI12 or execution compiler28. The inspection
payload and public report get their own explicit versions; reports use the prepared artifact-set
digest rather than creating an artifact self-reference.

Missing legacy detail, missing required new detail, unknown payload versions and authenticated
malformed detail need distinct located outcomes. Existing digest failures still fail archive
opening. Detail failure must not silently weaken a validator or substitute current source. The
current report helper's default version expression must be extended explicitly for the new report;
handwritten transport schemas would create an avoidable second public contract.

Candidate custody is a concrete prerequisite: `Candidate.from_preview` retains digests and native
products, while candidate creation has the prepared release in hand. Retain that product then,
bound to the managed result. `reconstruct_release` alone is not an authenticated detached reader.
Factor the existing manifest/input/artifact and archive-equality checks before using it; retain
DB-specific snapshot/relational coherence checks at the database reader. Old candidates can return
unavailable contract detail without changing their existing deployment/effect interpretation.

## 4. Composition and qualitative execution fit

| Read or transformation | Semantics and implementation route | Work and lifetime |
| --- | --- | --- |
| Capture authoring facts | Existing YAML load, LinkML contextual view and compiler decisions | One preparation-time compact index; no per-class reparsing of the source closure |
| Inspect one contract | Release-owned definitions/indexes plus optional decoded inspection product | Decode/index at release lifetime, select requested subject before formatting; no current preparation on archived reads |
| Page explanation | Stable rows and selection-bound continuation | Count and byte limits plus explicit continuation; metadata, nested contributors and MCP wire encoding must also remain bounded |
| Validate input | Existing selected-release compiled adapter | Demand-built boundary; validate the supplied input once, not again for each continuation page |
| Inspect candidate | Authenticated managed capsule using archive3 product representation | Managed-result lease/custody; no database publication or checkout recompilation needed for the read |
| Observe native adoption | Existing exact preview/candidate/archive/admission route | Separate explicit effects; metadata production alone supplies no native migration reason |

**Proposed A4 assessment.** This is credible for the supported model collection: preparation walks
the closed declarations once, immutable reads reuse prepared indexes, and results grow with the
selected subject and its contributors rather than hydrating corpus instances or provider models.
Store compact contributor references rather than repeated full source bodies or every inheritance
path. Large descriptions and contributor sets need honest bounded delivery/refusal, not silent
truncation. The selected output bounds are protection, while the release-local access path is the
reason ordinary reads are feasible (H5/H6/H12/H16/H18/H26). No measured speed or capacity gain is claimed.

## 5. Change and failure scenarios

| Scenario | Owned change and expected consequence | Independent challenge |
| --- | --- | --- |
| Add a derived class with mixin/slot/type constraints | Supplied model changes; existing induction produces effective facts; capture links declared contributors | Imported module/digest expectations, overridden versus conjunctive patterns and intersecting slot bounds |
| Replace or upgrade LinkML induction | Preparation owner changes with deliberate determinant/compiler handling; transports retain report contract | Installed `owner`/`from_schema` are not source winners; test genuine contributor semantics independently |
| Open old release beside a new one | Each immutable release supplies its own products and adapters | Different bounds and cross-release continuation rejection; unavailable legacy provenance remains explicit |
| Inspect retained candidate after checkout changes | Managed capsule supplies exact products through authenticated opening | Changed input/artifact/capsule bytes refuse; no current source acquisition to fill detail |
| Inspect/validate recursively required input | Skeleton stays finite; actual input enters selected-release boundary | Placeholders outside payload, absent/null/empty preserved, structural versus accepted-value result identified |
| Read CLI/MCP with reader authority only | Shared function plus reader snapshot; write queue stays unacquired | Public schema parity, full wire bounds, no provider/Docling startup or write-purpose connection |

## 6. Independent judgments and gates

These are target-design judgments, supported by inspected seams and the selected contracts;
implementation acceptance still has to exercise them.

| Judgment | Verdict and basis |
| --- | --- |
| A1 Localize change | Satisfied: preparation owns attribution, archive owns custody, report owns interpretation, transports own delivery |
| A2 Encode domain meaning | Satisfied: effective/declaration/support/observed distinctions govern the read and validation; physical correspondence remains distinct from semantic equality |
| A3 Extend through composition | Satisfied: existing induction, adapters, report generation, archive and managed-result custody compose without a new service or registry |
| A4 Fit execution | Satisfied for the selected model-inspection workload: preparation amortizes stable work and reads select release-local subjects with bounded detail |

| Gate | Verdict and basis |
| --- | --- |
| G1 Authority | Pass: inspection is a derived supplement; executable products keep semantic authority |
| G2 Fidelity | Pass: versions, explicit unavailable detail and contributor/standing distinctions prevent reinterpretation |
| G3 Validity | Pass: existing strict validators and archive checks remain the boundaries; malformed detail has defined outcomes |
| G4 Hidden behavior | Pass: inspection is pure/read-purpose; archive/admission are separate explicit effects |
| G5 Consistency/recovery | Pass: snapshot/capsule identity and request-bound continuation preserve coherence; partial delivery is explicit |
| G6 Transformation/reuse | Pass: archived bytes and release-local indexes govern reuse; no current compiler reconstructs missing historical detail |
| G7 Capability claims | Pass: profile support and observed admission differ; live acceptance remains an obligation rather than a current claim |
| G8 Library leverage | Pass: LinkML contextual induction, Pydantic boundaries, existing archive/report/custody mechanisms are retained; custom provenance addresses their actual gap |
| CI-G1 Fidelity/model | Pass: contributor roles, missing detail and enforcement standing are typed distinctions |
| CI-G2 Evidence closure | Pass: module/path/digest and selected immutable release bind served explanations |
| CI-G3 Non-circular evaluation | Pass at design level: independent known declarations/invalid inputs are required; round-trip agreement alone is insufficient |

FP-01–07 are satisfied for the proposed slice through the mechanisms above. Relevant supporting
rules DP-01–09, DP-12–16, DP-18–24 and CI-01/02/04/06/08/10/11/12/13 share those arguments.
New heuristic analytics and graph/program analyses are outside this authoring slice; the review
makes no separate claim about their correctness or execution fit.

## 7–9. Findings, library fit and alternatives

No additional demonstrated blocking finding is established. This does not close inherited audit
findings or the source opportunities; scheduled disposition stays in the DMC coordinator.

**Interface-checked, 2026-11-10.** Installed LinkML/runtime1.12.1's `SchemaView.induced_slot`
combines slot inheritance and class usages; attributes take priority over reusable slots, numeric
usage bounds intersect, and most other usage metaslots replace. Its `owner` assignment occurs
while traversing ancestors, so it does not prove a winning declaration. `type_ancestors` follows
`typeof`, while the repository's `_bounds` also follows `base`. Preserve the compiler's traversal
rather than substituting that helper. Installed source:
`.venv/lib/python3.14/site-packages/linkml_runtime/utils/schemaview.py`, `induced_slot`1820 and
`type_ancestors`1203. The [selected library account](../../library_leverage/libraries/domain-data-model/briefings/semantic-declarations.md)
provides broader discovery context; this review relies on the inspected narrow contract.

Pydantic's existing release adapters supply strict JSON/Python and structural/accepted-value
validation and directional `json_schema`. A structural schema is useful evidence about its
projection, not a full account of source/native constraints. Native DocGenerator rendering cannot
supply the missing effective/enforced distinction or precise original declaration attribution.
It remains an optional later consumer rather than an authoring prerequisite.

Reparsing current sources per read would lose historical meaning and repeat work. Persisting a
second editable model would duplicate authority. Requiring a new native migration merely for
inspection metadata would add lifecycle machinery without an enforcement benefit. The selected
artifact and authenticated detached custody are the smaller complete route to the actual readers.

## 10. Verification obligations

**Not_run:** product tests, database/provider commands and benchmarks for this static review.
The `git diff 8e69e2b5f HEAD -- …` source comparison passed and identifies the audit delta; it is
not functional qualification. DMC delivery must exercise independent expected provenance,
archive bytes/corruption/version handling, simultaneous releases, continuation/wire bounds,
finite skeletons, valid/invalid inputs, candidate immutability and read-only transport behavior.
The real development CLI/MCP journey must demonstrate existing `Formula` inheritance and a
released operation through exact archived products. Preserve failed receipts and distinguish
bounded package acceptance from DMC-17's final required union. No benchmark is warranted by
an unresolved performance premise identified here.

## 11. Rule impacts

**None.** The selected design changes derived products and discoverability within existing semantic
authority. The required compiler/product version updates and architectural documentation are
ordinary evolution of those contracts. The execution approach's corrected named-type pattern plus
slot-bound example preserves the existing supported profile rather than silently widening it.

## 12. Decision and next boundary

**Accept scoped — Proposed, 2026-11-10.** The DMC-01 artifact/shared-read boundary is ready for
implementation, including frozen candidate custody required for DMC-02. Preserve the explicit
contracts and independent cases above. A concrete contradictory library behavior, a native contract
change or an actual required consumer beyond this boundary reopens the affected decision; it does
not authorize silent loss or automatic widening. The enclosing series and assembled architecture
remain unqualified until their separately scheduled delivery/review. Current package disposition
and closure evidence belong solely to the DMC coordinator.

# Progressive corpus enrichment: contributions and semantic contracts

**Proposed implementation plan, 2026-11-04.** This companion develops PCE-01 and PCE-02 of the
[coordinator](../progressive-corpus-enrichment_2026-11-04.md). The coordinator is the sole owner
of package state, scheduled opportunity disposition, rule-change decisions and combined acceptance.
This document owns the shared contracts below and their migration design; package descriptions
are required future work, not a second execution ledger. Product checks and qualification are
**not_run** for this planning engagement. Source baseline: `a3b0f21d`, inspected 2026-11-04.

The source is the [progressive-enrichment functional review](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md),
particularly [O01](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md#O01),
[O10](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md#O10), and its RC02
intermediate-product impact. The operator explicitly accepted RC01–RC08 as planning decisions on
2026-11-04. That acceptance selects the target; it does not change an accepted ADR, deployed
release, existing admission rule or evidence label. The coordinator schedules the successor
decisions and architectural-owner edits before dependent production changes.

## Resulting behavior and responsibility

An operator can retrieve the exact occurrence of `qs` even if its proposed alias is unsupported,
and retrieve a table value even if its unit or header attachment is unresolved. A failed
definition assembly leaves the located term and defining-text proposals independently inspectable.
These are useful typed products with attributable standing. They do not acquire the authority of
an accepted whole record merely because their source locations are correct.

An operation produces the smallest useful answers to its stated question. A single native model
call may produce occurrences, role proposals and relation alternatives together. Those products
can share a computation and task transaction without sharing semantic identity. An independently
qualified local assertion may later be published by PCE-04, and a complete record or composite may
refer to the same contribution IDs. Assessment is owned by PCE-03; parsers, linking and mathematical
interpretation consume these contracts without independently redefining source or operation identity.

The plan extends the existing semantic release, operation graph, observation and consolidation
spine. It does not create another observation store, workflow engine, solver registry or task
lease protocol. The common layer owns attribution, source coordinates, dependency/custody and
contract shape. A domain pack owns its changing labels, role vocabulary, relation semantics,
qualification meanings and operation-specific assessment questions. New semantic categories must
be declared and compiled; a new instance of an existing category must not require a compiler edit.

## Focused foundation assessment

The assessment uses Core 3.3, Efficient Architecture 1.0, Code Intelligence 1.4 and the repository
binding declared in [standard.toml](../../design_review/design_principles/standard.toml). It is
plan creation under `create-plan`, using the design-review criteria; it is not a refreshed broad
audit. Relevant architectural owners are [D1](../../design/D1-knowledge-representation.md),
[D2](../../design/D2-schema-and-guidelines.md), [D3](../../design/D3-database.md),
[D4](../../design/D4-method-catalog.md), [D5](../../design/D5-consolidation-identity-confidence.md)
and [D6](../../design/D6-orchestration-metrics-policies.md), with D8 as the reading consumer.

| Inspected foundation | What the current code supplies | Change required for this target |
|---|---|---|
| [core/method.py](../../../python/corpus-structure/src/corpus_structure/core/method.py), `ObservationDraft`, `SourceViewDraft`, `UnitResult` | Methods return attributable observations, coverage and measurements; source-view pieces partition actual projected text | Reuse these boundaries; make independently addressable contributions a released product, without requiring a record parent |
| [semantic/observations.py](../../../python/corpus-structure/src/corpus_structure/semantic/observations.py), `observation_inputs`, `bind_result`, `source_value` | Archived report-schema acquisition, release-bound observation keys and lossless JSON scalar/container representation | Add contribution binding and validation to the same release boundary; retain exact source JSON kinds and existing report identity |
| [observations.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml), `SourceObservationBatch`, `SourceObservationReference`, `SourceRecord` | Reports, inputs, source coordinates, records, alternatives and evidence are representable | Declare independent occurrence/proposal/relationship roots and references, instead of forcing useful fragments into `SourceRecord` |
| [semantic/record_projection.py](../../../python/corpus-structure/src/corpus_structure/semantic/record_projection.py), `prepare_record_projection`, `project_record_reports`; [physical.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/physical.yaml) | Finite released record projection; fields, alternatives and evidence have record/interpretation foreign keys | Add contribution projection and relational roots under the same model/compiler authority; current record tables remain valid stronger products |
| [methods/record_assembly.py](../../../python/corpus-structure/src/corpus_structure/methods/record_assembly.py), `_assemble`, `AssemblyResult` | Exact field pieces, diagnostic failures and context dependencies; an unlocated canonical occurrence emits `unlocated_occurrence` and skips the record | Project contributions before the skip; assembly failure becomes an attributable composite failure rather than loss of already located parts |
| [methods/record_readings.py](../../../python/corpus-structure/src/corpus_structure/methods/record_readings.py), `native_model_observations` | Actual returned score shapes and dependence grouping, explicitly uncalibrated | Retain this diagnostic role; never use it as the inventory of all returned spans |
| [semantic/source_contexts.py](../../../python/corpus-structure/src/corpus_structure/semantic/source_contexts.py), `NativeSourcePin`, `SourceInterval`, `NativeSpanEvidence`, `CapturedSpanEvidence` | Exact native/captured coordinate ownership; explicit synthetic intervals and structural context retrieval outcomes | Extend the owner for contribution evidence; do not add a second substring-location or offset-conversion policy |
| [semantic/prepare.py](../../../python/corpus-structure/src/corpus_structure/semantic/prepare.py), [determinants.py](../../../python/corpus-structure/src/corpus_structure/semantic/determinants.py), [execution-model.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/execution-model.yaml) | Pure explicit-input release preparation, finite supported semantics, declared operation outcomes and versioned determinants | Compile contribution contracts and their actual consumer bindings into new releases; refusal for unsupported semantics stays explicit |

These foundations are useful because source reports and knowledge admission already have different
owners. The material gap is the root of the typed product and its consumers, not missing raw-report
retention. Adding an arbitrary JSON diagnostic reader would make every consumer reinterpret the
same payload. Adding a completeness fraction to records would still miss groups discarded before
record construction. Both alternatives fail the selected behavior.

FP-04/A2 and CI-01–04 require the model to preserve what was located, what was proposed and what
was established. FP-07/A4 and heuristics H2/H8/H12/H13/H16/H18/H23 favor shared computation,
selected-column reads and reuse over one task/table/full-context reconstruction per contribution.
The workload is many spans and several competing interpretations per retained source context,
with repeated local review and selective refinement. Compact source/report references plus indexed
operation and source selectors give a credible route; duplicating full reports and context per
span would amplify storage, hydration and validation. No throughput or capacity benefit is measured.

<a id="shared-contracts"></a>
## Shared contracts

These are the series' **Proposed** shared semantics. PCE-01 moves their enduring definitions into
the executable model and owning D-documents; subsequent packages consume the resulting versioned
contract. Names below state meanings, not a demand for a new class or relation for every noun.
They can be physically combined where their custody and access paths agree.

<a id="operation-contract"></a>
### Operation contract

A released operation declaration supplies the following meaning before a producer or public
consumer advertises support:

| Contract element | Required meaning |
|---|---|
| Question and semantic grain | What is being located, typed, linked, attached, normalized or composed, including endpoint roles and direction when relevant |
| Input universe | Selected source revision/regions, context policy and relevant inventories/products; input, eligible and actually inspected populations remain distinguishable |
| Output and alternatives | Released contribution kinds and role/relation vocabulary; how mutually exclusive alternatives and unresolved candidates are represented |
| Preconditions and support | Required source/recognition precision, required products, version compatibility and unsupported cases; no hidden hosted fallback |
| Outcomes and effects | Actual execution/result outcome, absence/empty meaning, limits and reasons; what the operation may persist and whether it can propose or admit knowledge |
| Dependencies and versions | Model/parser/adapter/policy/schema/context identities and complete consumed dependencies, including failed retrieval and rejected evidence when result-affecting |
| Assessment contract | The dimensions on which its result can be judged, applicable source-first omission population, and compatible rubric/frame version supplied by PCE-03 |

Different semantic operations may share one native invocation. The invocation's success does not
mean every contribution is supported, and an empty invocation does not prove the source contains
no relevant structure. For example, a lexical match answers that a string occurs in a source
scope; an alias decision answers whether that occurrence refers to a scoped target. The latter
must not be inferred from the former's label or confidence.

An implementation may use existing declarations, dataclasses and ordinary functions. A generic
pluggable operation framework is not required. Preparation must reject a declaration that names
unsupported outputs or admission effects rather than advertising an operation whose enforcement
is missing. Changing an operation's question or assessment event creates a new version; an old
complete-record label is never silently reclassified as a new local judgment.

<a id="identity-and-source-coordinates"></a>
### Identity and source coordinates

Keep these identities separate and joinable:

1. **Physical occurrence:** an authenticated source revision/product/view and coordinate recipe,
   with an exact interval or ordered real pieces. Native item/cell/text-field and captured
   recognition coordinates retain their actual precision. The source owner defines canonical
   piece identity; equal spelling elsewhere is a different occurrence.
2. **Producer observation:** a particular returned item under invocation, operation/configuration,
   input and report identity. Repeated windows or several providers may observe one physical
   occurrence. They remain distinct observations with shared dependence where applicable.
3. **Interpretation/proposal:** the occurrence or endpoints plus attributed semantic assertion,
   scoped role/relationship/qualification and operation version. Changing `qs` from an alias of
   one concept to an unresolved candidate changes this product, not its source occurrence.
4. **Composite or identity decision:** explicitly named members/endpoints, ordering, dependence,
   exclusions, scope and decision policy. This is stronger meaning than co-occurrence or equal
   text. Canonical identity stays with D1/D5 and PCE-06.

A contribution can cite several real pieces from one or several admitted source pins, preserving
piece order and source relationship. Joined context separators and model-coordinate whitespace
are diagnostics, not quotable source extents. A normalization retains the original lexical value,
transformation and premises. Exact decimal/scientific spelling remains text at the evidence
boundary; a derived numeric convenience column cannot replace it.

Source membership, selected context and semantic applicability are different facts. A selected
note is not thereby attached to a cell. A captured recognition string is not thereby native text.
Cross-view evidence uses authenticated run membership and exact product/projection/recipe bindings.
OCR or coordinate modes unsupported by the owning source protocol remain unavailable with a
reason; this plan does not infer precision from the presence of a substring.

When an adapter cannot locate a returned span, retain its raw item and an unlocated proposal or
diagnostic outcome under the operation contract. Do not mint a false located occurrence. When
only one piece is wrong, expose which contribution failed and retain the independently valid
pieces. The source owner remains the sole authority for establishing and authenticating locations.

<a id="independent-axes"></a>
### Independent axes

The following distinctions must survive producer, storage, query, export and assessment paths.
No single status, confidence or completion percentage may substitute for them.

| Axis | Example and preserved meaning |
|---|---|
| Execution outcome | Succeeded, empty, failed, skipped, unsupported, limited or not run according to the released operation's actual outcome domain |
| Source-field state | Existing `present`, `unstated`, `inapplicable`, `unresolved` retain their source-inspection meanings; a partial inspection cannot assert `unstated` |
| Interpretation disposition | Candidate, selected, rejected, unresolved or other released operation disposition; selection is relative to the stated alternatives and scope |
| Assessment | Boundary, type, role, target, direction, attachment, scope, evidence and integration judgments, each unassessed unless actually established by its protocol |
| Publication standing | Retained private product, inspectable proposal, eligible/admitted local assertion or admitted stronger composite under its own policy |
| Score availability and event | Missing/unsupported native score, uncalibrated decoder score, candidate-relative model quantity and empirical calibration remain different; a missing score is not zero |

The exact outcome vocabulary remains model-owned. This table requires independent meanings,
not a universal enum added alongside the existing finite operation domains. Query facets can
select these axes separately. An unsupported alias proposal may coexist with an exact, independently
assessed mention; rejection of the former neither removes the latter nor promotes another target.

<a id="dependency-and-reuse-contract"></a>
### Dependency and reuse contract

Retain the existing distinction between positive source/derivation premises and computation
dependencies. The latter include consumed counterevidence, rejected alternatives, retrieval
membership and no-match outcomes if changing them can change the result. One stable computation
identity may be referenced by many contribution rows. Report bytes, effective profiles and source
slices are retained once and addressed from those rows.

New adapters may reinterpret retained bytes under a new adapter/operation version when the exact
source context, preparation/profile and returned object are sufficient. This creates a new product
with explicit input lineage; it does not edit the historical report or pretend the old producer
performed a new question. If suppressed candidates, hidden decoder stages or absent source cues
were never retained, their availability is unknown/unavailable. The dependent producer work is
selected only for that missing or inadequate question.

Reuse is admitted by the existing operation/task determinant owner. A parser change should not
force re-extraction when the raw native output and context still suffice; a source-coordinate or
consumed-context change can invalidate dependent occurrences and interpretations. A rubric change
can invalidate assessment applicability without invalidating source bytes. Unknown determinants
remain conservative invalidation inputs. No second cache, reuse checker or restart policy is added.

## PCE-01 — Release, persist and read independent contributions

**Source obligations:** review O01/O10 and RC02; RC03/RC04/RC05/RC06/RC07/RC08 consume this
foundation through the coordinator. PCE-01 does not implement their assessments, admission,
embedding models or solvers.

**Inputs and prerequisites.** Consume the operator-confirmed target and successor-decision route
from the coordinator. Before dependent writes, update D1/D2/D3/D4 with the surviving attribution,
source-product placement and scoped authority obligations of the current ADRs. Preserve the
current distinction between accepted target and deployed behavior. Agreement on this document is
enough for other packages to design their consumers; implemented compiler/native/read contracts
are required before those consumers execute.

**Implementation work.** Extend the current observation/source-product declarations with typed
independent contributions, endpoints, alternative/composite memberships and operation references.
Extend release preparation, boundary generation, product validation and finite projection recipes
in the same change so no declaration is merely documentary. Reuse `SourceObservationReference`
and the existing source/report products where their meaning fits. Contribution roots cannot have
a mandatory `SourceRecord` foreign key; records may reference their contribution lineage.

Generate the required fixed physical metadata and forward Alembic/native migration through the
existing semantic model route. Typed projection tables/relations carry release/realization and
contribution/operation identity with source/evidence/dependency references. Choose indexes for
source/snapshot, operation/version, kind and endpoint/occurrence traversal. Shared raw reports
and context are not repeated per row. Native result completion authenticates source custody and
endpoint/member closure before the task product becomes visible. Private source products remain
excluded from generic knowledge membership, including disconnected or empty products.

Extend existing owned readers with selected-column inventory and bounded detail reads, including
the operation/report population with zero contributions. Filter source and operation before
hydrating evidence. A report's projection retains cardinalities and explicit unsupported payload
shapes so a contribution count can be reconciled to what the adapter actually inspected. Public
knowledge queries do not automatically expose unadmitted private proposals; the inspectable
product reader carries its declared standing. The query/CLI/MCP migration is completed in PCE-04.

Coordinate shared editing surfaces (`observations.yaml`, `execution-model.yaml`, `physical.yaml`,
compiler version/product constants and generated native products) under one integrated change.
Other packages add domain meanings using this contract rather than each introducing root and
custody conventions. An operation-specific product that genuinely needs different invariants
must update the owning model and explain the distinction.

**Available intermediate capability.** A manually specified small contribution batch can be
bound, sealed and read without a record, with authentic source and operation lineage. This is the
prerequisite slice PCE-02/03 and the producer companions need. Full PCE-01 completion still needs
consumer projection integration, forward migration behavior and the independent controls below.

**Independent acceptance cases.** Hand-specify source strings, offsets, operation questions and
expected relationships; production validators can enforce admission but cannot derive both the
actual and expected location/meaning.

- Two equal strings at different native locations produce distinct occurrences; two observations
  of one exact occurrence remain two observations joined to that occurrence. Altering a role
  proposal leaves its occurrence stable; changing the selected source pieces changes its identity.
- A source-pinned role proposal with no record parent survives completion, reopen and selected
  read. A foreign source pin, missing endpoint, malformed piece order or synthetic-gap quotation
  reaches and is refused by the actual protected boundary with its reason.
- A successful operation containing an unsupported relation and an unassessed located span keeps
  those independent axes. Missing native confidence remains missing after persistence/export.
- An explicitly empty inspected scope, a failed execution, an unrequested scope and a missing
  predecessor product are separately observable. An empty contribution relation cannot erase
  the operation population or establish original-source completeness.
- A new domain role instance uses the released declaration path; an unsupported operation effect
  refuses preparation. Generic graph publication still refuses source product datatypes and
  memberships. Existing record projection/admission controls retain their original behavior.

## PCE-02 — Recover contributions from retained native reports before assembly

**Source obligations:** review O01/O10, with O04's returned-native boundary and O08's retained-case
inspection needs; RC02. This package is a versioned adapter and consumer migration. It does not
require another broad model extraction, training attempt or provider run.

**Inputs and prerequisites.** Require PCE-01's actual binding, native custody and reader slice,
plus the retained reports, effective profiles and source contexts already selected by the run.
Use the review's retained table/alias/failed-group evidence as immutable case inputs where it
contains enough context. Evidence from the review is a diagnostic case source, not an independent
truth label for every field. PCE-03 supplies the first independent local judgments in parallel.

**Adapter behavior.** Decode the complete actually returned raw object, preserving group,
field/fragment position, exact value/lexical form, returned confidence shape and report digest.
Apply source-owner mapping to locate actual spans and native table/formula pieces. Emit occurrence,
type/role and relation/qualification proposals before `_assemble` decides whether a canonical
record occurrence exists. Preserve explicit group/fragment membership so a reviewer can traverse
from a raw group that produced no record to its valid and invalid local contributions.

`native_model_observations` remains a score diagnostic. Its current `continue` for unsupported or
absent confidence shapes must not decide which returned objects are retained as contributions.
Score availability is attached separately from source-location availability. Unsupported raw
shapes retain exact bytes and an adapter diagnostic; they are not silently counted as inspected,
empty or wrong. Invalid coordinates retain unlocated diagnostics and cannot generate admitted
source evidence.

Separate the raw-to-contribution adapter from record assembly. The current M1 raw extraction,
retained-reading resolver, structural table/formula branches and future parser adapters consume
the same located products where possible. Record assembly can build stronger `SourceRecord`
interpretations and reference those IDs; it must not re-invent occurrence identity or discard the
parts when `unlocated_occurrence` prevents the record. Preserve existing record policies and
source-field states while the new consumers migrate. Do not turn a local candidate into a record
with false completeness merely to reuse a record query.

**Stored and execution migration.** Add a release-bound adapter operation/version and its raw
report/context/profile dependencies to the existing operation graph and result binding. A new
adapter run over old bytes produces new derived products in a new release/run/cut as required by
the owning lifecycle; it never changes the sealed predecessor task result. Refuse claimed reuse
when the retained preparation hash has no reconstructible context, source pieces are unavailable
or the requested question requires unreturned native proposals. Record the exact missing input
and route only that requirement to future producer work. Adapter preparation and interpretation
occur outside the publication transaction; terminal task completion seals the batch under existing
attempt fences.

**Independent acceptance cases.** Extend the responsibilities exercised by current
[assembly tests](../../../python/corpus-structure/tests/methods/test_record_assembly.py),
[reading tests](../../../python/corpus-structure/tests/methods/test_record_readings.py) and
[source-context tests](../../../python/corpus-structure/tests/semantic/test_source_contexts.py).
Use hand-inspected retained/source examples to specify expected pieces and relations.

- A returned term span from a group rejected for missing canonical occurrence remains retrievable
  with its raw group and exact source. The assembly failure remains visible and no record is invented.
- A returned span without a supported confidence shape produces the same occurrence/role product
  as its scored counterpart, with score availability different. A fake zero must fail the expectation.
- A correct table cell value, ambiguous header path and unresolved unit produce separate local
  products. Rejecting the header/alias attachment leaves value/mention evidence unchanged.
- Multi-piece native source evidence preserves order and exact lexical text. A model span crossing
  synthetic whitespace does not become a fabricated continuous quote. Captured recognition and
  cross-view source claims retain their actual coordinate/relationship contracts.
- Reinterpreting one frozen report under a corrected adapter yields a newly attributed product,
  leaves predecessor bytes/digests unchanged and avoids model initialization. A report that lacks
  necessary source context refuses that interpretation rather than reconstructing plausible text.
- Repeated context windows share physical occurrence where the source contract establishes it,
  retain distinct observations/dependence and never become independent votes by count.

## Migration, retirement and later extension

PCE-01 first supplies the contribution contract and native/read slice. PCE-02 then exposes useful
retained-data products before any new parser, encoder or solver work is needed. PCE-03 can assess
the same frozen population; PCE-04 supplies common product queries and local admission. Later
producers reuse the shared contract, while PCE-09 exports the common inventories and evidence.
This is a dependency order, not a requirement to wait for every later assessment before exposing
an explicitly unassessed retained proposal.

During migration, current record consumers continue to consume complete-record products and
their existing admission path. Move every active new local-contribution consumer away from raw
JSON interpretation, confidence-only inventory and record-parent assumptions in the same package
that introduces that consumer. Once all active consumers have moved, remove superseded adapter
branches, duplicate identity/location reconstruction, transitional report-to-field plumbing and
record-only restrictions in the new path. Keep record assembly for the stronger product.
Remove an old selector only after its active CLI/MCP/export/evaluator callers have a replacement;
an archived format reader with a current historical consumer is not obsolete merely because a
new product exists.

Original source selections, archived semantic releases, immutable migrations, raw A/B/C outputs,
failed/interrupted records, old whole-reading grades and historical plans/evidence stay intact.
New products cite predecessor inputs and new semantics. They do not backfill a historical pass,
rewrite a report or change old identifiers to simulate adoption. PCE-09 owns the final active
consumer/decommissioning reconciliation; the coordinator owns whether its evidence is sufficient.

A future domain can add a condition/exception vocabulary and role-specific assessment without
changing common source identity. A new recognition producer can supply a new explicit coordinate
mode through the source owner without modifying alias semantics. A future parser can replace
the raw adapter while retaining occurrences whose source/recipe identity is unchanged. A new
relationship meaning requires a declaration and assessment contract, rather than relabeling a
similarity or co-occurrence edge. These are extension scenarios, not additional delivery scope.

## Verification boundary

Planned execution uses focused `uv run pytest` scopes for the contribution binding/compiler,
source custody, adapter, current record regression and native migration consumers as those
packages reach coherent endpoints. Existing test modules above are responsibility anchors;
implementation chooses the smallest discriminating scopes, adding new cases where no current
test owns the behavior. Native checks use the persistent development database unless the case
actually requires isolation. Provider/model execution is needed only for a claim about a new
provider output and is not required to reinterpret sufficient retained bytes.

The package controls establish their stated contracts, not full-series qualification. PCE-11
owns the final-source union and assembled native/query/CLI/MCP/export journeys through the
coordinator. No product tests, native migrations, model calls, database writes or benefit
measurements were run for this plan: **not_run**. The planning claims are **Proposed**; source
inspection establishes the baseline described above, not implementation of the new target.

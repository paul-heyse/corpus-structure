# Progressive corpus enrichment: publication, review export and lifecycle

**Implementation target and bounded execution evidence, updated 2026-11-05.** This companion develops PCE-04 and PCE-09 of the
[coordinator](../progressive-corpus-enrichment_2026-11-04.md), the sole owner of package state,
scheduled disposition, rule-change decisions and overall completion. It consumes the shared
[contribution contracts](contributions-and-semantic-contracts.md#shared-contracts), and does not
redefine their identities or maintain another progress register. Source baseline: `a3b0f21d`,
inspected 2026-11-04. The selected execution boundary below supersedes blanket `not_run`
statements for its implemented route. PCE-09 and unselected policies remain Proposed.

## Selected implementation and evidence — 2026-11-05

**Implemented and bounded Tested.** ADR-0064 and D5/D8 own operation-specific local publication
through the existing `PublicationBatch`, COPY staging, SERIALIZABLE retry/fencing and receipt
owner. Deterministic policies admit authenticated source-occurrence/literal claims independently
of complete records. A separate protected independent-contextual-denotation policy requires the
exact supported/stated full C statement, current captured grade, rubric/context/question/version,
source frame and same immutable producer contribution in the graded and selected cuts. Producer
confidence and vector similarity supply neither witness. Raw C remains inaccessible to writers;
only narrowly selected eligible evidence crosses the owned publication boundary and native
publication revalidates it atomically. Development and feature-fit references are eligible;
both held-out partitions refuse.

Actual run38 admits16 denotation claims and33 local source events over17 distinct physical
occurrences, with zero complete-record assertions. Claims and producer/cut witnesses retain
different identities. The common contribution service, CLI and external stdio MCP agree on
private/public standing, selected lineage/support, continuation and changed-selection/byte
refusals. Scientific support is explicitly `unmodeled`; inventory paging establishes no original
source completeness. The selected implementation captures at most10000 selected rows on each
page and refuses larger inventories rather than claiming corpus-scale pagination.

[Local capability evidence](../../design_review/evidence/2026-11-05_pce-local-capabilities/README.md)
retains actual publication/transport receipts and failed attempts. The v3 service separately selects typed interpretation and public assessment witnesses, operation
version, contribution and own physical occurrence. Its occurrence selector excludes anchorless
endpoint-associated products unless selected separately; it makes no association-closure claim.
Public assessment scope is `published_admission_witnesses_only`; missing public witnesses mean
`no_public_assessment`, not unassessed or unsupported. Full protected grades stay evaluator-only.
`ci contributions export` atomically detaches a bounded selection as JSONL plus a pinned manifest
and file hash through the same service. Actual run38 CLI/fresh MCP/export passes. Full detached
review bundles, capability manifests and broader consumer/export/lifecycle adoption remain PCE-09.
Existing complete-record admission and protected whole-reading assessments retain their stronger
meaning; the local path does not remove their cap.

The source [functional review](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md)
supplies [O08](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md#O08),
[O09](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md#O09) and
[O10](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md#O10), alongside O01's
independent products and O02's assessment population. RC04 and RC08 were explicitly accepted as
planning decisions with RC01–RC08 on 2026-11-04. Execution must first carry their consequences
through the coordinator's successor ADR/architectural-owner routes. Planning acceptance does not
remove the current whole-record admission cap or authorize current private products as knowledge.

## Intended operator and consumer behavior

The same pinned query, CLI and MCP journey can show a located term, its competing type/alias
proposals, the rejected relationship and any independently qualified local assertion. A user does
not need a complete definition record to inspect the term. A claim-producing query sees only the
products admitted for the claim it asks for; an inspection query can expose unassessed proposals
with that standing. Source support, population assessment and scientific truth remain different
claims, with unavailable modeling shown explicitly.

An external reviewer receives a complete package for a declared selection, including source-first
no-output cases, exact source slices/piece maps, actual returned reports, contribution inventory,
development judgments and comparable changes. The package can explain why a whole record failed
while preserving correct values and identifying the unresolved relationship. It states when parts
of the source or sealed assessment populations were excluded. A page-level export is never called
a complete corpus export.

Publication remains one consolidation-owned atomic operation. Review export extends the existing
capture/read/export lifecycle; it does not create a parallel report database or workflow service.
Original reports and historical releases remain immutable even after active consumers migrate.

## Foundation assessment and migration surfaces

Use the [declared standard](../../design_review/design_principles/standard.toml), especially
FP-02/04/07, A2/A4, CI-04/10/11/12/13 and heuristics H8/H12/H16/H18–20/H23–25. This is the focused
assessment required for plan authoring, not a new diagnostic audit. Architectural owners are
[D3](../../design/D3-database.md), [D5](../../design/D5-consolidation-identity-confidence.md),
[D6](../../design/D6-orchestration-metrics-policies.md), [D7](../../design/D7-evaluation-goldens-outer-loop.md)
and [D8](../../design/D8-agent-and-query-interfaces.md); semantic declarations remain authoritative
for the eventual executable shapes.

| Inspected surface | Existing useful behavior | Required evolution |
|---|---|---|
| [record_admission.py](../../../python/corpus-structure/src/corpus_structure/semantic/record_admission.py), `cap_record_selections`, `evaluate_record_admissions` | Complete record overlay caps record-produced field facts, with accepted/candidate/rejected/unresolved outcomes | Preserve this stronger claim; add operation-specific local eligibility through common consolidation without changing private record standing |
| [domain_operations.py](../../../python/corpus-structure/src/corpus_structure/semantic/domain_operations.py), [publication.py](../../../python/corpus-structure/src/corpus_structure/semantic/publication.py) | Sealed cuts, explicit domain policy, typed staging, same-connection COPY and atomic SERIALIZABLE publication with exact batch receipt/retry | Integrate local contributions, witnesses and admissions in the same model/native enforcement and transaction |
| [record_results.py](../../../python/corpus-structure/src/corpus_structure/serve/record_results.py), `RecordRequest`, `read_record_result_projection`, continuation identity | Pinned run/cut/projection selectors, bounded full population read, paged presentation and explicit source-coverage limits | Add contribution/operation roots and separate interpretation/assessment/publication facets; retain exact pin and refusal behavior |
| [record_support.py](../../../python/corpus-structure/src/corpus_structure/serve/record_support.py) | Source-reading support is distinct from scientific support; bounded support pages share the pinned record contract | Generalize consumed support to independent contributions; retain unmodeled scientific comparison and exact evidence lineage |
| [record_export.py](../../../python/corpus-structure/src/corpus_structure/serve/record_export.py), `write_record_relations` | Finite typed JSONL/Parquet, schema/count/hash manifests, exact decimal lexical values and `source_coverage=not_established_by_record_projection` | Include independent contribution and operation populations plus separately selected source/report bodies needed for portable review |
| [serve/export.py](../../../python/corpus-structure/src/corpus_structure/serve/export.py), `export_packet` | Detached complete-spine export in a fresh directory, relation binding checks, manifest after writes and final directory publication | Compose review payloads into that owned lifecycle; historical `semantic-export-*` contracts keep their meanings |
| [semantic/analytics.py](../../../python/corpus-structure/src/corpus_structure/semantic/analytics.py), [capture_storage.py](../../../python/corpus-structure/src/corpus_structure/semantic/capture_storage.py), D8 owned capture | Resident/spooled immutable capture, batch iteration, resource ownership and logical/physical digests | Stream selected partitions and deduplicate shared raw/context data; do not materialize full books per contribution |
| [cli/query.py](../../../python/corpus-structure/src/corpus_structure/cli/query.py), [cli/export.py](../../../python/corpus-structure/src/corpus_structure/cli/export.py), [intervene/semantic_server.py](../../../python/corpus-structure/src/corpus_structure/intervene/semantic_server.py) | Existing transport surfaces over common services | Register the same typed operation/contribution selectors and review products without transport-specific semantic classification |

The source review records an interrupted bulk protected prediction SELECT whose validation work
prevented useful inspection. That history does not authorize ordinary reads of protected judgments.
For new assessment/review products, validate/capture the source closure at its owning scope and
perform set-oriented selected-column reads within that binding. Repeated full source reconstruction
per metric or contribution is an unsuitable route for ordinary retained-data review. Retain native
custody checks where trust changes and preserve protected access. Any quantitative speed claim
still needs measurement; none is made here.

## PCE-04 — Common contribution queries and scoped local publication

**Source obligations:** O01/O09/O10, RC04 and the consumer sides of RC02/RC03/RC06. O09 capability
qualification remains owned by PCE-03 and the coordinator; this package supplies the enforcement
and read behavior that qualification consumes.

### Prerequisites and useful early slice

Require PCE-01's implemented typed contribution/operation projection, native source/endpoint
custody and bounded readers. PCE-02 supplies retained-data products for the first useful local
journey. A proposal inspection/query slice can proceed before empirical assessment is available,
provided it returns the correct standing and cannot create admitted knowledge. Local admission
requires the implemented PCE-03 rubric/frame and release-bound policy/witness contract applicable
to that operation and population. A design sketch or model score is not that prerequisite.

Before admission changes, the coordinator's RC04 route updates the D5/D8 authority and the relevant
successor to ADR-0060. Preserve whole-reading rules from ADR-0049/0060 where their stronger event
still applies, source product placement from ADR-0050, direct source custody and identity exclusions.
PCE-04 must not make a candidate record accepted merely to expose one local field assertion.

### Publication and support contract

Common consolidation consumes the sealed final cut and released operation policy. It determines
which contribution assertions may be selected, returning explicit local decisions and their exact
witnesses, alongside the existing complete-record overlay. The policy's event names the local
claim: for example, source occurrence boundary, source-reported value, or attached role under a
declared context. One qualifying event cannot authorize another event's assertion. A located `qs`
can be eligible as an occurrence while its proposed alias target stays unadmitted.

For each admitted assertion preserve contribution/interpretation ID, operation/version, applicable
policy and assessment/proof basis, source occurrence/evidence sets, scoped qualifiers, alternatives
and derivation dependencies. A deterministic source-location validation, independent semantic
judgment, model-relative marginal and empirical calibration are different witnesses. Do not impose
a universal 0.99 threshold, fitted logistic policy or posterior as a condition for every product.
A witness must be the declared kind and applicable to the selected event/population; the producer's
self-reported confidence cannot supply that authority.

Extend generated release/native admission and typed publication rows together. Protected native
publication authenticates the local decision, complete endpoint/member/evidence closure and exact
run/release/cut bindings before making any selected fact visible. Existing generic graph refusal
for source products remains; inspection products do not become domain memberships. Lowered
assertions reference original contribution lineage. Composite membership adds a stronger
interpretation, not new evidence votes. Inference sees only admitted premises under its existing
semantics, and direct source witnesses remain complete through rule closure.

Prepare interpretation, assessment applicability and batch data outside publication locks.
`publish_on_connection`/the existing retry owner seals source products, decisions and selected
assertions atomically in the current SERIALIZABLE transaction. Preserve exact immutable batch
identity, receipt conflict refusal, ambiguous-commit resolution and terminal attempt fencing.
Failure rolls back all new publication effects for that batch; retained earlier observations and
independently published products remain history. No new per-span transaction or retry loop is added.

Support responses expose the same lineage for private inspection and admitted local assertions,
with their standing visible. A source-reading value does not imply scientific truth; a negated
source assertion is not automatically scientific opposition. Scientific support/opposition remains
`unmodeled` where no released proposition/comparison operation exists. PCE-10 may add explicit
cross-document products; it must not upgrade this support contract by relabeling citations.

### Query, CLI and MCP migration

Introduce common typed requests over the owned contribution projection. The selection binds a
source/snapshot/run/cut, operation/version, contribution kind, optional occurrence/contribution
identity and separately selectable interpretation, assessment and publication facets. Unsupported
facet combinations fail explicitly. A transport can add presentation choices but cannot reinterpret
the operation's outcome or decide that an empty result means source absence.

Bind continuation tokens to normalized selection, release, realization/revision and projection
identity, as current record journeys already do. Source reads, evidence links and subsequent pages
retain that pin. A changed source, operation, rubric, facet or snapshot refuses an old continuation.
Budgets cover rows, bytes and hydrated evidence, with limits describing the affected selection.
A page may be complete for its selected product population while original-source coverage remains
unestablished. Preserve that distinction in machine output as well as readable text.

Migrate common query services, CLI query/export routes, registered MCP tool schemas, support and
explanation readers, and capability-manifest consumers together. Existing record queries continue
to expose the stronger record population with its original meaning. New local queries must not
depend on a complete record result being available, and source-only/no-output scopes need their
own operation inventory path. Retained reads acquire no model worker. Convenience summaries must
derive counts from the same selected inventory rather than scanning raw reports independently.

### Independent acceptance cases

Use specified source pieces, policy inputs and expected decisions, with real protected operations
for custody/publication claims. Existing
[admission](../../../python/corpus-structure/tests/semantic/test_record_admission.py),
[publication](../../../python/corpus-structure/tests/semantic/test_record_publication_native.py),
[consumer](../../../python/corpus-structure/tests/semantic/test_record_consumers.py) and
[support](../../../python/corpus-structure/tests/semantic/test_record_support_native.py) tests
identify current responsibilities; extend them or add focused scopes at the owning boundaries.

- A correctly located term from a failed definition is inspectable before assessment. After a
  valid local eligibility witness, the occurrence assertion can be queried while the definition
  record and alias remain unaccepted. Giving the occurrence witness to alias admission refuses.
- A private record with one correct value remains private and fails whole-reading admission if
  its complete contract fails. Its independently qualified value is admitted only by the local
  path. Removing the whole-record cap must make the independent regression fail.
- Missing/inapplicable/foreign witnesses, stale cut/release, foreign source or endpoint evidence
  and private-source-product graph ingress are refused at the native boundary, not merely by a
  friendly constructor. No partial selected knowledge remains after a failed publication.
- Duplicate publication with the same batch returns its exact receipt; changed content under
  the same identity conflicts. Cancellation/ambiguous commit follows the existing owner and
  cannot fabricate either success or safe rollback after committed publication.
- Query, CLI and actual registered MCP responses select the same contribution population and
  show separate assessment/interpretation/standing. Altering a selector or pin invalidates the
  continuation; exact lexical values and evidence links survive every surface.
- Explicit empty, failed, limited, unrequested and unavailable scopes remain distinguishable.
  Source support cannot be presented as scientific support or complete-source assessment.

## PCE-09 — Portable review, inventory and preservation-aware cutover

**Source obligations:** O08/O10 and the review-consumer side of O01/O02/O09, RC08; consumes
RC01/RC03's capability/population account without relabeling existing full-record metrics.

### Prerequisites and scope

The early review slice needs PCE-01/02's actual retained contribution and operation inventories,
source reader/capture and PCE-03's development judgments when available. It can export unassessed
products with explicit missing assessment. Complete PCE-09 integrates PCE-04 common selectors
and the actual parser, embedding/linking, mathematical and cross-document products selected by
the coordinator. It cannot close while claiming complete detail but omitting a required case
context, raw returned item or assessment dimension without describing the omission.

Define a declared review selection before reading data: source editions/excerpts and known
physical maps; run/cut/release/snapshot; operations and versions; source cases/populations;
included assessment cohorts and authority; desired payload classes and explicit resource bounds.
Human and AI review use the same evidence and population declaration. This is a concrete export
selection, not a new universal review registry or a claim that all corpus knowledge was inspected.

### Inventory and paired change views

Compose the following linked views from common readers; counts name their unit and cannot be
added across kinds as a progress score.

| View | Contents and limits |
|---|---|
| Source inventory | Original/edition/excerpt, physical page mapping where known, selected regions, source health and unavailable/unprocessed source; retained bytes do not imply processed coverage |
| Operation inventory | Input/eligible/inspected scopes, actual executions and empty/failed/skipped/limited/unrequested outcomes; expose diagnostics available versus never retained |
| Contribution inventory | Distinct physical occurrences, producer observations, semantic proposals, relationships/qualifications, alternatives and composite/identity decisions |
| Assessment matrix | PCE-03's event/dimension, independent judgments and rubric/frame/population applicability, with unassessed cells explicit |
| Gap account | Source-first missed structures and output-first unsupported structures, linked to source cases; observed stage facts distinct from hypothesized cause |
| Change account | Newly captured, corrected, regressed, newly spurious and unresolved contributions, with upstream input/operation/context changes visible |
| Capability account | Operation/version, domain distinctions, source population, policy/context, applicable assessment and limits; stronger complete-record grades remain separate |

Bind comparisons to baseline/revised product identities and an explicit common source-case
correspondence. Equal strings or local IDs do not establish it. A source/coordinate recipe or
semantic-grain change either has a declared justified mapping or produces an incomparable result
with its reason. Separate changed upstream input from changed interpretation under fixed input.
Retain both products and comparison protocol; do not rewrite the baseline to make a paired view.
Paired statistical conclusions remain with PCE-03's statistics owner.

### Portable package and physical route

Extend the existing capture and fresh-directory export owner with a versioned review format.
The package contains a readable overview and machine-readable contracts/tables sufficient to
reconstruct its declared cases without database access:

- A manifest binds exact selection, source/run/cut/release/snapshot and projection identities,
  operation/rubric/schema versions, relations, counts, logical and serialization digests, actual
  omissions and the meaning of every completeness claim.
- Versioned JSONL/Parquet relations carry source/operation/contribution/assessment/gap/change
  inventories, alternative/member/endpoint references and exact lexical values. Their schema
  metadata is checked against the same captured binding as ordinary readers.
- Source excerpts or self-contained source slices include the actual consumed context, ordered
  piece maps and native/captured addresses needed for each case. A `_retained_report` text hash
  without reconstructible context is insufficient. Page maps unknown in the source inventory
  remain unknown rather than invented from excerpt page numbering.
- Raw returned objects, effective profile/preparation/configuration and computation/dependency
  references support tracing each product. Include actual diagnostics where retained and identify
  hidden or unavailable native stages. Shared reports/context appear once and are referenced by ID.
- Exact operation contracts/rubrics and permitted development judgments accompany the cases.
  Comparison artifacts retain both sides, correspondence and incompatible-case reasons. A compact
  sealed-population inventory describes exclusions without leaking protected feedback.

The export captures one consistent selected closure through existing owned snapshot reads. Use
set-oriented population queries, selected columns and source/report IDs first; hydrate detail
only for selected cases. Validate authenticated source closure at the appropriate immutable scope
and reuse it while its premises hold, preserving protected access boundaries. Stream or spool
bounded partitions through existing batch readers/Parquet writers and compute completion manifests
after bodies are written. Existing capture cancellation and reader/transaction settlement remain
the lifetime owner; no report-specific worker pool, database mirror or duplicated closer loop.

Publish the finished directory through the existing fresh-destination/no-replace lifecycle after
all required readers are settled. A failed/cancelled pre-publication export has no successful
completion receipt. Once publication has linearized, cancellation cannot relabel it as absent.
An unavailable, permission-excluded or over-limit required body produces an explicit omission
with affected coverage, or refusal when the requested completeness contract cannot tolerate it.
A reduced export must declare a reduced scope rather than silently emitting a successful full
selection. Do not copy model weights, virtual environments, database directories or redundant
full books into every packet.

### Protected assessment and feedback lifecycle

Ordinary development packages include development judgments and an explicit inventory of sealed
fitting/calibration/final cohorts. Protected judgments require their own authorization and reader
capability; export selection cannot elevate an ordinary producer principal. A failed protected read
does not fall back to a more privileged or unprotected connection. A manifest records the exclusion
without exposing the held-out labels.

If deliberately authorized held-out feedback becomes development input, record that cohort's
exposure for future assessment applicability and obtain a fresh valid population for future claims.
Keep historical passes, old source references and grading protocols intact. A rubric/event/grain
change creates a new assessment protocol under PCE-03; it does not transfer old labels to new truth.
Feedback may select future refinement work only under this explicit population accounting.

### Cutover and legacy decommissioning

Use the following meaningful transitions, with the coordinator owning their actual state:

1. Independent retained products become inspectable through the new common contract. Existing
   record queries and archived exports remain usable. No default release/adoption changes follow.
2. Local policy and native witnesses become available for selected capabilities. Move relevant
   query/support/capability consumers to PCE-04; preserve complete-record admission for complete
   records. The release can expose mixed maturity with accurately scoped standing.
3. Portable review consumes the same selectors, inventories and source closure as live reads.
   Migrate CLI/MCP export dispatch, support/explanation consumers, detached analysis, evaluator
   comparisons and operator-facing summaries. Remove independent raw-JSON classification and
   record-only assumptions from every active local-contribution path.
4. Reconcile remaining active consumers and retire only replaced runtime branches, temporary
   conversion glue, obsolete current selectors and duplicated status/count interpretations whose
   replacement is functional and qualified. Keep a supported historical reader where an actual
   historical consumer requires it. Enduring meaning moves into D1–D8/model authorities; plans
   retain their final state and evidence links.

The migration does not repeat all historical M1 scope or use M1's five-family completion gate as
the new success criterion. The coordinator records exactly which active obligations transfer,
which remain stronger whole-record scope and which are superseded by an accepted rule decision.
Cutover must name its consumers and selected release. Provisioning, native migration, qualification
and default activation remain separate effects; production implementation does not silently adopt
the new default. PCE-11 and the coordinator own the final release/adoption decision and evidence.

Preserve original source selections, releases, immutable migrations, old report A/B/C bytes,
failed/interrupted runs, historical full-reading grades, plans and evidence. Do not delete or
rewrite them to simplify the new path. New adapter/schema/policy versions add attributed products
and explicit comparison correspondence. Recovery reuses sufficient retained products under the
existing determinant rules; it does not rerun broad extraction solely because an export failed.
Before removing any runtime branch, locate its current callers and historical-read obligations
in the changed tree, rather than assuming the baseline inventory is exhaustive.

### Independent acceptance cases

Use selected source cases with hand-specified expected counts, source pieces and relationship
outcomes. Existing [export](../../../python/corpus-structure/tests/semantic/test_standing_export.py),
[companion export](../../../python/corpus-structure/tests/semantic/test_companion_export_native.py),
[native export](../../../python/corpus-structure/tests/semantic/test_native_exports.py) and
[diagnostic selection](../../../python/corpus-structure/tests/semantic/test_record_diagnostic_selection.py)
tests are current responsibility anchors, not sufficient evidence for the new complete review.

- A detached reviewer follows a correct span through a rejected alias and a failed record using
  only exported source/pieces, raw output, typed contributions and local judgments. Removing the
  context body or changing a piece map is detected; a report hash alone cannot satisfy the case.
- A no-output source region appears in source/operation/gap views. Counts separately reconcile
  physical occurrences, observations, interpretations and admitted assertions. A retained full
  PDF and a selected excerpt cannot be counted as equivalent complete source coverage.
- JSONL and Parquet represent the same declared case population and preserve exact lexical
  values, direction, qualifiers, alternatives, evidence, missing score and unassessed dimensions.
  A reader checks manifest/schema/count/hash correspondence and detects omitted required members.
- A fixed-source paired comparison identifies an independently specified correction/regression.
  A different edition or semantic grain with no valid correspondence is incomparable; equal
  spelling does not force a match. Historical products and labels remain byte-identical.
- Missing/permission-excluded/over-limit detail yields the specified omission/refusal and affected
  coverage. An ordinary development export cannot retrieve sealed labels; authorized exposure
  changes future applicability without changing old grading receipts.
- Cancellation before final publication, a corrupt captured relation and an already-existing
  destination leave no claimed complete new package; readers and snapshot resources settle under
  the existing lifetime owner. A completed published package remains a completed effect.
- A retained-data inspection/export initializes no model worker. Shared context/raw objects are
  referenced once across many contributions; bounded spooled export does not first construct the
  entire detailed corpus in memory. Required custody and authorization still execute.
- Active query/CLI/MCP and detached export consumers agree on one selection and standing. A
  historical record export remains readable under its original contract after current-path cleanup.

## Extension scenarios, tradeoffs and completion boundary

A future review facet for attribution/modality is expressed through a domain operation and PCE-03
rubric plus generic typed selection, rather than a custom report parser in each transport. A new
source format supplies authenticated source slices through the source owner; review export reuses
its identity and piece map without inventing page coordinates. A new cross-document relation can
join the inventories only with its actual endpoint/scope/comparability semantics. These examples
explain the boundaries; they are not additional scope beyond the coordinator's selected products.

Rich portable context adds disk and serialization work, but is necessary for review without
database access. Shared retained objects, source selection and spooled batches keep that work
proportional to declared cases. Separate full-body requests from ordinary bounded query pages;
small page output alone does not bound capture/hydration work. Set-oriented reads and immutable
closure reuse remove avoidable reconstruction while maintaining trust boundaries. Assess these
choices qualitatively for large books, many alternatives, sparse failures and repeated review;
no universal resource estimator or new runtime accounting machinery is required.

During execution, use targeted `uv run pytest` scopes for actual publication/native admission,
query/continuation/support, CLI/MCP, capture/export cancellation and detached review behavior when
each coherent package reaches its endpoint. Actual registered external stdio MCP and real native
database controls are required for those integration claims; mocks establish only their local
scope. PCE-09's detached-review acceptance must use the assembled package without database access.
PCE-11 owns final-source full union, review cadence and applicable broad qualification through the
coordinator. No package-local pass establishes benefit magnitude or complete-series acceptance.

No production changes, model/provider execution, database writes, functional test commands or
performance measurements were run for this plan: **not_run**. Publication/link checks for the
plan documents are the coordinator's responsibility and do not establish product qualification.

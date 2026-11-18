# Lane OLDER-B: DA-041 to DA-067 (except DA-058) at `5139eaba3`

Design-reviewer audit contribution, 2026-11-18. Static source reading only. No test, database
or provider run. Source facts come from the frozen snapshot `snap6/` (paths below are relative
to `snap6/python/corpus-structure/src/corpus_structure/` unless they start with `domains/`,
`docs/` or `model/`). The snapshot does not contain `domains/`, so domain-pack facts were read
with `git show 5139eaba3:domains/...`. History was read with read-only git on explicit commits.

**How I read.** For each identity I took the original diagnosis from its first publication
(`85787108d` for DA-041–052, `90ed25c46` for DA-053, `9a265181b` for DA-054, `86425f72e` for
DA-055–057, `0cab80335` for DA-059–067) and its last full text (`fbd3f2a98~1`). Then I searched
the snapshot by module name *and* by concept (names of the decision, the check or the field).
Owners were read in the regions cited. Nothing was read end to end except
`methods/llm/producer.py` and `methods/llm/agent_opus.py`. Deletion commits come from
`git log --diff-filter=D 5139eaba3 -- <path>`.

## DA-055, DA-056, DA-057: the anchors are present, with upper-case ids

These three were never missing. They were published on 2026-11-06 in
`docs/design_review/audit/witnessed-enrichment.md` at `86425f72e` ("WCE refresh assembled
diagnostic account DA-055 through DA-057"), as WCE-AF01/AF02/AF03. They were restated on
2026-11-08 at `0cab80335`, and at `5139eaba3` they are carried at
`docs/design_review/audit/witnessed-enrichment.md:11–19` as `<a id="DA-055"></a>` and so on.
That is the only page that uses upper-case anchors, so a search for `id="da-055"` misses them.
The design review `design_review_domain-model-alignment_2026-11-08.md:212` links `#DA-056`.
None of them was retired, merged or left unassigned. Their statuses are below.

## Status table

| ID | Original claim (one sentence) | Subject at `5139eaba3` | Status | Conf. |
|---|---|---|---|---|
| DA-041 | A run had no recorded outcome, partial state or orphan state: consolidation failures after the final cut went unrecorded, and `ops.run` had no place for a reason | Run/task machinery is gone (`orchestrate/commands.py` removed in `64455a0f1`, `orchestrate/semantic.py` in `8b7b369a9`) | No longer applicable; the cause does not recur | High |
| DA-042 | Immutable products (the release, agent packets) were re-derived on every use | `load_release` survives as the full-verification route; readers use `open_release` | Changed footprint (partly corrected) | Medium |
| DA-043 | Consolidation and inference read the whole input realization through IN-lists, and the work grew quadratically within the cut | `semantic/domain_operations.py` (`64455a0f1`) and `semantic/consolidation.py` (`47dc7b873`) are gone; the successor is `semantic/rich_consolidation.py` | No longer applicable; the successor's scaling was not audited | Medium |
| DA-044 | Representatives and attributions were chosen by incidental ordering (first claim wins; minimum hash or lexical value) | Successor is in `semantic/rich_rule_evaluation.py` and `rich_decisions.py` | Corrected; the correction holds at new sites | Medium-high |
| DA-045 | Go-forward contracts lived in legacy modules, and layers depended upward | The legacy packages (`consolidate`, `validate`, `pool`, `orchestrate.phase0`) are gone; `core.*` remains | Changed footprint | Medium-high |
| DA-046 | The semantic core carried statistics and mathematical-text vocabulary | `model/semantic/core.yaml` still holds it | Stands (open boundary question) | High |
| DA-047 | Surfaces were maintained with no go-forward consumer | The cited views, tools and fuse are gone; authored SQL and the producer binding survive with no supplier or caller | Changed footprint; evidence for DA-080 | Medium |
| DA-048 | Pack composition namespaces each pack's operation inputs, but consumers read only root names, so checks are skipped | `semantic/regeneration.py:153–277` | Partly corrected / changed footprint | Medium |
| DA-049 | Archived releases had no declared compatibility lifetime; any change to the stack stranded them | ADR-0047 declares current-only operation | Corrected by decision; the behaviour holds as a declared limit | High |
| DA-050 | Explanations and other follow-up references sat outside the pinned journey and re-resolved `promoted` | `cli/explain.py` (`bcdc8d214`) and `serve/journey.py` (`bcff594c2`) are gone | No longer applicable; the cause does not recur | Medium |
| DA-051 | Producer attribution was declared by configuration and never established by the executing provider | Recognition and external-execution receipts | Corrected; holds | Medium |
| DA-052 | Claim-proposal production was welded to the name `agent.opus` rather than to a declared producer contract | `methods/llm/producer.py` and `agent_opus.py` still exist, with no importer | No longer applicable; the leftover owner is evidence for DA-080 | Medium-high |
| DA-053 | Source execution left claims it had taken outside renewal ownership | `semantic/claim_lifetime.py` and `orchestrate/data_operations.py` | Corrected; holds at new sites (small inferred residual) | Medium |
| DA-054 | Annotation task identity included unrelated downstream run settings | The task-dependency projection is gone (`task_dependency_scope.sql` removed in `200e396fc`) | Superseded by DA-078 (and DA-069) | Medium-high |
| DA-055 | Table attachments that can co-apply became exclusive alternatives | `methods/table_interpretation.py` | Corrected; holds | High |
| DA-056 | A completed numerical result lacked invariants; by 2026-11-08, event probabilities could contradict the displayed support | `semantic/local_interpretation_reports.py` | Corrected (`f3f2d1ca5`); the native counterpart was removed. The page's "open" note is stale | Medium-high |
| DA-057 | Dossiers erased predecessor interpretation and applicability | `methods/structural_products.py`, `semantic/structural_admission.py` | Corrected; holds | Medium-high |
| DA-059 | Managed model receipts omitted facts that the immediate reports carried | `cli/managed.py`, `cli/model.py` | Corrected; holds | Medium-high |
| DA-060 | Evidence retention lost unresolved cleanup custody | `cli/operations.py`, `cli/managed.py` | Corrected; holds | High |
| DA-061 | A formula witness depended on the installed release recipe, with room for one witness | `ingest/pdf_hierarchy.py` | Corrected (`8dc0bac00`); holds | Medium-high |
| DA-062 | Native report decoding discarded the object-field positions that replay requires | `semantic/source_value_native.py` | Corrected (`f3f2d1ca5`; regenerated in `366a5458d`); holds | High |
| DA-063 | Native admission checked the checkout head instead of the bound target revision | `semantic/execution_admission.py` | Corrected; holds | High |
| DA-064 | Dry visual routing could classify unexamined cues as a skip | `semantic/visual_routing.py` | Corrected; holds | High |
| DA-065 | Located-definition checks authenticated spans without authenticating the claimed derivation basis | `semantic/structural_products.py`, `methods/definition_applicability.py` | Changed footprint: corrected in `9e04d04d1`; enforcement retired on 2026-11-15/16 | Low-medium |
| DA-066 | A bounded mapped artifact could exceed every typed Reader budget | `serve/pdf_visual_evidence.py`, `semantic/visual_read_native.py` | Corrected; holds | Medium |
| DA-067 | Projection analysis could change under the same release identity, because it was taken from the installed physical profile | `semantic/projection_analysis_products.py` | Corrected; holds | High |

## Notes per identity (where the row needs evidence)

**DA-041.** The replacement declares a lifecycle: `pending, running, done, empty, failed,
cancelled`, with terminal and receipt-required sets
(`model/semantic/data-operation-native.yaml:5–13`). Failures go into an immutable table,
`ops.data_attempt_failure`, keyed by the exact attempt
(`model/semantic/data-operation-physical.yaml:598–617`). The release program requires a
nonempty code and message (`semantic/data_attempt_release_native.py:300–331`) and refuses to
change a recorded failure (`:393–394`). A running task whose lease has expired can be claimed
again (`semantic/data_claim_native.py:74–79, 200–206`). Lost attempts are reported with a
reason (`semantic/data_operation_renewal.py:61–93, 178–192`). This is a sound design. I did
not check whether a request-level aggregate states "partial".

**DA-042.** The cause partly recurs. Readers open releases without re-preparing them (55
`open_release` call sites, by grep). Full re-derivation through `load_release` /
`load_release_inputs` still runs at these sites:
- every demand registration: `semantic/data_operation_service.py:142, 300`;
  `orchestrate/source_operation.py:144, 324`; `orchestrate/native_execution.py:41`;
- every acquisition of an execution basis: `semantic/data_operation_service.py:182`;
- project setup: `orchestrate/project.py:106, 159`.

Within one process the cost is bounded by `lru_cache(maxsize=8)`
(`semantic/prepare.py:590–607`). The per-region book manifestation recorded on 2026-11-11 is
gone with `orchestrate/characterization.py` (removed in `fe69fddb0`). Whether re-preparing at
registration is required for trust is the open DA-033 question, and the capture with no holder
is DA-083. I record this as context for those findings, not as a separate defect. Call counts
per run were not established.

**DA-043.** The successor indexes facts by slot in dictionaries
(`semantic/rich_consolidation.py:356–372`). I found no IN-list load of a whole realization on
this path. Pairwise comparison within a functional slot remains
(`semantic/rich_scientific.py:224–226`, `combinations(members, 2)`); the original finding
already accepted that as necessary work. I did not audit the successor for cumulative work,
and I did not check the 31 `.in_(` sites in `semantic/data_operation_projections.py` for
unbounded lists.

**DA-044.** Scientific representatives are a named policy, `min-fact-id-1`, carried with a
component identity (`semantic/rich_decisions.py:35–39`;
`semantic/rich_rule_evaluation.py:93–97, 923–930`). The display choice is a deterministic
minimum by value string, then id (`:873–889`). Its comment states it is a presentation choice
and not evidence that other spellings are absent. I did not trace where entity attributes take
their evidence in the successor.

**DA-045.** The legacy owners the finding named are gone. Layer inversions of the same kind
recur at new sites, all as lazy imports:
- `semantic/` imports `orchestrate/`: `semantic/data_operation_service.py:233–234`,
  `semantic/visual_requests.py:664`, `semantic/pdf_capture.py:195`,
  `semantic/pdf_transforms.py:804`;
- `methods/` imports `cli/`: `methods/characterization_resources.py:481–482, 759`;
- `core/` imports `methods/` and `semantic/`: `core/text_structure.py:212, 223` and
  `core/db/host_bootstrap.py:20–26` (a module-level import); `core/method.py:38–40` does so
  only under `TYPE_CHECKING`.

The "contracts living in the earlier model" half is now DA-072: `methods/llm/producer.py:7`
still takes `TaskUnitType` from `core.vocab`. The finding's raw-connection `Reader` defect
does not recur: `core/method.py` has no `Reader`. I searched `methods/` for `text("SELECT|…
kb.|ops.")` and found nothing; the search covered only that one pattern.

**DA-046.** `model/semantic/core.yaml:614–713` still declares `StatementKind` with theorem,
lemma, exercise and solution; it also declares `proves` (`:526`), `family_param` (`:265`),
`exemplified` (`:689`) and `example_value` (`:711`). The toy pack narrows its statement slot to
`ToyStatementKind`, but that enum `inherits: [StatementKind]`
(`domains/toy/semantic.yaml:36–39, 65–69` at `5139eaba3`), so the toy schema still offers
theorem and exercise. DESIGN §1.3 still says the core "holds nothing statistics-specific"
(`docs/design/DESIGN.md:74`). The boundary question stands. The duplicated closed sets are
DA-072.

**DA-047.** The cited examples are gone: `data.selected_fact`, `record_direction`, the schema
hash of `propose_claims`, and the empty `fuse`, which now has a real kernel at
`semantic/analytical_kernels.py:170`. The same cause recurs at two sites:
- *Authored SQL on the release path.* Archival, admission and retention consume dependencies
  named `authored-sql/…` (`semantic/authored_sql.py:299–369`;
  `semantic/native_admission_release.py:461–500`; `cli/model.py:361–385`). Nothing supplies
  them: `acquire_pack` reads no such files (`semantic/regeneration.py:60–130`), and a search of
  `src`, `scripts` and `domains` at `5139eaba3` finds the prefix only in its consumers.
  `admit_sql` does have a live consumer, the database-description endpoint, which analyses a
  submitted query without executing it (`serve/database_description.py:165–200`).
- *Proposal producer binding.* `methods/llm/producer.py` (`SUPPORTED_PRODUCERS`,
  `producer_binding`) and `methods/llm/agent_opus.py` (`AgentOpusConfig`; its docstring says
  "historical … interpretation only") have no importer in `src` or `tests`.

DA-080 does not list either site; a search of the audit pages for `authored`, `producer.py`
and `agent_opus` found none.

**DA-048.** Partly corrected. When several packs are composed, the domain rules are coalesced
at the root name and conflicts are refused (`semantic/regeneration.py:189–211, 255–265`), and
some consumers now accept pack-scoped names (`methods/model_observation.py:30–31`;
`semantic/interpretation_questions.py:244`). The original structural cause recurs for inputs
that are not shared:
- every other operation input is still renamed `pack/<name>/…` (`:220–237`);
- `operation/rich-analysis-context.json` is read only under its root name
  (`semantic/rich_policy_binding.py:12, 24`);
- its validity check runs only when that root name is present (`semantic/prepare.py:1406–1414`).

A composed release would therefore skip the check silently. This is inferred from source and
was not executed. In practice only single-pack preparation is exercised, and the statistics and
toy policies probably differ, so composition would be refused earlier.

**DA-049.** ADR-0047 (`docs/adr/0047-current-only-domain-runtime.md`) declares current-only
operation. Exact equality of compiler and library versions remains at
`semantic/releases.py:489–499`, and old model encodings are refused with an instruction to
regenerate (`semantic/data_operation_model.py:1211–1216`). The original "undeclared lifetime"
claim no longer holds; the behaviour is the declared limit.

**DA-050.** Reads bind an exact demand ("Exact target demand; no promoted/latest selection",
`cli/selected_results.py:23`) and continue through a pinned `resource_handle`
(`serve/demand_context.py:140`; `semantic/demand_queries.py:296`). I did not survey every
follow-up surface.

**DA-051.** Recognition declares its identity assurance (`trusted_managed_service` or
`provider_reported`) and admits a managed generation only when the artifact digests match
(`ingest/pdf_recognition.py:65–73, 152–171`). External results record `actor_assertion` and
`model_assertion` and check them natively (`semantic/external_receipts.py:24–25`;
`semantic/external_execution_native.py:266–267`). They are labelled as assertions, which is
honest attribution. Not traced end to end.

**DA-052.** No Python source names `agent.opus` except `methods/llm/producer.py:10`, which has
no importer. External execution uses declared packet and result operations. `domains/*/methods.yaml`
still hold an `agent.opus` configuration section (statistics `:70`, toy `:8`). I did not check
whether anything reads that section.

**DA-053.** Claims become owned by `ClaimOwner` immediately after the claim transaction commits
(`orchestrate/data_operations.py:1203–1208`). They are renewed by `maintained_claims` and
settled or retained through the owner (`:1237, 1255, 1341, 1378`;
`semantic/claim_lifetime.py:79–186, 255–406`). An inferred residual: input hydration runs
inside the claim transaction, after the 300-second lease starts and before renewal can begin
(`orchestrate/data_operations.py:1091–1208`). It is bounded by `max_packet_bytes`. It was not
shown to exceed the lease.

**DA-054.** The legacy key is gone. The same family of cause (a dependency granularity coarser
than the declared dependencies) is DA-078 for readiness and DA-069 for implementation identity.

**DA-055.** Header levels and separate note or unit attachments now get separate axes. Only
competing readings of the same level and role are exclusive
(`methods/table_interpretation.py:313–333`).

**DA-056.** The 2026-11-08 restatement at `0cab80335` (13:39) said an event could report zero
probability while a displayed assignment that satisfies it had positive mass. One hour later,
`f3f2d1ca5` ("Implement DMA-00 through DMA-04") added bounds checking each marginal and event
against the displayed support. At `5139eaba3` those bounds are at
`semantic/local_interpretation_reports.py:285–308`. They run on the bind path
`validate_local_interpretation_report` (`:361`), which `semantic/contributions.py:267–270`
calls and which `semantic/observations.py:374` reaches. The audit page was never updated, so
the "open on 2026-11-08" note at `witnessed-enrichment.md:18` is stale. The native counterpart
in `semantic/sql/source_contributions.sql` was deleted in `3812d31cf` (2026-11-16). No
generated native module checks event probabilities; a search found only fitting in
`operation_event_native.py`. Whether native admission still needs these checks was not
established.

**DA-057.** Member identity includes `definition_interpretation` and `applicability_outcome`
(`methods/structural_products.py:1235–1257`). Admission rederives it with the same fields
(`semantic/structural_admission.py:242–248`).

**DA-059, DA-060.** `OperationAccount` carries the acquired target, predecessor, reached
revision, known effects and the cleanup state (`cli/managed.py:63–96, 341–378`). A failure is
recorded with kind, code, message and reason (`:429–442`). Evidence promotion refuses unless
`custody_settled()` (`cli/operations.py:410–415`; `cli/managed.py:92–97`).

**DA-061.** `8dc0bac00` (2026-11-08, DMA-06/07) corrected both parts. The recipe now holds a
list of witnesses keyed by original digest and pointer, not by the integrated product digest
(`model/semantic/section-text-recipe.json`: two entries). The Reader resolves the recipe from
the retained release (`ingest/pdf_hierarchy.py:354–380, 382–427`). The production path still
refuses when the installed bytes differ (`:346–351`); that is a refusal, not suppression.

**DA-062.** The native codec is generated from the LinkML layout. It requires the
`name/position/value` contract, contiguous ordered positions and unique names
(`semantic/source_value_native.py:64–66, 241–335`).

**DA-063.** The expectation is selected by the acquired revision, or by body fingerprint for
restricted principals (`semantic/execution_admission.py:55–59, 120–170`). Deployment passes
`revision=actual` (`schema/model_deployment.py:843, 879`).

**DA-064.** A skip requires every cue to be negative, otherwise the result is `unassessed`
(`semantic/visual_routing.py:235–239`). A blank page requires verified original bytes
(`:228–232, 744–761`).

**DA-065.** `9e04d04d1` (2026-11-08, DMA-05) bound named and geometry bases to an exact
annotation witness and enforced it in three places: native admission
(`semantic/sql/structural_products.sql`), the detached replay
(`serve/model_observation_replay.py`) and `serve/review_bundle.py`. All three were removed:
the SQL in `200e396fc`, the other two in `ee940a5ef`. No production or test source still
contains the message "definition basis lacks exact retained annotation witness". The current
declared type allows `witness=None` for `matched_cue` and `native_geometry`, and only forbids a
witness on other bases (`semantic/structural_products.py:601–616, 950–967`). The producer still
attaches a witness on its main path (`semantic/definition_component_products.py:519–556`), but
treats "no witnesses supplied" as qualified (`methods/definition_applicability.py:466, 572`).
The cause (a basis claim not bound to its witness at admission) therefore recurs at these
sites. Not established: whether declared-operation admission, which attests producer
implementation identity, makes the original forged-component scenario unreachable.

**DA-066.** Selection by occurrence and cell, with `after`/`limit`, is pushed into the native
read (`semantic/visual_read_native.py:75–170`). The Reader charges only the returned rows
(`serve/pdf_visual_evidence.py:5–45`). I did not examine the cost of the native scan.

**DA-067.** The analysis compiles the captured physical sources. Its source identity includes
the recipe digests, the captured physical id, the LinkML types digest, the compiler and the
runtime (`semantic/projection_analysis_products.py:119–190`). It does not compare against an
installed profile.

## Counts by status (26 identities; DA-058 excluded)

Counted by hand from the table above.
- Corrected, correction holds: 15. DA-044, 049 (by decision), 051, 053, 055, 056, 057, 059,
  060, 061, 062, 063, 064, 066, 067.
- Changed footprint (DA-048 partly corrected): 5. DA-042, 045, 047, 048, 065.
- Stands: 1. DA-046.
- No longer applicable: 4. DA-041, 043, 050, 052.
- Superseded: 1. DA-054 (by DA-078, with DA-069).

## Identities whose cause recurs in current code

- **DA-042**: full release re-derivation at registration and basis sites
  (`semantic/data_operation_service.py:142, 182, 300`; `orchestrate/source_operation.py:144, 324`;
  `orchestrate/native_execution.py:41`; `orchestrate/project.py:106, 159`). Bears on DA-033 and
  DA-083.
- **DA-045**: upward imports from `semantic` to `orchestrate`
  (`semantic/data_operation_service.py:233–234`, `visual_requests.py:664`, `pdf_capture.py:195`,
  `pdf_transforms.py:804`), from `methods` to `cli` (`methods/characterization_resources.py:481–482, 759`)
  and from `core` to `methods`/`semantic` (`core/text_structure.py:212, 223`;
  `core/db/host_bootstrap.py:20–26`). The contract half is DA-072.
- **DA-046**: statistics and mathematical vocabulary in `model/semantic/core.yaml:265, 526, 614–713`,
  inherited by `domains/toy/semantic.yaml:65–66`.
- **DA-047**: authored-SQL release machinery with no supplier (`semantic/authored_sql.py:299–369`,
  `semantic/native_admission_release.py:461–500`, `cli/model.py:361–385`); an unimported
  producer binding and agent configuration (`methods/llm/producer.py`, `methods/llm/agent_opus.py`).
  Both are candidate additions to DA-080 (also DA-052).
- **DA-048**: pack-scoped renaming (`semantic/regeneration.py:220–237`) against root-name
  consumers and a conditional check (`semantic/rich_policy_binding.py:24`; `semantic/prepare.py:1406–1414`).
- **DA-065**: the basis witness is optional in `semantic/structural_products.py:613, 950–967`, and
  absence is treated as qualified in `methods/definition_applicability.py:466, 572`; the enforcement
  sites were retired in `ee940a5ef` and `200e396fc`.

## Not resolved, and limits

- **DA-065**: whether producer attestation under declared operations closes the forged-basis
  scenario. That needs a trace of the admission of definition components through
  `semantic/definition_admission_native.py` and the CPU input basis, which I did not do.
- **DA-056**: whether native admission of local interpretation reports exists anywhere after
  `3812d31cf`. I searched only for probability, marginal and event checks in `semantic/*native*.py`.
- **DA-043, DA-044**: the successor's cumulative work and entity-attribute attribution were
  sampled, not audited.
- The DMA plan (`docs/plans/domain-model-alignment_2026-11-08.md`) is absent from the snapshot
  and was not read. Correcting commits were identified from code history, not from that plan.

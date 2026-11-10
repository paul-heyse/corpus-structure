# Integrated domain-data-model capability series

**Status: DMC-00–06 complete with scoped acceptance; DMC-07–17 planned · 2026-11-10.**
This coordinator owns DMC-00–17, DMC-I01–09, source opportunity disposition, selected branch
delivery and combined qualification. Supporting plans own target explanations and package
contracts, not duplicate progress. Existing PTD, DMA, WCE and PM2 scopes remain with their owners.

## Basis, operator decisions and execution entry

Consume the [functional review](../functional_reviews/domain-data-model_2026-11-10.md) and
five companions at `55ca782e4`, its [discovery](../library_leverage/libraries/domain-data-model/briefing.md)
at `3eeded857`, and the relevant library references cited by the supporting plans.
Authoring inspected clean source `8e69e2b5f6dc56bd01c3a63b27b0a7ee28d313da`, 2026-11-10;
concurrent PTD-11 coordinator work is preserved and is not qualification of this series.
During authoring, `044915435` and `dfe77f5a3` added the assembled PTD audit/review and scoped
native reader acceptance. PTD owner/evidence/qualification updates continued concurrently.
These records refine the eventual handoff; this plan does not declare PTD-11 complete.

Operator decisions, 2026-11-10: author a new series covering the complete review, including
all conditional and additional capability directions; investigate those areas and implement
justified selected branches, recording retain/reject/defer outcomes with reasons and triggers.
Include useful foundation improvements revealed by deeper investigation. Execute **after
completed PTD-11 and its handoff, before returning to PM2**. PTD's completion obligations remain
PTD-owned; this plan neither waives them nor treats a prior tranche as the required handoff.
Plan authoring authorizes documentation only, not current product/database effects.

DMC-00 must acquire the completed PTD-11 source, native head/catalog, compiler/reader/runtime
versions, defaults, retained run/cut/source identities and remaining declared limits. Reconcile
the actual tree and relevant requirements before production changes. If PTD-11 is unfinished,
authoring and independent research can proceed; execution entry remains unavailable.

Use [D1](../design/D1-knowledge-representation.md), [D2](../design/D2-schema-and-guidelines.md),
[D3](../design/D3-database.md), [D5](../design/D5-consolidation-identity-confidence.md) and
[D8](../design/D8-agent-and-query-interfaces.md), with ADR-0024/0031/0063/0067/0069, as current
owners. Executable version owners and the acquired handoff take precedence over dated version
examples in architectural prose. Core3.3, heuristics1.0 and code-intelligence1.4 selected by
[standard.toml](../design_review/design_principles/standard.toml) guide this focused assessment;
test-assessment applies to selected verification. No broad audit was initiated by plan authoring.

## Combined target and foundation assessment

The developer/operator gains an explicit-release contract explorer, complete recipe reconstruction,
typed directional archive opening and repair-oriented diagnostics. A bounded terminology pack
adds inspectable vocabulary meaning, selected source-grounded correspondences, update explanations
and recognized measurement interpretations. Conditional graph, independent-consumer and process
capabilities enter only through the decision/delivery contracts below.

| Inspected foundation | Target consequence and rationale |
| --- | --- |
| Effective release definitions/index/adapters exist; normalized classes omit descriptions and declaration origins | Emit one immutable inspection artifact during preparation with module, logical declaration path, source digest and inherited contributors. It describes effective products; it cannot override their semantic meaning. Exact source lines are not promised. |
| Archives retain authenticated inputs, closed product shape and byte reconstruction | Scope typed cattrs wire reconstruction to archive3 where bytes/meaning stay identical. New byte-producing artifacts follow deliberate compiler/product versioning. Existing archives lacking detail report unavailable rather than run today's compiler. |
| Structural-product schemas already nest the relevant reports | Investigate local normalization, not new nested schemas. Retain source-value tags, closure validators and independent native protections. |
| Validation preserves original objects only transiently; compact managed failures and report digests are not raw-report custody | Default to direct bounded detail; use the existing managed artifact lifetime for selected later retrieval. Retain originals before wrappers flatten them; distinguish explanatory markers from resolvable references. |
| Vocabulary members retain value/meaning/label, and ordinary external grounding has no admitted mapping kinds | Add richer read metadata in an immutable artifact first. Select vocabulary/consumer together; external correspondence is distinct from corpus denotes and accepted identity. |
| Threshold quantity is a source symbol; textual units/basis already gate consequences | Add source-preserving unit/quantity interpretations without relabelling source fields. Conversion is a separate selected operation. |
| Qualified graphs and native inference already govern production | Preserve conformance/entailment distinctions, complete universes and witnesses. Conditional navigation/research compares current SQL/export with graph mechanisms. |

Workload: selected released model kinds, the authenticated scientific corpus and its retained
products, bounded operator/agent inspection and selected independent tooling. Preparation follows
immutable inputs and release lifetimes. Small contract reads must not hydrate unrelated data or
recompile whole releases. Useful detail is bounded by count, nesting and bytes; a page cursor does
not justify repeating full validation. Independent enforcement remains where it protects a real
boundary. Expected benefits are qualitative, not speed/memory/quality claims.

## Design owners and reading route

| Supporting plan | Owned target and packages |
| --- | --- |
| [Authoring/release products](domain-data-model/authoring-and-release-products.md) | DMC-01/02; effective inspection/provenance, shared source facts and CLI/MCP contract exploration |
| [Construction/archives](domain-data-model/construction-and-archives.md) | DMC-03/04/05; exact recipe, directional wire reconstruction and selected nested normalization |
| [Terminology/measurements](domain-data-model/terminology-and-measurements.md) | DMC-06–10; source/consumer choice, immutable metadata, inspection, mapping, update impact and unit interpretation |
| [Diagnostics/graphs](domain-data-model/diagnostics-and-graph-workflows.md) | DMC-11/12/14; correction detail, custody, supported paths/components and selected research views |
| [Independent consumers/configuration](domain-data-model/independent-consumers-and-configuration.md) | DMC-13/15/16; offline contracts and selected configuration/tooling branches |

Each explanation owns its pivotal mechanism, version/source references, limits and alternatives.
Dependent packages link to it instead of defining competing contracts. A package is not an agent
assignment. One writer integrates shared semantic products, report schemas and native migrations;
independent work may still contend for those files.

## Execution queue

DMC-00–06 delivery and scoped acceptance are recorded in the execution receipts below;
DMC-07–17 remain **planned**. This table and receipt are the current package-state owner. Investigations may finish during execution entry where source inspection
settles their question; no experiment quota applies.

| Package | Required input → delivered capability and completion boundary |
| --- | --- |
| <a id="DMC-00"></a>DMC-00 | Completed PTD-11 handoff → reconciled source/native baseline, consumer/required-scope inventory and due target-review route before substantial changes |
| <a id="DMC-01"></a>DMC-01 | DMC-00 + current effective products → immutable inspection/provenance artifact, versioned unavailable-old-detail behavior and archive integration |
| <a id="DMC-02"></a>DMC-02 | Working DMC-01 read slice → bounded release/class/property/operation explorer through CLI/MCP, with honest examples/support and shared readers |
| <a id="DMC-03"></a>DMC-03 | I02 recipe decision → class-scoped complete reconstruction preserving invariants, bytes/digest and strict presence; affected callers migrated |
| <a id="DMC-04"></a>DMC-04 | I02 archive decision + actual archive ABI → typed directional opening with exact historical/current shape, located wire errors and independent authenticity retained |
| <a id="DMC-05"></a>DMC-05 | I03 selected normalization decision → release-local nested boundary and consumers migrated; otherwise explicit retain outcome, no duplicate nested schema |
| <a id="DMC-06"></a>DMC-06 | I01 source/consumer decision + DMC-01 artifact conventions → richer immutable vocabulary metadata and operation-owned source preparation under explicit supported profile |
| <a id="DMC-07"></a>DMC-07 | Working DMC-06 → two useful controlled fields, inspection/filter consumer, labels/hierarchy/mapping/check-status fidelity and offline archived reads |
| <a id="DMC-08"></a>DMC-08 | I04 selected grounding decision + DMC-06 lookup slice → located term candidates with separate mapping kinds, unresolved alternatives and authentic source/vocabulary pins |
| <a id="DMC-09"></a>DMC-09 | DMC-06/07 metadata + current semantic-diff owner → membership/meaning/label/mapping update explanation with known consumer scope and explicit unknowns |
| <a id="DMC-10"></a>DMC-10 | I01 measurement consumer + I05 → recognized unit/quantity interpretations and grouping/compatibility read; selected conversion/classification separately delivered |
| <a id="DMC-11"></a>DMC-11 | DMC-00 + current report/managed-result owners → bounded original-engine correction detail, typed reference/custody semantics and selected direct/retained CLI/MCP consumers |
| <a id="DMC-12"></a>DMC-12 | I06 selected navigation/component decision → supported paths or recurring constraints preserving qualified occurrences/universe, with readers and diagnostics integrated |
| <a id="DMC-13"></a>DMC-13 | I07 selected independent consumer + required DMC-01/11 contract slice → self-contained offline contract closure and real independent consumption |
| <a id="DMC-14"></a>DMC-14 | I06 selected graph-research question → bounded attributed exploratory view/comparison; current production inference/conformance retained |
| <a id="DMC-15"></a>DMC-15 | I08 selected acquisition/explanation decision → actual-instance source report/consumer change, masking and snapshot semantics preserved |
| <a id="DMC-16"></a>DMC-16 | I07/I09 selected tooling branches → each explicitly selected generator/transform/codec/provisional workflow and its complete consumer migration |
| <a id="DMC-17"></a>DMC-17 | All decisions and selected delivery complete → final-source qualification, native adoption where selected, assembled target review, durable owner updates and PM2 return handoff |

DMC-03/04 and early diagnostic work need not wait for all explorer functionality. DMC-06 needs
the shared artifact convention, not completed UI. Grounding/change impact need vocabulary lookup
or metadata slices, not every terminology consumer. Navigation may serve terminology or corpus
relationships without research entailment. Independent contracts package only their selected
consumer closure. DMC-16 is not a late consumer-completion bucket: consumers migrate with their
owning selected behavior. Native versioned effects serialize through their actual owner.

## Investigation contracts

Every branch receives a decision: implement with defined consumer/delivery checks, retain with
reason, reject on corrected premises, or defer with a specific unmet premise and revisit trigger.
I02/I03 are resolved; I01 has a selected source/field slice and remaining consumer/measurement
work. I04–09 remain open. Decisions and supporting evidence live in the owning companion;
this coordinator records their current disposition and selected package scope. A source/doc read
may suffice; an unresolved pivotal library behavior can justify a bounded probe.

| ID | Question and sufficient decision output | Dependent delivery |
| --- | --- | --- |
| <a id="DMC-I01"></a>DMC-I01 | Select scientific terminology source/revision/format, two useful fields and actual source-grounded measurement/inspection consumers. Resolve metadata versus enforced semantics, import closure, missing/obsolete terms and corpus applicability. Deliver named inputs and acceptance examples, not a test-only toy standing in for use | 06/07/10 |
| <a id="DMC-I02"></a>DMC-I02 | **Resolved, selected/retained mechanisms in the DMC-03–06 receipt.** Settle strict recipe annotation/constructor/subclass behavior and cattrs required/default/hex/byte reconstruction. Separately decide whether replacing publication JSON conversion removes useful work without changing accepted inputs/nonfinite/key semantics | 03/04 |
| <a id="DMC-I03"></a>DMC-I03 | **Resolved, subtree normalization selected and delivered.** Choose a credible nested-product extension; compare targeted loops with prepared subtree normalization under explicit release. Preserve source tags/variant/citation closure; select only a materially simpler complete route | 05 |
| <a id="DMC-I04"></a>DMC-I04 | Compare read-only terminology lookup, separate candidate product and explicit contextual-contract extension. Qualify field/case/offset/all-occurrence behavior before relying on OAK search/annotation; consider similarity only with declared ranking premises | 08 |
| <a id="DMC-I05"></a>DMC-I05 | Decide identification versus physical/contextual compatibility, numerical classification and actual conversion. Select established engine only for a named comparison, including basis/precision/affine/context obligations; no executable annotation strings | 10 |
| <a id="DMC-I06"></a>DMC-I06 | Select useful navigation/repeated invariant and research comparison questions. Compare indexed/native SQL, supported RDFLib paths/queries/compare, Core/SPARQL components, then SHACL-AF/OWL-RL/Datalog only for their actual semantics. Decide each family including stores/remote/patch/visualization with reasons | 12/14 |
| <a id="DMC-I07"></a>DMC-I07 | Choose independent offline/schema/SDK/cross-language consumer; compare existing derive/export with closed selected resources. Assess docs/renderer/JS/API/grammar/data-entry/Rust/PyO3/Map/YARRRML/spreadsheet routes against complete fidelity and actual activity | 13/16 |
| <a id="DMC-I08"></a>DMC-I08 | Establish whether deeper aliases/nesting/instance policy makes current config explanation insufficient. Assess source wrappers, files/secrets/cloud, CLI integration, reload/async/cache separately; retain two-source entry-point snapshot unless selected need warrants change | 15 |
| <a id="DMC-I09"></a>DMC-I09 | Evaluate concrete codec/object-lifecycle/provisional-preview/ETL/authoring workflows and generic Store/Automator alternatives. Name the maintained responsibility removed, preserve raw/completeness/admission semantics; assess domain-specific enrichment/federation/taxon/plugin directions for actual fit | 16 or other owning selected slice |

An investigation cannot close as merely “not investigated/no caller.” Develop the credible use
and assess its total burden; a reasoned lack of sufficient value is a valid outcome. Do not
implement every alternative or create a permanent capability registry. Selected branches enter
the owning target and this table before implementation, and add their required evidence union.

## Source disposition and complete correspondence

Rows preserve functional opportunity identities, not new defect IDs. O02/O03/O04 are complete
at their selected scope; O01 core inspection is delivered with conditional I07/I09 branches open;
O05 foundation is delivered with DMC-07 pending. Other rows remain open through their stated routes.

| Source review item | Responsible boundary and closure route |
| --- | --- |
| O01 / DDM-01/02 | Release/compiler/read owners → DMC-01/02; origin/effective/enforcement distinction, faithful source/operation lookup |
| O02 / DDM-03/13 | **Complete, DMC-03–06 receipt.** Recipe owner → I02/03; complete strict archived reconstruction, exact identity and callers |
| O03 / DDM-04 | **Complete, typed reconstruction delivered; publication conversion retained.** Archive owner → I02/04; directional typed wire, byte parity, authenticity; publication conversion separately decided |
| O04 / DDM-14 | **Complete, selected DMC-05 subtree normalization.** Structural observation owner → I03/05; existing nested schemas preserved, selected normalization or retain conclusion |
| O05 / DDM-05/11 | Vocabulary preparation/read owners → I01/06/07; useful terms/fields, retained meaning/provenance and shared scoped preparation |
| O06 / DDM-06 candidate branch | Candidate/selection owners → I04/08; external mapping never relabelled source support/identity |
| O07 / DDM-06 lifecycle branch | Semantic-diff owner →06/09; exact membership/metadata change, consumer coverage and old meaning retained |
| O08 / DDM-12 | Measurement owner → I01/I05/10; source/recognized/basis distinction; conversion/classification selected separately |
| O09 / DDM-08/09 errors | Report/error/custody owners →11; original errors/detail retained safely, direct versus resolvable reference and complete/partial/unavailable honest |
| O10 / DDM-02/07 | Relationship/projection owners → I06/12; admitted path grammar, identity/multiplicity/reference closure |
| O11 / DDM-03/09 resources | Independent consumer owner → I07/13; actual offline validation, explicit dialect/resource closure and limitations |
| O12 / DDM-10 | Process settings owner → I08/15; actual snapshot/report use or justified retain outcome |
| O13 / additional graph families | Research-view owner → I06/14; declared semantics/premises/universe and existing production ownership |

The source review's 21 additional-territory rows are consumed in full, with these branch routes:

| Additional territory (source order retained) | Decision/delivery route |
| --- | --- |
| 1 LinkML arrays/extras/logical slots/keys/conditional rules | I03/I06/I07 →01/05/12; actual consumer profile before lowering |
| 2 Documentation/annotator/API/renderer/JS/grammar/scaffolding | I07 →02/13/16 |
| 3 Rust/PyO3/language generation | I07 →13/16; independent structural versus executable fidelity |
| 4 Map/YARRRML/flattening/spreadsheets/ETL | I07/I09 →13/16; complete direction, presence/order/precision/lineage |
| 5 Store/Automator/workflow/storage alternatives | I09; chosen bounded authoring route or retain current custody |
| 6 Pydantic aliases/serializers/domain types/errors/core hooks | I02/I03 →03/04/05/11; public high-level composition first |
| 7 Partial/lazy/tolerant parsing/omission/fail-fast | I09 →16; provisional raw custody distinct from complete admission |
| 8 msgspec/binary/raw buffers, attrs lifecycle, cattrs delegation | I02/I09 →04/16; whole responsibility and hook/invariant fidelity |
| 9 OAK grounding/mappings/similarity/associations/enrichment | I04/I09 →08/16; explicit relation and evidence role |
| 10 OAK usages/obsoletion/KGCL and Valuesets maintenance | I01/I04 →09; exact product comparison and source coverage |
| 11 OAK federation/native OWL/subsetting/taxon/plugins/LLM/visualization | I06/I09 →14/16 or reasoned retain/defer |
| 12 Valuesets metadata/hierarchy/dynamic enum/slot/mixin sources | I01 →06/07; draft fit, selected source semantics |
| 13 Numeric classification/unit sources/SSSOM confidence | I01/I05 →07/10; no silent exclusivity/equivalence |
| 14 RDF names/collections/Describer/infixowl/compare | I06/I07 →02/07/12/14 |
| 15 Prepared SPARQL/CONSTRUCT/algebra/NetworkX/traversal | I06 →12/14; optimizer placement and sufficient universe |
| 16 Core/Meta-SHACL/focus/shape selection/components | I06 →11/12; selection not proof of complete closure |
| 17 SHACL rules/functions/JS/OWL-RL/Datalog | I06 →14 only if selected semantics; production conformance unchanged by default |
| 18 RDF stores/remote/events/patch/JSON-LD/HTML/server | I06/I07/I09 →13/14/16; no automatic second authority |
| 19 JSON dialects/dynamic refs/resources/unevaluated regions/extensions/formats | I07 →13; finite offline consumer profile and explicit unsupported semantics |
| 20 Generated property inputs/hypothesis-jsonschema | I02/I07 verification support; retain independent known-invalid/known-answer controls |
| 21 Settings files/cloud/default/CLI/reload/async/cache | I08 →15; explicit actual acquisition and lifecycle decision |

Inline corrections and alternatives also remain obligations: O04 already has nested schemas;
graph bytes are transient unless explicitly retained; unit symbols are not quantity kinds;
ontology search/annotation has field/case/offset limitations; RichEnum is lossy; subtraction
follows complete enum union; graph paths have a supported grammar; existing derive/export,
native inference and config snapshots are adopted foundations, not missing features.

## Rule changes, transition and acceptance

No change to §B authority, graph entailment/conformance mode, publication authority, settings
source policy or archive identity is selected merely by this plan. Adding metadata/display
within existing contracts is distinct from adding enforced semantics. If a branch requires a
real recorded-rule change, present the exact rule/owner, target, benefit, consequence and
conforming alternative for explicit accept/reject before fixing its dependent design. Record
the dated decision and ADR/owner route here. Do not treat an implementation allowlist as
automatically equivalent to an immutable architectural prohibition, or hypothetical impacts
as blanket permission requests. No numbered RC list was supplied by the source review.

Preserve source custody and frozen original artifacts; evolve current generated products and
required native projections through the normal forward model-change route. Consumer migration
and superseded code/config/mechanism-test retirement belong with the replacement. Historical
reads report unavailable newly introduced detail honestly; they do not fetch today's ontology,
rederive with today's compiler or invent earlier provenance. Archive shape changes require
explicit version handling; internal exact-shape reconstruction does not.

At execution entry schedule the binding's target review before substantial new boundaries and
one assembled target review at DMC-17, using its applicable prerequisites. This focused authoring
assessment is not a substitute. No recommendation/completion audit is added automatically.

During implementation use compile checks and `uv run ci test -- PATH` for actual affected
behavior. At complete selected functional scope run `uv run ci test` and `uv run ci check`, with
required native/provider/nonfunctional union declared by actual selected behavior and source/context.
Keep blocked required obligations open and original failed/interrupted records. A passing
round trip does not replace independent expected semantics for identity, mapping, source values
or diagnostics. No benchmark or quantified gain is required absent a serious decision-relevant risk.

DMC-17 requires all investigation branches decided, selected consumers delivered, dependent native
versions deployed/admitted if selected, source/release/runtime pinning verified, old paths retired,
required evidence accounted for and enduring design changes moved to their owners. Return to PM2
with the acquired successor baseline and remaining declared limitations. A decision or authored
ADR is not implementation; package completion is not whole-series qualification.

Plan-authoring product tests/native probes/benchmarks: **not_run**; no production effects were
performed. Documentation checks are recorded in STATUS with actual commands/outcomes.

## DMC-00–02 execution receipt · 2026-11-10

DMC-00 acquired completed PTD-11 at source `7e30c5d167`. Maintenance database observation
`uv run ci db status --maintenance --json` passed: `corpus_structure_dev`, PostgreSQL18.6,
`semantic_ptd_completion_repairs`, dedicated socket port5434, purpose maintenance/principal paul.
PTD handoff retains compiler19/execution28/boundary12 and its exact source/runtime/release pins;
run487/cut604, `/10` and the unselected project posture remain preserved. The
[entry target review](../design_review/reviews/design_review_domain-data-model-entry_2026-11-10.md)
and ADR-0075 govern the new boundaries. This receipt owns current package disposition.

DMC-00: complete; entry target review accepted scoped with no blocking finding or rule impact.
DMC-01/02: implemented and scoped acceptance complete; final evidence is below.
The operator selected newly archived development release demonstration and exact admission where
required, without activation or run selection. Named-type pattern plus inherited slot bounds
replaces the unsupported named-type numeric-bound acceptance example; the profile is unchanged.
Full-series qualification remains DMC-17-owned.

The native archive guard also enumerates compiler compatibility in `closure.sql`. The installed
PTD guard accepts through19, so compiler20 requires a forward `sem.require_archive_bytes(text)`
body update and its regenerated descriptor. The frozen candidate has exactly those two native
changes and no ordinary relational operations. Archive/boundary semantics remain unchanged.
The initial explicit-recreation request was refused (result `49780e78a3634fd9bec618add7f24f55`);
ordinary forward source comparison supplies the correct two-change candidate. The replacement
preview `92646e5f8149439cbd618190d3920da1`, apply `763ceda0c5924074b14caacccd20ccc5`, candidate
`6beabe05855246af82e180a3e71252a1` and registration `f504f781efb84be590ed4c0091d2fc0a` passed.
Candidate contract inspection passed before database archival, demonstrating detached custody.

Existing review-bundle contract fields already consume PreparedRelease definitions and selected
boundary schemas. Their detached format is retained; the explorer does not require exporting
its entire provenance artifact. Operation explanations remain in their existing owner.

Failed/intermediate receipts remain available: `a3c0e3d9115c40b29e5d3ead45810254` (fixture type),
`6f718dda5930438887b2ad1d762cee94`, `ccec61edf4584644a7edbf194110e00e`,
`9d9982eb7fd54cccad07135b47c4ca27`, and integrated `01e422f544a449fea8d8736f58dc99f1`
(174 selected,148 passed,26 failed:25 installed native compiler-allowlist refusals and one
managed-test settlement fixture). The fixture is repaired; registered migration qualification
must replace the affected native failures. Additional development test receipts from workers
retain their original bounded source applicability and do not close combined qualification.

The first deploy `2314363a4986466bb4dd668197344129` established migration
`semantic_dmc_inspection` but refused archive/admission at the separate producing-compiler
execution-projection guard. Its known migration effect and failed receipt are preserved.
The forward correction changes `sem.require_execution_projection(text)` from compiler19 to20
and regenerates its descriptor; it does not rewrite the deployed migration. Replacement preview
`9fcb2b3baf534147b2d309fc5ec9c292`, apply `a824b0f6a242486689e1f2cebf66c9e9`, candidate
`53d8c6b524a2466a877282680549185d`, registration `6d8edda51aef419488db2943ecc0e372` passed.
The intermediate retry `1d7a6215b70b4f40a2f456620e70dfb0` passed the managed-capsule fixture
and retained25 producing-compiler native refusals before this second migration existed.
The final grouped affected selection against the registered source supersedes that context.

Live old-archive inspection passed for PTD's compiler19 release: `Formula.language` remains
required, with explicit unavailable authoring detail. This uses archived products, without
backfilling today's source provenance. Types, lint, docs and `ci model check` passed at their
recorded intermediate source; final checks remain due after handoff edits.

Native deployment `8791940484e64d9ab4162e94d7f17a19` passed migration/archive/admission/verified
at `semantic_dmc_compiler20`. Release `release:4b5fd49b3879d7628e80a5feb78607b3cdc327ce223e37a5827f517f44d822f3`
uses execution `execution:7bf8d8d78f16df38f1454ed81b5ce64e9ad4d3ab72de2f3226a36266b996754c`
and artifact-set `226906703a28a535f8304ea70a62802aabb74dcbedffb9a8b933d3b622c18ec2`.
`uv run ci db check --release RELEASE --json`, `uv run ci release check --release RELEASE --json`,
maintenance status and the [actual CLI/MCP journey](../design_review/evidence/2026-11-10_dmc-contract-inspection/README.md)
passed on2026-11-10. The journey also excludes converter/GLiNER imports. Project selection/defaults
and original source custody remain unchanged.

Expanded affected campaign `8976b4b19cfb4f0aa7bd004ab188db4c` selected232 IDs, passed230 and
retained two setup failures. Exact retry `9c6113768e5c4129b9c8a842e80c312f` passed both with
real native contexts. Collection-only inspection identified an installed pytest9.1.1 ordering
limitation: semantic file selections followed by a parent-directory CLI file and then more semantic
files can lose the nested semantic fixture definitions. Group semantic files contiguously before
parent CLI files; the ordinary whole-tree route does not interleave those explicit file arguments.
No production model failure was found in those cases. The original failure receipts are held.

That investigation exposed a CLI reporting defect: string pytest longreprs were reduced to a
trailing source location. `scripts/test_receipts.py` now preserves exception lines while excluding
fixture inventories; two independent regression cases cover fixture/collection/fallback detail.
`uv run ci test --json -- tests/scripts/test_test_receipts.py python/corpus-structure/tests/test_cli_test_evidence.py`
passed 108 (`9124043b15e944aa80bd59f330aba115`). This diagnostic-only change does not alter
semantic test behavior or native bindings. The grouped full affected rerun passed all 232 selected identities, as recorded below.

### Scoped completion and successor handoff

**Implemented; scoped Tested, 2026-11-10. DMC-00, DMC-01 and DMC-02 complete.**
The accepted entry review and ADR-0075, immutable artifact/archive reader, shared report and
both transports, bounded skeleton/input validation and frozen candidate authoring loop are delivered.
Known contributors preserve unresolved precedence rather than becoming another enforcement model.
Compiler20 is producing;14–19 remain readable; archive3/boundary12/execution28 are unchanged.

Final grouped `uv run ci test --json -- PATH...` passed **232/232**, held result
`a772719b2d8544219c427786fd27e948`. The declared required selection is the three new inspection
modules plus prepare, archive reader/wire, release/compatibility/publication, operation reporting,
published reports, review-bundle and model-inspect consumers. All semantic file selections precede
the parent CLI selection. This covers all affected identities, including the two earlier fixture
setup failures, with real native-required outcomes at `semantic_dmc_compiler20`. There is no
unresolved identity in this selected scope. The original failed campaigns remain held as failures.

The diagnostic repair's separate108-test selection passed in held result
`9124043b15e944aa80bd59f330aba115`; formatting preserved its behavior. Final types/lint,
`uv run ci model check --json`, `uv run ci docs check` and root `just turn-end` passed at this
tranche endpoint. The final test tree contains the registered compiler20 migrations and diagnostic
fix; later handoff edits affect prose only. No dependency/toolchain change, Rust behavior, provider
run or benchmark is selected. Whole-series qualification and assembled target review remain
DMC-17 obligations, not claims made by this scoped completion.

DMC-03–17 and all conditional investigation contracts retain their planned states. O01's core
inspection delivery is complete; additional authoring/generator branches remain with I07/I09 as
already scheduled. DMC-04's typed directional/archive work and DMC-11's retained diagnostic custody
were not pulled into these packages. Next is I02/DMC-03–04 at the construction/archive owner;
PM2 stays suspended until the selected DMC series handoff.

## DMC-03–06 execution receipt · 2026-11-10

Baseline403822dfb was clean; development acquired `semantic_dmc_compiler20`. The
[scoped target review](../design_review/reviews/design_review_domain-data-model-construction-terminology_2026-11-10.md)
accepts the selected boundaries at Proposed strength, with no blocking finding or rule impact.
ADR-0076 and D2/D8/§B5 own terminology projection/metadata authority. Final scoped completion is below.

I02 resolved: keep exact archived recipe presence plus actual-class cached TypeAdapter. The
single-parse BeforeValidator candidate loses strict JSON tuple behavior on Pydantic2.14.1.
Operator selected preservation of accepted NaN/positive-infinity/integer timeout behavior.
Directional archive3 root/rows use scoped cattrs, independent authentication and exact writer
omission rules. Publication JSON conversion is retained, including nonfinite refusal/key behavior.
I03 selects one structural-subtree JSON bridge through the released property adapter; handwritten
closure and comparison SourceValue semantic checks remain independent.

I01 source/field slice selects STATO v2026-04-20 at commit a5910e6115217a88ee86e2666e12983ef2ef2a42.
The qualified projection retains original OWL, converted OBO, converter identity/warnings and
selected RDF metadata; no full OWL equivalence or checked source binding is claimed. Fields are
optional independent distribution_family and distribution_attribute, distinct from global identity,
parameterization, sample statistics and MeasurementValueRoleName. Populated filtering/grounding
and measurement source/consumer work remain DMC-07/08/10 and the remaining I01 slice.

The new metadata/locator products require compiler21;20 remains readable. Archive3, boundary12
and execution28 remain unchanged. Both native compiler guards move together through the normal
frozen candidate route. Pronto2.7.4 is now a direct dependency without changing its resolved version;
lock changes are limited to the direct declarations. `uv run ci doctor --json` passed.

Source conversion qualification corrected the planning observation: two dumps in one process
were identical, but independent processes produced different clause/frame order. Acquisition
therefore canonicalizes the OBO AST through pinned Fastobo0.14.2 and verifies semantic clause
sets and selected original RDF facts independently. The qualified OBO digest is
`2e4438fb7246e7dc53a90fa04d79eda423b4906910c101608614e4289d9c6581`; the original OWL digest
remains `7e8f945ee30c6b24139f0064d57c2edbcfc988f3f74811cad6b5c84819ce1494`.
Fastobo is declared directly at its existing resolved version; no dependency was upgraded.

Pure construction/archive/capsule/locator selection passed43 in managed result
`f888af1d985a43e48d73a573a234c04e`; prior recipe/subtree46 and finalrecipe15 receipts remain
bounded worker evidence. Integrated scope and native handoff are recorded below.


### Scoped completion and successor handoff

**Implemented; scoped Tested, 2026-11-10. DMC-03, DMC-04, DMC-05 and DMC-06 complete.**
Complete actual-class recipe reconstruction preserves constructor/default/archive distinctions,
strict tuple handling, accepted timeout values and canonical identity. The typed directional
archive3 root/rows now share read/write mapping and located diagnostics while authentication,
exact historical/current bytes and publication conversion remain independent. Structural binding
uses the released subtree adapter and retains handwritten closure and SourceValue semantics.
Superseded representation-specific retrieval/contribution traversal is removed.

STATO acquisition, original OWL qualification, deterministic OBO projection, shared operation-owned
OAK preparation, two optional controlled field declarations, immutable rich metadata and enum/PV
locators are delivered. Ordinary archived and candidate inspection consumes retained products.
Known contributors do not claim an inferred unique winner; unsupported ontology semantics,
unchecked facts and unavailable historical detail stay explicit. O05's populated source-record
inspection/filtering remains DMC-07; located external-term review is DMC-08 and measurement
recognition/compatibility is DMC-10. I01 is only partially resolved by this foundation.

Forward preview `0bd5580f5a414d4baeca9d38c47656d1`, apply
`7299c781a82541cda8b49efacb860407`, candidate `b0c20388a4174c49842c289804a7a667`,
registration `68933185e70a4ae89a11ec4ea1cc0657` and deployment
`b83986b697504bbb845009fd795407cf` passed. The candidate contains exactly three function-body
changes: both native compiler guards and `data.execution_contract_descriptor()`. Owners/ACLs
are unchanged; there are no ordinary relational operations. The dedicated development database
now runs `semantic_dmc_terminology`; migration, archive, admission and verified reader stages passed.

- Release: `release:61d19b6ff98f69e0b0363500ff1b9867ecb044dc912e71d87bcbb5f643a01c72`.
- Execution: `execution:95216c8a88030e4674446ef58f8a4d2e9354c516b5a378c6c83eb3a79e159904`.
- Artifact-set: `441bf231af2cd0ef2adb0c7367091345759aca94300c19f38c20d42e5c1d42f6`.
- Physical: `physical:89a7c561254db10003b43437832e1188e02ccfebe68e00913b1f40e6fbce7e52`.

`uv run ci db status --maintenance --json`, `uv run ci db check --release RELEASE --json`
and `uv run ci release check --release RELEASE --json` passed. The
[live acceptance](../design_review/evidence/2026-11-10_dmc-construction-terminology/README.md)
passed explicit variance definition/meaning and enum/PV origin checks, CLI/MCP/frozen-candidate
equality, valid/invalid controlled-field validation and compiler20 archive reading. Its record is
`dmc.terminology-native-inspection`. Ordinary opening does not acquire current ontology sources.
No activation or run selection occurred; `/10`, run487/cut604 and original source pins remain preserved.

The declared affected union is the construction/archive/locator/terminology modules and their
prepare, release, reporting, structural observation, worker and CLI consumers, plus pack acquisition,
execution contracts/projection, native reporting and retained regeneration. Grouped semantic files
precede ingest/parent CLI selections to avoid the known installed pytest fixture-order limitation.
Main campaign `5e48ca24388548d58723428d228af46c` passed **346 selected identities**, with real native
contexts. Adjacent campaign `9b5824e481b64535a08fd17fd0ceaba6` selected 80 and passed 79; the sole
failure was an overbroad test prohibition on every post-acquisition `Path.read_bytes` call, now
reached by the existing temporary ontology bridge. Focused reproduction `5bbb011920af46b5a635ac68b8925f7f`
retains the same failure. The corrected test permits only exact paths written during the operation
from acquired ontology bytes, still refuses ambient source reads, prohibits component compilation
and compares repeated composition. Independent source review confirmed the captured-input contract.
Original failures remain held. Exact retry `784c5f2ff29a49c2b0310da9fae10dc4` supplies the affected
replacement; final coverage accounting follows below.

Earlier terminology campaign `52f94fceda9940c69810e2bab5840566` passed 41 of 42 with one fixture
using incompatible statistics/toy operation policies. A compatible explicit shared policy corrects
the multi-pack fixture while production conflicting-policy refusal stays intact; exact retry
`e7f00be0b6f44832bde7f8d99d3b2a26` passed, and the final346 campaign includes that corrected case.
No production behavior changed after its registration/deployment: subsequent edits affect test
fixtures, evidence and owner prose. The registered native migration is present in the final tests.

Pronto2.7.4 and Fastobo0.14.2 are direct exact dependencies at their already-resolved versions.
`uv run ci doctor --json`, `uv run ci check --only deps --json`, types/lint and
`uv run ci model check --json` passed. Final docs/maintenance checks and retry coverage are recorded
at the endpoint below. Rust, external inference providers, fault-lane changes and benchmarks are
not selected by this tranche. Whole-series functional/provider/nonfunctional qualification and
assembled review remain DMC-17-owned. Expected preparation reuse/simplification is qualitative;
no quantitative performance or scientific-fidelity benefit is claimed.


Final source/context account: the main 346 identity coverage is complete, with 29 native-required
identities and zero native unresolved. The adjacent 80 identity coverage is complete after its
one-node retry, with 17 native-required identities and zero native unresolved. `ci test coverage`
retains the original adjacent attempt's failed status while reporting all 80 nodes covered, no
unresolved nodes and no missing lanes. `sources_differ=true` is accounted for: only the selected
acquisition test guard and owner/evidence prose changed; production modules, frozen migration bytes,
Python3.14.10, library versions and native target remain identical. Formatting only wrapped that
test's comprehension. The accepted scoped union is **426 identities**, all covered by applicable
passes, including 46 native-required identities. The coverage delivery is not itself an automatic
whole-series qualification. DMC-07–17 and the remaining I01/I04–09 obligations stay open.


Final endpoint, 2026-11-10: `uv run ci check --only types --json`,
`uv run ci check --only lint --json`, `uv run ci check --only deps --json`,
`uv run ci model check --json` and `uv run ci docs check` passed. Publication checked 825 canonical
pages and 73 ADRs with no broken links. `uv run ci evidence finalize` and `uv run ci evidence index`
passed; `uv run ci evidence check --json` passed with zero errors and 41 inherited warnings outside
this record. Root `just turn-end` completes maintenance; it introduces no functional-source change.
The current native/release identifiers above and the held managed selection/retry receipts are the
successor baseline for DMC-07. Whole-series qualification remains explicitly `not_run` until DMC-17.

# Design principle audit

The living diagnostic account maintained by the
[audit skill](../../../.claude/skills/design-principle-audit/SKILL.md). The
[repository binding](../design_principles/binding/corpus-structure.md#design-principle-audit)
owns freshness and disposition. This account diagnoses current design; reviews own solution
reasoning, and implementation plans own scheduled work and closure evidence. It certifies
nothing and authorizes no change.

<a id="baseline"></a>

## Baseline

| Item | Inspected state |
|---|---|
| Date | 2026-11-17 |
| Audited source | `fbd3f2a98362da44d9c9bdb9f59bab1ff305bd36`, committed `main`, clean tree. Contributors read a frozen export of that commit, so cited lines are exact for it. The operator stated during the audit that production edits were in progress; later source is outside this refresh |
| Excluded | The untracked `docs/libraries/analytical_infrastructure/cachetools.md` (read as a library overview, not audited); the migration trees beyond their shape; Chandra OCR as scheduled work |
| Standard | Core 3.3; efficient-architecture heuristics 1.0; code-intelligence 1.4; repository binding. Test-assessment 1.2 applies through the test account |
| Previous broad baseline | `67cbe680e` (2026-11-08), about 2,000 commits earlier, followed by ten scoped refreshes to 2026-11-12. All of that text is in Git at `fbd3f2a98` |
| Kind | Broad refresh by static source reading. No test, database command, provider call or benchmark was run |
| Emphasis (operator, 2026-11-17) | The comprehensive domain data model, and efficiency of execution, assessed together with the [test account](../test-audit/README.md) at the same commit |
| Publication | The commit that publishes this account, distinct from the audited source |

This refresh replaces the stacked scoped entries of the earlier README with one current
account. It was needed because the declared-data-operations work replaced most of the code
those entries described: since the 2026-11-12 entry, 364 production files were added, 149
deleted and 307 modified, and the owners cited by the earlier domain model map were removed on
2026-11-16.

Observations are **Interface-checked by source inspection** on 2026-11-17 unless a row says
"not re-examined", in which case the last evidence keeps its original date. Nothing here is
labelled Tested or Measured.

## Scope and method

The functional target is unchanged: progressively enriched, attributed source knowledge under
an executable domain release, delivered through typed interfaces to one operator and to agents
on one host. The development workload is one 518-page book. Agents reach the system through
the `ci` CLI, which runs one process per command, and through a long-lived MCP server.

Five read-only contributors each read one area against a shared set of ten questions: four on
the domain model (what is declared, what is restated by hand, where scope is decided without
the declared dependencies, whether each identity is complete for what it keys), four on
execution (what repeats while its inputs are unchanged, what is examined in whole where a
subset is known, the facts of every cache and prepared holder, where assurance is re-proved or
dropped), and two on where they meet (which model facts could key or invalidate work, and
which caches key on something the model does not govern).

| Area | Read |
|---|---|
| Model declaration and compilation | Model owners, the compiler and effective model, wire generation, static preparation, release preparation |
| Dependency, validity, reuse, change impact | Change impact, projections, the demand planner, established validity, demand results, the validity and closure SQL |
| Execution host and method runtime | The process host and executor, CPU execution, native model hosts, math and construction grammars, PDF capture and recognition |
| Native storage, admission, publication | Storage, ports, admission, installation, PDF publication and reading, the admission and binding SQL |
| Serving, evaluation, CLI | The query cache and its six consumers, query custody, the archive reader, reporting, scientific evidence, the MCP servers, CLI entry |

The coordinator read the decisive source behind each published finding, checked stored test
results where a finding claimed a test could not pass, and reconciled candidates by structural
cause across both accounts. A fresh reviewer then challenged the draft against source before
publication; its effect is recorded under [Independent challenge](#independent-challenge).

## How the foundations were assessed

- **FP-04 / A2, domain model and semantic authority (priority).** By mapping where each kind of
  fact is declared, compiled and realized ([domain model map](domain-model-map.md)), then
  looking for the same meaning held twice and for decisions taken without the declaration.
  Findings: [DA-070](semantic-model-and-authority.md#da-070),
  [DA-071](semantic-model-and-authority.md#da-071),
  [DA-072](semantic-model-and-authority.md#da-072),
  [DA-073](semantic-model-and-authority.md#da-073), [DA-074](native-integrity.md#da-074),
  [DA-076](served-claims.md#da-076), [DA-077](served-claims.md#da-077).
- **FP-07 / A4, execution fit (priority).** By following what a change invalidates and what a
  repeated request recomputes, using H5 (smallest sufficient scope), H12 (stable preparation
  kept apart from changing values), H13 (identity matched to what varies), H18 and H19
  (assurance placed once and carried while its premises hold) and H21 (shared capacity).
  Findings: [DA-068](execution-fit.md#da-068), [DA-069](execution-fit.md#da-069),
  [DA-075](execution-fit.md#da-075), [DA-078](execution-fit.md#da-078),
  [DA-033](execution-fit.md#da-033), [DA-058](execution-fit.md#da-058).
- **FP-01 / FP-03, responsibility and composition.** By asking which code still has a consumer:
  [DA-080](boundaries-and-composition.md#da-080).
- **FP-02, contracts.** The wire boundary validates once on each side and the native read has
  one entry point; no new finding.
- **FP-05, explicit failure.** [DA-079](boundaries-and-composition.md#da-079); and the fail-open
  direction of DA-070.
- **FP-06, local reasoning.** Addressed mainly through the test account. On the production
  side, the hand lists of DA-070, DA-073 and DA-074 are what a reader cannot infer locally.
- **Code-intelligence profile.** Pinned serving (CI-13) and attributable evidence (CI-10, CI-11)
  informed DA-076, DA-077 and the contrary evidence for DA-068. Unknown is kept distinct from
  absent in the served reports read.

## Diagnostic synthesis

The integrated argument, with the test account, is on the
[joint page](model-and-execution.md). In brief:

- **The model's core is sound and should be preserved.** One compiled model per release, typed
  origins, refusal of conflicting owners, and a result identity that excludes release and
  runtime. Where a dependency is expressed through that identity, reuse is exact.
- **Run-time governance is not yet in the model.** Which validity rules apply to an operation,
  what a support edge means, which relations are guarded, and which code an answer depends on
  are held as hand-written lists. An omission from the validity lists fails open (DA-070).
- **Several identities are far coarser than their premise.** A digest over about forty modules
  stands for the kernel; whole files and library versions stand for an operation's
  implementation; the read instance stands for the content of a served result. Each discards
  valid work on an unrelated edit, and the first also forces indefinite re-validation of
  history.
- **Two identities are narrower than their premise.** The served implementation identity and
  the scientific policy both miss code that shapes results.
- **Immutable release content is re-proved on every admission and binding** although receipts
  that record the proof already exist.
- **The new query cache rarely hits** on five of its six paths, and never for the CLI, because
  of how it is keyed and because every cache in the system is process-local.

## New and changed findings

| Finding | Summary |
|---|---|
| [DA-068](execution-fit.md#da-068) | One digest over every captured native source keys admission, read acquisition and carried assurance |
| [DA-069](execution-fit.md#da-069) | Implementation identity of construction and formal operations takes whole files, whole model files and library versions |
| [DA-070](semantic-model-and-authority.md#da-070) | Validity families are assigned from hand-written operation-id lists; an unlisted operation is treated as valid |
| [DA-071](semantic-model-and-authority.md#da-071) | Support-graph meaning is encoded three times and the change-impact copy disagrees |
| [DA-072](semantic-model-and-authority.md#da-072) | The earlier core and system model is still live, with the same closed sets declared in both |
| [DA-073](semantic-model-and-authority.md#da-073) | Release operation membership is composed by hand-written flag logic |
| [DA-074](native-integrity.md#da-074) | Native authorization and guard membership are code lists outside the declaration |
| [DA-075](execution-fit.md#da-075) | Five of six query cache keys include the acquisition instance, so identical fresh requests do not share an entry |
| [DA-076](served-claims.md#da-076) | The implementation identity of a served read omits modules that shape the answer |
| [DA-077](served-claims.md#da-077) | The archived scientific policy describes the kernel instead of deriving from it |
| [DA-078](execution-fit.md#da-078) | The readiness watermark is coarser than the declared role dependencies |
| [DA-079](boundaries-and-composition.md#da-079) | The process host refuses a second concurrent run with an unclassified error |
| [DA-080](boundaries-and-composition.md#da-080) | Superseded machinery remains, kept alive only by tests or by nothing |
| [DA-033](execution-fit.md#da-033) (changed) | Admission and binding re-prove immutable release content |
| [DA-058](execution-fit.md#da-058) (changed) | Visual recognition re-prepares its runtime every four packets |

Eighty DA identities exist; none is retired or reused. Of DA-001–067: 14 no longer apply
because the machinery they described was removed, 8 are corrections that hold or likely hold,
3 stand as they were, 15 have a changed footprint recorded on their page, and 27 were not
re-examined and keep their earlier evidence date. Each topic page lists its own.

<a id="deviations"></a>

## Limits

- **Read in part or not at all.** Most model YAML bodies and the generators; `ontology.py` and
  `conditional_rules.py`; the planner's batch, settle and hydrate bodies; family validators
  other than contextual; most PDF storage and record SQL bodies; the GLiNER, HanLP and PM2
  method bodies; `cli/model.py`, `cli/managed.py` and `cli/schema.py`; consolidation and the
  rich rule evaluator; every migration revision except the most recent.
- **Not established.** Whether equal outputs stop recomputation below the formal operations;
  whether a content-based cache key is sound; whether any relation is wrongly outside the
  frontier guard; whether concurrent MCP renders actually overlap; how large any of the
  repeated work is. Each finding states its own uncertainty.
- **Not run.** Product tests, native or provider runs, fault injection, measurement and
  integrated qualification. Several commits that introduced the mechanisms read here record
  `runtime not_run`; this account judges their design, not whether they currently pass.
- **Inherited.** Twenty-seven earlier identities were not re-examined. The witnessed-enrichment
  observations and the documentation-publication observations of 2026-11-08 are among them.

<a id="independent-challenge"></a>

## Independent challenge

A fresh reviewer, given the criteria and the drafted pages but not the contributors' reports,
opened the cited sources and tried to refute each new finding and each "corrected" or "no
longer applicable" claim. Its effect on the published account is recorded here.

- **Withdrawn:** none.
- **Reframed as documented choices:** DA-068 (the plan chose the kernel digest for the seal and
  the full battery on mismatch; the finding is now what that digest covers and one divergence
  from the plan), DA-078 (the watermark's granularity is the plan's specification) and DA-079
  (one run per host is ADR-0125's stated trade).
- **Corrected:** DA-070's claim that the other lists fail closed (an omission fails open at
  completion too), with the consequence now split by family; DA-071's statement of which
  projection the planner consumes, and the divergence shown to run both ways; DA-080's count of
  unreferenced SQL files (fourteen, not twelve); DA-069's list of captured files; three line
  references in the earlier-identity tables.
- **Narrowed:** DA-075 from six paths to five, because the exclusion comparison keys on content
  stamps and can hit; that also shows the "open premise" is already relied on once. DA-058's
  mechanism: building the runtime only hashes the checkpoints, and the model load follows on
  first inference.
- **Sharpened:** DA-033 (the finalization receipt is read immediately before the re-proof it
  could carry).
- **Removed as a residual:** the release being derived at registration and again per host
  basis, which the production-efficiency review records as a deliberate boundary.
- **Confirmed as drafted:** DA-072, DA-073, DA-076, DA-077.
- **Not checked by the challenger:** the domain model map beyond a skim, and the PE-F12, F14
  and F24 rows of the state table.

## Reading routes

| Topic | Current use |
|---|---|
| [The domain model and execution](model-and-execution.md) | Integrated analysis with the test account; cache inventory; state of the production-efficiency mechanisms |
| [Domain model map](domain-model-map.md) | Where meaning is declared, compiled and realized; how a change becomes recomputation |
| [Semantic model and authority](semantic-model-and-authority.md) | Model facts restated by hand (DA-070–073) |
| [Execution fit](execution-fit.md) | Coarse identities, the query cache, re-proved assurance (DA-068, 069, 075, 078, 033, 058) |
| [Native integrity](native-integrity.md) | Guard and grant lists (DA-074); native strengths |
| [Served claims](served-claims.md) | Implementation and policy identity of served results (DA-076, 077) |
| [Boundaries and composition](boundaries-and-composition.md) | Host concurrency (DA-079); superseded machinery (DA-080) |
| [Structure and invariants](structure-and-invariants.md) | Earlier identities only |
| [Witnessed enrichment](witnessed-enrichment.md) | Earlier identities only, not re-examined |
| [Local reasoning and assurance](local-reasoning-and-assurance.md) | Navigation and the boundary with the test account |

## Ownership and reuse

Each cause has one primary home across this account and the test account. IDs are never
reused. Removing a diagnosis here does not close a plan obligation. The new findings are
unscheduled: no plan owns them until the operator asks for a review or a plan revision, and
their revisit trigger is the next design-review engagement on the declared-data-operations
target. Findings of the production-efficiency review keep their `PE-Fnn` identities and their
disposition in the [DDO plan](../../plans/declared-data-operations_2026-11-12.md); this account
reports their state in source and does not re-own them. Consuming reviews cite this account's
publication revision and stable anchors, and reconcile intervening source changes.

## Earlier engagement anchors

These preserve existing links. The entries they named described source that has since been
replaced; their text and dates are in Git at `fbd3f2a98` and earlier.

<a id="declared-data-operations-entry-refresh"></a>
<a id="book-ready-execution-refresh"></a>
<a id="book-execution-entry-refresh"></a>
<a id="text-characterization-entry-refresh"></a>
<a id="cld-assembled-refresh"></a>
<a id="cld-entry-refresh"></a>
<a id="domain-data-model-assembled-refresh"></a>
<a id="domain-data-model-interpretation-correction-refresh"></a>
<a id="domain-data-model-construction-terminology-refresh"></a>
<a id="domain-data-model-entry-refresh"></a>
<a id="ptd-assembled-refresh"></a>
<a id="pm2-parser-refresh"></a>
<a id="pm2-foundation-refresh"></a>
<a id="ghv-follow-on-publication-refresh"></a>
<a id="documentation-publication-refresh--2026-11-08"></a>
<a id="text-characterization-producer-reconciliation"></a>
<a id="m1-admission-refresh"></a>
<a id="m1-public-reference-refresh"></a>
<a id="m1-source-evidence-refresh"></a>
<a id="m1-initial-target-refresh"></a>
<a id="unified-model-refresh"></a>
<a id="sql-authoring-refresh"></a>

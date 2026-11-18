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
| Scoped refresh, 2026-11-18 | `d78c98765b2543a0a86515134257259debe75dfd`, committed `main`, read in a frozen export of that commit. DA-068 to DA-081, DA-033 and DA-058 were re-read, and the typed-program and generator layer was audited as new scope. The 27 earlier identities not re-examined are unchanged. Static reading only. See [the refresh](#refresh-2026-11-18) |

This refresh replaces the stacked scoped entries of the earlier README with one current
account. It was needed because the declared-data-operations work replaced most of the code
those entries described: since the 2026-11-12 entry, 364 production files were added, 149
deleted and 307 modified, and the owners cited by the earlier domain model map were removed on
2026-11-16.

Observations are **Interface-checked by source inspection** on 2026-11-17 unless a row says
"not re-examined", in which case the last evidence keeps its original date, or a paragraph is
headed "Refresh, 2026-11-18", in which case it was read at `d78c98765` on that date. Nothing
here is labelled Tested or Measured.

<a id="refresh-2026-11-18"></a>

## Refresh of 2026-11-18 at `d78c98765`

**Kind.** A scoped refresh, not a broad one. `main` moved 163 commits from `1afa63f88` to
`d78c98765b2543a0a86515134257259debe75dfd` (197 from `fbd3f2a98`), and in that range most of
the model-owned SQL conversion ([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md))
landed. The conversion is not complete: the ADR says it "records the target while conversion
is open" (`:51`), and the [DDO plan](../../plans/declared-data-operations_2026-11-12.md)
records residual SQL authoring as open in its status line and its remaining-conversion
paragraphs (`:3, 100–103, 191–195`). Two things were done:

- DA-068 to DA-081, DA-033 and DA-058 were re-read in a frozen export of the commit;
- the typed-program and generator layer that the conversion has produced so far, the
  hand-written SQL that remains, and the DuckDB modules were audited as new scope.

The 27 earlier identities that the 2026-11-17 refresh did not re-examine stay as they are.
**Interface-checked by source inspection, 2026-11-18.** Nothing was run: no test, database
command, provider call or benchmark. Statements of cost are counts of repeated work read from
code paths, never timings. The standard versions are those of the [baseline](#baseline). Three
read-only contributors read one area each (identity and reuse; model authority; generators and
remaining SQL) and a fourth mapped analytical computation. Their candidates were then
reconciled by structural cause, and the lines that decide each finding were checked in the
snapshot. An independent challenge followed and is recorded
[below](#refresh-challenge).

### Status of the re-read findings

| Finding | Status at `d78c98765` |
|---|---|
| [DA-068](execution-fit.md#da-068) | Stands, wider again: about 75 to 85 captured modules and six library versions; seven uses of the digest confirmed, where five were recorded |
| [DA-069](execution-fit.md#da-069) | Stands unchanged; no commit to its owners |
| [DA-070](semantic-model-and-authority.md#da-070) | Stands, changed footprint: the id list was transcribed into a Python tuple, and the dispatch `CASE` became a second Python tuple; both lists already existed in the deleted SQL, and both fail open. The condition for closing it is not met |
| [DA-071](semantic-model-and-authority.md#da-071) | Stands: three encodings, all now Python; the change-impact disagreement is unchanged |
| [DA-072](semantic-model-and-authority.md#da-072) | Stands, lines moved; the earlier model also feeds a generated facade of the released model |
| [DA-073](semantic-model-and-authority.md#da-073) | Stands unchanged; no commit to its owners |
| [DA-074](native-integrity.md#da-074) | Stands, wider footprint: membership unchanged; 176 occurrences of role names in 39 modules; every `ph:read_roles` annotation is empty; shared-stream membership has a declaration that nothing reads |
| [DA-075](execution-fit.md#da-075) | Stands unchanged |
| [DA-076](served-claims.md#da-076) | Stands unchanged; contrary evidence is stronger for native SQL drift |
| [DA-077](served-claims.md#da-077) | Stands unchanged; a third comparison site found |
| [DA-078](execution-fit.md#da-078) | Stands; the kernel component of the watermark is now established, where it was inferred |
| [DA-079](boundaries-and-composition.md#da-079) | Stands unchanged; no commit to its owners |
| [DA-080](boundaries-and-composition.md#da-080) | Partly corrected, changed footprint: ten of fourteen orphan SQL files deleted, six files now without a loader; new unconsumed items (a migration helper, two migration trees, two analytical kernels, six settings fields). The earlier "stale `scientific_layout.sql` key" remark is withdrawn |
| [DA-081](semantic-model-and-authority.md#da-081) | Stands, much wider footprint: there is no typed registry of programs and generated outputs. The program set is listed by hand in six places, two of which already disagree; a rendered program's facts are recovered by parsing text; and the released model has no generator registry at all |
| [DA-033](execution-fit.md#da-033) | Changed footprint, substance stands: the checks are generated and perform the same re-proof. The capture-rebuild sentence moved to DA-083 |
| [DA-058](execution-fit.md#da-058) | Stands unchanged; no commit to its owners; Chandra remains outside scope |

### New findings

| Finding | Summary | Home |
|---|---|---|
| [DA-082](execution-fit.md#da-082) | The PDF lowering identity is a hand-kept list of 70 files and 14 library versions with no completeness check. It omits two modules on the lowering path and lists shared infrastructure whole | Execution fit |
| [DA-083](execution-fit.md#da-083) | The native source capture has no holder and no file custody: it is rebuilt twice per admission check and three times per definition admission, on the execution path, and pairs SQL from imported code with module bytes read fresh from disk | Execution fit |
| [DA-084](boundaries-and-composition.md#da-084) | Hand-written PostgreSQL that ADR-0131 schedules for conversion is still deployed, is not inventoried by the plan, and holds the family and role lists; model changes do not reach it. The audit adds the inventory: about 1,830 lines of PL/pgSQL strings in eleven generator modules, ten loaded `.sql` files and eleven splice sites | Boundaries and composition |
| [DA-085](semantic-model-and-authority.md#da-085) | The LinkML part of the released model is composed separately by each consumer through a copied routine, holds its physical constraints as JSON strings inside annotations, and is not one object with the effective operation model | Semantic model and authority |
| [DA-086](semantic-model-and-authority.md#da-086) | Generators and analytical modules restate as Python literals facts that the model declares or a typed source already carries: task states, the value-codec vocabulary, four field-kind-to-type maps, hand-declared Arrow schemas | Semantic model and authority |

### Revised diagnostic synthesis

The 2026-11-17 delta observed that the conversion "changes how statements are written, not
where their facts come from". **That still holds at `d78c98765`, with one real exception.**

- *The exception, which is sound.* Relations, columns and column types now come from the
  compiled model. A typed program names a table through compiled metadata, so a renamed table
  or column fails when the program is generated. Raw SQL text is refused inside a program,
  every step must parse as one statement, a security-definer routine must declare its search
  path, and generated bytes are kept in custody beside their generators and frozen into the
  migration that deploys them. Deployment imports no generator.
- *What did not move.* Every membership and governance fact recorded on 2026-11-17 is still a
  hand list: validity families (DA-070), support-edge meaning (DA-071), release composition
  (DA-073), guards, roles and grants (DA-074). The lists moved from SQL into Python, often word
  for word. Where the model does declare a fact beyond relations and columns, generators often
  do not read it (DA-086).
- *What is still open.* The conversion is unfinished by its owners' own record. Hand-written
  PostgreSQL is still deployed beside the typed route, and it holds exactly the family layer
  where the DA-070 lists live and much of the role text of DA-074, so the order of the
  remaining work matters (DA-084).
- *What the layer left.* There is no typed registry of programs: the set is listed by hand in
  six places, and once rendered a program is text whose facts later steps recover by parsing
  (DA-081).
- *What the layer made worse.* The kernel identity is wider (DA-068), the lowering list grew
  by hand with every generator commit (DA-082), and the capture that both depend on became
  expensive to build while still being rebuilt at every admission-side call (DA-083).
- *Underneath.* There is no one object that a generator could read cross-view facts from:
  each consumer composes its own LinkML view, and those views are separate from the effective
  operation model (DA-085). That operations have two authoring routes is an accepted decision
  (ADR-0092) and is not part of the finding.

The three recurring causes of the 2026-11-17 synthesis stand. The integrated argument, with an
identity inventory, a refreshed cache inventory and a map of analytical computation, is on the
[joint page](model-and-execution.md); the current owners of every model fact are on the
[domain model map](domain-model-map.md).

### Limits of this refresh

- **Not read.** Generator bodies for equivalence with the SQL they replaced; the bodies of
  most of the 72 `*_native.py` modules; `native_call_generation.py` beyond its header;
  `schema/relational.py` beyond its outline and annotation readers; `schema/model_deployment.py`;
  migration revision bodies; `ontology.py` beyond its dynamic-enum block; `conditional_rules.py`;
  `schema/stage_b.py`; `rulelang.py`; the generated `_pdf_native_calls.py`; `cli/` and
  `intervene/`.
- **Not re-read, with no commit in range.** `visual_requests.py`, `ingest/pdf_chandra.py`,
  `execution_admission.py`, `file_custody.py`, `orchestrate/execution_host.py`,
  `cpu_execution.py`, `archive_reader.py`, `methods/math/grammar.py`, `change_impact.py`,
  established validity, and the serving consumers of the query cache beyond their key lines.
  Their 2026-11-17 text is taken as still valid.
- **Counted by script or search.** The hand-written PL/pgSQL line figures are the challenger's
  recount by a syntax-tree walk and depend on the method (about 1,800 to 2,100 lines). The
  free-callee and SQLite site counts and the LinkML feature counts are a contributor's and
  were not recounted.
- **Not established.** How often the native capture is rebuilt in a real run, or what one
  rebuild costs; replay volumes; whether preparation runs in a long-lived process; which
  hand-written bodies reference relations or columns; whether the per-consumer model closures
  differ in result; whether further modules are missing from the lowering list; realistic row
  counts for any analytical computation.
- **Not in scope.** The test account was not refreshed, and the production-efficiency state
  table was updated only where a re-read finding touches a row.
- **A count that differs from a contributor's report.** One report gave 45 LinkML schemas;
  the snapshot has 43 under `model/semantic/` and 45 when the two earlier-model schemas are
  included. One report said no generator is reached from admission; the admission check does
  rebuild the capture and so runs the generators (DA-083). Both were settled in the snapshot.

<a id="refresh-challenge"></a>

### Independent challenge

A separate reviewer challenged the drafted pages before publication. It read source at
`d78c98765` and the plans and decision records first, did not read the contributors' reports,
and tried to refute each new finding, each status claim and samples of the three inventory
tables. Its effect:

- **Reframed:** DA-084. The drafts had taken the conversion to be complete and presented the
  remaining hand-written PostgreSQL as a defect outside ADR-0131. The ADR and the DDO plan
  record it as open, scheduled work. The finding now states that, and offers what the plan
  lacks: the inventory, the fact that model changes do not reach it, and that it holds the
  family and role lists.
- **Narrowed:** DA-085. Two authoring routes for operations compiled into one effective model
  is the accepted decision of ADR-0092 and moved to contrary evidence. The finding is now the
  per-consumer LinkML composition and the constraints held as JSON strings.
- **Merged:** a drafted finding on text as the handoff between generation and installation
  was folded into DA-081, since both come from the absence of a typed registry of programs.
  The refresh therefore adds five identities, not six.
- **Withdrawn:** the claim, in DA-080 and DA-081, that installation dispatches on a stale
  `scientific_layout.sql` key. The name is a label for a generated artifact.
- **Corrected:** DA-081's contrary evidence (the required-set check accepts an unexpected
  artifact, and omits six that are concatenated, which is now part of the footprint); DA-070's
  statement that a second list was new; DA-086's field-kind item (the model does declare it);
  DA-082's earlier entry count and the consequence stated for one omitted module; and counts
  of hand-written SQL lines, splice sites, operation-declaring modules, role-name occurrences
  and concatenated artifacts.
- **Re-located:** three facts whose generators the drafts had not found (the renew program;
  that a directly revoked producer cannot be rehabilitated; that only revocation takes an
  exclusive lock on the trust scope).
- **Nothing else refuted.** DA-082, DA-083 and the status claims for DA-068, DA-072, DA-074,
  DA-075 and DA-080 were confirmed. DA-071, DA-073, DA-076 to DA-079, DA-033 and DA-058 were
  spot-checked by line only.
- **Not checked by the challenger:** the analytical section, the production-efficiency state
  table and the superseded planned-change table on the joint page; generator bodies for
  equivalence; `domains/`.

### Sound designs worth preserving

- The semantic request key, which excludes release and runtime
  (`semantic/binding_admission_native.py:213`).
- The program compiler's rule that Core and parsed nodes own statements and the compiler owns
  only procedural framing, with raw text refused (`semantic/native_program.py:1–5, 126–131`).
- Server-side normalization and static checking in a rollback-only scope, exact frozen
  statements and catalog snapshots in migration custody, and deployment that imports no
  generator (`semantic/native_objects.py:1–5, 950–1121`).
- Derivations that already work and show the pattern: immutability and archive triggers from
  declared classes; physical value sets from the protocol; protocol function grants from
  declared purposes; the SourceValue codec's closed-set check against LinkML; universe validity
  read from a typed literal; Arrow schemas for PDF records and exports from compiled metadata
  ([map](domain-model-map.md#strengths)).
- The read kernel pin, which turns kernel drift into reacquisition instead of a wrong answer
  (`semantic/data_read_boundary_native.py:84–92`).
- File custody with stat identity, and query custody's loader that compiles exactly the hashed
  bytes and refuses a reload (`semantic/file_custody.py:79–137`; `_query_custody.py:136–200`).
- The capture's required-set check and its equality check against the physical model
  (`semantic/data_operation_storage.py:569–692`), and generated bytes captured beside their
  generators.
- The rich assets' identity over the parsed meaning of a module, the finest implementation
  identity in the codebase (`semantic/python_module_projection.py:111–120`).
- The selected-query cache's byte accounting and immutable encoded entries; wire-protocol
  caches keyed by content; deployment expectations cached by file digest and stat.
- Submitted read-only SQL admitted through a parsed allowlist and bound by PostgreSQL in a
  read-only transaction (`semantic/authored_sql.py`).
- Per-invocation DuckDB connections with private spill directories and cancellation checks,
  and DuckDB used through its relational API with no SQL text.

<a id="delta-1afa63f88"></a>

## Delta of 2026-11-17 at `1afa63f88`

A scoped re-read, not a refresh. `main` moved 34 commits from `fbd3f2a98` to
`1afa63f883f07873c8b4d3cccb9fc6622b558d50` (70 production files changed) while the model-owned
SQL conversion ([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md)) was in progress.
Only DA-068 to DA-080, DA-033 and DA-058 were re-read, in a frozen export of the pin.
**Interface-checked by source inspection, 2026-11-17.** Nothing was run. Later commits and
uncommitted work are outside this delta.

The conversion so far changes how statements are written, not where their facts come from. The
hand lists behind DA-070, DA-071 and DA-074 are all still in place.

| Finding | Status at `1afa63f88` |
|---|---|
| [DA-068](execution-fit.md#da-068) | Wider: generators, three model files and three library versions joined the digest; the program layer also joined the PDF lowering identity |
| [DA-069](execution-fit.md#da-069) | Stands; footprint grew |
| [DA-070](semantic-model-and-authority.md#da-070) | Stands unchanged (`semantic/sql/data_operations.sql:345–353, 2311–2328`). The "typed validity" commits convert product validation, a different mechanism |
| [DA-071](semantic-model-and-authority.md#da-071), [DA-072](semantic-model-and-authority.md#da-072), [DA-073](semantic-model-and-authority.md#da-073) | Stand; cited code unchanged. The new generators read only the released model |
| [DA-074](native-integrity.md#da-074) | Stands; statement rendering changed, membership lists did not |
| [DA-033](execution-fit.md#da-033) | Changed footprint; substance stands |
| [DA-080](boundaries-and-composition.md#da-080) | Partly corrected (one of fourteen unreferenced SQL files deleted) |
| [DA-078](execution-fit.md#da-078) | Indirectly wider, because its watermark includes the kernel digest (inferred) |
| DA-075, 076, 077, 079, 058 | Not affected by the diff |
| [DA-081](semantic-model-and-authority.md#da-081) | New: generated native facades registered a second time by hand |

Eighty-one DA identities existed after this delta. Sound designs added in the range, worth preserving:
rendering that refuses raw SQL text and requires each step to parse as one statement
(`semantic/native_program.py:87–122`); generated bytes kept in custody beside their generators;
captured metadata refused when it differs from its inputs
(`semantic/data_operation_projections.py:2474–2479`); one generated wire validation point;
typed CHECK and index predicates compared with the bound catalog; one type table for
declarations and grants (`semantic/native_call_contracts.py`).

Not read: the large generator bodies for equivalence with the SQL they replace, the DuckDB
modules, and whether PDF search reads carry a served implementation identity. What the
remaining planned steps would do to these findings is on the
[joint page](model-and-execution.md#planned-change), which the
[refresh of 2026-11-18](#refresh-2026-11-18) has since superseded.

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

This is the synthesis of 2026-11-17 at `fbd3f2a98`. The
[refresh of 2026-11-18](#refresh-2026-11-18) revises it for `d78c98765`; figures below such as
"about forty modules" are those of the earlier reading. The integrated argument, with the test
account, is on the [joint page](model-and-execution.md). In brief:

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

Summaries are current at `d78c98765` for every finding re-read or established in the
[refresh of 2026-11-18](#refresh-2026-11-18).

| Finding | Summary |
|---|---|
| [DA-068](execution-fit.md#da-068) | One digest over every captured native source keys admission, read acquisition and carried assurance |
| [DA-069](execution-fit.md#da-069) | Implementation identity of construction and formal operations takes whole files, whole model files and library versions |
| [DA-070](semantic-model-and-authority.md#da-070) | Validity families are assigned from hand-written operation-id lists; an unlisted operation is treated as valid |
| [DA-071](semantic-model-and-authority.md#da-071) | Support-graph meaning is encoded three times and the change-impact copy disagrees |
| [DA-072](semantic-model-and-authority.md#da-072) | The earlier core and system model is still live, with the same closed sets declared in both |
| [DA-073](semantic-model-and-authority.md#da-073) | Release operation membership is composed by hand-written flag logic |
| [DA-074](native-integrity.md#da-074) | Native authorization and guard membership, including role names and execute grants, are code lists outside the declaration |
| [DA-075](execution-fit.md#da-075) | Five of six query cache keys include the acquisition instance, so identical fresh requests do not share an entry |
| [DA-076](served-claims.md#da-076) | The implementation identity of a served read omits modules that shape the answer |
| [DA-077](served-claims.md#da-077) | The archived scientific policy describes the kernel instead of deriving from it |
| [DA-078](execution-fit.md#da-078) | The readiness watermark is coarser than the declared role dependencies |
| [DA-079](boundaries-and-composition.md#da-079) | The process host refuses a second concurrent run with an unclassified error |
| [DA-080](boundaries-and-composition.md#da-080) (partly corrected at `d78c98765`) | Superseded machinery remains, kept alive only by tests or by nothing, now with unread settings, kernels with no caller and two unconsumed migration trees |
| [DA-081](semantic-model-and-authority.md#da-081) (delta at `1afa63f88`; wider at `d78c98765`) | The native program set and its generated outputs have no typed registry: they are listed by hand in several places and their facts are recovered from text |
| [DA-082](execution-fit.md#da-082) (new at `d78c98765`) | The PDF lowering identity is a hand-kept file list with no completeness check, at once too narrow and too broad |
| [DA-083](execution-fit.md#da-083) (new at `d78c98765`) | The native source capture has no holder and no file custody |
| [DA-084](boundaries-and-composition.md#da-084) (new at `d78c98765`) | Hand-written PostgreSQL that ADR-0131 schedules for conversion is still deployed, is not inventoried by the plan, and holds the family and role lists; model changes do not reach it |
| [DA-085](semantic-model-and-authority.md#da-085) (new at `d78c98765`) | The LinkML part of the released model is composed separately by each consumer, holds its physical constraints as JSON strings, and is not one object with the effective operation model |
| [DA-086](semantic-model-and-authority.md#da-086) (new at `d78c98765`) | Generators and analytical modules restate as Python literals facts that the model declares or that a typed source already carries |
| [DA-033](execution-fit.md#da-033) (changed) | Admission and binding re-prove immutable release content |
| [DA-058](execution-fit.md#da-058) (changed) | Visual recognition re-prepares its runtime every four packets |

Eighty DA identities existed at `fbd3f2a98`, eighty-one after the [delta](#delta-1afa63f88),
and eighty-six exist after the [refresh of 2026-11-18](#refresh-2026-11-18), which added
DA-082 to DA-086; none is retired or reused. The next new identity is DA-087. Of DA-001–067: 14 no longer apply
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
| [The domain model and execution](model-and-execution.md) | Integrated analysis with the test account; cache inventory; identity inventory; analytical and set-wise computation; state of the production-efficiency mechanisms |
| [Domain model map](domain-model-map.md) | Declaration owners, composition, compiler paths, what is generated from what, LinkML features used, fact ownership and data-model library roles, at `d78c98765` |
| [Semantic model and authority](semantic-model-and-authority.md) | Model facts restated by hand (DA-070–073, DA-086); no typed registry of programs (DA-081); per-consumer LinkML composition (DA-085) |
| [Execution fit](execution-fit.md) | Coarse and hand-kept identities, the query cache, re-proved assurance, the unheld native capture (DA-068, 069, 075, 078, 033, 058, 082, 083) |
| [Native integrity](native-integrity.md) | Guard, role and grant lists (DA-074); native strengths |
| [Served claims](served-claims.md) | Implementation and policy identity of served results (DA-076, 077) |
| [Boundaries and composition](boundaries-and-composition.md) | Host concurrency (DA-079); superseded machinery (DA-080); hand-written PostgreSQL still awaiting conversion (DA-084) |
| [Structure and invariants](structure-and-invariants.md) | Earlier identities only |
| [Witnessed enrichment](witnessed-enrichment.md) | Earlier identities only, not re-examined |
| [Local reasoning and assurance](local-reasoning-and-assurance.md) | Navigation and the boundary with the test account |

## Ownership and reuse

Each cause has one primary home across this account and the test account. IDs are never
reused. Removing a diagnosis here does not close a plan obligation. The new findings, including
DA-082 to DA-086, are unscheduled as findings: no plan owns them until the operator asks for a review or a plan revision, and
their revisit trigger is the next design-review engagement on the declared-data-operations
target. DA-084 is the exception in substance: the conversion it inventories is scheduled work
of the DDO plan, and only the inventory and the ordering observation are the audit's. Findings of the production-efficiency review keep their `PE-Fnn` identities and their
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

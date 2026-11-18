# Design review: one domain model, its derived forms, and execution in the production package

Formal design/target review, 2026-11-18. Supporting documents:
[cache-design.md](unified-domain-model-and-execution/cache-design.md) (the cache system, recommendation R09) and
[dispositions.md](unified-domain-model-and-execution/dispositions.md) (one disposition per consumed audit finding). Audit publication consumed: `90467bde0`.

**Revised recommendations · 2026-11-18.** The recommendations of this review were revised by an
independent recommendation audit on 2026-11-18, from input revision `b4eb74f67`, on the
operator's concern that the target should represent the pipeline's intentional flexibility and
optionality rather than govern it away. The revised judgments (chiefly R02, §3.2, R03, R05, R07,
R13, the new R15 and R16, finding F05 and rule impacts RC01, RC04, RC05, RC12 and RC14) are the
auditor's; the first reviewer did not author or endorse them. The companion
[audits/design_review_unified-domain-model-and-execution_2026-11-18_audit.md](audits/design_review_unified-domain-model-and-execution_2026-11-18_audit.md)
explains every change and its evidence; the original text is recoverable from Git at
`b4eb74f67`.

**Revised to current source · 2026-11-18.** This review was revised on 2026-11-18 by an
independent reviewer, who wrote neither the review, its recommendation audit, the diagnostic audit
nor the code, against source `5139eaba3` (127 commits after the original baseline `d78c98765`),
consuming the diagnostic audit as updated at that source (the coordinator states its publication
commit), from input revision `c25cada3f` of these three files. The revised judgments recorded in
"What changed in this revision" below, and the text they changed, are this reviewer's; neither the
first reviewer nor the recommendation auditor authored or endorsed them. The input text is
recoverable from Git at `c25cada3f`.

## What changed in this revision

Between `d78c98765` and `5139eaba3` the admission modules were regenerated as typed programs, the
directory `semantic/sql/` was removed, and the native stage advanced from revision N13 to N29. The
largest consequence for this review is that its central ordering argument has been overtaken: the
conversion it asked to wait for declared facts went ahead, and the facts were transcribed into
Python lists inside the generators, as the review predicted. The revision therefore restates R07
as an extraction of transcribed facts, and changes R02 and R16 so that guards select operations at
run time by a lowered, declared attribute instead of by lists written into the kernel. Statuses:
**delivered** (removed from the target), **partly delivered** (the remainder restated), **changed**
(the code or the evidence moved the recommendation, and it is re-argued), **unchanged** (it stands
as written; only line references were refreshed where they moved).

| Item | Status in this revision |
|---|---|
| R01 One composer and a held compiled model | Unchanged. No composition site changed; a content-keyed holder for the companion projection was added and is a fourth per-consumer composition; typed decoding of semantic annotations (DA-004) added |
| R02 Declared vocabularies and classifications | Changed. Family membership is lowered per release from the operation's declaration, and every guard, validator and dispatch selects by the lowered column (precedent: two guards already select by a declared effect, and four families already declare one); per-family member requirements replace per-operation pins; transcribed narrowings (query producers by id) read lowered dependencies; DA-001 and DA-040 connections added |
| R03 Typed physical profile | Unchanged |
| R04 Typed program registry | Partly delivered. The typed trigger and view forms exist (`4760982d8`, `a9c594d48`) and scratch tables are retargeted on the parse tree (`759dd837f`); the registry, the text handoff and a new comment-boundary recovery remain |
| R05 Identity from declared dependencies | Changed (strengthened). The capture is 99 modules; revision N29 changed no generated statement and restamped two provenance digests; ADR-0092 `:27` already forbids a broad runtime digest as a recipe fallback; frozen revisions already hold per-object statements, so program identity and revision deltas follow them; DA-028 is added as R17 |
| R06 The execution path generates nothing | Unchanged in substance, strengthened: the generated release guard already compares the archived digest with the installed descriptor in the same call |
| R07 Remaining PostgreSQL conversion and its order | Changed. The order is overtaken; R07 now specifies the extraction of transcribed facts, its cost and order, and the small remaining SQL residue |
| R08 One support-edge meaning and one walk | Unchanged. A narrow fourth walk is noted for the owner |
| R09 Cache system | Unchanged. The cache design's keys, bounds and invalidation premises hold; inventory deltas recorded in the cache document |
| R10 Served-read reuse basis and watermark | Unchanged. The watermark gained a role-matched component; the kernel component remains |
| R11 Carried assurance | Unchanged. The release guard is now generated and performs the same re-proof |
| R12 Analytical placement and DuckDB conditions | Unchanged. No DuckDB module changed; DA-020's literal limits are covered by the configuration wiring |
| R13 Retirement | Partly delivered. Six unloaded SQL files (`c25cada3f`), the published-address migration helper (`54a232131`) and the scalar encoder kernels (`93b7141ec`) are gone; six newly found items added, among them the dead native fitting path |
| R14 Scientific policy | Unchanged |
| R15 Declared openness of vocabularies | Unchanged |
| R16 Graded consequences for undetermined declarations | Changed. The undetermined state now also governs completion guards, which select by the lowered family; their present early returns are the fail-open point the declaration removes |
| R17 Release-bound pack inputs come from the release (DA-028) | New in this revision |
| F01 Per-acquisition check regenerates the capture | Unchanged (re-verified); the comparison it performs is now redundant with the generated release guard |
| F02 Unlocked and unbounded process-global memos | Unchanged (no commit to the owners) |
| F03 DuckDB connections take library defaults | Unchanged; three further sites set literal limits (DA-020) |
| F04 SQLite SQL text in application code | Unchanged (58 execute sites, as before) |
| F05 Vocabulary openness only in the earlier model | Unchanged |
| RC01 | Changed: the conversion-order clause is replaced by an extraction clause |
| RC02 | Ready as written |
| RC03 | Ready as written |
| RC04 | Ready as written |
| RC05 | Changed: the column is lowered from the operation's declaration |
| RC06 | Ready as written (evidence strengthened) |
| RC07 | Ready as written |
| RC08 | Ready as written |
| RC09 | Ready as written |
| RC10 | Ready as written |
| RC11 | Ready as written |
| RC12 | Ready as written (locations refreshed) |
| RC13 | Ready as written |
| RC14 | Ready as written |
| RC15 | New: native revisions are authored when installed program bytes differ, not when the kernel digest moves |

The audit update was independently challenged while this revision was written; its corrections are
used here: the SQL counts are stated by population; role-name literals moved from SQL into Python
and fell in total (246 to 199); the task guard already read the declared lifecycle at `d78c98765`,
so nothing of DA-086 was delivered in the range; N29 restamped two provenance digests and changed
no generated statement; one real hand-written PostgreSQL item remains, and the native fitting path
is dead code; two guards, not one, already select by a declared effect, and four families already
declare one; DA-065 is a changed footprint, not a regression; ADR-0092 `:27` supports DA-068.

## 1. Scope, outcome and coverage

| Field | Value |
|---|---|
| Subject | The production package `python/corpus-structure/src/corpus_structure/`, its model declarations (`model/`, packs), its generators, and the scripts that provision and deploy it, at commit `d78c98765` (frozen snapshot; committed tree, no dirty state). Revised against commit `5139eaba3` (frozen snapshot), 2026-11-18 |
| Standard | Core principles, template and efficient-architecture heuristics 3.3 / 1.0; code-intelligence profile 1.4; corpus-structure binding (from `docs/design_review/design_principles/standard.toml`) |
| Tier and purpose | Design; target |
| Focus (operator, 2026-11-18) | Combined. Principles: a unified domain data model with scoped semantic authority (FP-04, A2); execution fit, meaning efficient and fast execution (FP-07, A4); application code kept away from writing or managing SQL text. Libraries as hypotheses: the data-model family (LinkML and relatives, SQLAlchemy, Alembic, pydantic, pyarrow, jsonschema, pglast, SQLGlot, valuesets) on equal footing, with unification allowed to come from connecting existing declarations; DuckDB 2.0 case by case; cachetools 8.0 given prioritized treatment as a cache *design* |
| Reviewer and date | Independent design reviewer (wrote neither the audit, the code nor earlier reviews), 2026-11-18. Recommendations revised by an independent recommendation auditor, 2026-11-18, on the operator's flexibility concern (see the attribution above) |
| Maturity and outcome | Design stage. The review should let the operator plan a separate series: which facts each authority owns and how consumers obtain them, an identity and cache design, the remaining-SQL conversion order, and the place of DuckDB |
| Supported scope and workload | Book-scale document processing through declared data operations, many operations per run; repeated focused reads from a long-lived MCP server (one process, tool calls on worker threads) and from the `ci` command line (one process per command and per page); model changes previewed, replayed and deployed; one operator, several coding agents, one host |
| Baseline | `d78c98765`. Audit revision consumed: the broad audit as refreshed on 2026-11-18 at that source (publication `90467bde0`), with the independent challenger's corrections of the same date ([independent challenge](../evidence/2026-11-18_production-review-inputs/challenge.md)) folded in. The coordinator records the publication commit. **Revision baseline:** `5139eaba3`, consuming the audit's [update of 2026-11-18 at that source](../audit/README.md#update-2026-11-18-5139eaba3) (its status table, topic pages, rebuilt fact-ownership, library-role, identity and cache inventories, and analytical map); the coordinator records its publication commit |
| Excluded | Test code (owned by the test review of 2026-11-17; seams this design touches are named in one line each); the declared-data-operations plan's PE findings (read as current design, not re-owned); Chandra OCR (operator direction) |
| Method and coverage | Static reading. Read in full: the brief, the audit pages, the seven contributor reports, ADR-0131, DESIGN §2 and §B4/§B5 heads, ADR-0124 and ADR-0125 decisions. Inspected in source at the decisive lines: the native capture and its digest (`semantic/data_operation_storage.py:40–140, 695–815, 1095–1135, 1535–1562`), `semantic/metadata.py`, `schema/physical.py:130–200`, `semantic/prepare.py:340–375, 585–625, 950–990, 1015–1035`, `semantic/data_operation_admission.py:270–360`, `semantic/data_operation_identity.py:340–420`, `semantic/python_operation_sources.py` (outline and the slicer), `semantic/python_module_projection.py`, `semantic/file_custody.py`, `_query_custody.py`, `semantic/data_operation_wire.py:40–70`, `semantic/data_operation_read_index.py`, the DuckDB connection sites, `semantic/analytical_kernels.py:15–65`, `semantic/alembic_privileges.py:20–40`, `semantic/target_installation.py:345–356`, `semantic/support_trust_native.py:85–95`. Three bounded read-only helpers mapped (a) the hand-written PL/pgSQL residue, (b) whether validity families are derivable from compiled fields, (c) the cache and holder inventory; their results were checked at the lines this review relies on. Not read: generator bodies for equivalence; `schema/rulelang.py`; `semantic/ontology.py` beyond its use; `schema/stage_b.py`; migration revision bodies; `cli/` beyond the paging entry; `domains/` (not in the snapshot). **Revision coverage (2026-11-18, at `5139eaba3`):** read in full the brief, the audit update's README section and topic pages, its rebuilt inventories, the five lane reports behind it and the recommendation-audit companion. Re-inspected in source at the decisive lines: `semantic/data_operation_storage.py:705–722, 1075–1081, 1127–1142`; `semantic/execution_admission.py:182–203`; `semantic/native_admission_release.py:510–535, 600–625`; `semantic/data_operation_compiler_native.py:468–525, 900–926`; `semantic/data_validity_native.py:270–288`; `semantic/contextual_admission_native.py:185–240, 730–740`; `semantic/definition_admission_native.py:380–420`; `semantic/rich_admission_native.py:1130–1195`; `semantic/data_completion_settlement_native.py:545–566`; `semantic/data_operation_protocol.py:105–135`; `semantic/companion_projection.py:555–640`; `semantic/native_objects.py:140–175`; `semantic/pdf_publication_native.py:470–500`; `semantic/target_installation.py:365–375, 620–640`; `semantic/native_admission.py:40–60`; `semantic/data_operation_read_index.py:18–30`; `semantic/data_operation_projections.py:150–172`; `semantic/metadata.py:28–52`; `semantic/prepare.py:975–990`; `semantic/data_operation_preparation.py:255–265`; `schema/model_explanation.py:418–426`. The independent challenge of the audit update (2026-11-18) was read and its corrections applied; its new precedent sites were checked in source (`semantic/record_policy_completion_native.py:422–442`; the effect declarations in `methods/record_policy.py`, `methods/operation_events.py`, `methods/rich_knowledge.py`, `methods/structural_admission.py`; `docs/adr/0092-ddo-operation-authority.md:27`). Commit history of every file the review cites was listed with `git log d78c98765..5139eaba3`. The frozen revisions N28 and N29 were compared by script (below). Not re-read: the bodies of files with no commit in the range |
| Evidence labels | Source facts: **Interface-checked by source inspection, 2026-11-18**. Every remedy: **Proposed**. Library facts: **documented**, **observed in installed source**, or **probed on synthetic data** (each says which). Nothing is Tested or Measured; no speedup is claimed. The audit's additions carry the same labels; its LinkML facts are observed in installed linkml and linkml-runtime 1.12.1 source, and the `domains/` packs it cites were read from commit `d78c98765` with `git show`. Revision: new source facts are **Interface-checked by source inspection, 2026-11-18**, at `5139eaba3`; line references in unchanged text were refreshed where the code moved; existing labels are kept. One scripted comparison of frozen revision files (N28 against N29, 64-hex strings masked) was run by this reviewer on repository files, read-only; no library probe, test, database or provider was run. Library versions are unchanged in the range (`pyproject.toml` and `uv.lock` have no diff) |

## 2. The assessment in brief

The system's intent is a highly structured representation of documents produced by declared data
operations, with one explicit model from which storage, wire shapes, programs, validity,
authorization and analysis derive, and with work keyed, scoped and invalidated by what that model
declares.

Its core realizes that intent well and must be preserved. One effective operation model is
compiled per release from two authoring routes (ADR-0092), with tracked origins and refusal of
conflicting owners. The semantic request identity is built from the recipe, content-addressed
inputs and implementation slices and excludes the release and the runtime, so results survive a
new release (`semantic/binding_admission_native.py:213`). Typed native programs take relations and
columns from compiled metadata and refuse raw SQL text (`semantic/native_program.py:126–131`).
Generated bytes are kept in custody and deployment imports no generator. File and query custody
make a process refuse instead of silently mixing code.

The pipeline is also deliberately exploratory. Its objective is progressive grounded structure,
with complete records as a stronger outcome (`docs/design/DESIGN.md:62–66`, ADR-0070); useful
partial contributions, competing alternatives, unknowns and unsupported proposals are kept and
represented explicitly (ADR-0062, ADR-0024, ADR-0077; for example `MissingReason`,
`CoverageOutcome` and `UnresolvedBinding` in `model/semantic/core.yaml`, private and alternative
proposals in `model/semantic/data-operation-rich-proposals.yaml`). The target design must keep
that latitude and represent it, in the declared space of behaviours as well as in content. The
constraints this review proposes act on two layers only: the internal consistency of the declared
space of behaviours (a name must have a definition, a dispatch must have a handler) and system
integrity (authorization, guards, provenance, custody). They do not constrain the knowledge the
pipeline discovers, and where a behavioural declaration is not yet known the target says so
explicitly instead of forcing a classification.

Four structural causes explain the problems, and they are connected rather than one:

1. **Governing facts have no declared home.** Which validity family an operation belongs to,
   what a support edge means, which relations a guard covers, which roles exist and who may
   execute what are hand lists (at `5139eaba3` in Python only, inside the generators), and an
   omission fails open
   ([DA-070](../audit/semantic-model-and-authority.md#da-070),
   [DA-071](../audit/semantic-model-and-authority.md#da-071),
   [DA-074](../audit/native-integrity.md#da-074)). Not every absence is an omission: some
   operations deliberately belong to no family. The defect is that the model cannot tell the
   designed state from the forgotten one, and that the forgotten one is treated permissively.
   Several facts that *are* declared are not read
   ([DA-086](../audit/semantic-model-and-authority.md#da-086)), and one intended distinction,
   whether a vocabulary may be extended by packs, is declared only in the earlier model that is
   due to retire (F05).
2. **There is no single compiled model object to read from.** Each consumer composes its own
   LinkML view; physical constraints sit in JSON strings; the effective operation model and the
   LinkML views are not one object generators read together
   ([DA-085](../audit/semantic-model-and-authority.md#da-085), narrowed by the challenger).
3. **Identity answers "which code" by hand or by everything.** One digest over every captured
   generator module and six library versions stands for "the kernel that validated this"; hand
   file lists stand for the code of PDF lowering and of served reads; release and preview
   identities hash whole trees ([DA-068](../audit/execution-fit.md#da-068),
   [DA-069](../audit/execution-fit.md#da-069), [DA-076](../audit/served-claims.md#da-076),
   [DA-082](../audit/execution-fit.md#da-082)). Coarse keys discard valid work; narrow keys
   let stale work through.
4. **Derived artifacts have no holder, and programs become text before their facts are
   recorded.** The native program capture is regenerated on the execution path at every
   admission-side call ([DA-083](../audit/execution-fit.md#da-083)), and the program set is
   listed by hand in several places, then handled as text that is concatenated, patched and
   re-parsed ([DA-081](../audit/semantic-model-and-authority.md#da-081), which now also
   carries the former DA-087).

The first text of this review made the most consequential near-term point an **ordering**: the
hand-written PostgreSQL then remaining held exactly the family and role lists of cause 1, so
converting it before those facts had a declared home would transcribe the lists a second time.
**At `5139eaba3` that has happened** (revision of 2026-11-18). Hand-written SQL text in Python
modules fell from about 2,430 lines to about 180, and the sixteen `.sql` files went to none (about
3,700 lines to about 180 in all; the audit's count, confirmed by its independent challenge), one
small hand-written PostgreSQL block remains and the rest is permitted control SQL or SQLite, and every regenerated admission module resolves its relations and columns
against captured metadata, so a renamed column fails at generation. That is a real gain and part
of the core to preserve. But the generators receive only table metadata
(`semantic/contextual_admission_native.py:175`, `semantic/definition_admission_native.py:47`,
`semantic/rich_admission_native.py:1927`), so every fact that says *which operation* (family,
producer, entry point, profile, role) was written into them as a Python tuple: twelve lists now
hold family membership, each guard begins by returning early for an operation not on its list
(`semantic/contextual_admission_native.py:215`, `semantic/definition_admission_native.py:386`),
and the role-name literals of the deleted SQL files moved into Python (246 occurrences in all
before, 199 now, by the challenge's count). Cause 1 is therefore unchanged in
substance and wider in footprint, and its remedy is no longer an ordering of the conversion but an
**extraction** of the transcribed facts (R07, revised). The design question that extraction must
answer is where an operation fact enters the kernel. The answer this revision adopts, following
the audit's lead, is that it does not enter the generators at all: per-operation facts are
lowered per release into the definition rows the guards already read, and the guards select by
the lowered, declared attribute at run time, as rich admission and policy authorization already do
with a declared effect (`semantic/rich_admission_native.py:1135–1145`;
`semantic/record_policy_completion_native.py:425–441`), and as four families could at once, since
their operations already declare a native effect. Handing the operation model to the generators
instead would put every operation edit into the kernel digest.

Identity evidence also strengthened. The kernel digest now covers 99 captured modules, and one
native revision in the range, N29, changed no generated statement: nine of 585 desired objects
differ, only in digest literals (a scripted comparison by this reviewer of the frozen N28 and N29
files, 2026-11-18; the independent challenge mapped every substitution one to one). It restamped
two provenance digests: the kernel digest, after an edit to a captured renderer input, and the
authoring-source digests recorded in the execution-contract descriptor, after an authoring edit
whose generated output was byte-identical. Edits with no effect on installed statements thus
produced a full native revision, as cause 3 predicts.

**Decision: Revise** (unchanged in this revision). A2 is violated for supported behavior (an
unlisted operation's family premises are silently skipped, now at three levels: classification,
dispatch and each guard's early return; and the model cannot distinguish "no family check applies"
from "not yet classified"), A4 is violated (generation on the execution path, invalidation far
broader than its premise, a full native revision for a change that alters no installed byte, no
cross-process reuse for the command line), and gates G1, G2, G3, G6, G7 and G8 fail in supported
scope. The enclosing architecture needs revision around a preserved core: the request identity,
the typed program compiler with its model-resolved relations and columns, custody, and
PostgreSQL's authority over execution, locks and roles all stay.

## 3. The target design

This section states the target as one account. Section 4 gives the arguments, alternatives and
library mechanisms behind each part.

### 3.1 Authorities and the compiled centre

The target has five kinds of authority and nothing else that is authored:

1. **The LinkML released model** for domain shapes, vocabularies (domain and operational), each
   declaring whether it is closed, pack-extensible or open with known members (R15), physical
   declarations under a typed annotation profile, projections, and the schema of operation
   declarations and of the custom catalogs.
2. **Operation declarations as instance data**, through the two routes ADR-0092 accepts:
   implementation-owned `__data_operation__` literals beside their callables (about 62 modules)
   and declaration-owned model protocols. The Python literals stay where they are; what changes is
   that their grammar and vocabularies are declared in LinkML and checked against that
   declaration, instead of by a hand validator. Declarations that may not be known when an
   operation is first written (its validity family above all) are optional, with a declared
   meaning for their absence (R16).
3. **The native protocol** (JSON Schema draft-7) as a peer authority for wire encodings LinkML
   cannot express, the task lifecycle and the native operation ABI and purposes. It already feeds
   physical value sets through `ph:values_from`, a working cross-formalism derivation.
4. **Typed Python registries** for code-shaped facts: the native program declarations (name,
   schema, signature, language and volatility, purposes, callees, owning family) and the
   generated-output registry. These are authorities because programs and outputs are code
   artifacts, not domain data.
5. **Derived code identity**, computed from declared entry points, for "which code determines
   this artifact". It is not authored at all; it replaces every hand-kept file list.

Everything else is derived. The centre is not one object but three held ones, each identified by
its inputs:

- a **compiled model** per model-sources identity (the captured closure of LinkML schemas,
  protocol and catalogs), composed once by one composer and exposing lazily derived projections:
  merged `SchemaView`, physical and read SQLAlchemy `MetaData`, wire validators, expanded value
  sets, the type resolution for field kinds, Arrow schemas, the role and grant matrix, the
  support-edge traversal table and the operation-declaration validator;
- the **effective operation model** per release, as today, compiled from the compiled model plus
  the operation declarations;
- a **program set** per compiled model and generator code, holding program declarations,
  rendered bytes and identities.

The second, older model (`model/core.yaml`, `system.yaml`, `revisions.yaml` and what is generated
from them) retires after its live consumers move to released-model types.

### 3.2 Declared homes, explicit openness and safe defaults

Every governing fact has **one declared home**, and every dispatch over it is generated from the
declared members with no hidden default. What the declaration must say depends on the layer it
governs:

- **Integrity memberships are closed and complete.** Roles and purposes are LinkML vocabularies
  (`Role` with membership and login properties as member annotations; `Purpose` with its roles);
  table read roles and frontier-guard classification (`guarded` or `exempt`) are declared in the
  physical profile, each with a declared default per schema and per-relation overrides, so a new
  relation is safe without extra ceremony and no default lives in code; execute grants come from
  each program declaration's purposes; shared-stream triggers are selected by the already declared
  `ph:immutability: pending-content`; support-edge kinds form a closed set and an unrecognised
  support reference refuses; task states are read from the protocol lifecycle by every program
  that tests them.
- **Internal consistency is checked.** A named validity family must name its validator program
  unless the family is declared provisional; generation refuses a dangling name; completion
  dispatches on the lowered family instead of every guard selecting itself by an id list; a
  program's callees must be declared programs (R04).
- **Operation facts reach the kernel through the release, not through generation** (revision of
  2026-11-18). Model-level vocabularies (the families and their validator programs, roles,
  purposes, the lifecycle) are generator inputs, as the protocol lifecycle already is for the task
  guard (`semantic/data_operation_protocol.py:117–128`). Per-operation facts (which families an
  operation belongs to, its entry point, profile, forms, dependencies, effects) are lowered per
  release into `sem.data_operation_definition` rows, and guards, validators and dispatch select by
  those rows at run time. Adding an operation to a family then changes the release, not the
  kernel.
- **Operation classifications are three-state, not total.** An operation's `validity_family` is
  optional and may name several families. Named families mean their validators run, in
  conjunction. An explicit `none` is a positive claim that only generic validity applies (outcome,
  revocation, support propagation). Absence, or an explicit `undetermined`, means "not yet
  classified": the operation compiles and runs, preparation reports a non-refusing diagnostic, and
  validity applies a **conservative premise check** that over-invalidates rather than
  under-invalidates (R16). The lowered column is an enum-checked set whose empty and undetermined
  states are distinct.
- **Vocabularies declare their openness** (R15): closed (programs may dispatch on it), pack-extensible
  (members are added per release by packs), or open with known members (any value is accepted;
  only known members carry meaning that consumers may test). Members may be marked provisional.
  `Profile`, `KindUniverse`, `Form`, `SupportEdgeKind`, `Purpose`, `Role` and the task lifecycle are
  closed, as they are today in code; the operation `ownership` description is open with known
  members (today it is free text with sixteen values, and consumers test only `immutable`); the
  free-text `preparation` and `cancellation` descriptions stay unconstrained.
- **Refusal is reserved** for internal inconsistency and omissions in the integrity layer. Where a
  behavioural declaration is undetermined, the stated consequence applies, and the operator decides
  whether some promotion boundary (default-release activation, knowledge publication) should
  refuse it (RC14).

None of these constraints acts on the knowledge content the pipeline discovers. Content keeps its
explicit states for partial, missing, unknown, competing and unsupported results, and a constraint
on selected values never prevents recording what a source says (ADR-0024).

### 3.3 Identity layered by purpose

- **Program identity**: the digest of one program's rendered bytes. **Kernel identity**: the digest
  over the sorted program names and identities that are installed. Generator source and library
  versions are *provenance*, recorded in custody, and key only the generation cache.
- **Validator identity** per validity family, and for the conservative validator that unclassified
  operations receive (R16): the digest over the identities of that family's validator programs and the
  programs they call. An operation in several families carries each family's identity. Receipts record it; replay is gated on it and its
  success is recorded.
- **Read-closure identity** for native reads; a native operation's declared behavior is its own
  program closure's identity, not the whole kernel.
- **Derived code identity** for Python artifacts (PDF lowering, served reads, opaque operation
  boundaries, generators): the static first-party import closure from declared entry modules,
  each module digested by its parsed syntax (comments and layout do not count), plus the versions
  of the distributions the closure actually imports. Function-level slices are used where the
  existing slicer resolves them without unknowns.
- The **release id** covers generated artifacts and the model capture, not generator source.
- **Native revisions follow program identities** (revision of 2026-11-18): a frozen revision
  already records each desired object's statements and normalized catalog form; its delta is the
  set of programs whose identity changed, and a candidate whose delta is empty is not authored
  (RC15).
- **Release-bound inputs are read from the release** (R17): a pack file the release archives is
  read from the archive by every path that attributes its result to that release.
- The semantic request identity, the cut identity and the per-operation fingerprints stay as
  they are.

### 3.4 The cache system

Six in-process tiers and two disk tiers, keyed by those identities, coordinated with cachetools
8.0.1 `condition` single-flight (or a future-based single-flight where failures must be shared),
owned by one small registry module, with the command line crossing processes through
content-addressed files for generated program sets and continuation pages. The execution path no
longer generates anything. Full design: [cache-design.md](unified-domain-model-and-execution/cache-design.md).

### 3.5 SQL out of application code

PostgreSQL keeps execution, locks and roles. Application code does not write or maintain SQL text:
product logic is typed programs reading declared facts; independent controls stay hand-written but
take generated expectations as data arguments instead of spliced text; SQLite scratch stores use
SQLAlchemy Core tables; DuckDB use stays on the relational API with model-derived input schemas.
Frozen migrations and submitted read-only SQL remain exceptions. At `5139eaba3` the statement half
of this is almost done for PostgreSQL (revision of 2026-11-18); what remains is the facts the typed
programs carry by hand, two small text sites, the SQLite stores and the text handoff after
rendering (R07).

### 3.6 Analytical placement

PostgreSQL keeps everything bound to its authority (validity, support walks, authorization,
paging, ranking). DuckDB keeps the three uses where set operations, spill and external sort pay
for themselves, gains certification folds over Arrow replay files, and loses its two uncalled
kernels. Python keeps small object-graph work and numerics. Change impact stops re-encoding
support semantics and consumes the authority's explanation.

### 3.7 Carried assurance

Established results are recorded once and carried while their premises hold: compiled-model
validation per model identity, release-content proof per release and kernel, binding facts from
admitted definition rows, validator reconfirmation per receipt and validator identity.

## 4. Corrective arguments

Each recommendation names its intended behavior, the alternatives considered and why they lose,
the library mechanisms it relies on, and a challenge case.

<a id="r01"></a>

### R01 — One composer and a held compiled model (Q2; DA-085, part of DA-083)

**Diagnosis.** Three near-identical closure routines (`semantic/prepare.py:350–373`,
`semantic/native_call_sources.py:95–117`, `semantic/projection_analysis_products.py:85–107`), a
separate physical closure (`schema/physical.py:166–197`) and further single-purpose views
(`semantic/companion_projection.py:552` from a disk path; `semantic/rule_views.py:402`;
`semantic/conditional_rules.py:178`; `semantic/ontology.py:159, 260, 626`;
`semantic/source_value_native.py:56`). `semantic/metadata.py:32–50` compiles two `MetaData`
projections at import in every importing process; `native_protocol_sources` compiles the physical
model again when not handed metadata (`semantic/data_operation_storage.py:123–136`).

**Target behavior.** One composer turns a model-sources capture into a `CompiledModel` (merged and
induced view, with the project's single `expand_enum` applied to value sets). Projections are
derived on first use and held on the immutable object. The object is held in cache tier T1 by
its model-sources identity, so a candidate and the running model coexist and a changed YAML
source yields a new entry instead of a restart (rule impact RC09). `semantic/metadata.py`'s globals
become accessors.

**Alternatives.** Keeping per-consumer composition loses: every new consumer adds a closure and
cross-view facts have no shared object, which is one reason membership facts fell back to Python
lists. (The value-set expansion kept is the released model's `semantic/ontology.py:328`; the
earlier model's `schema/model.py:333` carries the pack-extensibility rule and retires with R13
once R15 has carried that rule forward.) A single eager module global (today's `metadata.py`) loses: every command pays for it,
candidate and running models cannot coexist, and a model edit needs a restart. A materialized
derived schema file (`SchemaView.materialize_derived_schema`) as the one artifact is a useful disk
form later but leaves each consumer composing projections. The challenger notes that separate
closures partly serve custody (each artifact's identity covers its closure); in the target each
projection still has its own sub-identity (the physical sources id stays), so custody granularity
is kept without separate composition.

**Library mechanisms.** linkml-runtime `SchemaView(schema, importmap=...)`, `imports_closure()`,
`merge_imports()` (observed in installed source by the library contributor); the project's
`expand_enum`, needed because `induced_enum` and the JSON Schema and Pydantic generators do not
expand `inherits`, `include` or `minus` (probed on synthetic schemas by the library contributor,
[data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F6, F7); the project's `schema/relational.py` as the `MetaData` compiler (LinkML's
SQL generators read only three annotations and know no PostgreSQL schemas, checks, triggers or
grants, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F10, so they are not adopted); cachetools `cached` with `condition` for the
holder ([cache-design.md §4 T1](unified-domain-model-and-execution/cache-design.md#t1--compiled-model)).

**Challenge case.** A preview compiles a candidate model while the MCP server serves the running
one: both entries coexist under different identities; nothing pinned to the running model moves.
A model edit that leaves bytes identical produces no new entry.

**Revision of 2026-11-18 (unchanged).** No composition site changed in the range: the sixteen
`SchemaView` construction sites are the same, and `semantic/metadata.py` (no commit) still compiles
two `MetaData` projections at import (`:33–52`), now in 63 importing modules. One holder was added:
the companion projection's captured inputs are held by a content-keyed `lru_cache`
(`semantic/companion_projection.py:561–617, 620`), keyed by the PDF domain contract's captured sources.
It is a sound key and confirms T1's premise that a captured source set identifies a compiled view,
but it composes its own view and compiles the physical model a further time (`:587`), so it is a
fourth per-consumer composition and becomes a T1 projection in the target. One addition from the
audit's recurring findings: release annotations of the semantic model (`cs:` keys) are still
decoded from raw strings by each rich consumer, at 36 sites
([DA-004](../audit/semantic-model-and-authority.md#da-004)). The compiled model exposes them once
as typed values (a boolean annotation as a boolean, a case policy as its enum), so the
`str(...).lower() == "true"` pattern and the near-synonymous class-level `cs:case` and
property-level `case_policy` are read in one place, where their distinction is stated.

<a id="r02"></a>

### R02 — Declare the governing vocabularies and classifications, with their openness (Q1, Q3; DA-070, DA-073, DA-074, DA-086)

**Diagnosis.** The validity family of 27 operations in seven families is a Python tuple rendered
as a `CASE` with no `ELSE` (`semantic/data_operation_compiler_native.py:468–520`); dispatch is a
second tuple with `else_=True` (`semantic/data_validity_native.py:272–288`); the column is an
optional string (`model/semantic/data-operation-physical.yaml:88`). Both lists already existed in
the deleted SQL; the conversion transcribed both. The helper's extraction of all 27 literals found
no compiled field that identifies a family: `profile` is `derivation` for 25 of them, `ownership`
does not separate families, and several operations with family-like ids are deliberately outside
every family. **Family is an authored choice**, so a declared field is needed; connecting an
existing declaration is not available here. The plan defines the lowered column as null "when no
per-kind validator applies" (`docs/plans/declared-data-operations/products-and-support.md:422–423`),
so "outside every family" is a designed state; the defect is that it shares its representation with
a forgotten entry, and that the forgotten entry is treated permissively.

**What is intentionally open here, and what is not.** The declared space of operations is meant to
grow by trying things: an operation may be written before anyone knows which native premises its
results depend on, may later turn out to need two families' checks, and may sit in a release that
includes only some groups. The current grammar already closes its field names, profile, forms and
kind universe (`semantic/data_operation_compilation.py:85, 104–140, 341–348, 1068–1073, 1491–1493`)
and leaves `ownership`, `preparation` and `cancellation` as free text (`:1559–1566`). The target
keeps those closures, keeps those descriptions open, and represents the not-yet-known family
explicitly instead of either refusing it or treating it permissively.

**Target behavior.** A LinkML schema for the Python authoring route's declaration grammar
(`DataOperationDeclaration`) and its vocabularies, each declaring its openness (R15): `Profile`,
`KindUniverse`, `Form`, `ValidityFamily`, `SupportEdgeKind`, `Purpose`, `Role` closed; `Ownership`
open with known members (the members consumers test, today `immutable`, carry declared meaning;
other values remain descriptive and are reported, not refused). Operation literals stay in Python
(ADR-0092's route); the compiler validates each literal against the declaration class with
closed-world validation of field names (as today), and records a warning for recommended but
absent declarations. `_PROFILES`, `_KIND_UNIVERSES` and the hand grammar validator
(`semantic/data_operation_compilation.py:85–188, 330–345`) retire. The compiled dataclasses keep
`Literal` fields for the closed vocabularies and check them against the enum members at import, the
closed-set pattern `semantic/source_value_native.py:55–66` already uses; the open `ownership` stays
a string.

The validity family follows R16: `validity_family` is an optional set of `ValidityFamily` members;
`none` is an explicit claim that only generic validity applies; absence (or `undetermined`) means
"not yet classified", compiles with a non-refusing diagnostic, and receives conservative validity.
Each `ValidityFamily` member names its validator program in a structured annotation, or carries
`status: provisional` while its validator is unwritten (its members are then treated as
undetermined). Dispatch, completion guards and the contextual and completion id lists are generated
from these declarations; a non-provisional member without a validator refuses at generation.

Release composition becomes "the closure of requested operations, mapped to source collections"
(DA-073). The source collection of an operation is derived by static extraction from the captured
collection that includes its literal (`semantic/python_operation_sources.py`), and an
`acquired_by` field is declared only to override that derivation. The manifest names requested
operations or families, so a release that includes only some operations remains the ordinary case.

**Where connecting existing declarations is the lighter route** (no new specification): shared-stream
trigger membership from `ph:immutability: pending-content` (`model/semantic/physical.yaml:1757,
1776`, already in `relation.info`, `schema/relational.py:492`); task-state tests from the protocol
lifecycle (`model/semantic/data-operation-native.yaml:5–14`, already read by the task guard,
`semantic/data_operation_protocol.py:116–160`); the four field-kind type maps from the type
resolution the physical compiler already performs on LinkML type `uri` and `ph:sql_type`
(`model/semantic/physical.yaml:33–36`; `schema/relational.py:79–89, 437–440`); the data-operation
value codec's tags from the LinkML observations vocabulary, as the SourceValue codec does; the
operation dependency graph from the compiled `selected-dependencies` projection
(`semantic/data_operation_model.py:713–725`); companion grouping columns from `cp:role`
annotations.

**The contextual per-operation contract.** `semantic/contextual_admission_native.py:23–50` restates
entry point, profile, forms and preparation that the effective model holds. The challenger notes
it acts as an independent pin when compared with the admitted definition. In the target it is kept
only as a pin between distinct inputs: generated from the declaration captured when the kernel is
authored, compared with the admitted release's definition. If kernel and release are generated from
the same input the comparison is circular and retires.

**Alternatives.** Deriving the family from existing fields is refuted by the extraction; whether it
is derivable from declared input roles (an operation that consumes a trust-bearing cut or a
linguistic premise) was not examined and would make the field an override. Annotations on schema
elements are wrong for operations, which are instances, not schema elements
([data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) A.2). A pydantic-authored metamodel is lighter for the structural grammar alone
and is an acceptable variant if the operator prefers it; it loses on the vocabularies, which SQL
reads through families and edge kinds, so those should be LinkML enums either way. A **required
total classification** with an explicit `none` and refusal of absence (this review's first round)
removes the fail-open state but makes every new operation decide its validity semantics before it
can compile, conflates "not applicable" with "not yet decided" in the other direction, and forbids
an operation in two families; it is not selected. Positive-only `in_subset` membership was rejected
in the first round because it does not fail closed; with the conservative default it becomes safe
where it is convenient.

**Library mechanisms.** LinkML enums with `permissible_values`, whose annotations take structured
values (annotation values are `AnyValue` and load as Python lists or dicts through `SchemaView`,
observed in installed linkml-runtime 1.12.1 by the library contributor, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F1);
permissible values also carry `status` and `deprecated` through `common_metadata`, so a provisional
member needs no custom annotation (observed in the installed 1.12.1 metamodel,
`linkml_runtime/linkml_model/model/schema/meta.yaml`, `permissible_value` and `common_metadata`);
validation of instance data with `linkml.validator.Validator(schema,
validation_plugins=[JsonschemaValidationPlugin(closed=True), RecommendedSlotsPlugin()])`, compiled once per schema and held in
T1 (documented and observed, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) §D); `recommended: true` slots are reported by
`RecommendedSlotsPlugin` with `Severity.WARN`, not as errors (observed in installed source,
`linkml/validator/plugins/recommended_slots_plugin.py`); the JSON Schema plugin also enforces LinkML
`rules` while the Pydantic plugin does not (probed, F8). An open vocabulary uses a slot range of
`any_of` the enum and `string`, since the 1.12.1 metamodel has no openness flag on enums (observed).
Limits: annotations are untyped by default and `instantiates` validation is not enforced in 1.12.1
(F5); cross-record checks are a compiler pass, not a stock plugin.

**Challenge cases.** An operation that genuinely has no family validator declares `none`; it is no
longer indistinguishable from a forgotten one. A new operation whose validity semantics nobody has
worked out yet declares nothing: it compiles, runs and produces results, its derivations are
re-validated conservatively, and preparation lists it as unclassified. An operation that needs two
families' checks lists both. A renamed family member refuses at generation until its validator
program is named or the member is marked provisional.

**Revision of 2026-11-18 (changed).** *What the code did.* The classification tuple and the
dispatch are unchanged (`semantic/data_operation_compiler_native.py:468–520`;
`semantic/data_validity_native.py:272–288`, `else_=True`), and the column is still an optional
string (`model/semantic/data-operation-physical.yaml:88`). The converted guards added ten more
lists, twelve in all ([DA-070](../audit/semantic-model-and-authority.md#da-070) counts them by
reading). Every family guard now begins with `If(operation.not_in(<list>), (Return(),))` and every
family validator returns true for an operation not on its list (for example
`semantic/contextual_admission_native.py:215, 736`; `semantic/definition_admission_native.py:386,
418`). Completion calls all fourteen guards and each selects itself
(`semantic/data_completion_settlement_native.py:548–563`), so a family member missing from a
guard's list skips it. A forgotten member therefore escapes at three levels: classification,
dispatch and each guard. The guards also pin per-operation facts that the effective model already
holds (a twelve-entry factory dictionary, `semantic/contextual_admission_native.py:188–201`;
profile, forms and receipt counts per id, `:234–259`), and one list narrows what the declarations
allow: a contextual query is admitted only from two listed producers, although the scoring
operation declares its query input by kind (`:301–310, 369`; the refusal of a third encoder is the
audit's inference from two texts, not run).

*Where operation facts should enter the kernel.* The generators receive only captured metadata,
and the audit's lead is right that they should not simply be handed the operation model: one
native kernel serves many releases, and reading per-operation facts at generation would bake them
into a release-independent artifact and put every operation edit into the kernel digest, as the id
lists already do. The code already has the alternative at hand. Lowering runs inside the kernel
with the archived effective operation in scope and lowers its dependencies in the same block
(`semantic/data_operation_compiler_native.py:900–926`), and two guards already select by a
declared, lowered attribute: rich admission refuses any operation that declares the effect
`native-rich-knowledge-admission` unless it is `rich.admit`
(`semantic/rich_admission_native.py:1135–1145, 1183–1192`), and policy authorization refuses any
operation that is not of command class `policy` but is `record_policy.authorize` or declares
`native-evaluator-policy-authorization` (`semantic/record_policy_completion_native.py:425–441`),
where the command class itself comes from eligibility predicates, not ids
(`semantic/data_operation_compiler_native.py:530–550`). Four families already declare a native
effect per operation, with its authorization premises (`methods/record_policy.py:70`,
`methods/operation_events.py:328`, `methods/rich_knowledge.py:405`,
`methods/structural_admission.py:132`); contextual, definition and artifact operations declare
none (for example `methods/contextual_scoring.py:130–131`, `"effects": []`). The independent
challenge of the audit update found this precedent; it is wider than the lanes reported. The
revised target therefore is:

1. **Membership is lowered from the declaration.** Lowering reads the operation's declared
   `validity_family` from the archived effective operation, as it reads its dependencies, instead
   of calling `ops.ddo_classify_validity`; the classification program retires. The lowered column
   is a set whose empty (`none`) and undetermined states are distinct (R16). Preparation checks
   each named member against the `ValidityFamily` vocabulary, so a name the vocabulary lacks cannot
   be lowered. For the four families whose operations already declare a native effect, the
   lowered `support_contract` effects are already in the definition rows, so their guards can
   switch to selection by declaration before the family field exists; the family field is new
   only for contextual, definition and artifact operations and for families that have no effect.
   The declaration is kept out of the recipe identity, so classifying an operation
   later does not recompute its results; validity follows the current lowered declaration
   (Proposed; the native owner confirms whether the definition identity must cover it).
2. **Every selection reads the lowered column.** Each family guard and validator tests the
   admitted definition row it already looks up for membership of its family, instead of an id
   list; dispatch is generated from the family vocabulary with no `else`; the live completion chain
   is generated from the same vocabulary. Classification, dispatch and guards then read one fact in
   one place and cannot disagree. The early return inside validators is no longer a selection point
   (they are reached only through dispatch) and goes. The guard name list that completion calls is
   a program list and moves to R04's registry.
3. **Per-operation pins become per-family member requirements.** What a guard now pins per id
   (entry point, profile, forms, receipt counts) a family declares once for its members, as
   structured annotations on its `ValidityFamily` member (required forms or profile, required input
   role kinds, the number of CPU receipts). Preparation refuses an operation that claims a family
   whose requirements it does not meet, which is internal inconsistency, and the guard checks the
   same requirements against the lowered row. The implementation itself is already authenticated
   per operation by the definition's implementation-slice revision, which the guards check
   (`semantic/contextual_admission_native.py:225–236`), so per-id factory pins retire. This is safe
   in the direction that matters: claiming a family adds checks (validity is a conjunction and
   guards refuse), so a wrong claim can cause a refusal but not a fail-open result; the fail-open
   direction is not claiming, which R16 covers.
4. **Privileged effects stay closed.** Where a guard authorizes rather than validates (the
   evaluator-authorization subset, `semantic/data_completion_settlement_native.py:576–587`; the rich
   admission effect), membership is an integrity fact. The privileged effects are already declared
   per operation with their authorization premises; what is still a literal in the guard is the
   one permitted owner (`rich.admit`, `record_policy.authorize`). In the target the effect
   vocabulary member declares its permitted owner operations, the declaration is a generator
   input, and any other claimant is refused, which is the shape these two guards already have. A
   privilege change is rare and should change the kernel.
5. **Transcribed narrowings read the declarations.** Producer restrictions per input role read the
   lowered dependencies and role kinds of the definition rows, so a further encoder that the
   declared roles admit is admitted. Until the lists are extracted, the owner-module constants
   (`GRADE_OPERATION`, `AUTHORIZATION_OPERATION`, `ADMISSION_OPERATION`) are the interim single
   statement, and the inline ids beside them (`semantic/operation_event_native.py:295, 315, 1206`)
   use them.

*Connections added by this revision* (no new specification needed): product member families and
their required fields from the protocol definitions they restate
(`semantic/data_product_admission_native.py:56–90`); encoder failure codes from the Python set
(`semantic/contextual_admission_native.py:653–660` against
`semantic/contextual_encoder_batch.py:19–26`); codec tags in kernels from the codec's constants;
the table read-grant JSON literal from `DEFAULT_READ_ROLES`
(`semantic/native_admission_tables.py:176–184`), until R03 declares read roles. Two earlier audit
identities join this list. The per-predicate qualifier partition is compiled, validated and
archived but read by nothing ([DA-001](../audit/semantic-model-and-authority.md#da-001)); a pack
declaration that governs nothing should either govern (scientific grouping reads the compiled
`ComparisonProjection.partition` where it now keys on `qualification_meaning`) or be retired, and
the reviewer leans to connecting it because the statistics pack declares a non-trivial partition
(owner decision). The decimal expansion bound
([DA-040](../audit/structure-and-invariants.md#da-040)) exists in two modules and not in the
codec or the generated canonicalizer; it becomes one declared limit of the value codec, read by the
Python codec and by the canonicalizer generator, so an oversized exponent is a classified value
refusal on both sides.

*Did regeneration close something open by intent?* By the audit's openness table, the closed
sets that are new in the range (public reads disclose only `ordinary` and `source` kinds; a native
selection has exactly four keys) are integrity closures, declared and sound. The other closures
(producer ids, per-id profiles, encoder codes, endpoint scope, partition values) were already
closed in the SQL they replaced; the conversion transcribed them. No intended openness was newly
closed, but the existing narrowings moved into Python generator code, where they are less visible
and now part of the kernel digest.

**Revision challenge cases.** An exploratory operation declares no family: no guard selects it,
completion applies the generic checks (product validations, output witnesses), validity applies
the conservative check, and preparation lists it. An operation claims `contextual` with a form the
family does not admit: preparation refuses and names the family requirement. A family member's
entry point is renamed: the release changes and the kernel does not; the implementation slice
authenticates the new code. A third query encoder that the declared roles admit: admitted.

<a id="r03"></a>

### R03 — A typed physical profile (DA-074, DA-085)

**Target behavior.** Physical annotations take structured values instead of JSON strings
(`ph:foreign_keys`, `ph:checks`, `ph:indexes`; decoded today at `schema/relational.py:297,
548–563`), typed by profile classes (`PhysicalRelation`, `PhysicalColumn`, `ForeignKey`, `Check`,
`Index`) written as ordinary LinkML classes, and checked once per compiled model by validating each
element's annotation dictionary as an instance of its profile class. The integrity
classifications (frontier guard; read roles) are declared for every relation in a guarded schema
through a **declared schema-level default** (guarded schemas default to `guarded`; each schema
declares its default read roles) with per-relation overrides (`exempt`; explicit read roles). A
relation therefore always has a declared classification, absence at the relation level means the
schema's declared default rather than a code default, and a forgotten exemption fails safe (an
over-guarded write refuses visibly). These are system relations: domain packs add classes and
properties as registry rows without physical DDL (`docs/design/DESIGN.md:1208–1222`), so trying a
new record, product or relation kind in a pack touches none of this profile.

**Alternatives.** Keeping JSON strings works but keeps the constraints invisible to LinkML tooling
and checkable only by custom code. `in_subset` for guard membership has no declared default and
leaves an unlisted relation unguarded. A required per-relation slot (the first-round proposal) is
equally safe but adds ceremony to every new native relation for no further protection.

**Library mechanisms and limits.** Structured annotation values (F1); validation through
`Validator` with a closed JSON Schema plugin; class annotations are not inherited and `slot_usage`
replaces rather than merges inherited slot annotations (probed, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F2, F3), so the
reader resolves inheritance by walking `class_ancestors`. About fifty lines of glue
([data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) A.3, inference).

**Revision of 2026-11-18 (unchanged).** The two model edits in the range add no annotation
encoding; all 84 `ph:read_roles` annotations are still the empty list; the frontier guard is still
a twelve-name tuple (`semantic/data_operation_storage.py:1952–1965`), now rendered by the typed
trigger constructor. The table-admission module restates the default read roles as a JSON literal
(`semantic/native_admission_tables.py:176–184`), which the schema-level default replaces.

<a id="r04"></a>

### R04 — A typed program registry, carried from generation to installation (DA-081 including the former DA-087)

**Diagnosis.** The program set is held in several hand lists that must agree: `native_protocol_sources`
(`semantic/data_operation_storage.py:139–567`), the concatenation tuple in `native_sql` (37 named
artifacts plus two appended, `:753–812`), `capture_native_authoring_inputs`
(`semantic/native_products.py:131–153`), the installation table (`semantic/target_installation.py:209–231`)
and a provider order (`:302–314`). The required-set check refuses missing or duplicated artifacts
but accepts extras, and it already omits six artifacts that `native_sql` concatenates (challenger
§4), so a missing one surfaces as a `KeyError` rather than a classified refusal. After rendering,
facts the program objects held are recovered from text: grants assigned by matching names in a
re-parsed kernel (`:1873–1914`), the inventory re-parsed (`semantic/native_inventory.py:83–158`),
entry points renamed by a parse-and-reprint pass (`:715–748`), scratch DDL made by string
replacement (`semantic/native_authoring.py:293–313`).

**Target behavior.** Each generator registers program declarations: name, schema, signature (from
the call binding where one exists), language, volatility and security, purposes, callee names and
owning family. The registry is the one list. Generation renders each program once; its identity is
the digest of its bytes. Order is a topological sort over declared callees, refusing a callee that
no program declares; this also produces the provider order for SQL-language bodies, which bind
their callees when created. Installation consumes per-program text with a known name and signature,
so nothing re-parses a concatenated script to find functions. Grants are generated from purposes.
The wire wrapper and implementation names are generated from one declaration. Scratch tables are
produced from compiled `Table` objects. A descriptor program, generated last, carries the program,
kernel and validator identities as literals; guards call it instead of having a digest spliced into
their bodies. The facade outputs join a self-checking generated-output registry of the
`schema/generate.py:540–578` kind, retargeted to the released model.

**Typed forms to add.** The helper established that the compiler can already express trigger
functions (`semantic/closure_native.py:45–83`) and `GRANT`/`REVOKE` (`pglast.ast.GrantStmt` at
several sites) but not `CREATE TRIGGER` (only f-strings, `semantic/target_installation.py:326–374`,
`semantic/data_operation_storage.py:1929, 1954`) or `CREATE VIEW` (`semantic/pdf_publication_native.py:490–535`).
Two finite forms close the gap: a trigger statement built from `pglast.ast.CreateTrigStmt` with the
relation taken from compiled metadata, and a view built from `pglast.ast.ViewStmt` over a Core
`select`.

**Alternatives.** Keeping text with after-the-fact verification works (each transform verifies
preservation) but keeps several sources of truth and repeated parses that grow with owners per
script. Deriving the set by scanning modules for generator functions without a registry hides the
list instead of declaring it.

**Library mechanisms.** pglast AST nodes and `RawStream` printing (observed in the project's use);
SQLAlchemy `CreateTable` and `Table.to_metadata()` for scratch tables; networkx
`lexicographical_topological_sort`, already pinned and used (`semantic/graph_runtime.py`).

**Test seam.** Native authoring fixtures that assemble the kernel by name list move to the registry.

**Revision of 2026-11-18 (partly delivered).** *Delivered:* the two typed forms. Triggers are
built from `pglast.ast.CreateTrigStmt` on a captured relation by `native_before_trigger_sql`
(`semantic/native_objects.py:154–175`, `4760982d8`), now used for the frontier-guard and
shared-stream triggers; published PDF views are `pglast.ast.ViewStmt` over a Core `select`
(`semantic/pdf_publication_native.py:470–495`, `a9c594d48`), exactly the form proposed. Authoring
scratch tables are retargeted on the parse tree instead of by string replacement
(`semantic/native_authoring.py:303–328`, `759dd837f`). These leave the target. *Remaining and
wider:* the hand lists grew by hand (91 capture artifact names, 94 in the required set, 28 module
names in the authoring capture list, `semantic/native_products.py:134–164`); the six artifacts
`native_sql` joins that the required set lacks are the same six; grants are still assigned by
matching names in the re-parsed kernel (`semantic/data_operation_storage.py:1887–1928`); and one
new text dependency appeared: the admission guard emits boundary comments around its catalog checks
and `catalog_checks` recovers them by substring, with literal SQL fragments as fallback anchors for
older frozen guards (`semantic/native_admission.py:42–82`, `1b643e7ed`). For guards generated in
the current process the program objects know those boundaries, so the registry carries the
catalog-check part as its own declared sub-program and nothing searches comments. For frozen
guards, whose authenticated bytes are replayed, text is legitimate; the boundary is recorded once
in the frozen revision when it is frozen, and the fallback anchors remain only for the revisions
already frozen without it. Digest literals are spliced into program bodies; at N29 nine desired
objects changed only in such literals (the comparison under R05). The descriptor program proposed
above is what lets an identity change rewrite one object instead of every body that embeds it.

<a id="r05"></a>

### R05 — Identity from declared dependencies (Q4; DA-068, DA-069, DA-076, DA-078 part, DA-082, DA-083 custody)

**Diagnosis.** `native_source_digest()` hashes every captured `native/*` artifact including whole
generator modules and six library versions (`semantic/data_operation_storage.py:703–713`); it keys
seven consumers (descriptor check, release admission, read pin, completion seal, receipt
validator, each native operation's declared behavior, the readiness watermark). PDF lowering is a
hand list of 70 files and 14 libraries, too narrow and too broad (`semantic/pdf_lowering.py:15–104`).
Served reads use hand lists (`_query_custody.py:17–127`; `semantic/demand_queries.py:117–124`).
Opaque boundaries for construction and formal operations hash whole files and library versions
(`semantic/characterization_ports.py:47–193`; `semantic/formal_products.py:688–756`). The finest
existing identities are unused for this: each program's generated bytes are captured, and the
module meaning projection ignores formatting (`semantic/python_module_projection.py:110–120`).

**Target behavior.** The identity layering of §3.3. Concretely:

- the descriptor check, release admission and the read pin compare kernel identity (program bytes);
- the completion seal and receipts carry the validator identity of each of the operation's families, or of the
  conservative validator for an unclassified operation; the replay gate compares
  it, and a successful replay is recorded per receipt and validator identity by a routine that can
  write, outside the stable validity function (R11);
- each native operation's declared behavior names its own program closure's identity, so its
  recipe changes only when its programs change;
- the watermark's kernel component becomes the read-and-validity closure identity (the remaining
  watermark granularity question is R10's premise, not this one);
- PDF lowering identity is the identities of the PDF programs plus the derived code identity of the
  Python lowering entry modules; served-read identity is the derived code identity of the read entry
  modules plus the read programs' identities; opaque boundaries use derived code identity for code
  and content digests for grammars and rule data files;
- code custody (query custody generalized) loads the derived closure's modules, compiling exactly
  the hashed bytes, so recorded module bytes and imported code cannot diverge (DA-083's hermeticity
  gap);
- the release id covers generated artifacts and the model capture; generator provenance is
  recorded beside them.

**Alternatives.** Keeping the whole-capture digest is safe and fails A4 (every docstring edit or
library patch invalidates admission, reads, receipts and watermarks). Hand lists with completeness
tests stay hand lists. A runtime-recorded import closure misses modules imported earlier by other
code. Function-level slices everywhere are finest, but the existing slicer refuses unknowns on
dynamic code, so they are used where they resolve and the module closure is the fallback.

**Library mechanisms.** Python `ast` (the existing `admitted_operation_module_meaning` pattern);
the closed-source extractor (Griffe, LibCST, astroid) already used for operation slices
(`semantic/python_operation_sources.py:1063–1140`); `importlib.metadata.packages_distributions()`
and `version()` to map imported top-level packages to distribution versions (standard library,
documented).

**Challenge cases.** A generator change that changes semantics changes bytes, so it changes the
program identity; there is no semantic change without a byte change in what is installed. A
pglast or SQLAlchemy patch that changes rendering changes bytes and so identity; one that does not
changes nothing downstream. A served-read helper importing a module through `importlib` by string
would escape the static closure: such imports are refused by code custody's finder for covered
packages. Where the closure computation meets a dynamic import it cannot resolve, the served read
still runs but its identity is incomplete, so its result is neither cached nor offered as a
resumable continuation; this is ADR-0092's rule that unknown determinants withhold reusable
identity, and it keeps an exploratory served helper usable without letting it be reused on a
guessed identity. A docstring edit
in a closure module still changes the module's syntax projection (docstrings are syntax); stripping
docstrings is a possible refinement, not required.

**Revision of 2026-11-18 (changed: strengthened, with one design consequence).** *Evidence.* The
capture now holds 99 distinct Python modules by the audit's stated method (about 95 at
`d78c98765` by the same method), four joined in the range, and the digest still keys the same seven
consumers (`semantic/data_operation_storage.py:712–722`). The shared seal builder of N27
(`b294ab4e2`) removed one definition that could drift, and its `kernel` field is still the whole
digest, so it did not narrow the key. Most decisively, the consequence this recommendation
predicted was observed once. This reviewer compared the frozen revision files
`target_alembic/versions/semantic_ddo_pe_n28_native.json` and `..._n29_native.json` by script on
2026-11-18: both hold 585 desired objects with the same identities; nine differ, and none differs
once 64-hex strings are masked; the two admission files are equal under the same masking. The
independent challenge of the audit update mapped the substitutions one to one: one kernel-digest
pair in seven functions, one renderer-pin pair in `ddo_pdf_search_pin`, and 17 digests inside
`data.execution_contract_descriptor`, eight of them body hashes of the changed functions and the
rest source digests of four `authoring/*` modules. Two edits caused it: `477c82762`, a
construction helper in `semantic/native_source_view.py`, captured whole as a PDF search renderer
input, moved the kernel digest and the pin; `1b643e7ed`, the typed catalog verification that the
plan describes for N29 (`docs/plans/declared-data-operations/postgresql-realization-and-retirement.md:459–463`),
changed authoring modules whose generated output was byte-identical, which is itself good evidence
that the conversion preserved behavior. So the execution-contract descriptor's authoring-source
list (`semantic/native_products.py:54–170`) is a second provenance digest stamped into a deployed
object. Under this recommendation both are provenance: recorded beside the frozen revision, not
spliced into deployed bodies, so neither edit changes a program's bytes, no identity moves and no
revision is authored. This is one instance of digest-only churn; how often it recurs was not
established.

The diagnosis also has an accepted-decision basis that the first text did not cite: ADR-0092 states
that "no broad runtime digest is a recipe fallback" (`docs/adr/0092-ddo-operation-authority.md:27`),
while each native operation's declared behavior is `"ddo-native-v1:"` followed by the whole kernel
digest (`semantic/data_operation_storage.py:993`), so every native operation's recipe moves with
it (inferred tension; the ADR's carve-out for release-bound execution attestation covers the seal and
receipts, not the recipe). Naming each operation's own program-closure identity instead, as above,
resolves it.

*Design consequence of the frozen-revision form.* Each frozen revision stores, per desired object,
its identity, its rendered statements and its server-normalized catalog form with ACL, plus the
operations that move the predecessor state to it (N29 lists nine). So the per-program granularity
this recommendation asks for already exists at freezing time; only the kernel identity is coarse.
That settles what a program identity should key. It keys the program's rendered statements, which
generation produces without a server and which the frozen file already records; the
server-normalized catalog form stays the admission authority for drift, as today. The kernel
identity is the digest over the sorted (object identity, program identity) pairs of the desired
set, computable from the frozen file itself. A revision's operations are then exactly the objects
whose program identity changed, and a candidate with none is not authored (RC15). The audit notes
that every revision also freezes the full catalog state again (8.5 to 10.6 MB each, about 206 MB
for N14 to N29 as ordinary Git blobs); content-addressing frozen objects by program identity would
let revisions share unchanged bodies, but that is a lifecycle and storage decision outside this
review's focus, noted for the owner, not recommended here.

*Added consumer.* An operation fact edit would, under R02's revised route, change the release and
not the kernel; so with this recommendation and R02 together, neither operation edits nor
byte-identical generator edits reach the kernel identity. Only program bytes do.

<a id="r06"></a>

### R06 — The execution path generates nothing (DA-083; review finding F01)

**Diagnosis.** `require_data_operation_native(connection, prepared)` receives the prepared release
and ignores it: it calls `native_source_digest()` twice with no arguments, regenerating the whole
capture from the checkout, and compares the result with the installed descriptor
(`semantic/data_operation_storage.py:1116–1131`). Yet the release already records its kernel digest:
`native_digest_from_dependencies(dependencies)` computes it from the release's captured artifacts
(`:1069–1070`, used at `semantic/prepare.py:1024–1030`), the release row stores `native_kernel_digest`
(`model/semantic/data-operation-physical.yaml:22`), and release admission compares it with the
installed descriptor (`semantic/data_operation_compiler_native.py:998–1093`).

**Target behavior.** The per-acquisition check compares the installed descriptor with the kernel
identity the prepared release records, a value already in hand. No generator runs on port
acquisition, cached-port recheck, publication-port acquisition or definition admission. Working-tree
drift of Python code is detected by code custody (restart), as for served code; drift of the
installed kernel against the release is still refused. The demand export reads its wire schema from
the compiled model's protocol projection (`serve/demand_export.py:281`).

**Alternatives.** The audit's lead, a holder for the capture under file custody, would still make
every acquisition depend on generation and on the checkout; it is right for authoring (T2) and
unnecessary on the execution path.

**Challenge case.** A process that imported generator modules, then had them edited, then acquires
a port: the installed kernel still matches the release, so acquisition proceeds with the code the
release was prepared with; the edited generator is used only by authoring commands, which refuse
through code custody.

**Revision of 2026-11-18 (unchanged; strengthened).** The function is unchanged and moved to
`semantic/data_operation_storage.py:1127–1142`: it calls `require_native_execution` and then
`native_source_digest()` twice. The release's recorded digest is at `:1080–1081` and
`semantic/prepare.py:1025–1031`. What the revision adds: `require_native_execution`
(`semantic/execution_admission.py:182–203`) runs the generated `data.require_execution_release`,
whose archived-projection check already requires the release's archived native digest to equal
the installed descriptor and refuses otherwise (`semantic/native_admission_release.py:516–533,
609–622`). So by the time the Python comparison runs, the installed kernel is already known to be
the release's; the two rebuilds add only "the checkout equals the installed kernel", which is
working-tree drift and belongs to code custody. The target is therefore simpler than first
written: delete the two calls and return the release's recorded digest (or the descriptor's). The
capture is larger per rebuild than at `d78c98765` (about 46 generator invocations, and the
`*_native.py` generator modules grew by about 28% in lines by the audit's count), so the work
removed grew; its time was not measured.

<a id="r07"></a>

### R07 — The remaining PostgreSQL work: extracting the transcribed facts, and the small text residue (Q5; DA-084, DA-086, DA-070, DA-074)

**Revised 2026-11-18 at `5139eaba3` (changed).** The first text of this recommendation, written at
`d78c98765`, gave the conversion of the then-remaining hand-written PostgreSQL a target and an
order: convert each module only after the facts it holds had a declared home, so that the family
and role lists would not be transcribed again. That order is overtaken. The modules were converted
first, and the lists were transcribed into the generators as Python tuples; the original table is
recoverable from Git at `c25cada3f`. What the conversion achieved is substantial and is kept:
hand-written SQL text in Python modules fell from 2,423 to 183 lines by the audit's stated method (a
syntax-tree count of string constants holding two or more uppercase SQL keywords; it undercounts
lowercase or fragmented SQL), the sixteen `.sql` files went to none (about 3,700 lines to about 180
in all, by the audit's independent challenge), loaded `.sql` files fell from ten to none, splices into hand-written bodies from
eleven to none, and every regenerated module resolves relations and columns against captured
metadata, so ADR-0131's "propagates or refuses" now holds for relations and columns
([DA-084](../audit/boundaries-and-composition.md#da-084)).

The recommendation is therefore no longer about converting statements. It is about **extracting
the facts the converted programs carry by hand** to the declared sources R02 names, and about the
small residue of text. Per category:

| Category | At `5139eaba3` | Target | Order and cost |
|---|---|---|---|
| Validity-family membership and guard selection: twelve lists, early-return guards, a default-true dispatch ([DA-070](../audit/semantic-model-and-authority.md#da-070)) | Python tuples in nine generator modules and the classification program | Declared, lowered per release from the operation's declaration; every guard, validator and dispatch reads the lowered column (R02 revised, R16) | **Step A.** Highest consequence. Needs the optional `validity_family` field and the `ValidityFamily` vocabulary; one change to lowering; one predicate change per guard (mechanical once the column exists). One native revision for the batch, and the release archive gains a field, so releases are prepared once more. Can land before R16's conservative program: it already removes the omission-by-list failure for every operation that declares its family, and leaves the undeclared case visible as a diagnostic |
| Per-operation pins and narrowings: factory dictionaries, per-id profiles, forms and receipt counts, producers per input role | Dictionaries and literals per module (53 entry-point lines in 15 files) | Per-family member requirements declared on the family member; producer restrictions read the lowered dependencies and role kinds (R02 revised, item 3 and 5) | With step A, family by family inside the same revision |
| Privileged-effect owners: the evaluator-authorization subset; the rich admission effect | Ids | An owner declaration on the effect vocabulary member, read at generation; other claimants refuse (R02 revised, item 4) | With step A |
| Role names, purpose map, execute grants, principal restrictions, application schemas, private kernels ([DA-074](../audit/native-integrity.md#da-074)) | 199 role-name occurrences in 47 Python modules (they moved from the deleted SQL files; 246 in all before); the purpose map written twice (`semantic/data_operation_storage.py:1899–1907`; `semantic/closure_native.py:174–181`); new tuples (`semantic/native_admission_tables.py:27–32`; `semantic/native_admission_principals.py:8–16`) | `Role` and `Purpose` vocabularies; grants generated from program purposes (R04); schemas from `MetaData` | **Step B**, once the vocabularies exist (R02); independent of step A. An interim consolidation costs nothing in design: every literal reads the existing constants (`PURPOSE_ROLES`, `DEFAULT_READ_ROLES`) now, as `semantic/native_admission_functions.py:149` already does, so step B has one source to move |
| Frontier-guard membership | Twelve-name tuple, now rendered by the typed trigger constructor | Schema-level default with `exempt` overrides (R03) | With R03 |
| Facts already declared and not read: shared-stream triggers (`ph:immutability`), task and record state literals (21 quoted `pending` or `running` in eight kernel files, at both commits), kind-universe literals (43 lines), codec tags, product member families (protocol), encoder failure codes | Literals | Read the declaration: `relation.info["immutability"]`; the lifecycle projection, as the task guard already does (`semantic/data_operation_protocol.py:117–128`); the typed universe literal, as `semantic/support_trust_native.py:91` does; the codec constants; the protocol definitions; the Python set | **Now.** Each connection has a working pattern in the code. Batch them into one native revision, or into step A's |
| Paths into the lowered `support_contract` (`["capabilities"]["prepared_factory"]["entrypoint"]` and others) | Free strings; the read boundary types the column `dict[str, Any]` (`semantic/native_definition_projection.py:31–42`) | The typed read boundary takes its shape from the effective model's `capabilities` dataclass, so a renamed property fails at generation | With step A, which reads these rows |
| Hand-written PostgreSQL outside the permitted kinds: the TEMP grant (`semantic/target_installation.py:623–637`, a `DO` block by concatenation with quote escaping), the one real item | Text | The grant as a typed program (the compiler already builds `GRANT` and `REVOKE` nodes; the database name is the one dynamic part) | Independent, small |
| The native fitting path (`evaluate/operation_fitting.py:530–620`, four `text(...)` calls) | No caller in `src`, `tests` or `scripts`; it calls `eval.*` functions defined only in the unconsumed `semantic_alembic/` tree, none in the deployed `target_alembic/` state; yet it is listed in a hand-kept implementation boundary (`evaluate/declared_operation_events.py:46–57`) | Retire (R13), and leave the boundary list | Independent ([DA-080](../audit/boundaries-and-composition.md#da-080), per the audit's independent challenge) |
| Independent control SQL (84 lines: catalog and server observation, a qualification probe, the submitted-SQL validator's catalog reads) | Hand-written by design; the splice at a role check is gone (`9364a5b88`) | Kept; expectations and role names as data arguments | Role names as data with step B |
| `literal_column(` (37 sites in 16 files, mostly identifiers, three small SQL literals) | The route past the compiler's refusal of raw text (`semantic/native_program.py:128–129`) | Identifiers taken from metadata where they name a relation or column; the three literals become typed expressions | Independent; by code review, no new lint |
| Text handoff after rendering, including the new comment-boundary recovery | Concatenate, patch, rename, re-parse | R04 | R04 |
| Free callee names (1,113 references, 260 distinct, against 887 references at `d78c98765`) | Bound at installation; checked by `plpgsql_check` during authoring | Checked against the program registry at generation | With R04 |
| The model preview's SQL change explanation, still rooted at the removed `semantic/sql` (`schema/model_explanation.py:413–460`) | Reports "no SQL change" for changes to generated SQL | Explains the difference between the two generated-SQL snapshots the preview already holds ([DA-080](../audit/boundaries-and-composition.md#da-080)) | Independent; it can mislead an operator now, so early |
| SQLite stores (59 lines, 58 execute sites, unchanged in the range) | Text built by concatenation, including field names in `json_extract` paths (`semantic/data_operation_read_index.py:20–27`) | SQLAlchemy Core over SQLite with private declared `Table`s; the certification fold to DuckDB (R12) | Independent; RC02 decides whether the rule covers them (F04) |
| DuckDB | No SQL text | Unchanged | — |
| Frozen migrations; submitted read-only SQL | Exceptions | Unchanged; the release-side authored-SQL machinery that has no supplier retires (R13) | — |

**Why this order.** Priority follows consequence: the family lists fail open, so step A comes first
among the extractions, and the connections of already-declared facts can go at once because each
has a working pattern and costs one predicate change. Prerequisites follow capability: step A needs
only the family field and vocabulary; step B needs the role and purpose vocabularies; neither waits
for the ownership vocabulary, the grammar migration or derived source collections. Each extraction
changes program bytes, so it costs a native revision; while every revision freezes a full catalog
snapshot, batching extractions into few revisions is worth doing, and RC15 removes the revisions
that change no byte.

**Alternatives.** Leaving the lists where they are with a test that they agree (they agree today:
the audit's scripted set comparison found twelve of twelve contextual ids) keeps the omission point
and keeps every membership edit in the kernel digest; acceptable only as an interim guard. Moving
the lists into one shared Python table read by every generator (the pattern of
`STRUCTURAL_REPORT_PRODUCERS`, `semantic/declared_structural_admission.py:276`) removes
disagreement between lists but keeps membership outside the declaration and inside the kernel;
it is a reasonable interim step if step A is delayed, not the target. Passing the effective
operation model into the generators makes facts derivable at generation but bakes per-release facts
into a release-independent kernel and puts every operation edit into the kernel digest; rejected
(R02 revised). Classifying the residue as a fourth permanent exception, or encoding PL/pgSQL in
LinkML (ADR-0131's rejected option 2), still lose.

<a id="r08"></a>

### R08 — One declared support-edge meaning and one walk (DA-071)

**Target behavior.** `SupportEdgeKind` (use, episode, population, original) is declared with a
structured traversal table per purpose (validity; lock and scope superset) and the reference-to-node
mapping and scope-key rule. The validity edge program (`semantic/data_validity_native.py:88–240`) and
the support walk (`semantic/data_operation_projections.py:117–242`) are generated from that table.
Change impact stops re-encoding the walk: revocation causes come from an explanation output of the
validity closure program (per reached node, valid or the revoking edge and selector), produced in the
acquisition transaction, and the operation-level "which operations changed" comes from the compiled
`selected-dependencies` projection instead of `semantic/change_impact.py:157–193`. The trust-scope key
has one definition, `ops.ddo_scope`. `_revocation_causes` and its two private mappings retire. The
reference-to-node mapping covers every declared reference kind and refuses an unrecognised one,
replacing today's open default that classifies any reference that is neither an original nor a use
as an episode (`semantic/data_operation_projections.py:117–129`).

**What this closes and what it leaves open.** Support edges are provenance among native rows (uses,
episodes, populations, originals); validity, revocation and lock scope must know every kind, so the
set is closed by purpose and a new kind is a native schema change in any case. Knowledge relations,
pack predicates, proposed links and alternatives are not support edges; they stay open in the packs
and in the content model and are untouched by this recommendation.

**Alternatives.** Moving change impact's walk to DuckDB over exported edges re-hosts the third
encoding rather than removing it (the DuckDB tie-breaker of [DuckDB report](../evidence/2026-11-18_production-review-inputs/library-duckdb.md) §G prefers removal).
Keeping three encodings with a cross-check test leaves three places to edit per edge kind.

**Challenge case.** The scope walk is deliberately a superset of validity; generating both from one
table with two traversal profiles keeps that distinction explicit instead of erasing it.

**Revision of 2026-11-18 (unchanged).** The validity program, change impact and the trust-scope
program have no commit in the range, so the disagreement stands. `_support_walk` moved to
`semantic/data_operation_projections.py:171` with its own `_reference_node` and the open `episode`
default (`:156–169`), and now has six callers; its new disclosure checks read declared attributes
(`public_disclosure`, kind universe), which is sound. A fourth, narrow traversal is now a typed
program: the episode lineage walk of source admission follows only `support_derivation_id` edges
(`semantic/source_admission_native.py:1129–1135`). It serves one purpose; under this
recommendation it becomes a third traversal profile of the same declared table if its owner
confirms it must agree with validity, and otherwise stays a named, single-purpose walk.

<a id="r09"></a>

### R09 — The cache system (Q7)

See [cache-design.md](unified-domain-model-and-execution/cache-design.md). Summary of choices: T1 compiled model and T2 program set as
count-bounded `LRUCache`s wrapped by `cached(..., condition=Condition(RLock()), info=True)` with
negative caching of deterministic build errors; T3 releases and archives bounded by retained bytes and
keyed by database identity instead of engine object; T4 served results as a byte-and-count bounded
`LRUCache` subclass with a future-based single-flight that shares failures, keyed by query,
implementation identity, authorization scope and a declared reuse basis; T5 CPU runtimes bounded by
declared footprint; T6 memos on `cachetools.func.lru_cache` and `cached` with `condition`; a sixty-line
owner module for registration, statistics, settings-driven sizes and event clears; and two
content-addressed disk tiers (program sets; continuation pages) for the command line. GPU residency and
the execution host keep their lifecycles (ADR-0125). About 55 cheap `functools` caches stay.

**Revision of 2026-11-18 (unchanged).** No cache key, bound or invalidation premise of the design
moved: the query cache, the archive cache, the grammar memos, the spaCy holder and
`semantic/metadata.py` have no commit in the range, and cachetools is still pinned at 7.2.7. The
new content-keyed companion-projection holder supplies part of T1 for one consumer; the removal of
the per-request CPU global (`5c5443d16`) closes a shared-state hazard outside the tiers; the native
capture, the subject of T2 and of R06, is unchanged and larger. The cache document records these
deltas.

<a id="r10"></a>

### R10 — Served-read reuse basis and the watermark premise (DA-075, DA-078)

**Target behavior.** Each served query may declare its reuse basis, `cut` or `content`; a query that
declares nothing uses `cut`, the basis that is sound today, so a new or exploratory served query
needs no declaration. Continuation pages
reuse across CLI processes now (cut-keyed, sound because the cut pins frontier, trust snapshot and
visibility, and authority is re-acquired per call). A query may declare `content` (frontier content
stamp, release, runtime, selection, implementation, authorization scope, without the read instance)
only after the native owner establishes that its derived rows are a function of frontier content; the
identity-exclusion comparison already relies on that premise. The readiness watermark drops the kernel
component (R05); narrowing it from "every transitive prerequisite operation by source" to the declared
role producers is proposed, subject to the native owner's soundness argument, because binding remains
the authority and a conservative watermark cannot admit a wrong result.

**Alternatives.** Content keys everywhere now: unsound until the premise is settled. Keeping read-instance
keys only: the command line never hits.

**Revision of 2026-11-18 (unchanged).** The cache key sites have no commit in the range. The
watermark gained a role-matched component for dependency-free operations
(`semantic/data_operation_projections.py:1781–1809, 1919–2059`); it is the first local-wake
component that uses declared roles, which supports the role-granular direction, but it adds to the
watermark rather than replacing the operation-granular prerequisite component, and the kernel
component remains (`:2184–2191`), so a restamp such as N29 advanced every watermark. A new read
boundary field, `public_disclosure`, was added; whether it enters the cut pins was not traced and
matters to the cut-keyed continuation premise (the native owner confirms it with the cut's pins).

<a id="r11"></a>

### R11 — Carried assurance (Q8; DA-033, DA-068 replay)

**Target behavior.**

- Release-content proof: admission checks the finalization receipt and the deployment-admission receipt
  for (release id, physical id, descriptor digest, kernel identity) and skips re-hashing every archive
  input on each acquisition; the full re-proof stays available as an explicit verification command and at
  activation. Lapse: any of the four identities changes. This needs the operator's trust decision (DA-029's
  premise that definer roles are trusted already applies) and is rule impact RC08.
- Binding: `ops.ddo_require_binding` and population selection read the admitted definition rows, which
  already hold the binding expression and identities, instead of parsing and hashing
  `data_operations.json` per call (`semantic/binding_admission_native.py:232–251`;
  `semantic/population_acquisition_native.py:906–921`).
- Validator replay: recorded per receipt and validator identity; lapses when the family's validator
  identity changes.
- Established product validity: keyed by the validator asset's content identity rather than the release
  (the audit's row; the PE item is owned by the DDO plan and is affected, not re-owned).
- Model validation (profile and consistency checks, declaration validation, the list of unclassified declarations) runs once per compiled model and is
  carried by the compiled-model object.

**Challenge case.** A superuser alters archive bytes despite immutability triggers: per-acquisition
re-hashing would detect it, the target detects it only at explicit verification or activation. That is the
trust trade the operator decides.

**Revision of 2026-11-18 (unchanged).** `data.require_execution_release` is now fully generated
(`semantic/native_admission_release.py:343–409`), predicate for predicate from the hand-written
`admission.sql` it replaced (`9364a5b88`), and performs the same re-proof per call; its receipt is
still recorded only if absent and still short-circuits nothing. Binding and population selection
have no commit. One per-call check now runs over an input population that is always empty: the
authored-SQL inputs, which nothing supplies ([DA-080](../audit/boundaries-and-composition.md#da-080));
it retires with that machinery (R13).

<a id="r12"></a>

### R12 — Analytical placement and DuckDB conditions (Q6)

**Conditions of use**, from the library contributor's decision rule, kept: inputs are an immutable
identified snapshot (exported Parquet, Arrow from the authorizing session, Arrow IPC files); the work is
set-shaped and large enough that fixed per-query cost does not dominate; it is built from expression objects
with model-derived input schemas; and the connection sets `TimeZone='UTC'`, threads, memory limit and an
absolute spill directory from `AnalyticsSettings`, with one cursor per thread. PostgreSQL inputs arrive by
exporting Arrow from the application's own session (ADBC or binary `COPY`), never by `ATTACH`.

**Typing from the model.** One bridge on the compiled model produces Arrow schemas: for physical relations
through `MetaData` and `semantic/arrow_types.sql_arrow_type`, for non-physical LinkML classes through the
slot-range mapping the companion projection already uses (`semantic/companion_projection.py:88–140, 165–216`).
DuckDB scans Arrow with its type mapping; outputs are finished with `table.cast(model_schema, safe=True)`.
Traps to handle (probed by the library contributor on synthetic data, [DuckDB report](../evidence/2026-11-18_production-review-inputs/library-duckdb.md) §D): dictionary
columns arrive as `VARCHAR` (cast to an `ENUM(...)` type string derived from the model only for
vocabularies declared closed, R15; open and pack-extensible vocabularies stay `VARCHAR`, so an analysis
over data that uses a term not yet settled does not refuse); `TIMESTAMPTZ` takes the session time zone; JSON typing ends at the boundary; a union can widen
silently.

**Keeping "no SQL text".** The relational API accepts strings in filters, conditions and `sql_expr`. The
convention is: expression objects only (`col`, `lit`, `fn`, `when`), column names taken from the
model-derived schema, no `sql`, `query` or `sql_expr`. A renamed column then refuses at relation
construction: DuckDB raises `BinderException` when a missing column is projected (probed by this reviewer,
§10). No new lint is proposed (the project rule against alignment linting stands); the convention rides on
code review.

**Where operation-local shapes are code.** An Arrow schema that only one kernel builds and reads (candidate
boxes `ingest/pdf_candidate_geometry.py:60–72`; the recognition replay `ingest/pdf_stream_reconciliation.py:233–241`;
the rich view relations `semantic/analytical_kernels.py:21–60`) is an implementation detail, not a domain fact,
and stays a local `pa.schema`. Names inside it that *are* model slots derive from the model: the projected
entity attributes `("id", "key", "types", "label", "symbol")` (`semantic/analytical_kernels.py:62`) come from
the rule-view `Entity` class (`model/semantic/rule-view.yaml:23`).

The judgment per computation is the table in §5.

**Revision of 2026-11-18 (unchanged).** None of the six DuckDB modules has a commit in the range.
The resource settings are still unread, and three sites set their own literal limits (`threads=1`,
`memory_limit="2GB"`: `semantic/rich_consolidation.py:405–412`;
`ingest/pdf_candidate_geometry.py:87`; `ingest/pdf_stream_reconciliation.py:301–305`)
([DA-020](../audit/boundaries-and-composition.md#da-020)). The configuration wiring above covers
both: every connection takes threads, memory and spill from `AnalyticsSettings`, and the literals
become the settings' defaults.

<a id="r13"></a>

### R13 — Retirement (Q9; DA-072, DA-080)

The target removes: the earlier model (`model/core.yaml`, `model/system.yaml`, `model/revisions.yaml`,
`core/vocab.py`, `core/_model/*`, the parts of `core/keys.py` not live, `schema/change.py`, `schema/pack.py`,
`schema/lookup.py`, `domains/statistics/schema/statistics.yaml`) after its 39 importing modules move to
released-model types, including the generated facade that emits `core.vocab.TaskUnitType`
(`semantic/native_call_generation.py:106`); the per-consumer composition routines; the hand operation-grammar
validator, `_PROFILES`, `_KIND_UNIVERSES`; the validity tuples, guard id lists and the completion `If` chain;
the frontier-guard tuple and shared-stream name set; role literals outside the vocabulary; the four field-kind
maps; the hand program lists and facade tuples; text markers and the entry-point rename pass; `LOWERING_FILES`,
the query custody lists and the capture's module enumeration; the scientific recipe description; the two
uncalled DuckDB kernels (`semantic/analytical_kernels.py:150, 170`; `semantic/rich_relations.py:112, 115`) and
`FileRelation`; six unloaded `.sql` files; `semantic/published_address_migration.py`; the evaluation modules with
no production importer (`evaluate/equivalence.py`, `affine.py`, `artifact_pilot.py`, `sampling.py`,
`split_decisions.py`, `split.py`, `sets.py`) unless the operator names a consumer; and, by operator decision,
`semantic_alembic/` and `alembic/`. Unread `AnalyticsSettings` fields are wired (R12), not removed.

One prerequisite protects an intentional flexibility. The earlier model is the only place that
declares whether a vocabulary may be extended by packs (`Lifecycle`: `static` or `schema_version`,
`model/core.yaml:1034–1040`, enforced by `schema/pack.py`). Before `core.yaml`, `schema/model.py` and
`schema/pack.py` retire, that distinction moves to the released model (R15), and the released route
for pack extension (pack schemas imported by the release, `domains/statistics/operations.yaml`) is
confirmed to cover what the earlier pack loader allowed.

**Revision of 2026-11-18 (partly delivered).** *Delivered:* the six unloaded `.sql` files went
with the whole `semantic/sql/` directory (`c25cada3f`, a commit whose message describes a
documentation change); `semantic/published_address_migration.py` was deleted (`54a232131`); the
scalar encoder kernels, not listed before, were deleted (`93b7141ec`). These leave the list.
*Stands:* the earlier model (41 importing modules by the audit's wider pattern, the same set at
both commits; the 39 above came from a narrower pattern), the evaluation modules, the rendition
keying modules, the earlier pack loader, the two uncalled DuckDB kernels and `FileRelation`, and
the two migration trees. *Added* from the audit's update
([DA-080](../audit/boundaries-and-composition.md#da-080)): `pdf_shape_guard_sql`
(`semantic/pdf_contracts.py:578–588`, a hand-written PL/pgSQL fragment with no caller); the
release-side authored-SQL machinery, whose `authored-sql/…` dependencies nothing supplies
(`semantic/authored_sql.py:299–369`; `semantic/native_admission_release.py:461–500`), while the
live submitted-SQL analyser `admit_sql` stays; two LLM producer modules with no production importer
(`methods/llm/producer.py`, kept alive only by `tests/ingest/test_managed_recognition.py`, and
`methods/llm/agent_opus.py`, with no importer); the native fitting path
(`evaluate/operation_fitting.py:530–620`, which calls `eval.*` functions the deployed state no longer
defines, R07); and the Unicode parity check with no
caller since `bcff594c2` (`semantic/unicode_identity.py:233–246`), which is either wired to the
release check it was written for or retired (owner decision). The model preview's SQL explanation
is not retired but retargeted (R07).

<a id="r14"></a>

### R14 — The scientific policy derives from its declaration (DA-077)

**Target behavior.** `scientific-policies.yaml` becomes instance data validated by a LinkML class; the
comparison kernel reads its parameters (for example the sampling bounds now written as `rng.uniform(0.25, 3, …)`
at `semantic/scientific_evidence.py:1301`) from that declaration; the archived recipe is the canonical
serialization of the same declaration, computed once per compiled model. A kernel edit then changes the recipe
or nothing, and a wording edit cannot refuse every release.

<a id="r15"></a>

### R15 — Declared openness of vocabularies (F05; added by the recommendation audit)

**Diagnosis.** The earlier model declares, per enum, whether a set changes only with code
(`static`, enforced by a digest-named check) or may be extended by packs (`schema_version`, enforced
by per-version member rows) (`model/core.yaml:1034–1040`, applied at `:895, 913`); its pack loader
refuses pack members for a static set and accepts them for an extensible one (`schema/pack.py:1–22`).
The released model has no successor: `semantic/ontology.py:328–410` composes `inherits`, `include`,
`minus`, `concepts` and ontology `reachable_from` members without any openness property, and every
released enum is closed in validation. R13 would retire the earlier model and with it the only
representation of this intended distinction.

**Target behavior.** Each released vocabulary declares one of three kinds of openness, with stated
consequences:

- **closed**: changes with code; programs may dispatch on it; checked at import (`Literal` copies),
  in physical checks through `ph:values_from`, and in analysis casts (R12);
- **pack-extensible**: a pack may add members through `inherits` or `include` in its own schema;
  members become per-release vocabulary rows; a program that dispatches on such a set names its
  handling of members it does not know;
- **open with known members**: any value is accepted; known members carry declared meaning that
  consumers may test; an unknown value carries none and is reported through the existing
  non-refusing `unchecked` diagnostic (`semantic/prepare.py:485–530`, category `unassessed`,
  `semantic/operation_reporting.py:372–410`), never refused.

Individual members may be marked provisional with the `status` slot permissible values already carry
in LinkML; a provisional member is accepted and reported. Ontology-derived vocabularies keep their
`reachable_from` membership and their `unchecked` reporting. Knowledge content is not governed by
this declaration: a source term outside a vocabulary is still recorded with its explicit state
(candidate, `missing_candidate`, unsupported proposal, validation error retained under ADR-0077).

**Library mechanisms.** No openness flag exists on LinkML 1.12.1 enums (observed in the installed
metamodel's `enum_expression` slots), so the declaration is a released-model annotation succeeding
`ci:lifecycle`, admitted deliberately by the preparation profile, which refuses unsupported
annotations (`semantic/prepare.py:259`). Open slots use a range of `any_of` the enum and `string`.
Provisional members use the native `status` slot of `common_metadata`.

**Challenge cases.** A pack tries a new measurement-role term: if the vocabulary is pack-extensible it
adds the member in its own schema and no core edit is needed; if it is closed, the refusal is the
declared intent and says so. An extraction yields an ownership-like label nobody has defined: for an
open vocabulary it is kept and reported. A program that dispatches on a vocabulary can only do so for a
closed one or with a declared handling for members it does not know, so a new pack member can
never reach a dispatch without a handler.

<a id="r16"></a>

### R16 — Graded consequences for undetermined declarations (DA-070; added by the recommendation audit)

**Diagnosis.** Today an operation outside the classification list gets the most permissive
treatment: its family premises are never evaluated (DA-070). The first-round remedy went to the
other extreme, refusing any operation that has not classified itself. The project already has a
middle course in two places: identity, where unknown required determinants withhold reusable
identity without forbidding execution (ADR-0092; `semantic/data_operation_identity.py:378–387`), and
preparation, where unchecked vocabulary terms are reported as `unassessed` without refusing.

**Target behavior.** An undetermined declaration is permitted and carries a stated conservative
consequence. For the validity family:

- *named families*: each family's validator runs; validity is their conjunction;
- *`none`*: a positive claim that only generic validity applies (outcome, revocation, support
  propagation); derivations survive later changes of trust and kernel;
- *absent or `undetermined`*: the operation compiles and runs; preparation reports it as
  unclassified; validity adds a **conservative premise check**, under which a derivation is valid
  only while the trust snapshot and the validator identity it was produced under are unchanged. This
  over-invalidates and never under-invalidates. The conservative check is one generated program with
  its own validator identity (R05, R11);
- *a provisional family*: its members are treated as undetermined until its validator exists.

A **promotion boundary**, at which undetermined declarations refuse, is the operator's choice
(RC14): none; activation of the default release; or knowledge publication. Because the conservative
check already removes the integrity risk, the recommendation is none, with the diagnostic as the
pressure to classify. The same graded pattern is available, not imposed, for other declarations
that may be unknown when an operation is first written.

**Feasibility and limits.** The store already records some of the premises the conservative check
needs: publication receipts hold `trust_snapshot` and an optional `validating_kernel_digest`
(`model/semantic/data-operation-physical.yaml:475–484`), support rows record the trust scope and
epoch they relied on (`:458–466`), and demand reads record a trust snapshot and kernel digest
(`:619–631`). Whether every episode can be tied to the trust snapshot it consumed is for the native
owner to confirm (Proposed). The default cannot cover a family-specific premise outside trust and
kernel, such as the contextual linguistic premise (DA-070); that residual risk is why family
bindings exist, and under this design it is visible as an unclassified diagnostic rather than silent.

**Challenge cases.** An exploratory operation is added and run on a book: no declaration is needed; its
results are kept; a trust revocation elsewhere invalidates them conservatively and they are recomputed
on demand. Once its semantics are understood it declares `none` or a family and stops paying for the
conservative check. A family is designed before its validator is written: it is declared provisional,
and its members behave as unclassified until the validator lands.

**Revision of 2026-11-18 (changed).** The converted guards add a second place where today's
permissive treatment applies: at completion, each family guard returns early for an operation not
on its list, so an operation outside every list receives only the generic completion checks
(`ops.ddo_require_product_validations`, `ops.ddo_assert_output_witnesses`,
`semantic/data_completion_settlement_native.py:548–563`). That treatment is right for an operation
that genuinely belongs to no family and wrong for a forgotten member, and today the two cannot be
told apart. Under R02's revised route the guards select by the lowered column, so the early return
stops being an omission point: a member that declares its family is always selected. The three
states then have stated consequences at completion as well as at validity:

- *named families*: each family's completion guard and validator run;
- *`none`*: generic completion checks and generic validity, by positive claim;
- *absent or `undetermined`*: generic completion checks (no family's output contract is known to
  apply), the conservative premise check at validity, and the preparation diagnostic. No family
  guard is invented for it; the diagnostic is what makes the gap visible.

This narrows what R16 has to carry. Before the revision the conservative check was the only
protection against a forgotten member; with membership declared beside the operation and read by
every selection point, forgetting can happen only by not declaring, and that case is reported. The
conservative check remains the integrity backstop for that case, and its feasibility question (can
every episode be tied to the trust snapshot it consumed) is unchanged. Step A of R07 can land before
the conservative program exists; until it does, an undetermined operation keeps today's treatment
but is listed, which is no worse than today and strictly more visible.

<a id="r17"></a>

### R17 — Release-bound pack inputs come from the release (DA-028; added in the revision of 2026-11-18)

**Diagnosis.** Preparation archives the pack's `slices.yaml` as the release artifact
`operation/slices.yaml` (`semantic/regeneration.py:110–118`), and nothing reads that archived copy.
The production source-demand path receives the loaded release and then reads the working tree's
`slices.yaml` to select document scopes, finding the pack directory by matching a name in the live
`semantic.yaml` against archived module names without comparing bytes
(`orchestrate/source_operation.py:54–60, 160–176`)
([DA-028](../audit/semantic-model-and-authority.md#da-028)). A release that archived slices X can
therefore execute a demand under live slices Y and attribute the result to the release. This is the
same structural cause as R05's: an input that determines a result sits outside the identity the
result is attributed to.

**Target behavior.** Every path that attributes its result to a release reads release-bound pack
inputs from the release archive: source demand selects scopes from `operation/slices.yaml` in the
loaded release. A working-tree pack edit then takes effect through a new release, as a model edit
does, and a name lookup without bytes is no longer the link between a release and its pack.

**Alternatives.** Comparing the live file's digest with the archived one and refusing on a
difference is safe but makes the ordinary edit loop refuse instead of simply using the release's
bytes. Leaving the live read and recording the live digest on the result makes the drift visible but
attributes a result to a release whose inputs it did not use.

**Challenge case.** An exploratory slice is added to the pack while a release runs: the running
release keeps its archived slices; the new slice is available once a release is prepared with it.
Nothing about trying a new slice becomes harder, only its attribution becomes exact.

## 5. DuckDB judgment over the analytical inventory

IDs follow the analytical map ([analytical inventory](../evidence/2026-11-18_production-review-inputs/analytical-inventory.md) §10). "Bound" means the work needs PostgreSQL's transaction,
locks, principal or writes.

| ID | Computation | Verdict | Reason and condition |
|---|---|---|---|
| G1 | Validity closure and fixpoint | Keep in PostgreSQL | Bound: visibility by transaction id, revocation table, caller principal |
| G2, G3, R1 | Support walk, watermark prerequisites, tree and dependency walks | Keep in PostgreSQL | Bound; generated from the declared edge table (R08) |
| S4 | Full-text ranking | Keep in PostgreSQL | `ts_rank_cd` parity and dictionaries; DuckDB's BM25 differs (documented) |
| G7, C1 (database part) | Mutual exact-cosine neighbours over pgvector | Keep in PostgreSQL, as a typed program (delivered: generated Core over pgvector, `semantic/contextual_neighborhood.py:70–300`, `32ec30618`) | Pure, but its numerical backend is pinned and checked (DP-11) |
| D1 | Rich-rule occurrence views (same slot, alternative of, declared projections) | Keep in DuckDB, conditional | Join-and-group shape over up to 100,000 members; round trip from Python objects costs per invocation. Revisit to plain Python if observed per-subject inputs are small. Derive model slot names (R12); connection settings from configuration |
| D1b | `disagreements`, `fuse` kernels | Retire | No production caller; the live disagreement grouping is Python (`semantic/rich_consolidation.py:336–372`) |
| D2 | Companion export inventory and multiset comparison | Keep in DuckDB | File-scoped `EXCEPT ALL` with multiplicity is its strength. Derive grouping and excluded columns from `cp:` annotations; set time zone and spill; bound the materialized difference (today unbounded, `serve/companion_export.py:582–600`) |
| D3 | PDF candidate geometry joins | Keep in DuckDB | Containment and intersection joins with windows; box schema is operation-local |
| D4 | Recognition replay external sort | Keep in DuckDB | Spilling sort of a large IPC file; fix the duplicated `input_key` in `pin_json` (returned to the audit) |
| D5 | Splink scoring | Keep | Library-owned SQL |
| I8 | Certification staging folds (SQLite staging, then ordered folds) | Move to DuckDB, conditional | Rows already arrive as Arrow IPC; a DuckDB sort by key streams to the Python digest fold and removes a per-row SQLite copy. Condition: binary key ordering matches today's `COLLATE BINARY` (DuckDB's default string comparison is binary; verify once) |
| X1 | Companion export (PostgreSQL to ADBC to Parquet) | Keep | Bound to the exported snapshot; already Arrow |
| X2 | Companion file verification | Plain Python, with carried status | Verification runs per path per inventory and twice per compare; carry the verified status per file identity (T0 custody) instead of moving it |
| X5 | Detached selected-result export (SQLite dedup, then Parquet per relation) | Plain Python with Core over SQLite | Keyed dedup and ordered batches; DuckDB adds JSON-to-typed conversion work for modest gain. Revisit if export size makes the per-row path material |
| X6, S6, S7, S8, S1 | Per-page joins and shaping of acquired pages; identity-exclusion comparison | Plain Python | Page-sized, after authority; S6's whole-admission index is held in T4 |
| S3 | Source catalog with one native read per row | Keep in PostgreSQL, set-wise | Push the per-row header read into the page's native read (an N+1, returned to the audit) |
| X7 | Model and release comparison | Plain Python | Small compiled models |
| X8 | Selected-source package verification | Plain Python with Core over SQLite | Replace per-row ancestry queries with one set-wise query; keyed |
| G4, G6, G8, G9 | Semantic graph, graph inspection, bounded rich walks, rich closures | Plain Python (networkx) | Small or explicitly budgeted; G4 held in T1 with the compiled model |
| G5 | Change impact | Remove the re-encoding (R08); the remaining classification is plain Python | Index revocations by node instead of scanning nodes against all revocations |
| G10 | Pairwise artifact candidates with string ratio | Plain Python | rapidfuzz scores are the numerical contract; DuckDB string functions differ |
| E1–E6, SC | Alignment, matching, bootstrap, fitting, sampling, scientific comparison, record interpretation | Plain Python numerics | numpy and scipy semantics; no set-shaped gain |
| I1, I2 | Page availability flags by per-row loop over Arrow | Plain Python with `pyarrow.compute` | Vectorize the loop; no engine needed |
| I3 | Candidate counts | Keep (`pyarrow.compute`) | Already vectorized |
| I6, I7, M1 | Docling graph selection, box merging, table interpretation | Plain Python | Object-graph work |
| T1, T2 | Arrow to PostgreSQL copy; row streaming into operation inputs | Keep | Bound |

**Where DuckDB should not be used:** anything needing PostgreSQL's snapshot, locks, principal or writes; read-side
paging served to clients; point lookups and small keyed reads (SQLite or a dict); tens to hundreds of rows already
in Python; full-text ranking; any route that would `ATTACH` PostgreSQL. DuckPGQ is not adopted (community research
extension, 2.0.0 binary unconfirmed, SQL text).

**Revision of 2026-11-18 (unchanged, with four new rows considered).** No DuckDB module changed and
no computation moved to or from DuckDB in the range ([analytical map](../audit/model-and-execution.md#analytical)),
so every verdict above stands. The audit's update adds four PostgreSQL rows, each bound to native
authority and therefore kept there: binding population selection now selects independent optional
roles per role from the anchor, removing a cross product (`semantic/data_operation_bindings.py:1028–1055`,
`1d3640990`); PDF inventory completeness materializes access edges once for both directions
(`semantic/pdf_publication_native.py:1925, 2160–2210`, `66c36d4c8`); archived class matching for
record grading parses the archived model once per call (`semantic/record_grade_native.py:150–175`,
`a31503daf`), though still once per grading call, which is a candidate for R11's carried
binding facts rather than for DuckDB; and public reads add a second recursive support closure per
page (`semantic/data_operation_projections.py:452, 2231`), which stays with the walk of R08. The
captured document composition is plain Python over a canonically ordered set and stays so. The
companion export's projection inputs are now held (R01 revision); its unbounded difference
materialization (§16) is unchanged.

## 6. Fact-authority table

"Retires" lists what the target removes for that fact.

| Fact | Target authority | How consumers obtain it | Retires |
|---|---|---|---|
| Record and product shape | LinkML released model | Compiled model: merged view, `MetaData`, Arrow bridge, generated facades | Earlier-model copies; hand Arrow schemas for model relations |
| Field type and constraint | LinkML range, pattern, bounds; physical checks as structured annotations under the profile | Compiled `MetaData` checks | JSON strings in annotations; the universe check literal beside `_KIND_UNIVERSES` |
| Field kind to database and Python type | LinkML type `uri` and `ph:sql_type` (declared today, `model/semantic/physical.yaml:33–36`) | The physical compiler's type resolution (`schema/relational.py:79–89, 437–440`), exposed once on the compiled model | Four maps (`semantic/native_call_contracts.py:16–25`; `semantic/native_call_sources.py:28–37, 133–136`; `semantic/pdf_search_native.py:98–104`; `semantic/native_program.py:621–622`) |
| Domain value sets | LinkML enums, expanded once by the released `expand_enum`, each declaring its openness (closed, pack-extensible, open with known members; R15) and optionally provisional members | Compiled value sets; closed-set checks for Python `Literal` copies of closed sets; physical checks through `ph:values_from`; unknown values of open sets reported, not refused | Duplicates in the earlier core; one of the PDF outcome pair |
| Operational vocabularies (profile, kind universe, ownership, forms, validity family, support edge kind, purpose, role) | LinkML enums in a declaration schema with declared openness: profile, kind universe, forms, validity family, support edge kind, purpose and role closed; ownership open with known members; preparation and cancellation descriptions unconstrained | Compiler, generated dispatch, closed-set checks for closed sets | `_PROFILES`, `_KIND_UNIVERSES`, hand tuples |
| Operation (existence, roles, dependencies, capabilities) | Instance data through ADR-0092's two routes; Python literals validated against the LinkML declaration class | Effective operation model | Hand grammar validator |
| Validity family membership | Optional, set-valued field on each operation declaration: named families, explicit `none`, or absent/`undetermined` with conservative validity and a non-refusing diagnostic (R02, R16) | Lowered per release from the archived declaration into the definition column, which distinguishes the three states; every guard, validator and dispatch selects by that column at run time (revision) | The classification program, the dispatch tuple and the ten guard lists, the completion chain, the validators' early returns (twelve lists at `5139eaba3`) |
| Family contract (validator program, premises, member requirements) | Enum member annotations naming the validator program and the requirements its members must meet (forms, profile, input role kinds, receipt count), or `status: provisional` while the validator is unwritten | Program registry; generator input (model-level); preparation checks members against the requirements | Dispatch tuple; per-id profile, form and receipt tables in guards |
| Per-operation contract facts (entry point, profile, forms, preparation, effects) | Effective operation model (exists) | Lowered definition rows, read at run time; the implementation is authenticated by the implementation-slice revision; the typed read boundary for `support_contract` takes its shape from the effective model (revision) | Per-id factory dictionaries and entry-point literals in guards (53 lines in 15 files at `5139eaba3`); free JSON paths into `support_contract` |
| Support-edge meaning, reference-to-node map, scope key | Declared closed `SupportEdgeKind` with a traversal table per purpose (provenance edges only; knowledge relations stay in packs) | Generated validity and support walks; change impact through the validity explanation; unrecognised references refuse | `_support_walk`'s private map and its open `episode` default; `_revocation_causes`; change impact's scope formula |
| Operation dependency graph | Compiled `selected-dependencies` and `potential-producers` | Change impact, planner | `changed_operations` hand graph |
| Release composition | Source collection derived from the captured collection that includes each literal (an `acquired_by` field only to override), plus a manifest of requested operations or families; partial releases are ordinary | Closure over compiled dependencies mapped to source collections | Flag logic in `semantic/primary_operations.py:118–392` |
| Relation physical layout (keys, foreign keys, checks, indexes, immutability, archive role, search configuration) | LinkML physical declarations under the typed profile | `MetaData` and its `info` | JSON-string encodings |
| Frontier-guard membership | Declared schema-level default (`guarded`) with per-relation `exempt` overrides in the physical profile | `MetaData.info`; generated trigger | Twelve-name tuple |
| Shared-stream trigger membership | Existing `ph:immutability: pending-content` | `MetaData.info` | Name set |
| Roles (names, login, memberships, prohibitions) | LinkML `Role` vocabulary | Host bootstrap, grants, control expectations as data | Constants in `semantic/alembic_privileges.py:25–33`; 199 role-name occurrences in 47 Python modules at `5139eaba3` (176 in Python and 70 in the deleted SQL files before); the role tuples of `semantic/native_admission_tables.py:27–32`, `semantic/native_admission_principals.py:8–9` and `semantic/native_admission_release.py:400–404` (`admission.sql` is gone) |
| Purpose to role | `Purpose` vocabulary member annotations | Protocol function grants; program grants; the runtime principal check | Two copies: `semantic/data_operation_storage.py:1899–1907`; `semantic/closure_native.py:174–181` |
| Table read grants | Declared default read roles per schema, explicit `ph:read_roles` where a relation differs | Alembic privilege operations; table admission | `DEFAULT_READ_ROLES` as a code default; the JSON literal of `semantic/native_admission_tables.py:176–184` |
| Execute grants for native functions | Program declarations' purposes | Generated `GRANT` nodes; control expectations | Name-matching chain; installation tuples; default grants in helpers |
| Task states and transitions | Protocol lifecycle (retained) | Compiled lifecycle projection, as the task guard already reads it (`semantic/data_operation_protocol.py:117–128`; it read the lifecycle at `d78c98765` through a template and has been a typed program since `32ec30618`) | State string literals in the other kernels (21 quoted `pending` or `running` in eight files) |
| Wire shape and native operation ABI | Protocol (retained peer) | Generated wire module; validators held in the compiled model | — |
| Value-codec vocabulary | LinkML observations vocabulary | Closed-set check at import | Python `Literal` plus hand `_TEXT` tuple |
| Native program set (existence, order, signature, grants, callees, family) | Typed program registry | Program set; topological order | Hand lists, naming conventions, markers |
| Generated outputs (facades) | Self-checking generated-output registry | Preview renders every registered output | `_NATIVE_OUTPUTS` zip and `__main__` paths |
| Code that determines an artifact | Derived code identity plus program identities | Identity computation | `LOWERING_FILES`, query custody lists, capture module enumeration, port generator list, opaque asset lists |
| Scientific policy parameters | Policy declaration validated by a LinkML class | Kernel reads it; recipe is its serialization | Hand recipe description; kernel literals |
| Custom catalogs (PDF actions, analysis policy, metrics, characterization questions) | Instance documents, each with a LinkML class; closed-world where fields drive behaviour; the explicit open states inside them (for example `insufficient_evidence`, `missing_candidate`) kept | Validated once per compiled model | Ad-hoc parsing (consumers not traced) |
| Operation-local analytical shapes | Local `pa.schema` beside the kernel; model slot names from the model | — | Hand restatement of model slot names |
| Companion grouping and provenance columns | `cp:` annotations | Companion projection | Literals in `serve/companion_export.py:419–424, 557–589` |
| Identity determinants | Compiled (sound); unknown determinants withhold reusable identity (ADR-0092), also for served reads whose code closure is unresolved (R05) | — | — |
| Vocabulary openness and member status | Released-model openness declaration succeeding `ci:lifecycle`; LinkML `status` on members (R15) | Preparation, closed-set checks, pack loading, analysis casts | `ci:lifecycle` in the earlier model |
| Undetermined declarations and their consequences | The declaration's own optional field with a declared meaning for absence; promotion boundary chosen by the operator (R16, RC14) | Preparation diagnostics (`unassessed`); conservative validator program | Permissive `else` defaults |
| Privileged-effect ownership (revision) | The effect, already declared per operation with its authorization premises in four families (`methods/record_policy.py:70` and siblings); an owner declaration on the effect vocabulary member, closed and complete (integrity) | Generator input; any other claimant refuses, as rich admission and policy authorization already do (`semantic/rich_admission_native.py:1135–1145`; `semantic/record_policy_completion_native.py:425–441`) | The evaluator-authorization id subset (`semantic/data_completion_settlement_native.py:576–587`); the inline owner ids |
| Product member families, fields and required sets (revision) | Protocol definitions (exist) | Generated product admission reads them | `_FAMILIES` (`semantic/data_product_admission_native.py:56–90`) |
| Encoder failure codes (revision) | The encoder's Python set (exists) | Generated contextual admission reads it | Literal codes in `semantic/contextual_admission_native.py:653–660` |
| Value admissibility bounds (revision; DA-040) | One declared limit of the value codec | The Python codec and the canonicalizer generator | Unbounded expansion in `semantic/value_codec.py:15–20` and `semantic/data_operation_value_native.py:112–149`; the bounds kept separately in two modules |
| Release-bound pack inputs (revision; R17, DA-028) | The release archive (`operation/slices.yaml` and siblings) | Source demand and every path that attributes results to the release | The working-tree read in `orchestrate/source_operation.py:160–176` and the name-only match at `:54–60` |
| Semantic release annotations (revision; DA-004) | LinkML `cs:` annotations (exist) | Decoded once into typed values on the compiled model | 36 decoding sites in `semantic/` and `serve/` |
| Per-predicate qualifier partition (revision; DA-001) | `cs:qualifiers`, `cs:identity_qualifiers` (exist, compiled and validated) | Scientific grouping reads the compiled partition, or the declaration retires (owner decision) | The unread `ComparisonProjection.partition` |
| Principal restrictions, application schemas, private kernels (revision) | Role vocabulary; `MetaData` schemas; program registry | Generated admission | Tuples and signature text in `semantic/native_admission_principals.py:8–16` |
| Catalog-check boundaries of the admission guard (revision) | Program registry (a declared sub-program); the frozen revision for frozen guards | Frozen catalog verification | Marker comments and substring recovery (`semantic/native_admission.py:42–82`) |
| Pack rule language | `schema/rulelang.py` (not examined) | — | Open; returned to the audit |

**Formalisms after the change:** LinkML (primary); the protocol as a peer for wire, lifecycle and native ABI;
Python literals as the storage form of one operation route; typed Python registries for code artifacts. The custom
catalogs stop being a separate formalism (they become LinkML-typed instance data), and the earlier LinkML model
retires.

**Derivations between retained authorities** (all existing or supported): LinkML to `MetaData` (project compiler);
`MetaData` to Arrow (`semantic/arrow_types.sql_arrow_type`); LinkML classes to Arrow (companion projection's slot
mapping, generalized); Arrow to DuckDB relation types (DuckDB scan mapping); protocol to physical value sets
(`ph:values_from`); protocol to wire module and validators (project generator); `MetaData` and the program registry
to typed programs (Core and pglast); closed LinkML enums to Python `Literal` checks (closed-set check); LinkML declaration
class to validation of operation literals (`linkml.validator` with the closed JSON Schema plugin for field names and
the recommended-slots plugin for warnings).

**Revision of 2026-11-18.** Rows marked "(revision)" were added against the audit's rebuilt
[fact-ownership table](../audit/domain-model-map.md#fact-ownership); rows whose "Retires" column
changed name the sites at `5139eaba3`. One derivation is added to the list above, and it carries
the revised R02: the archived effective operation to the lowered `sem.data_operation_definition`
row, performed by the existing lowering program inside the kernel, which is how per-operation facts
reach guards without entering the generators. The split it enforces: model-level vocabularies (and
the declarations attached to their members) are generator inputs and part of the kernel's
identity; per-operation instance facts are release content and are not.

## 7. Change and failure scenarios

| Scenario and kind | Today | Target |
|---|---|---|
| Add a modeled field (domain concept) | LinkML slot; typed programs pick it up through compiled columns; hand bodies and hand Arrow schemas do not; the kernel digest and release id change; PDF certification refuses if a listed model file changed | LinkML slot; new model identity; only programs whose bytes change get new identities; Arrow schemas derived |
| Add a value-set member (instance) | Edit once, or twice where the set is duplicated in the earlier core; the value codec tuple may be missed silently | One enum; for a closed set, checks of code copies refuse drift at import; for a pack-extensible set, the pack adds the member; for an open set, nothing is required |
| Add a data operation (instance) | Literal, plus the classification tuple and every guard list of its family (twelve lists in nine modules at `5139eaba3`), per-id pins, release flags and program lists as applicable; each list edit is a kernel edit and a native revision; an omission fails open at classification, dispatch and each guard | Literal; its source collection is derived; its family is declared when known and lowered with the release, so the kernel does not change. An operation left unclassified compiles with a non-refusing diagnostic, generic completion checks and conservative validity |
| Add a validity family or a guard (policy) | New tuples, validator, dispatch entry, guard tuple | Enum member naming its validator program, or provisional until it exists; generation refuses a non-provisional member without one; new relations in guarded schemas are guarded by the declared schema default unless exempted |
| Add a role or change a grant (policy) | Edits across 39 modules and SQL | Vocabulary member and purpose annotation; generated grants; controls receive expectations as data |
| Change one generator module (mechanism) | Kernel digest changes: every acquisition refuses until a new kernel is deployed; release id changes; receipts replay; reads reacquire; watermarks advance; PDF work may refuse | Program set regenerates; if no bytes change nothing else changes; otherwise only the changed programs, the kernel identity and families whose validator closure includes them |
| Edit a captured Python helper or authoring module without changing any generated statement (mechanism; observed in the range) | Observed at N29: a renderer-input helper moved the kernel digest and an authoring edit with byte-identical output moved the authoring-source digests; a full native revision was authored and deployed, changing nine objects only in digest literals | No program's bytes change, so no identity moves and no revision is authored (RC15) |
| Bump a library the generators use (mechanism substitution) | As above, even if every byte is identical | Generation cache key changes; regeneration; identical bytes change nothing downstream |
| Evolve the model with existing data | Alembic from `MetaData` and data steps; the preview rebuilds the capture two or three times | Unchanged migration route; candidate and running models coexist in T1; one generation per preview |
| Add an analytical question over published products | Hand Arrow schema; per-site DuckDB settings | §5 rule; Arrow schema from the compiled model; Arrow from the authorizing session; settings from configuration |
| Identical read from CLI and long-lived process | MCP hits only on continuation; CLI never | Continuation hits across CLI processes (D4); fresh identical requests once the content basis is certified |
| Two concurrent identical cold reads | Both derive | Both re-acquire authority; one derives; the other shares the value or the failure |
| Model change published while caches are warm | Import-time model kept until restart | New model identity; new entries; old entries remain valid for pinned reads; memory freed by event |
| Interrupted run resumed | Request identity reuse (sound) | Unchanged; disk tiers write-once with atomic replace; replay reconfirmation records are idempotent |
| Try an operation whose validity semantics are not yet known (exploration) | Indistinguishable from a forgotten family entry; its derivations are never re-validated against changed premises | No declaration needed; conservative validity; listed as unclassified until it declares `none` or a family |
| Try a relation or product kind in one pack (domain extension) | A pack class inheriting from a core class; registry rows, no DDL | Unchanged; none of the physical, guard or support-edge closures applies |
| Use a vocabulary term before it is settled (exploration) | Refused by a closed enum, or reported `unchecked` for ontology-derived sets | Accepted and reported for an open or pack-extensible vocabulary, or as a provisional member; refused only by a vocabulary declared closed |
| Keep competing structures side by side (content) | Alternatives, private proposals and disagreements retained (ADR-0024, ADR-0062, ADR-0077) | Unchanged; no recommendation constrains content |
| A release that includes only some operations (composition) | Profile flags in code; omissions refused at compile | A manifest of requested operations or families; closure over declared dependencies |

The domain extension (a new family) and the mechanism substitution (a library bump; a generator rewrite) both stay
local in the target; today both propagate across unrelated consumers. The exploratory scenarios stay as cheap as they are today or become cheaper; none of
them acquires a new mandatory declaration.

## 8. Correctness and fidelity gates

| Gate | Verdict | Evidence | Required action |
|---|---|---|---|
| G1 Authority | Fail | Family, edge meaning, guard and role facts held as independent lists with no reconciliation (DA-070, DA-071, DA-074; at `5139eaba3` twelve family lists and 199 role-name occurrences); earlier and released value sets (DA-072); vocabulary openness declared only in the earlier model (F05); a release attributed results computed under working-tree slices (DA-028) | R02, R03, R08, R13, R15, R17 |
| G2 Semantic fidelity | Fail | A `NULL` validity family means both "no validator applies" and "forgotten" (DA-070) | R02, R16 (explicit `none`; explicit undetermined state with its own consequence) |
| G3 Validity | Fail | An unlisted operation reaches validity with its family premises skipped, and at `5139eaba3` also skips every family completion guard by early return (DA-070) | R02, R16 (selection by the lowered declaration; conservative validity for unclassified operations; no permissive default) |
| G4 Hidden behavior | Pass, with one concern | No undeclared effects found; a capture can pair generated SQL with module bytes from different code in a long-lived process (DA-083) | R05 code custody |
| G5 Consistency and recovery | Pass | Refusals are fail-closed; unrecorded replay is cost, not inconsistency | — |
| G6 Transformation and reuse | Fail | Narrow identities let resumed pages and lowering certification survive edits to code they omit (DA-076, DA-082; both halves exercised in the range) | R05 |
| G7 Truthful capability claims | Fail, scoped | ADR-0131's consequence ("propagates or refuses") now holds for relations and columns in every converted module, and does not hold for declared facts the generators restate (task states, codec tags, product member fields; DA-086). The family and role lists are not an ADR-0131 promise (its consequence clause concerns model field and type changes, `:46`); they are G1 and A2 gaps, and their transcription was the predicted consequence of converting before declaring, not a divergence from the ADR; the model preview reports "no SQL change" because its explanation walks a removed directory (DA-080) | R07, R02 |
| G8 Library leverage | Fail, moderate | Hand `OrderedDict` LRUs, a hand entry cap, no single-flight; JSON strings where structured annotations exist; a hand grammar validator where schema validation exists; per-consumer composition | R01, R02, R03, R09 |
| CI-G1 Fidelity | Fail, scoped to change impact | Change impact follows edges validity does not and misses causes it sees; project-scoped revocations never match (DA-071) | R08 |
| CI-G2 Evidence closure | Fail across processes | A resumed served page can come from code its implementation identity omits (DA-076) | R05 |
| CI-G3 Evaluation integrity | Not assessed | Outside the operator's focus | — |

## 9. Findings

Consumed audit findings keep their identities and live in the audit; their dispositions are in
[dispositions.md](unified-domain-model-and-execution/dispositions.md). Additional review findings:

| ID | Finding and consequence | Principles · gate | Evidence | Correction | Closure evidence | Disposition |
|---|---|---|---|---|---|---|
| F01 | The per-acquisition native check ignores the prepared release it receives and regenerates the checkout's capture to compare with the installed descriptor, although the release records its kernel digest. This is the direct cause of DA-083's execution-path rebuilds, and it ties execution to the checkout instead of to the release. Revision of 2026-11-18: unchanged, and the comparison is redundant with the generated release guard, which already requires the archived digest to equal the installed descriptor in the same call | FP-07, DP-10; A4 | At `d78c98765`: `semantic/data_operation_storage.py:1116–1131`; `:1069–1070`; `semantic/prepare.py:1024–1030`; `model/semantic/data-operation-physical.yaml:22`; `semantic/data_operation_compiler_native.py:998–1093`. At `5139eaba3`: `semantic/data_operation_storage.py:1127–1142, 1080–1081`; `semantic/prepare.py:1025–1031`; `semantic/native_admission_release.py:516–533, 609–622` | R06 | A traced port acquisition that runs no generator and refuses when the installed descriptor differs from the release | Deferred to plan creation; reopens DA-083's remedy |
| F02 | Process-global memos reached from MCP tool threads are mutated without a lock, and several caches in long-lived processes are unbounded (parsers, a spaCy pipeline, a grammar resource). Revision of 2026-11-18: unchanged (no commit to the owners); the separate per-request CPU global was removed (`5c5443d16`) | DP-20; A4; G5 (likely, not observed) | `methods/math/grammar.py:309–327, 966–993`; `ingest/sentences.py:58`; `semantic/constructions/forest.py:36`; tool threads per `intervene/mcp_observations.py:11` | R09 tiers T5, T6 | Inspection of the migrated holders | Deferred to plan creation |
| F03 | DuckDB connections at four sites take library defaults: machine time zone, 80 percent of memory, all threads, a working-directory-relative spill path; the settings meant to govern them are unread. Revision of 2026-11-18: unchanged; three further sites set literal limits instead ([DA-020](../audit/boundaries-and-composition.md#da-020)) | DP-11, DP-20 | `serve/companion_export.py:410, 552`; `semantic/artifact_identity.py:481, 579`; library defaults probed by the library contributor ([DuckDB report](../evidence/2026-11-18_production-review-inputs/library-duckdb.md) §E) | R12 | Inspection of connection configuration | Deferred to plan creation |
| F04 | Application code writes SQLite SQL by concatenation, including field names in JSON paths, in five modules, outside any decision about SQL text. Revision of 2026-11-18: unchanged (59 lines, 58 execute sites, as at `d78c98765`) | FP-02; operator concern | `semantic/data_operation_read_index.py:20–27, 66–74` and four further modules (audit fact under DA-084) | R07 | Inspection of the converted stores | Deferred to plan creation; rule impact RC02 |
| F05 | The released model cannot say whether a vocabulary is closed, pack-extensible or open. The earlier model declares it per enum (`Lifecycle`: `static` or `schema_version`) and its pack loader enforces it; the released vocabulary expansion and preparation carry no such property, so every released enum is closed in validation and pack extension of a shared set is neither declared nor refused. R13 would retire the only representation of this intended distinction (added by the recommendation audit) Revision of 2026-11-18: unchanged (no commit to the earlier model, `schema/` or the ontology composer) | FP-04/A2 (model adequacy) | `model/core.yaml:1034–1040, 895, 913`; `schema/pack.py:1–22`; `semantic/ontology.py:328–410`; `semantic/prepare.py:480–530` | R15, R13 | Each released enum declares its openness and preparation enforces it; no openness rule remains only in the earlier model | Deferred to plan creation |

## 10. Library fit, verdicts and probes

**Selected mechanisms** (each also named in its recommendation): LinkML `SchemaView` composition, enums with
structured annotations, `linkml.validator.Validator` with the closed JSON Schema plugin (R01, R02, R03);
LinkML `recommended` slots with `RecommendedSlotsPlugin` warnings, `status` on permissible values, and `any_of` an
enum and `string` for open vocabularies (R02, R15; observed in installed 1.12.1 source by the recommendation
auditor, 2026-11-18);
SQLAlchemy `MetaData`, Core, `CreateTable`, `Table.to_metadata` (R04, R07); pglast AST nodes including
`CreateTrigStmt` and `ViewStmt` (R04); pyarrow schemas and safe casts (R12); DuckDB relational and expression API
(R12); cachetools 8.0.1 `LRUCache`, `cached` with `condition`, `cachetools.func.lru_cache`, `keys.hashkey`
(R09); standard-library `ast` and `importlib.metadata` (R05); networkx topological sort (R04).

**Do not adopt**, with reasons:

- LinkML SQL, SQLAlchemy and Pydantic generators for the physical model: they honour three annotations and no
  PostgreSQL schemas, checks, triggers or grants (probed, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F10); the project compiler stays.
- linkml-map for retiring the earlier model: the problem is duplicated schema, not data to move; its SQL backend
  drops expressions silently (documented).
- linkml-datalog, pySHACL or an RDF store for support closure and change impact: alpha or open-world, no consumer
  needs RDF.
- Subclassing LinkML's `Generator` for output governance: it is a single-output visitor; the project's registry
  with an ownership check is the right owner.
- valuesets as a runtime import: vendored YAML capture is sufficient.
- DuckDB `ATTACH` to PostgreSQL: separate credentials and snapshot; text through `postgres_query`.
- DuckPGQ: research extension; SQL text; 2.0.0 binary unconfirmed.
- `duckdb-engine` for SQLAlchemy over DuckDB: predates 2.0.
- diskcache, asyncache, pickled cache persistence, a CLI daemon now, TTL expiry for content-identified results
  (reasons in [cache-design.md §6](unified-domain-model-and-execution/cache-design.md#6-crossing-processes)).
- A generic dependency-tracking cache framework: identity keys suffice.

<a id="probes"></a>

**Probes run by this reviewer** (synthetic data only, scratch directory outside the repository, 2026-11-18):

1. cachetools 8.0.1 from the downloaded sdist under CPython 3.14.10: nine threads over two keys with
   `cached(LRUCache(16), condition=Condition(RLock()), info=True)` ran the loader twice,
   `CacheInfo(hits=7, misses=2, maxsize=16, currsize=2)`; four threads calling a raising loader under
   `condition` ran it four times in 0.20 s (no shared exception); `cache_clear()` during an in-flight load was
   followed by the load's insert (`{(1,): 'old'}`); an `LRUCache` subclass's `__delitem__` saw both eviction and
   `pop` (`[1, 2]`) while `clear()` bypassed it.
2. DuckDB 2.0.0 with pyarrow 26.0.0 (project virtual environment, read-only use): projecting a missing column
   raised `BinderException` at relation construction; `union` returned six rows for three plus three
   (bag semantics) and two after `distinct()`; `columns` and `types` were available without executing.
3. Revision of 2026-11-18, by the revising reviewer: a scripted, read-only comparison of the frozen files
   `target_alembic/versions/semantic_ddo_pe_n28_native.json` and `semantic_ddo_pe_n29_native.json` in the
   `5139eaba3` snapshot (standard-library Python in isolated mode). Both hold 585 desired objects with
   identical identity sets; 9 objects differ; after replacing every 64-hex string by one token, none differs.
   The two `_admission.sql` files are equal under the same masking. The masking is a heuristic and would hide a
   real change to another 64-hex literal. This is a comparison of repository files, not a library probe.

Other library facts come from the contributor reports, labelled there.

## 11. Alternatives and tradeoffs

| Alternative | Change propagation | Semantic authority and composition | Total machinery and risk | Decision |
|---|---|---|---|---|
| Current baseline | Multi-site edits for families, roles, guards, programs; unrelated edits invalidate kernel, release and receipts | Hand lists beside a sound compiled operation model | No new machinery; fail-open omissions; repeated generation on the execution path | Not retained |
| Proposed design | Local: one declaration per governing fact; identity changes follow bytes and declared dependencies | Five authority kinds with supported derivations; one composer | New: declaration schema, profile check, program registry, derived code identity, cache owner and store (each small); removes more than it adds | Selected |
| Library-maximal variant (LinkML for operations and programs too; LinkML SQL generators) | Similar for domain facts | Pushes procedural and code facts into a schema language (ADR-0131's rejected option 2) | Larger and lossier; generators lack PostgreSQL features | Rejected |
| Simplest viable variant (transcribe nothing new; add completeness tests to the hand lists; hold the capture) | Still multi-site | Lists stay authorities | Least new code; tests mirror the lists and cannot refuse an inconsistency at compile | Rejected for A2; acceptable only as an interim guard |
| Required total classification (this review's first round: every operation declares a family with explicit `none`; closed vocabularies throughout; absence refuses) | Local | Removes the fail-open state but conflates "not applicable" and "not yet decided" by forcing a choice; closes descriptive fields that are open today | Small, but every new operation must decide its validity semantics before compiling, and an operation in two families needs a schema change | Not selected (recommendation audit, 2026-11-18) |
| Declared homes with explicit openness and safe defaults (selected) | Local | Integrity memberships closed; operation classifications three-state; vocabularies declare openness | Adds one conservative validator program and an openness declaration; removes two would-be mandatory fields | Selected |
| Operation model as a generator input (revision of 2026-11-18: the alternative that the converted modules invite) | Every operation edit changes generated bytes, the kernel identity and the native revision | Facts derivable at generation, but per-release facts baked into a release-independent kernel | No new mechanism; one native revision per operation edit | Rejected |
| Run-time selection by lowered, declared attributes (revision of 2026-11-18; selected for R02 and R07) | Operation edits change the release only; model-level vocabulary edits change the kernel | Membership declared beside the operation, lowered once per release, read by every selection point | One lowering change and one predicate per guard; the pattern exists in rich admission | Selected |

What becomes easier: adding operations, families, roles and fields; trying operations and vocabulary terms before
they are settled; library bumps; previews; CLI paging. What becomes harder: unclassified operations pay for conservative
re-validation until they are classified; and (revision of 2026-11-18) the extraction of the transcribed facts costs
native revisions and one re-preparation of releases, where the first text expected the conversion itself to absorb
that cost.

## 12. Verification and uncertainty

| Claim | Label and date | How it would be settled |
|---|---|---|
| Family is not derivable from compiled fields | Interface-checked by source inspection, 2026-11-18 (all 27 literals extracted statically) | Already settled for the current set |
| The per-acquisition check can use the release's recorded kernel identity | Interface-checked, 2026-11-18 | A traced acquisition after R06 |
| Identical bytes after a library patch imply unchanged behavior of installed programs | Proposed (reasoning: installed behavior is the installed bytes) | — |
| Derived code identity covers what hand lists covered | Proposed | Compare the derived closure with `LOWERING_FILES` and the query custody lists once; the two known omissions must appear |
| Continuation pages are sound across processes keyed by cut | Proposed, from the in-process soundness argument | Native owner review of the cut's pins |
| Content basis for fresh requests | Open premise (DA-075) | Native owner's argument that derived rows depend only on frontier content |
| Role-granular watermark | Open premise (DA-078) | Native owner's soundness argument |
| Carrying release-content proof | Open trust decision (DA-033) | Operator decision |
| Materiality of each removed repetition | Unmeasured by design | Measure only if a plan step depends on the size |
| A conservative premise check can be realized for unclassified operations from recorded trust snapshots and validator identities | Proposed (recommendation audit; premises partly recorded, `data-operation-physical.yaml:458–484, 619–631`) | Native owner's confirmation that each episode can be tied to the trust snapshot it consumed |
| LinkML 1.12.1 has no openness flag on enums; `recommended` slots warn through `RecommendedSlotsPlugin`; permissible values carry `status` | Observed in installed source, 2026-11-18 (recommendation audit) | — |
| Revision N29 changed no generated statement, only digest literals (kernel digest, renderer pin, execution-contract descriptor) | Interface-checked by scripted comparison of the frozen files, 2026-11-18; substitutions mapped one to one by the audit's independent challenge | — |
| The generated release guard already requires the archived native digest to equal the installed descriptor | Interface-checked by source inspection, 2026-11-18 (`semantic/native_admission_release.py:516–533, 609–622`) | A traced acquisition after R06 |
| Family membership can be lowered from the archived declaration without a generator input | Interface-checked for the host (lowering already reads the archived effective operation and lowers its dependencies, `semantic/data_operation_compiler_native.py:900–926`); the remedy is Proposed | The first family moved in R07 step A |
| A wrong family claim can cause refusal but not a fail-open result | Proposed (reasoning: validity is a conjunction; guards refuse) | Native owner review of each family validator for checks that could widen validity |
| A third query encoder admitted by the declared roles is refused by the kernel | Inferred by the audit from two texts, not run | A preparation and completion of such an operation |

**What would change the judgment (revision of 2026-11-18).** If a family validator's soundness
depends on the specific implementation of its members beyond what a family can declare of them
(roles, forms, profile, effects), its per-operation pins remain, but as a declared, closed owner
list on the family member (an integrity membership in the model and a generator input), not as a
tuple in generator code. If lowering cannot carry a declared family because the archived effective
model omits it, the field is added to the archive format once, which costs one re-preparation of
releases, not a change of route.

**What would change the judgment.** If the conservative premise check proves unrealizable, unclassified operations
must at least lose reuse across premise changes, or classification becomes required for operations that consume
trust-bearing cuts. If family membership proves derivable from declared input roles, it is derived and the field
becomes an override. If no operation ever needs two families, the set-valued field can be simplified. Evidence that generated bytes depend on ambient state not captured in the generation
key (would require adding it to T2's key). A finding that the effective-model archive's SQL readers depend on field
names that LinkML generation would change (would slow the declaration-schema step, not reverse it).

**Unexamined breadth, not defects.** Generator bodies for equivalence; `schema/rulelang.py`; the ontology path;
migration bodies; the CLI beyond paging.

## 13. Rule impacts

The review does not change these rules; plan creation presents them for confirmation. The last column marks each for the operator after the revision of 2026-11-18: ready as written, changed in this revision, or no longer needed (none is no longer needed).

| ID | Rule and where recorded | Proposed change | Depends on it | If the rule is kept | Status (revision of 2026-11-18) |
|---|---|---|---|---|---|
| review#RC01 | ADR-0131 and §B4/§B5: typed programs compose procedural forms; three exceptions | Add: facts that programs dispatch on have one declared home and programs read it instead of restating it; per-operation facts reach programs through the release (lowered definition rows read at run time), and only model-level vocabularies and their member declarations are generator inputs; an undecided membership is declared as undetermined and programs apply its stated conservative consequence; generation refuses only internal inconsistency (a name without a definition, a dispatch without a handler) and omissions in the integrity layer (roles, grants, guards, support-edge kinds, privileged-effect owners); independent controls take expectations as data, never spliced text. The clause "each module's conversion follows the declarations it reads" is replaced, because the conversion has happened, by: operation facts transcribed into generators are extracted to their declared homes (revised by the recommendation audit; revised again on 2026-11-18) | R02, R07, R16 | The transcribed family and role lists stay in the generators, every membership edit stays a kernel edit, and the guards keep their early returns | Changed in this revision |
| review#RC02 | ADR-0131's scope is PostgreSQL only | Extend "no maintained SQL text in application code" to SQLite scratch stores and DuckDB use | R07, F04 | SQLite text remains an accepted, low-risk exception | Ready as written |
| review#RC03 | §B5 "one captured LinkML closure" with per-artifact closures | One composer and one compiled model per model-sources identity; per-artifact sub-identities kept | R01 | Per-consumer composition continues | Ready as written |
| review#RC04 | ADR-0092: two operation authoring routes compiled into one model | Keep both routes; add that the Python route's grammar and vocabularies are declared in LinkML, that each vocabulary declares its openness, that descriptive fields stay open, and that literals are validated against the declaration with closed field names | R02, R15 | Hand grammar validator remains; vocabularies stay Python literals | Ready as written |
| review#RC05 | DDO plan, products and support: `validity_family` null when no per-kind validator applies (`products-and-support.md:422–423, 451`) | Null stops meaning "no per-kind validator applies"; that meaning is declared as `none`; absence means undetermined and receives conservative validity; the field may hold several families (revised by the recommendation audit; replaces "required enum with explicit `none`"; the column is lowered from the operation's own declaration instead of from a kernel classification program, and guards select by it (revision of 2026-11-18)) | R02, R16 | Forgotten and not-applicable stay indistinguishable and permissive; A2 MUST gap stays | Changed in this revision |
| review#RC06 | DDO plan: completion seal and receipts keyed by the kernel digest; full battery on mismatch (`products-and-support.md:428, 528, 534`) | Validator identity per family; recorded reconfirmation | R05, R11 | Replay amplification after any captured edit remains | Ready as written; evidence strengthened (N27 kept the whole digest in the seal; N29) |
| review#RC07 | DDO plan: watermark over prerequisite operations and exact pins (`products-and-support.md:574–575`) | Drop the kernel component now; role granularity after the soundness argument | R10 | Waiting-obligation skip stays largely unrealized for the one-source workload | Ready as written (a role-matched component was added beside the kernel component) |
| review#RC08 | Admission re-proves release content per acquisition (current native admission design; DA-029 trust premise) | Carry finalization and deployment-admission receipts; explicit verification command | R11 | Per-acquisition re-hashing of immutable content remains | Ready as written (the guard is now generated and re-proves the same content) |
| review#RC09 | ADR-0124 and file custody: drift refuses and requires restart | Keep for Python code; for model declarations, a changed source yields a new compiled model | R01, R09 | Model edits require restarting the MCP server | Ready as written |
| review#RC10 | ADR-0124: serving identity names the listed running code | Derived import closure under the same custody mechanism | R05 | DA-076 stays | Ready as written |
| review#RC11 | Release id hashes generator sources and the whole native capture (`semantic/prepare.py:956–985`; native capture as dependencies) | Generated artifacts and model capture in the id; generator provenance recorded beside | R05 | Generator edits force new releases | Ready as written (unchanged at `semantic/prepare.py:975–986`; preparation still passes the whole capture) |
| review#RC12 | Role constants and default read roles in code (`semantic/alembic_privileges.py:25–35`); host bootstrap reads them | Role and purpose vocabularies in the model; read roles declared per schema with per-relation overrides, no code default | R02, R03 | Privilege policy keeps no model owner | Ready as written; locations refreshed (`semantic/alembic_privileges.py:25–33`; role tuples now also in `semantic/native_admission_tables.py` and `semantic/native_admission_principals.py`) |
| review#RC13 | Production-efficiency realization of the query cache (process-local, keyed by cut; PE-F17, owned by the DDO plan) | Declared reuse basis; disk tier for CLI continuation | R09, R10 | CLI paging never reuses | Ready as written |
| review#RC14 | ADR-0024 and the D2 preparation contract: unsupported required semantics refuse; preparation diagnostics are refusing except unchecked terms | Add: preparation distinguishes refusing diagnostics (unsupported or inconsistent semantics, integrity omissions) from non-refusing `unassessed` diagnostics for undetermined declarations, and records the promotion boundary, if any, at which undetermined declarations refuse (none, default-release activation or knowledge publication; the operator chooses) (added by the recommendation audit) | R15, R16 | R16 still works through the existing `unchecked` route, but the promotion boundary stays undecided | Ready as written |
| review#RC15 | Native revision practice, recorded implicitly: the descriptor check refuses execution whenever the checkout's kernel digest differs from the installed descriptor (`semantic/data_operation_storage.py:1127–1142`), so a new frozen revision is authored and deployed for any digest change (observed at N29; revisions narrated in `docs/plans/declared-data-operations/postgresql-realization-and-retirement.md`) | A revision is authored when the set of installed program identities differs; its operations are the programs whose identity changed; a candidate with none is not authored; the kernel identity is computed over the desired objects' program identities | R05, R04 (descriptor program) | Byte-identical restamp revisions continue, each freezing a full catalog snapshot and replaying older receipts | New in this revision |

Not a rule change: moving cachetools from 7.2.7 to 8.0.1 is ordinary dependency judgment (it changes the served
identity once). Deleting `semantic_alembic/` and `alembic/` needs the operator's decision; the rule protecting plans
and evidence does not name migration trees.

## 14. Order of work

**Revised 2026-11-18 at `5139eaba3`.** The first order made the remaining conversion (its step 5) wait
for the declared homes of the facts each module reads. That step has been overtaken: the statements
are converted and the facts transcribed. The order below replaces it; the original is recoverable
from Git at `c25cada3f`.

Priority by consequence: the fail-open validity families and the stale-code reuse across processes (correctness and
fidelity) first; then execution-path amplification and revisions that change no installed byte; then cache reuse.

Prerequisite order by the capability each step supplies:

1. **Compiled model holder and cache owner (R01, part of R09).** Supplies the one object that every later
   derivation reads. Includes the cachetools 8.0.1 move.
2. **Family declaration and run-time selection (R02 revised, R07 step A, then R16).** Supplies the optional
   `validity_family` field, the `ValidityFamily` vocabulary with validator programs and member requirements,
   lowering from the archived declaration, and selection by the lowered column in every guard, validator and
   dispatch. Needs step 1 only for the vocabulary's home; the lowering and predicate changes need nothing else.
   R16's conservative program follows; until it lands, undetermined operations keep today's treatment and are
   listed. The ownership vocabulary, the grammar migration and derived source collections belong to R02 but gate
   nothing here.
3. **Role, purpose, guard and read-role declarations (R02, R03; R07 step B).** Supplies the integrity vocabularies
   and schema defaults the role and grant literals move to. Independent of step 2.
4. **Program registry (R04, remaining part).** Supplies program objects with identities, the descriptor program and
   the catalog-check sub-program. The typed trigger and view forms are already delivered. Independent of steps 2
   and 3.
5. **Identity layering, code custody and revision practice (R05, RC15).** Needs step 4 for program identities.
6. **The single support walk (R08).** Needs the edge declaration of R02.
7. **Carried assurance (R11).** Needs step 5 for validator identity and the operator's trust decision.
8. **Disk tiers and served reuse basis (R09, R10).** The content basis needs the native owner's premise.

Can proceed independently now: R06 (delete the two capture rebuilds; small and high value, and the generated release
guard already does the comparison that matters); the connections of already-declared facts in R07 (shared-stream
triggers, state literals, universe literals, codec tags, product member families, encoder codes), batched into one
native revision; interim consolidation of role literals onto the existing constants; retargeting the model preview's
SQL explanation to the generated-SQL snapshots (R07); R17 (source demand reads the archived slices); the two small
text sites of R07; continuation-page reuse for the CLI (cut-keyed); bounding and locking the unbounded and unlocked
holders (F02); DuckDB connection settings (F03, DA-020); the retirements of R13 that need no decision and do not touch
the earlier model's openness rule; R14.

**Test seams (one line each).** Tests importing the `semantic.metadata` globals move to the accessor; native
authoring fixtures move to the program registry; family dispatch, the three family states, selection by the lowered
column and the conservative validator need independent tests, which the test review owns; deployment-key tests change
if release dependencies change (R05).

## 15. Architectural judgment and decision

| Judgment | Verdict | Scenario evidence | Action |
|---|---|---|---|
| A1 Localize change | Violated | Adding an operation, a family, a role, or editing a generator propagates across unrelated owners (§7); at `5139eaba3` adding an operation to a family edits up to twelve lists and authors a native revision | R02, R04, R05, R07 |
| A2 Encode domain meaning explicitly | Violated | Governing facts without model authority; an unlisted member fails open, now at three levels; "not applicable" and "not yet classified" share one representation; vocabulary openness is declared only in the retiring model; the earlier model duplicates value sets; a release attributes results computed under working-tree slices | R02, R03, R08, R13, R15, R16, R17 |
| A3 Extend through composition | Violated | A new program or family needs three to five registry edits (the lists grew by hand in the range); each consumer composes its own model | R01, R04 |
| A4 Fit execution to the workload | Violated | Generation on the execution path (each rebuild larger); invalidation far broader than premise, observed once as a revision that changed only digest literals; no CLI reuse; no coalescing of identical misses | R05, R06, R09, R10, RC15 |

**Bounded decision: Revise** (unchanged by the revision of 2026-11-18). **Enclosing architecture: needs revision**,
around the preserved core named in §2, which the range strengthened: relations and columns are now model-resolved in
every converted program. Evidence strength: Interface-checked by source inspection, 2026-11-18 (at `d78c98765`, and
for the revision at `5139eaba3`); remedies Proposed. Review acceptance is distinct from release qualification.

**Next decision and owner.** The operator confirms or rejects RC01 to RC15 in plan creation, including the promotion
boundary of RC14, whether `Ownership` stays open, and RC15's revision practice; the first plan steps are R06 and the
already-declared connections of R07, alongside R01, with the family declaration and run-time selection (R02 revised,
R07 step A) as the decision that removes the fail-open lists.

## 16. Returned to the audit (out of focus)

- DA-079 (typed busy refusal for a second concurrent run) is outside this focus; it stands as recorded.
- `schema/rulelang.py`, the packs' custom rule language, was not examined; whether it should become LinkML `rules`
  or stay is open.
- `ingest/pdf_stream_reconciliation.py:260–261`: `pin_json` duplicates `input_key` (a defect noted by the generator
  lane; the file has no commit in the range).
- `serve/source_catalog.py:117–129`: one native read per catalog row (N+1; no commit in the range).
- `ingest/pdf_capacity.py:19–20`: sticky GPU quarantine globals with no clearing route (no commit in the range).
- `serve/companion_export.py:582–600`: unbounded materialization of export differences (no commit in the range).
- [DA-065](../audit/semantic-model-and-authority.md#da-065) (revision of 2026-11-18): per the audit's independent
  challenge, not a regression. The production producer always attaches the witness and admission checks the
  attested reply; what was lost is the independent enforcement at three retired sites. It is a changed footprint for
  the audit's test and assurance owners; this target adds nothing for it.
- Frozen revisions freeze the full catalog state again each time (about 206 MB for N14 to N29 as ordinary Git
  blobs); storage of frozen revisions belongs to the lifecycle owner (R05 revision).

---

## Coordinator publication note — 2026-11-18

The coordinator, who wrote the audit this review consumes, prepared the brief, the pinned
snapshot and the contributor reports now published as
[review inputs](../evidence/2026-11-18_production-review-inputs/README.md), and did not write
the review. The brief first described the model-owned SQL conversion as complete; the
independent challenge of the audit refresh corrected that, and the reviewer received the
correction before finishing. Before placing the review the coordinator checked the decisive
lines of finding F01 against the snapshot (`semantic/data_operation_storage.py:1116–1131`,
`:1069–1070`; `model/semantic/data-operation-physical.yaml:22`); they match. The review text
above is the reviewer's; only link targets were changed for placement.

**Reconciliation at publication.** `main` was at `90467bde0`, five commits after the baseline
`d78c98765`. None of them changes a file under the production package, so every source
citation above is as read. Uncommitted work by other sessions was not read.

### Coordinator note on the revision of 2026-11-18 at `5139eaba3`

The revision above was written by a third independent reviewer from input revision
`c25cada3f`, consuming the audit update published as `568d70596`
([inputs](../evidence/2026-11-18_production-audit-update/README.md)). The independent
challenge of that audit update reached the reviewer before the revision was finished. The
coordinator did not write the revision; only this note was added at placement. `main` was at
`5139eaba3`, the revision's baseline, when it was published, so no later source change is
unreconciled. Uncommitted work by other sessions was not read.

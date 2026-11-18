# Independent read of the UDM plan series drafts (focused advice, not a formal review)

Reader: design reviewer, wrote none of the drafts. Date 2026-11-19 (session clock 2026-11-18).
Inputs: the seven drafts in `drafts/`, `RULINGS.md`, `DRAFT_BRIEF.md`, `COMMON.md`, the four
investigations, the review (`snap7/docs/design_review/reviews/design_review_unified-domain-model-and-execution_2026-11-18.md`),
its `dispositions.md`, the outline of `cache-design.md` and of the recommendation audit. Source
facts below come from the frozen snapshot `snap7/` of `cb4e09667` and are labelled
**Interface-checked by source inspection, 2026-11-19**; paths are relative to
`snap7/python/corpus-structure/src/corpus_structure/` unless stated. Nothing was run except
read-only `grep`/`sed` and one isolated stdlib count over a frozen JSON file. Section (d) says
what was not read.

Severity: **must fix** = the series would be wrong, contradictory, unexecutable or would lose a
source item if placed as is; **improve** = clarity, evidence strength or a smaller risk.

---

## (a) Coverage table

"Route" names the package (or decision/deferral/handover) that owns the item in the drafts.
**GAP** = no route; **partial** = gestured at, or routed on one side only.

### Recommendations R01–R17 (as revised)

| Item | Route | Note |
|---|---|---|
| R01 compiled model, one composer | UDM-01 (+ T1 in UDM-13) | covered |
| R02 vocabularies, grammar, lowered facts, DA-073 composition, DA-001/DA-040 connections | UDM-02, UDM-05, UDM-06; DA-073 in UDM-05; DA-001/DA-040 in UDM-18 | covered |
| R03 typed physical profile | UDM-03 | covered |
| R04 program registry, callee check, catalog-check sub-program | UDM-09 | covered; grants half partial (defect 12) |
| R05 identity layers, code identity, RC15 | UDM-10, UDM-11 | covered; acceptance thin for two layers (defect 20) |
| R06 execution path generates nothing | UDM-08 | covered |
| R07 categories | see "Remaining-SQL categories" below | covered except TEMP-grant double ownership (defect 6) |
| R08 support-edge meaning | UDM-07 | covered; blocking premise P5 |
| R09 cache system | UDM-13, UDM-14 | covered; X2 and G4 parts missing (defect 11) |
| R10 reuse basis and watermark | UDM-13 (basis), UDM-15 (content basis), UDM-12 (watermark) | covered |
| R11 carried assurance | UDM-12 | covered |
| R12 DuckDB conditions | UDM-16 | covered; `cp:` derivation for D2 missing (defect 11) |
| R13 retirement | UDM-04, UDM-19, UDM-16 | covered; `acquire_publication_port` missing (defect 10) |
| R14 scientific policy | UDM-18 | covered |
| R15 declared openness | UDM-02 | covered |
| R16 graded consequences | UDM-06 | covered |
| R17 release-bound pack inputs | UDM-18 | partial: only `slices.yaml`; review says "and siblings" (defect 36) |

### Review findings F01–F05

F01 UDM-08; F02 UDM-13 (T6, closure by inspection); F03 UDM-16; F04 UDM-17; F05 UDM-02 then
UDM-04. All routed.

### Rule impacts RC01–RC15

All fifteen appear in the coordinator's rule-change table with a route and a consuming package.
Gaps in the route column: RC14 changes ADR-0024's stated rule, which two companions list as
superseded, but UDM-00 plans no record for ADR-0024 (defect 29). "Amends" (coordinator) versus
"superseded by a record" (model and programs companions) for ADR-0092 and ADR-0124 (defect 29).

### Fact-authority table (review §6, 42 rows)

| Row | Route | Row | Route |
|---|---|---|---|
| Record and product shape | UDM-01; earlier copies UDM-04; **"hand Arrow schemas for model relations": GAP** | Roles | UDM-03 |
| Field type and constraint | UDM-03; universe literal UDM-02/05 | Purpose to role | UDM-03 |
| **Field kind to database and Python type (four maps)** | **GAP** (defect 11) | Table read grants | UDM-03 |
| Domain value sets | UDM-02, UDM-04; **"one of the PDF outcome pair": GAP** | Execute grants | UDM-03, UDM-09 |
| Operational vocabularies | UDM-02 | Task states | UDM-05 (connections) |
| Operation existence | UDM-02 | Wire shape and ABI | protocol kept; validators to T1 (UDM-13) |
| Validity family membership | UDM-05, UDM-06 | Value-codec vocabulary | partial: kernel side UDM-05; Python `_TEXT` tuple unrouted |
| Family contract | UDM-05 | Native program set | UDM-09 |
| Per-operation contract facts, `support_contract` boundary | UDM-05 | Generated outputs (facades) | UDM-09 |
| Support-edge meaning | UDM-07 | Code that determines an artifact | UDM-10 |
| Operation dependency graph | UDM-07 | Scientific policy | UDM-18 |
| Release composition | UDM-05 (DA-073) | **Custom catalogs as LinkML-typed instance data** | **GAP** (defect 11) |
| Relation physical layout | UDM-03 | Operation-local analytical shapes | UDM-16 |
| Frontier-guard membership | UDM-03 | **Companion `cp:` grouping and provenance columns** | **GAP** (defect 11) |
| Shared-stream trigger membership | UDM-05 | Identity determinants | UDM-10 |
| Vocabulary openness, member status | UDM-02 | Undetermined declarations | UDM-06 |
| Privileged-effect ownership | UDM-05 | Product member families | UDM-05 |
| Encoder failure codes | UDM-05 | Value admissibility bound | UDM-18 |
| Release-bound pack inputs | UDM-18 (partial) | Semantic release annotations | UDM-01 |
| Qualifier partition | UDM-18 | Principal restrictions, schemas, private kernels | UDM-03 |
| Catalog-check boundaries | UDM-09 | Pack rule language | returned to audit (review); not plan scope |

### DuckDB judgment table (review §5)

Every row is carried in the analytical companion's decided table. Disagreements: X2
("carried status in the custody tier, UDM-13") is not in UDM-13's scope, whose T0 says "nothing
migrates" (defect 11); G4 "held in T1 with the compiled model" is not in UDM-13's T1 list
(defect 11); D2's "derive grouping and excluded columns from `cp:` annotations" was dropped
(defect 11); G5's "index revocations by node" is not mentioned (improve, defect 11). D1 and I8
conditional rows are routed, but D1's settlement point violates the credit rule (defect 1).

### Remaining-SQL categories (review R07 table, 17 rows)

Family membership: UDM-05/06. Per-operation pins: UDM-05. Privileged-effect owners: UDM-05.
Roles, purposes, grants: UDM-03 (+UDM-09). Frontier guard: UDM-03. Already-declared facts:
UDM-05 (RULINGS 7). `support_contract` paths: UDM-05. TEMP grant: **UDM-03 and UDM-17 both**
(defect 6). Native fitting path: UDM-19. Independent control SQL: UDM-03 (role names as data).
`literal_column`: UDM-17. Text handoff: UDM-09. Free callee names: UDM-09. Preview SQL
explanation: UDM-19. SQLite: UDM-17. DuckDB: none. Frozen migrations and authored SQL: UDM-19.

### Cache tiers

T1 UDM-01/UDM-13; T2 UDM-13 (after UDM-09); T3, T4, T5, T6 UDM-13; D2, D4 UDM-14; T0 custody
registers only (correctly not counted among the six, as `cache-design.md` §3 says). Covered.

### Finding dispositions

DA-068 to DA-086 (all nineteen), DA-033, DA-058 (deferred, trigger), DA-001, DA-004, DA-020,
DA-028, DA-040 and DA-065 (retained) all have coordinator rows that agree with
`dispositions.md`. DA-086 split per RULINGS 7 is stated in the companions but not in the
coordinator row (defect 3).

### Open premises and uncertainties of the review (§12, §15, "what would change the judgment")

| Review item | Route |
|---|---|
| Family not derivable | settled (UDM-05 writes 27 explicit declarations) |
| Per-acquisition check can use the release's value | UDM-08 acceptance |
| Identical bytes after library patch imply unchanged behaviour | carried as design reasoning (UDM-10/11); fine |
| Derived code identity covers the hand lists | UDM-10 acceptance (two omissions) |
| Continuation pages sound across processes (native owner review of cut pins) | settled by reading in programs companion correction 4 and used by UDM-14; **the review asked for native-owner review**; improve: record it as settled by reading, name what would reopen it |
| Content basis (DA-075) | UDM-15, premise D1 |
| Role-granular watermark (DA-078) | UDM-12, premise W1 (RULINGS 2) |
| Carrying release proof (DA-033) | accepted with RC08 (T1) |
| Conservative check realizable | settled with requirement (P6, UDM-06) |
| **A wrong family claim can cause refusal but not fail open (native owner reviews each validator for widening checks)** | **GAP** (defect 14); UDM-05 asserts it as reasoning only |
| Third query encoder admitted | UDM-05 acceptance |
| Promotion boundary (RC14) | operator: none |
| Whether `Ownership` stays open | decided open (UDM-02) |
| Fallback if a family's soundness needs per-member pins (closed owner list on the family member) | partial: UDM-05 allowed sets; fallback not named as a reopen condition |
| Generated bytes depending on ambient state not in T2/D2 key | not routed (improve) |
| Archive SQL readers depend on field names LinkML generation would change | not routed (improve; UDM-02 risk) |
| Operator option: an identity-excluded notes field (recommendation audit) | not recorded as declined or open (improve) |

### The 24 taken-over validation obligations (VALIDATION.md A1–A24)

All 24 have a row in the qualification companion (1–24) with package, route and standing (carried,
restated, dropped, excluded). A22 excluded (Chandra), A23 dropped into UDM-20 and obligation 3.
Inconsistencies: obligation 4 versus UDM-22 triage (defect 24); obligation 19 executability
(defect 26). Not routed: the TDM "production context owned outside" items listed at the end of
VALIDATION.md (defect 30).

---

## (b) Defects

### 1. Credit rule broken by decisions taken from final-run observations — **must fix**

*Where:* cache companion, "Where sizes are declared" (three defaults "chosen at execution" settled
by "the whole-book run") and premises M1, S1 ("Observation during qualification (UDM-22,
UDM-23)"); lowered companion, open premise "Project-wide share locks … Observation during the
whole-book run (UDM-23); it settles whether the lock is held"; analytical companion D1 row
("records the per-invocation input row counts … in particular the whole-book run of UDM-23 …
the views move to plain Python in a follow-up"); coordinator "Evidence status" ("The series plans
measurement in one place").

*What is wrong:* each of these changes source (a settings default, a lock branch, a placement)
after the final run that is supposed to qualify that source. Under the series' own rule ("no
earlier run earns credit for source that changed afterwards") the change would void UDM-22/23,
and repeating the book run for a default is not intended. The coordinator's "measurement in one
place" is also untrue as drafted.

*Correction:* fix values before final source and make any later change a follow-up outside the
series. Replacement for the cache companion's paragraph beginning "Three defaults are…":

> Three defaults are set at implementation from evidence available before final source: the
> retained bytes of releases prepared on stage (`release_bytes`, never below today's eight
> releases), the model-file sizes of the loaded CPU runtimes (`runtime_bytes`), and the macro
> tables seen in UDM-20's bounded reproductions (`parser_entries`). They are not changed once
> UDM-22 starts. If UDM-23's retained observations show one to be wrong, the change is a
> follow-up deferred with that observation as its trigger, outside this series' final source.

Same pattern for the lock premise (replace "settles whether the lock is held" by "a material
contention observed in UDM-23 is the trigger for a deferred follow-up that records the epoch map
without share locks; the series ships the locking design") and for D1 (already deferred in the
coordinator; say in UDM-16 "the follow-up is outside this series"). Coordinator "Evidence status",
replace the last two sentences with:

> The series plans one measured diagnosis, UDM-20, because an unexplained failure to complete the
> book is a risk to finishing at all. Qualification runs retain a few named observations (cache
> footprints, rich-rule input sizes, lock waits); none is a target, and a change they motivate is
> a follow-up with that observation as its trigger, outside the series' final source.

Also verify at UDM-16 entry that "ordinary runs already produce" per-invocation row counts; if they
do not, recording them must land before final source.

### 2. Nearly the whole book pipeline would run under conservative validity — **must fix**

*Where:* lowered companion UDM-05 ("writes an explicit `validity_family` on the 27 operations that
are classified today"), "Old rows convert with null becoming conservative", UDM-06 consumer scope
("Every operation that today sits outside the classifier's list … becomes conservative, by
design … the operator may declare `none`"); qualification UDM-23.

*What is wrong:* the classifier covers contextual, definition, artifact, operation-event,
record-grade/fit and rich operations only (`semantic/data_operation_compiler_native.py:470–535`,
27 ids, checked). Capture, organization, discovery, sentence annotation, canonical projection,
formal evidence, math, HanLP, construction and the composition are all outside it. After UDM-05
and UDM-06 each of their completions takes share locks on **every trust scope of the project**
inside the settlement transaction, whose `lock_timeout` is 5 s (`semantic/claim_lifetime.py:204–211`,
`settings.py:71`), records a project-wide snapshot per receipt, and is invalidated by any trust
change in the project and, until UDM-10, by every kernel change. The previous book run failed
precisely in settlement. The DDO specification's documented meaning of null was "no per-kind
validator applies" (`products-and-support.md:422–423`); the series replaces it with conservative
treatment for all of them without anyone deciding, operation by operation, which null was
deliberate. That is a behaviour change across the main workload and a direct risk to UDM-23, not
an exploratory affordance.

*Correction:* add to UDM-05's first steps:

> The entry step lists every operation outside the 27 and, with its owner, declares `none` for
> each whose null today means, by design, that only generic validity applies (the DDO
> specification's meaning). Only operations whose owner cannot decide are left undetermined. The
> list and the declarations are recorded in the package's completion note; at least one real
> operation that the book run exercises, or a fixture operation run on stage, remains
> undetermined so that T1 is observed on real material.

In UDM-06's cost paragraph, add the settlement interaction: "the share locks are taken inside the
completion transaction under the 5-second lock timeout; a revocation in the project during a
completion therefore surfaces as a lock timeout classified as an operational failure." In UDM-23's
pass list, state the expected count of conservative operations. Nothing here is forced on an
exploratory operation: declaring `none` is the owner's positive claim.

### 3. Coordinator not brought into line with RULINGS.md — **must fix**

Exact corrections to the coordinator draft:

- Queue row UDM-04: Needs `UDM-01, UDM-02`; Delivers append "; the model-change preview's
  successor (a comparison of two compiled models)" (RULINGS 6).
- Queue row UDM-09: Needs `—` (RULINGS 4); add "reads the compiled model of UDM-01 where it has
  landed".
- Queue row UDM-10: Needs "code-identity slice: none; program, kernel and validator slice:
  UDM-09 and UDM-05" (RULINGS 3).
- Queue row UDM-14: Needs "UDM-13; for D2 also UDM-10's code identity and program identities
  (see defect 16); D4: UDM-13 only" (RULINGS 3).
- Queue row UDM-19: Needs "None for the preview retarget, the migration trees, the dead fitting
  functions, the modules with no production importer and `acquire_publication_port`; the
  release-side authored-SQL removal joins revision B if it changes installed bytes" (RULINGS 10,
  14; see defect 10 on why UDM-04 is not needed).
- Queue row UDM-21: Delivers append "; defines the named re-adoption check that UDM-23 repeats"
  (RULINGS 12). UDM-22 Needs: add UDM-20 (the qualification companion says so).
- Disposition row DA-086: Package "UDM-02 (declared homes, Python copies); UDM-05 (kernel-side
  connections, revision A)" (RULINGS 7).
- "Native revisions" paragraph, replace with:

> **Native revisions.** The series plans three, authored and frozen close together in the order
> A, B, transition, and packages join them instead of adding their own. Revision A: UDM-05 and
> UDM-06, with UDM-18's decimal bound and any byte-changing repair from UDM-20. Revision B:
> UDM-03 and UDM-07, with UDM-19's removal of the release-side authored-SQL machinery if it
> changes installed bytes. The identity transition: UDM-10's native slice with the
> installed-object changes of UDM-11 and UDM-12 (and UDM-09's differing objects if premise B1
> fails); role-granular watermarking joins it only if premise W1 is settled before the freeze.
> Each revision forces every release to be prepared again. After the transition and UDM-11, a
> change that alters no installed byte produces no revision.

- "Environments during the series", replace with:

> **Environments during the series.** The stage follows each native revision (rollback-only
> replay, then deployment). Canonical development and the book project are adopted twice only: at
> the current head (N29) in UDM-21, and at the final head on entry to UDM-23, after the last
> revision is frozen. Qualification evidence is gathered on final source only: no earlier run
> earns credit for source that changed afterwards.

- Open-premise table: add the rows RULINGS 16 lists (UDM-04 preview successor and what the
  revision log must provide, blocking, operator; DA-001 partition connect-or-retire, default
  connect, UDM-18; no evaluation module serves golden generation, operator, UDM-19; Unicode parity
  check, default delete, UDM-19; K1 value kinds in served rows, UDM-14; server-side statement
  timeout, UDM-20), plus: DA-073 inventory (RULINGS 8, UDM-05); P1 `definition_identity`
  (UDM-05); P7 rich branches (UDM-05); lineage-walk owner statement (UDM-07); the programs
  companion's P1 "no consumer needs pre-transition releases" (operator confirmation, UDM-10);
  family-validator widening review (defect 14). Fix the wording of "Cut scopes lie in the
  request's project — Reading the acquisition programs" to "Reading
  `ddo_record_grade_completion_scopes` and its two siblings".
- Add a short section "Design choices made in authoring" listing RULINGS 13's five cache
  resolutions (no event publishers; observation once per request scope; nothing warmed in spawned
  workers; typed canonical JSON lines with a closed set of value kinds, a row outside it served
  but not written; `CacheSettings` with root `build/cache`) and saying the operator may revisit
  them.
- "Shared editing surfaces": add `settings.py` (UDM-20 binding deadline), `schema/model_change.py`
  (UDM-01 three compile sites, UDM-13 T2), `semantic/target_installation.py` (UDM-03 or UDM-17,
  UDM-09), `semantic/data_operation_storage.py` (UDM-03 grants and guard tuple, UDM-05, UDM-13
  fallbacks), `semantic/native_admission_release.py` (UDM-10, UDM-12, UDM-19).
- "Why this order": the start-at-once list omits UDM-01, UDM-09, the UDM-10 code-identity slice,
  UDM-13's owner module and T3–T6, and UDM-19's independent part.

### 4. Two homes for "which programs validate a family", and disagreement on what validator identity covers — **must fix**

*Where:* programs companion, "The program declaration" ("the validity families it validates, when
it is a validator") and "What UDM-10 consumes from UDM-05" item 1 ("Until a vocabulary member
names its program, the match is carried by the 'families validated' set on the validator's
program declaration"); identity table ("the family's validator programs and their transitive
callees"); lowered companion "The contract UDM-05 supplies to UDM-10" item 2 (validator *and*
`completion_guard` and `completion_live`).

*What is wrong:* the same fact (family to validator program) gets a declared home on the
`ValidityFamily` member (UDM-05) and a second one on the program declaration (UDM-09), which is
the duplication the series exists to remove. Under RULINGS 3 the native slice of UDM-10 needs
UDM-05, so the interim fallback never applies. And the two companions disagree on whether a
family's completion guard and live-completion program enter its validator identity, which decides
when seals replay.

*Correction:* programs companion: delete "the validity families it validates, when it is a
validator" from the program declaration and delete the second sentence of item 1; state "the
family-to-program mapping is the `ValidityFamily` member annotation (UDM-05); the registry
resolves those names to declarations". Then state one rule in both companions, for example:
"A family's validator identity is the digest over the program identities of its `validator`,
`completion_guard` and `completion_live` programs and their transitive callees" (or exclude the
guards and say why the seal does not depend on them). The identity table and item 2 must match.

### 5. Shared contract "Per-operation facts never enter generators" contradicts UDM-05 — **must fix**

*Where:* coordinator, shared contracts row "Lowered operation attribute"; lowered companion
"Privileged-effect owners stay closed" (owner lists naming operations are generator inputs).

*Correction:* replace the contract text's last sentence with: "Per-operation facts never enter
generators, with one deliberate exception: the declared owners of a privileged effect, which are
integrity memberships, are generator inputs, so a change of privilege changes the kernel."

### 6. The TEMP grant is owned twice with contradictory revision statements — **must fix**

*Where:* model companion UDM-03 (target design "The TEMP grant becomes a typed program"; delivered
list; Removed "the `DO` block built by concatenation"; Native revision "the typed TEMP grant
program … are the bytes that may differ"); analytical companion UDM-17 (owns it; "not an
installed program object … no revision").

*Source:* the grant is applied as `ExecuteSQLOp(target_database_privileges_sql())` in the
fresh-root bootstrap (`semantic/target_installation.py:950–951`) and appears in the frozen
`target_alembic/versions/semantic_ddo_current_root_upgrade.txt`; it is not a desired object of the
frozen native state (whose keys are `desired`, `operations`, `predecessor`, `privileges`,
`version`). UDM-17's reading is the right one.

*Correction:* the brief's table gives it to UDM-17. Remove it from UDM-03's target design,
delivered list, Removed list and Native-revision paragraph (which then reads "the bytes that may
differ are any guard trigger that a schema default adds"). UDM-17 keeps its "Native revision. None"
with the frozen root upgrade text as a standing exception.

### 7. UDM-11's detection is invoked before it exists — **must fix**

*Where:* model companion UDM-03 "once UDM-11 is in place nothing is authored for it"; analytical
companion UDM-19 Native revision ("UDM-11's rule decides which") and its last open premise
("UDM-11's detection").

*What is wrong:* under RULINGS 1, revision B is frozen before the transition, and UDM-11 lands
with the transition. Neither package can use UDM-11 to decide whether it contributes to B.

*Correction:* in both places use "a statement-by-statement comparison of the generated objects and
privileges with the head frozen revision (the comparison UDM-09's acceptance performs; before
UDM-09, a comparison of the generated script with the frozen statements)".

### 8. UDM-11 and RULINGS 2 disagree on whether UDM-11 changes installed objects — **must fix**

*Where:* programs companion UDM-11 "Native revision. None of its own; the detector is authoring
code. It first applies to revisions authored after the transition"; Sequence section ("UDM-11 and
UDM-12 … their installed-object changes are frozen in the same revision"); RULINGS 2.

*Correction:* the companion's description is the accurate one (a candidate-command change). Make
both say: "UDM-11 changes authoring code only and installs nothing; it is delivered together with
the transition revision so that every revision after the transition is subject to it." If the
coordinator intended that UDM-11 also removes installed digest literals, that belongs to UDM-10's
descriptor program and should be said there. Also, the Sequence section's "The coordinator orders
the two model revisions (A and B) against this one" should state the settled order A, B,
transition.

### 9. UDM-20's repairs and UDM-21's rationale do not fit RULINGS 11 — **must fix**

*Where:* qualification UDM-20 "A repair that changes installed program bytes joins native revision
A", its acceptance ("the bounded case that failed … completes after it"); UDM-21 "It follows
UDM-20 because a repair found there may move the head"; Prerequisites "UDM-20 supplies a head that
will not move again".

*What is wrong:* a byte-changing repair joining revision A is not installed until A is frozen and
deployed to stage, long after UDM-20's diagnosis; UDM-20 therefore cannot show "completes after it"
when it ends, and the head does not move between UDM-20 and UDM-21. There is also no fallback if A
is already frozen (UDM-18 has one; UDM-20 does not).

*Correction:* UDM-20: "A repair that changes installed bytes joins the next planned revision that
is not yet frozen (A, otherwise B, otherwise the transition). Its after-observation on the bounded
case is made on stage once that revision is deployed there; until then UDM-20's state is
'diagnosed; repair pending revision X'. A repair that changes no installed byte is observed at
once." UDM-21: replace the rationale with "It follows UDM-20's diagnosis, so that any cause found
in canonical-development state (the unresolved intent, leases) is settled before adoption; repairs
that change installed bytes arrive with the series' revisions, not here."

### 10. UDM-19 omissions and an inverted dependency — **must fix**

- `acquire_publication_port` (no caller; `semantic/data_operation_admission.py:375`, checked) is
  "left for UDM-19 to retire" in the programs companion and RULINGS 14, but UDM-19's scope and
  Removes lists do not contain it. Add it to UDM-19's dead-code paragraph and consumer scope.
- UDM-19 says it needs UDM-04 because `evaluate/equivalence.py` depends on `core/keys.py`, while
  UDM-04's consumer scope migrates `evaluate/equivalence.py` (listed among `core/keys.py`
  importers). Deleting a module that imports the earlier model does not need the earlier model to
  be retired first; the dependency runs the other way. Correction: UDM-19 deletes the no-importer
  evaluation modules early (after the operator's confirmation, RULINGS 16), and UDM-04's
  `core/keys.py` row drops `evaluate/equivalence.py` ("deleted by UDM-19"). The same applies to
  tests of listed modules. After this, nothing in UDM-19 needs UDM-04, which RULINGS 10 already
  implies; say so.

### 11. Source items with no route — **must fix**

Each is in the review's fact-authority table, DuckDB table or a disposition and has no package:

- *Field kind to database and Python type* (four maps: `semantic/native_call_contracts.py:16–25`,
  `semantic/native_call_sources.py:28–37, 133–136`, `semantic/pdf_search_native.py:98–104`,
  `semantic/native_program.py:621–622`; DA-086 "field-kind types from the physical compiler's
  resolution"). Route: UDM-01 (a type-resolution projection of the compiled model) with the four
  maps in its consumer scope; if any is kernel-side and changes bytes, that part joins revision A
  under UDM-05.
- *Custom catalogs as LinkML-typed instance data* (PDF actions, analysis policy, metrics,
  characterization questions; DA-085 disposition; recommendation audit "Retain"). Route: add to
  UDM-02 (or a named part of UDM-01) with "closed-world where fields drive behaviour; disposition
  vocabularies keep their explicit open states", or record an explicit deferral with a trigger.
- *Companion `cp:` grouping and provenance columns* (`serve/companion_export.py:419–424,
  557–589`; DA-086; review D2 row). Route: UDM-16, D2 row and consumer scope.
- *X2 carried verification status per file identity* (analytical table assigns UDM-13; UDM-13 T0
  says "Nothing migrates"). Route: add to UDM-13 T0 scope, or move the row to UDM-16.
- *G4 semantic graph held in T1*: add to UDM-13 T1 list or record "not adopted" in the table.
- *"Hand Arrow schemas for model relations"*, *"one of the PDF outcome pair"*, the Python
  value-codec `_TEXT` tuple, and G5's "index revocations by node": route each (UDM-16, UDM-02,
  UDM-02, UDM-07 respectively) or state them as declined with a reason.

### 12. UDM-09's acceptance does not cover grants — **must fix**

*Source:* the head frozen file `target_alembic/versions/semantic_ddo_pe_n29_native.json` has 585
`desired` objects and a separate `privileges` list of 113 entries (counted). Grants are not inside
the desired objects' statements.

*Correction:* UDM-09 acceptance, first sentence, append: "and the privileges the registry derives
from declared purposes equal the frozen file's `privileges` entry by entry". Same independent
oracle for UDM-03's last acceptance item ("the grant matrix generated from program declarations
equals the frozen `privileges` of the revision UDM-03 installed").

### 13. Integrity defaults left unstated (opposite error) — **must fix**

The frame requires integrity memberships to be closed and complete. The drafts do not say what
happens when an integrity declaration is absent in four places:

- *Privileged effect with no declared owners* (lowered companion, "Privileged-effect owners stay
  closed"): add "An effect member marked privileged that declares no owners refuses at generation;
  absence never means 'any claimant'."
- *A `SupportEdgeKind` member without a source kind, target kind, group or profile* (UDM-07): add
  "refuses at generation (integrity omission)".
- *A `Role` member without its login and membership annotations* (UDM-03): add the same.
- *A program declaration with no purposes* (UDM-09 and UDM-03): state on both sides "receives no
  execute grant; the registry reports it, and an installed program with no purposes and a public
  wire entry refuses at generation" (or the rule the owner prefers). Also state in UDM-09 who
  supplies purposes for the five special-cased programs and for `ddo_field` and
  `data_binding_rows` (sets of purposes), which UDM-03 mentions and UDM-09 does not.

### 14. "A wrong family claim cannot fail open" is asserted, not routed — **must fix**

*Where:* lowered companion "Three states" ("claiming a family is safe in the direction that
matters … guards refuse"); review §12 lists it as Proposed, settled by "Native owner review of
each family validator for checks that could widen validity".

*Correction:* add to the lowered companion's open premises: "P9. No family validator or guard
contains a check that could widen validity for a member that claims it (the basis for allowing
several families and for treating a wrong claim as safe). Settled by the native owner's reading of
each of the seven validators and fourteen guards. Constrains: multi-family claims in UDM-05; if a
widening check exists, that family refuses co-membership until it is removed." Add the row to the
coordinator.

### 15. Revision B can block the transition — **improve (schedule risk)**

UDM-07 cannot generate until P5 is ruled (blocking), and UDM-03's final `Purpose` members wait for
the role-name ruling. With the order A, B, transition, an unsettled ruling stalls the transition and
therefore UDM-11, UDM-12 and final source. Add to the coordinator's revisions paragraph: "If B's
blocking premises are unsettled when the transition is ready, B is frozen without UDM-07, and
UDM-07 joins the transition, or a later revision that the stage absorbs before final source."

### 16. D2's prerequisite is named differently in RULINGS and both drafts — **improve**

RULINGS 3 says "only the program-identity part for its program-set tier". The cache companion
says "UDM-10's code identity slice supplies the generator code identity and the complete-or-
incomplete flag that both disk keys need"; the programs companion says the cache "consumes this
slice". D2's key needs the generator **code** identity; its content holds **program** identities;
D4 needs neither (its implementation identity is opaque, per UDM-13). Correct the cache
companion's UDM-14 prerequisite to: "D2 needs UDM-10's code-identity slice (the generator code
identity and its completeness flag) and the program-identity computation over UDM-09's rendered
statements, which needs no revision. D4 needs only UDM-13." Align RULINGS wording on reading.

### 17. Duplicate diagnostics for an absent `validity_family` — **improve**

UDM-02 makes `validity_family` `recommended: true`, so `RecommendedSlotsPlugin` warns
(`unchecked`), and UDM-06 emits `validity_undetermined` from the compiled state. An absent
declaration then yields two diagnostics and an explicit `undetermined` yields one. Correction:
do not mark `validity_family` recommended; UDM-06's diagnostic is the single route. UDM-02's
acceptance row becomes "an absent `validity_family` is accepted with no grammar diagnostic (the
validity diagnostic is UDM-06's)". The LOWERING advice already wrote it that way (L3 row).

### 18. UDM-17 newly refuses a working lookup — **improve (frame)**

"A lookup on a group the store did not index is refused before any statement is built. Today such
a lookup would run without an index." Refusing it is neither internal inconsistency nor integrity:
with the path sent as a bound parameter no text reaches the statement. Correction: "The entry step
reads every caller of the lookup. If all callers use the declared groups, an undeclared group is an
internal inconsistency and refuses. Otherwise an undeclared group runs as an unindexed lookup with
the path bound as a parameter, and only declared groups render the path inline for the index."

### 19. UDM-05 perturbation acceptance cannot fail as written — **improve**

"P's claim is edited … The kernel descriptor's source digest is unchanged … A generator that still
reads operation ids … moves the digest." P is a hand-authored fixture operation, so no generator
reads its id or captures its module, and the digest cannot move whatever the code does. Correction:
perform the perturbation on a real operation among the 27 (edit its declaration in a temporary copy
of its owner module): the descriptor digest must stay unchanged and the release id must change.
The same applies to UDM-06's perturbation.

### 20. Acceptance gaps for identity layers — **improve**

UDM-10 has no acceptance for the read-closure identity, the operation-behaviour identity, or the
change UDM-06 promises ("when UDM-10 delivers the validator identity layer, a kernel change that
does not touch [the conservative validator] stops invalidating"). Add: a fixture change to a
non-read program leaves the read-closure identity and reads unchanged; a change to one native
operation's program changes only that operation's `behavior`; a change to a family validator leaves
a conservative operation's derivation valid.

### 21. UDM-02's expected diagnostics list and the `Ownership` noise — **improve**

"All 62 real modules compile, and the diagnostics list equals a hand-kept expected list": say how the
list is produced independently (an inventory of the `ownership` and `preparation` values in the
literals by a plain text search, not a run of the validator). Second, with only `immutable` known and
sixteen values in use (review §3.2), fifteen `ownership_unknown_term` diagnostics would appear on
every preparation and mark every report incomplete, drowning `validity_undetermined`. Declare the
values in use as known members (provisional where no meaning is attached); only genuinely new terms
are then reported. This keeps the vocabulary open.

### 22. Overclaimed "what this keeps open" statements — **improve**

- UDM-01: "editing a model declaration without restarting a serving process … becomes ordinary" is
  true only after UDM-13 adds per-request observation; UDM-01's interim single reference does not
  observe changes. Say "with UDM-13".
- UDM-03: "Newly closed: nothing in meaning" omits that a new relation in a guarded schema is now
  write-guarded by default, where today an unlisted relation is not. Say "Newly closed, in the
  integrity layer: a new relation in a guarded schema is guarded unless declared exempt." In its
  acceptance, add the catalog of a database deployed from the current head as an oracle beside the
  hand-written matrix, so "unchanged in effect" is checked against the code that produced today's
  grants.

### 23. UDM-20 instrumentation is not executable as described — **improve**

"Loads PostgreSQL's `auto_explain` module for the session" and "statement durations enabled for the
session": the completions run in the product's worker connections, not in the diagnostician's
session, so session-level settings capture nothing. State the mechanism: on stage only, set
`session_preload_libraries = 'auto_explain'`, `auto_explain.log_nested_statements`,
`auto_explain.log_min_duration` and `log_min_duration_statement` per database or per application
role (`ALTER DATABASE … SET` or `ALTER ROLE … SET`, needing the administrative login), record the
settings in the evidence record, and revert them after. Also, "compiling the fixture's binding with
that revision of the binder in a separate checkout" conflicts with the repository's worktree rule;
prefer rendering the parent's statement from a probe in the evidence folder that imports the
parent's `data_operation_bindings.py` obtained with `git show`, or record the operator's agreement to
a temporary worktree.

### 24. Obligation 4 contradicts UDM-22 triage — **improve**

Obligation 4: "The two negative controls recorded as expecting older error codes are resolved by
their owner before the run." UDM-22 triage lists the same controls as a second-class failure routed
to their owner. Choose one: "They are routed to their owner before UDM-22; if unresolved at the run,
they are second-class failures with that owner."

### 25. T11 contradicts T8 and UDM-02/05 — **improve**

"A missing grant, guard, role, support-edge kind or owner of a privileged effect refuses; nothing else
about a declaration's content does." T8 refuses a member outside a closed vocabulary; UDM-05 refuses a
self-contradictory claim, a requirement violation and a dangling family name. Replacement:

> T11 | Refusal at generation or preparation occurs only for internal inconsistency (a field outside
> the declaration, a member outside a closed vocabulary, a self-contradictory or unmet family claim,
> a dangling name) and for omissions in the integrity layer (a grant, guard, role, support-edge kind
> or privileged-effect owner). An undetermined declaration or an unknown term of an open vocabulary
> never refuses.

Also add one sentence: "Every design package's acceptance tests are part of the required selection."

### 26. The PE-S33 comparison may not run as planned — **improve**

The script "requires the exact retained demand id" and evidence is never edited, while UDM-23 runs a
new demand on a release whose construction recipe changed between N23 and N29. State how the script
is pointed at the new demand (a successor copy in UDM-23's evidence folder if it hard-codes the
demand), and list the expected disagreements from the recorded recipe change before the run, so a
disagreement is judged against a prior statement.

### 27. Numbers — **improve**

- Analytical companion: "eight connection sites" (twice) against its own table of seven; source has
  seven `duckdb.connect(` calls (`serve/companion_export.py:410, 552`;
  `semantic/artifact_identity.py:481, 579`; `semantic/rich_relations.py:71`;
  `ingest/pdf_stream_reconciliation.py:301`; `ingest/pdf_candidate_geometry.py:87`). Say seven.
- `semantic/metadata.py` importers: 63 (model companion) against 64 files (cache companion). Use
  one number, "re-counted at entry" (RULINGS 15).
- Frozen storage: coordinator handover gives 206 MB (N14–N29 as Git objects); programs and
  analytical companions give 387 MB (46 files). Coordinator should state both with their scopes.

### 28. Model-change preview gates native authoring through the earlier model — **improve**

`schema/model_change.py:651–660` refuses a native change unless the earlier model's change record
names an `alembic_revision` (or `request.native_revision` is given). Retiring the earlier model
(UDM-04) therefore changes how a native revision request is validated, on the same code path
UDM-11 changes. UDM-04's open premise should name this check explicitly, and the coordinator should
sequence UDM-04 and UDM-11 on `schema/model_change.py` (single owner or a stated order).

### 29. Decision-record routes — **improve**

UDM-00 lists ADRs for ADR-0131, ADR-0092 and ADR-0124 only. Two companions list ADR-0024 `:46`
("Unsupported required semantics refuse") as replaced by RC14; UDM-00 should name the record (an
amending or superseding record, or the D2 preparation contract section, whichever owns the rule).
Use one verb: accepted ADRs are immutable, so the coordinator's "An ADR amends ADR-0092 / ADR-0124"
should read "A record supersedes ADR-0092 (ADR-0124), carrying its decision forward", as the model
and programs companions say.

### 30. Production context handed over by the test series is unrouted — **improve**

VALIDATION.md (end of Part D) lists items the test plan records as owned by production: release
identity depending on a filesystem location; hand-written role SQL in
`tests/native_private_bootstrap.py:30–106`; `admit_kernel` restating the persist-admit-bind order;
TDM-06's deployment key hashing the wrong migration tree. Route the first to UDM-10 (RC11 release
id), the second to UDM-03's consumer scope (role names from the vocabulary), the third to UDM-09
(installation order derived), and say whether UDM-19's deletion of the root deployment-key test
interacts with the fourth; or record each as a handover.

### 31. UDM-15 can need a fourth revision — **improve**

"If showing the premise requires a read program to stop reading an instance field, that change joins
whichever planned revision is open." After the transition none is open. Say: "Such a change must land
before the transition is frozen; otherwise UDM-15 for that query waits, or the coordinator accepts
one further revision before final source."

### 32. UDM-22 prerequisites — **improve**

"All functional packages (UDM-01 to UDM-19)": UDM-15 is gated. Say "UDM-01 to UDM-19, with UDM-15
only for the queries whose premise was settled; T14 otherwise recorded as not adopted".

### 33. Smaller agreement points — **improve**

- UDM-13 T1 migrates the scientific recipe holders "once UDM-18 derives the recipe": add UDM-18 as a
  prerequisite of that part.
- UDM-01 migrates `semantic/authored_sql.py:350` while UDM-19 deletes `semantic/authored_sql.py:299–369`;
  say whichever lands second drops the site.
- Model companion "Native revision. B": "once UDM-11 is in place" (see defect 7).
- Programs companion paths note: "`target_alembic/` relative to `python/corpus-structure/`" is right;
  but the model files are at `src/corpus_structure/model/…` in the snapshot, while companions cite
  `model/semantic/…` "relative to `src/corpus_structure/`" in some places and to the project in
  others. Make the convention uniform.

### 34. Usability and length — **improve**

*Undefined at first use, across companions:* derivation and episode (defined in lowered only),
population, use, original, cut and read cut, read instance, trust scope and epoch, intent, seal and
completion battery, watermark, frontier guard, lease, fate, generation (of a project), demand, the
"stage". A ten-line glossary in the coordinator, linked from each companion, fixes this without
repeating definitions.

*Length:* analytical (820 lines) repeats the "read by nothing" baseline (about 50 lines) nearly
verbatim in UDM-19's vision and consumer scope; keep it in one place. Its judgment table carries
about twelve rows marked "none"; one sentence listing those IDs as "kept as the review decided" saves
about fifteen lines without losing a decision. "Pivotal capabilities" restates the connection
configuration given in "One connection owner". Programs (763 lines): "The investigation's acceptance
checks, by package" (16 lines) repeats each package's acceptance; the "Sequence" section repeats each
package's native-revision paragraph. Qualification (738): the dropped-expectations list and "What
this supersedes" restate each other; the cadence argument appears in "Rules" and again in UDM-21's
"What must be regenerated". The lowered (739) and model (724) companions carry needed detail; the
cache companion (654) is fine.

*Examples that could read as complete scope:* UDM-10's "the corresponding construction ports" (name
them or give the count and "complete at entry"); UDM-17's 37 `literal_column(` sites (the review's
count, no list). Elsewhere the drafts mark examples and complete lists clearly.

*Project rules:* no new alignment lint or standing check is introduced (the UDM-02 consistency check
is model-internal consistency, and the UDM-16/17 "search finds no …" items are one-off acceptance
searches; say "not added to `ci check`"). No history or flaky tracking. No compatibility layer
without a consumer (interim holders and tables are staging steps with a stated end). Chandra is
excluded throughout. The DDO documents get one status line. Measurement: see defect 1.

---

## (c) Spot checks in the snapshot (2026-11-19, `cb4e09667`)

| Claim | Result | Evidence |
|---|---|---|
| Lowering has the archived effective operation in scope | **Holds** | `semantic/data_operation_compiler_native.py:773–806` reads `operation["effects"]`, `["capabilities"]`, `["support_policy"]` etc.; `:905–911` lowers dependencies; `:916–926` sets `validity_family` by `func.ops.ddo_classify_validity(lowered["operation_id"])` |
| Classifier holds 27 ids | **Holds** | 17 slash-form ids and 10 dotted or URN ids in `:470–535` (count by string extraction; two may belong to the command classifier beside it) |
| One receipt per published derivation, with a trust snapshot; snapshot covers declared support plus grade/fit/event cut scopes | **Holds** | unique `intent_id` on `data_derivation` and `data_publication_receipt` (`src/corpus_structure/model/semantic/data-operation-physical.yaml:403–420, 475–490`); insert with `trust_snapshot`, `validating_kernel_digest` (`semantic/data_derivation_native.py:604–615`; the digest is a generation-time literal, `:112, 796`); scope union with the three `*_completion_scopes` (`semantic/support_trust_native.py:208–231`). Note `validating_kernel_digest` is `required: false` in the model; always populated by the generated program |
| Generated guard's release-versus-installed comparison is conditional | **Holds** | the `native_digest = descriptor.source_digest` filter sits in a CTE (`semantic/native_admission_release.py:516–533`) consulted only inside `If(invalid, …)` where `invalid` requires a pattern constraint or a scope outside `shape`/`accepted_value` (`:585–626`) |
| 19 selection sites (sampled five) | **Hold** | site 6 factory dictionary `semantic/contextual_admission_native.py:188–201`; site 11 `_OPERATIONS`/`_FACTORIES` `semantic/definition_admission_native.py:33–44`; site 12 one id three times `semantic/artifact_admission_native.py:112, 147, 217`; site 15 `_OPERATIONS` `semantic/operation_event_native.py:55–60` (and site 16 at `:1277`); site 18 `semantic/structural_admission_native.py:1058`; site 10 producer ids `semantic/contextual_witness_native.py:240–251` |
| Every worker pool uses spawn | **Holds** | `semantic/cpu_execution.py:697, 724–726`; `semantic/pdf_publication.py:662`; `ingest/pdf_worker.py:141`; `ingest/pdf_chandra.py:258`; no other `get_context`/`set_start_method` found |
| Model-change preview runs on the earlier model | **Holds** | `schema/model_change.py:21` imports `schema.change`, `schema.model`; `:622–636` writes `core.yaml`, `system.yaml`, `revisions.yaml` to a temp dir, `model.load` both sides, `change.diff`; `:651–660` gates native authoring on the change record's `alembic_revision` (see defect 28) |
| Nothing reads the two retired migration trees | **Holds within search scope** | over `.py`, `.toml`, `.ini`, `.cfg`, `justfile`, `.yaml` under `snap7/`: only `tests/scripts/test_native_deployment_key.py:170` (asserts absence) and the table name `semantic_alembic_version`; `ALEMBIC_DIR` is `target_alembic` (`semantic/migrations.py:14`); "alembic" hits are the library. Not searched: `docs/` prose, evidence scripts |
| N29 has 585 desired objects | **Holds** | stdlib count: `desired` 585, `operations` 9, `privileges` 113 (defect 12) |
| TEMP grant is an installed program | **Does not hold** | applied by `ExecuteSQLOp` in the fresh-root bootstrap (`semantic/target_installation.py:623–637, 950–951`), text in `target_alembic/versions/semantic_ddo_current_root_upgrade.txt` (defect 6) |
| Eight DuckDB connection sites | **Does not hold** | seven (defect 27) |
| `acquire_publication_port` has no caller | **Holds** in `src/` (definition only at `semantic/data_operation_admission.py:375`); tests and root scripts not re-searched |
| Settlement lock timeout is 5 s | **Holds** | `semantic/claim_lifetime.py:204–211`; `settings.py:70–71` |
| Hand grammar's closed sets are closed today | **Holds** | `_PROFILES`, `_BINDING_OPERATORS` (`semantic/data_operation_compilation.py:85–103`), `_KIND_UNIVERSES`, `_PROJECTION_FAMILIES` (`:341–342`), forms (`:1491–1493`), so UDM-02 narrows nothing |

---

## (d) What I did not read

- Read fully: all seven drafts, RULINGS.md, DRAFT_BRIEF.md, COMMON.md, VALIDATION.md; LOWERING.md
  §§4–10; the review's "What changed", §§1–3, R07, R08, §§5–16; `dispositions.md`.
- Sampled: IDENTITY.md (outline, premises); `cache-design.md` (tier table and outline);
  the recommendation audit (outline, §3 table, §5.1); CACHES.md not opened (its facts reached me
  through the cache companion).
- Not read: review R01–R06 and R09–R17 argument bodies beyond the summaries and tables; the
  production audit pages; the DDO plan and its companions (passages are cited by the drafts as
  quoted); the test series plan; the create-plan skill and its plan-structure reference (so I did
  not check heading-level conformance to the authoring contract); the contributor reports.
- Source: only the lines named in (c) and in defects 2, 6, 12, 28. No tests, databases or
  providers were run.

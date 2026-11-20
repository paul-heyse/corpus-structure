# Unified domain model and execution

**Status:** In progress. **Created:** 2026-11-19.
This coordinator owns the series' combined target, shared contracts, package queue, rule-change
record, the scheduled disposition of every finding it lists, and the qualification of the
assembled system. Companion plans own the detailed designs and package descriptions.
Architecture pages and accepted ADRs remain the authority until the decision records of
[UDM-00](#udm-00) change them; writing this plan authorizes no implementation.

<a id="outcome"></a>

## Outcome and source baseline

Give the production code one authority for each kind of domain fact, with every other form
derived from it or connected to it; key, scope and invalidate work by what the model declares;
keep SQL text out of application code; hold expensive results in a designed cache system; and
do all of this while **representing the pipeline's intentional variability and optionality,
not closing it**. Then validate the whole system end to end on final source, including a
complete run over the book.

**Source.** The [design review of the unified domain model and execution](../design_review/reviews/design_review_unified-domain-model-and-execution_2026-11-18.md)
(latest publication `cb4e09667`, read at `main` `5139eaba3`, judgment Revise), its
[cache design](../design_review/reviews/unified-domain-model-and-execution/cache-design.md),
its [dispositions](../design_review/reviews/unified-domain-model-and-execution/dispositions.md)
and its [recommendation audit](../design_review/reviews/audits/design_review_unified-domain-model-and-execution_2026-11-18_audit.md),
which revised the recommendations so that the target represents intentional flexibility. The
review consumed the [production audit](../design_review/audit/README.md) at publication
`568d70596`. References such as R05 or RC06 below are to the review.

**Improvement amendment.** The [plan-improvement review](../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md)
at `929124ae5` extends the target to preserve recoverable work through timeouts, releases and
process exits, and to make those decisions visible through `ci`. The amendment was authored
against that clean tree, whose production source still matches `5139eaba3`. Its I01–I08
references are distinct from R/RC and audit IDs. [Recovery](unified-domain-model-and-execution/operation-reuse-and-recovery.md)
owns the private handoff and PDF checkpoints. [CLI](unified-domain-model-and-execution/operational-cli.md)
owns the operator workflows. The [disposition table](#improvement-dispositions) links to the
rest of the companion changes.

**Code dependency closure amendment · 2026-11-19.** The
[closure review](../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md)
at `1982a20c3` adds a bounded implementation follow-up to UDM-10 and the remaining cache and
CLI work. Its four entry-point scans reproduced the same 33 diagnostic sites. The retained
fixture also showed an indirect import changing a result under an unchanged, supposedly complete
digest. The broad scan supplies discovery evidence. Reuse requires authenticated closure for the
specific workload. The [amendment dispositions](#code-closure-dispositions) name the owners and
the evidence needed for closure. This refines the existing RC10 and RC13 guarantees under
[ADR-0137](../adr/0137-serving-code-and-model-custody.md). N33 and N34 receipts retain their
original scope.

**Approved continuation amendment · 2026-11-20.** The operator accepted
[ADR-0141](../adr/0141-serving-continuation-and-reuse.md). The
[qualification amendment](unified-domain-model-and-execution/qualification.md#continuation-compatibility-amendment)
restores stable installation-compatible continuation while cache eligibility keeps its stronger
proof. D2/D4 persistence and cross-request entity hit targets are deferred and their unused
mechanisms are retired. T4 requires fresh-process replay with current native authority. T14
requires equal entity rows and distinct native pins. Producer identity, exact original custody,
acknowledged PDF and completion-draft recovery, and whole-book no-new-provider-work remain required.
Earlier diagnostic and test records retain their original acceptance basis.

**Authoring baseline.** `main` `cb4e09667`, 2026-11-19. Its production source is identical to
the review's baseline. Four investigations made for this plan are published as
[authoring evidence](../design_review/evidence/2026-11-19_udm-plan-authoring/README.md); where
one corrects the review, the verified fact governs and the owning companion says so.

**Evidence status.** Target designs are **Proposed** where their owning decision or implementation
has yet to land. The [entry increment](#entry-increment) records accepted decisions, integrated
source and observed checks. Baseline source facts are
**Interface-checked by source inspection, 2026-11-19**. Receipts and outcomes taken from other
plans are quoted, not re-observed. No package has a speed target and no measured speedup is a
completion criterion. Measurement is planned only where a named decision needs it. One is the
diagnosis of the stopped book run ([UDM-20](unified-domain-model-and-execution/qualification.md)),
because an unexplained failure to complete the book is a risk to finishing at all. It settles
whether the repairs already made explain the two failures or a further repair is needed
before the whole-book run. The others are bounded observations, each made on the stage by the
package that owns the decision and settled before final source:

- UDM-06 observes that the conservative path completes within settlement limits under
  concurrent completions. It settles whether a project's trust scopes are locked or only
  recorded for an undetermined operation.
- UDM-13 fixes the three cache defaults (retained release bytes, runtime bytes, parser
  entries) from releases prepared on the stage, the model files of the loaded runtimes and
  UDM-20's bounded reproductions. The same run settles whether the on-disk model tier is
  adopted; the default is that it is not.
- UDM-14 retires the deferred program/page stores and validates fresh continuation replay.
  Disk budgeting has no current qualification obligation.
- UDM-16 observes the per-invocation input sizes of the rich-rule views. It settles whether
  they stay in DuckDB or return to plain Python.

The final runs (UDM-22 and UDM-23) observe and do not tune. If either reveals a needed
change, the change is made within the series and the affected evidence is gathered again.

**Scope.** The production package `python/corpus-structure/src/corpus_structure/`, its model
declarations and domain packs, its generators and frozen native revisions, the scripts that
provision and deploy it, the tests each change needs, the decision records for the accepted
rule changes, and the qualification of the assembled system on the stage, canonical
development and book-project environments. Out of scope: Chandra OCR (operator direction; see
[handovers](#handovers)); the test system's own design, which the
[test series](test-domain-model-and-execution_2026-11-17.md) owns; and any edit to the
declared-data-operations plan beyond one status line.

<a id="takeover"></a>

## What this series takes over and what it supersedes

The [declared-data-operations (DDO) plan](declared-data-operations_2026-11-12.md) stopped
execution at the operator's request with its final qualification open. On 2026-11-19 the
operator directed that this series **take over all remaining validation** from it. This is
not a transfer of DDO scope: where this series' design differs from what the DDO plan
specified, this series governs, and the validation is written against this target.

**Validation taken over** ([qualification companion](unified-domain-model-and-execution/qualification.md)):
the managed test and check union (no full run has passed since 2026-11-10 and the fault lane
has never run); native, provider, public, rich, graph and export coverage; the registration
and re-verification of the 29 originals; bringing the book project from native revision N23
to the current head; the whole-book run over 518 pages and 29 regions, whose last attempt
ended with nine regions at the settlement limit and a stalled composition query; and
same-demand interruption, resume and unchanged repeat.

**Design items superseded.** Each is replaced by a package here; the owning companion quotes
the passage it replaces.

| DDO or ADR specification | Replaced by | Package |
|---|---|---|
| `validity_family` is null "when no per-kind validator applies"; families assigned by a kernel classification over operation ids | A declared, three-state, possibly multi-valued claim per operation, lowered per release. Every existing operation declares its claim, a family or an explicit `none`, so its behaviour is unchanged; only an operation added later without a claim is undetermined | UDM-05, UDM-06 |
| Completion seals, receipts and the readiness watermark keyed by one kernel digest over the whole native capture | Program, kernel and per-family validator identities; the watermark without its kernel component | UDM-10, UDM-12 |
| The release identity hashes generator sources and the whole native capture | The release identity covers generated artifacts and the model capture; generator provenance is recorded beside it | UDM-10 |
| A new frozen native revision for any change of the kernel digest | A revision is authored only when installed program bytes differ | UDM-11 |
| Admission re-proves immutable release content on each acquisition; the native check regenerates the capture from the checkout | Carried receipts with an explicit verification command; acquisition compares against the digest the release records | UDM-08, UDM-12 |
| Serving identity names a hand-kept list of running code (ADR-0124) | Code identity derived from declared entry points | UDM-10 |
| Typed programs with three stated exceptions (ADR-0131), silent on where the facts programs dispatch on come from | Facts programs dispatch on have one declared home; facts about an individual operation reach programs through the release; model-level vocabularies and integrity memberships are generator inputs | UDM-00, UDM-05 |
| Preparation refuses unsupported required semantics (ADR-0024) | Preparation distinguishes refusing diagnostics from non-refusing ones; an undetermined declaration or an unknown term of an open vocabulary is reported and not refused | UDM-02, UDM-06 |
| Two operation authoring routes whose Python route is validated by a hand grammar (ADR-0092) | Both routes kept; the Python route's grammar and vocabularies declared in LinkML | UDM-02 |
| Role constants and default read roles in code | Role and purpose vocabularies and read roles declared in the model | UDM-03 |
| The process-local query cache keyed by the read cut | Declared process tiers and safe command-line continuation through bounded rederivation; persistent tiers deferred under ADR-0141 | UDM-13, UDM-14 |

When the series is placed, the DDO coordinator receives one dated status line pointing here.
Reconciling the DDO documents in detail is left for the operator's later pass
([UDM-24](#udm-24) prepares the list).

<a id="rule-changes"></a>

## Rule changes confirmed by the operator

The operator accepted all fifteen rule impacts on 2026-11-19, as revised by the recommendation
audit and the review's revision. Accepted ADRs are immutable, so each ADR change is a
superseding record written in [UDM-00](#udm-00) that carries the earlier decision forward,
with the owning design section amended in the same commit. Three further choices were made
the same day: no refusal boundary
for an undetermined validity family (RC14); LinkML for both the declaration grammar and its
vocabularies; and deletion of the two retired migration trees.

| Item | What changes | Route | Needed by |
|---|---|---|---|
| RC01 | Facts that programs dispatch on have one declared home and programs read it; facts about an individual operation reach programs through the release, while model-level vocabularies and integrity memberships are generator inputs; an undecided membership is declared undetermined and receives its stated conservative consequence; generation refuses only internal inconsistency and omissions in the integrity layer; independent controls take expectations as data | A record superseding ADR-0131; DESIGN §B4 and §B5 | UDM-05, UDM-17 |
| RC02 | "No maintained SQL text in application code" extends to SQLite stores and DuckDB use | Same record as RC01 | UDM-16, UDM-17 |
| RC03 | One composer and one compiled model per model-sources identity; per-artifact sub-identities kept | DESIGN §B5 | UDM-01 |
| RC04 | Both authoring routes kept; the Python route's grammar and vocabularies are declared in LinkML and literals are validated against them | A record superseding ADR-0092 | UDM-02 |
| RC05 | Null stops meaning "no per-kind validator applies"; that is an explicit `none`; absence means undetermined; the field may hold several families; the column is lowered from the operation's own declaration | Recorded here and in the owning design section; supersedes the DDO products-and-support specification | UDM-05 |
| RC06 | Completion seals keyed by a validator identity per family, with recorded reconfirmation | Recorded here and in the owning design section | UDM-10 |
| RC07 | The watermark drops its kernel component; role granularity follows a soundness argument | Recorded here | UDM-12 |
| RC08 | Finalization and deployment-admission receipts are carried; verification is an explicit command | Recorded here and in the owning design section | UDM-12 |
| RC09 | Drift of Python code still refuses and requires restart; a changed model source yields a new compiled model | A record superseding ADR-0124 | UDM-01, UDM-13 |
| RC10 | Serving identity is a derived import closure under the same custody mechanism | Same record as RC09 | UDM-10 |
| RC11 | The release identity covers generated artifacts and the model capture; generator provenance is recorded beside it | Recorded here and in the owning design section | UDM-10 |
| RC12 | Role and purpose vocabularies in the model; explicit read roles with declared defaults | Recorded here and in the owning design section | UDM-03 |
| RC13 | Declared reuse eligibility separated from safe continuation; persistent tiers and cross-request entity hits deferred under ADR-0141 | Recorded here and ADR-0141 | UDM-14, UDM-15 |
| RC14 | No promotion boundary: an undetermined operation compiles, runs and publishes under conservative validity, with a diagnostic | A record for the rule ADR-0024 states (see [UDM-00](#udm-00)) | UDM-02, UDM-06 |
| RC15 | A native revision is authored when the set of installed program identities differs, and only then | Recorded here and in the model-change design section | UDM-11 |

Moving cachetools from 7.2.7 to 8.0.1 is ordinary dependency judgment, named in the commit
that does it (UDM-13).

### Confirmed improvement rule impacts

The operator explicitly confirmed all three amendments during UDM-00 execution planning,
along with the canonical `evaluate` purpose, the UDM-09 grants prerequisite, and the UDM-08
acquisition change. The accepted decisions govern future implementation at their owning
packages. Shared revision B registration and deployment stay in the series' revision sequence.

| Review | Accepted consequence and route | Dependent work |
|---|---|---|
| I02 | A bounded private completion handoff can survive a terminated producer, and a new authorized claim can consume it without changing original producer attribution. Recorded in D3/D6 and ADR-0140 alongside ADR-0125/0126; preserve the physical retirement, live support, classified failure and publication requirements. Late or unacknowledged output is outside recovery. | UDM-25 draft adoption |
| I03 | An acknowledged PDF page can cross a request or release change when its complete producing premises are compatible and the original writer has retired. ADR-0139 and its owning section define compatibility and original contributor custody. | UDM-25 checkpoint adoption |
| I07 | An authenticated local caller can request cooperative stop of an exact managed invocation. The owning host still controls draining, retirement and quarantine. ADR-0140 and D6/D8 record the caller/host contract alongside ADR-0125/0069. | UDM-27 effect route |

The identity, validation, query-cache, and discovery changes refine existing authority. They
carry forward complete reuse determinants, exact selected use, and fresh current support. They
do not require reapproving RC01–RC15. The UDM-20 diagnosis and passive CLI slice can begin
independently of recovery and stop implementation.

<a id="frame"></a>

## The flexibility frame

This contract governs every package. It comes from the operator's direction of 2026-11-18 and
the recommendation audit that followed it.

The pipeline is exploratory. It progressively structures the knowledge contained in a body of
documents, and what it will find, and which operations will prove useful, is not known in
advance. The domain model therefore **represents** variability and optionality; it does not
govern them away. Three layers are treated differently:

1. **Knowledge content** that the pipeline discovers is unconstrained by this series. It keeps
   its explicit states for partial, missing, unknown, competing and unsupported results.
2. **The declared space of behaviours and links** (operations, products, support relations,
   vocabularies, packs) gets one declared home per fact, but a declaration may be
   *undetermined*, and each vocabulary states its own openness: closed, extensible by packs,
   or open with known members. Members may be marked provisional. An undetermined declaration
   has a stated consequence; it is not refused.
3. **System integrity** is closed and complete: roles, grants, guards, support-edge kinds and
   the owners of privileged effects. Refusal is reserved for omissions here and for internal
   inconsistency, such as a named family with no validator.

Every package description states what it keeps open: the exploratory move it keeps cheap, and
anything it newly closes with the reason it belongs to the integrity layer. A package whose
acceptance would fail an operation merely for being unclassified, or a vocabulary term merely
for being new in an open vocabulary, is wrong by this contract.

<a id="glossary"></a>

## Terms used across the series

Companions link here instead of repeating these definitions.

- *Kernel, native revision.* The kernel is the set of generated PostgreSQL programs a database
  has installed. A native revision is a frozen record of that set; N-numbers such as N29 name
  revisions, and the head is the latest.
- *Release.* A prepared, immutable capture of the model and operations that execution runs
  against.
- *Derivation, episode.* A derivation is a published result of an operation. The node that
  stands for a derivation in the support graph is an episode.
- *Original, use, population.* An original is a registered source document, a use is one
  admitted use of an original, and a population is the set of members an operation runs over.
- *Trust scope, epoch, trust snapshot.* A trust scope is the unit to which trust in a source
  is attached within a project. Its epoch advances when trust is revoked. A trust snapshot is
  the map from scope to epoch that a publication receipt records.
- *Cut, read cut, read instance.* A cut is the fixed set of published results that a grade,
  fit or event operation was judged against. A read cut is the fixed view of published results
  from which one read is answered, and a read instance is the random identifier created each
  time a read is acquired.
- *Intent, seal, completion battery.* An intent is the record of one completion, to which its
  derivation and receipt are tied. The completion battery is the full set of checks a
  completion must pass, and a seal records that a completion passed them, so that an exact
  replay does not repeat them.
- *Watermark.* The readiness watermark is the value waiting obligations compare to learn that
  their inputs may have changed and they must bind again.
- *Frontier guard.* The write guard installed on guarded relations.
- *Demand, fate.* A demand is a request for the results of named operation families over part
  of a project. A fate is the recorded final outcome of one demanded piece of work, including
  a classified failure.
- *Generation, lease.* A project's generation is its numbered selection of the release it
  runs on, moved by activation. A lease is a run's time-limited hold on a generation; a live
  lease blocks activation.
- *The stage, canonical development, the book.* The stage is the owned stage database with its
  bounded project. Canonical development is the development database on the dedicated
  cluster. The book is the 518-page project on canonical development.

## Target and foundation assessment

The core of the current design is kept: the request identity that leaves out release and
runtime, the typed program compiler that refuses raw SQL text, generated bytes held in
custody, one generated wire validation point, and PostgreSQL's authority over execution,
locks, publication and roles. The conversion to generated programs is nearly complete:
hand-written SQL fell from about 3,700 lines to about 180, and a renamed column or relation
now fails at generation.

What the conversion did not change is where *facts about operations and roles* come from.
The generators receive table metadata only, so the lists of which operation belongs to which
validity family, which role may execute what, and which entry point serves which operation
were transcribed from SQL into Python. An operation absent from a list is still treated as
valid, now also through early returns in several family guards. One digest over about 99
modules and six library versions still keys admission, seals and the watermark, so an edit
that changes no installed byte can still force a new native revision. The per-acquisition
check still regenerates the whole program capture. Caches are process-local, uncoordinated
and invisible to the command-line tool.

| Area | Target in one sentence | Companion |
|---|---|---|
| Model authorities | One composer builds one compiled model that every consumer asks for; the operation grammar and its vocabularies are declared in LinkML and say how open they are | [Model authorities and openness](unified-domain-model-and-execution/model-authorities-and-openness.md) |
| Operation facts and validity | Each operation declares its own facts; they are lowered per release and programs select by them at run time; an unclassified operation runs under conservative validity | [Lowered operation facts and validity](unified-domain-model-and-execution/lowered-operation-facts-and-validity.md) |
| Programs and identity | Programs are declared objects from generation to installation; identity is built from generated bytes and declared dependencies; a revision exists only when installed bytes differ | [Programs, identity and revisions](unified-domain-model-and-execution/programs-identity-and-revisions.md) |
| Caches | Six in-process tiers and two on-disk tiers, each with a stated key, bound, invalidation and release rule, under one small owner | [Cache system](unified-domain-model-and-execution/cache-system.md) |
| Analysis, SQL and retirement | DuckDB where it pays and under stated conditions; no SQL text in application code; superseded machinery removed | [Analytical placement, SQL and retirement](unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md) |
| Qualification | The whole system validated on final source, including the book | [Qualification](unified-domain-model-and-execution/qualification.md) |

**Foundations assessed during authoring** (read-only, at `cb4e09667`; details in the
companions and the [authoring evidence](../design_review/evidence/2026-11-19_udm-plan-authoring/README.md)):

- *The conservative check can be built.* Every published derivation has one receipt with a
  trust snapshot. That snapshot covers only declared-support scopes, so for an undetermined
  operation the check must lock and record all of the project's trust scopes; comparing the
  existing snapshot alone would under-invalidate. The locking happens inside settlement, which
  has a five-second lock timeout and is where the last book run failed, so UDM-06 shows on the
  stage that it fits before revision A is frozen.
- *Selection by a declared attribute has precedent, but less than the review said.* The PDF
  guard and the external guard select by a declared attribute. Rich admission and policy
  authorization refuse foreign claimants of a privileged effect, which is a different thing.
- *Nineteen sites select by a hand list of operation ids,* seven more than the audit counted.
- *The release-versus-installed comparison is conditional today,* so making the execution path
  generate nothing means adding an explicit comparison, not only deleting two rebuilds.
- *A program registry can be accepted by equality* with the 585 objects and 113 privilege
  entries of the current frozen revision; if that holds it needs no native revision.
- *A plain import walk is too coarse for code identity:* it reaches the same 447 of 767
  modules from every entry point. The existing operation slicer narrows it where that matters.
- *No in-process event announces a publication or activation;* those run in short-lived
  command-line processes. A long-lived process must notice a changed generation on next use.
- *Every worker pool uses spawn,* so workers start with empty caches and no fork handling is
  needed.
- *The earlier core and system model still has 56 importers* and the model-change preview
  depends on it; retiring it is a migration that includes a successor for the preview.
- *The book project is six native revisions behind the head.* The archived capture recipe
  changed. Recheck the material producing basis before deciding which work needs regeneration
  and which can be carried to the validating run.

**Credible changes the target should absorb**, each traced in the owning companion: an
operation is added whose validity semantics are not yet known; a vocabulary term is used
before it is settled; a pack adds members; a field, value-set member, validity family, guard
or role is added; one generator module changes without changing any installed byte; a library
the generators use is bumped; an analytical question is added over published products; an
identical read is repeated from the command line and from a long-lived process; two identical
cold reads arrive together; a model change is published while caches are warm; a run is
interrupted and resumed.

<a id="shared-contracts"></a>

## Shared contracts

Each contract has one owner. Companions use these names and do not redefine them.

| Contract | Meaning | Owner |
|---|---|---|
| Fact authority | The one place a kind of domain fact is declared: a LinkML declaration, instance data conforming to a LinkML class, a typed Python registry the compiler builds, or legitimately code. The review's fact-authority table assigns each | UDM-01 to UDM-03 |
| Compiled model | The immutable object built once from a captured set of model sources and held by that capture's identity; every consumer asks for it instead of composing its own closure | UDM-01 |
| Declared openness | What a vocabulary says about itself: closed, extensible by packs, or open with known members; members may be provisional | UDM-02 |
| Lowered operation attribute | A per-operation fact declared on the operation and written per release at lowering, which programs read at run time. Facts about an individual operation never enter generators and reach programs through the release. Model-level vocabularies and integrity memberships, including which declared purposes may own a privileged effect, are generator inputs | UDM-05 |
| Conservative validity | The validity an operation receives when its owner has declared no claim: it over-invalidates and never under-invalidates, and is reported by the one `validity_undetermined` diagnostic, which UDM-02 owns and UDM-05 switches on. An explicit `none` is a claim and does not receive it | UDM-06 |
| Program declaration | The typed description of one generated program (identity, body, callees, purposes or the explicit internal marking of a program that no purpose may execute, the validity families it validates, model inputs) from which installation order, grants, capture and facades are derived. It is the one home of which program validates a family; generation refuses a family that is not provisional and has no validator program or more than one | UDM-09 (UDM-05 holds the family table until the registry exists) |
| Identity layers | Program identity (digest of generated bytes); kernel identity (composed from program identities); validator identity per family, covering every program that decides a validity outcome for the family (its validator program, that program's transitive callees and the family's completion guard); the shared live-completion program serves every family and belongs to the kernel identity, while the per-family requirement programs it calls belong to their family's; code identity (derived from declared entry points); release identity. Each states what it keys and what a mismatch does; an unresolvable dependency withholds reuse and never refuses service | UDM-10 |
| Cache tier | One named class of held result with its key, bound, invalidation, coordination of concurrent misses, release rule and statistics | UDM-13, UDM-14 |
| Determining Python closure | The declared workload's authenticated initialization, executed definitions, verified dynamic boundaries and material runtime dependencies. Exact source files copied into an artifact also enter that artifact's input basis. Incomplete determination withholds reuse | [UDM-10 follow-up](unified-domain-model-and-execution/programs-identity-and-revisions.md#udm-10-code-closure), consumed by UDM-14/15 |
| Recoverable work | A private, acknowledged draft or immutable page checkpoint with verified producing evidence and a bounded lifetime. Native settlement or certification supplies public standing | UDM-25 |
| Operational report | Attributed observations and exact next actions over managed evidence and pinned native reads. It preserves the scope and authority of each reported fact | UDM-26, UDM-27 |
| Qualification union | The set of behaviours that must be observed on final source for the series to be complete, each with its route and evidence | UDM-22, UDM-23 |
| The flexibility frame | [Above](#frame) | This coordinator |

<a id="queue"></a>

## Package queue

The table owns execution state. Row order is one useful route; "Needs" is what binds. A
package is not automatically one worker's assignment.

| Package | Delivers | Needs | Sources | State |
|---|---|---|---|---|
| <a id="udm-00"></a>UDM-00 | Entry: baseline re-read; decision records for RC01 to RC15 with design sections amended | — | RC01–RC15 | Complete (`8ce85c0c2`) |
| UDM-01 | One composer and one held compiled model; field-kind type resolution and the companion `cp:` columns read from it | — | R01, RC03, RC09, DA-085, DA-004, DA-086 (part) | Compiled composition and ordinary consumers integrated. [Capture isolation for integrity consumers](unified-domain-model-and-execution/model-authorities-and-openness.md#integrity-projection-across-model-captures) passed. |
| UDM-02 | Declaration grammar and vocabularies in LinkML, each stating its openness; declared homes and checked Python copies of facts the model already declares; the one `validity_undetermined` diagnostic for an absent validity claim, switched on by UDM-05; hand grammar validator retired | UDM-01 | R02, R15, RC04, RC14, F05, DA-086 (part) | Complete. Validity activation and native consumers landed with UDM-05 |
| UDM-03 | Role and purpose vocabularies; typed physical profile with declared per-schema defaults; grants from program declarations (native revision B) | UDM-02; bounded UDM-09 grant slice | R03, R07 step B, RC12, DA-074 | Default privilege correspondence verified in N31/N32. [Candidate-sensitive principals and schema grants](unified-domain-model-and-execution/model-authorities-and-openness.md#integrity-projection-across-model-captures) passed on a private fresh target. |
| UDM-04 | The earlier core and system model retired after its consumers move; the model-change preview's successor, a comparison of two compiled models | UDM-01, UDM-02; the operator's decision on what the revision log must provide | R13, DA-072, DA-080 (part) | Complete. Compiled preview integrated and earlier model retired. [Execution evidence](unified-domain-model-and-execution/model-authorities-and-openness.md#udm-04-execution) |
| UDM-05 | Every existing operation's validity claim declared (27 name families, the others `none`) and lowered per release; selection by the lowered attribute at every site; kernel-side connections of already-declared facts; release composition from the closure of requested operations (native revision A) | UDM-02; the operator's reading of the proposed claims before revision A is frozen | R02, R07 step A, RC01, RC05, DA-070, DA-073, DA-086 (part) | Complete. Declared authority, lowering, dispatch and requested closure integrated. [Validity evidence](unified-domain-model-and-execution/lowered-operation-facts-and-validity.md#revision-a-candidate-execution) |
| UDM-06 | Conservative validity for operations left undetermined, shown on the stage to fit settlement; the non-refusing `validity_claim_unprotected` report (native revision A) | UDM-05 | R16, RC14, DA-070 (part) | Complete. Private successor and concurrent stage settlement verified on N30 and N32. [Revision A evidence](unified-domain-model-and-execution/lowered-operation-facts-and-validity.md#revision-a-candidate-execution) |
| UDM-07 | One declared support-edge meaning and one mapping; current-demand discovery closure (native revision B or transition for the discovery predicate) | UDM-02; the ruling on the population edge; early UDM-20 evidence for discovery | R08, DA-071, I03 | Complete. N31/N32 live discovery and private selective-member, historical raw lineage and authority passed. [Support evidence](unified-domain-model-and-execution/lowered-operation-facts-and-validity.md#revision-b-execution) |
| UDM-08 | The execution path generates nothing | — | R06, F01, DA-083 | Complete. Private PostgreSQL acquisition and export verified |
| UDM-09 | Typed program registry from generation to installation, declaring each program's purposes and the families it validates | —; it reads the compiled model of UDM-01 where that has landed | R04, DA-081, DA-074 (part) | Complete. One typed installation graph owns the inventory, declared grants and family validators. Fresh installation, N29 conversion and N32 stage cutover passed. [Transition evidence](unified-domain-model-and-execution/programs-identity-and-revisions.md#transition-integration) |
| UDM-10 | Identity layers in two slices: code identity, with no revision; program, kernel and per-family validator identity, with the identity transition revision | Code-identity slice: none. Program, kernel and validator slice: UDM-09 and UDM-05 | R05, RC06, RC10, RC11, DA-068, DA-069, DA-076, DA-082 | Complete for the bounded stage. Derived code custody, selective validation and material release identity landed with N33. Incomplete producing identities select demand-scoped execution. [Fresh PDF publication](unified-domain-model-and-execution/operation-reuse-and-recovery.md#fresh-pdf-qualification-on-n35) passed on N35. [Identity evidence](unified-domain-model-and-execution/programs-identity-and-revisions.md#identity-successor) |
| [UDM-10 code-closure follow-up](unified-domain-model-and-execution/programs-identity-and-revisions.md#udm-10-code-closure) | Conservative serving continuation compatibility and preserved producer identity | Existing UDM-10 custody, captured source/model inputs and native read authority | RC10, DA-069, DA-076, DA-082, closure I01, ADR-0141 | In progress. Serving migrates to the managed-installation contract. Stronger producer/reuse proofs retain their existing standing. Revised native continuation qualification remains open. |
| UDM-11 | A revision only when installed bytes differ. Its installed part, the explicit kernel predicate in the generated guard, joins the identity transition revision; the model-change commands change outside any revision | UDM-10 | RC15, DA-068 (part) | Complete for the bounded stage. N38 froze two changed helper-source guards and their descriptors. Stage deployment and Standard application proof passed. Both offline D2 invocations established parity with 620 frozen N38 objects. [N38 evidence](../design_review/evidence/2026-11-20_udm-closure-provider-readiness/README.md#typed-boundaries-and-source-navigation) |
| UDM-12 | Carried assurance, admitted binding facts, and the kernel-independent watermark | UDM-08, UDM-10 | R11, R10, RC07, RC08, DA-033, DA-078 | Complete for the bounded stage. N34 activated at generation 31 and was superseded by N35 at generation 32. Role granularity remains deferred under W1. [Stage evidence](../design_review/evidence/2026-11-19_udm12-carried-assurance/README.md) |
| UDM-13 | Cache owner module, cachetools 8.0.1, six in-process tiers, with the three size defaults fixed from bounded observations | UDM-01, UDM-09, UDM-10, UDM-12 stage cutover, and UDM-18's typed scientific policy slice | R09, RC09, F02, DA-083 (part), I04 | Six process retention mechanisms implemented on N34. Scoped holder and diagnostic controls passed. Generator and serving reuse remain subject to complete workload custody. [Cache results](unified-domain-model-and-execution/cache-system.md#udm-13--the-owner-module-cachetools-801-and-the-six-in-process-tiers) |
| UDM-14 | Stable continuation compatibility with bounded fresh derivation; retire persistent program/page tiers | UDM-10 continuation amendment, UDM-13 and native-authoring parity | R09, RC13, DA-075 (part), closure I02–I03 | Implemented under ADR-0141. Fresh native demand replay and offline N38 parity passed. Remaining T4 coverage is owned by the [qualification companion](unified-domain-model-and-execution/qualification.md#continuation-compatibility-amendment). |
| UDM-15 | Two authorized entity reads with equal rows and fresh native pins | UDM-14 continuation contract and private native publication | R10, RC13, DA-075, closure I03 | Revised native T14 passed with equal rows and distinct authorized pins. Cross-request entity cache reuse deferred. Exclusion keeps two cuts. [Qualification](unified-domain-model-and-execution/qualification.md#continuation-compatibility-amendment) |
| UDM-16 | DuckDB owner, expression-only relations, settings and unused-kernel retirement. Certification stays on SQLite. | — | R12, RC02, F03, DA-020, DA-080 (part) | Connection conversion, local controls and [spawned-worker settings](unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md#effective-analytics-settings-in-spawned-workers) passed. [D1](unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md#d1-bounded-rich-placement) selected typed Python and passed the final admitted cohort. [Evidence](unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md#execution-evidence) |
| UDM-17 | Five SQLite stores use typed statements. The forward TEMP policy binds to its applying database. | — | R07, RC02, F04, DA-084 | Scratch, default-model fresh root and native demand export controls passed. [Candidate TEMP inputs](unified-domain-model-and-execution/model-authorities-and-openness.md#integrity-projection-across-model-captures) passed on the private changed-policy target. Fresh selected-source and companion exports passed privately on registered N35. [Evidence](unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md#execution-evidence) |
| UDM-18 | Archived slices, declared scientific policy, qualifier partition and decimal bound. | — | R17, R14, DA-028, DA-077, DA-040, DA-001 | Complete for the bounded increment. Private N34 T15 and scientific admission/proof passed. Decimal bound landed in N30. [Evidence](unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md#execution-evidence) |
| UDM-19 | Retirement of both obsolete migration trees and dead code. Generated SQL preview compares captured models. | — | R13, DA-080 | Complete for the bounded increment, including evaluation and golden retirement, generated preview and N34 parity. [Evidence](unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md#execution-evidence) |
| UDM-20 | Early preservation and bounded diagnosis, then stage confirmation after the owning repairs are deployed | Entry needs no design package; confirmation consumes the affected fixes | Taken-over validation, I02, I03 | Complete for the bounded stage. N36 passed 60- and 66-page regional settlement, complete-family composition, and actual two-region withholding and refill. [Evidence](unified-domain-model-and-execution/qualification.md#retained-book-diagnosis) |
| UDM-21 | Environments at the first adoption head (N29), original verification, guarded activation, and a bounded Integrated provider check | UDM-20's canonical diagnosis | Taken-over validation | Complete. The [first canonical adoption](../design_review/evidence/2026-11-19_udm20-21-canonical/README.md) set book generation 5 at N29. The [Integrated N35 check](../design_review/evidence/2026-11-19_udm21-integrated-stage/README.md) verified actual Nemotron requests and launcher restoration. |
| [UDM-25](unified-domain-model-and-execution/operation-reuse-and-recovery.md#udm-25) | Recoverable completion drafts and compatible PDF checkpoint adoption | Early UDM-20 diagnosis; UDM-10 producing identity and UDM-12 current validity contracts; confirmed custody decisions | I02, I03 | Complete for the bounded increment. [Recovery ordering, draft retirement, and changed-request uptake](unified-domain-model-and-execution/operation-reuse-and-recovery.md#remaining-recovery-implementation) passed. [N35 cutover](../design_review/evidence/2026-11-19_udm-audit-closure/README.md#bounded-stage-activation) verified installed proof and retained project readback at generation 32. Regional workload confirmation belongs to UDM-20. |
| [UDM-26](unified-domain-model-and-execution/operational-cli.md#udm-26) | Passive preview, managed run recovery, attributed progress, model impact and bounded local reuse explanations | Initial slice uses existing managed and native records. Reuse explanations consume typed UDM-10/14/15 outcomes where applicable | I04, I06–I08, [closure review I04](#code-closure-dispositions) | Implemented and scoped CLI controls passed. Live watch and exact managed repeat passed on the N36 full-family demand. Assembled final-source acceptance remains open. |
| [UDM-27](unified-domain-model-and-execution/operational-cli.md#udm-27) | Exact managed invocation stop with observed drain or retirement | UDM-26 managed binding; confirmed local host-control contract | I07 | Scoped controls and repaired actual N36 CUDA stop passed. Independent readback confirmed physical retirement and native lease release. Whole-book interruption and resume remain with UDM-23. |
| UDM-22 | Managed final-source union, native-authoring parity and safe selected-read continuation | Revised UDM-10/14/15 acceptance, UDM-25–27 and stage confirmation | Taken-over validation, I01–I08 | In progress. N42 native deployment and actual rich admission passed. The Standard and Integrated applications need final preparation on main after a transform custody mismatch. Event scoring and authority assertions, scoped M1 readback and the final test union remain open. [Campaign and successor evidence](unified-domain-model-and-execution/qualification.md#retained-fit-custody-and-rich-producer-authority) |
| UDM-23 | The re-adoption check at the final head, then the whole-book run with interruption, resume, repeat and comparison | UDM-21, UDM-22; UDM-20 stage confirmation | Taken-over validation, I01–I08 | `not_run`. Full run awaits UDM-22. |
| <a id="udm-24"></a>UDM-24 | Closing | All | — | Not started |

**Why this order.** Much of the series can start at once, because it depends on nothing:
UDM-01, the composer every later model package reads; UDM-08, because acquisition regenerating
the capture is pure waste with a small fix; UDM-09, the program registry; the code-identity
slice of UDM-10; the owner module of UDM-13 with the four tiers that hold neither the model
nor programs; the
independent tidy work in UDM-16 to UDM-18; the independent part of UDM-19; and UDM-20, because
the cause of the stopped book run should inform the design work and is the largest risk to
finishing.

The main line is the model: UDM-01 gives every later package one compiled model to read;
UDM-02 puts the grammar and vocabularies there; UDM-05 and UDM-06 then move validity onto
declared, lowered attributes with a safe default for an operation nobody has classified. This
line carries the series' central correction and its central flexibility guarantee, so it
should not wait behind identity or caching.

The second line is programs and identity: UDM-09 makes programs declared objects, UDM-10
builds identity from them, UDM-11 and UDM-12 use that identity to stop needless revisions and
re-proof. The native slice of UDM-10 takes the per-family declarations from UDM-05, which is
the one hard join between the two lines.

Caches follow what they hold: the model and program tiers need the compiled model and the
program registry to exist as things worth holding, and the on-disk program tier needs code
and program identity.

In the closure follow-up, preserve producer identity and recovery proofs while introducing the
independent managed-installation continuation fingerprint. Retire the deferred disk paths,
verify fresh authoring parity, and exercise revised T4 replay and T14 independent reads.
UDM-26 presents owner-supplied continuation and reuse reasons without conflating their standing.

Preserve evidence and diagnose retention and discovery early in UDM-20. Those results inform
the UDM-25 mechanism and UDM-05/07 discovery proof before their revision allocations freeze.
Stage confirmation follows the owning fixes and does not gate their start. UDM-26's early
projection can expose current evidence for diagnosis. Its model-impact and mature reuse views
wait for the semantic contracts they report. UDM-27 can use the early managed binding without
waiting for the model-impact view.

**Native revisions.** The series plans three, authored and frozen close together in the order
A, B, transition, and packages join them instead of adding their own. Revision A: UDM-05 and
UDM-06, with UDM-18's decimal bound. N31 froze revision B with UDM-03 and UDM-07.
The identity transition includes any installed changes from UDM-19's remaining
release-side authored-SQL retirement, UDM-10's native slice, the explicit UDM-11 kernel
predicate, UDM-12's installed-object changes, and UDM-09's differing objects if its
equality premise fails. UDM-11's model-change commands install nothing and change outside any
revision. Role-granular watermarking joins the identity transition revision only if its
soundness premise is settled before that revision is frozen; otherwise it is deferred, with
the settling of that premise as its trigger, and the series plans no further revision for it.
A byte-changing repair from UDM-20
joins revision A, or the next planned revision that is not yet frozen. If revision B's
blocking premises are unsettled when the transition is ready, B is frozen without UDM-07, and
UDM-07 joins the transition or, if necessary, the coordinator re-plans final deployment.
Discovery closure joins B with UDM-07 where its existing identities suffice, otherwise the
transition. Finalize the chosen UDM-25 intake/consume path and checkpoint adoption predicates
before the transition freeze. Their byte-changing programs and derived grants join that
transition. Record existing-object reuse or Python-only changes when no new installed bytes
are needed. Validate the complete current validator family set in the transition. Extra
revisions are not the default for either recovery slice. UDM-26/27 consume native contracts and
each relies on the owning package for any required changes to those contracts.

Whether a package changes installed bytes is answered by generating and comparing with the
current frozen objects and privileges, which is possible today; no package waits for UDM-11 to
answer it. Each revision changes the kernel identity and forces every release to be prepared
again. After the transition and UDM-11, a change that alters no installed byte produces no
revision, which is itself one of the behaviours qualification observes.

**Environments during the series.** The stage follows each native revision (rollback-only
replay, then deployment). Canonical development and the book project are adopted twice only:
at the current head (N29) in UDM-21, and at the final head on entry to UDM-23, after the last
revision is frozen. UDM-21 defines the re-adoption check (database and release checks, the 29
originals re-verified, book activation) and UDM-23 repeats it. Qualification evidence is
gathered on final source only: no earlier run earns credit for source that changed afterwards.

**Shared editing surfaces.** Independent packages meet in a few files and should be sequenced
or single-owned there: `semantic/data_operation_compiler_native.py` (UDM-05, UDM-09, UDM-10);
`semantic/data_operation_storage.py` (UDM-03 for grants and the guard tuple, UDM-05, UDM-08,
UDM-09, UDM-10, UDM-13); `schema/model_change.py` (UDM-01 for its three compile sites, UDM-04,
UDM-09, UDM-11, UDM-13); `semantic/target_installation.py` (UDM-09, UDM-17);
`semantic/native_admission_release.py` (UDM-10, UDM-12, UDM-19); the admission generator
modules (UDM-03, UDM-05); `settings.py` (UDM-13, UDM-16, and UDM-20 if it declares a binding
deadline). In `schema/model_change.py` the order is fixed: UDM-04 replaces the preview and its
check that a native change names a revision before UDM-11 changes how a revision request is
judged, because both edit the same path.

### UDM-00 — entry

*Purpose.* Establish what is true when execution begins and put the accepted rule changes
into their authorities before dependent work starts.

*Baseline re-read.* Other sessions continue to commit. For each package, re-read the sites
its companion cites and record in the companion's state table what has moved. A package whose
whole subject was delivered meanwhile is closed with a reference to the delivering commit.

*Decision records.* One record supersedes ADR-0131 (RC01, RC02), one supersedes ADR-0092
(RC04) and one supersedes ADR-0124 (RC09, RC10). Each carries forward the decision it
replaces, names what is preserved, and amends its design section in the same commit. RC14
changes the rule "unsupported required semantics refuse" that ADR-0024 states: UDM-00 reads
whether the ADR or the D2 preparation contract section owns that rule today and writes the
record at that owner, a superseding record if it is the ADR. The remaining rule changes are
recorded in the owning design sections named in the table above. The flexibility frame is
added to the functional target in DESIGN §1 as a stated property of the system, so later
reviews judge against it.

UDM-00 records ADR-0135 through ADR-0140 and updates the governing design sections.
The operator confirmed `evaluate`, I02/I03/I07, the UDM-08 acquisition change and the minimal
UDM-09 program-purpose slice. The remaining registry work, recovery and stop implementation
follow their existing packages.

*Acceptance.* `uv run ci adr lint` passes; each superseded ADR names its successor; DESIGN
carries the frame and the amended sections; each companion's state table reflects source at
the entry commit.

<a id="entry-increment"></a>

### Entry increment · 2026-11-18

UDM-00 recorded the accepted decisions against `85ed1bc74`. The implementation moved UDM-08
ahead of authoring changes. A prepared release supplies the digest recorded in its native
definition projection. Acquisition first authenticates the frozen catalog and archive, then
compares the recorded digest with the installed descriptor. Export uses the captured running
wire protocol. New authoring uses the real generator capture, so a newly prepared release
requires the matching installed native revision.

UDM-01 moved physical metadata, scoped views, native call field types and companion columns to
the captured composer. The running package holds its capture for the process lifetime. UDM-13
owns new-source observation on subsequent requests. The earlier core and system model routes
belong to UDM-04. Protocol bindings are selected for the operations actually present in the
effective model, and an incompatible selected protocol operation refuses. UDM-05 still owns
composing a release from requested operations and their dependencies.

UDM-02 uses LinkML declaration validation and explicitly declared vocabulary openness. Release
preparation retains the exact grammar and vocabulary sources that it compiled. An
unknown open term and an absent recommended claim use the `advisory` outcome. The archive
preserves these observations for reporting, and native admission continues to refuse unchecked
required semantics. The two PDF outcome declarations now share one enum in the captured PDF
closure. Observations' `SourceValue` and the DDO semantic-value codec have distinct tags and
payloads, so no correspondence is imposed between them. UDM-05 turns on the recommended
validity claim and moves the remaining native classifications.

UDM-03 moved table policy, frontier guard membership, restricted principals and purposes to
declared integrity facts. The package declares empty role memberships per ADR-0103. Native
function authorization uses an explicit purpose set or internal marker. The grant slice of
UDM-09 still reads the generated PDF function inventory to recover that producer's existing
access declarations. UDM-09 owns registering those declarations directly, collecting callees,
and deriving install order and the full program manifest.

`uv run ci adr lint` passed (`ce0017d7a1014f42b62635de4a6421d2`). The source policy comparison
matched N29's 109 table ACL policies and 12 frontier guards. The fresh PostgreSQL installation
and acquisition control passed (`e756ea3b74c64e4fba62167307c7db3e`). The control passed actual
release publication, definition admission, acquisition and recheck with generation disabled,
refused a different digest, and verified a detached demand export. Its generated state matched N29's
585 object identities, owners and ACLs and all 113 table and schema policies. Of 22 changed
statement lists, 16 changed embedded digests only. The others record exact execution-catalog
descriptor inputs, reordered guard role checks, the `fit` principal in the closure guard, and
three evaluator-authorized eligibility checks using `evaluate`. Shared revision B owns the
integrity and purpose changes. The native sequence retains the actual new source digests.

The 207-case focused selection recorded 205 passes and two failures
(`d0f58f11ffc441fd84e80522a6440cf1`). Both cases passed in the 25-case declaration and
composition rerun after correcting input order and testing vocabulary custody through an open
term (`9a5b3aaa912f48159205401f20d8136f`). `uv run ci check --only types` passed
(`c1806ce0749540e4a1f34518438c8972`) and `uv run ci check --only lint` passed
(`78f105f74a3b4b0eba8cf419b393268c`). `uv run ci docs check` passed
(`77dc6f96a20046d2b23851d428fb592d`).

Stage and canonical revision B registration and deployment, provider qualification and the book
run are `not_run` in this increment.

<a id="udm-0406-increment"></a>

### UDM-04–06 increment

The operator selected compiled comparisons and managed receipts as the successor to the earlier
revision log. The [model authority companion](unified-domain-model-and-execution/model-authorities-and-openness.md#udm-04-execution)
records the compiled preview and retirement of the earlier model, generated projections, and
test-only evaluator. The [validity companion](unified-domain-model-and-execution/lowered-operation-facts-and-validity.md#revision-a-candidate-execution)
records the private N29 successor, remaining protected owners and capture selectors, and N30
stage acceptance at generation 27. N30 includes UDM-18's decimal bound. Canonical and book
adoption belong to UDM-21.

**Verified 2026-11-18.** `uv run ci test collect` selected 8,909 tests
(`42bbbeeb59124cbc96473abe3c13217c`). `uv run ci check --only types`
(`7405a1434b4a4c49b263a1bdd45cdb4f`), `uv run ci check --only lint`
(`802f3ba02bba4119834845f6ec2e8921`), `uv run ruff format --check`, `just model check`
and `uv run ci docs check` (`12588b39cf4f4c5fbd9b40577d313f16`) passed. The full functional
suite is `not_run`.

### N31 stage and foundation registry increment

The [revision B record](unified-domain-model-and-execution/lowered-operation-facts-and-validity.md#revision-b-execution)
owns the stage acceptance and remaining discovery cases. The
[registry record](unified-domain-model-and-execution/programs-identity-and-revisions.md#typed-foundation-registry)
owns the six-program frozen comparison, static correspondence repair and remaining
producer conversion. On 2026-11-18, `uv run ci test collect` selected 8,767 tests
(`63075896cbe7498dacd10dca9892bdf5`). `uv run ci check --only types`
(`612a77d77b8447fda7dfb765499dd416`), `uv run ci check --only lint`
(`75ad9d0d221d4fd2b374177dae8b0a55`), `uv run ruff format --check` and
`just model check` passed. UDM-22 owns the full functional and provider qualification.

### N32 identity transition

UDM-00 through UDM-09 were completed for the bounded transition. N32 and its matching source-native statistical application were deployed on the owned stage
database. `ddo-current-pdf-bounded` activated that release at generation 29 with its retained
requests, intents and episodes. The [native transition record](unified-domain-model-and-execution/programs-identity-and-revisions.md#bounded-stage-cutover)
owns the checked inventory, registration, deployment, activation and no-change evidence.
The [qualification companion](unified-domain-model-and-execution/qualification.md)
owns canonical adoption, the original book cases and final qualification.

### N33 identity successor

UDM-10 and UDM-11 installed on the owned stage. The source-native statistical release is
active for `ddo-current-pdf-bounded` at generation 30. Readback preserved all 16 requests,
14 completion intents and 14 episodes. At N33 the release selected demand-scoped execution for 11 of its
51 operations with incomplete producing code identity. The
[identity successor record](unified-domain-model-and-execution/programs-identity-and-revisions.md#identity-successor)
owns qualification and the retained-result assessment.

### UDM-24 — closing

After [UDM-22](unified-domain-model-and-execution/qualification.md) and UDM-23 have passed on
final source: refresh the production audit by its own skill so each corrected finding's
status reflects delivered source (not an edit made from this plan's claims); record the
handovers below at their owners; prepare for the operator the list of DDO packages and
obligations this series superseded or completed, as input to the operator's reconciliation
of the DDO documents; run the handoff skill.

<a id="dispositions"></a>

## Finding disposition

This table is the single scheduled-disposition owner for the findings it lists. Diagnoses stay
in the [production audit](../design_review/audit/README.md) and corrective reasoning in the
review. "Closure evidence" is what must be observed, not a claim that it has been.

| Finding | Package | Closure evidence | State |
|---|---|---|---|
| [DA-068](../design_review/audit/execution-fit.md#da-068) one digest keys everything | UDM-10, UDM-11 | A generator edit that changes no installed byte produces no revision and leaves seals valid | N33 separates native, family, release and authoring custody. Equal installed statements and independent family controls passed |
| [DA-069](../design_review/audit/execution-fit.md#da-069) whole-file implementation identity | UDM-10 | An edit outside an operation's import closure leaves its implementation identity unchanged | Derived custody and scoped slicing implemented. Complete workload closure remains open. Demand scope limits reuse. [Fresh PDF publication](unified-domain-model-and-execution/operation-reuse-and-recovery.md#fresh-pdf-qualification-on-n35) now passes with exact current custody. |
| [DA-070](../design_review/audit/semantic-model-and-authority.md#da-070) validity families from id lists, fail open | UDM-05, UDM-06 | An operation named in no former list is governed by its own declaration; an existing operation keeps its behaviour under its declared claim; an undetermined one is conservatively valid and reported | N32 conservative settlement passed on stage, and exact protected authority and the independent undetermined PDF guard passed on the registered head |
| [DA-071](../design_review/audit/semantic-model-and-authority.md#da-071) support graph encoded several times | UDM-07 | One edge declaration; every walker agrees on a hand-authored graph | Shared traversal profiles, selective changed-member reuse and N31/N32 cross-release discovery passed. The validity companion owns evidence |
| [DA-072](../design_review/audit/semantic-model-and-authority.md#da-072) two models | UDM-04 | No importer of the earlier model remains | Earlier loaders, generated types, and declarations removed. Real pack preparation covers released openness |
| [DA-073](../design_review/audit/semantic-model-and-authority.md#da-073) release composition by flags | UDM-05 | Composition follows the closure of requested operations | Explicit requests and workflows select source collections and provider acquisition by closure. The unselected manifest deliberately acquires its configured full profile |
| [DA-074](../design_review/audit/native-integrity.md#da-074) roles and guards as code lists | UDM-03, UDM-09 | An undeclared role refuses at generation; grants follow program declarations and equal the frozen privileges | Default catalog correspondence verified. [Candidate isolation](unified-domain-model-and-execution/model-authorities-and-openness.md#integrity-projection-across-model-captures) passed with the changed publisher and captured TEMP policy. |
| [DA-075](../design_review/audit/execution-fit.md#da-075) query cache keys | UDM-14/15 | Revised T4 verifies authorized page replay and T14 verifies equal entity rows with fresh pins | Persistent program/page reuse and cross-request entity hit efficiency deferred under ADR-0141. Reopen when repeated preparation obstructs an actual operator workflow. |
| [DA-076](../design_review/audit/served-claims.md#da-076) served-read identity allowlist | UDM-10 | Application source/resource inventory changes invalidate continuation compatibility without a list edit | Conservative installation compatibility implemented under ADR-0141. Inventory-drift controls and native demand replay passed. Remaining native coverage follows T4. |
| [DA-077](../design_review/audit/served-claims.md#da-077) scientific policy describes the kernel | UDM-18 | Changing a declared parameter changes both the policy and the kernel's behaviour | Typed release policy and altered sampling verified in the scoped UDM-18 slice. Private admission and explicit proof passed on N34 |
| [DA-078](../design_review/audit/execution-fit.md#da-078) coarse readiness watermark | UDM-12 | The watermark does not advance on a kernel-only change | Kernel component removed. A dependent operation without a source-set pin still needs the operation-granular component. W1 owns the role-scope deferral |
| [DA-079](../design_review/audit/boundaries-and-composition.md#da-079) unclassified concurrent-run refusal | — | — | Retained by the review with its reason |
| [DA-080](../design_review/audit/boundaries-and-composition.md#da-080) superseded machinery | UDM-19 (migration trees, dead modules and functions, the stale preview explanation, authored-SQL machinery); UDM-04 (the earlier model); UDM-16 (uncalled kernels) | Each listed item is gone with its tests | Superseded preview, both obsolete migration trees, unused evaluation machinery and uncalled analytical kernels removed. The active chain and independent deployment-key controls remain |
| [DA-081](../design_review/audit/semantic-model-and-authority.md#da-081) hand-kept program lists and text handoff | UDM-09 | One registry; generated objects and privileges equal the current frozen ones | All producers enter the typed graph. Fresh install, frozen ACL comparison and N32 stage activation passed |
| [DA-082](../design_review/audit/execution-fit.md#da-082) hand-kept lowering list | UDM-10 | The lowering identity is derived; an unlisted dependency cannot exist | Derived lowering and exact certification installed. Incomplete PDF lowering identity withholds cross-attempt reuse. [Fresh N35 contribution](unified-domain-model-and-execution/operation-reuse-and-recovery.md#fresh-pdf-qualification-on-n35) authenticates the current producer and archive. |
| [DA-083](../design_review/audit/execution-fit.md#da-083) capture rebuilt per acquisition | UDM-08, UDM-13 | Acquisition performs no generation | Private acquisition verified under UDM-08. UDM-13 limits model and program retention to owning identities and authoring use. No native change was authored for cache adoption |
| [DA-084](../design_review/audit/boundaries-and-composition.md#da-084) remaining hand-written PostgreSQL | UDM-17 | No hand-written PostgreSQL outside the stated exceptions | Typed operation passed ordinary and quoted database controls under the default model. [Candidate role selection](unified-domain-model-and-execution/model-authorities-and-openness.md#integrity-projection-across-model-captures) passed on a private fresh target. |
| [DA-085](../design_review/audit/semantic-model-and-authority.md#da-085) per-consumer model composition | UDM-01 | One composer; no consumer builds its own closure | Central composition integrated. [Integrity consumers](unified-domain-model-and-execution/model-authorities-and-openness.md#integrity-projection-across-model-captures) now use the captured model policy. UDM-04 owns earlier-model retirement. |
| [DA-086](../design_review/audit/semantic-model-and-authority.md#da-086) generator literals for declared facts | UDM-02 (declared homes and Python-side copies); UDM-01 (field-kind types and `cp:` columns); UDM-05 (kernel-side connections, revision A) | Each listed literal reads its declaration | Declared authority, family programs, validity and selective native consumers integrated and exercised by the bounded transition |
| [DA-033](../design_review/audit/execution-fit.md#da-033) release content re-proved | UDM-12 | A carried acquisition skips archive proof | N34 verified receipt-backed acquisition and explicit proof of the actual archive and catalog |
| DA-001, DA-004, DA-020, DA-028 recurring at new sites | UDM-18, UDM-01, UDM-16 and UDM-18 respectively | As stated in the owning companion | Qualifier partition and archived source selection integrated. [Spawned-worker settings](unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md#effective-analytics-settings-in-spawned-workers) passed. D1 passed the final admitted cohort with the typed Python implementation. |
| DA-040 decimal bound | UDM-18, joining revision A (B if A is already frozen) | One declared limit, read by the Python codec and by the generated canonicalizer | Landed with N30 under revision A |
| [DA-058](../design_review/audit/execution-fit.md#da-058) visual recognition runtime | — | — | Deferred; trigger: Chandra OCR enters scope |
| DA-065 | — | — | Retained as a changed footprint; no target change |
| Review findings F01 to F05 | UDM-08, UDM-13, UDM-16, UDM-17, UDM-02 | As stated in the owning companion | F03 worker settings and typed-Python placement passed their bounded checks. Final qualification and the other findings retain their owning package boundaries. |

A package finishing does not close a finding that has other contributors.

<a id="design-choices"></a>

<a id="improvement-dispositions"></a>

### Plan-improvement dispositions

All eight recommendations from the 2026-11-18 review are scheduled as proposed scope. Conditional design decisions and
their consequences stay at the owning packages. Closure requires the [qualification evidence](unified-domain-model-and-execution/qualification.md).

| Source | Owning packages | Closure evidence |
|---|---|---|
| [I01](../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I01) | UDM-09–12, UDM-16/18 | Independent expected producer fates for equal content, material edits, and newly applicable validators |
| [I02](../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I02) | UDM-25, UDM-20 | Pre-retention rollback and lost acknowledgment recover one result with the original evidence and no recomputation |
| [I03](../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I03) | UDM-05/07, UDM-25, UDM-20 | Equivalent discovery closes across releases; compatible retired checkpoint is reused; changed or revoked basis refuses adoption |
| [I04](../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I04) | UDM-10, UDM-13–15 | Bounded process tiers, attributable stats, valid cursors across storage-only changes, and durable work after pruning |
| [I05](../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I05) | UDM-14, UDM-16/18/19 | Concurrent publication and prune keep readable immutable entries; relevant analytical changes move the basis |
| [I06](../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I06) | UDM-26 | Passive preview and exact recovery from a fresh process preserve policy and refuse wrong target |
| [I07](../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I07) | UDM-26/27 | Scoped observation, exact stop, shared-interest detachment, and independently verified settlement |
| [I08](../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I08) | UDM-04, UDM-09–12, UDM-26 | Reviewed model and program effects, recoverable apply, consistent terminal and JSON outcomes |

<a id="code-closure-dispositions"></a>

#### Code dependency closure dispositions

The four amendments below consume the dated review at `1982a20c3`. Its site table remains the
evidence inventory. The [UDM-10 follow-up](unified-domain-model-and-execution/programs-identity-and-revisions.md#udm-10-code-closure)
owns the evidence needed to resolve those sites per workload. Package status remains in the queue.

| Source | Owning packages | Closure evidence |
|---|---|---|
| [Closure I01](../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md#I01) | UDM-10 follow-up, with dependent producer and serving consumers | Authenticated initialization, reached code and dynamic boundaries establish the supported workload. Required unknowns stay visible and ineligible for reuse |
| [Closure I02](../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md#I02) | UDM-14 | D2 persistent reuse deferred under ADR-0141. Fresh authoring must retain exact captured inputs, frozen program parity and guarded deployment. |
| [Closure I03](../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md#I03) | UDM-14/15 | Revised T4 verifies safe continuation replay and revocation. T14 verifies equal entity rows with distinct authorized pins. Persistent/cross-request hit counts deferred. |
| [Closure I04](../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md#I04) | UDM-26 | Terminal and JSON show the same bounded owner-supplied explanation for eligibility, blocker, and fresh derivation |

## Design choices made in authoring

These were settled while the plan was written, without a separate operator decision. Each is
argued in its owning companion. The operator may revisit any of them when reading; a change
is a plan revision and does not reopen the review.

- *Caches* ([cache companion](unified-domain-model-and-execution/cache-system.md)). No event
  publishers: a long-lived process notices change because each request reads the model files
  through custody, the read cut and the installed descriptor, and those values are in the
  keys. The model is observed once per request scope. Nothing is warmed in spawned workers.
  The on-disk result tier is typed canonical JSON lines over a closed set of value kinds, and
  a row outside that set is served but not written. Settings live in a `CacheSettings` section
  with root `build/cache`.
- *Existing operations declare `none`* (UDM-05). The 27 classified operations name their
  families and every other existing operation declares `none`, which is what null meant when
  it was written, unless its owner deliberately marks it undetermined. The list of operations
  and proposed claims goes to the operator before revision A is frozen.
- *The program declaration is the home of "which program validates a family"* (UDM-09; a typed
  table in UDM-05 until the registry exists). The `ValidityFamily` member does not name a
  program.
- *A comparison of two compiled models succeeds the model-change preview* (UDM-04). What the
  earlier revision log must still provide is left to the operator as a blocking premise.
- *The book-run diagnosis is made on the stage only, with bounded repair authority* (UDM-20).
  It may repair code that no design package owns; a cause inside a design package's subject
  is routed to that package. A repair is confirmed on the stage once the revision that
  carries it is deployed there.
- *Canonical development and the book project are adopted twice,* at the current head and at
  the final head, and not after each revision.

<a id="candidates-and-deferrals"></a>

## Candidates, deferrals, rejected options and open premises

**Deferred with a trigger.**

- *Persistent programs/pages and cross-request entity reuse (UDM-14/15).* Trigger: repeated
  preparation materially obstructs an actual operator workflow, with a bounded trustworthy
  reuse basis available. Revised T4/T14 qualify safe fresh reads and continuation. Additional
  content variants need a query-specific native witness if deliberately reintroduced.
- *Role granularity for the readiness watermark.* Role-granular watermarking joins the
  identity transition revision only if its soundness premise is settled before that revision
  is frozen; otherwise it is deferred, with the settling of that premise as its trigger, and
  the series plans no further revision for it.
  The premise is settled by an enumeration of what the binding programs read.
- *A second, named DuckDB thread count for export work.* A candidate; UDM-16 ships one thread
  count as an operator-changeable setting and plans no measurement. Trigger: an export slow
  enough to affect an operator's working loop.
- *Custom catalogs as LinkML instance data* (PDF actions, analysis policy, metrics,
  characterization questions). A candidate, not scheduled. Trigger: a catalog gains a second
  consumer, or a validation defect is found in one.
- *An identity-excluded notes field on operation literals,* an operator option the
  recommendation audit recorded. Not adopted; field names stay closed. Trigger: the operator
  asks for it.
- *Chandra OCR and DA-058.* Trigger: the operator brings it into scope.

**Rejected, so they are not proposed again.**

- *A required validity family, refused at compile when absent.* It treats intended latitude
  as a forgotten decision and blocks exploratory operations.
- *Passing the operation model into the generators.* Every operation edit would enter the
  kernel identity; facts reach programs through the release instead.
- *Annotations as the home for facts about operations.* Operations are instances, not schema
  elements, and annotation values are unvalidated in the pinned LinkML.
- *linkml-map, a Datalog route, SHACL or an RDF store* for the model's operational facts. The
  review's library research gives the reasons.
- *Attaching PostgreSQL from DuckDB.* It would move snapshot, role and audit authority out of
  PostgreSQL; data crosses as Arrow from the application's own session.
- *A cross-process cache built on an in-process library.* cachetools holds nothing across
  processes; the on-disk tiers are content-addressed files.
- *A holder for the capture on the execution path.* The execution path should not generate
  at all.
- *Tuning a default or a placement from the final runs.* It would change source after the
  evidence for it was gathered.

**Open premises.** Each is the first step of the package it constrains, or blocks it until an
owner decides. The owning companion states each in full.

| Premise | Settled by | Constrains |
|---|---|---|
| The four support-edge encodings disagree on the population-to-episode edge | The native owner's ruling on which is intended | UDM-07 (blocking) |
| Existing effect authorizations require the canonical evaluator purpose | Operator confirmed `evaluate`; PostgreSQL role remains `corpus_sem_evaluator` | UDM-03 and UDM-05 |
| The structural dossier id has no declared home | A decision on where it is declared | UDM-05 |
| The CPU-receipt count has no declared source | A decision on its source | UDM-05 |
| Each existing operation's proposed claim (27 families; the others `none`) is what its owner intends | The operator's reading of the list before revision A is frozen | UDM-05 |
| `definition_identity` may cover the validity record while the recipe excludes it | The native owner's reading of its consumers | UDM-05 |
| The rich module's further per-operation branches each have a declared selector | Reading each branch | UDM-05 |
| The three-operation evaluator subset is derivable from declarations | The native owner's confirmation | UDM-05 |
| A declared purpose is as strong an owner of a privileged effect as today's operation-id pin, for each of the three effects | The native owner's reading of the three guards and of who may declare each purpose | UDM-05, at the two owner sites; until it is settled the affected guard keeps its pin |
| The flag logic that composes a release can be replaced by the closure of requested operations (DA-073) | An inventory at UDM-05's entry | The DA-073 part of UDM-05 only |
| No family validator or guard contains a check that could widen validity for a member that claims it | The native owner's reading of the seven validators and fourteen guards | Multi-family claims in UDM-05; UDM-06's acceptance |
| Cut scopes lie in the request's project | Reading `ddo_record_grade_completion_scopes` and its two siblings | UDM-06 |
| The conservative path completes within settlement limits under concurrent completions | A bounded observation on the stage; if it fails, the design changes in UDM-06 before revision A is frozen | UDM-06 |
| The lineage walk of source admission must agree with validity | Its owner's statement | UDM-07 |
| The count and list of model composition sites (sixteen by search, seventeen in the investigation's headline) | A search at the entry commit | UDM-01 (first step) |
| The vocabulary module can be imported into the physical closure without the physical compiler refusing it | Reading that refusal once UDM-01 is in place | UDM-02 (first step) |
| The generated declaration schema changes no field name that a SQL reader of the effective-model archive depends on | Reading the archive's SQL readers at entry | UDM-02 |
| What the earlier revision log must provide that a comparison of two compiled models does not, including the check that a native change names a revision | The operator's decision | UDM-04 (blocking) |
| Registry output equals the current frozen objects and privileges | Generating and comparing | UDM-09 |
| Callees collected from typed bodies cover the provider binding of SQL-language bodies | Installing the registry's order into an empty authoring database | UDM-09 |
| Supported generator and selected-read workloads close over actual initialization, bindings, dynamic effects and authenticated code | Resolve the review's sites per workload and challenge the boundary with independent controls. Apply the same proof where PDF lowering or other producer reuse consumes it | UDM-10 code-closure follow-up and dependent reuse |
| No consumer needs releases prepared before the identity transition | The operator's confirmation | UDM-10 |
| What the binding programs read, for watermark role granularity | Reading those program bodies before the transition is frozen | UDM-12 |
| Which value kinds occur in served rows | Reading the declared served row types when needed | Deferred persistent codec |
| The exact generator artifact depends only on captured inputs and authenticated rendering code | Preserve input capture and frozen-output parity; complete proof remains necessary for reuse | T2 reuse and deferred D2; fresh authoring parity remains current |
| A content-based key for served results is sound across fresh requests | The native owner's query-specific argument | Deferred cross-request entity reuse. Current UDM-15 requires equal rows and independent pins |
| Certification fold placement | The same SQLite store supplies validation and reconstruction reads | Settled in UDM-16 and UDM-17. Typed SQLite preserves binary-fold ordering |
| DA-001 qualifier partition | Declared context and compared-qualifier controls | Connected in UDM-18 |
| Evaluation and golden modules | Operator authorized full retirement | Retired in UDM-19 |
| Uncalled Unicode release wrapper | Consumer inventory | Retired in UDM-19 |
| Installed parity after retirement | Offline comparison of 617 current objects against N34 returned `no_native_change` | Settled in UDM-19. No native revision required |
| The failed run's records are still in the result store | Placing them on hold | UDM-20 (first step) |
| A demand can be scoped to one region of the book without registering an excerpt | Reading the demand's scoping at entry | UDM-20, the construction of its bounded cases |
| Whether a server-side statement timeout exists on the cluster | Reading the cluster and role settings | UDM-20 |
| The causes of the settlement timeouts and the stalled composition | UDM-20's reproduction | UDM-21, UDM-23, and any design package the cause touches |
| The smallest independently durable draft custody, and the exact authorized consume boundary after producer retirement | Early UDM-20 and UDM-25; compare short intake and verified spool | UDM-25 native transition and UDM-20 confirmation |
| Which PDF dependencies are page-local, and which discovery equivalence proves current declared scope | UDM-25 checkpoint analysis and UDM-05/07 native closure controls | Checkpoint adoption and discovery revision allocation |
| How a local managed invocation proves its ownership and receives cooperative stop | UDM-27 inspection of managed and host ownership | Effect route and UDM-23 interruption journey |
| The fault lane can have the native host to itself | Arrangement with the operator before the run | UDM-22 |
| The retained comparison script can be pointed at a new demand without changing what it compares | Reading the script at entry | UDM-23 |

<a id="handovers"></a>

## Handovers to other owners

| Observation | Owner | What this series does meanwhile |
|---|---|---|
| Chandra OCR is excluded from this series and from its qualification union (operator direction, 2026-11-19) | Operator | Records DA-058 as deferred |
| Frozen native revisions each carry a full catalog snapshot: about 206 MB for N14 to N29 as Git objects, and about 387 MB for all 46 frozen files in the working tree | Owner of the model-change machinery | UDM-11 stops revisions that change no installed byte; what a revision freezes is unchanged |
| Detailed reconciliation of the DDO coordinator and companions with what this series supersedes | Operator | UDM-24 prepares the list |
| The test series' own closing package and its open final qualification | [Test series](test-domain-model-and-execution_2026-11-17.md) | UDM-22 produces the assembled full-run evidence and reports test-system failures to that series |
| Production context the test series records as owned outside it: a release identity that depends on a filesystem location; hand-written role SQL in a test bootstrap; `admit_kernel` restating the persist, admit and bind order; a deployment key that hashes the wrong migration tree | [Test series](test-domain-model-and-execution_2026-11-17.md) for the tests; this series for the causes | Routed to UDM-10, UDM-03, UDM-09 and UDM-19 respectively; each companion says what it changes |
| A process host that refuses a second concurrent run with an unclassified error (DA-079) | Production, as the review retained it | None |

## Completion audit

**Interface-checked, 2026-11-19.** The audit examined clean source at
`618fff894b27d718775e7bc0a0e435ea39546a26`. It covered all eight companions and the
coordinator's current completion claims, including delivered slices of UDM-10 and UDM-14–17,
UDM-20 and UDM-25. The three independent source inspections traced normal consumers and reconciled
the claims against the accepted decisions and amendments.

**Implementation.** UDM-00, UDM-02, UDM-04–09, UDM-11/12 and bounded UDM-18/19 retain their
inspected completion. The accepted ADRs and the ADR index's evidence labels have different
purposes. Source inspection sustains the declared validity, native registry, archived source and
retirement claims at their recorded boundaries. UDM-01/03 retain their completed composition and
default grants, with candidate integrity capture reopened. UDM-16 retains its connection and
relational conversion, with spawned settings reopened. UDM-17 retains typed scratch conversion and
default-model TEMP results, with candidate roles routed to UDM-01/03. The PDF contributor guard
also narrows the fresh-execution claim in UDM-10. UDM-25 has bounded private handoff and checkpoint
implementation plus open recovery ordering, lifecycle and changed-request obligations. The queue
and dispositions above carry those corrections.

**Historical qualification, before ADR-0141.** The audit read existing evidence and used a read-only model perturbation. It
did not launch product qualification. The retained N34 comparison covers 617 installed objects
and the bounded cutover used the recorded stage target and generation. Those results remain
applicable to their original source and context. The UDM-13 mechanisms are present and complete
workload custody still gates actual generator and serving reuse. D2, T4 and T14 remain open. T15
reached native source-request preparation from the archive after removal of the working pack.
The native selected-source export case failed before package export at the fresh PDF contributor
guard. UDM-20 establishes the historical intent-retention failure boundary and the scope of the
bounded controls. Exact canonical intent standing, regional timing, actual composition and
confirmation on the repaired head remain open. W1 and Chandra OCR retain their recorded
dispositions. Final-source qualification and series closeout retain their existing owners.

**Benefits.** Bounded observations support the stated cache defaults and the tested recovery
behaviors. Book-scale cost, avoided recomputation across the open paths and production speedup
remain unmeasured.

### Audit closure implementation

**Tested, 2026-11-19.** The bounded closure corrected candidate integrity and TEMP policy capture
(UDM-01/03/17), carried effective analytics settings into spawned workers and selected typed
Python for the observed D1 workload (UDM-16), and installed the UDM-25 recovery corrections.
Registered N35 passed fresh PDF publication, exact selected-source export and detached companion
controls. The bounded stage activated at generation 32 with exact retained project readback.
[Implementation and cutover evidence](../design_review/evidence/2026-11-19_udm-audit-closure/README.md)

The approved continuation amendment replaces the earlier D2/T4/T14 closure prerequisites.
UDM-10/14 now own stable continuation compatibility and authoring parity. UDM-20 still owns
regional workload confirmation, followed by canonical adoption and series qualification.

## Completion

The series is complete when every package's acceptance holds on final source; the disposition
table's closure evidence has been observed for every scheduled finding; the decision records
of UDM-00 are accepted with their design sections; the qualification union has been observed
on final source, including the full managed test and check routes, the fault lane, the
re-adoption check at the final head with the 29 originals verified, and the whole-book run with
interruption, resume and unchanged repeat, and UDM-24's records are written. The series remains
in progress. Report implementation and qualification separately, and state benefits at the
strength of the evidence.

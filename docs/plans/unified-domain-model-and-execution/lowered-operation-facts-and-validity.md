# Lowered operation facts and validity: declared families, selection by lowered attribute, the conservative check and one support-edge meaning

**Status:** In progress. Validity source and selected release composition are integrated.
**Created:** 2026-11-19. Writing this plan authorizes no implementation.

This companion owns the designs of **UDM-05** (per-operation validity declarations lowered per
release, with every selection by operation-id list replaced by selection on the lowered
attribute), **UDM-06** (the conservative validity check for undetermined operations and its
diagnostic) and **UDM-07** (one declared support-edge meaning and one reference-to-node
mapping). It contributes to findings
[DA-070](../../design_review/audit/semantic-model-and-authority.md#da-070),
[DA-073](../../design_review/audit/semantic-model-and-authority.md#da-073),
[DA-071](../../design_review/audit/semantic-model-and-authority.md#da-071) and
[DA-086](../../design_review/audit/semantic-model-and-authority.md#da-086), and it depends on
rule impacts RC01, RC05 and RC14, which the operator accepted as revised on 2026-11-19 and whose
required content is stated under [What this supersedes](#what-this-supersedes). Package state,
the queue, finding dispositions, the shared contracts (**fact authority**, **compiled model**,
**declared openness**, **lowered operation attribute**, **conservative validity**, **program
declaration**, **program identity** and the other identity layers, **the flexibility frame**)
and the decision records of UDM-00 are the
[coordinator's](../unified-domain-model-and-execution_2026-11-19.md). This document uses those
names and does not redefine them. Terms of the system that are not defined here at first use
(episode, population, use, original, trust scope, cut, intent, seal, the stage) are in
the coordinator's [glossary](../unified-domain-model-and-execution_2026-11-19.md#glossary).

**Baseline and evidence.** Section references such as R02 or §3.2 mean the
[design review of 2026-11-18](../../design_review/reviews/design_review_unified-domain-model-and-execution_2026-11-18.md)
as revised at `5139eaba3`; its "What changed in this revision" section explains why R02, R07 and
R16 were re-argued after the conversion to typed programs. The plan was authored against commit
`cb4e09667` (the authoring baseline; its production source is identical to `5139eaba3`). Source
facts are **Interface-checked by source inspection, 2026-11-19** at that commit. Nothing was
run; where this document says a program "cannot" behave in some way, that is by reading. Every
design statement is **Proposed**. No speedup is claimed. The investigation this companion draws
on is the
[lowering and declaration advice](../../design_review/evidence/2026-11-19_udm-plan-authoring/lowering.md);
the validator-identity layering it hands to is in the
[identity advice](../../design_review/evidence/2026-11-19_udm-plan-authoring/identity.md).
Passages quoted from the declared-data-operations (DDO) plan are quoted, not re-observed
behaviour. `src/…` and `tests/…` are relative to `python/corpus-structure/`, and bare module
paths such as `semantic/data_validity_native.py` are relative to `src/corpus_structure/`.

Where the investigation corrects the review, the investigation governs. Two corrections apply
here. The review says two guards already select by a declared effect; in fact rich admission and
policy authorization select by operation id or command class and *refuse a foreign claimant* of a
privileged effect. The precedents for selecting by a declared attribute are the PDF completion
guard and the external completion guard. And the review asks the native owner whether every run
can be tied to a trust snapshot; the investigation settled that from source, with a requirement
stated under [Conservative validity](#conservative-validity).

## Why this work exists

A *derivation* is a published result of an operation. It stays valid while its producer is
admitted, its outcome was success or empty, nothing it relied on was revoked, and, for some
operations, further premises still hold: a grade depends on trust in the cut it was graded
against, for example. Those further premises are checked per *validity family*. Seven families
exist, and each has a validator program and, usually, a completion guard that checks a
completing run's output contract.

Which operation belongs to which family is written as lists of operation ids inside the
generators of the native kernel. A classification program holds 27 ids; the dispatch holds a
second list with a default of "valid"; each guard begins by returning early for any operation
that is not on its own list. An operation missing from a list therefore escapes at three levels,
and escapes silently, because "belongs to no family" and "was forgotten" have the same
representation and the permissive treatment. The lists were transcribed from the SQL they
replaced, so the defect is old, but the lists now also sit inside the kernel's source digest:
adding an operation to a family changes the kernel.

The same pattern of several hand encodings that must agree appears in how support is walked.
Four pieces of code encode which rows support which, and they disagree on one edge and on what
to do with a reference they do not recognise.

The target has one declared home for each of these facts, and every program reads it. The
exploratory character of the pipeline shapes the remedy. An operation may be written before
anyone knows which premises its results depend on. The first-round remedy, refusing an operation
that has not classified itself, would have made that exploratory move impossible; the operator
decided against any refusal boundary. So the undecided case is represented explicitly and given
a stated conservative consequence instead. That consequence is for the genuinely undecided.
Every operation that exists today keeps its behaviour: its owner states its claim, a family or
an explicit `none`, and only an operation added later without a claim is undetermined.

## Baseline at `cb4e09667`

### Classification, dispatch and guards

The classifier `ops.ddo_classify_validity` is a `CASE` over 27 operation ids with no `ELSE`
(`semantic/data_operation_compiler_native.py:483–529`). Lowering runs inside the kernel with the
archived effective operation in scope: it reads the operation record's effects and capabilities
(`:775–820`), lowers dependencies from it (`:905–911`), and sets `validity_family` by calling
the classifier with the operation id (`:916–926`). The column is an optional string
(`model/semantic/data-operation-physical.yaml:88`). The 27 ids are contextual, definition,
artifact, operation-event, record grade and fit, and rich operations. Capture, organization,
sentence, formal, math, linguistic, construction and composition operations, which are most of
the book pipeline, are outside the classifier on purpose: the DDO specification defines null as
"no per-kind validator applies". Dispatch is a `case` over seven family names
with `else_=True` (`semantic/data_validity_native.py:272–288`).

Completion calls fourteen guards by name and each selects itself
(`semantic/data_completion_settlement_native.py:548–563`); the evaluator authorization is
performed for three literal ids (`:576–587`); the live-completion chain selects by literal ids
(`:744–806`). The family modules pin per-operation facts the effective model already holds: a
twelve-entry dictionary from operation id to factory entry point
(`semantic/contextual_admission_native.py:188–201`); profile, forms, preparation, effects and a
CPU-receipt count per id (`:234–259`, the count being zero for the scoring operation and one
otherwise); required roles and the permitted producers of each input role by id (`:291–310,
369`). The implementation itself is already authenticated per operation by the definition's
implementation-slice revision, which the guards check (`:225–236`).

### The precedents

Two guards have the target shape: select by a declared attribute, and refuse the family's
evidence when not selected. PDF completion selects on `capabilities.preparation == 'pdf-native'`
and refuses PDF evidence otherwise (`semantic/pdf_completion_native.py:137–146`). External
completion selects on the lowered `support_contract.external` and refuses an external receipt
otherwise (`semantic/external_execution_native.py:893–899`).

Three guards protect a privileged effect by refusing any claimant other than the one permitted
owner: rich admission (`semantic/rich_admission_native.py:1135–1145`, owner pin at `:1186`),
policy authorization (`semantic/record_policy_completion_native.py:425–441`, where the command
class comes from eligibility predicates at `semantic/data_operation_compiler_native.py:530–550`)
and structural admission (`semantic/structural_admission_native.py:1475–1494`). Four families
already declare a native effect per operation (`methods/record_policy.py:70–71`;
`methods/operation_events.py:326–330`, where only `authorize` declares one and `frame` and `fit`
declare none; `methods/rich_knowledge.py:405`; `methods/structural_admission.py:130–139`).
Contextual, definition and artifact operations declare none.

### What validity compares today, and what a receipt records

Generic validity is: the producer's definition is admitted, the outcome is success or empty, the
family check passes, and no revocation matches the episode's scope and selectors
(`semantic/data_validity_native.py:290–330`), with support propagated through conjunctive edges.
Every published derivation has exactly one publication receipt (unique `intent_id` on both
`ops.data_publication_receipt` and `ops.data_derivation`;
`model/semantic/data-operation-physical.yaml:403–420, 475–490`), and the receipt records a
required `trust_snapshot` and the generated `validating_kernel_digest`
(`semantic/data_derivation_native.py:604–615`). The snapshot is the map from trust scope to
epoch for the scopes locked at completion. Those are the ordinary support scopes plus, for
grade, fit and event operations only, their cut scopes
(`semantic/support_trust_native.py:208–231`). A helper gives a snapshot's meaning with an absent
scope and a zero epoch treated alike, so that lazily created scopes do not count as change
(`:126–160`). Trust scopes carry their project (`ops.data_trust_scope.project_id`,
`model/semantic/data-operation-physical.yaml:109–116`). The completion locks are taken inside
the settlement transaction, whose lock timeout is five seconds
(`semantic/claim_lifetime.py:204–211`, `settings.py:70–71`); settlement is the phase in which
the last book run failed.

### Four encodings of the support walk

1. The validity edge program (`semantic/data_validity_native.py:87–240`): node kinds episode,
   use, population and original, a `producer` pseudo-node, alternative groups keyed by `choice`
   for value substitution, and a reference classified inline (`:179–200`).
2. The projection walk `_support_walk` (`semantic/data_operation_projections.py:171–270`), with
   six callers (`:396, 466, 530, 1157, 1685, 2232`), its own `_reference_node` whose default
   classifies any reference that is neither an original nor a use as an episode (`:156–169`), an
   `authority` leaf kind for public reads, and a population edge that requires both
   `admission_use_id` and `derivation_id` (`:245–255`).
3. Change impact's `_revocation_causes` (`semantic/change_impact.py:332–441`), in Python, with
   its own reference mapping (`:346–351`), a `selected-episode` kind, an edge from a population
   to an episode (`:381–382`) that the other encodings lack, and the trust-scope key recomputed
   in Python (`:427`) beside the kernel's `ops.ddo_scope`
   (`semantic/support_trust_native.py:99–119`).
4. Source admission's lineage walk, which follows only `support_derivation_id`
   (`semantic/source_admission_native.py:1129–1135`).

## Target design

### Where operation facts enter the kernel

**Proposed.** One native kernel serves many releases. A fact about the model as a whole is a
*generator input*: it is read when the kernel is generated and it rightly moves the kernel
when it changes. Model-level vocabularies (which families exist, the task lifecycle), program
declarations (which program validates each family) and integrity memberships (roles, purposes,
and which declared purposes may own a privileged effect) are of this kind. A fact about one
operation (which families it belongs to, its entry
point, profile, forms, dependencies, effects) is a **lowered operation attribute**: preparation
archives it with the release, lowering copies it into the release's definition rows, and guards,
validators and dispatch read those rows at run time. Adding an operation to a family then
changes the release and not the kernel. Facts about an individual operation never enter
generators and reach programs through the release. This is RC01.

The rejected alternative is to hand the generators the effective operation model. That makes
every fact derivable at generation, and bakes per-release facts into an artifact that is
supposed to be independent of releases, which is what the id lists do today. A shared Python
table of memberships read by every generator removes disagreement between lists and keeps
membership outside the declaration and inside the kernel; it is an acceptable interim if this
work is delayed and is not the target.

### Three states, and their lowered form

**Proposed.** An operation's declaration has an optional, multivalued `validity_family` (the
slot is declared by [UDM-02](model-authorities-and-openness.md#udm-02--the-declaration-grammar-and-its-vocabularies-each-stating-its-openness);
its meaning is owned here). Its values are members of the closed `ValidityFamily` vocabulary, or
`none`, or `undetermined`.

| Declared | Meaning | Archived record | Lowered `(validity_families, validity_conservative)` |
|---|---|---|---|
| one or more ready families | each family's guard and validator apply, in conjunction | `families` = the named members | `(F, false)` |
| `none` | a positive claim that only generic validity applies | empty | `(∅, false)` |
| nothing, or `undetermined` | not yet classified | empty, conservative | `(∅, true)` |
| a claim that includes a provisional family | the ready part applies; the rest is not yet checkable | the ready members, conservative | `(ready part, true)` |

Mixing `none` or `undetermined` with family names refuses at preparation. That is internal
inconsistency: the declaration contradicts itself.

The physical representation replaces the optional string with two required columns on
`sem.data_operation_definition`: `validity_families`, a multivalued `ValidityFamily` that may be
empty, and `validity_conservative`, a boolean. Both are required, so absence in the row no
longer means anything; the three states are distinct values.

The reasoning for a set and not a single family is that an operation may turn out to need two
families' checks, and claiming a family is safe in the direction that matters: it adds checks,
since validity is a conjunction and guards refuse, so a wrong claim can cause a refusal and not
a permissive result. The permissive direction is not claiming, which the conservative flag
covers. That a claim can only add checks is reasoning from the shape of validity and is an open
premise (P9) until the native owner has read each validator and guard for a check that could
widen validity. A *required total classification with an explicit `none`* (the review's first
round) is rejected: it forces every new operation to decide its validity semantics before it
can compile and forbids membership of two families. *Reopens the choice:* if a family's
soundness proves to need pins per member that allowed sets cannot express, the review's
fallback is a closed owner list on the family member. That would bring facts about individual
operations into a generator input, so it is decided with the coordinator and not adopted here.

**Existing operations declare their claim.** Null today means, by the DDO specification's own
definition, that no per-kind validator applies, and most of the book pipeline is in that state
on purpose. The migration therefore has each existing operation's owner state its claim: the
27 classified operations name the families the classifier assigns them, and every other
existing operation declares `none`, unless its owner deliberately marks it undetermined. The
list of existing operations with their proposed claims is presented to the operator before
revision A is frozen. After the migration, only an operation added without a claim is
undetermined.

### Family declarations: member requirements, and one home for the validator

**Proposed.** Each non-provisional `ValidityFamily` member carries structured annotations for
the requirements a member operation must meet and for the inputs the family protects. It does
not name a program. Which program validates a family is stated in one place, the **program
declaration** of that program, which names the families it validates; a family's completion
guard and live-completion program are stated the same way. Programs are code artifacts whose
authority is the typed registry of UDM-09, so the fact sits with them. The vocabulary and the
program declarations are both generator inputs.

At generation, every family that is not provisional must have exactly one validator program
with the expected signature (one text argument, a boolean result). A family with no validator
is a dangling claim and a family with two is a duplicated one; both refuse, as does a program
that claims a family outside the vocabulary. That is internal inconsistency. UDM-05 precedes
the registry, so until UDM-09 exists it holds the mapping as one typed table in the compiler,
from family to validator, completion guard and live-completion program, checked against the
parsed statements that generation already walks
(`semantic/data_operation_storage.py:1890–1897`). UDM-09 absorbs that table into program
declarations and it is then deleted. Lowering refuses a family name outside the kernel's
generated set of ready families, so a release cannot claim a family that the installed kernel
cannot validate.

What a guard pins per operation id today, a family declares once for its members. Preparation
refuses an operation that claims a family whose requirements it does not meet, naming the
requirement, and the guard checks the same requirements against the lowered row. The per-id
factory pins retire, because the implementation-slice revision already authenticates the code.

**Requirements are written as allowed sets, not single values.** This is the point at which the
design could close something that is open today. The per-id pins *vary* across the members of a
family: contextual operations have profiles `derivation` and `discovery`, forms `[scalar]` and
`[batch]`, and CPU-receipt counts of zero and one. A requirement written as one value per family
would refuse members that exist. So the contextual family's requirement reads: profile within
`{derivation, discovery}`; forms within `{[scalar], [batch]}`; preparation `resource`; effects
empty. A member that meets the allowed sets needs no kernel edit, which is what makes adding a
member cheap. Where a pin distinguishes members by something other than an allowed set, the
distinction must come from the member's own declaration: sub-behaviours that today branch on the
id branch on declared input roles, and the receipt count needs a declared source, which is an
open premise.

Producer restrictions read the declarations. Where a guard today admits an input only from
listed producer ids, it reads the lowered dependencies and role kinds of the consuming
operation's definition row. A third query encoder that the declared roles admit is then
admitted, where today it would be refused by a list.

### Privileged-effect owners stay closed

**Proposed.** Where a guard authorizes rather than validates, membership is an integrity fact
and stays closed. The member of the effect vocabulary declares which purposes may own that
effect; that declaration is an integrity membership and a generator input. An operation claims
the effect and states its effect authorization in its own declaration, which is lowered with
the release, and the guard refuses any claimant whose lowered authorization carries none of
the permitted purposes. This is the shape the three guards named in the baseline already have,
with the owner stated as a declared purpose in place of an operation id, so that no fact about
an individual operation enters a generator. Whether a declared purpose is as strong an owner
as today's id pin for each of the three effects is an open premise (P10). An effect member
marked privileged that declares no owning purpose refuses at generation; absence never means
"any claimant". A change of privilege is rare and should change the kernel. The evaluator authorization performed for three literal ids becomes a
derivation from declarations: an operation whose output kind universe is `evaluator`, or whose
declared effect authorization includes the evaluator purpose. That derivation is inferred from
source and is an open premise for the native owner.

### Generated dispatch and the completion chain

**Proposed.** Dispatch is generated from the ready members of `ValidityFamily`: the conjunction,
over ready families, of "this family is in the row's `validity_families` implies its validator
holds for the node", and "the row is conservative implies the conservative validator holds".
There is no `else`. The completion chain is generated the same way: each family's guard runs
under "this family is in the row's set"; guards selected by a declared attribute (PDF, external,
command class) keep their declared selectors; the generic checks (product validations, output
witnesses) run for every operation. The early returns inside validators and guards are removed,
because the programs are reached only through the generated dispatch and chain and an early
return is no longer a selection point. The list of guard names that completion calls is a list of
programs and moves to the program registry (UDM-09) when that exists.

Classification, dispatch and guards then read one fact in one place and cannot disagree.

### Keeping the kernel free of per-operation edits

**Proposed.** Three conditions make "adding an operation to a family changes the release, not
the kernel" true. First, no generator reads an operation id (the table under UDM-05). Second,
the kernel capture stops including operation-owner modules that it captures only for their
constants: `semantic/declared_structural_admission.py`
(`semantic/data_operation_storage.py:362–365`), `semantic/record_policy_authority.py`
(`:391–394`), `evaluate/selected_operation_events.py` and `evaluate/declared_record_policy.py`
(`:368–378`), and `methods/operation_events.py` with `evaluate/declared_operation_events.py`
(`semantic/operation_event_native.py:231–238`). A capture is kept only where a generator still
renders from the module; each is checked before removal. Third, the vocabulary module and the
family table are generator inputs and do move the kernel: adding a family is a kernel change, and adding an
operation to one is not. The whole-capture digest is replaced later by **program identity**
(UDM-10); these conditions are what make that layering meaningful for operation edits.

### Two enabling fixes

Two defects would make a correct design fail in practice, and both are in scope.

**The physical compiler's check for an array column.** For a slot whose range is an enumeration,
the relational compiler renders a membership check as `column IN (...)`
(`schema/relational.py:512–517`). That is wrong for a multivalued slot, which compiles to an
array column: the check must be containment, `column <@ ARRAY[...]`. `validity_families` is the
first multivalued enumeration-ranged physical column that needs the check. The fix belongs to
the relational compiler and applies to every multivalued enumeration range.

**Old rows keep the meaning they were written with.** Existing definition rows are converted
by the revision's migration: a non-null family string `f` becomes `({f}, false)`, and null
becomes `(∅, false)`, the lowered form of `none`, because "no per-kind validator applies" is
what null meant when those rows were written. No old row becomes conservative. Releases are
re-prepared at revision A in any case, and a re-prepared release lowers the claims its
operations now declare. The development database is regenerable, so regenerating it is an
acceptable alternative to the conversion.

### Releases are re-prepared, not re-lowered

Any native revision already forces re-preparation: the generated release guard requires the
archived native digest to equal the installed descriptor's
(`semantic/native_admission_release.py:516–533`), and release ids hash the native capture
(`semantic/prepare.py:975–986`). So this work needs no data step that re-lowers admitted
releases, of the kind `ddo_n1_relower` was (`schema/data_steps.py:115–160`). The default
releases are re-prepared and admitted under the new kernel, and older releases remain as inert
rows that cannot be deployed. The archive gains the validity record on each operation.

### Conservative validity

**Proposed.** The shared contract **conservative validity** is realized as follows. It applies
to an operation whose lowered row is conservative, which after the migration means one added
without a claim, one its owner marked undetermined, or one that claims a provisional family.
The whole-book run does not exercise it unless the operator chooses to mark an operation
undetermined.

*Meaning.* "Over-invalidates rather than under-invalidates" means: for every state change after
publication that could make any family's validator judge the derivation invalid through a
recorded mutable premise, the conservative check judges it invalid; it may also invalidate where
no family would. The recorded mutable premises are a trust epoch in the project and the
validating kernel.

*The requirement.* Every run is tied to a trust snapshot, because every published derivation has
one receipt with one. But for an operation that declares no family, the snapshot covers only the
scopes of its declared support. A trust-bearing input it consumes outside declared support, as a
grade consumes its cut, is not recorded, and comparing that snapshot alone would
*under*-invalidate. Therefore, for an operation whose lowered row is conservative, completion
locks and records **all trust scopes of the request's project**, by extending the scope union of
the completion lock program (`ddo_lock_completion_support`) with a branch selected by the lowered
flag.

*The validator.* One generated program. A derivation of a conservative operation is valid when
generic validity holds, the meaning of the receipt's trust snapshot equals the meaning of the
project's current epoch map (so a scope created later at epoch zero does not count as change,
and one created later and revoked does), and the receipt's `validating_kernel_digest` equals the
installed kernel. When UDM-10 delivers the validator identity layer, the last comparison becomes
the conservative validator's own identity, and a kernel change that does not touch it stops
invalidating.

*Cost, stated qualitatively.* Completion of an undetermined operation takes share locks on every
trust scope of its project, where a classified operation locks only the scopes it supports on.
Those locks contend with revocation, which takes scope locks exclusively: a revocation anywhere
in the project waits for in-flight completions of undetermined operations, and they wait for it.
The receipt's snapshot holds one entry per scope of the project. And the check invalidates on
any trust change anywhere in the project and, until the validator identity exists, on any kernel
change; invalid derivations are recomputed on demand, as today. The share locks are taken
inside the settlement transaction under its five-second lock timeout, so a revocation in the
project during such a completion surfaces as a lock timeout classified as an operational
failure. For a project the size of one book, with few scopes and rare revocations, this is
expected to be a small price for running an operation nobody has classified.

*Shown to fit settlement before the book run.* UDM-06 makes one bounded observation on the
stage, described under that package, of the conservative path completing inside settlement
under concurrent completions. It settles one decision: whether the conservative branch holds
share locks on the project's trust scopes across settlement, or records the project's epoch
map without holding them and states the narrower guarantee. If the path cannot complete
within settlement limits, the design changes in UDM-06 before revision A is frozen. The final
runs observe and do not tune; if either reveals a needed change, the change is made within the series and the affected evidence is gathered again.

*What would make classification preferable.* The price grows with the number of scopes in the
project, with the frequency of revocation, with the number of undetermined operations completing
concurrently, and with the cost of recomputing their results. An expensive operation (a model
inference over a whole book) whose results are discarded by an unrelated revocation is the case
where declaring `none` or a family pays for itself at once; so is a project with many sources
under active trust revision. The diagnostic exists to make that choice visible. Nothing in the
design forces it.

*Residual risk.* A family-specific premise outside trust and kernel, such as the contextual
family's linguistic premise, is not covered by the conservative check. That is why family
bindings exist, and under this design the gap is reported for each undetermined operation and
is not silent.

*What an undetermined operation receives.* The generic completion checks; any guard selected by
an attribute it declares; no family guard, since no family's output contract is known to apply;
and the conservative validator.

*Rejected:* comparing the receipt's existing snapshot without widening the lock (it
under-invalidates, as shown); treating undetermined as permissive with a diagnostic only (today's
behaviour made visible, which leaves the integrity risk); refusing at a promotion boundary (the
operator decided against it). *Reopens the choice:* only the bounded observation above, which
decides between holding the locks and recording the epoch map without them.

### The diagnostic, and where the operator sees it

**Proposed.** An undetermined operation produces exactly one non-refusing diagnostic. For an
absent declaration it is the structural diagnostic that
[UDM-02](model-authorities-and-openness.md#the-declaration-class-and-its-validator) owns, the
recommended-slot warning, which UDM-05 switches on in the change that writes the existing
claims; UDM-06 supplies its consequence text and adds no second diagnostic for it. For an
explicit `undetermined`, which the grammar accepts silently, the compiler
emits the same diagnostic from the compiled state:

> code `validity_undetermined`; location: the operation id; message: "validity family not
> declared; conservative validity applies"; outcome `unchecked`; remedy: "declare
> `validity_family: [<family>…]` or `[none]`".

A claim that includes a provisional family produces `validity_family_provisional` in its
place, naming the family. An operation that declares `none` while its declaration shows it
consuming an input that a ready family protects is reported by the same route as
`validity_claim_unprotected`, naming the family. That second diagnostic is a non-refusing
report owned by UDM-06: the operation is not refused, because `none` is its owner's positive
claim, and the report is how a wrong one is noticed. The operator sees these
in two places. The first is the preparation validation
report, where the outcome `unchecked` maps to the category `unassessed` and the report is marked
incomplete without refusing (`semantic/operation_reporting.py:372–377`); this is the route
[UDM-02](model-authorities-and-openness.md#the-declaration-class-and-its-validator) opens by
giving the compiler a diagnostics return. The second is durable: the lowered columns of every
admitted release record which operations are conservative, so a release inspection lists
unclassified operations from the database without the in-memory report, for any release and at
any later time. UDM-06 owns which existing inspection command carries that list; no new report
type is added.

### One support-edge meaning

**Proposed.** `SupportEdgeKind` is a closed vocabulary. Each member carries structured
annotations: its source node kind, the relation and key columns that realize it, its target node
kind, its group (conjunctive, or an alternative with its activation condition, which is value
substitution under a value-strength demand), and the *traversal profiles* it belongs to. A
member without its source kind, target kind, group or profiles refuses at generation, as an
omission in the integrity layer. The profiles are `validity`; `scope`, which is deliberately a superset of validity and is used for
lock scope; `public`, which adds the authority leaf for public reads; and optionally `lineage`.

One reference-to-node mapping is declared once: a reference of kind `original-source` or
`authored` is an original, identified by `admission_id`; one with `admission_use_id` present is
a use; one with `derivation_id` present is an episode; anything else **refuses**. The default
that classifies an unrecognised reference as an episode is removed.

From the table are generated: the validity edge program; `_support_walk`, as a recursive common
table expression in SQLAlchemy Core; the lock-scope walk; and an *explanation output* of the
validity closure, which reports for each reached node that it is valid or names the revoking
edge and selector. Change impact consumes that output, and its own walk, its reference mapping
and its Python scope key retire. The trust-scope key then has one definition, `ops.ddo_scope`.

Generating two profiles from one table keeps the distinction between validity and its superset
explicit instead of erasing it. *Rejected:* moving change impact's walk to DuckDB over exported
edges, which re-hosts the third encoding; keeping the encodings with a cross-check test, which
leaves several places to edit per edge kind. *Reopens the choice:* if the lineage walk's owner
shows it must not agree with validity, it stays a named single-purpose walk outside the table.

## The contract UDM-05 supplies to UDM-10

UDM-10 defines a validator identity per family. It takes the following from this companion and
nothing else.

1. **The enumeration of families.** The ready members of `ValidityFamily`, read from the
   compiled model's vocabulary table, plus one reserved family-like entry for the conservative
   validator (added by UDM-06). The set is closed, so the identity map has a known key set at
   generation.
2. **The programs of each family.** For each ready member, its validator program and its
   completion guard, from the typed family table of UDM-05 or, once UDM-09 has absorbed it,
   from the program declarations. Generation has already refused a family with no validator or
   with two, so every name UDM-10 receives is an installed program. UDM-10 computes the
   identity. A family's validator identity covers every program that decides a validity outcome for
   the family: its validator program, that program's transitive callees and the family's
   completion guard. The shared
   live-completion program (`ddo_require_completion_live`,
   `semantic/data_completion_settlement_native.py:722–760`) serves every family: it belongs to
   the kernel identity, not to any one family's. The per-family requirement programs it calls,
   such as the record-grade cut requirement, decide an outcome for their family and are inside
   that family's identity. Today it reaches them by testing a literal operation id, which is
   one of the selection sites UDM-05 replaces.
3. **Provisional members have no validator identity.** Their member operations are conservative,
   and the conservative entry's identity covers them.
4. **The per-operation key set.** The lowered row gives, for any operation, `validity_families`
   and `validity_conservative`. The set of identities a receipt or seal must carry for that
   operation is exactly the row's families plus the conservative entry when the flag is set.
5. **The interim.** Until UDM-10 lands, receipts and the conservative validator compare the
   whole kernel digest, as today. The transition from digest to per-family identity is UDM-10's
   and belongs to the identity transition revision, not to revision A.

A change to this contract (what a validator identity covers; a requirement that changes which
program validates) is a change both companions record.

## What this supersedes

UDM-00 writes the decision records and amends the design sections; this table states what they
must say. Passages concerning the grammar, openness and privileges are listed in the
[model authorities companion](model-authorities-and-openness.md#what-this-supersedes).

| Owner and passage | Says today | Replaced by |
|---|---|---|
| DDO [products and support](../declared-data-operations/products-and-support.md) `:422–423` | "`validity_family` (null when no per-kind validator applies)" | RC05: two required columns; `none` is explicit and is what every existing unclassified operation declares, so old null rows convert to `none`; absence on an operation added later is undetermined and conservative; several families allowed |
| the same, `:451–452` | the per-kind check "runs only when its lowered `validity_family` is non-null and checks only mutable premises (kernel digest, and cut trust …)" | generated dispatch over the family set, plus the conservative validator |
| the same, `:429–432` | "Validity compares `native_kernel_digest` …; a successor that changes the lowering re-lowers every admitted release" | kept until UDM-10 changes the comparison; this series re-prepares releases instead of re-lowering them |
| [ADR-0131](../../adr/0131-model-owned-postgresql-programs.md) Decision (`:32–42`) | the model governs "physical types and call correspondence"; "Convert remaining maintained owners forward" | RC01: facts that programs dispatch on have one declared home; facts about an individual operation reach programs through lowered release rows; model-level vocabularies, program declarations and integrity memberships are generator inputs; generation refuses only internal inconsistency and integrity omissions; the conversion clause becomes an extraction clause |
| DESIGN §B4 head (`docs/design/DESIGN.md:505–508`) | native behaviour "compiles from model-owned relations, call contracts and typed Python programs … Full source conversion remains open." | add declared vocabularies and lowered operation facts; drop the sentence about open conversion |
| DESIGN §B4, the ADR-0122 paragraph (`docs/design/DESIGN.md:513–518`) | completion correspondence "reusable only under its actual validator identity; … mutable family checks" | unchanged in substance; the conservative validator is added as a family-like identity |
| [ADR-0024](../../adr/0024-semantic-release-preparation.md) (`:46`) | "Unsupported required semantics refuse" | RC14, as used here: an undetermined validity declaration is a non-refusing `unassessed` diagnostic with a stated consequence; no promotion boundary |

## UDM-05 — Validity declarations lowered per release, and selection by the lowered attribute

**Implementation vision.** The package gives each `ValidityFamily` member its requirement
annotations and holds the family table. It writes an explicit claim on every existing
operation: the 27 that are classified today name the families the classifier assigns them, and
every other one declares `none` unless its owner deliberately marks it undetermined, so that
behaviour is unchanged for all of them. In the same change it switches on the `recommended`
marking of the slot. It then compiles the claim into the archived validity record, replaces
the column with the two required columns, changes lowering to copy the archived record,
generates dispatch and the completion chain from the vocabulary and the family table, and
replaces every selection by id. It owns the family requirements, written as allowed sets, and
the declared owning purposes of privileged effects. Its failures are all at preparation or
generation. Three are internal inconsistency: a self-contradictory claim; a claim on a family
whose requirements the operation does not meet; a family with no validator program or with
two. One is an omission in the integrity layer: a privileged effect with no declared owning
purpose. At run time a guard refuses a completion that violates its family's contract, as
today.

The entry step lists every existing operation with its proposed claim. The list is presented
to the operator before revision A is frozen and is recorded in the package's completion note.

The package also delivers the connections of facts that are already declared and that kernels
restate as literals (R07's "now" row; DA-086), in the same revision, because each changes
program bytes: shared-stream trigger membership from `ph:immutability: pending-content`; task and
record state tests from the protocol lifecycle, as the task guard already reads it
(`semantic/data_operation_protocol.py:117–128`); kind-universe literals from the typed universe;
codec tags, including the tuple at `semantic/data_operation_value_native.py:49`, from the
observations vocabulary; product member families from the protocol definitions;
encoder failure codes from the Python set. The typed read boundary for the lowered
`support_contract` (`semantic/native_definition_projection.py:31–42`) takes its shape from the
effective model's dataclasses, so a renamed property fails at generation. A field-kind type map
that UDM-01 finds to change a generated byte when connected is delivered here too.

Release composition (DA-073) is the remaining part of R02 assigned here: a release's contents
become the closure of the requested operations mapped to source collections, with the source
collection of an operation derived by static extraction from the captured collection that holds
its literal (`semantic/python_operation_sources.py`) and an `acquired_by` field declared only to
override the derivation. It stays in this package because it needs the per-operation
declarations and changes no installed program. The investigation behind this companion did not
design it, so it begins with an inventory of the flag logic
(`semantic/primary_operations.py:118–392` and the family source functions the finding names),
which is an open premise.

**First steps, from the open premises.** Before generation changes: the native owner reads every
consumer of `definition_identity` and confirms that it may cover the validity record while the
recipe excludes it (P1); the further per-id branches of the rich module are read and each is
given a declared selector or a family requirement (P7); the home of the structural dossier id
(P3), the declared source of the CPU-receipt count (P2) and the evaluator-authorization
derivation (P4) are settled or the affected site keeps an interim declared owner; and the
native owner reads the validators and guards for a widening check (P9) and confirms the
owning purposes of the three privileged effects (P10). These are listed under
[Open premises](#open-premises).

**Complete consumer scope: every selection by hand list, and its replacement.** These are the
audit's twelve lists and seven further sites found by searching generator modules for
operation-id literals. This is the complete scope, not a sample.

| # | Site | Today | Becomes |
|---|---|---|---|
| 1 | `data_operation_compiler_native.py:483–529` | classifier over 27 ids | retired; every existing operation declares its claim; lowering copies the archived record and refuses a family name the kernel has no validator for |
| 2 | `data_validity_native.py:272–288` | dispatch with `else_=True` | generated from ready `ValidityFamily` members, plus the conservative branch; no `else` |
| 3 | `data_completion_settlement_native.py:548–563` | fourteen guards, each selecting itself | generated chain: family guards under family membership; attribute guards keep their declared selectors; generic checks unconditional; the name list moves to the program registry |
| 4 | `data_completion_settlement_native.py:576–587` | evaluator authorization for three ids | derived from the output kind universe `evaluator` or a declared evaluator effect authorization (P4) |
| 5 | `data_completion_settlement_native.py:744–806` | live-completion chain by literal ids | generated from the live-completion program the family table names for each family |
| 6 | `contextual_admission_native.py:188–201, 215, 568, 736` | twelve-entry factory dictionary; early returns | dictionary retires (the implementation slice authenticates, `:225–236`); returns removed |
| 7 | `contextual_admission_native.py:234–259, 571, 635, 686` | per-id profile, forms, receipt count, sub-behaviours | family requirements as allowed sets, checked against the lowered row; sub-behaviour by declared input roles; receipt count per P2 |
| 8 | `contextual_admission_native.py:291–310, 369` | required roles and producers per role by id | lowered dependencies and role kinds |
| 9 | `contextual_definition_native.py:51–57, 140–170` | lineage producer ids | lowered dependencies of the consumer |
| 10 | `contextual_witness_native.py:136, 240–251` | producer ids | lowered dependencies of the consumer |
| 11 | `definition_admission_native.py:33–44, 345–372, 386, 418` | `_OPERATIONS`, `_FACTORIES`; early returns | family requirement; returns removed |
| 12 | `artifact_admission_native.py:112, 147, 217` | one id, three times | family membership and requirement |
| 13 | `rich_admission_native.py:606–622, 816–823, 903–910` | three lists | family membership; the `rich.admit` owner pin (`:1186`) becomes the effect member's declared owning purpose (P10) |
| 14 | `rich_admission_native.py:582, 676, 920, 944, 951, 1219, 1278` | further per-id branches | declared roles or effects per branch, after the owner's reading of each (P7) |
| 15 | `operation_event_native.py:55–60, 350, 1287, 1359` | `_OPERATIONS`; early returns | family membership; returns removed |
| 16 | `operation_event_native.py:1277` | kind universe by id | the lowered output kind contract's universe |
| 17 | `record_grade_native.py:534, 702, 1445`; `record_policy_completion_native.py:1140, 1170, 1471–1476` | owner constant or literal; early returns | family membership |
| 18 | `structural_admission_native.py:1058` | `structure.dossier/declared` by id | needs a home (P3) |
| 19 | `structural_admission_native.py:824–831`; policy and PDF eligibility | owner id inside an eligibility predicate | owning purposes declared on the effect vocabulary member; a claimant without one refuses (P10) |

Sites 9, 10, 14, 16, 18 and 19 and part of 17 are the ones the audit's count did not include.
All paths are under `semantic/`. Beyond these: every existing operation literal, in the 62
modules that assign `__data_operation__`, which gains an explicit claim (operations re-counted
at entry); the physical declaration and its relational check; the archive's operation
record; and the tests of the classifier, dispatch and guards, which move to the declarations.

**Removed.** The classification program; `else_=True`; every early return used as a selection
point; `_FACTORIES`, `_OPERATIONS` and the factory dictionary; the per-id pins; the evaluator id
list; the captures of operation-owner modules held only for constants; the optional
`validity_family` string column.

**Prerequisites.** UDM-02 supplies the `ValidityFamily` vocabulary with its openness, the
`validity_family` slot on the declaration class, the vocabulary table on the compiled model and
the compiler's diagnostics return. The operator's reading of the proposed claims precedes the
freeze of revision A.

**Native revision.** A, shared with UDM-06 and with the decimal bound of UDM-18. It is the
first of the series' three revisions. The two are batched so that no interim exists in
which the conservative flag is lowered and no conservative program is installed. If they must be
separated, dispatch maps the flag to today's generic treatment plus the diagnostic until UDM-06
lands, which is no worse than today and more visible; the plan does not prefer that.

**What this keeps open.** Every existing operation behaves as it does today. Adding an
operation with unknown validity semantics stays cheap: it declares nothing, compiles, runs and
publishes. An operation may claim two families. A family
may be declared before its validator is written, as a provisional member. A new member that
meets a family's allowed sets needs no kernel edit, and a new producer that the declared roles
admit is admitted. Newly closed, and in the integrity layer: a family name the kernel cannot
validate refuses (a dangling name), and a privileged effect has declared owning purposes, as
the guards already enforce by literal, and refuses at generation when it has none. The risk this package carries is narrowing by accident: a family
requirement written as a single value would close what the per-operation pins vary today.
Requirements are therefore allowed sets, and the first acceptance item below fails if any of the
27 existing members is refused.

**Acceptance evidence.** Expected values are written by hand and are never outputs of the
compiler or of lowering.

- The 27 existing operations, with their explicit declarations, prepare without refusal, and
  their lowered rows equal a hand-kept table of `(families, false)`. A requirement written too
  narrowly refuses one of them. Every other existing operation lowers as `(∅, false)`, against
  the list the operator read; none is conservative unless that list marks it undetermined, and
  preparing the real modules yields no `validity_undetermined` diagnostic for any of them.
- A small hand-authored model and fixture database with four operations whose ids appear in no
  former list. P claims two real families; Q declares `none`; R declares nothing; S claims a
  family whose requirement it violates. Expected: lowered rows `P: ({f1, f2}, false)`,
  `Q: (∅, false)`, `R: (∅, true)`; S refuses at preparation and the message names the
  requirement. A lowering that still calls a classifier yields null or empty for P.
- A completion of P runs both family guards: each guard's refusal is provoked once by a
  completion that violates that family's contract. A guard that still selects by id returns early
  for P and the violating completion succeeds.
- A change of cut trust invalidates P through its grade-family premise and leaves Q valid. A
  dispatch that still defaults to valid leaves P valid.
- Perturbation of the declaration in the test, on a real operation among the 27, because no
  generator reads a fixture's id or captures its module: its claim is edited in a temporary
  copy of its owner module and the release re-prepared. The kernel descriptor's source digest
  is unchanged, the release id changes, and the removed family's guard no longer runs for it.
  A generator that still reads operation ids or captures an operation-owner module moves the
  digest.
- A family is added to a copy of the vocabulary with no validator program in the family table:
  generation refuses and names the family. A second program claiming an existing family refuses
  as a duplicate. Marked provisional, the new family generates, and its claimant lowers as
  conservative.
- A privileged effect member stripped of its owning purposes in a copy refuses at generation. A
  fixture operation that claims the effect without a permitted purpose is refused at
  completion.
- A third query encoder, declared with the roles the scoring operation's input admits, is
  admitted as a producer; expected by reading the declared roles, not the former list.
- The array check: inserting a definition row whose `validity_families` holds a value outside
  the vocabulary is rejected by the database, and an empty array and a two-member array are
  accepted.
- The conversion: a database holding definition rows with a family string and with null is
  migrated; the expected rows are `({f}, false)` and `(∅, false)`, and no converted row is
  conservative.

## UDM-06 — The conservative validity check and its diagnostic

**Implementation vision.** The package adds the conservative branch to the completion lock
program, generates the conservative validator, wires the conservative branch of dispatch to it,
emits from the compiled state the diagnostics the grammar cannot see (`validity_undetermined`
for an explicit `undetermined`, `validity_family_provisional` and
`validity_claim_unprotected`), and makes the unclassified operations of a
release listable from its lowered rows. It owns the definition of the conservative premise and
the choice of inspection command that carries the list. It never refuses an operation for being
undetermined; its only run-time effect is that a derivation of such an operation is judged
invalid when the project's trust or the validating kernel has changed.

**The bounded settlement observation.** Before revision A is frozen, the package shows on the
stage that the conservative path fits settlement. With the revision's candidate programs on
the stage's bounded project, a fixture operation left undetermined completes while other
completions of the same project settle concurrently and while a revocation is issued in the
project. The observation records the lock waits inside settlement against the five-second
lock timeout and whether every completion settles. It is a functional check with a recorded
wait, not a speed target. The decision it settles is whether the conservative branch holds
share locks on the project's trust scopes across settlement. If the path cannot complete
within settlement limits, the design changes here, for example to recording the scopes
without holding locks across settlement, with the narrower guarantee stated, and the
observation is repeated on the changed design. The result is an evidence record.

Its first step settles the premise that the cut scopes of grade, fit and event operations lie in
the request's project (P6), by reading `ddo_record_grade_completion_scopes` and its two siblings.
The project-wide snapshot assumes it; if a cut scope can lie outside the project, the
conservative branch must also record those scopes, or the guarantee is stated with that
exception.

**Complete consumer scope.** The completion lock program and its scope union
(`semantic/support_trust_native.py:208–231`); the receipt's trust snapshot as written at
publication (`semantic/data_derivation_native.py:604–615`), whose content widens for
conservative operations and whose shape does not change; the dispatch generated by UDM-05; the
compiler's diagnostics; the preparation validation report; one release inspection command. No
existing operation becomes conservative through this package: UDM-05 has each of them declare
its claim. The consumers are operations added afterwards without a claim and any existing
operation its owner chose to mark undetermined.

**Removed.** The permissive treatment of an unlisted operation. Nothing else; this package adds
the backstop that makes UDM-05's removal of the default safe.

**Prerequisites.** UDM-05 supplies the lowered `validity_conservative` flag and the generated
dispatch.

**Native revision.** A, with UDM-05.

**What this keeps open.** This package is the reason the exploratory move stays cheap: an
operation nobody has classified runs on a book and its results are kept, at the price stated
under [Conservative validity](#conservative-validity). Nothing is newly closed. What changes is
a default, from permissive to conservative, and only for an operation added without a claim.

**Acceptance evidence.**

- Using the UDM-05 fixture: a revocation in a scope of the same project that R's declared
  support does not touch invalidates R and leaves Q valid. Expected by hand from the definition.
  A validator that compares only the declared-support snapshot leaves R valid, which is the
  under-invalidation the requirement exists to prevent.
- A trust scope created in the project after R's publication at epoch zero leaves R valid; the
  same scope then revoked invalidates R.
- R's receipt records an epoch for every trust scope of the project present at completion; the
  expected scope list is written from the fixture. Q's receipt records only its support scopes.
- A revocation in another project leaves R valid.
- Perturbation of the declaration in the test: R's declaration is edited to `none` and the
  release re-prepared. The release id changes, R's next derivation records only its support
  scopes, and a later unrelated revocation leaves it valid. That the kernel digest does not
  move with a claim is shown on a real operation in UDM-05's perturbation.
- The diagnostic: preparing the fixture yields exactly one diagnostic for R, the structural
  `validity_undetermined` that UDM-02 owns, with the stated remedy text; the report's category
  is `unassessed` and the report is incomplete and not refused. An explicit `undetermined`
  yields the same single diagnostic. A claim on a provisional family yields
  `validity_family_provisional` and no second diagnostic.
- A wrong claim cannot fail open. A fixture operation that names a family whose validator
  would refuse it is refused, at preparation where it violates a requirement and at
  completion where its output violates the family's contract; in neither case is its result
  published as valid. A fixture operation that declares `none` while consuming an input the
  grade family protects is reported as `validity_claim_unprotected` and is not refused.
- The bounded settlement observation above has a recorded result on the stage, and the
  conservative branch that ships is the one it supports.
- The durable list: the inspection command, run against the admitted release with no preparation
  report in memory, lists R and not P or Q.
- An undetermined operation that declares `pdf-native` preparation still receives the PDF guard,
  provoked by a violating completion.

## UDM-07 — One declared support-edge meaning and one reference-to-node mapping

**Discovery correspondence (I03).** UDM-05 supplies the current declared discovery relation and
operation contract. UDM-07 aligns the native attachment and closure paths. Today attachment can
fulfill an equivalent prior-release discovery while `close_data_population`
(`semantic/demand_registration_native.py:1338–1365`) separately requires the producing request's
release to match. Replace that release-equality shortcut with the exact fulfilled current-demand
use and the relation it admits. Check the authenticated original derivation, producer recipe and
output role against the current allowed relationship and shape; verify exact member coverage and
completeness, project and source scope, and live purpose, trust and support. Preserve the old
producer and release on its evidence. Use existing admitted demand use and native relationships;
supersede the overlapping same-release-only check. If equivalence cannot be established, attachment
must not claim closure; report fresh discovery or refusal under current authority as appropriate.

Use UDM-20's small cross-release reproducer before selecting the native revision. This change
joins B when the proof is expressible over current released facts; it joins the identity transition
if it needs UDM-10's new identities. Stage confirmation and UDM-22 check an equivalent producer
that closes without invocation, wrong role/relation, incomplete scope, changed recipe, revoked
support, and a changed member that schedules only the necessary new work. Retain the actual
population edge kind and direction in every case. [Identity and current validity](programs-identity-and-revisions.md)
own the family and authorization gates. [Recovery](operation-reuse-and-recovery.md#udm-25) owns
private artifacts, which do not enter this closure as published results.

**Implementation vision.** The package annotates the `SupportEdgeKind` members with the traversal
table, declares the reference-to-node mapping, generates the validity edge program, the
projection walk and the lock-scope walk from the table, adds the explanation output to the
validity closure, and moves change impact onto it. It owns the table and the profiles. It has
two failures: at generation, a `SupportEdgeKind` member without its required annotations
refuses; at run time, a support reference that matches no declared kind refuses at the point
where the reference is read. What remains of change impact after its walk retires is a plain
Python classification, which indexes revocations by node instead of scanning every node
against every revocation, as the review's judgment table asks.

The execution plan resolved P5. A population follows its admitted discovery use and
parent population. A bare population-to-episode hop carried no corresponding evidence in
validity and is removed from change impact. Source admission uses the separate historical
lineage profile because it establishes source ancestry without imposing current validity
on historical evidence.

**Complete consumer scope.** The validity edge program (`semantic/data_validity_native.py:87–240`);
`_support_walk` and its six callers (`semantic/data_operation_projections.py:396, 466, 530, 1157,
1685, 2232`), including the public reads that use the authority leaf; `_reference_node`
(`:156–169`); the lock-scope walk; `_revocation_causes`, its reference mapping and its scope key
(`semantic/change_impact.py:332–441`); the operation-level "which operations changed"
computation in change impact, which reads the compiled `selected-dependencies` projection
instead of its own traversal; and the lineage walk of source admission
(`semantic/source_admission_native.py:1129–1135`), which becomes the `lineage` profile if its
owner confirms that it must agree with validity and otherwise stays a named single-purpose walk.
Knowledge relations, pack predicates, proposed links and alternatives are not support edges and
are not touched.

**Removed.** `_revocation_causes` and its two private mappings; the Python trust-scope key; the
`episode` default of `_reference_node`; the inline reference classification in the validity
program.

**Prerequisites.** UDM-02 supplies the `SupportEdgeKind` vocabulary and the vocabulary table.
The ruling on the population edge.

**Native revision.** B, shared with
[UDM-03](model-authorities-and-openness.md#udm-03--role-and-purpose-vocabularies-the-typed-physical-profile-grants-from-program-declarations).
If the generated validity program is byte-identical to the installed one once the disagreement is
resolved in its favour, the differing bytes are only the explanation output and the refusal.

**What this keeps open.** Everything in the knowledge layer: support edges are provenance among
native rows, and a new knowledge relation or pack predicate is unaffected. The scope walk stays a
deliberate superset of validity. Newly closed, in the integrity layer: an unrecognised support
reference refuses where today it is treated as an episode. A new provenance node kind is a
native schema change in any case, so this closes nothing that an exploratory move in a pack or
an operation could reach.

**Acceptance evidence.**

- A fixture support graph with one alternative group under value substitution and one population
  chain. The validity set, the scope set and the public set are computed by hand for each
  traversal profile and compared with the generated walks. A table that puts an edge in the
  wrong profile changes one set; the scope set must strictly contain the validity set in the
  fixture, which fails if the two profiles were collapsed.
- A reference with neither an original kind, an `admission_use_id` nor a `derivation_id`
  refuses and names the reference; today's code would classify it as an episode. An edge kind
  stripped of its target kind in a copy of the table refuses at generation.
- Change impact's reported causes for a revocation in the fixture equal the hand-computed
  revoking edges and selectors, and are produced with `_revocation_causes` deleted.
- Perturbation of the declaration in the test: an edge kind is removed from the `validity`
  profile in a copy of the table, and the node it reached leaves the hand-predicted validity set
  while staying in the scope set.
- The trust-scope key reported by change impact for a project and source equals the value of
  `ops.ddo_scope` for the same pair.
- The population edge: one fixture case constructed so that the two former encodings would
  disagree, with the expected answer taken from the ruling.

## Open premises

P-numbers are the investigation's. P8 (importing the vocabulary module into the physical
closure) is the first step of UDM-02 and is listed in the
[model authorities companion](model-authorities-and-openness.md#open-premises).

| Premise | Evidence that settles it | Work it constrains |
|---|---|---|
| P1. `definition_identity` may cover the validity record while the recipe excludes it, so that classifying an operation later changes neither its results nor their reuse | The native owner's reading of every consumer of `definition_identity` (`semantic/data_operation_model.py:529–566` against `:594–620`) | First step of UDM-05 |
| P2. The contextual CPU-receipt count (zero for scores, one otherwise; `semantic/contextual_admission_native.py:255–258`, `semantic/definition_admission_native.py:366–369`) has no declared source | Tracing what produces CPU receipts; if the count is not derivable from forms or preparation, the native owner or the operator chooses a declared execution-evidence field for the grammar | **Blocking** for site 7 of UDM-05; until settled the count is a declared per-member requirement value, not an id test |
| P3. The home of `structure.dossier/declared` (`semantic/structural_admission_native.py:1058`): a validity family member, a command class, or generic | The native owner's or the operator's decision | **Blocking** for site 18 of UDM-05 |
| P4. "Writes a kind of the evaluator universe" implies the evaluator purpose for every operation, so the evaluator authorization can be derived | The native owner's confirmation against `semantic/operation_event_native.py:1277` and the declared effects; depends on the role-name premise in the model authorities companion | Site 4 of UDM-05 |
| P5. Population support | The accepted execution plan follows admitted discovery use and parent population | Settled for UDM-07 |
| P6. The cut scopes of grade, fit and event operations lie in the request's project | Reading `ddo_record_grade_completion_scopes` and its two siblings | First step of UDM-06 |
| P7. The rich module's further per-id branches (`semantic/rich_admission_native.py:582, 676, 920, 944, 951, 1219, 1278`) were located and not read | Reading each; each receives a declared selector or a family requirement | First step of UDM-05 for site 14 |
| Historical lineage | Source admission establishes source ancestry even when later support is revoked | UDM-07 supplies a separate `lineage` profile |
| The release-composition part (DA-073) was not designed by the investigation | An inventory of the flag logic and source functions at UDM-05's entry | The DA-073 part of UDM-05 only; nothing else waits on it |
| P9. No family validator or guard contains a check that could widen validity for a member that claims it, which is the basis for allowing several families and for treating a wrong claim as safe | The native owner's reading of each of the seven validators and fourteen guards | Multi-family claims in UDM-05; if a widening check exists, that family refuses co-membership until it is removed |
| P10. A declared purpose is as strong an owner as today's operation-id pin for each of the three privileged effects (rich admission, policy authorization, structural admission) | The native owner's reading of the three guards and of who may declare each purpose | Sites 13 and 19 of UDM-05; until settled, the affected guard keeps its pin |
| Every existing operation's proposed claim is what its owner intends | The operator's reading of the list before revision A is frozen | The migration in UDM-05 |
| The conservative path completes within settlement limits under concurrent completions | The bounded observation of UDM-06 on the stage, before revision A is frozen | Whether the conservative branch holds share locks or records the epoch map without them |

<a id="revision-a-candidate-execution"></a>

## Revision A candidate execution

The release compiler archives explicit `none`, ready families or a conservative claim. The
27 previously classified operations carry their N29 claims. Definition identity covers the
validity record. Recipe identity excludes it. PostgreSQL lowering copies the record into
required `validity_families` and `validity_conservative` columns. The migration converts the
stored N29 scalar and removes the classifier and scalar column. The array check rejects
unknown, provisional and null elements. Historical releases retain their original admission
meaning and require re-preparation to run with the current kernel.

The conjunction and family guards read the lowered set. Contextual and definition receipt
counts read the declared CPU receipt count. Contextual, definition, artifact, rich preparation,
event and selected evaluator consumers started reading roles, forms, kinds and family membership.
Protected grading and fit census selections and the three privileged effect pins remain.
Their removal requires a declared owner or capability with equivalent protection and a
negative control for foreign claimants. The remaining native owner captures and live-completion
branches still need that disposition before every per-operation fact leaves generation.

Authored workflows and explicit requests seed the required and alternative dependency closure
before provider configuration, asset reads, and collection construction. The same path handles
capture, arbitrary operation roots, and native-only requests. A selected learned collection
still acquires its declared four-provider bundle. A manifest without a selection deliberately
authors the configured full profile. Actual statistics acquisition passed for formal-only and
source-only roots without provider profile reads, and for its configured `phase0` workflow.

The declaration and batch compilation controls passed 30 cases on 2026-11-18
(`b0154a806f1944f788d5b010bafb1c7e`). They cover prior N29 family membership, claim consistency,
and replacement operation inputs that retain the exact captured grammar. Actual preparation of
a capture-only release succeeded with the unrelated profile paths unavailable. The capture
manifest and broad default controls passed (`0c88af703cd24c2a972e45480d52715e`).

Conservative settlement records the project epoch map under ordered share locks. Its validity
check compares the retained publication against the current nonzero project epochs and kernel
digest. `ci db check --release RELEASE --view validity` reports the conservative operation
IDs after authenticating the retained projection. Preparation reports `validity_undetermined`
and can advise `validity_claim_unprotected` for an explicit `none` that consumes a protected
input. The private candidate is scoped to this increment. Shared revision A includes the UDM-18
decimal bound. Full native claim parity remains open.

**Tested, 2026-11-18.** `uv run ci test --native-host private --workers 1 -- python/corpus-structure/tests/semantic/test_udm_validity_native.py`
passed (`be346d29a38d4ed0a770d7b0283be765`). The test authored and replayed a private successor
from N29, verified scalar-to-array conversion and malformed-array refusal, and admitted a real
release with one undetermined operation. Two settlements waited behind the same native
revocation and both completed under the five-second lock timeout. Their receipts include the
revoked scope's new epoch and exclude the other project's epoch. Replay reused the publication.
A zero epoch left older validity intact and a same-project revocation of a different source
invalidated it. The read principal authenticated the archive and reported the conservative ID.
The earlier attempts remain held. `72c64f7635c94e65942400ee9f4244ce` caught a missing local in
the definition guard, corrected to use the lowered input role. `1f1bfaa3465c4ff6b1cfa7d5a7d934ac`
replayed the migration and stopped at a release/kernel digest mismatch during concurrent source
edits. The passing retry checked matching captured, installed and prepared digests.

The integrated native rerun passed both the N29 successor and the fresh installation route
(`60fdd94b2f52482a9621eb9ba2427425`). It verified unchanged owner and privilege policy on
shared object identities, classifier removal, conservative validator installation, and detached
demand export with the declared validity facts. The prior fresh-install result
`e3db388b4bd24763ab99ea103e434ac0` found those facts missing from detached rows. The output
now includes them so the detached verifier can compare them with the captured release.

The follow-up moved grade and fit census protection onto lowered families and the declared
policy command class. Separate family live checks all run for a multiply classified operation.
Privileged-effect ownership keeps its existing pins where a copied declaration could otherwise
claim authority. Revision A also incorporates DA-040. The captured value-codec policy limits
canonical fixed-point decimals to 16,384 digits. Python and generated PostgreSQL check the
canonical width before allocating the expansion or overflowing a PostgreSQL integer cast.

**Tested, 2026-11-18.** The follow-up N29 successor, Python decimal vectors and fresh-install
ACL/export selection passed all 20 controls (`05f630cfe3f24fb3b2801ef8dcf693c4`). The successor
also passed on the shared PostgreSQL test host (`e9f93946ff32479f9863dd03d72f60d0`). Both earlier
cohorts that held changed source during release preparation remain recorded
(`f6f6d5c81b6b4bbdb9e73c10e96a5b99`, `0810024170434c7db1c50978e62c8815`).

The stable declaration and acquisition selection passed 63 controls (`0fca0e69b426459993f8401917f7b715`).
The managed A candidate (`0a24d6bc40db4aebb231ebde36bbb231`) replayed and was registered
(`a9cb64e84a404513a6e67574727ef732`). Deployment `4bae9b8ceaf24df58c89074b0fb772eb`
advanced the owned stage to N30 and archived the release. Definition admission refused
`DdoFormalProduct` because five member identities changed under its existing container identity.
The release identity projection now includes the native nominal member dependencies. The frozen
N30 programs and historical kind rows retain their custody.
The stage settlement observation passed against the installed N30 kernel (`43df462d22804d6d83d9020c7b6ed460`).
It used a bounded synthetic project on the owned stage, observed both completion lock waits
during revocation, and checked the resulting publication receipts and retained inspection.
The corrected application-only deployment passed archive, admission, and verification on N30
(`d807cfc761104106b3af8fae3aaea7a9`). It retained the exact N30 generator bytes and prepared a new
application release with corrected nominal kind identities. The 21 nominal member controls passed
(`b639e17532e24b25b1d5b9d143373595`). Independent `ci db check` and `ci release check` passed for
`release:10bbf4c1a4573778e4dd30f5f2e6022b5ef05213b493759ed676cb520c1b2299`.
`ci release activate --expected-generation 26` selected it for `ddo-current-pdf-bounded` at
generation 27. Canonical development and book activation remain in UDM-21.

```bash
uv run ci test --native-host private --workers 2 -- \
  python/corpus-structure/tests/semantic/test_udm_validity_native.py \
  python/corpus-structure/tests/semantic/test_target_installation_native.py::test_actual_fresh_target_authoring_render_replay_install_and_acl
```

## Revision B execution

The LinkML support-edge vocabulary now generates the validity, lock-scope, public-read and
historical-lineage profiles. Its reference vocabulary supplies the PostgreSQL and Python
reference classifiers. Unknown shapes refuse at the consuming boundary. Population
support follows the admitted use and parent population. Historical source lineage
continues through the producer's own evidence. Change impact reads the compiled
operation dependencies and the native validity explanation. Its explanation names the
root use, the reached endpoint and the applicable revocation selector.

Discovery closure uses the exact fulfilled use in the current demand. It checks the
current discovery producer recipe and output role, project and source scope, and retained
population coverage. Reuse preserves the original derivation and release. The private
cross-release scenario established population closure without a second discovery
invocation and refused a wrong output role and revoked support. The original mixed
receipt `0b463502ff67452ca8fbeccaeea5d55b` recorded that native pass along with a stale
assertion about traversal profiles. The corrected profile control passed
(`9288d554ea6c489e88ca0177bed56fa1`).

**Tested, 2026-11-18.** N30-to-N31 rollback-only candidate
`bfe5d6de22934a00a66b735ce1885164` contained 32 native changes and zero privilege
changes. Registration `f1afa641d82d45ae89604e98b914d635` froze it. Stage deployment
`35700b09ca64459bbcf18382a53c6eaa` reached N31, admitted and verified
`release:9ac526c87da3e67038033fefec18b7bf1d915d9fbc6a1c866171b868eb24ff74`
on PostgreSQL OID `130661481`. Independent `ci db check` and `ci release check` passed.
`ci release activate --expected-generation 27` selected it for `ddo-current-pdf-bounded`
at generation 28. The owned-stage observation (`949abc3179834a57aea9598b7da470b9`)
verified exact N31 source custody, reused a prior-release discovery without invoking it,
and refused wrong role, foreign source, wrong page and revoked support. Detached exports
keep their selected cut and provenance. Validity explanations are available in live
change-impact inspection.

## State

| Package | State |
|---|---|
| UDM-05 | Claims, lowering, guard dispatch and release closure integrated. Remaining authority, capture and full native parity are open |
| UDM-06 | Conservative publication and inspection passed on the private successor and the owned N30 stage. Matching application activated at stage generation 27 |
| UDM-07 | One support vocabulary and cross-release discovery reuse integrated. N31 deployed and activated at stage generation 28. Bounded live acceptance passed. The complete matrix remains open |

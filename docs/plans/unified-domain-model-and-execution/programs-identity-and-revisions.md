# Programs, identity and revisions: the program registry, the identity layers, revisions by program bytes and carried assurance

**Status:** In progress. The typed registry and transition programs are integrated. The
[UDM-10 code-closure follow-up](#udm-10-code-closure) is scheduled for the generator and selected
readers, with real reuse qualification still open.
**Created:** 2026-11-19. Writing this plan authorizes no implementation.

This companion owns the designs of **UDM-08** (the execution path generates nothing), **UDM-09**
(a typed program registry carried from generation to installation), **UDM-10** (the identity
layers and the one identity transition revision), **UDM-11** (a native revision is authored only
when installed program bytes differ) and **UDM-12** (carried assurance, and the readiness
watermark without its kernel component). UDM-12, and UDM-11 for its installed part, change
installed objects and join UDM-10's transition revision. It contributes to review recommendations R04, R05, R06,
R10 (watermark part) and R11, to review finding F01, to rule impacts RC06, RC07, RC08, RC10, RC11
and RC15, which the operator accepted on 2026-11-19, and to audit findings
[DA-033](../../design_review/audit/execution-fit.md#da-033), [DA-068](../../design_review/audit/execution-fit.md#da-068),
[DA-069](../../design_review/audit/execution-fit.md#da-069), [DA-076](../../design_review/audit/served-claims.md#da-076),
[DA-078](../../design_review/audit/execution-fit.md#da-078), [DA-081](../../design_review/audit/semantic-model-and-authority.md#da-081),
[DA-082](../../design_review/audit/execution-fit.md#da-082) and [DA-083](../../design_review/audit/execution-fit.md#da-083).
Package state, the queue, finding dispositions, the shared contracts named below and the decision
records for the rule impacts are the [coordinator's](../unified-domain-model-and-execution_2026-11-19.md).

**Baseline and evidence.** Section references such as R05 or §3.3 mean the
[design review of 2026-11-18](../../design_review/reviews/design_review_unified-domain-model-and-execution_2026-11-18.md),
which read production source at `5139eaba3`. This plan was authored against commit `cb4e09667`
(the authoring baseline), whose production source is identical. Source facts are
**Interface-checked by source inspection, 2026-11-19** at `cb4e09667`; they come from the
[identity investigation](../../design_review/evidence/2026-11-19_udm-plan-authoring/identity.md),
and the lines cited here were re-read for this draft. Nothing was run. Every design statement is
**Proposed**. No speedup is claimed; where this document names repeated work that disappears, it
names the work and leaves its size unmeasured. Paths omit `python/corpus-structure/src/corpus_structure/`
unless they begin with `docs/`, `tests/` or `target_alembic/`; the latter two are relative to
`python/corpus-structure/`.

The shared contracts **program declaration**, **program identity** and the other identity layers,
**compiled model**, **lowered operation attribute**, **conservative validity**, **cache tier** and
**the flexibility frame** are defined once in the coordinator's
[shared contracts](../unified-domain-model-and-execution_2026-11-19.md#shared-contracts) and
[frame](../unified-domain-model-and-execution_2026-11-19.md#frame). This document uses those names
and describes how its packages realize them.

Terms of the system used below (the kernel, a native revision, a release, a seal, the completion
battery, a read cut, the stage) are in the coordinator's
[glossary](../unified-domain-model-and-execution_2026-11-19.md#glossary). One term
is local: a **completion receipt** records a published result.

## Why this work exists

The system installs a set of PostgreSQL programs (functions, triggers, views and grants; the
"kernel") that are generated from the model and from typed Python program objects. Three things
about that set are held by hand or held too coarsely today.

1. **The set is a group of hand lists that must agree.** What is generated, captured, concatenated,
   installed in which order and executable by whom are separate lists, and facts the program
   objects knew at generation are recovered afterwards by parsing rendered text (DA-081).
2. **One digest stands for everything.** Any edit to a captured Python file moves the one digest
   that keys seven consumers, including edits that change no installed byte. Execution then
   refuses until a new native revision is deployed, every release is prepared again, every
   completion receipt replays its battery and every waiting obligation is bound again (DA-068,
   DA-069, DA-082). Revision N29 changed no generated statement and restamped digest literals in
   nine objects (R05).
3. **The execution path regenerates the whole program set to compare one value it already holds**
   (F01, DA-083), and the generated release guard proves the same immutable release content again
   on every acquisition (DA-033).

**What this companion consumes.** The accepted rule impacts named above. The held compiled model
of UDM-01, which registrants read where it has landed; it is a convenience and not a prerequisite.
The lowered validity families of UDM-05 and the conservative validator of UDM-06, under the
contract stated in [What UDM-10 consumes from UDM-05](#what-udm-10-consumes-from-udm-05). The
existing typed program forms of [ADR-0131](../../adr/0131-model-owned-postgresql-programs.md), the
frozen revision format of the native chain, file custody and query custody
([ADR-0124](../../adr/0124-serving-code-custody.md)), and the closed-source slicer of
[ADR-0092](../../adr/0092-ddo-operation-authority.md), all of which are kept.

**What it produces.** A release-bound execution check that generates nothing; one declared list of
program registrants from which order, grants, capture, facades and the descriptor are derived;
identities layered by what each one keys; a candidate command that reports `no_native_change`
when no installed byte would differ; a per-acquisition guard that relies on recorded receipts;
and a watermark that no longer moves with the kernel.

**Where its responsibility ends.** The validity family vocabulary, its lowering and the
conservative validator are the
[lowered operation facts companion's](lowered-operation-facts-and-validity.md). Roles, purposes
and the generation of grants *policy* from the purpose vocabulary are UDM-03's
([model authorities and openness](model-authorities-and-openness.md)); this companion supplies the
purposes each program declares, which is why UDM-03's grants from program declarations need
UDM-09. The holders that keep a generated program set in memory and on disk, and the
served-result key, are the [cache system's](cache-system.md). Archived pack slices (R17) and the
scientific policy recipe (R14), which the identity investigation also designed, are UDM-18's
([analytical placement, SQL and retirement](analytical-placement-sql-and-retirement.md)).

## Corrections to the review

The identity investigation corrects the review in three places. In each, the investigation's
verified fact governs. It also found that `acquire_publication_port` has no caller in `src/`,
`tests/` or `scripts/` (`semantic/data_operation_admission.py:375`); UDM-19 retires it.

1. **The generated guard's comparison of the release with the installed kernel is conditional.**
   R06 and F01 say the guard "already requires the release's archived native digest to equal the
   installed descriptor". It does so only inside the native constraint checks
   (`semantic/native_admission_release.py:531`), and the refusal fires only when some applicability
   row carries a pattern constraint or a scope outside `shape` and `accepted_value` (`:585–626`). A
   release with no such row passes under any installed kernel. The only other comparison runs at a
   release's first definition admission (`semantic/data_operation_compiler_native.py:999–1006`),
   and the Python check compares the checkout, never the release, with the installed descriptor
   (`semantic/data_operation_storage.py:1135–1142`). Deleting the rebuilds is therefore not enough:
   UDM-08 adds an explicit comparison against the value the release records.
2. **A module-level import closure is nearly the whole package.** From four different entry modules
   the closure of every import statement, including those inside functions, is 447 of 767 package
   modules. The review's "module closure fallback" is about as coarse as today's capture, so the
   narrowing by the existing slicer carries the benefit where reuse is costly.
3. **`public_disclosure` is pinned by the cut.** It is a required column of the read row
   (`model/semantic/data-operation-physical.yaml:620–632`), and the cut carries `read_id` among its
   required pins (`semantic/demand_results.py:72–84`). The review asked for the native owner's
   review of the cut's pins; this plan records the question as settled by reading, for cut-keyed
   continuation, which the cache companion uses. A field of the read row that a read-page program
   consults and that the cut does not pin would reopen it.

## Baseline at `cb4e09667`

### The hand lists and the text operations

| Hand list or text operation | Site | Size |
|---|---|---|
| Capture list | `native_protocol_sources`, `semantic/data_operation_storage.py:48–574` | 97 artifact constructions, 93 distinct literal `native/…` names, a 7-entry program tuple yielding a `.sql` and a `.py` each, 7 splatted helper families |
| Required set | `_captured`, `:577–701` | 106 names; refuses a missing or duplicated name and accepts extras |
| Concatenation list | `native_sql`, `:761–822` | 37 named artifacts and 2 appended; 6 of them are not in the required set, so a missing one is a `KeyError` |
| Digest splice | `:815–819` | two markers replaced by `str.replace`; the markers live in 5 generator modules |
| Entry-point rename | `_rename_native_entrypoints`, `:725–758` | parses the whole kernel, renames, reprints, reparses and splices by span |
| Wire wrappers | `_wire_wrapper_sql`, `:825–876` | text appended after the rename |
| Per-function re-parse | `data_operation_native_definitions`, `:1897–1935`; three selectors in `semantic/native_authoring.py:177–268` | each parses a concatenated script again to find named functions |
| Grants by name | `:1906–1932` | a 5-entry map from purpose to role and 5 named special cases |
| Installation table | `semantic/target_installation.py:227–249` (11 rows), runtime bindings `:281–295` (3), provider order `:317–329` (7) | |
| Authoring capture | `semantic/native_products.py:133–165` (28 module names) and 12 artifacts `:166–200`; `extra_sources`, `semantic/target_installation.py:87–122` (12) | |
| Inventory re-parse | `semantic/native_inventory.py:83–158` | recomputes owner and EXECUTE from parsed text |
| Catalog-check recovery | `semantic/native_admission.py:42–82` | comment substrings, with literal fragments as fallback anchors |
| Facade outputs | `schema/model_change.py:53–61` (7 paths) zipped strictly with 7 calls at `:540–548` | |

### What the one digest keys

`native_source_digest` (`semantic/data_operation_storage.py:712–722`) hashes every captured
`native/*` artifact: generated SQL, module bytes, the physical and LinkML closure, and library
versions. It keys seven consumers: the installed descriptor literal and a release's first
definition admission (`semantic/data_operation_compiler_native.py:999–1006`); the release row's
`native_kernel_digest`; read acquisition (`semantic/data_read_boundary_native.py:98`, column
`model/semantic/data-operation-physical.yaml:632`); the completion seal
(`semantic/data_completion_settlement_native.py:490`); the receipt replay gate (`:671`); each
native operation's `behavior` (`semantic/data_operation_storage.py:993`) and call binding; and the
readiness watermark (`semantic/data_operation_projections.py:2189`). Three further identities are
hand lists: PDF lowering names 70 files and 14 libraries (`semantic/pdf_lowering.py:15–104`);
served reads use an owner-declared allowlist (`_query_custody.py:1–4, 17–127`;
`semantic/demand_queries.py:117–124`); opaque construction and formal boundaries hash whole files
and library versions (`semantic/formal_products.py:686–774`). The release id is the digest of a
manifest whose dependencies list every artifact, the whole native capture and the generator files
included (`semantic/prepare.py:956–986`). The deployed execution-contract descriptor also carries
authoring provenance (`semantic/native_products.py:389`).

### The execution path

`require_data_operation_native` (`semantic/data_operation_storage.py:1127–1142`) calls
`native_source_digest()` twice with no argument, and each call rebuilds the whole capture. Its
callers are `acquire_python_execution` (`semantic/data_operation_admission.py:285`, reached from
`acquire_prepared_execution` at `:230` and from `orchestrate/native_demand_io.py:99`),
`recheck_cached_execution` (`:354`, reached from `orchestrate/native_demand_io.py:114`),
`acquire_publication_port` (`:390`, no caller) and `admit_data_operation_definitions`
(`semantic/data_operation_storage.py:1561`, with a third rebuild in its return at `:1571`; reached
from release admission at `semantic/data_operation_admission.py:131`). The demand export rebuilds
the capture to read one protocol schema (`serve/demand_export.py:281`). About 20 test lines refer
to the two functions.

### Per-acquisition proof, and the watermark

On each acquisition Python stats every revision file, queries catalog fingerprints and admits the
descriptor and guard (`semantic/execution_admission.py:120–178`). The generated guard
(`semantic/native_admission_release.py:343–409`) hashes the manifest and prepared bytes again, runs
the whole catalog battery, decodes and walks the release's projections, and inserts the deployment
admission receipt if it is absent (`:59–97`); the receipt's presence short-circuits nothing.
Binding and population selection decode and hash `data_operations.json` on every call
(`semantic/binding_admission_native.py:231–251`; `semantic/population_acquisition_native.py:906–921`).

The watermark (`semantic/data_operation_projections.py:2062–2192`) is consumed only as a skip
predicate: a waiting obligation is not bound again while its watermark is unchanged
(`semantic/data_operation_demands.py:731–737`). Binding stays the authority. A watermark that is
too coarse costs repeated binding; one that is too narrow could leave an obligation waiting; neither
can admit a wrong result.

## Target design

### The program declaration, and what is derived from it

A **program declaration** is one immutable value per installed object. It carries the object's
identity (the existing `NativeIdentity`); its body as typed statement objects, rendered once to
the install statements that frozen revisions already store per object; the callees collected from
the typed body; the purposes for which it may be executed, and its owner; the validity families
it serves as validator, as completion guard or as live-completion program; an optional wire entry, from which both the public
wrapper and the implementation name are generated; the model inputs it reads (tables and columns
found by walking the typed body); and its sub-programs, so that the guard's catalog-check block is
a declared part and nothing searches comments for it. A body may be bytes only for residue that
has no typed form, and such a program declares its callees by hand.

**The program declaration is the one home of "which program validates a family".** Programs are
code artifacts whose authority is the typed registry, so the member of the `ValidityFamily`
vocabulary (UDM-05) does not name a program. Generation checks that every family that is not
provisional has exactly one validator program, and it refuses a missing, duplicated or dangling
claim. UDM-05 lands before the registry and holds the same fact as one typed table in the
compiler; UDM-09 absorbs that table and deletes it, so the fact never has two homes.

**Purposes are an integrity declaration and fail closed.** A program that no purpose may execute,
such as a trigger function or an internal callee, carries an explicit internal marking, which
grants nothing. A program with neither declared purposes nor that marking refuses at generation,
so that an empty set is always an omission. The owner of each generator module supplies its programs' purposes in the
registrant, including those of the programs the grants code special-cases by name today
(`semantic/data_operation_storage.py:1906–1932`): `admit_data_operation_definitions` (admit),
`ddo_require_feature_fit_principal` (fit), `data_operation_native_descriptor` (read, write, admit
and evaluate), and `data.ddo_field` and `data_binding_rows` (read, write and evaluate).

Each generator module exposes one registrant, a function that takes the compiled model and returns
its declarations. The registry module holds one tuple of registrants. That tuple is the single
declared list; everything else is derived from the declarations it yields.

| Derived product | Derived from | Replaces |
|---|---|---|
| Installation order, and the provider order for SQL-language bodies | A topological sort over callees | The installation table and the provider list |
| Install definitions | Each declaration's rendered statements | Re-parsing a concatenated script by function name |
| Grants | Declared purposes, through the purpose vocabulary of UDM-03 | The purpose-to-role map and the named special cases |
| The release's program manifest (object identity to program identity) | The declarations | Module bytes and concatenated SQL in the capture; the required-set check |
| Wire wrapper and implementation names | The wire entry | The rename pass and the appended wrappers |
| Python facades | Registered outputs | `_NATIVE_OUTPUTS` and its strict zip |
| The descriptor program | The identities, generated last | The two marker splices |
| The inventory (owner and EXECUTE) | Declarations | The inventory re-parse |

Completeness holds by construction, because there is no second list to disagree with. Reading
rendered text remains legitimate only for authenticated frozen bytes: the catalog-check boundary
is recorded in a revision when it is frozen, and the fallback anchors serve only the revisions
already frozen without that record.

**Whether a change alters installed bytes can be answered today.** Any package generates its
objects and privileges and compares them, statement by statement, with the head frozen revision.
UDM-09's acceptance performs that comparison through the registry; before UDM-09 lands, the
generated script is compared with the frozen statements. No package waits for UDM-11 to learn
whether it contributes to a revision.

### The identity layers, and what each keys

| Identity | Definition | What it keys | On a difference |
|---|---|---|---|
| Program | The digest of the canonical list of one object's rendered install statements | Revision deltas; every identity below | — |
| Kernel | The digest over the sorted pairs of object identity and program identity of the installed set, excluding the descriptor program | The descriptor comparison at acquisition; the release record; definition admission; the release guard | That release is refused with a re-prepare instruction; reads are acquired again |
| Validator, per validity family | The digest over the sorted names and program identities of the family's validator program, that program's transitive callees and the family's completion guard; the conservative validator has its own | The completion seal and receipts, as a map from family to identity | The battery runs and a reconfirmation is recorded |
| Read closure | The closure identity of the read-acquisition and read-page programs | The read row's kernel field and the read-currency check | The read is acquired again |
| Operation behavior | The closure identity of a native operation's own programs | The operation's `behavior`, so its recipe moves only with its programs | A recipe change, as today |
| Code (Python) | A derived closure, described below | PDF lowering, served reads, opaque boundaries, the generation cache | Reuse is withheld; service is never refused |
| Release id | A manifest over the model capture, the generated artifacts and the program manifest with the kernel identity | The release | A new release |

The kernel identity excludes the descriptor program because the descriptor returns the kernel
identity; including it would require a fixed point. A program identity is computed from rendered
statements, which generation produces without a server and which every frozen revision already
records per object. The server-normalized catalog form stays the admission authority for drift, as
today. A change to any program inside a family's validator identity replays that family's seals
and no other's; [What UDM-10 consumes from UDM-05](#what-udm-10-consumes-from-udm-05) states
which programs are inside.

**The descriptor program** returns the kernel identity, the map of program identities, the
validator identity of each family, the read-closure identity and the physical model identity.
Guards and seals call it, or a small accessor over it, instead of embedding digest literals. An
identity change then rewrites the descriptor and the programs whose bytes actually changed, where
today it rewrites every body that embeds the digest.

**Seals and reconfirmation (RC06).** The receipt's `validating_kernel_digest` and the seal's
kernel field become a map from validity family to validator identity, with one entry for each of
the operation's families and the conservative validator's entry for an operation whose family is
undetermined. The skip predicate enumerates the **currently applicable** families from the
lowered consumer contract, including conservative validity where applicable. Each requires a
matching recorded identity or a reconfirmation for that receipt, family and current identity.
A missing entry, including a newly applicable family, runs its check. Historical entries remain
attributed evidence. Current trust, source and purpose still have their own checks. The battery
runs today inside stable functions
(`semantic/data_completion_settlement_native.py:695`), which cannot write, so reconfirmation is
recorded by a routine that can: the next publish or settlement that runs the gate for that
request, or an explicit `ci` command that reconfirms a release's receipts after a deployment. The
record is append-only and idempotent.

### Code identity

**Producing determinants (I01).** UDM-09's program and reference declarations and UDM-10's
source closure distinguish production from acquisition, settlement and serving. Start from the
callable or installed program that produces the outcome, and include the exact effective input
meaning, selection and parameters, output contract, material assets, scientific policy, and
output-affecting code, runtime, numerical and batch settings. Keep required subject and replicate
context in the existing request identity. Admission and validator selectors govern current use;
full releases, runtime attestations, producer attempts, and generator evidence remain attributable.
An orchestration, settlement, authoring or downstream edit which cannot change the result does
not move its producing identity. Trace the current fixed PDF lowering list from
`semantic/pdf_lowering.py:31` into the actual operations before dropping any dependency.
A broader closure can authorize reuse only when its supported execution and material-input
contract is complete. The module discovery scan alone cannot establish that premise. An unknown required determinant
withholds reuse with a diagnostic. [Recovery](operation-reuse-and-recovery.md#udm-25) consumes this
basis for checkpoints and drafts. [CLI](operational-cli.md#udm-26) projects the resulting decisions.

**Serving identity (I04).** Keep authenticated imported-code custody and current read authority.
Separate the code and declared query/order semantics that determine a continuation from the
cache wrapper and its retention or file codec. The storage-only cachetools version belongs in
cache entry compatibility. Identify when an older opaque cursor cannot be interpreted under the
new basis and report its explicit transition refusal. A later storage-only version move must
leave a current semantic continuation usable, even if its cached page needs deriving again.

Python code that determines a result outside an installed program receives a workload-specific
identity from one authenticated source capture. The capture supports separate projections for
import initialization, reached callable behavior, explicit dynamic capabilities and copied
artifact provenance. A normalized syntax digest names the captured meaning. The executing code
must also correspond to the admitted bytes through the shared import-custody mechanism.

**Implemented baseline · 2026-11-19.** The static module scanner follows import statements,
including function-local imports and package parents, records recognized dynamic forms, and maps
external imports through distribution metadata. Its optional closed-source slicing refuses
uninterpreted initialization. The [closure probe](../../design_review/evidence/2026-11-19_udm-code-dependency-closure/README.md)
reproduced 33 identical diagnostic sites for four roots and showed both an uncalled import being
included and an indirect import whose determining helper was missed despite a reported complete
identity. These observations supersede the earlier premise that the module walk is generally
sound. A module count or the absence of recognized dynamic syntax cannot establish completeness.

**Target · Proposed.** The [code-closure follow-up](#udm-10-code-closure) derives reusable identity
relative to an explicit supported workload. A required unresolved binding, initializer, dispatch
or external input withholds reuse. A coarser captured execution boundary is viable when its
material inputs and effects are bounded and verified. Discovery results remain attributable
evidence and can explain a blocker. Runtime observations can reveal edges for investigation.
The owner's supported execution contract establishes whether the required edges are complete.

Query custody's finder and loader compile the admitted bytes and verify loaded module identity.
The bootstrap itself receives explicit custody. Shared metadata checks continue to detect supported
file and module drift, which requires restart under [ADR-0137](../../adr/0137-serving-code-and-model-custody.md).
Preparation retains its immutable source capture and checks the relevant runtime premises when
that capture is used.

An incomplete determining identity permits fresh computation under the existing authorization
contract. Serving withholds cached rows and resumable cursors, PDF lowering withholds eligible
record reuse, and opaque operation recipes retain their unknown determinant. The diagnostic
names the required missing premise. The existing producing path retains its demand-scoped
execution and original-attempt recovery constraints while its closure is unresolved.

Parse and resolve a captured population once per source/runtime basis, using the existing shared
parser cache and lock. Repeated use checks the already established runtime premises through
custody and the relevant authenticator. Acquisition and cache lookup consume the resulting
identity and report rather than reparsing a checkout on every request.

### The release id and generator provenance (RC11)

A release's manifest keeps the model capture, the pack inputs and the generated artifacts (wire
contracts, call bindings, the ports manifest, and the program manifest with the kernel identity).
It drops the generator files and the module bytes of the native capture. Generator provenance,
meaning the generator code identity, the per-module digests, the distribution versions and the
model identity, is recorded as a **sidecar**: a field written into each frozen revision when it is
frozen, replacing the input list in the deployed execution-contract descriptor
(`semantic/native_products.py:389`), and a component of the generation cache key. It stays
auditable by inspecting a revision and it is no longer an input to any identity. The reader that
takes provenance back from the deployed descriptor (`semantic/native_admission.py:23–39`) reads the
sidecar instead.

### Revisions follow program bytes (RC15)

Before it connects to the authoring database, the candidate command computes two maps from object
identity to program identity: one from the registry, and one from the head frozen revision's
per-object statements. Frozen files are not migrated; their identities are computable from what
they already store. The native delta is the set of objects added, removed or changed in program
identity, together with differences in privilege policy. If the delta is empty and the request
names no physical change, data step, retirement or recreation, the command reports
**`no_native_change`** with the head revision, the object count and the kernel identity, and
writes no products. Today a request for native authoring falls back to an
`explicit_native_authoring` basis whenever nothing else applies (`schema/model_change.py:993–994`);
that fallback is replaced by the requirement of a differing program identity. An explicit
`recreate` remains the operator's override. The design does not change what a revision freezes;
it reduces how often one is authored.

The rule has an installed half. Today the run-time descriptor check refuses execution whenever the
checkout's digest differs from the installed descriptor, and that refusal is what forces a
revision for any digest change. Under RC15 the comparison made at acquisition is between the
kernel identity the release records and the kernel identity the descriptor returns, stated as an
explicit, unconditional predicate in the generated guard beside `release_preconditions`
(`semantic/native_admission_release.py:41–56`). That predicate is an installed object, so UDM-11
joins the identity transition revision for it. UDM-08 makes the same comparison in Python first.

### The execution path generates nothing

`require_data_operation_native` reads the kernel value the prepared release records and compares
it with the installed descriptor, with no generation. The recorded value is the `native_digest` of
the archived `data_operation_native_definitions.json` artifact (`semantic/prepare.py:1373–1393`),
which is the same value the generated guard reads (`semantic/native_admission_release.py:529–531`),
so the Python and the native comparison cannot disagree about what "the release's kernel" means.
The comparison is unconditional. Working-tree drift of generator modules is no longer an execution
concern: generators are off the execution path and authoring regenerates. Operation modules keep
their custody against the runtime manifest, served helpers keep query custody, and model files
follow RC09. The report that the checkout differs from the installed kernel, which the rebuild
gave only incidentally, belongs to the authoring commands (UDM-11).

### Carried assurance and the watermark

Today's guard body becomes a named full re-proof routine, used at activation, by an explicit
verification command and whenever no receipt exists. The per-acquisition guard checks four things:
the release is finalized; a deployment admission receipt exists for the release id, the physical
model identity, the descriptor digest and the kernel identity; the release's kernel equals the
descriptor's; and the caller-purpose checks pass. If any of the four identities differs, the full
proof runs and records the receipt, by the admitter or owner only, as today
(`semantic/native_admission_release.py:76–96`); any other caller is refused with the verification
command named. Binding and population selection read the admitted definition rows, which already
hold the binding expression and identities. The trade the operator accepted with RC08 is that a
superuser who alters archive or catalog bytes is detected at verification or activation and not on
every acquisition.

The watermark **drops its kernel component**. This is sound once UDM-08 has landed: a demand
belongs to one release, and that release runs only under the kernel it records, so the component
is constant for every runnable demand. If a later design lets a release survive unrelated kernel
changes, the component to put back is the identity of the binding closure (the binding,
population and discovery programs and their callees), not the kernel. Narrowing the watermark from
operation granularity to role granularity is a separate step, conditional on premise W1 as UDM-12
states.

### What UDM-10 consumes from UDM-05

The validator identity is defined per validity family, so the native slice of UDM-10 needs four
things that the [lowered operation facts companion](lowered-operation-facts-and-validity.md) owns
and that this document does not redefine. The two companions state this contract to match.

1. **The enumeration of families.** The members of the `ValidityFamily` vocabulary with their
   status, read from the compiled model, plus one reserved entry for the conservative validator.
   A provisional member has no validator identity; its operations are covered by the conservative
   entry.
2. **The programs of each family.** UDM-05's typed table in the compiler gives, for each family
   that is not provisional, its validator program and its completion guard; UDM-09 absorbs the
   table into the program declarations, which are then the one home. UDM-10 adds the validator's
   transitive callees from the registry and computes the identity. A family's validator identity covers every program that decides a validity outcome for
   the family: its validator program, that program's transitive callees and the family's
   completion guard. The shared
   live-completion program (`ddo_require_completion_live`,
   `semantic/data_completion_settlement_native.py:722–760`) serves every family: it belongs to
   the kernel identity, not to any one family's. The per-family requirement programs it calls,
   such as the record-grade cut requirement, decide an outcome for their family and are inside
   that family's identity. Today it reaches them by testing a literal operation id, which is
   one of the selection sites UDM-05 replaces.
3. **The lowered operation attribute** that gives, for each operation of a release, its set of
   validity families: possibly several, possibly the declared `none`, possibly undetermined.
   Native code reads it from the release when it builds a seal and when it gates a receipt. The
   identities a receipt carries for an operation are exactly its families, plus the conservative
   entry when the operation is undetermined.
4. **The conservative validator** of UDM-06 as a registered program, so that it has a validator
   identity of its own.

Until the transition revision, receipts and the conservative validator compare the whole kernel
digest, as today. The contract follows the coordinator's wording: facts about an individual
operation never enter generators and reach programs through the release; model-level vocabularies
and integrity memberships, among them which program validates a family, are generator inputs. A
family added later needs no change here.

## Choices, alternatives rejected and what would reopen them

- **Keep the whole-capture digest.** It is safe, and it makes every docstring edit and library
  patch invalidate admission, reads, receipts and watermarks. Rejected; N29 is the observed cost.
- **Hand lists with completeness tests,** which remain hand lists, and **scanning modules for
  generator functions,** which hides the list. Rejected; one tuple of registrants is declared.
- **A code identity recorded from the imports a process actually performed.** It misses modules
  another caller imported earlier. Rejected in favour of the static walk.
- **Function-level slices everywhere.** The slicer refuses dynamic forms, so slices are used where
  they resolve and the module closure stands elsewhere.
- **A mapping table from old release digests to new kernel identities,** so that existing releases
  keep running across the transition. No consumer needs old releases to keep running and the data
  is regenerable (premise P1, for the operator to confirm), so releases are prepared again once.
  Evidence of a release that cannot be prepared again would reopen this.
- **Keep the checkout comparison on the execution path behind a holder.** Every acquisition would
  still depend on generation and on the checkout. Rejected; a holder is right for authoring only.
- **Content-addressed storage of frozen objects by program identity,** so that revisions share
  unchanged bodies. A storage decision for the native owner, not planned here; the 46 frozen state
  files in the working tree total about 387 MB, which is the evidence that would motivate it.
- **Strip docstrings from the syntax digest.** A possible refinement, not planned.

## Library capabilities the design relies on

- **networkx `lexicographical_topological_sort`** gives a deterministic installation order over
  declared callees and refuses a cycle. It is already pinned and used (`semantic/graph_runtime.py`).
  The limit that matters is premise X1: SQL-language bodies bind their callees when they are
  created, so the callee set collected from typed bodies must be complete for them.
  [networkx reference](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.lexicographical_topological_sort.html).
- **SQLAlchemy `sqlalchemy.sql.visitors.iterate`** over a typed body finds `FunctionElement` nodes,
  whose package and name are the callees, and the tables and columns that form a program's model
  inputs. A callee named in a text fragment is invisible to it, which is why residue declares
  callees by hand. [SQLAlchemy visitors](https://docs.sqlalchemy.org/en/20/core/visitors.html).
- **pglast** AST nodes and its printer render each statement once; the typed forms are in use
  already (`semantic/native_objects.py:154–175`; `semantic/pdf_publication_native.py:470–495`). A
  pglast or SQLAlchemy release that changes rendering changes bytes and therefore program
  identities; one that does not changes nothing downstream.
- **`importlib.metadata.packages_distributions()` and `version()`** map imported top-level names to
  distributions. `importlib.util.find_spec` is deliberately not used for first-party names, because
  it executes parent packages.
  [importlib.metadata](https://docs.python.org/3.14/library/importlib.metadata.html).
- **The closed-source extractor** (`semantic/python_operation_sources.py`) records a
  `SourceUnknown` for an unresolved reference or a missing body (`:1152–1171`) and fails on
  unsupported dynamic call forms (`:2118`). The [code-closure follow-up](#udm-10-code-closure)
  extends its captured-source projections and defines the supported workload contract for C1.

## What this supersedes

UDM-00 writes the decision records for the accepted rule impacts; the passages below are the ones
those records and the design sections replace. The DDO plan is not edited by this series; UDM-24
records the superseded items for the operator's later reconciliation.

| Passage | What it says | What replaces it |
|---|---|---|
| `docs/plans/declared-data-operations/products-and-support.md:429–430` | Validity compares `native_kernel_digest` with the installed source digest | The explicit comparison of the release's kernel identity with the descriptor's, and per-family validator identity |
| The same file, `:452–453` | The per-kind check covers mutable premises, the kernel digest among them | Per-family validator identity |
| The same file, `:489, 492` | The read records the native kernel digest and refuses on a kernel difference | The read-closure identity |
| The same file, `:527–535` (PE-S21) | The completion intent records the installed kernel digest; a differing or absent digest runs the full battery | The intent records per-family validator identities; the battery records reconfirmation (RC06) |
| The same file, `:575–576` | `inputs_watermark` over prerequisite operations and exact pins | The kernel component is removed (RC07) |
| [ADR-0124](../../adr/0124-serving-code-custody.md), Decision `:32–38`, with `_query_custody.py:1–4` | Serving identity from source digests authenticated at import, over an owner-declared allowlist | The derived closure under the same custody; drift refusal stays (RC10). A superseding ADR |
| `docs/design/D2-schema-and-guidelines.md:403`, with `semantic/prepare.py:956–986` | Composed dependencies archive their bytes with the semantic release | Generator bytes become provenance (RC11) |
| Revision practice narrated for N14 to N29 in `docs/plans/declared-data-operations/postgresql-realization-and-retirement.md` | A revision is authored whenever the digest moves | Revisions follow program identities (RC15) |

ADR-0092 `:27` is supported and not superseded. ADR-0131 is extended by the registry and not
superseded.

## Sequence and the identity transition revision

The series plans three native revisions, authored and frozen close together in the order A
(UDM-05 and UDM-06), B (UDM-03 and UDM-07), then the identity transition, which is the only
revision this companion plans. Each changes the kernel identity and forces every release to be
prepared again; the stage follows each one, and canonical development and the book project are
adopted only at the current head and at the final head, as the
[coordinator's queue](../unified-domain-model-and-execution_2026-11-19.md#queue) states. After the
transition, a change that alters no installed byte produces no revision.

UDM-08, UDM-09 and the code identity slice of UDM-10 need no revision and can start at once. The
transition revision installs the native slice of UDM-10, the guard predicate of UDM-11 and the
guard, re-proof routine and watermark of UDM-12, each as its package describes, and UDM-09's
objects only if premise B1 fails. The catalog-check boundary is recorded in frozen revisions from
this one on.

**What happens to existing state.** Releases record an old-style digest and are prepared again
once; there is no mapping table. Receipts and seals have no validator map, so the battery runs on
first use and records the reconfirmation; there is no backfill. Reads are acquired again, each
waiting obligation is bound again once, and frozen revisions keep their bytes.

## Packages

### UDM-08 — The execution path generates nothing

UDM-08 was moved ahead of captured generator edits in the UDM-00–03 increment. The older
renderer embeds a digest of the generator capture, so changing the checkout can change rendered
bytes even when the installed behavior is equivalent. Execution uses the exact archived and
installed identities. Authoring preserves the real source digest and routes resulting native
deltas through the existing revision order.

**Implementation vision.** `require_data_operation_native` receives the connection and the
prepared release, as today. After the existing call to `require_native_execution` it makes the
comparison described under [The execution path generates nothing](#the-execution-path-generates-nothing)
and returns the recorded value. It owns one decision, whether this release may execute under this
installed kernel, and one refusal, which says that the release was prepared for a different kernel
and names re-preparation as the remedy. A prepared release that lacks the artifact or the field is
refused as internally inconsistent; it is not treated as matching.
`admit_data_operation_definitions` returns the same recorded value where it returns a rebuilt
digest today. The demand export takes its reader contract from the ambient wire contracts, which
the process already holds (`semantic/data_operation_wire.py:47–50, 525–529`); the cache companion
later moves that to the compiled model's protocol projection.

**Complete consumer scope.** The four callers named in the baseline (three with callers of their
own, and `acquire_publication_port`, which has none), the return at
`semantic/data_operation_storage.py:1571`, and `serve/demand_export.py:281`. About 20
test lines that refer to `require_data_operation_native` or `native_source_digest` on the
execution path are rewritten to the new contract.

**Removes.** The two rebuilds per acquisition and per recheck, and the three per definition
admission (`semantic/data_operation_storage.py:1139, 1142, 1571`); one rebuild per export.

**Prerequisites.** None. **Native revision.** None. The value it compares is already recorded in
every admitted release, the installed descriptor already returns the value it is compared with,
and the comparison is made in Python, so no installed object changes. The native form of the same
predicate arrives with the transition revision (UDM-11).

**What this keeps open.** Editing a generator, a model file or an operation while a server runs
no longer stops execution of an admitted release, so exploratory authoring beside a running system
is cheaper. It newly closes one thing: a release whose recorded kernel differs from the installed
one is always refused, where today the outcome depends on whether the release happens to have
pattern constraints. That is an integrity membership (which kernel a release was admitted
against), and re-preparation answers it.

**Acceptance evidence.** With an import blocker on the generator modules, or a counting spy on
generation, acquisition, cached recheck and definition admission all succeed and the count is
zero. A prepared release whose recorded kernel value has been altered in the test is refused, and
the case is repeated for a release with no pattern constraints, which the generated guard alone
would pass. The expectations are stated by the test (zero generations; refusal), not read from the
function under test.

### UDM-09 — The typed program registry

**Implementation vision.** Each generator module gains a registrant that returns program
declarations built from the typed objects it already constructs. The registry module collects
them, checks that object identities are unique and that every callee in a registry schema is
declared, sorts them, and offers the derived products of the table above. Generation renders each
declaration once. Installation turns each declaration into a native definition directly; the
existing per-statement parse for server normalization stays. The release capture holds the
program manifest and the generated client artifacts. Facades register as generated outputs of the
self-checking kind (`schema/generate.py:540–578`). Grants are emitted from declared purposes; the
vocabulary of purposes and the role each maps to are UDM-03's, and until UDM-03 lands the registry
reads the existing five-entry map as data, so no second policy is written. The registry absorbs
UDM-05's typed table of family validators, completion guards and live-completion programs where
UDM-05 has landed; otherwise UDM-05
writes its claims directly on the declarations.

Failure behaviour: an undeclared callee, a duplicate identity, a cycle among callees and each
refusal stated under [the program declaration](#the-program-declaration-and-what-is-derived-from-it)
stop generation with the names involved. Nothing is installed from a registry that fails.

**Complete consumer scope.** Every row of the hand-list table in the baseline, with the counts
given there. The authoring callers of the capture move to the registry's products:
`semantic/data_operation_preparation.py:261`, `semantic/primary_operations.py:403`,
`semantic/regeneration.py:331`, `semantic/native_products.py:110`,
`semantic/data_operation_storage.py:1857, 1865` and the model-change preview
(`schema/model_change.py:525–552, 603`). Native authoring fixtures in tests that assemble the
kernel by name list move to the registry, and the test helper `admit_kernel`
(`tests/semantic/data_operation_kernel_support.py:318`), which restates the persist, admit and
bind order by hand, takes the derived order; the test series recorded that item as owned by
production. The digest splice itself is removed by UDM-10, when the descriptor program exists;
until then the registry renders the same marker replacement as one declared step, so the bytes
stay equal.

**Removes.** The lists and text operations named above, except reads of authenticated frozen
bytes. Comment-boundary recovery remains only for revisions frozen before the boundary is
recorded.

**Prerequisites.** None. Where UDM-01 has landed, registrants read its held compiled model;
before that they read the model as generators do today. **Native revision.** None, provided
premise B1 holds: the registry renders install statements byte-identical to the head frozen
revision's. If it does not, the differing objects are frozen in the identity transition revision
and UDM-09's installation cutover waits for it.

**What this keeps open.** Adding, removing or reshaping a program is one registrant's change, and
a program without a typed form may still be registered as bytes with declared callees. It newly
closes the set of callees within registry schemas, the uniqueness of object identities and the
presence of purposes or the internal marking on every program; all three are in the integrity layer (what is installed and
who may call it). A family marked provisional needs no validator, so declaring a new family stays
cheap.

**Acceptance evidence.** The registry's rendered statements equal the `statements` recorded in the
head frozen state file for every desired object (585 objects in
`target_alembic/versions/semantic_ddo_pe_n29_native.json` at the baseline); the expectation is the
frozen file, which the registry did not write. The privileges the registry derives from declared
purposes equal the same file's `privileges` list entry by entry (113 entries at the baseline);
grants are not inside the objects' statements, so this is a separate comparison. Installing the
registry's order into an empty authoring database succeeds, which settles premise X1. A fixture
registrant that calls an undeclared function is refused by name, as are a fixture program with neither
purposes nor the internal marking, a fixture family with two validators and one with none. Removing a registrant from the
tuple in a test removes its objects from the manifest, the order and the grants without any other
edit.

### UDM-10 — The identity layers and the transition revision

**Implementation vision.** The package has two slices with different prerequisites.

*The initial code identity slice* established derived source capture, conservative incomplete
identities and bounded slicing on N33. Its broader closure guarantee is revised by the
[code-closure follow-up](#udm-10-code-closure), which supplies the complete supported workload
identity needed by UDM-14 and UDM-15. PDF lowering and opaque boundaries consume the same shared
contract. A changed producing identity selects its normal re-preparation and reuse consequences.

*The native identity slice* begins with the program identity function, a digest over a
declaration's rendered statements, which needs UDM-09 only and installs nothing; the cache
companion's program store (UDM-14) needs this step and the code identity slice and nothing else
from this package. With UDM-05 as well, the slice then computes kernel, validator, read-closure and operation behavior
identities from the registry's declarations, generates the descriptor program last, rewrites the
embedding bodies to call it, changes the seal and receipt to the family map with the
reconfirmation relation, moves the release manifest to the program manifest with provenance as a
sidecar, and freezes the transition revision together with the installed-object changes of UDM-11
and UDM-12.

**Complete consumer scope.** The seven consumers of the one digest and the three hand-listed
identities, at the sites the baseline gives under
[What the one digest keys](#what-the-one-digest-keys), each moved to the identity the layer table
assigns it. In addition: the nine callers of `installed_read_implementation`
(`serve/rich_queries.py:109`), whose library list at `:71–100` is replaced by the distributions
the closure imports; the construction boundaries that hash whole files as the formal boundary
does, listed by a search at entry and complete then; the capture assembly
(`semantic/data_operation_preparation.py:261–266`); the generator file list
(`semantic/data_operation_artifacts.py:22–39`); and the reader of the descriptor's provenance
fields (`semantic/native_admission.py:23–39`). The release id's dependence on a filesystem
location, which the test series recorded as owned by production, is removed with the manifest
change: the manifest names artifacts by content and logical name.

**Removes.** `native_source_digest` as a key; the two markers; the hand lists named above; the
generator bytes in the release manifest.

**Prerequisites.** The code identity slice has none. For the native slice, UDM-09 supplies
declarations with rendered statements and callees, without which no program identity or closure
exists, and UDM-05 supplies the families, as stated in
[What UDM-10 consumes from UDM-05](#what-udm-10-consumes-from-udm-05). **Native revision.** The
native slice owns the identity transition revision, frozen after revisions A and B. A cause found by the book-run diagnosis (UDM-20) that lies in identity
or replay is repaired here and not in UDM-20.

**What this keeps open.** Editing helper code, comments, generator internals or a library version
no longer forces a revision, a re-preparation or a replay unless installed bytes change. An
operation whose family is undetermined is sealed under the conservative validator's identity and
runs normally. A served helper that uses a dynamic import still runs; only its reuse is withheld.
The package newly closes nothing in the declared behaviour space. The refusals it keeps are the
existing integrity ones: a release under a different kernel, and recording a receipt without
authority.

**Acceptance evidence.**

- The kernel identity computed from the registry equals the one computed from the head frozen
  state file by an independent few-line computation over that file.
- A docstring or helper edit in a captured authoring module, made in a temporary copy, that
  changes no rendered byte preserves the native program, kernel and family identities. Exact
  source bytes recorded in the replay artifact still change its provenance basis and D2 key.
  The existing receipt and release rules determine any other material consequences.
- A fixture generator variant adds one statement to one family's validator. Only that family's
  validator identity and the kernel identity change; only that family's receipts run the battery
  and record reconfirmation. The expected sets come from a hand-written fixture map from family to
  program.
- Add a family that was absent from the original receipt (and a provisional family that becomes
  ready). Its required check runs even when every recorded identity still matches. An authentic
  result is retained when the current check accepts it. A revoked or incompatible result is
  refused. Keep independent expected invocation and derivation counts for equal-content input,
  an orchestration-only change, a material producer or contract edit, a changed region with
  unaffected siblings, and an intentional replicate.
- In a temporary package tree, a module imported inside an entry function moves the code identity
  without any list edit. Replacing it with `importlib.import_module` on a variable marks the
  identity incomplete, and the result is served and neither cached nor resumable.
- The two known omissions of the 70-file PDF lowering list (review §12) appear in the derived
  identity.
- A fixture change to a program outside the read closure leaves the read-closure identity
  unchanged and existing reads current. A change to one native operation's program changes that
  operation's `behavior` and no other operation's.
- A change to one family's validator or completion guard leaves the conservative validator's
  identity unchanged, so the derivations of an undetermined operation stay valid; a change to a
  guard alone moves its family's validator identity.

<a id="udm-10-code-closure"></a>

#### UDM-10 code-closure follow-up

**Tested increment · 2026-11-19.** Tagged values have a lightweight semantic owner. Direct
consumers now import the value codec without loading operation identity. The semantic package
initializer no longer re-exports preparation machinery. Selected reads pass an immutable native
page, typed selection and validated model-derived Decimal limit to the projection. The pure
codec consumes that limit directly. Six selected-page consumers now use finite envelope policies.
Cursor encoding has its own small owner. Callable discovery includes explicitly declared owners
even when the entry module does not import them. The 292 codec and reader controls and 124
runtime correspondence controls passed (`6dc85d72a8864eb6b5013c37148d90fa`,
`fd7ea68602fc49fab8ad1e3f39eb3180`).

Native protocol authoring and the archived model version now have owners outside runtime
storage. The renderer probe reduced required eager premises from 426 to 115 on its measured
baseline. Offline comparison of all 620 N35 objects returned `no_native_change` on the
integrated source (`6a41d5552b674d5cb660f18770f7c3b7`). The proposed `SourceArtifact` move was
held after a separate comparison found two changed installed routines. Their exact helper
source digests include the affected import locations. This leaves one current source-artifact
owner and exposes a boundary for later provider-source closure work. After the separate
canonicalization repair, the offline N36 comparison also returned `no_native_change`
for all 620 objects (`af411378c9384cefb4ae180702ff436a`).

Strict D2 is still blocked by determining renderer contracts. Native demand serving has ten
remaining eager library premises on its measured probe. Rich and contribution preparation
still acquire broader model and runtime context. Exact stage capture invoked under two runtime
bindings used separate demand-scoped producer requests because its PDF lowering asset has
incomplete determining identity. These obligations remain in the
[qualification companion](qualification.md#code-closure-and-real-reuse-qualification).

**Partial implementation · 2026-11-19.** The bootstrap checks the executing package body and
the exact sibling loader bytes. Package startup no longer scans the reader module population.
Workload identity requires explicit callables, records eager initialization separately, and
uses captured LibCST package context for relative bindings. The admitted source check compares
the exact analyzed bytes with the executing or promised files. Module discovery supplies a
separate diagnostic inventory. The bounded controls cover the indirect import counterexample,
uninvoked local imports, and a determining initializer. The actual generator and selected-read
roots still lack required initialization and external-operation contracts. Their reuse remains
withheld. The supported initializer forms and captured library operations still need to be
extended against the real workload boundaries below.

**Boundary implementation · 2026-11-19.** The generator and served readers now declare
rendering or projection entry points independently of their lookup and acquisition wrappers.
The shared identity retains reached definitions. When a workload completes static closure,
the existing closed runtime verifier checks its live definitions and consumed bindings under
executing source custody. Reuse rechecks those premises. The bounded initializer model admits
literal construction and the supported standard dataclass profile. The installed generator and
selected readers still reach unadmitted initializers and external imports. The remaining work
is to close the relevant typed model, cache declaration and library contracts or move their
effects outside rendering and projection. Incomplete workloads continue to derive afresh.

**Scheduled target · Proposed · 2026-11-19.** Incorporate
[I01](../../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md#I01)
of the code dependency review, published at `1982a20c3` against production baseline `aa128c808`.
The native N33 transition evidence below retains its bounded scope. This follow-up supplies
workload identity to [UDM-14 and UDM-15](cache-system.md#udm-14--the-two-on-disk-tiers), and
attributed diagnostics to [UDM-26](operational-cli.md#udm-26). The coordinator owns execution
state and review disposition.

**Resulting behavior.** Capture one immutable source population with its module identities,
origins and exact bytes. Derive the necessary initialized modules and callable dependencies
for the selected entry. An import performs initialization, while a local import inside an
uncalled function requires a separate callable-reachability edge. Model eager decorators,
defaults, class bodies, bases/metaclasses, supported annotation evaluation, alias rebinding and
receiver dispatch. Include any relevant module state and external resources in the workload's
input contract. Each node, edge or unknown retains its source site, operation owner and evidence
kind. A finite explicit capability may close a dynamic operation when its executing code,
permitted inputs and runtime binding are verified.

The generator's capture includes code used in rendering and exact source bytes copied into
`ProgramSetArtifact`. A native-authoring module outside the render call path may still be a
material copied resource. UDM-14 owns its complete generator input acquisition and T2/D2 key.
Selected reads consume typed native authorization and cuts before lookup, with body acquisition
on a miss and deterministic derivation under the supported query/profile contract. UDM-14/15
own those reader boundaries and their cut/content semantics. Native authority and custody
checks remain active when the output can be reused.

**The 33-site route.** The
[review table](../../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md#disposition-of-the-33-findings)
retains each original site and its inspected semantics. Execution carries its evidence into the
existing identity/report rather than maintaining another findings register. For each generator,
native-demand, rich and contribution entry, explain any retained material path or demonstrate
why a site is outside the supported workload. Record newly exposed required unknowns as well.

| Saved sites | Owning closure work and evidence needed |
|---|---|
| 01–04, package bootstrap and `_query_custody` | Authenticate the fixed sibling loader, exact compiled/executed bytes, loaded module and bootstrap comparison. Exercise origin replacement, mismatching code and unsupported drift. |
| 05–06, contextual encoder and GLiNER | Account for version checks and the executed pinned correction wherever reached. Producer-only paths may exit a reader closure after its acquisition/derivation boundary is established. Runtime facts copied into the generator artifact still enter its key. |
| 07–13, operation consumers | Verify the admitted source population, executing consumer/factory code, imported owner/member and concrete type, including re-export bindings. Retain compile-for-comparison semantics in the verifier's own dependency contract. |
| 14–16, CPU capsule | Reuse finite captured membership, loaded module/callable provenance and exact source comparison in the CPU authenticator. |
| 17–30, operation ports | Verify captured construction/import bindings and compile comparisons. Close annotation evaluation over its exact expression and namespace, including any second evaluation of a string. Verify parent-child module bindings as one import capability. |
| 31 and 33, prepared and sentence products | Associate the source compiled for verification with the executing callable under authenticated byte custody. Prove producer verification is outside a direct retained-row derivation before pruning it. |
| 32, native candidate verification | Keep execution of a generated candidate in the authoring verifier. Establish its exclusion from generation and reading, while preserving its file bytes as generator provenance wherever captured. |

**Library responsibilities.** Installed versions below are the inspected `1982a20c3` pins.
The dependency policy governs later changes. A library result retains its evidence kind and
supported source/runtime scope in the application model.

| Mechanism | Selected use and decisive contract |
|---|---|
| Python 3.14 `ast.parse`, `ast.dump(..., include_attributes=False)` | Parse captured bytes and normalize syntax for semantic identity. Add explicit supported initialization/effect handling in the shared model. Syntax normalization alone supplies no binding or runtime completeness guarantee. [AST reference](../../libraries/python_introspection/ast.md) |
| LibCST 1.9.0 `ScopeProvider`, `QualifiedNameProvider`, `FullyQualifiedNameProvider` | Extend `ClosedPythonSources` metadata to scope-sensitive bindings and absolute relative-import targets. Build `MetadataWrapper(cst.parse_module(captured_bytes), cache={FullyQualifiedNameProvider: ModuleNameAndPackage(module_name, package_name)})` from admitted source and captured module context. `resolve_many` shares provider dependencies. Resolve lazy metadata through the provider/visitor API. The retained probe confirms relative aliases, and an installed-version check confirms captured provider-cache construction. [Metadata reference](../../libraries/python_introspection/libcst.md#52-built-in-metadata-providers), [1.9.0 provider](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/metadata/name_provider.py), [wrapper cache](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/metadata/wrapper.py) |
| Griffe 2.4.1 `griffe.visit`, `GriffeLoader.resolve_aliases(implicit=True, external=False, ...)` | Populate the existing module collection from captured source, retain `search_paths=[]` and `allow_inspection=False`, and resolve effective interfaces/re-exports within that collection. Keep unresolved/circular aliases attributable. Use the existing bounded resolution passes and captured stub distinctions. [Aliases](../../libraries/python_introspection/griffe.md#41-aliases-represent-references-not-copied-declarations), [source collection integration](../../../python/corpus-structure/src/corpus_structure/semantic/python_operation_sources.py) |
| Astroid 4.3.4 closed manager and `AssignName.assigned_stmts()` | Preserve bounded single-assignment alias refinement over captured modules. Receiver inference can be added only within a declared closed profile that yields a unique admitted target and checks runtime binding. Multiple targets, unsupported constructors, inference failure and `Uninferable` keep required uncertainty visible. [Inference and limits](../../libraries/python_introspection/Astroid.md#3-static-inference-astroids-defining-capability), [closed manager and builder](../../../python/corpus-structure/src/corpus_structure/semantic/python_operation_sources.py) |
| `OpaqueBoundary` and `AuthenticatedSlice` | Reuse the typed dynamic boundary and runtime premise authenticator for finite captured loads, verification and mutable callable bindings. The owner verifies loaded origins, resources and effective objects. The boundary's digest names the established contract. [Boundary model](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_model.py), [runtime authenticator](../../../python/corpus-structure/src/corpus_structure/semantic/runtime_slice.py) |

Ast-grep-py 0.51.2 `SgRoot(source, "python").root().find_all(...)` supports structural inventory
and candidate codemods. `ty` 0.0.102 `ty server` definition, implementation and reference LSP
queries support development investigation. Their results remain discovery evidence, with
Pyrefly retaining the repository type-checking role. If the existing typed dependency projection
needs traversal for operator explanations, NetworkX 3.7 `descendants`, `ancestors` and
`strongly_connected_components` provide reachability and cycle groups. The edge producers own
binding resolution and completeness. Use that projection when its facts suffice, and retain
partial/unknown standing when they do not. [ast-grep patterns](../../libraries/python_introspection/ast-grep-py.md#3-structural-pattern-matching),
[ty public interfaces](../../libraries/python_introspection/ty.md),
[NetworkX traversal](../../libraries/scientific_compute/networkx.md#3-traversal-paths-reachability-and-connectivity).

**Integration and retirement.** Extend the existing source collection and import-custody owners.
Migrate generator capture, every `installed_read_implementation` consumer, PDF lowering,
operation code assets, opaque construction and the UDM-25 checkpoint/draft compatibility reader
where the shared result changes. Preserve each operation's material parameters and original
producer attribution. Each workload's completion includes its actual consumer entry and useful
independent verification. Retire the authoritative module-wide alias heuristic, blanket
initializer refusal and syntax-list completeness decision for migrated supported workloads.
Retain useful broad discovery diagnostics under their weaker evidence contract. The cache
owner removes the obsolete T2 fallback and D2 duplicate sweep with the replacement capture,
and the CLI owner moves the first-site formatter to the shared typed explanation.

**Prerequisites and choices.** Establish bootstrap custody and typed workload input acquisition
before dependent reuse. The source collection can be improved alongside these contracts.
D2 and D4 can then integrate independently. A broader generator envelope is a conditional
alternative when its finite code, initialization, material files and ambient inputs can be
bounded and verified. A restricted worker is conditional on an acquisition boundary that the
in-process contract cannot enforce. Record the settling evidence and dependent work in the
owning package before selecting either. Preserve ADR-0137's semantics and route any necessary
rule change through the existing decision owner. The code follow-up requires no native revision
unless its implementation changes installed bytes under UDM-11's normal comparison.

**Acceptance.** Retain the indirect-import counterexample with independently expected results.
Add controls for shadowed aliases, relative imports/re-exports, type-only and runtime branches,
eager decorators/defaults/class initialization, supported receivers, ambiguous dispatch,
annotation namespaces, copied provenance and verified dynamic loads. Require an unmodeled
required determinant to remain incomplete. Verify changed determining code/resources change
identity and proven unrelated edits preserve reuse. Authenticate actual executing bytes and
exercise drift and origin replacement. UDM-14 owns two fresh authoring/reading process journeys
with actual identity discovery, and UDM-15 owns the private native entity witness journey.
[UDM-22](qualification.md#udm-22--the-managed-union-on-final-source) includes the affected final
source selection. A controlled complete identity exercises a cache consumer but cannot settle
this follow-up's actual entry-point closure.

### UDM-11 — A revision only when installed bytes differ

**Implementation vision.** The package implements both halves of
[Revisions follow program bytes](#revisions-follow-program-bytes-rc15). The authoring half is the
offline detection in the candidate command; the preview command reports the same delta, which is
where "the checkout differs from what is installed" becomes visible to the author. When the delta
is not empty, the revision's operations are exactly the objects in it. The installed half is the
run-time descriptor check: the explicit kernel predicate in the generated guard.

**Complete consumer scope.** The candidate route in `schema/model_change.py` (the basis fallback
at `:993–994` and the preview's facade and fingerprint paths), its CLI entry in `cli/schema.py`,
and the guard generator's preconditions (`semantic/native_admission_release.py:41–56`). The same
file gates a native request on the earlier model's change record (`schema/model_change.py:651–660`),
which UDM-04 changes when it retires that model; the coordinator fixes the order on this file, and
UDM-04's replacement of the preview lands first.

**Removes.** The `explicit_native_authoring` fallback as a reason to author a revision, and the
conditional form of the guard's kernel comparison.

**Prerequisites.** UDM-10 supplies program identities computable from both the registry and a
frozen file, and the kernel identity the predicate compares. **Native revision.** The identity
transition revision, for the guard predicate. The model-change commands are authoring code and
install nothing, so they change outside any revision.

**What this keeps open.** Authors may change generators freely and learn offline whether anything
installed would change. Nothing is newly closed; the operator's override remains.

**Acceptance evidence.** Against the head frozen revision with an unchanged registry, the command
reports `no_native_change`, writes no file and opens no connection (a connection factory that
fails the test if called). With one fixture program changed, the reported delta is exactly that
object, by comparison with the fixture's stated identity. A release with no pattern constraints
whose recorded kernel identity differs from the installed one is refused by the generated guard
itself, with the Python comparison of UDM-08 bypassed in the test.

### UDM-12 — Carried assurance and the watermark

**Implementation vision.** The package implements
[Carried assurance and the watermark](#carried-assurance-and-the-watermark): the generated guard
is split into the per-acquisition predicate set and the full re-proof routine, with the lapse rule
stated once. `ci release check --native-proof --release RELEASE_ID --target TARGET` reads the
archive and its projections without cache reuse, authenticates the current installed proof, and
establishes a missing receipt under admission authority. The ordinary release check still verifies
archived releases independently of the current kernel. The Python side of
acquisition (`semantic/execution_admission.py:120–178`) keeps authenticating the installed
descriptor and guard bodies against the frozen expectations.

N33 carried receipts but still decoded the release kernel in the fast guard and decoded and hashed
the archived operation model in binding and population acquisition. One successor moves the kernel
comparison to the admitted release header and stores the binding-type and parameter facts in the
protected release and operation rows. The generated data step derives only the new fields from each
retained release's digest-authenticated archive. Historical lowering, identities, and references
keep their original meaning. Full proof compares the new fields and the admitted binding against the
archive, and activation runs the same full proof.

Role-granular watermarking joins the identity transition revision only if its soundness
premise is settled before that revision is frozen; otherwise it is deferred, with the settling
of that premise as its trigger, and the series plans no further revision for it.
The premise is W1. While it is unsettled, the operation-granular prerequisite component stays
beside the role-matched one that already exists (`semantic/data_operation_projections.py:1781–1809, 1919–2059`).
In the current design a dependent operation without a source-set pin can wake when a new eligible
same-demand prerequisite output appears. The current role components exclude that case. Keep the
operation component until the role projection accounts for this wake-up and the rest of W1.

**Complete consumer scope.** The guard generator, binding admission, population acquisition, the
watermark projection and its one consumer, at the sites the baseline gives under
[Per-acquisition proof, and the watermark](#per-acquisition-proof-and-the-watermark), and the
activation path, which calls the full proof.

**Removes.** Per-acquisition hashing of immutable release content; the per-call decode and hash of
`data_operations.json`; the kernel component at `semantic/data_operation_projections.py:2189`.

**Prerequisites.** UDM-08 supplies the fact that a release runs only under its recorded kernel,
which makes dropping the component sound. UDM-10 supplies the kernel identity that the receipt
and the lapse rule name. **Native revision.** The transition establishes the receipt foundation.
Its successor completes the binding and population conversion before UDM-13 begins. A cause found by
UDM-20 that lies in carried assurance or the watermark is repaired here.

**What this keeps open.** Nothing about knowledge content or the declared behaviour space is
touched. The watermark stays a skip predicate under binding's authority, so a later change to
what wakes an obligation is a change to the watermark and cannot admit a wrong result. The package
relaxes one check (per-acquisition content proof) under the accepted trust decision; it closes
nothing new.

**Acceptance evidence.** With a receipt present, archive bytes altered in a test database with the
immutability trigger disabled do not stop acquisition, and the explicit verification command
refuses. Without a receipt, a caller who is neither admitter nor owner is refused with the
verification command named. A revision that changes only the descriptor leaves every
`inputs_watermark` unchanged, compared with values captured before the revision. Binding returns
the same admitted expression after the archived `data_operations.json` bytes are altered in the
test database, which shows that it reads the rows.

Apply the current-family and support checks to revalidation, reconciliation, and UDM-25
adoption. Keep the eligible reuse decision distinct from the watermark skip. The native owner
reports the settled fate and its reason to UDM-26. An expired writer or uncertain commit is
resolved by its exact intent, publication, or recovery authority before additional work starts.

## Open premises

| Premise | What settles it | Work it constrains |
|---|---|---|
| C1. The required initialization, callable and dynamic-input boundaries of each supported workload close | The [UDM-10 follow-up](#udm-10-code-closure) establishes root-specific attributed evidence using the retained counterexample and admitted runtime contracts | Generator and selected-reader reuse in UDM-14/15. PDF lowering and operation assets use a complete supported boundary or retain their incomplete identity and fresh execution |
| W1. A role-granular watermark is sound: every fact that can turn a waiting obligation bindable appears in a watermark component, and removals cannot | The native owner enumerates the relations that binding and population selection read (the model inputs the registry records for the binding closure) and compares them with the components, before the transition revision is frozen | The role-granular step of UDM-12; unsettled at the freeze, it is deferred. Dropping the kernel component does not wait on it |
| T1. The operator's trust decision for carried release proof | Accepted with RC08 on 2026-11-19; UDM-00 records it in the decision record | UDM-12 |
| B1. The registry renders byte-identically to the head frozen revision | UDM-09's first acceptance check | Whether UDM-09 lands without a revision; differing objects join the transition revision |
| P1. No consumer needs releases prepared before the transition to keep running | Operator confirmation; the standing position is that data is regenerable | The absence of a digest mapping table in UDM-10 |
| X1. Callees collected from typed bodies cover the provider binding of SQL-language bodies | Installing the registry's order into an empty authoring database, in UDM-09 | Derived installation order |

### Static Python correspondence on N31

During the private historical PDF control, the runtime repeatedly reached JSON Schema
validation from `python_port_identity`. The prepared schema carried LinkML loader-specific
string values in inherited and local patterns and resolved vocabulary labels. The cache
correctly reserves reuse for ordinary immutable input types, so those records bypassed it.
Schema preparation now detaches those values into Python text. Port correspondence uses
the shared static preparation entry point. The retained source model and the native
authorization checks still govern acquisition.

Readback of the deployed N31 release established that the re-prepared definitions and
vocabularies equal the archived records and qualify for static reuse. The cache controls
continue to exercise exact input changes, compiler substitution and colliding subclasses.
The private historical PDF case and nine cache and input controls passed
(`64d1c4441f8c42508e8876bd3a8afc67`) on 2026-11-18.

### Typed foundation registry

Foundation declarations now retain the typed routine body through installation. SQLAlchemy
visitors and pglast collect dependencies and model inputs. NetworkX derives deterministic
installation order for SQL-language binding dependencies. Procedural calls retain their
dependency identity while PostgreSQL resolves them at invocation. The registry refuses
undeclared callees, ambiguous overloads, duplicate identities and installation cycles.

The active cohort contains canonical JSON, decimal canonicalization, finite-float and
archive validation, and the immutable-mutation and finalized-insert guards. Authoring
holds the rendered cohort alongside the exact captured scripts and installs it directly.
The per-function selectors and paired archive-guard parser for this cohort are retired.
Model preview and the standalone model check also use one declaration of each generated
facade's path and renderer.

**Verified, 2026-11-18.** The identity, closure and native closure SQL scripts match
their N31 generation byte for byte. The prospective native source digest changed
from `53c1fd9e7cfd95f60f590f40d79f5eddbced6d6b2086294323eed20df596d6db` to
`8098d39a4885613af8c801db43b2cdf60b9283948d129f71b33e9532679f7e7a`.
Stage continues to acquire the frozen N31 kernel and application. The private fresh-install
and closure suite passed all nine cases (`9b5ce53624b9489bbc6b6f7ad9aff445`). The fresh
install matched normalized statements, owners and EXECUTE privileges for all six programs
against frozen N31. Application admission, runtime acquisition and Parquet export passed
with generation disabled. This fresh-install evidence covers the prospective source.

The registry still needs the DDO, PDF and remaining admission producers, their wire
entries and family claims, and a complete program manifest and install-order comparison.
The interim family-program table and the remaining named-script selectors stay under
UDM-09. The native descriptor includes the authoring capture, so registry source changes
that affect the descriptor join UDM-10 and UDM-11's identity transition.

### Transition integration

The current installation builds one graph from typed routines, views and triggers. The graph
collects calls from SQLAlchemy and pglast objects, orders creation dependencies, and derives
privileges from declared purposes. Calls to overloads use arity and an explicit signature when
arity is ambiguous. The published PDF readers declare SQL-standard bodies where PostgreSQL must
bind the underlying objects at creation. The former installed-program scanners and fixed PDF
provider order are retired. A function inventory still normalizes server-observed catalog facts
for admission. [Producer controls](../../design_review/evidence/2026-11-19_udm09-pdf-producer-cohorts/README.md)
record independent SQL and grant comparisons for the conversion cohorts.

The program manifest hashes exact ordered install statements per object, including privileges
and trigger state. The kernel identity composes those entries. The two generated descriptors
are checked separately against frozen statements to avoid self-reference. Declared calls derive
operation, lowering, read and per-family validity identities. The current source captures
authoring provenance with the frozen revision and reads the installed identities during
acquisition. Catalog proof and activation use the named verification programs. Ordinary
execution checks the carried receipt. The readiness watermark omits the kernel component.
Completion receipts carry applicable validator identities. A write-side replay records
reconfirmation after the historical episode and current check succeed.

**Tested, 2026-11-18.** The full-registry source passed fresh authoring, rendered replay,
installation, unchanged-revision comparison, and real grant checks. The same managed selection
passed the N29 conversion and conservative settlement. Three fixture assertions in the selection
failed because they expected name-only call references, a kernel-wide call digest, and a
writer-only claim grant. They were updated to use the declared ABI and actual purposes. The
original result remains `85b9c42f11444d589790fbd07775283d`.

The stage inventory compared current source against 586 frozen N31 objects. It generated 603
including the execution descriptor and identified two retirements, the release-side authored-SQL
admission entry and the superseded rich producer lookup signature. The source-native statistics
selector prepared 51 operations. Three private cases used the registered N32 head to exercise
protected authority traversal, the undetermined PDF guard and historical raw ancestry
(`d9daadb725d24e27a97b9236538a536f`).

#### Bounded stage cutover

The N32 record below is the predecessor for the [UDM-10/11 identity successor](#identity-successor).

**Tested, 2026-11-18.** The source and frozen transition are in `a07122316`. The reviewed
preview `f7b69ed2019d4eda82da7e0b588609db` bound the N31 predecessor and stage database
OID 130661481. Rollback authoring `80c15df2f6d04adb9472ba2b351b22c1` produced the one N32
transition and preserved the complete starting project snapshot. The candidate preserved the
owner and ACL of all 584 common objects. Registration `20788efec9bf40d5b203a1134cc3319a`
and deployment `f9e1664161a1413b85d03f45edcc3afc` passed. Deployment committed native
migration, archive admission and application verification.

Independent `ci db check --target deployment --release` and `ci release check --target
deployment --release` passed for the new release. The explicit activation of
`ddo-current-pdf-bounded` advanced its generation from 28 to 29. A repeatable-read comparison
found the same 16 request IDs, 14 completion-intent IDs and 14 published episode IDs. Live
readback found eight validator identities and confirmed both retired signatures absent.
The kernel identity is
`kernel:5a39fd82bf50220ac7fce542678af078a23399bafcf147d17cf9eff9ce73e0b3`.
With an unusable database endpoint, `ci schema native-candidate --expected-predecessor
semantic_ddo_pe_n32` returned `no_native_change` and created no candidate output
(`303bcab38f6547ef8a4128de3eac9e5f`).

The integrated private selection recorded 51 passed and one failed fixture
(`afc1886e16e943d2a47ec7bbb719a464`). Its synthetic table omitted the mandatory explicit
read-role declaration. The corrected exact case passed (`648928406fc644ee82f130610e163ded`).
Pyrefly and Ruff passed (`3e7c0481e7d0488997b0606707d09302`,
`3d0e2d2715cb414bb3974694f0912e8b`).

Both installed controls passed (`f2beb4a348664a07a7e9c721754a1180`). They exercised
cross-release discovery, retained support inspection and concurrent conservative settlement in
isolated projects. The bounded project's retained identities and generation were independently
read back after both controls. [Stage evidence](../../design_review/evidence/2026-11-19_udm09-stage-cutover/README.md)

#### Identity successor

The source capture now derives Python code identity from declared producing and serving entry
points. Formal, sentence, characterization and PDF assets retain their explicit material
parameters. Exact transport custody travels with the execution binding. An unresolved code
closure selects demand-scoped execution and constrains draft consumption to the original attempt.
The [fresh PDF contribution refusal on N34](operation-reuse-and-recovery.md#fresh-pdf-contribution-on-n34)
limits that route for PDF publication. Reads report the unresolved
dependency and withhold the page cache and resumable cursor.

The statistical release prepares 51 operations. Eleven have incomplete producing code
identity, including PDF capture, recognition, and reconciliation. The current capture therefore
withholds checkpoint reuse across attempts for that PDF workflow. Both provider attestations
remain in the execution binding, which retains nine transport inputs.

The release manifest binds material inputs, generated artifacts and the serialized release
products. Exact generator sources and external distributions travel with the authenticated
native authoring state. The native PDF guard compares schemas, actions and native inputs.
The lowering identity is authenticated by the producing release and checked at certification.
Updating observed Python producing code therefore leaves installed PDF program statements
unchanged when the native requirements are equal.

The inspection capsule and the persisted archive use the same material input inventory.
Archive replay derives the current port products from the retained model, protocol and SQL
artifacts. The former generator file checklist and its duplicate acquisition routes were
removed. The candidate inspection view `--view provenance` reports the authenticated
authoring state.

The consuming-release check preserves attribution to the original completion. For the same
request and binding it checks only newly applicable or changed family identities. A different
consuming binding checks its whole applicable family set. Reconfirmation retains its original
receipt scope.

The model-change preview compares typed installed program statements, privilege policies and
descriptor effects with the frozen head. For equal installed bytes a native-only request
settles before acquiring authoring resources. An application change can continue through the
same model-change route with its reviewed application effects.

**Tested on 2026-11-19.** The material-archive replay, runtime binding and exact execution-source
readback passed on a private PostgreSQL clone. The same selection passed the 16 port artifact
controls (`4d0ff3c22f2d4d5a9495bebe80bde8aa`). The refreshed N33 candidate
(`8038f3c8831245bbad7e3c6b212f5630`) preserved the prior draft's install statements
for all 616 objects, catalog and privilege facts, migration operations, and admission SQL. Its
authoring provenance changed. The bounded project readback matched the starting snapshot
after rollback-only authoring.

The exact registered statistical candidate passed private native installation, separate
archive and admission commits, runtime readback, and source byte verification
(`f61cf755370d4c93a569ba65078dcab7`). The final registered head returned
`no_native_change` through both `ci schema native-candidate` and a native-only
`ci model change preview` with unreachable database endpoints
(`6926c7221a6c49b5871ce49c4a0c8969`, `c3ca99d795d54f2bab196f3cb1351502`).

**Stage cutover, 2026-11-19.** Registration `215f4a0144f24dcea3cd46af3c67550f`
and deployment `4058aa94d5e84b0882bd4a946c418d1d` installed N33 and statistical
release `release:3cd1f63feb0dc2374c4e14fe10f9ddc81d8d273b65d773606a02779fe4a48b5e`
on `corpus_structure_ddo_stage` (OID 130661481). Its kernel identity is
`kernel:6e2c4df0656b4473a83b77d12599d886802f33636b4a647e55d9cfe159d02311`.
The release and database checks passed. Compare-and-set activation advanced
`ddo-current-pdf-bounded` from generation 29 to 30. The 16 request IDs, 14 intent
IDs and 14 episode IDs matched the preflight snapshot after authoring, installation
and activation. The new release shares none of the 14 retained episodes' exact recipes,
so the stage assessment found zero eligible historical episodes for adoption.

Installed cross-release discovery and concurrent conservative settlement both passed in
isolated stage projects (`8dd74a2505e140a7a3181d6ce9782c4a`). The bounded project
matched the complete post-activation snapshot afterward. [Stage readback and receipts](../../design_review/evidence/2026-11-19_udm10-11-stage-cutover/README.md)

## State

| Package | State |
|---|---|
| UDM-08 | Acquisition and export use retained identities and the running wire protocol. See the [entry increment](../unified-domain-model-and-execution_2026-11-19.md#entry-increment) for evidence. |
| UDM-09 | Complete. One typed installation graph, direct grants and family declarations are integrated. The fresh install, frozen ACL correspondence and N29 conversion passed. N32 established stage generation 29. |
| UDM-10 | N33 bounded identity transition complete. The [code-closure follow-up](#udm-10-code-closure) is scheduled. Real generator and selected-reader reuse needs complete supported workload custody. Unresolved producing code selects demand-scoped fresh execution. The [N34 PDF contributor refusal](operation-reuse-and-recovery.md#fresh-pdf-contribution-on-n34) prevents fresh PDF publication in the observed case. |
| UDM-11 | Complete for the bounded stage. The installed kernel guard and exact program comparison passed. Both equal-byte authoring routes settled offline. |
| UDM-12 | Complete for the bounded stage. N34 carries admitted binding and population facts and runs explicit archive and catalog proof. The cutover advanced generation 30 to 31. [Stage evidence](../../design_review/evidence/2026-11-19_udm12-carried-assurance/README.md). W1 remains deferred on the prerequisite wake-up premise. |

# Identity, program registry, revisions and carried assurance: design advice for the UDM plan

Focused design advice (not a formal review), 2026-11-19. Scope: R04, R05, R06/F01, R10, R11, R14,
R17 and rule impacts RC06–RC11, RC13, RC15 of
`docs/design_review/reviews/design_review_unified-domain-model-and-execution_2026-11-18.md`.

**Baseline and coverage.** Source facts from the frozen snapshot `snap7/` (commit `cb4e09667`,
production source equal to `5139eaba3`); paths below are relative to
`snap7/python/corpus-structure/src/corpus_structure/` unless they start with `docs/` or
`target_alembic/`. Labels: **[S]** established by source inspection 2026-11-19 at the cited
lines; **[I]** inference; **[P]** proposed. Read in full: the review sections named above;
`semantic/data_operation_storage.py:1–1142, 1550–1575, 1845–1935`; `semantic/execution_admission.py`;
`semantic/native_products.py:1–260, 330–402`; `semantic/target_installation.py:60–500, 727–833`;
`_query_custody.py:1–260`; `semantic/file_custody.py`; `schema/model_change.py:500–1066`;
`cli/schema.py:400–660`. Every other path cited was read at the cited lines. Not read: generator
bodies beyond those lines; the bodies of `ops.ddo_require_binding` and population selection beyond
`:225–255` / `:900–925` (matters for §5); `schema/model_deployment.py`; the CLI `model` command
bodies. I ran one read-only stdlib script over the snapshot to compute static import closures
(§2.4). No project code, test, database or provider was run.

## 0. Corrections to premises the brief and review carry

1. **[S] The generated release guard's kernel comparison is conditional, not unconditional.** The
   review (R06 revision, F01) says `data.require_execution_release` "already requires the
   release's archived native digest to equal the installed descriptor". It does so only inside
   `_native_constraint_checks` (`semantic/native_admission_release.py:505–627`): the archived
   projection CTE filters on `native_digest = descriptor.source_digest` (`:531`), and the refusal
   "archived DDO native constraint projection is missing or incompatible" fires only under
   `If(invalid, …)` (`:608–626`), where `invalid` requires some applicability row with a pattern
   constraint or a scope outside `shape`/`accepted_value` (`:585–604`). A release with no such row
   passes the guard under any installed kernel. The only other comparison is at *first* definition
   admission (`semantic/data_operation_compiler_native.py:999–1006`, `new_release AND …`). The
   Python rebuild in `require_data_operation_native` compares the **checkout** with the installed
   descriptor, never the release with it (`semantic/data_operation_storage.py:1135–1141`).
   Consequence for R06: deleting the two rebuilds is not enough; the replacement must compare the
   release's recorded kernel value with the descriptor explicitly (§4).
2. **[S] A module-level import closure is nearly the whole package** (447 of 767 modules from
   every entry tried, §2.4), so the review's "module closure fallback" is about as coarse as
   today's capture; function-level slices carry R05's benefit where reuse is costly.
3. **[S] `acquire_publication_port` has no caller** anywhere in the snapshot (`src/`, `tests/`,
   `scripts/`; `semantic/data_operation_admission.py:375`). It is a retirement candidate for R13,
   and one fewer R06 call site to migrate.
4. **[S] `public_disclosure` is pinned by the cut.** It is a required column of the read row
   `ops.data_demand_read` (`model/semantic/data-operation-physical.yaml:620–632`, with
   `trust_snapshot` and `kernel_digest`), and the cut carries `read_id` among its required pins
   (`semantic/demand_results.py:72–84`). The review's open question on it (R10 revision) is settled
   for the cut-keyed continuation basis.

## 1. Program registry and handoff (R04)

### 1.1 What exists today [S]

| Hand list / text operation | Site | Size at `cb4e09667` |
|---|---|---|
| Capture list | `native_protocol_sources`, `semantic/data_operation_storage.py:48–574` | 97 `SourceArtifact` constructions, 93 distinct literal `native/…` names, a 7-entry program tuple each yielding `.sql`+`.py` (`:143–194`), 7 splatted helper families |
| Required set | `_captured`, `:577–701` | 106 names (92 literals + 14 from the program loop); refuses missing/duplicate, accepts extras |
| Concatenation list | `native_sql`, `:761–822` | 37 named + 2 appended (`:810, 813`); 6 not in the required set: `data-attempt-release`, `data-claim`, `data-claim-batch`, `data-completion-settlement`, `data-operation-renewal`, `data-read-boundary` (so a missing one is a `KeyError`) |
| Digest splice | `:815–819` | two markers replaced by `str.replace`; markers live in 5 generator modules (`data_operation_compiler_native.py:49–50`, `data_completion_settlement_native.py:47`, `data_read_boundary_native.py:98`, `demand_result_native.py:223`, `data_derivation_native.py:614` via `storage.py:141–178`) |
| Entrypoint rename | `_rename_native_entrypoints`, `:725–758` | parse whole kernel, rename, reprint, reparse, splice by span |
| Wire wrappers | `_wire_wrapper_sql`, `:825–876` | text appended after rename |
| Per-function re-parse | `data_operation_native_definitions` `:1897–1935`; `_task_call_definitions`, `_release_guard_definitions`, `current_admission_definitions` (`semantic/native_authoring.py:177–268`) | each re-parses a concatenated script to find named functions |
| Grants by name | `:1906–1932` | 5-entry purpose→role map + 5 named special cases |
| Installation table | `semantic/target_installation.py:227–249` (11 rows), runtime bindings `:281–295` (3), provider order `:317–329` (7) | |
| Authoring capture | `semantic/native_products.py:133–165` (28 module names) + 12 artifacts `:166–200`; `extra_sources` `target_installation.py:87–122` (12) | |
| Inventory re-parse | `semantic/native_inventory.py:83–158` | recomputes owner/EXECUTE from parsed text |
| Catalog-check recovery | `semantic/native_admission.py:42–82`, markers `native_admission_release.py:35–38` | comment substrings, literal fallback anchors |
| Facade outputs | `schema/model_change.py:53–61` (7 paths) zipped `strict=True` with 7 calls `:540–548` | |

### 1.2 Target [P]

**A program declaration** (one immutable value per installed object) carries: *identity* (the
existing `NativeIdentity`); *body* as typed statement objects (`native_program.function`/
`sql_function`, pglast `CreateTrigStmt`/`ViewStmt`/`GrantStmt`), or bytes for residue only, rendered
**once** to the install statements that frozen revisions already store per object (N29 object keys:
`catalog, identity, role_bindings, source, statements`); *callees* collected from the typed body
(SQLAlchemy `visitors.iterate` over `FunctionElement` package/name, pglast `FuncCall`), declared by
hand only for residue, with an undeclared registry-schema callee refused as internal inconsistency;
*purposes* from which grants are generated through the purpose vocabulary (RC12), plus owner;
*families validated* (set), on the validator's declaration until R02's `ValidityFamily` member
names its program; an optional *wire entry* from which the public wrapper and the `ddo_impl_`
body are both generated; *model inputs read* (tables/columns found by SQLAlchemy visitors), used for
change explanation and the watermark check (§5) but not for identity; and *sub-programs*, so the
guard's catalog-check block is its own declared part.

**Who registers.** Each generator module exposes one registrant (`register(model)` returning its
declarations); the registry module holds the one tuple of registrants, the single declared list.
Facades and other generated Python register as outputs (the self-checking
`schema/generate.py:540–578` kind, retargeted to the released model).

**Consumers.** *Installation*: `networkx.lexicographical_topological_sort` over callees gives the
order and replaces the provider list; each declaration becomes a `NativeDefinition` directly
(`definition_from_sql` still parses its one statement for server normalization). *Capture*: the
release holds a **program manifest** (name → identity) and the generated client artifacts, not
module bytes plus concatenated SQL (§2.5). *Required-set check*: gone; completeness holds by
construction. *Facades*: registry outputs; `_NATIVE_OUTPUTS` and the strict zip go. *Descriptor*:
one program generated last, returning the identities (§2.2); guards call it.

**Text operations that disappear** for current generation: kernel concatenation, both marker
splices, the entrypoint rename, appended wrappers, the per-name re-parse selectors, grants by name,
inventory re-parse, comment-boundary recovery, and `function_bodies`/`literal_json_descriptor`
reads of current products. Text reads remain only for authenticated frozen bytes. The catalog-check
boundary is recorded in a revision when it is frozen, and the fallback anchors serve only revisions
frozen without that record.

**Byte-equality acceptance for the registry alone [P].** Introducing the registry with the same
renderers must produce install statements byte-identical to the N29 frozen `statements` for all
585 desired objects (independent expectation: the frozen JSON file). If that holds, R04 lands
**without a native revision**; the descriptor-program change is part of the identity transition
(§3.3), not R04.

## 2. Identity (R05, RC06, RC10, RC11)

### 2.1 Today [S]

`native_source_digest` (`semantic/data_operation_storage.py:712–722`) hashes every `native/*`
captured artifact (generated SQL **and** module bytes, the physical/LinkML closure, library
versions via `importlib.metadata.version` imported at `:56`). It keys: the installed descriptor
literal (`data_operation_compiler_native.py:1207`); first definition admission (`:999–1006`) and
the release row `native_kernel_digest` (`:1055–1093`); read acquisition
(`data_read_boundary_native.py:98`, `demand_result_native.py:223`, column
`data-operation-physical.yaml:632`); the completion seal (`data_completion_settlement_native.py:490–499`);
the receipt replay gate (`:671`, `data_derivation_native.py:614`, column `:484`); each native
operation's `behavior` (`data_operation_storage.py:993`) and each call binding's `source_digest`
(`:1068`, checked `data_operation_artifacts.py:93`); the watermark (`data_operation_projections.py:2189`).
PDF lowering: 70 files + 14 libraries (`semantic/pdf_lowering.py:15–106`). Served reads: the
owner-declared allowlist (`_query_custody.py:1–4, 17–127`). Release id: sha256 of a manifest whose
`dependencies` lists every artifact, including the whole native capture and `generator/*`
(`semantic/prepare.py:956–986`; capture assembled at `data_operation_preparation.py:261–266`,
`primary_operations.py:403–404`; generator files `data_operation_artifacts.py:22–39`). The execution
contract descriptor also carries authoring provenance (`native_products.py:389`, 40+ input digests).

### 2.2 Target layering [P]

| Identity | Definition | Keys | On mismatch |
|---|---|---|---|
| Program | sha256 of the canonical list of an object's rendered install statements | revision deltas; the other identities | — |
| Kernel | sha256 over sorted (object identity, program identity) of the installed set, **excluding the descriptor program** (no fixed point) | descriptor check at acquisition; release record; definition admission; release guard | refuse execution of that release ("re-prepare"); reads re-acquire |
| Validator, per family | sha256 over sorted (name, program identity) of the family's validator programs and their transitive callees; the conservative validator (R16) has its own | completion seal and receipts carry `{family: identity}` for the operation's families | run the battery; record reconfirmation (§2.3) |
| Read closure | closure identity of the read-acquisition and read-page programs | `ops.data_demand_read.kernel_digest` successor; `ddo_read_acquisition_present` | re-acquire the read (cheap) |
| Operation behavior | closure identity of a native operation's own programs | `behavior` (`storage.py:993`), so recipes move only with their programs | recipe change, as today |
| Code (Python) | derived closure, §2.4 | PDF lowering, served reads, opaque boundaries, generation cache | withhold reuse; never refuse service |
| Release id | manifest over model capture + generated artifacts + program manifest (incl. kernel identity) | release | new release |

The descriptor program returns the kernel identity, the program-identity map, the per-family
validator identities, the read-closure identity and `physical_id`. Guards and seals **call** it
(or a small accessor) instead of embedding literals, so an identity change rewrites one object plus
the programs whose bytes changed.

### 2.3 Seals and reconfirmation (RC06) [P]

The receipt's `validating_kernel_digest` (`data-operation-physical.yaml:484`) and the seal's
`kernel=_KERNEL` (`data_completion_settlement_native.py:490`) become a `{family: validator identity}`
map. If an operation is in several families, the map has one entry per family. An unclassified
operation gets the conservative validator's entry. A receipt skips the battery only when, for
every family, the recorded identity equals the descriptor's or a reconfirmation row
`(receipt, family, identity)` exists. Today the battery runs in stable functions (`:695–697`), which
cannot write. Reconfirmation is therefore recorded by a volatile routine: the next publish or
settlement that runs the gate for that request, or an explicit `ci` command that reconfirms a
release's receipts after a deployment. The record is append-only and idempotent.

### 2.4 Code identity: mechanism and limits [S] facts, [P] design

**What exists.** `semantic/python_operation_sources.py` is a *closed supplied-source* extractor
("no target imports or loader discovery", `:1–5`): the caller supplies the module collection
(`:104–111`); Griffe, LibCST and astroid models are built per module (`:242–347`);
`implementation_slice` (`:1063–2212`) walks reached definitions from entry callables, records
`SourceUnknown` for unresolved references or missing bodies (`:1152–1171`) and fails on unsupported
dynamic call forms (`:2118`). It does not discover modules, so it cannot compute an import closure
alone. `semantic/python_module_projection.py:110–120` gives a layout-insensitive module meaning.

**Measured on the snapshot (my stdlib script, every `Import`/`ImportFrom` including function
bodies, `TYPE_CHECKING` blocks excluded, first-party resolved by path):** 767 package modules;
from `serve.rich_queries`, `semantic.pdf_lowering`, `semantic.data_operation_storage` and
`semantic.native_admission_release` the closure is **447 modules in every case** (121 third-party
or stdlib top-level names); top-level imports only give 68, 15, 21 and 17 modules but miss lazy
imports and are unsound. The package's pervasive function-local imports form one large component.
Dynamic imports exist (`semantic/data_operation_ports.py:1242, 2194–2198`,
`data_operation_consumers.py:309, 369, 408–462`, `terminology.py:38`, `methods/pm2_*.py`).

**Design.**

1. *Stage 1, module closure (always computed, sound, coarse).* A small stdlib-only function: walk
   every import node from the declared entry modules, resolve relative imports, map first-party
   names to files under the package root without importing (no `find_spec`, which executes parent
   packages), skip `if TYPE_CHECKING:` bodies, map third-party top-level names to distributions with
   `importlib.metadata.packages_distributions()` and `version()`, drop `sys.stdlib_module_names`
   (covered by the interpreter version). Each module contributes its
   `python_module_projection`-style syntax digest. Non-literal `importlib.import_module`,
   `__import__`, `spec_from_file_location`, `exec`/`compile` of loaded text inside the closure mark
   the identity **incomplete** with the locations.
2. *Stage 2, reachability narrowing (where reuse is costly).* Run `ClosedPythonSources` over the
   stage-1 module set from the declared entry callables; when the slice has no unknowns, the identity
   is the reached definitions' normalized nodes plus their modules' top-level statements and the
   distributions those reach. With unknowns, stage 1 stands (sound, coarse). Use stage 2 for PDF
   lowering and opaque construction/formal boundaries; served reads may stay on stage 1 (a cache miss
   after an unrelated edit is cheap and the MCP process restarts on drift anyway).
3. *Custody* (RC09, RC10): `_query_custody`'s finder and loader stay; its allowlist is replaced by the
   stage-1 module set computed at process start for the declared served entry modules. It compiles
   exactly the hashed bytes, as today (`_query_custody.py:142–176`). Drift still refuses with restart.
4. *Incomplete identity* (ADR-0092 `:27`, "Unknown required determinants refuse reusable identity"):
   the result is computed and served, but not cached (T4/D4), not offered as a resumable
   continuation, not reused as a lowered PDF record, and an opaque boundary's recipe carries an
   unknown determinant so its request identity is not reused. A diagnostic names the dynamic site.
5. *Execution fit [I].* Stage 1 parses ~450 files once per process or preparation; stage 2 runs in
   preparation, keyed by module digests. Neither runs per request.

**Open premise C1.** Whether the slicer resolves the PDF lowering and served-read entry callables
without unknowns. Settle: run `implementation_slice` once per entry inside the implementing package
(a bounded check, not a separate probe folder unless it fails broadly). If it does not, PDF lowering
identity is the 447-module closure: sound, and still better than the 70-file list, which omits
modules (the review's two known omissions must appear, §12 of the review).

### 2.5 Release id and provenance (RC11) [P]

Release manifest `dependencies` keep the model capture, pack inputs and generated artifacts (wire
contracts, call bindings, ports manifest, the program manifest with the kernel identity). They drop
`generator/*` and the module-bytes `native/*.py` artifacts. Generator provenance (generator code
identity, per-module digests, distribution versions, model identity) is recorded (a) in each frozen
revision as a sidecar field written at freeze time, replacing the `inputs` list in the deployed
`data.execution_contract_descriptor` (`native_products.py:389`; `native_admission.py:23–39` reads it
back and moves to the sidecar), and (b) in the generation cache key (T2/D2). It stays auditable by
revision inspection without being an identity input.

## 3. Revisions (RC15)

### 3.1 Detection [P]

Before connecting to the authoring database, the candidate command computes the registry's
(object identity → program identity) map and the predecessor's map from the head frozen state's
per-object `statements` (no migration of frozen files: identities are recomputable from what N14–N29
already store). The native delta is the set of objects added, removed or with a differing program
identity, plus privilege-policy differences. If that set is empty and the request has no physical
change, data step, retire or recreate, the command reports **`no_native_change`** (head revision,
object count, kernel identity) and writes no products. Today `native_basis` falls back to
`"explicit_native_authoring"` whenever native is requested (`schema/model_change.py:993–994`); that
fallback is replaced by "requires a differing program identity"; explicit `recreate` remains the
operator's override.

### 3.2 Run time [P]

`require_native_execution` keeps authenticating the installed descriptor and guard bodies against
frozen expectations (`semantic/execution_admission.py:120–178`); the per-acquisition comparison
becomes **release-recorded kernel identity = descriptor kernel identity**, explicit in the generated
guard (a new predicate beside `release_preconditions`, `native_admission_release.py:41–56`) and, until
that revision lands, in Python (§4).

### 3.3 Migration [P]

One **identity transition revision** installs the descriptor program, rewrites the bodies that
embedded the two markers to call it, adds the receipt validator-identity map and the reconfirmation
relation, and adds the explicit kernel predicate. Then:

- *Releases*: their recorded `native_kernel_digest` is old-style; they refuse with a re-prepare
  instruction and are re-prepared once. No mapping table: no consumer needs old releases to run, and
  data is regenerable. Batch this re-preparation with R02/R07's (lowered family column) and R14's.
- *Receipts and seals*: old receipts have no validator map, so they differ; the battery runs on first
  use and reconfirmation is recorded (§2.3). No backfill.
- *Reads*: re-acquired. *Watermarks*: change once (§5), so each waiting obligation re-binds once.
- *Frozen revisions*: unchanged bytes; the catalog-check boundary is recorded from this revision on.

### 3.4 Catalog snapshots

[S] N29 freezes 585 objects with statements and normalized catalog (`_native.json` 9.06 MB, plus
`_upgrade.txt` 2.76 MB, `_admission.sql` 0.60 MB); the 46 `*_native.json` files total 387 MB (audit:
about 206 MB for N14–N29). [P] The design does **not** change what a revision freezes
(`admit_native`/`load_native_state` need the full catalog). It reduces how often one is authored, and
program identities would key shared object storage if the owner later chooses it (a separate
decision).

## 4. The execution path generates nothing (R06, F01)

**Callers today [S].** `require_data_operation_native` (`data_operation_storage.py:1127–1142`;
`native_source_digest()` at `:1139` and `:1142`, each a full `native_protocol_sources()` rebuild) is
called by `acquire_python_execution` (`data_operation_admission.py:285`; reached from
`acquire_prepared_execution` `:230` and `orchestrate/native_demand_io.py:99`),
`recheck_cached_execution` (`:354`; `native_demand_io.py:114`), `acquire_publication_port` (`:390`;
no caller, §0.3) and `admit_data_operation_definitions` (`data_operation_storage.py:1561`, plus a
third rebuild in its return `:1571`; reached from `admit_data_operation_release`
`data_operation_admission.py:131` ← `execution_admission.py:40`, `schema/model_deployment.py:1008`,
`semantic/releases.py:599`). `serve/demand_export.py:281` rebuilds the capture to read one
protocol schema. About 20 test lines reference these two functions.

**Change [P].**

1. `require_data_operation_native` reads the release's recorded kernel value from the prepared
   release, with no generation: the `native_digest` of the archived
   `data_operation_native_definitions.json` (`prepare.py:1373–1393`) or the ports manifest's
   `native_source_digest` (`data_operation_artifacts.py:118`). It compares that value with
   `sem.data_operation_native_descriptor()` and returns it. This is the **explicit** release ⇄
   installed check that §0.1 shows is missing today. Delete `:1139`, `:1142` and `:1571`.
2. `serve/demand_export.py:281` uses `wire_contracts()` (the ambient, process-cached protocol,
   `data_operation_wire.py:47–50, 525–529`), later the compiled model's protocol projection (T1).
3. *Working-tree drift.* Generator modules are off the execution path, and authoring
   regenerates. Operation modules keep custody against the runtime manifest
   (`data_operation_admission.py:303–315`), served helpers keep query custody, and model files
   follow RC09. The rebuild was only incidentally a checkout ⇄ installed detector; that comparison
   moves to `ci model change preview` and status reporting.
4. *Why first.* It needs no registry, no revision and no new identity. The value it compares is
   already recorded in every admitted release. It removes the largest repeated work and makes the
   kernel check unconditional.

## 5. Carried assurance (R11, RC08) and the watermark (R10, RC07)

**Per acquisition today [S].** Python stats every revision file, queries catalog fingerprints and
admits the descriptor and guard (`execution_admission.py:120–178, 240–250`). The SQL guard
(`native_admission_release.py:343–409`) re-hashes manifest and prepared bytes
(`archive_projection_native.py:219–270` → `closure_native.py:315–340`), runs the whole catalog
battery, decodes and walks the release's diagnostics, constraint and inference projections, checks
the always-empty authored-SQL population, and inserts the receipt if absent (`:59–97`), which
short-circuits nothing. Binding and population decode and re-hash `data_operations.json` per call
(`binding_admission_native.py:231–251`, `population_acquisition_native.py:906–921`).

**Target [P].** Rename today's body to a full re-proof routine (used at activation, by
`ci … verify` and when no receipt exists). The per-acquisition guard checks four things:
finalization; a deployment-admission receipt for (release id, `physical_id`, descriptor digest,
kernel identity); release kernel = descriptor kernel; and the caller-purpose checks. Lapse: any of
the four identities differs, which runs the full proof and records the receipt (admitter or owner
only, as today at `:85–96`; otherwise refuse with the verification-command instruction). Binding and
population read the admitted definition rows. Trust trade (accepted with RC08): a superuser
altering archive or catalog bytes is detected at verification or activation, not on every
acquisition.

**Watermark [S]/[P].** The watermark (`data_operation_projections.py:2062–2192`) is consumed only as
a skip predicate. A waiting obligation is not re-bound while its watermark is unchanged
(`data_operation_demands.py:731–737`); binding stays the authority. A too-coarse watermark costs
re-binding; a too-narrow one can leave an obligation waiting (liveness), never admit a wrong
result. **Dropping the kernel component** (`:2189`) is sound once §4 lands: a demand belongs to one
release, and after §4 that release runs only under its recorded kernel, so the component is
constant for every runnable demand. If a later design lets releases survive unrelated kernel
changes, put back the identity of the binding closure (binding, population and discovery programs
and their callees), not the kernel. **Role granularity** needs this argument:
every fact that can turn a waiting obligation bindable appears in a watermark component. Those
facts are new visible products matching its input roles, populations, discovery, original
admissions, trust-snapshot changes and binding-program identity. Removals (revocations,
supersession) cannot turn waiting into bindable [I; the argument must confirm it]. The argument **can be made from source** by
enumerating the relations that `ops.ddo_require_binding` and population selection read and checking
each against a component. I did not read those bodies. Once registry declarations record the model
inputs they read, the enumeration is the binding closure's read set and a test can compare it with
the watermark's components. Until then, keep the operation-granular prerequisite component next to
the role-matched one that already exists (`:1781–1809, 1919–2059`).

## 6. Served-read reuse basis (R10, RC13)

**Premise (DA-075), stated exactly.** For a served query q with normalized selection s, the
derived rows depend on the read instance only through (frontier content stamp, release, runtime,
implementation identity, authorization scope). They do not depend on `read_id`, `read_snapshot`,
`frontier_at`, `owner_xid`, `access_universes`, `public_disclosure` or the census flags of
`ops.data_demand_read`, except as those are functions of the content stamp. **What settles it:** the
native owner shows, for each read-page program closure, which read-row fields it reads, and that each
one is either in the content key or determined by it. `public_disclosure` and `access_universes` are
authorization-shaped, so for most queries they must enter the key with the authorization scope.
**Buildable now:** the per-query `reuse_basis` field (default `cut`), the D4 continuation-page store
keyed by (query identity, cut, implementation identity, authorization scope, format version), and
the authority recheck per page. The cut pins `read_id`, hence the read row with
`public_disclosure` and `trust_snapshot` (§0.4). The `content` basis is declared per query only
after the premise holds; the identity-exclusion comparison is the first candidate.

## 7. R14 and R17

**R14 [S]/[P].** `scientific_policy_recipe` (`semantic/scientific_evidence.py:192–243`) is a
hand-written dict with prose fields and `"bounds": [0.25, 3]`, duplicated by the kernel's
`rng.uniform(0.25, 3, …)` (`:1301`). `require_scientific_policy` (`:246–257`) compares it byte for
byte with the archived artifact, so a wording edit refuses every release. Decision rules are already
validated YAML (`:66–78`, `model/semantic/scientific-policies.yaml`). Target: one LinkML class
holds the computation parameters (bounds, tolerances, seed rules, method names) as instance data
in that file; the kernel reads the bounds from the validated declaration; the recipe is the
canonical serialization of the declaration plus the schemas, computed once per compiled model. It
needs no native revision unless the scientific layout in the descriptor changes
(`native_products.py:373–386`), and it needs re-preparation (batch with §3.3).

**R17 [S]/[P].** Preparation archives `operation/slices.yaml` (`semantic/regeneration.py:110–118`).
`prepare_source_demand` instead resolves a pack directory by matching the live `semantic.yaml`
`name` against archived module names without comparing bytes
(`orchestrate/source_operation.py:32–68`), then reads the working tree's `slices.yaml`
(`:160–164`). Target: read `operation/slices.yaml` from the release's archived inputs
(`semantic/releases.py:422–428`, `open_release_inputs`), with absent meaning `{}` as today. Drop
the name-matching lookup if nothing else needs the pack directory (in this function only `:160`
uses it [S]; whether a release can archive two packs' `operation/` files is [I] no, because the
names are unprefixed). No revision.

## 8. Supersession (passages these designs override)

- `docs/plans/declared-data-operations/products-and-support.md:429–430` ("Validity compares
  `native_kernel_digest` with the installed source digest") and `:452–453` (per-kind check of
  "mutable premises (kernel digest, …)"): replaced by per-family validator identity and the explicit
  release ⇄ descriptor kernel check.
- `:489, :492` (the read records "the native kernel digest"; "refuses on a kernel difference"):
  the read-closure identity takes its place.
- `:527–535` (PE-S21, "The intent records the installed kernel digest, which covers every
  completion-validator body … A differing or absent digest runs the full battery as today"): the
  intent records per-family validator identities, and the battery records reconfirmation.
- `:575–576` (`inputs_watermark`): loses the kernel component (`data_operation_projections.py:2189`).
- ADR-0124 Decision `:32–38` (identity "from source digests authenticated at import" over the
  owner-declared allowlist, `_query_custody.py:1–4`): becomes the derived closure under the same
  custody (supersede by ADR; drift refusal stays, RC09/RC10).
- Release id: `semantic/prepare.py:956–986` and `docs/design/D2-schema-and-guidelines.md:403`
  ("composed dependencies archive their bytes … with the semantic release"): generator bytes
  become provenance (RC11). `semantic/native_products.py:26–41, 389`: provenance leaves the deployed
  descriptor.
- Revision practice narrated in `docs/plans/declared-data-operations/postgresql-realization-and-retirement.md`
  (N14–N29): revisions follow program identities (RC15). ADR-0092 `:27` is supported, not
  superseded.

## 9. Order, packages and acceptance

| # | Package | Delivers | Needs | Native revision | Migrates / removes |
|---|---|---|---|---|---|
| 1 | Execution path generates nothing (R06, F01) | explicit release ⇄ descriptor check from recorded value; demand export from ambient protocol | — | none | removes 3 rebuilds per definition admission, 2 per acquisition/recheck; tests referencing the rebuild |
| 2 | Release-bound pack inputs (R17) | archived slices | — | none | removes live slices read and name lookup |
| 3 | Program registry (R04) | declarations, registrants, topological install, generated grants, facades as outputs | — | **none if byte-identical** (acceptance) | removes the lists and text operations of §1.1; authoring fixtures move to the registry |
| 4 | Code identity and custody (R05 code part, RC10) | stage-1 closure, custody from it; stage-2 for PDF lowering and opaque boundaries | — (C1 for stage 2) | none | removes `LOWERING_FILES`/`LOWERING_LIBRARIES`, query allowlists, whole-file opaque hashes; lowered PDF records recomputed once |
| 5 | Identity transition (R05 native part, RC06, RC07 drop, RC11, RC15, R11/RC08) | program/kernel/validator/read-closure identities, descriptor program, reconfirmation, carried receipts, explicit guard predicate, revision detection, release id without generator bytes, provenance sidecar | 3; validator identity uses the interim family attribute or R02's vocabulary | **one transition revision** | releases re-prepared once; receipts reconfirm lazily; watermark kernel component removed |
| 6 | Scientific policy (R14) | declared parameters, derived recipe | — | none (unless layout changes) | re-preparation batched with 5 |
| 7 | Served reuse basis (R10, RC13) | `reuse_basis`, D4 continuation pages | 4 (implementation identity) | none | — |
| 8 | Role-granular watermark | the §5 argument, then the component change | 3 (model inputs), argument | rides the next revision | — |

**Batching.** Package 5's revision should also carry R02's lowered family column and guard
selection, R16's conservative validator, R11's binding-from-rows and R07's connections: all of them
change guard and validator bodies and need the same re-preparation. Alternatively, R07's batch can
land first. Every revision after package 5 gets RC15 detection.

**Acceptance (independent expectations; each fails on a wrong implementation) [P].**

1. Registry statements equal the N29 frozen `statements` for all 585 objects, and the RC15 detector
   reports `no_native_change` against N29 (expectation read from the frozen JSON).
2. Kernel identity computed from the registry equals the one computed from the head frozen file.
3. A docstring or helper edit in a captured authoring module (temporary copy) that changes no
   rendered byte yields no candidate, unchanged identities and release id, and seals that skip the
   battery.
4. A fixture generator variant adds one statement to family X's validator: only X's validator
   identity and the kernel identity change; only X's receipts run the battery and record
   reconfirmation (expected sets from a hand-written family → program fixture map).
5. A module imported lazily inside an entry function (temporary package tree) moves the code
   identity with no list edit; `importlib.import_module(name_var)` instead marks it incomplete, and
   the result is served but neither cached nor resumable.
6. With a meta-path blocker on registrant modules, or a counting spy on generation, acquisition,
   recheck and definition admission succeed with zero generations. A `PreparedRelease` whose recorded
   kernel differs is refused, including one with no pattern constraints (§0.1).
7. With a receipt present, archive bytes altered in a test database (immutability trigger disabled)
   do not stop acquisition; the explicit verification command refuses.
8. A descriptor-only revision leaves every `inputs_watermark` unchanged.
9. With archived slices X and working-tree slices Y, the demand selects X's sections.
10. A declared bound edit changes the recipe and, under a fixed seed, the sampled interval; a prose
    edit outside the declaration changes nothing.

## 10. Flexibility check

Nothing here constrains knowledge content, vocabularies or the declared behaviour space. Program
identity digests what is installed, and code identity is derived without any new declaration. An
unclassified operation gets the conservative validator's identity (R16). Refusals cover internal
inconsistency (undeclared callee, duplicate identity) and integrity (release kernel ≠ installed
kernel, unauthorized receipt recording). **Unresolved code identity withholds reuse and never
refuses service** (§2.4 item 4). An older release now refuses explicitly, where today the outcome
depends on whether the release has pattern constraints (§0.1). Re-preparation answers it.

## 11. Open premises

| ID | Premise | Settles it |
|---|---|---|
| C1 | The slicer resolves PDF lowering and served-read entries without unknowns | Run `implementation_slice` per entry in package 4 |
| W1 | Role-granular watermark soundness | Enumerate binding/population read sets (registry model inputs) against components |
| D1 | DA-075 content basis per query | Native owner's per-program read-row field argument (§6) |
| T1 | Operator trust decision for carried release proof | Accepted with RC08; record it in the ADR |
| B1 | Registry renders byte-identically to N29 | Acceptance 1; if not, package 3 carries a revision and is batched with 5 |
| P1 | No consumer needs pre-transition releases to keep running | Operator confirmation (memory: data regenerable) |
| X1 | Collecting callees from typed bodies covers SQL-language provider binding | Topological install of the registry against an empty authoring database |

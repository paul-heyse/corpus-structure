# Execution fit

**Interface-checked by source inspection.** The page was read as a whole on 2026-11-17 at
source `fbd3f2a98` ([baseline and limits](README.md#baseline)). Every finding that carries a
"Refresh, 2026-11-18" paragraph was re-read at source `d78c98765`
([refresh](README.md#refresh-2026-11-18)), and DA-082 and DA-083 were established there; text
without such a paragraph keeps its 2026-11-17 date. Source paths omit
`python/corpus-structure/src/corpus_structure/`; `sql/` means `semantic/sql/`. Nothing on this
page is a measured latency, throughput or memory claim: each finding states work that is
unnecessary or amplified by structure. The integrated view of these findings with the domain
model and the test account is on the [joint page](model-and-execution.md).

Findings of the [production-efficiency review](../reviews/design_review_production-efficiency_2026-11-17.md)
keep their `PE-Fnn` identities and their disposition in the
[DDO plan](../../plans/declared-data-operations_2026-11-12.md). Where one of them is only
partly realized in source, that is recorded on the
[joint page](model-and-execution.md#pe-state), not as a new finding here.

The hand-written file `semantic/sql/data_operations.sql`, which the 2026-11-17 text cited, was
deleted in commit `2910d9817`. Its programs are now produced by generator modules named
`semantic/*_native.py`, and the citations below name the generator that holds each fact.

<a id="da-068"></a>

## DA-068 — One digest over every captured native source keys admission, read acquisition and carried assurance

**Refresh, 2026-11-18, source `d78c98765`.** Stands, and wider again. The capture now holds
about 75 to 85 whole Python modules (57 `read_bytes` sites in
`semantic/data_operation_storage.py`, against 45 at `1afa63f88`), the generated SQL of about 45
programs, the physical model closure and the installed versions of six libraries. Two further
uses of the digest were confirmed, so there are seven. The cited SQL file is gone and the body
below names the generators. Thirty commits touched the storage module in
`1afa63f88..d78c98765`. The absence of a holder and of file custody for the capture is its own
finding, [DA-083](#da-083).

**FP-04/A2, FP-07/A4; DP-04, DP-08, DP-09, DP-10, DP-19; H18, H19.**

`native_source_digest()` hashes every captured `native/*` source
(`semantic/data_operation_storage.py:703–713`). The capture (`:48–567`) is much wider than the
installed kernel. It holds, whole, the bytes of each generator module beside the SQL that
generator produced (`:184–191`), twelve binding modules and the whole
`data_operation_model.py` (`semantic/data_operation_binding_native.py:30–53`), wire,
operation-event, source, search and projection helpers, the physical YAML closure and LinkML
types (`semantic/data_operation_projections.py:2463–2470`), three logical model files
(`data_operation_storage.py:41–45`), and the installed versions of pglast, sqlalchemy,
linkml-runtime (`:206–214`), networkx (`:537–546`), docling-core and docling
(`semantic/pdf_source_search.py:63`). That one digest is then used as identity in seven places:

1. it is spliced into the generated SQL in place of `__DDO_SOURCE_DIGEST__`
   (`data_operation_storage.py:804`) and the installed descriptor is required to equal the
   digest of the current checkout on every `require_data_operation_native` (`:1116–1131`);
2. release admission compares the archived projection's `native_digest` with the installed
   descriptor (`semantic/data_operation_compiler_native.py:998–1093`; `sql/admission.sql:46`);
3. it is stamped on each demand read (`semantic/demand_result_native.py:209`), and a read
   acquired under another kernel is treated as not present
   (`semantic/data_read_boundary_native.py:84–92`);
4. it is part of the completion seal that publication compares before skipping its battery
   (`semantic/data_completion_settlement_native.py:509–528`);
5. it is each receipt's `validating_kernel_digest` (`semantic/data_derivation_native.py:614`);
6. each native protocol operation declares its `behavior` as `"ddo-native-v1:"` followed by
   the digest (`data_operation_storage.py:982`), so every native operation definition, and
   with it that operation's recipe, changes with the digest;
7. it is a component of the readiness watermark
   (`semantic/data_operation_projections.py:1932`; [DA-078](#da-078)).

The capture is also part of the release identity: the release id hashes every dependency
artifact digest (`semantic/prepare.py:956–985`), and preparation passes the whole native
capture as dependencies (`semantic/data_operation_preparation.py:261–271`;
`semantic/primary_operations.py:403–413`; `semantic/native_products.py:109–118`).

`ops.ddo_require_episode_correspondence` runs the complete original-producer completion
battery whenever a receipt's digest differs from the current one
(`semantic/data_completion_settlement_native.py:661–676`). The routine is declared stable
(`:685`), so it cannot write and does not record that the replay succeeded. Seven family
dependency validators call it inside validity evaluation
(`contextual_admission_native.py:226`, `definition_admission_native.py:129`,
`operation_event_native.py:409`, `record_grade_native.py:709`,
`record_policy_completion_native.py:595`, `artifact_admission_native.py:58`,
`rich_admission_native.py:483`).

**Consequence.** An edit that changes no native behavior (a docstring in a captured module, an
unrelated generator) changes the digest, and so does a patch release of sqlalchemy, pglast,
linkml-runtime, networkx or docling even when every generated byte is identical. The
comparison is between the checkout's capture and the installed descriptor, so the trigger is a
working-tree edit, not a deployment. From then on:

- every port acquisition, cached-port recheck, publication-port acquisition and definition
  admission refuses until a new native revision is authored and deployed
  (`semantic/data_operation_admission.py:285, 354, 390`; `data_operation_storage.py:1548`);
- the release id changes, so releases must be prepared and admitted again;
- every historical episode in those seven families re-runs its full battery on each validity
  evaluation that reaches it. Validity is not cached across statements, and by search nothing
  other than publication writes a receipt's digest, so this continues until receipts are
  rewritten;
- every read is reacquired and every waiting obligation's watermark advances;
- if the edited module is also on the PDF lowering list ([DA-082](#da-082)), PDF certification
  refuses as well.

The chain is established from source; how often it occurs and the volume of replayed episodes
are not. The assurance being protected depends on the validator code that ran. The key covers
far more than that.

**This is a documented choice, with one divergence from the plan.** The plan chose the kernel
digest for the seal on the premise that it "covers every completion-validator body", and
specified that a differing or absent digest "runs the full battery as today"
(`docs/plans/declared-data-operations/products-and-support.md:428, 528, 534`; plan lines as
read on 2026-11-17). What the plan did not weigh is that the digest covers many other modules
as well, or what the replay costs over time. The plan also said the producer replays inside
the dependency validators would leave validity and be recorded under the kernel digest
(`:466–469`). In source they remain inside validity, gated on the receipt digest, and their
outcome is not recorded. Several validators say in their own comments that they intend no
replay on support reads (`contextual_admission_native.py:220–222`;
`artifact_admission_native.py:59–61` and `definition_admission_native.py:130–131` as read on
2026-11-17); the digest gate brings it back after any kernel change.

**Contrary evidence and what to keep.** Capturing generator source makes candidate authoring
attributable (CI-11), and the capture fails closed. Replaying under changed validator code
protects a real premise. The capture's required-set check and its equality check between the
projection and the physical model are sound (`data_operation_storage.py:569–692`). A finer
identity already exists beside this one and is not used for keying: the exact generated bytes
of each program are captured as `native/<name>.sql` beside the generator (`:184–191`), and
`__DDO_LOWERING_DIGEST__` is already the digest of one generated file,
`native/data-operation-compiler.sql` (`:805–808`). The per-program bytes would separate "the
generated SQL changed" from "a generator module or a library changed".

**Footprint.** Established for the mechanism and the seven uses. How often it bites, and the
volume of replayed episodes, are not measured.

**Lead.** Separate provenance (what was captured) from identity (what is installed and what
validated a result), and record a successful replay.

<a id="da-069"></a>

## DA-069 — Implementation identity of source-level operations takes whole files, whole model files and library versions through opaque boundaries

**Refresh, 2026-11-18, source `d78c98765`.** Stands unchanged. No commit in
`1afa63f88..d78c98765` touched `semantic/formal_products.py`,
`semantic/characterization_ports.py` or `semantic/python_operation_sources.py`. Current sites:
construction assets at `semantic/characterization_ports.py:47–193`; formal assets at
`semantic/formal_products.py:688–756`, with the module's own slicing at `:723–744`. One
addition: `formal_execution_custody` captures whole `formal_products.py`,
`established_validity.py`, `cpu_execution.py` and `cpu_receipts.py` (`:676–686`) and is passed
as a boundary contract (`:771`); whether it enters the implementation revision or only runtime
custody was not traced.

**FP-04, FP-07; DP-04, DP-09; H13.**

The compiled model gives each operation an implementation-slice fingerprint over the normalized
source of what it calls. Operations can also declare an opaque boundary whose digest is folded
into that fingerprint (`semantic/python_operation_sources.py:941–973`), and native completion
requires the implementation revision to equal the definition's
(`semantic/data_completion_settlement_native.py:935`;
`semantic/data_derivation_native.py:371–372`).

For the construction and formal families the opaque artifact is coarse:

- `characterization/construction-assets` hashes whole files (`established_validity.py`, the
  characterization modules, nine construction modules including `navigation.py`,
  `retained_rules.py`, `forest.py` and `layers.py`, `methods/annotation_rules.py`,
  `ingest/annotation_views.py`), rule JSON, the prose grammar, the entire
  `model/semantic/data-operation-constructions.yaml`, and the installed versions of `lark`,
  `pydantic` and `spacy` (`semantic/characterization_ports.py:47–193`);
- `formal/profile-assets` does the same for twelve whole module files (among them
  `source_products.py`, `characterization.py` and `established_validity.py`), the math grammar,
  transform and TeX modules with the shipped and extension grammars, three model YAML files and
  the `lark`, `sympy` and `pydantic` versions (`semantic/formal_products.py:688–756`).

The finer mechanism sits in the same function: `formal_products.py` itself is sliced to
selected definitions (`:723–744`) while its sibling modules are captured whole.

**Consequence.** An unrelated edit (a helper in `source_products.py` used by another operation,
another product added to the constructions YAML, a patch release of pydantic) changes the
formal or construction implementation revision, so their prior derivations cannot be reused.
Formal is at the root of the characterization chain for the book workload. The plan intends
propagation to stop at an equal admissible value and support
(`docs/plans/declared-data-operations/implementation-contracts-and-fingerprints.md:279–280`);
whether it does was not traced in source.

**Contrary evidence.** The plan explicitly permits "an explicitly coarse module boundary" and
accepts conservative recomputation after some harmless refactors
(`docs/plans/declared-data-operations/implementation-contracts-and-fingerprints.md:258–283`).
Whole-file capture also covers JSON rule files and grammars that slicing cannot see, and
adapter and receipt code is deliberately kept out of recipe meaning. The rich assets use a
finer identity, a projection of the module's parsed meaning
(`semantic/python_module_projection.py:111–120`), which shows the alternative is in use. This
is over-invalidation, not unsoundness.

**Footprint.** Established for the capture; the downstream extent is likely, not established.

<a id="da-075"></a>

## DA-075 — Five of six selected-query cache keys include the acquisition instance, so identical fresh requests do not share an entry

**Refresh, 2026-11-18, source `d78c98765`.** Stands unchanged. No commit touched the key
sites. Keys were re-read at `serve/rich_queries.py:225`, `serve/contribution_facets.py:263`,
`serve/interpretations.py:207`, `serve/structural_products.py:282` and
`semantic/demand_queries.py:200–213`. The read instance is now minted by generated code
(`semantic/demand_result_native.py:189`; snapshot and clock at
`semantic/demand_registration_native.py:803–804`). The sub-point that four consumers page the
frontier twice was not re-read.

**FP-07/A4; DP-09, DP-10; H12, H19.**

Five of the six cached serving paths include `cut.identity` in the key of
`SELECTED_QUERY_CACHE`: `serve/rich_queries.py:225`, `serve/contribution_facets.py:263`,
`serve/interpretations.py:207`, `serve/structural_products.py:282` and
`semantic/demand_queries.py:200–213`. The sixth, identity-exclusion comparison, keys on the
implementation, the selection and content stamps of the frontier rows, which carry no read
identity (`serve/identity_exclusion_comparison.py:155`; `semantic/demand_results.py:350–354`).
`CutSelection.identity` is the SHA-256 of every pin, including `read_id`, `read_snapshot` and
`frontier_at` (`semantic/demand_results.py:64–104`). A request without a `read_id` makes native
acquisition mint `read:` followed by a random UUID, the current snapshot and the clock time
(`semantic/demand_result_native.py:189`; `semantic/demand_registration_native.py:803–804`).

**Consequence.** For those five paths, two identical requests against an unchanged database get
different keys. A hit can only come from a continuation page, a `resource_handle` replay or an explicitly pinned
re-request, and only inside one long-lived MCP server process. The `ci` CLI runs each page in a
new process (`cli/selected_results.py:96–130`), so it never hits, and the replay cost the cache
was added to remove (PE-F17) remains for CLI paging. On each miss the request re-reads support
into a new temporary index, reopens the release, binds the model and re-validates the graph
(`serve/rich_knowledge.py:118–130`; `semantic/demand_results.py:431–473`).

Two related repetitions share the miss path:

- four consumers page the whole frontier in `recheck_selected_frontier` and then page it again
  under the same read in `selected_record_index`
  (`serve/contribution_facets.py:248–270`; `serve/selected_contributions.py:353–367`;
  `semantic/demand_results.py:401–461`);
- `byte_bounded_page` rebuilds the full report envelope once per accepted row
  (`semantic/selected_query_cache.py:189–200`), and rich entries store the cumulative
  `unknowns` list in every cached row (`serve/rich_queries.py:246–251`), so entries reach the
  8 MiB cap sooner.

**Contrary evidence and what to keep.** Keying on the read makes reuse trivially safe: frontier,
trust snapshot and visibility are fixed. Every request, hit or miss, rechecks native authority
first, and a revocation between pages refuses. The cache itself is well built: byte-accounted,
bounded by entry and row count, immutable encoded entries, a fresh copy on each hit.

**Open premise, already relied on once.** Four consumers compute a content stamp of the
frontier on every request; three then add the cut identity on top of it, and the exclusion
comparison keys on the stamp alone, so within one process its identical fresh requests can
hit. Whether (frontier stamp, release, runtime, selection, implementation) fully determines
the derived rows depends on whether whole-read support visibility is a function of frontier
content. Either that holds at least for product-scoped exclusions, or the exclusion path is
keyed too loosely. The native owner has to settle which.

**Footprint.** Established for the key composition and the two repetitions; how often agents
repeat identical requests is unknown.

<a id="da-078"></a>

## DA-078 — The readiness watermark is coarser than the declared role dependencies

**Refresh, 2026-11-18, source `d78c98765`.** Stands. The watermark is now built by
`_inputs_watermarks` at `semantic/data_operation_projections.py:1809–1935`: it digests the
fulfilled uses of every transitive prerequisite operation with the same original source
(`:1821–1857`), relevant populations, every visible original admission for the demand
(`:1892–1901`), the source sets, and the whole trust snapshot and kernel digest
(`:1927–1935`). The kernel component, which the 2026-11-17 delta marked as inferred, is now
established. The skip is at `semantic/data_operation_demands.py:732–738`.

**FP-07/A4; DP-08, DP-10; H5.**

The planner skips re-binding a waiting obligation only when its inputs watermark is unchanged
(`semantic/data_operation_demands.py:732–738`). `_inputs_watermarks` digests, for each waiting
obligation, every fulfilled use of every transitive prerequisite operation with the same
original source, regardless of subject or scope, together with the whole read trust snapshot
and the kernel digest (`semantic/data_operation_projections.py:1809–1935`).

**Consequence.** In the one-book workload every obligation shares one original source, so any
upstream publication advances every waiting obligation's watermark and each round re-binds all
of them. The waiting-obligation skip that PE-F06 intended is then largely unrealized for that
workload. The model declares which roles each operation consumes and from which producers; the
watermark does not use it. Because the kernel digest is a component, every kernel change
([DA-068](#da-068)) also advances every watermark.

**Contrary evidence.** This granularity is the plan's specification: the watermark is "the
latest visible fulfilled use, population or original among its prerequisite operations and
exact pins" (`docs/plans/declared-data-operations/products-and-support.md:574–575`), with a
soundness argument in `demand-planning-and-execution.md:688–692`. Binding is the authority, so
a conservative watermark cannot admit a wrong result, and an unchanged repeat run still ends
after one round. What the plan text does not weigh is the one-source workload, or that folding
in the whole trust snapshot makes any trust-epoch change advance every watermark.

**Footprint.** The key composition is established. The skip rate in the book run is likely, and
rests on that run's subject and source granularity.

<a id="da-033"></a>

## DA-033 — Admission and binding re-prove immutable release content that earlier steps already established

**Refresh, 2026-11-18, source `d78c98765`.** Changed footprint; the substance stands. The
release preconditions are now generated (`semantic/native_admission_release.py:13–28`,
commits `f52742977` and `c1a2cdcbc`) and the binding check is a typed program (`b1c10cbbf`),
but each performs the same re-proof. The hand-written files `sql/execution_projection_check.sql`
and `sql/data_operation_bindings.sql` that the earlier text cited no longer exist, and the body
below names the generators. The repeated rebuild of the Python native capture, which this
finding used to mention, is now homed in [DA-083](#da-083), because its cause is a derived
artifact with no holder, not assurance that is not carried.

**FP-07/A4; DP-10, DP-19; H12, H18, H19.** Changed footprint; the 2026-11-03 question was
whether cumulative assurance work was avoidable. The publication scans cited then are gone.
The current form is narrower and established.

`data.require_execution_release` runs on every `require_native_execution` call: each port
acquisition, cached-port recheck, publication-port acquisition, definition admission and
activation (`semantic/execution_admission.py:196–221`; `semantic/data_operation_admission.py:285, 354, 390`;
`semantic/releases.py:568–619` as read on 2026-11-17). Before it reaches its catalog checks it:

- checks that the finalization row exists and then performs `sem.require_execution_projection`
  (`semantic/native_admission_release.py:13–28`), which parses the prepared archive and the
  registry again (`semantic/archive_projection_native.py:114–264`);
- inside that, performs `sem.require_archive_bytes` (`archive_projection_native.py:264`), which
  hashes every input and artifact (`sql/closure.sql:36–77`);
- parses the archive again for diagnostics (`sql/admission.sql:20–24`) and reads the archived
  projection (`:40–60`).

Archive publication already ran the first two and wrote `sem.release_finalization`; admission
records `sem.deployment_admission` for the release, physical id and descriptor digest, and
records it only if absent (`semantic/native_admission_release.py:31–67`). Both receipts are on
this path: the precondition checks that the finalization row exists immediately before it
starts the re-proof. Neither short-circuits the re-proof. The 2026-11-17 observation that the
inspection path runs the full check twice in one transaction
(`semantic/data_operation_admission.py:147`) was not re-read.

The same pattern recurs per obligation: `ops.ddo_require_binding` reads, parses and hashes
`data_operations.json` and parses the native definitions projection for every call
(`semantic/binding_admission_native.py:232–251`), and population selection repeats it
(`semantic/population_acquisition_native.py:906–921`). The admitted
`sem.data_operation_definition` rows already hold the binding expression and identities.

**What is not in question.** The catalog half of admission (functions, triggers, tables, ACLs,
indexes; `sql/admission.sql:123–186`) guards against deployment drift, which is a live premise.
The per-call kernel paths that carry facts instead of re-proving them are sound
(`ops.ddo_require_release_facts`, `require_pdf_operation`, `require_runtime_binding`; not
re-read on 2026-11-18).

**Open decision.** Re-hashing would detect tampering by an owner or superuser. The design
already trusts definer roles (DA-029), so whether that premise justifies per-acquisition
re-proof of content protected by immutability triggers is an owner decision about trust.

<a id="da-058"></a>

## DA-058 — Visual recognition re-prepares its runtime every four packets

**Refresh, 2026-11-18, source `d78c98765`.** Stands unchanged. No commit in
`1afa63f88..d78c98765` touched `semantic/visual_requests.py` or `ingest/pdf_chandra.py`, so the
cited lines hold. Chandra remains outside scope by operator direction.

**FP-07/A4; DP-10; H2, H12, H24.** Changed footprint. The 2026-11-08 manifestations (page
render and original-PDF open per group) are gone: the image is a packet input and a retained
attempt result is reused before inference (`semantic/visual_requests.py:360–378, 439–462`).

The current form: `execute_visual_demand` loops up to 100 rounds; each round runs a full demand
sweep, takes `session.queue(limit=4)` packets and creates a new `_LocalChandraGroup` whose
lifetime is that round (`visual_requests.py:697–710`). Building `ChandraRuntime` hashes every pinned checkpoint file in full
(`ingest/pdf_chandra.py:50–68, 152–157`); the model load, the PDF GPU slot and the Nemotron
suspension follow on the group's first recognition (`visual_requests.py:475–512`).
Without a group, the runtime (including the checkpoint hash) is built before the check for a
retained result (`:583` against `:597`). Checkpoint hashing does not use the process file
custody that other model assets now use.

**Consequence.** Every round re-hashes the checkpoints, and a round that needs any inference
also pays model load, slot acquisition and the service handoff, so these recur about once per
four packets. One invocation covers at most about 400 packets.

**Limits.** Whether the round size of four is deliberate (GPU memory) was not established.
Chandra OCR is outside the current DDO scope by operator direction; this is recorded as the
state of the code, not as scheduled work.

<a id="da-082"></a>

## DA-082 — The PDF lowering identity is a hand-kept file list with no completeness check, at once too narrow and too broad

**FP-04; DP-04, DP-09; CI-10, CI-11; H18.** Established in the refresh of 2026-11-18 at source
`d78c98765`. **Interface-checked by source inspection, 2026-11-18.**

"Lowering" here means turning PDF records into their stored and transported forms. The code
that does it is identified by `LOWERING_FILES`, a hand-written tuple of 70 paths (64 Python
modules, five model YAML files and one JSON schema; `semantic/pdf_lowering.py:33–104`), with
fourteen library names beside it (`:15–30`, among them sqlalchemy, pglast, pyarrow, linkml and
pydantic). The comment above the tuple calls it an "explicit runtime responsibility closure"
(`:31–32`). The list had 58 entries at `1afa63f88`, and ten commits touched the file in
`1afa63f88..d78c98765`.

The list decides an identity with several consumers. The lowering contract
`implementation/pdf/lowering-contract.json` records the digest of every listed file, the
generated JSON schemas and Arrow codecs, the PDF boundary sources and the library versions
(`:243–256`). The contract enters the release through `pdf_domain_sources`
(`semantic/pdf_domain.py:144–147`), so it is part of the release id, and its digest is each
receipt's `lowering_identity`. `require_lowering_identity` (`:276–310`) refuses when current
metadata differs from the boundary ("restart required", `:300`) or when the recomputed
contract differs from the released one (`:303`). It is called by PDF stream production
(`orchestrate/pdf_streaming.py:666`), by the producer contract used in certification
(`semantic/pdf_certification.py:76`) and by published-oracle capture
(`semantic/pdf_publication.py:1276`).

Nothing establishes that the list is complete. No derivation, import-closure comparison or
coverage test was found; the tests read exercise the equal path and a tampered artifact
(`tests/semantic/test_pdf_lowering_contract_inputs.py`;
`tests/semantic/test_pdf_producer_certification.py:137–170`).

**Consequence.** The identity is wrong in both directions.

- *Too narrow.* The listed `semantic/pdf_staging_native.py` appends the SQL produced by
  `pdf_spool_native_sql()` from `semantic/pdf_spool_native.py` (`pdf_staging_native.py:168–170`),
  and that module is not on the list. `semantic/pdf_domain.py`, which supplies the PDF call
  bindings to listed modules (`pdf_publication_native.py:415`, `pdf_domain_native.py:24`,
  `pdf_observation_native.py:53`), is not listed either and does not capture its own bytes. An
  edit to either does not change the lowering identity. For `pdf_spool_native.py` the edit
  changes deployed SQL, so its effect on produced work arrives through native deployment,
  whose own identity was not examined for this module; the established statement is only that
  the lowering identity does not move.
- *Too broad.* Shared infrastructure is listed whole (`semantic/native_program.py`,
  `schema/relational.py`, `schema/physical.py`, `semantic/metadata.py`, `semantic/identity.py`,
  `semantic/prepared_sql.py`). An unrelated edit there, or a patch release of any of the
  fourteen libraries, refuses PDF production, certification and oracle capture until a new
  release is prepared. The same files are in the native kernel capture
  ([DA-068](#da-068)), so one edit invalidates both identities together.

**Contrary evidence.** The list is labelled as a deliberate closure. Custody is sound: each
listed file is read through verified file custody with a stat recheck (`:107–165, 259–273`), so
a process whose files changed underneath it refuses instead of mixing code; contract bytes are
compared in full; retained sources are re-hashed against the contract. The two omissions were
found by reading call sites, not by a systematic closure, so further omissions are possible
and none is established.

**Footprint and uncertainty.** Established for the list, the two omissions and the refusal
paths. How often a refusal occurs is unknown. This is not a manifestation of DA-068 (a
different identity with different consumers), of [DA-069](#da-069) or of
[DA-076](served-claims.md#da-076) (served reads), although all four are hand-kept answers to
"which code determines this artifact". The closest sibling of the too-broad half is DA-069,
which also takes whole files and library versions as an implementation identity.

**Lead (not a selected remedy).** The compiled model already derives an implementation slice
for Python operations (`semantic/data_operation_identity.py:378–414`); no comparable derived
owner exists for PDF lowering.

<a id="da-083"></a>

## DA-083 — The native source capture has no holder and no file custody

**FP-07/A4; DP-10; CI-11; H12.** Established in the refresh of 2026-11-18 at source
`d78c98765`. **Interface-checked by source inspection, 2026-11-18.** Costs below are counts of
rebuilds read from call paths, not timings. Lineage: the sentence in [DA-033](#da-033) about
the native closure being rebuilt uncached moved here.

The native capture is the set of artifacts returned by `native_protocol_sources()`
(`semantic/data_operation_storage.py:48–567`). Building it runs about 45 SQL generators,
compiles the physical LinkML model when none is supplied (`:123–136`; `compile_physical` is
uncached, `schema/physical.py:166–199`, and the identical module-level metadata of
`semantic/metadata.py:33` is not reused), builds a further LinkML schema view for source
values (`semantic/source_value_native.py:56`), renders every program with one parse per
statement, and reads about eighty files from disk. Nothing holds the result.

The capture is rebuilt on every use that passes no sources:

- `require_data_operation_native` builds it twice per call, once to compare with the installed
  descriptor and once for the return value (`data_operation_storage.py:1128, 1131`). That
  function runs at each Python port acquisition (`semantic/data_operation_admission.py:285`,
  reached once per operation per execution context from `orchestrate/data_operations.py:698–757`),
  at each cached-port recheck (`data_operation_admission.py:354`;
  `orchestrate/data_operations.py:782–785`) and at each publication-port acquisition (`:390`);
- definition admission builds it three times, twice through that function and once more for
  its own return value (`data_operation_storage.py:1548, 1558`);
- each preparation builds it (`semantic/data_operation_preparation.py:261`;
  `semantic/primary_operations.py:403`; `semantic/regeneration.py:331`), as do candidate
  definitions (`data_operation_storage.py:1844`);
- a demand export rebuilds the whole capture to read one wire schema
  (`serve/demand_export.py:281`);
- one model-change preview reaches a full rebuild at least twice (`schema/model_change.py:603`
  and the facade rendering at `:525–552`), and a third time if the compilation fingerprint
  runs in the same command (as reported by the generator lane; the third was not traced here).

So the execution path, not only authoring, runs the generators: a run that touches N
operations performs at least two full captures per operation at port creation, and two more
for each operation whose cached port is rechecked.

The capture also has no custody. Each program's SQL is produced by the generator objects that
the process has already imported, while the module bytes recorded beside it are read fresh
from disk (`data_operation_storage.py:184–191`). Unlike the PDF lowering list and query
custody, nothing refuses when the two differ.

Two adjacent facts share the cause. The wire protocol's caches key on the whole captured
source tuple (`semantic/data_operation_wire.py:46–485`), so a freshly rebuilt capture hits
only after every artifact's bytes are hashed and compared (inferred cost). And
`semantic/metadata.py:32–50` reads the physical closure and compiles two metadata projections
at import, in every process that imports it.

**Consequence.** The cost of every admission-side call scales with the size of the converted
kernel, and it grew with the conversion work: before it, the capture read hand-written SQL files;
now it runs about 45 generators and a LinkML compile per rebuild. In a long-lived process
after an edit, the captured module bytes and the generated SQL come from different code.
Admission then refuses, which is fail-closed, but a preparation run inside such a process
would record a capture that is not hermetic (CI-11).

**Contrary evidence.** Rebuilding from the checkout is what makes the descriptor check track
working-tree edits, which the design wants as a signal to restart or redeploy. Read
acquisition does not reach the generators. Deployment reads frozen payloads and imports no
generator (`semantic/native_objects.py:1–5`). The wire protocol's content-keyed caches are
sound. `ci model change` runs in a fresh process, so the mixed-code case needs a long-lived
process that prepares.

**Footprint and uncertainty.** The call sites and the absence of a holder and of custody are
established. Call counts per run, the time of one rebuild and whether preparation ever runs in
a long-lived process were not established.

**Lead (not a selected remedy).** A holder would need the file-custody pattern that the
lowering list already uses (`semantic/pdf_lowering.py:107–165`), so that a held capture is
refused when its files change.

## Prior identities on this page

<a id="da-024"></a>
<a id="da-025"></a>
<a id="da-042"></a>
<a id="da-043"></a>
<a id="da-054"></a>

Earlier text for these is in Git at the publication before this refresh (`fbd3f2a98`).

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-024 | No longer applicable | `semantic/publication.py` is gone; publication is `ops.publish_data_derivation` and PDF validate/seal |
| DA-025 | No longer applicable | Unchanged from 2026-11-03: legacy rendition keying is not on the current path. The unused machinery itself is [DA-080](boundaries-and-composition.md#da-080) |
| DA-042 | Changed footprint | The cited readers are gone. Read paths use `open_release` (PE-F03 implemented). Execution still derives the release at registration and once per host basis, which the production-efficiency review records as a deliberate verification boundary |
| DA-043 | Not re-examined | Last evidence 2026-11-04; consolidation was outside this refresh |
| DA-054 | No longer applicable | The task-dependency projection is gone. Reuse is now keyed by the semantic request identity, which excludes release and runtime. The successor granularity question is DA-078 |

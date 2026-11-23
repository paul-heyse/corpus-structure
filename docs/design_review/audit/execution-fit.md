# Execution fit

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`
([update](README.md#update-2026-11-18-5139eaba3); [baseline and limits](README.md#baseline)).
Every finding on this page was re-read at that source and carries an "Update, 2026-11-18"
paragraph that states its status. Body text was corrected where the cited code moved; a
sentence that keeps an earlier date says so. Source paths omit
`python/corpus-structure/src/corpus_structure/`. Nothing on this page is a measured latency,
throughput or memory claim: each finding states work that is unnecessary or amplified by
structure, and every count of repeated work is read from call paths. The integrated view of
these findings with the domain model and the test account is on the
[joint page](model-and-execution.md).

Findings of the [production-efficiency review](../reviews/design_review_production-efficiency_2026-11-17.md)
keep their `PE-Fnn` identities and their disposition in the
[DDO plan](../../plans/declared-data-operations_2026-11-12.md). Where one of them is only
partly realized in source, that is recorded on the
[joint page](model-and-execution.md#pe-state), not as a new finding here.

Native programs are produced by generator modules named `semantic/*_native.py`. The directory
`semantic/sql/`, which text before 2026-11-18 cited, no longer exists
([DA-084](boundaries-and-composition.md#da-084)).

<a id="da-087"></a>

## DA-087 — A population's tagged document controls native, worker and point-read work

**Interface-checked by source inspection, 2026-11-23**, source `cc05ce725`.
[Scoped baseline and limits](README.md#refresh-2026-11-23-sbx-populations).
**FP-03, FP-05, FP-07/A4; DP-08, DP-10, DP-19; H5, H7, H8, H10, H15, H16, H19.**

The model already gives populations collection, partition, field-group and address semantics.
The physical and interchange unit is nevertheless one tagged document per partition. A caller
or consumer that needs item fields generally expands that document and constructs a local
representation. The representation is meaningful for exact heterogeneous values, but its
boundaries force repeated preparation across the supported producer-to-consumer path.

**Current mechanism.** The physical declaration stores `body` on
`kb.data_product_partition`, indexed by product, collection and partition order
(`model/semantic/data-operation-physical.yaml:295–313`). Construction computes a canonical
partition digest and separately tags its items. Field-group construction projects each declared
group and canonicalizes the projected collection (`semantic/data_operation_partitions.py:116–148`).
Decoding the tagged value reconstructs the Python value and re-encodes it to reject
noncanonical representations (`semantic/data_operation_value_codec.py:17–24`).

- Native partition admission normalizes the submitted partition, verifies its digest and
  schema-checks its items. Field-group evaluation expands the body into rows and resolves each
  declared path through the tagged mapping (`semantic/data_operation_partition_native.py:115–211`).
  Declared rule evaluation independently expands stored `body[1]` for its source rows
  (`semantic/data_operation_rule_native.py:476–506`). A single native transaction gives
  atomicity, while these forms still repeat representation preparation for their queries.
- Hydration fetches and serializes JSON and meaning bodies before constructing the consumer
  value, then acquires selected partition packets, recomputes the headers and serializes those
  packets for `PartitionedInput` (`semantic/data_operation_consumers.py:313–436`). The callable
  adapter can reconstruct the complete population value again in either its JSON or Python
  route (`semantic/data_operation_ports.py:829–857`).
- Prepared CPU submission serializes each argument through its adapter into a JSON string
  embedded in the outer packet. Worker acceptance parses or validates those strings again
  (`semantic/data_operation_cpu.py:117–142,421–451`). The CPU ownership and request/reply
  seals protect real process-boundary failures. This carrier still reconstructs a document
  even when the following transformation requires only columns or selected fields.
- A selected item reference authorizes the exact parent on every access. The first lookup
  acquires the whole selected partition, decodes every item and builds its address index,
  then returns a deep copy of the selected item (`semantic/reference_resolution.py:177–203`;
  `semantic/live_reference_resolution.py:130–155`). Whole-population work therefore occurs
  on a point lookup even when the parent, partition and exact item key are known.
- Selected export writes JSON records through a scratch index and a closure JSONL file.
  Parquet output reloads those records into Python dictionaries before constructing Arrow
  batches (`serve/demand_export.py:352–419`). The detached verifier reconstructs the selected
  index from closure JSONL (`:552–561`). Existing typed relations do not carry those consumers
  through the complete path.

**Consequence.** Preparation scales with all items in the acquired partition, the declared
field groups and later consumers even where the answer is one item or a compact set fact.
The same population can coexist as tagged bytes, parsed tagged trees, decoded mappings and
per-consumer indexes. `_sentence_partition_body` retains both frozen tagged values and decoded
row mappings while its weight counts encoded lengths (`semantic/sentence_partitions.py:79–97`).
The code establishes the different live representations and the accounting basis. It does
not establish the actual retained footprint. Protective byte bounds still serve their declared
failure boundary, but they do not remove the preceding expansion or repeated representation
work. This cause differs from the broad invalidation determinant in [DA-068](#da-068) and
immutable release revalidation in [DA-033](#da-033).

**Contrary evidence and required semantics.** The generic tagged carrier supports dynamic
collection declarations, exact values and canonical identities. Independent native admission
protects against forged producer values. Per-use authorization, missing-versus-withheld standing,
proof establishments, item order and multiplicity remain necessary. The implementation already
has useful narrower mechanisms: selected partition keys, an invocation-owned acquired carrier,
completion-local rule-premise preparation, and a same-transaction Arrow COPY path
(`semantic/established_validity.py:71–136`, `semantic/sentence_products.py:1458–1484`,
`semantic/arrow_transfer.py:134–171`). Those improvements remove some repetitions while the
cross-boundary population carrier remains in use.

**Footprint and uncertainty.** Established by current source reading for partition creation,
admission and rule expansion, shared hydration and arguments, prepared CPU transport, selected
item resolution and selected export/replay. No test, database query or probe was run. This
finding attributes structural work. The dominant native cost, lock waits, measured speedup,
memory retained across runs and every provider-specific conversion remain unestablished.
The [SBX coordinator](../../plans/set-based-execution_2026-11-21.md#columnar-redesign-amendment)
owns scheduled correction and closure. A selected replacement must carry the real validation,
identity and custody obligations across all affected consumers.

<a id="da-068"></a>

## DA-068 — One digest over every captured native source keys admission, read acquisition and carried assurance

**Update, 2026-11-18, source `5139eaba3`.** Stands, and wider. Three things changed.

- *The count.* The capture now holds 99 distinct Python modules. The method: list every
  Python module read inside `native_protocol_sources` and the nine capture helpers it splices
  in, then remove duplicate paths (storage 61 read sites, binding 13, search 7, wire 4,
  operation event 3, source 3, original documents 3, visual read 3, projections 1, source
  values 1). The same method gives about 95 at `d78c98765`, so the "about 75 to 85" published
  in the previous refresh was an undercount. Four module names joined in the range
  (`contextual-neighborhood`, `original-document-native`, `source-admission-native`,
  `visual-read-native`); eleven commits touched the storage module.
- *A concrete instance of digest-only churn.* Native revision N29 changed no generated
  statement relative to N28: nine installed objects differ only in digest literals, because
  the kernel digest and a second stamped identity were restamped (below).
- *The shared seal builder did not narrow the key.* Native revision N27 (`b294ab4e2`, frozen
  by `956661772`) introduced one seal builder used by the writer and the checker. The seal's
  `kernel` field is still the whole digest.

One change is an improvement that does not narrow the key: eight generators now receive the
captured physical metadata (`semantic/data_operation_storage.py:251–356`), so their SQL
derives from the captured physical closure and not from metadata compiled at import (CI-11).

**FP-04/A2, FP-07/A4; DP-04, DP-08, DP-09, DP-10, DP-19; H18, H19.**

`native_source_digest()` hashes every captured `native/*` source
(`semantic/data_operation_storage.py:712–722`). The capture (`:48–575`) is much wider than the
installed kernel. It holds, whole:

- the bytes of each generator module beside the SQL that generator produced (`:183–190`; seven
  program modules at `:143–189` and about ninety further artifact lines);
- twelve binding modules (`semantic/data_operation_binding_native.py:39–52`);
- wire, operation-event, source, original-document, visual-read, projection and source-value
  helpers;
- the six Python files and one recipe file of the PDF search renderer
  (`semantic/pdf_source_search.py:29–37`), a further hand list nested inside this one;
- the physical model closure (five imported YAML files reached from `physical.yaml`, plus
  referenced value-set sources, `:124–135`), the LinkML types (`:128`) and three logical model
  files (`:41`);
- the installed versions of six libraries: pglast, sqlalchemy and linkml-runtime (`:207–214`),
  networkx (`:545–552`), docling-core and docling (`pdf_source_search.py:63`).

About 46 generator invocations run per build (37 inside the function by a search for
`_sql(` calls, against 36 at `d78c98765`; the rest are in helpers). That one digest is then
used as identity in seven places:

1. it is spliced into the generated SQL in place of `__DDO_SOURCE_DIGEST__`
   (`data_operation_storage.py:815`), and the installed descriptor is required to equal the
   digest of the current checkout on every `require_data_operation_native` (`:1135–1142`);
2. release admission compares the archived projection's native digest with the installed
   descriptor (`semantic/native_admission_release.py:515–531`;
   `semantic/data_operation_compiler_native.py:1055–1093`;
   `semantic/data_operation_read_native.py:208`);
3. it is stamped on each demand read (`semantic/demand_result_native.py:223`), and a read
   acquired under another kernel is treated as not present
   (`semantic/data_read_boundary_native.py:98, 126`);
4. it is the `kernel` field of the completion seal
   (`semantic/data_completion_settlement_native.py:489–499`), which publication compares before
   skipping its battery (`semantic/data_derivation_native.py:382–394`);
5. it is each receipt's `validating_kernel_digest` (`data_derivation_native.py:614`);
6. each native protocol operation declares its `behavior` as `"ddo-native-v1:"` followed by
   the digest (`data_operation_storage.py:993`), so every native operation definition, and
   with it that operation's recipe, changes with the digest;
7. it is a component of the readiness watermark
   (`semantic/data_operation_projections.py:2189`; [DA-078](#da-078)).

The capture is also part of the release identity: the release id hashes every dependency
artifact digest (`semantic/prepare.py:986`), and preparation passes the whole native capture as
dependencies (`semantic/data_operation_preparation.py:261`; `semantic/primary_operations.py:403`;
`semantic/native_products.py:110`).

`ops.ddo_require_episode_correspondence` runs the complete original-producer completion
battery whenever a receipt's digest differs from the current one
(`data_completion_settlement_native.py:669–672`). The routine is declared stable (`:695`), so
it cannot write and does not record that the replay succeeded. Seven family dependency
validators call it inside validity evaluation (`contextual_admission_native.py:752`,
`definition_admission_native.py:427`, `operation_event_native.py:1366`,
`record_grade_native.py:720`, `record_policy_completion_native.py:1658`,
`artifact_admission_native.py:229`, `rich_admission_native.py:844`).

**What the shared completion digest of N27 is.** `b294ab4e2` factors one seal builder,
`_completion_seal_value` (`data_completion_settlement_native.py:489–499`), used by both
`ops.ddo_completion_seal` (`:519–541`) and the retain-intent insert (`:1042`), and computes
the completion's content digest once for the stored payload digest and the seal. That removes
one definition that could drift and one repeated digest. Nothing seals or gates against a
narrower identity, and publication still recomputes the seal, digesting the content again
(`data_derivation_native.py:383–385`).

**Consequence.** An edit that changes no native behavior (a docstring in a captured module, an
unrelated generator) changes the digest, and so does a patch release of any of the six
libraries even when every generated byte is identical. The comparison is between the
checkout's capture and the installed descriptor, so the trigger is a working-tree edit, not a
deployment. From then on:

- every port acquisition, cached-port recheck, publication-port acquisition and definition
  admission refuses until a new native revision is authored and deployed
  (`semantic/data_operation_admission.py:285, 354, 390`; `data_operation_storage.py:1561`);
- the release id changes, so releases must be prepared and admitted again;
- every historical episode in those seven families re-runs its full battery on each validity
  evaluation that reaches it, until receipts are rewritten;
- every read is reacquired and every waiting obligation's watermark advances;
- if the edited module is also on the PDF lowering list ([DA-082](#da-082)), PDF certification
  refuses as well.

**An instance of digest-only churn in installed objects: N28 to N29.** The frozen revisions
`target_alembic/versions/semantic_ddo_pe_n28_native.json` and `…n29_native.json` were compared
object by object, first by the identity lane and then independently by the challenge of this
update. Each holds 585 desired objects with the same identities and equal privileges. Nine
objects differ, and N29 changed no generated statement: every difference is a digest literal,
and every substitution maps one to one. Two identities were restamped.

- *The kernel digest.* One pair of values in seven functions (the descriptor, read presence,
  read result, publication, the completion seal, episode correspondence and retain intent),
  and the renderer pin in `ddo_pdf_search_pin`. The cause is `477c82762`, which added a
  construction-validation helper to `semantic/native_source_view.py`; that file is captured
  whole as a PDF search renderer input (`pdf_source_search.py:34`).
- *The authoring-source digests in `data.execution_contract_descriptor`.* Four of its 48
  `authoring/*` entries changed (`authoring/native_admission.py`, `authoring/native_authoring.py`,
  `authoring/native_catalog.py` and `authoring/native-fixed-calls.json`), after `1b643e7ed`
  edited those authoring modules. The descriptor's other changed digests are the body hashes
  of the changed functions. The authoring list is the hand list built by
  `capture_native_authoring_inputs` (`semantic/native_products.py:54–170`). It is a second
  provenance digest stamped into a deployed object, beside the kernel digest
  ([identity inventory](model-and-execution.md#identity-inventory), row 30).

The revision had a purpose. The plan describes it: "N29 shares typed catalog verification
framing between rollback-only authoring and deployed checks"
(`docs/plans/declared-data-operations/postgresql-realization-and-retirement.md:459–461`). That
work produced generated output byte-identical to N28's, which is sound evidence that the
catalog-verification conversion preserved behavior. What the instance shows is narrower than
"a revision made to restamp a digest": an authoring edit whose output was identical, and a
Python-only helper edit, each changed installed objects in digest literals only. The kernel
restamp, once deployed, makes every older receipt in seven families replay on validity
evaluation. The identity lane reports that N21 and N25 also changed only digest literals, in
the execution-contract descriptor.

The chain is established from source. Replay volume and the cost of one replay are not
measured. The assurance being protected depends on the validator code that ran. The key covers
far more than that.

**This is a documented choice, with one divergence from the plan.** The plan chose the kernel
digest for the seal on the premise that it "covers every completion-validator body", and
specified that a differing or absent digest "runs the full battery as today"
(`docs/plans/declared-data-operations/products-and-support.md:428, 528, 534`; plan lines as
read on 2026-11-17). What the plan did not weigh is that the digest covers many other modules
as well, or what the replay costs over time. The plan also said the producer replays inside
the dependency validators would leave validity and be recorded under the kernel digest
(`:466–469`). In source they remain inside validity, gated on the receipt digest, and their
outcome is not recorded.

**A decision this bears on (inferred).**
[ADR-0092](../../adr/0092-ddo-operation-authority.md) states "No broad runtime digest is a
recipe fallback" (`:27`). Use 6 above makes each native protocol operation's `behavior`, and
with it that operation's recipe, move with any of 99 modules, which is a broad digest acting as
a recipe determinant. The ADR's separate allowance for "release-bound execution attestation"
covers the seal and the receipts, not the recipe. Whether use 6 is within the decision is for
its owner.

**Contrary evidence and what to keep.** Capturing generator source makes candidate authoring
attributable (CI-11), and the capture fails closed. Replaying under changed validator code
protects a real premise. The capture's required-set check and its equality check between the
projection and the physical model are sound (`data_operation_storage.py:577–700`). Finer
identities already exist beside this one and are not used for keying: the exact generated
bytes of each program are captured as `native/<name>.sql` beside the generator (`:183–190`);
`__DDO_LOWERING_DIGEST__` is already the digest of one generated file (`:816–818`); and the
release carries the native digest it was prepared with (`native_digest_from_dependencies`,
`semantic/prepare.py:1031, 1385`).

**Footprint.** Established for the mechanism, the seven uses and the 99-module count, which
the challenge reproduced by its own static method (95 at `d78c98765`). The N28-to-N29
comparison is established for that pair. How often digest-only churn occurs beyond it, and the
volume of replayed episodes, are not measured.

**Lead (not a selected remedy).** Separate provenance (what was captured) from identity (what
is installed and what validated a result), and record a successful replay.

<a id="da-069"></a>

## DA-069 — Implementation identity of source-level operations takes whole files, whole model files and library versions through opaque boundaries

**Update, 2026-11-18, source `5139eaba3`.** Stands. The construction and formal asset lists
are unchanged apart from a one-line shift (`semantic/characterization_ports.py:48–194`;
`semantic/formal_products.py:692–757`). One hand addition in the range:
`semantic/enriched_document_products.py`, already a whole-file `view` asset (`:78`) and in
execution custody (`:206`), is now also appended by hand as a Python source of the composition
view (`characterization_ports.py:1144–1155`; `67a6e7a51`, after `590b67b7a` and `1fab40234`).
The fact "which code determines the view" is now stated three times. Whether the slicer slices
that module or folds it whole was not traced, and whether `formal/execution-custody`
(`formal_products.py:677–687`) enters the implementation revision or only runtime custody is
still not traced. `FormalEvidenceProduct.semantic_id` became a per-object memo
(`formal_products.py:150`), which is sound.

**FP-04, FP-07; DP-04, DP-09; H13.**

The compiled model gives each operation an implementation-slice fingerprint over the normalized
source of what it calls. Operations can also declare an opaque boundary whose digest is folded
into that fingerprint (`semantic/python_operation_sources.py:941–973`, as read on 2026-11-17),
and native completion requires the implementation revision to equal the definition's.

For the construction and formal families the opaque artifact is coarse:

- `characterization/construction-assets` hashes whole files (`established_validity.py`, the
  characterization modules, nine construction modules including `navigation.py`,
  `retained_rules.py`, `forest.py` and `layers.py`, `methods/annotation_rules.py`,
  `ingest/annotation_views.py`), rule JSON, the prose grammar, the entire
  `model/semantic/data-operation-constructions.yaml`, and the installed versions of `lark`,
  `pydantic` and `spacy` (`semantic/characterization_ports.py:48–194`);
- `formal/profile-assets` does the same for twelve whole module files (among them
  `source_products.py`, `characterization.py` and `established_validity.py`), the math grammar,
  transform and TeX modules with the shipped and extension grammars, three model YAML files and
  the `lark`, `sympy` and `pydantic` versions (`semantic/formal_products.py:692–757`).

The finer mechanism sits in the same function: `formal_products.py` itself is sliced to
selected definitions while its sibling modules are captured whole.

**Consequence.** An unrelated edit (a helper in `source_products.py` used by another operation,
another product added to the constructions YAML, a patch release of pydantic) changes the
formal or construction implementation revision, so their prior derivations cannot be reused.
Formal is at the root of the characterization chain for the book workload. The plan intends
propagation to stop at an equal admissible value and support
(`docs/plans/declared-data-operations/implementation-contracts-and-fingerprints.md:279–280`);
whether it does was not traced in source.

**Contrary evidence.** The plan explicitly permits "an explicitly coarse module boundary" and
accepts conservative recomputation after some harmless refactors (same plan, `:258–283`).
Whole-file capture also covers JSON rule files and grammars that slicing cannot see, and
adapter and receipt code is deliberately kept out of recipe meaning. The rich assets use a
finer identity, a projection of the module's parsed meaning
(`semantic/python_module_projection.py:111–120`), which shows the alternative is in use. This
is over-invalidation, not unsoundness.

**Footprint.** Established for the capture; the downstream extent is likely, not established.

<a id="da-075"></a>

## DA-075 — Five of six selected-query cache keys include the acquisition instance, so identical fresh requests do not share an entry

**Update, 2026-11-18, source `5139eaba3`.** Stands unchanged. No commit in
`d78c98765..5139eaba3` touched `semantic/selected_query_cache.py`, `semantic/demand_queries.py`,
the four serving consumers, `serve/identity_exclusion_comparison.py` or
`cli/selected_results.py`. `semantic/demand_results.py` changed only in detached verification
(`426f64319`, `32ec30618`). The read instance is still `read:` followed by a random UUID
(`semantic/demand_result_native.py:195`). A new boundary field, `public_disclosure`
(`ed410b80f`), was added to the read boundary; whether it enters the cut pins was not traced.
The sub-point that four consumers page the frontier twice was not re-read.

**FP-07/A4; DP-09, DP-10; H12, H19.**

Five of the six cached serving paths include `cut.identity` in the key of
`SELECTED_QUERY_CACHE`: `serve/rich_queries.py:225`, `serve/contribution_facets.py:263`,
`serve/interpretations.py:207`, `serve/structural_products.py:282` and
`semantic/demand_queries.py:200–213`. The sixth, identity-exclusion comparison, keys on the
implementation, the selection and content stamps of the frontier rows, which carry no read
identity (`serve/identity_exclusion_comparison.py:155`). `CutSelection.identity` is the SHA-256
of every pin, including `read_id`, `read_snapshot` and `frontier_at`
(`semantic/demand_results.py:64–102`). A request without a `read_id` makes native acquisition
mint `read:` followed by a random UUID, the current snapshot and the clock time
(`semantic/demand_result_native.py:195`; `semantic/demand_registration_native.py:803–804`).

**Consequence.** For those five paths, two identical requests against an unchanged database get
different keys. A hit can only come from a continuation page, a `resource_handle` replay or an
explicitly pinned re-request, and only inside one long-lived MCP server process. The `ci` CLI
runs each page in a new process (`cli/selected_results.py:96–130`), so it never hits, and the
replay cost the cache was added to remove (PE-F17) remains for CLI paging. On each miss the
request re-reads support into a new temporary index, reopens the release, binds the model and
re-validates the graph (`serve/rich_knowledge.py:118–130`; `semantic/demand_results.py:431–473`,
as read on 2026-11-17).

Two related repetitions share the miss path (2026-11-17; not re-read):

- four consumers page the whole frontier in `recheck_selected_frontier` and then page it again
  under the same read in `selected_record_index`;
- `byte_bounded_page` rebuilds the full report envelope once per accepted row
  (`semantic/selected_query_cache.py:189–200`), and rich entries store the cumulative
  `unknowns` list in every cached row, so entries reach the 8 MiB cap sooner.

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

**Footprint.** Established for the key composition; how often agents repeat identical requests
is unknown.

<a id="da-078"></a>

## DA-078 — The readiness watermark is coarser than the declared role dependencies

**Scoped refresh, 2026-11-21, source `d918a09ea`.** Stands, with a changed footprint.
The current digest includes visible use, population and original-admission identities,
the frozen source sets and original pins, and the acquired trust snapshot. The kernel
digest is absent from this expression. Exact pinned and dependency-free candidate routes
use role matching, which can inspect member or product bodies. The recursive prerequisite
component still scopes fulfilled uses by operation and original source. Native demand-result
and record-grade reads use the same page projection. The planner compares its watermark
when revisiting a waiting fate. An exact-pin control distinguishes a newly usable episode
from an unrelated same-context product. Those observations are about readiness even when
the product value remains equal. Source inspection establishes these paths and determinants.
Examined work and skip rates were not measured.
[Digest and page projection](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py#L2004) ·
[Record-grade acquisition](../../../python/corpus-structure/src/corpus_structure/semantic/record_grade_native.py#L447) ·
[Exact-pin control](../../../python/corpus-structure/tests/semantic/test_data_operation_pinned_reuse_native.py#L538)

**Update, 2026-11-18, source `5139eaba3`.** Stands, with a changed footprint. The
operation-granular component remains, and a second component was added (`6d699ab46`,
`110e8aa1e`). `_unconstrained_watermark_uses`
(`semantic/data_operation_projections.py:1919–2059`) adds, for selected operations that
declare no dependencies, the fulfilled uses of the same demand whose outputs match an input
role (`_watermark_role_matches`, `:1781–1809`) and that pass disclosure and access checks. It
is the first watermark component for local wakes that uses declared roles (pinned uses already
did). It adds to the watermark, so the watermark advances on more events, not fewer. The
component joins every fulfilled use of the demand with roles, outputs and members for each
dependency-free obligation and evaluates access functions per candidate, so its cost grows with
the demand's use count (inferred, not timed).

**FP-07/A4; DP-08, DP-10; H5.**

The planner skips re-binding a waiting obligation only when its inputs watermark is unchanged
(`semantic/data_operation_demands.py:734–737`). `_inputs_watermarks`
(`data_operation_projections.py:2062–2192`) digests, for each waiting obligation, every
fulfilled use of every transitive prerequisite operation with the same original source,
regardless of subject or scope (`:2069–2110`), the role-matched local uses described above,
relevant populations, every visible original admission for the demand, the source sets, and the
whole read trust snapshot and the kernel digest (`:2184–2191`).

**Consequence.** In the one-book workload every obligation shares one original source, so any
upstream publication advances every waiting obligation's watermark and each round re-binds all
of them. The waiting-obligation skip that PE-F06 intended is then largely unrealized for that
workload. The model declares which roles each operation consumes and from which producers; the
prerequisite component does not use it. Because the kernel digest is a component, every kernel
change ([DA-068](#da-068)), including a restamp such as N29, advances every watermark.

**Contrary evidence.** This granularity is the plan's specification: the watermark is "the
latest visible fulfilled use, population or original among its prerequisite operations and
exact pins" (`docs/plans/declared-data-operations/products-and-support.md:574–575`), with a
soundness argument in `demand-planning-and-execution.md:688–692` (plan lines as read on
2026-11-17). Binding is the authority, so a conservative watermark cannot admit a wrong result,
and an unchanged repeat run still ends after one round. What the plan text does not weigh is
the one-source workload, or that folding in the whole trust snapshot makes any trust-epoch
change advance every watermark.

**Footprint.** The key composition is established. The skip rate in the book run is likely, and
rests on that run's subject and source granularity.

<a id="da-033"></a>

## DA-033 — Admission and binding re-prove immutable release content that earlier steps already established

**Update, 2026-11-18, source `5139eaba3`.** Changed footprint; the substance stands.
`data.require_execution_release` is now fully generated by `admission_kernel`
(`semantic/native_admission_release.py:343–409`). The hand-written `admission.sql` is gone
(`9364a5b88`), and the generated text is a predicate-for-predicate translation of it plus
generated catalog checks in three new modules (`native_admission_functions.py`,
`native_admission_principals.py`, `native_admission_tables.py`; `06102f3dd`, `de5792052`,
`920f1b746`, `08284dc6f`, `1b643e7ed`, `46cda0b30`). Nothing new is carried: each call
performs the same re-proof, and the receipt it records still does not short-circuit any of it.
The rebuild of the Python native capture is [DA-083](#da-083).

**FP-07/A4; DP-10, DP-19; H12, H18, H19.**

`data.require_execution_release` runs on every `require_native_execution` call
(`semantic/execution_admission.py:182–213`): each port acquisition, cached-port recheck,
publication-port acquisition and definition admission
(`semantic/data_operation_admission.py:285, 354, 390`; `semantic/data_operation_storage.py:1561`).
Per call it:

- checks that the release is finalized and then performs `sem.require_execution_projection`
  (`native_admission_release.py:41–56`), which parses the archive again and performs
  `sem.require_archive_bytes` (`semantic/archive_projection_native.py:264`; the byte hashing is
  generated in `semantic/closure_native.py:316–380`);
- decodes the release's prepared bytes to scan diagnostics (`:438–459`);
- hashes every authored-SQL input and its admission again and decodes the admission JSON
  (`:461–496`);
- hashes `data_operations.json` and decodes the archived native projection (`:513–534`);
- reads every inference rule (`:629–808`), decodes the manifest (`:835`) and runs
  `sem.require_scientific_layout` (`:857`).

It then records the deployment-admission receipt, and records it only if absent (`:59–97`).
Archive publication already ran both proofs (`semantic/archive_native.py:468–469`) and wrote
the finalization row that the precondition reads immediately before it starts the re-proof.
Neither receipt short-circuits the re-proof.

The same pattern recurs per obligation. `ops.ddo_require_binding` reads, parses and hashes
`data_operations.json` and parses the native definitions projection for every call
(`semantic/binding_admission_native.py:232–251`), and population selection repeats it
(`semantic/population_acquisition_native.py:906–921`); neither file has a commit in the range.
The admitted `sem.data_operation_definition` rows already hold the binding expression and
identities.

Release preparation shows a related repetition outside SQL, recorded here as context and not as
a separate defect. Readers open releases without preparing them again, but full derivation
through `load_release` still runs at every demand registration
(`semantic/data_operation_service.py:142, 300`; `orchestrate/source_operation.py:144, 324`;
`orchestrate/native_execution.py:41`), at every acquisition of an execution basis
(`data_operation_service.py:182`) and at project setup (`orchestrate/project.py:106, 159`).
Within one process it is bounded by an eight-entry cache (`semantic/prepare.py:590–607`). The
production-efficiency review records the registration and basis derivations as a deliberate
verification boundary. This is the current form of [DA-042](#da-042).

**What is not in question.** The catalog half of admission (functions, triggers, tables, ACLs,
indexes) guards against deployment drift, which is a live premise.

**Open decision.** Re-hashing would detect tampering by an owner or superuser. The design
already trusts definer roles (DA-029), so whether that premise justifies per-acquisition
re-proof of content protected by immutability triggers is an owner decision about trust.

<a id="da-058"></a>

## DA-058 — Visual recognition re-prepares its runtime every four packets

**Update, 2026-11-18, source `5139eaba3`.** Stands unchanged. No commit in
`d78c98765..5139eaba3` touched `semantic/visual_requests.py` or `ingest/pdf_chandra.py`, so the
cited lines hold. Chandra remains outside scope by operator direction.

**FP-07/A4; DP-10; H2, H12, H24.**

`execute_visual_demand` loops up to 100 rounds; each round runs a full demand sweep, takes
`session.queue(limit=4)` packets and creates a new `_LocalChandraGroup` whose lifetime is that
round (`semantic/visual_requests.py:697–710`). Building `ChandraRuntime` hashes every pinned
checkpoint file in full (`ingest/pdf_chandra.py:50–68, 152–157`); the model load, the PDF GPU
slot and the Nemotron suspension follow on the group's first recognition
(`visual_requests.py:475–512`). Without a group, the runtime (including the checkpoint hash) is
built before the check for a retained result (`:583` against `:597`). Checkpoint hashing does
not use the process file custody that other model assets now use.

**Consequence.** Every round re-hashes the checkpoints, and a round that needs any inference
also pays model load, slot acquisition and the service handoff, so these recur about once per
four packets. One invocation covers at most about 400 packets.

**Limits.** Whether the round size of four is deliberate (GPU memory) was not established.
Chandra OCR is outside the current DDO scope by operator direction; this is recorded as the
state of the code, not as scheduled work.

<a id="da-082"></a>

## DA-082 — The PDF lowering identity is a hand-kept file list with no completeness check, at once too narrow and too broad

**Update, 2026-11-18, source `5139eaba3`.** Stands. `semantic/pdf_lowering.py` has no commit
in `d78c98765..5139eaba3`: the list still has 70 entries and 14 library names, and nothing
joined or left. Both halves of the finding were exercised in the range.

- *Too narrow.* The unlisted `semantic/pdf_spool_native.py` was regenerated (+605/−140,
  `af01f7776`), and `semantic/published_document.py`, `semantic/native_objects.py` and
  `semantic/native_catalog.py` changed, without moving the lowering identity.
- *Too broad.* The listed shared infrastructure `semantic/native_program.py` and
  `semantic/native_sql_body.py` changed (two commits each), moving the lowering identity and the
  kernel digest together.

The identity lane also ran a one-level static check: it parsed every listed Python file,
collected first-party import targets including lazy imports, and kept the existing files that
are not on the list. Thirty first-party modules are imported by listed modules and are
unlisted, at `d78c98765` and now. Among them are `semantic/pdf_spool_native.py`,
`semantic/pdf_domain.py` (nine listed importers), `semantic/native_objects.py` (thirteen),
`semantic/pdf_effect_contract.py`, `semantic/pdf_observations.py`,
`semantic/visual_evidence.py` and `semantic/published_document.py`. Not every one shapes
lowering, so thirty is an upper bound on the gap one level deep, not its size.

**FP-04; DP-04, DP-09; CI-10, CI-11; H18.**

"Lowering" here means turning PDF records into their stored and transported forms. The code
that does it is identified by `LOWERING_FILES`, a hand-written tuple of 70 paths (64 Python
modules, five model YAML files and one JSON schema; `semantic/pdf_lowering.py:33–104`), with
fourteen library names beside it (`:15–30`, among them sqlalchemy, pglast, pyarrow, linkml and
pydantic). The comment above the tuple calls it an "explicit runtime responsibility closure"
(`:31–32`).

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
coverage test was found.

**Consequence.** The identity is wrong in both directions.

- *Too narrow.* The listed `semantic/pdf_staging_native.py` appends the SQL produced by
  `pdf_spool_native_sql()` from `semantic/pdf_spool_native.py` (`pdf_staging_native.py:168–170`),
  and that module is not on the list. `semantic/pdf_domain.py`, which supplies the PDF call
  bindings to listed modules, is not listed either and does not capture its own bytes. An edit
  to either does not change the lowering identity. For `pdf_spool_native.py` the edit changes
  deployed SQL, so its effect on produced work arrives through native deployment; the
  established statement is only that the lowering identity does not move.
- *Too broad.* Shared infrastructure is listed whole (`semantic/native_program.py`,
  `schema/relational.py`, `schema/physical.py`, `semantic/metadata.py`, `semantic/identity.py`,
  `semantic/prepared_sql.py`). An unrelated edit there, or a patch release of any of the
  fourteen libraries, refuses PDF production, certification and oracle capture until a new
  release is prepared. The same files are in the native kernel capture
  ([DA-068](#da-068)), so one edit invalidates both identities together.

**Contrary evidence.** The list is labelled as a deliberate closure. Custody is sound: each
listed file is read through verified file custody with a stat recheck (`:107–165, 259–273`), so
a process whose files changed underneath it refuses instead of mixing code; contract bytes are
compared in full; retained sources are re-hashed against the contract.

**Footprint and uncertainty.** Established for the list, the two omissions found by reading
call sites, the one-level import count and the refusal paths. How often a refusal occurs is
unknown. This is not a manifestation of DA-068 (a different identity with different
consumers), of [DA-069](#da-069) or of [DA-076](served-claims.md#da-076) (served reads),
although all four are hand-kept answers to "which code determines this artifact". The closest
sibling of the too-broad half is DA-069, which also takes whole files and library versions as
an implementation identity.

**Lead (not a selected remedy).** The compiled model already derives an implementation slice
for Python operations (`semantic/data_operation_identity.py:378–414`, as read on 2026-11-18 at
`d78c98765`); no comparable derived owner exists for PDF lowering.

<a id="da-083"></a>

## DA-083 — The native source capture has no holder and no file custody

**Update, 2026-11-18, source `5139eaba3`.** Stands unchanged in structure, and each rebuild is
now larger. No holder, memo or custody was added: `native_protocol_sources` and
`native_source_digest` carry no decorator, and the only new holders in the range are elsewhere
(the companion projection, [inventory](model-and-execution.md#cache-inventory)). The commits to
the storage module changed what is captured, not how often. The generators that each rebuild
runs grew (the structural, rich, record-policy and product admission generators by about 1,000
to 2,500 lines each, and the `*_native.py` family by 28% in lines), so the cost of one rebuild
probably rose (inferred, not timed). One sharpening: the release already carries the native
digest it was prepared with, and the SQL guard already compares that archived digest with the
installed descriptor (`semantic/native_admission_release.py:531`); the Python check rebuilds the
capture twice only to compare the checkout with the descriptor.

**FP-07/A4; DP-10; CI-11; H12.** Costs below are counts of rebuilds read from call paths, not
timings.

The native capture is the set of artifacts returned by `native_protocol_sources()`
(`semantic/data_operation_storage.py:48–575`). Building it runs about 46 SQL generators,
compiles the physical LinkML model when none is supplied (`compile_physical` is uncached,
`schema/physical.py:166`, and the identical module-level metadata of `semantic/metadata.py:33`
is not reused), builds a further LinkML schema view for source values, renders every program
with one parse per statement, and reads about 110 files from disk (99 modules and the model
files). Nothing holds the result.

`require_data_operation_native` (`data_operation_storage.py:1127–1142`) uses the prepared
release only to call `require_native_execution`, and calls `native_source_digest()` twice
(`:1139`, `:1142`), each call rebuilding the whole capture from the checkout. Rebuilds per
call, by call path:

| Call | Full captures | Site |
|---|---|---|
| Python or prepared port acquisition | 2 | `semantic/data_operation_admission.py:285`, reached from `orchestrate/data_operations.py:718, 754` |
| Cached-port recheck | 2 | `data_operation_admission.py:354`, reached from `orchestrate/data_operations.py:784` |
| Publication-port acquisition | 2 | `data_operation_admission.py:390` |
| Definition admission | 3 | `data_operation_storage.py:1561, 1571` |
| Preparation, regeneration, native products, candidate definitions, demand export | 1 each | `semantic/data_operation_preparation.py:261`; `semantic/primary_operations.py:403`; `semantic/regeneration.py:331`; `semantic/native_products.py:110`; `data_operation_storage.py:1857`; `serve/demand_export.py:281` |
| Model-change preview | at least 2 | `schema/model_change.py` (no commit in the range; as read at `d78c98765`) |

So the execution path, not only authoring, runs the generators: a run that touches N
operations performs at least two full captures per operation at port creation, and two more
for each operation whose cached port is rechecked. One change in the range lowers the
acquisition count: the dispatch loop now acquires a port for the first ready item only when
the operation is a batch (`orchestrate/data_operations.py:1765–1777`, `2619d5aef`), and
reconciliation no longer builds a context. The per-execution acquisition and recheck paths are
unchanged.

The capture also has no custody. Each program's SQL is produced by the generator objects that
the process has already imported, while the module bytes recorded beside it are read fresh
from disk (`data_operation_storage.py:183–190`). Unlike the PDF lowering list and query
custody, nothing refuses when the two differ.

Two adjacent facts share the cause. The wire protocol's caches key on the whole captured
source tuple (`semantic/data_operation_wire.py:47–560`), so a freshly rebuilt capture hits
only after every artifact's bytes are hashed and compared (inferred cost). And
`semantic/metadata.py:33–50` reads the physical closure and compiles two metadata projections
at import, in every process that imports it (63 importing modules by search, 56 at
`d78c98765`).

**Consequence.** The cost of every admission-side call scales with the size of the converted
kernel, and it grew with the conversion work. In a long-lived process after an edit, the
captured module bytes and the generated SQL come from different code. Admission then refuses,
which is fail-closed, but a preparation run inside such a process would record a capture that
is not hermetic (CI-11).

**Contrary evidence.** Rebuilding from the checkout is what makes the descriptor check track
working-tree edits, which the design wants as the signal to restart or redeploy. Read
acquisition does not reach the generators. Deployment reads frozen payloads and imports no
generator. The wire protocol's content-keyed caches are sound. `ci model change` runs in a
fresh process, so the mixed-code case needs a long-lived process that prepares.

**Footprint and uncertainty.** The call sites and the absence of a holder and of custody are
established. Call counts per run, the time of one rebuild and whether preparation ever runs in
a long-lived process were not established.

**Lead (not a selected remedy).** A holder would need the file-custody pattern that the
lowering list already uses (`semantic/pdf_lowering.py:107–165`), so that a held capture is
refused when its files change. The digest that the release carries is an existing identity for
the comparison that does not depend on the checkout.

## Prior identities on this page

<a id="da-024"></a>
<a id="da-025"></a>
<a id="da-042"></a>
<a id="da-043"></a>
<a id="da-054"></a>

Statuses were established on 2026-11-18 at `5139eaba3` by reading the code that replaced each
cited subject. Earlier text is in Git at `fbd3f2a98` and before.

| ID | Status at `5139eaba3` | Note |
|---|---|---|
| DA-024 | No longer applicable | `semantic/publication.py` was removed in `47dc7b873`; the final transaction it described no longer exists |
| DA-025 | No longer applicable | Rendition keying is not on the current path. The surviving `core/keys.py`, with only helper consumers, belongs to [DA-072](semantic-model-and-authority.md#da-072) and [DA-080](boundaries-and-composition.md#da-080) |
| DA-042 | Changed footprint, partly corrected | Readers use `open_release` (55 call sites by search). Full derivation through `load_release` still runs at registration, at each execution-basis acquisition and at project setup; the sites are listed under [DA-033](#da-033), and the production-efficiency review records them as a deliberate boundary. The per-region manifestation of 2026-11-11 went with `orchestrate/characterization.py` (`fe69fddb0`). Call counts per run were not established |
| DA-043 | No longer applicable | `semantic/domain_operations.py` (`64455a0f1`) and `semantic/consolidation.py` (`47dc7b873`) are gone. The successor indexes facts by slot (`semantic/rich_consolidation.py:356–372`) and no whole-realization list load was found on that path. The successor's cumulative work was sampled, not audited |
| DA-054 | Superseded by [DA-078](#da-078), with [DA-069](#da-069) | The task-dependency projection is gone (`200e396fc`). The same family of cause, a dependency granularity coarser than the declared dependencies, is DA-078 for readiness and DA-069 for implementation identity |

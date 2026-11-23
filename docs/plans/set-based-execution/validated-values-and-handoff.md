# Validated values and hand-off

**Status:** SBX-08 and SBX-09 in progress. SBX-10 proposed.
Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns what happens to a value between PostgreSQL and a kernel, and between one
operation and the next, inside Python. It owns SBX-08 to SBX-10. The revised typed carrier is integrated with the native item
representation before the replacement root. Source facts below describe the original
**Inspected** baseline at `7a415d18d`.

## Baseline

**Carriers.** No typed carrier crosses a process. Workers receive JSON bytes and rebuild with
pydantic; the release reaches them as a shared-memory capsule.

- `FrozenNativeSource` (`cs/semantic/source_products.py`): `acquire` is the only validating
  route, but the constructor is public and unchecked. `.value` deep-copies on every access;
  `selector_index()` and `native_items()` rebuild per call. `NativeSourceView` recomputes the
  projection digest per instance. `DeclaredNativeFrameSource` is a second source carrier that
  acquires again. There are 43 `acquire` call sites; several functions receive an acquired object
  and acquire it again (`PreparedSentenceProfile.run`, `PreparedFormalEvidence.run`,
  `PreparedConstructionProfile.run`).
- Product wrappers (`SourceAnnotations`, `FormalEvidenceProduct`, `InterpretedProduct`,
  `CanonicalProduct`, `HanlpProduct`, `RetainedCharacterizationProduct`): frozen over bytes,
  `.value` validates on every access, `inventory()` rebuilds, and `dataclasses.replace` drops the
  one cached identity. `CanonicalProduct.reference` validates and hashes the whole product per
  access and is read once per token in `detach_hanlp_sentence`.
- `SelectedConsumerValue.value()` decodes on every call: two or three decodes per input in
  `_hydrate` (`cs/orchestrate/data_operations.py`).
- A hazard for caching: `_validated_python_input` (`cs/semantic/data_operation_ports.py`) rebuilds
  dataclasses and refuses a value whose instance attributes are not exactly its fields.

**Verification of loaded code.** Three routes exist. The plain port and the prepared port reduce
to one `AuthenticatedSlice.check` and a `stat` per file. The family-specific ports (sentence,
formal, characterization, HanLP, canonical, learned primary, source discovery, contextual native,
three PDF ports, selected source) recompute everything per call: they re-read files, rebuild
asset custody and compile whole modules; the constructions port does this five times per call.
Prepared ports build a new descriptor, re-hashing sources, per call. The end is real: a
long-lived process must not run code other than what it was admitted with, and function-local
imports mean a module can first load mid-call.

**Digests.** The reply's echo of the request digest ties a reply to its request across a process
and is required. The result digest checked in `bind_execution_evidence` compares the parent's
bytes with themselves. PostgreSQL checks fence fields, runtime binding, implementation revision,
output witnesses and proof correspondence; receipt contents are stored, not checked.

**Derived data.** All of these are pure functions of immutable bytes and are rebuilt per
consumer: token and sentence rows from annotations (13 call sites), restored annotations (10),
product inventories, source-view indexes, formal readings, the navigation index, topology
columns, selected formula inputs. Formula contexts depend on configuration as well as bytes.

**Latent defect.** `hydrate_consumer_selection` passes a decoded value to `canonical_bytes`,
which accepts only JSON types and `Decimal`; a body carrying a date, an optional state or a
collection value would raise.

<a id="typed-worker-custody"></a>
## Typed worker custody and lifetime

**Selected planning target · Proposed · 2026-11-22.** Follow the
[columnar redesign amendment](../set-based-execution_2026-11-21.md#columnar-redesign-amendment)
and the shared [population contract](common-analytical-basis.md#columnar-population-target).
Rule confirmation for ADR-0145 precedes dependent adoption. SBX-08 retains the single validating
constructor and SBX-09 retains its request/reply and loaded-code verification bracket.

**One owned representation.** An acquired population holds model-derived Arrow columns,
canonical item commitments and established facts under the release and interpretation contract.
Expose only the consumer's declared projection. Preserve explicit optional states and adequate
numeric meaning. In-process consumers can share compatible buffers while retaining their
owner. Derive an inventory or index once for a real consumer lifetime. Completion owns the
shared observations and distinct premise projections for its rule attestations. Remove the
restoration, repeated canonicalization, freezing and thawing superseded by those acquired views.

**Process boundary.** Write sealed Arrow IPC with PyArrow 26.0.0 `ipc.new_file`, then accept
through `ipc.open_file` over a memory-mapped file owned by the invocation. Bind schema, logical
commitments, transfer seal, request identity and declared input projection. Authenticate the
transfer before relying on its data. IPC byte equality establishes transfer custody while the
canonical commitments establish logical identity. The parent keeps backing storage alive until
worker completion and result acceptance. Refuse a changed file, schema or request, and release
readers, mappings and temporary files on success, failure, expiry and cancellation. Retain the
post-encoding verification point for PDF/visual outputs and checks covering late code imports.

**Resource ownership.** Configure Arrow CPU/I/O pools at the worker/process owner and coordinate
DuckDB threads, asynchronous I/O, spill and active invocations through the existing execution
policy. A relation reader supplies incremental result consumption; joins, windows, sorting and
aggregates still own retained state. Explicitly materialize once when several consumers need a
single-use reader. Charge cached typed views by retained backing allocation or scope them to the
invocation. A small slice can retain a much larger buffer. Close the consumer before releasing
its source and retire any connection whose cleanup cannot establish a usable state.

**Scope and acceptance.** First migrate annotation, canonical and construction, then HanLP and
affected member producers and consumers before replacement-root qualification. Remove their
old population packet path with the migrated callers. Use independent commitments and field
expectations for multiple batches, empty values, all optional states, dictionary/chunk changes,
wide numbers, nested HanLP records and renamed/repeated blocks. Exercise early reader close,
expired attempts, transferred-byte tamper, alias mutation, cancellation and repeated invocation
cleanup. The [cutover owner](cutover-and-qualification.md#columnar-cutover-sequence) reconciles
source/root/context applicability of earlier receipts.

## Target

**A carrier retains established validation.** A source or product carrier can be constructed only
by its validating constructor, or by one named worker-side acceptance of bytes a parent validated and
sealed. Holding the type is then evidence of payload validation under that decoder and rule
contract within a process. Each occurrence acquires its placement, role, support and authority
through its own boundary. A changed validation premise belongs to that boundary's owner. Closing
construction supplies the custody end ("a hand-built wrapper is not authority") without repeating
unchanged payload validation.

**Validated once, derived once.** A population carrier owns its established typed relation and
its canonical commitments. Small control values retain their appropriate immutable representation.
Derived payload views (row view, indexes, inventory, identity) are computed once within that owner.
Immutable payload interpretation is shared per process through a bounded registry keyed by content
digest and decoder contract. Under [partitions](populations-rules-and-proofs.md#collections-and-partitions)
the unit held is the partition, keyed by its digest, which PostgreSQL already supplies. Two placed
uses can share that payload while retaining independent occurrence carriers. A placement-dependent
view additionally binds the placement facts it consumes.

**Retained state has an owner.** Use the existing process-owned bounded cache. Charge derived
state by replacing an entry with its updated weight, retain it as a separately weighted entry, or
scope it to the invocation or worker that needs it. Owner close releases its references to
indexes, Arrow buffers and Docling objects. Lazy growth must have that lifetime or charge route,
and an oversized value can remain usable without cache admission. Partition content uses this
bounded owner without retaining an entire book's carriers.

The [pinned cachetools 8.0.1](../../../python/corpus-structure/pyproject.toml#L65)
`LRUCache(maxsize, getsizeof=...)` charges size at insertion or
replacement. It does not observe later mutation. Preserve the existing
`cached(..., condition=Condition(lock))` load coordination in `caches._Declared`, and account for
derived storage explicitly. See [cachetools size accounting](../../libraries/analytical_infrastructure/cachetools.md#22-capacity-can-represent-much-more-than-entry-count)
and the [existing owner](../../../python/corpus-structure/src/corpus_structure/caches.py#L194).
This target integrates [I07](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I07).

**One decode at ingress.** Hydration decodes a body once into the carrier that the port, the
envelope and the kernel all use. Role values are not deep-copied; carriers are immutable.

**Workers.** A worker receives bytes sealed by the request digest and accepts them through the
single acceptance path, as the formal operation does today. The parent validates the returned
product against its own carriers. Population transport follows the sealed typed worker contract below.

**One bracket.** Each port builds its authenticated slice once at admission, covering its code
closure and assets. Check it inside actual work admission, after capacity is granted, and after
the final work using those captured premises. The CPU route checks after collecting the result.
The threaded PDF and visual routes check after their final captured code or asset use, including
result encoding where it uses those premises. The parent also checks current attempt activity
after collection. Family-specific verification uses the same two-check mechanism.

*Alternatives rejected.* Keeping per-access validation and adding caches inside each wrapper:
leaves construction open, so the validation cannot be dropped. A cache keyed by object identity:
does not survive `replace` and does not share across consumers. Importing the whole closure
eagerly at admission in place of the post-computation check: import side effects and cycles, and
it does not detect a file changed during the run.

<a id="sbx-08"></a>
## SBX-08 — Validated carriers

**Population hand-off · Revised planning target · 2026-11-22.** The
[annotation-fork pilot](common-analytical-basis.md#pilot-implementation-and-evidence) selected
immutable blocks and established scoped parity. That implementation is the baseline for the
[typed worker replacement](#typed-worker-custody). Migrate acquisition and actual consumers
together, preserving established facts, exact commitments, attempt correspondence and cleanup.
The replacement closes only when its ordinary and spawned routes use the same typed contract.

<a id="sbx-live-page-handoff"></a>
### Admitted live page handoff

**Implemented · 2026-11-22.** The private `DemandResult` constructor passes its immutable
interpreted snapshot to selected-query projection after the native storage boundary admits the
wire result and `read_demand_result` verifies the project. Eager canonical bytes still serve the
selected-query cache and pinned readers. The shared snapshot avoids another parse, interpretation,
generated validation and material equality traversal. The carrier owns the frozen value and gives
consumers detached views. The public bytes constructor still follows strict input interpretation.
[Efficiency amendment](../set-based-execution_2026-11-21.md#validation-postgresql-efficiency-amendment) ·
[Review I01](../../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I01)

Use the [retained draft](../../design_review/evidence/2026-11-22_python-postgresql-efficiency/live-page-candidate.patch)
as the starting implementation. The isolated source at `663254b05` plus that draft passed 78
selected native and wire/cut controls (`a091707e98c443ae954a80a58ad2b01e`), including the exact
independent-read test that reached a watchdog on main. The integrated guarded read and metadata
summary passed in `3ec5861d83384056a6e3006fa8727ba7`. Final-source qualification remains paused.
[Current qualification checkpoint](cutover-and-qualification.md#sbx-09-qualification-pause)

The synthetic depth comparison establishes local validation amplification and equality of the compared
rows and cut bytes. Its timings do not establish an end-to-end speedup for the native journey.

At integration, demonstrate that first admission supplies every shape and material guarantee
the removed generated check supplied to projection. Compare valid and malformed native pages
with missing fields, excess support keys, Boolean versus integer values, unknown tags, malformed
numeric strings and missing tag payloads. Retain exact value types, presence states, nominal
contracts, mutation isolation and the independent expected selected rows. Check current and
historical cut/cursor bytes, including ordinary exponent spelling and negative zero. Both shape
paths admitted the spelling `"01"` in the probe, while the canonical semantic codec refused it.
Keep that semantic check at its existing owner. Close a demonstrated admission gap there or keep
the narrow consumer check needed for that gap.

Raw bytes and a caller-created `DemandResult` without native acquisition continue through strict
raw admission. Preserve detached interpretation and lexical cut extraction, current authorization
and trust, the independent caller byte-budget check, and selection-specific cache keys. Exercise
a repeat with a different product filter and lower budget after a warm cache. The shared payload
does not supply current authority for another use. Implement the
[summary correction](owner-resolved-reads.md#sbx-live-summary-correction) alongside this handoff
before the broad retry, under SBX-11's response contract.

Where an actual raw or detached reader still has measured depth growth, compare the current
generated recursive union with the existing first-tag schema and canonical tag decoder. Select
tag-directed validation only after preserving strict arity, envelope and nominal contracts,
presence, numeric precision and member/partition/reference refusals. The isolated field-adapter
comparison supplies a candidate mechanism. It does not replace whole-reader acceptance.

<a id="sbx-witness-handoff"></a>
### Witness preparation and completion handoff

**Scheduled · 2026-11-22.** Before targeted acceptance through SBX-09, make witness preparation
follow the operation's declared witnesses. Build input rows and normalize analyzed scopes only
for the roles and fields that those witnesses consume. `SelectedConsumerValue.value()` already
returns an admitted cached value. Retain it through hydration and share the owned output
snapshot with witness matching and completion assembly where both consume the same meaning.
Avoid reconstructing that meaning independently for each consumer. Preserve the output byte
and reply limits and charge any retained match relation to the invocation or existing byte owner.
[Review I05](../../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I05) ·
[Proof correspondence](populations-rules-and-proofs.md#sbx-04)

Compare authoritative native witness enforcement with a prepared normalized match relation
keyed by the declared group and occurrence. Python currently scans candidate members per output
and canonicalizes comparison operands repeatedly. Remove the repeated production Python check
only when the native check establishes the same member, occurrence, numeric and contextual
meaning and required diagnostics. Otherwise retain the scoped Python check and prepare its
comparison keys once. Independent Python expectations can continue to test native semantics.
Keep exact source/producing-role references and refuse cross-product or cross-member matches.

Exercise one authentic two-report construction or event journey, with each independent producer
allowed to emit at position zero. Compare per-role materialization and bytes on that journey
to establish which repeated preparation was removed. Retain independent invalid-witness, numeric/context equality,
partial coverage and wrong-occurrence controls. Check a file first imported or an asset changed
during work, an expired attempt and a mismatched reply before publication. The SBX-09 admission
and post-encoding checks and request/reply fences remain part of this integrated acceptance.

Completion assembly consumes the same immutable representation only while its bytes and
validation version remain fixed. The
[native attachment and completion investigation](references-and-projection-keys.md#sbx-native-attachment-and-completion)
owns wrapper, canonicalization, proof, lock and publication attribution. Carry its selected
correction through these consumers, retaining the separate framed intent identity and payload
digest, seal verification and current claim/support checks. A new protected handle follows that
owner's evidence and decision conditions before any consumer relies on it.

**Remaining carrier acceptance · Proposed · 2026-11-22.** Formal, interpreted, retained
characterization, composition, native frame and sentence partition carriers already have the
scoped implementation receipts below. Thread their admitted values through remaining ordinary,
retained, detached and spawned consumers. Keep decoded partition bodies shared within the
existing byte owner, population and placement commitments on each acquired assembly, and derived
indexes within their invocation or charged owner. Reuse admitted characterization blocks in
construction when their current support permits it. Sparse reference acquisition follows SBX-05.
Retain scope and authority on each use and independently verify retained replies against the
request. The five native stream cases passed on a registered checkpoint. Reconcile their scope
against final source and rerun the affected cases. Close ordinary provider acceptance through the installed successor and cold-root
qualification. [Proof premises](populations-rules-and-proofs.md#sbx-04) ·
[Reference work](references-and-projection-keys.md#sbx-05) ·
[Final-root qualification](cutover-and-qualification.md#development-reset-through-sbx-09) ·
[Review I05](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I05)

**Partition retention · Tested · 2026-11-22.** The sentence-family carrier retains nominal
headers and decoded partition bodies separately in the runtime byte budget. Each acquired
assembly checks its own population and placement commitments. A body cache hit still
compares the actual decoded digest to the committed digest. Twenty selected annotation and
partition controls passed with `uv run ci test` (`3db106fc6ad84c29889413846a39f95f`),
including relocated shared bodies, altered-row refusal and reacquisition after cache clear.

**Retained characterization and composition · Tested · 2026-11-22.** Retained
characterization and enriched document constructors acquire immutable decoded payloads and
retain their publication meaning and member bytes. Context rebinding carries the same
payload. Five composition controls passed (`uv run ci test`,
`cd3ab7165fb84013893653fe48166998`). Final installed coverage remains open.

**Formal carrier · Tested by selected identity · 2026-11-22.** The carrier holds immutable
formal meaning, publication members and its exact source. Construction retains the formal
product's examined scope and checks current source and nominal correspondence without
replaying producer validation. The retained mathematical readers consume the same
interpretation. The selected formal controls and retained-syntax and declared-analysis retries
passed by identity (`uv run ci test`, `7ab26424ff5e48cabc555e225315fdb5`,
`3ad3d6d2eba34674a0da6016353f40af`, `3301fd706aff40e59d95125ffe5c3654`).
These mixed results do not establish aggregate qualification.

**Interpreted carriers · Tested · 2026-11-22.** Construction, contextual meaning,
contextual native, and declaration syntax acquire frozen payloads at their respective
boundaries. Direct consumption and context rebinding use the carried value. A sealed
characterization worker decodes each existing packet once and detaches its reply at
egress. Forty-three selected construction, contextual and composition controls passed
(`uv run ci test`, `384fb6f0a09441b0a3e16aa0a1ef8f58`, stable source snapshot).
Selected operation events now reuse an acquired source frame, with seven event controls
passed (`ad60ca01fd9c4aa3baadee973c51d986`).

**Native frame ingress · Tested · 2026-11-22.** Parent, retained-read and sealed worker
routes now construct one acquired frame. Detached proposal records validate their source
projection, while selected proposal composition reuses the acquired source. Raw frame
construction and its alternate view are retired. The 67 frame cases passed (`uv run ci
test`, `76adb046d16044b089d50ec9a4a2aa46`, isolated implementation worktree). The
receiving-consumer controls passed by identity across `cc5010ae49514ae4a93ac63a83404cf8`
and `1f0d5e3266b040f7874f9bbccbc51713`. Final registered-root provider qualification remains open.

**CPU descriptor handoff · Tested by selected identity · 2026-11-22.** The child acquires one
descriptor per invocation and carries its callable, signature, adapters and verification through
scalar, batch, stream and coroutine execution. Twenty-five focused controls passed by identity
in `uv run ci test --native-host private` (`a9e448fa74394151a3e4e3dcb33c310a`). The five native
stream controls stopped before execution at the legacy installed descriptor in that attempt.
They later passed on a registered checkpoint (`5edb009f93ad4e94b4442b6c0899374f`).
Final-source acceptance retains the request fence and independent retained-reply check.

**Threaded PDF reply custody · Tested by selected identity · 2026-11-22.** Region rendering,
visual mapping, capture, transforms and views construct the complete reply before their final
acquired-premise check. The two threaded region controls passed with a controlled renderer and
the actual verification (`uv run ci test`, `5ffe892a01f64933944211def96e9984`), including a
file change during encoding. The visual mapping controls passed by identity in the mixed
result `9627a7ac6d0f45bebd7a2b4098437ae0`. Real PDF provider and native stream acceptance use
the registered-root qualification scope.

**Implementation checkpoint · 2026-11-21.** The closed source constructor, same-decoder
acceptance and sealed CPU worker ingress share the selected validation contract. The immutable
decoded source payload is bounded by the process runtime-byte owner. Invocation-owned indexes
are derived separately. Scoped source and CPU controls passed
(`uv run ci test`, `6b2500dde3244790a839a8e3f8d00fb9`). The binding query carries both admitted
display and tagged meaning, and hydration measures both owned buffers. The private typed value
controls passed for a date, optional and collection values and the byte ceiling
(`0f9b4ffe3ac2478bbf5d144c62cf18d7`). An integrated writer exposed a call to the private decoder
(`7b5b49844c394cc08392c57500788df0`, failed). Hydration subsequently switched to the decoded
column already returned by the authorized native binding reader.
Selected values now use one sealed acquisition across consumers. The native-bound entry
accepts an immutable decoded value, exact stored bytes and, when applicable, its selected
partition layout. The raw JSON fallback was removed. Thirty-four selected carrier and
capability cases passed in the implementing checkout
(`uv run ci test`, `3891a1503b524211829214bc6e97c1a8`).
Scalar hydration now carries the selected value and exact stored display and tagged bytes into
source acquisition. The native source memo independently binds the selected kind and tagged
meaning. A changed tagged value and a scalar role with multiplicity two refuse. The 150-case
source and consumer selection, five final affected controls and three actual CUDA controls
passed (`d7396424c28940318bbf91a21db6a240`, `59e8ceba050048cbbbd182c2a6f7c465`,
`f3083e4d95d24ef19210c110a5781012`).

**Owns.** Closing construction of the source and product carriers; the worker acceptance path;
the bounded shared payload registry, occurrence carriers and derived-state lifetime, following
the existing process-owned caches; the single decode in `_hydrate` and
`hydrate_consumer_selection`; removal of the argument deep copy
and the dump-and-revalidate round trip for carriers; the change to `_validated_python_input` so a
carrier is accepted as itself; the fix of the latent defect, by measuring the stored canonical
bytes instead of re-encoding a decoded value.

**Consumer scope (complete).** The carrier classes named in the baseline; the 43 `acquire` call
sites and four aliases; `_compute_formal`; `_hydrate`, `_arguments`, `_complete`; every function
that re-acquires an acquired source.

**Removes.** Re-acquisition of an acquired source; per-access validation and thawing; the second
source carrier's own acquisition; the self-checked result digest; the second read of a source
file in the worker.

**Failure behaviour.** Constructing a carrier outside its constructor is a type error. A worker
that receives bytes not matching the sealed digest refuses before running.

**Evidence.** On the sentence, constructions and predicate operations, a counter on the
validating constructor shows one acquisition per source per process and one validation per
product per process, against today's counts written in the test. The published results and
receipts of a fixture run are byte-identical before and after. A body containing a date is
hydrated without error and its measured size equals its stored size. An attempt to build a
carrier by hand fails. Two placed occurrences share one payload decode while resolving different
absolute spans and their own authority. An occurrence-dependent view binds its context. Eviction
or owner close releases owned derived buffers, while an active carrier remains valid for its
declared lifetime.

<a id="sbx-09"></a>
## SBX-09 — One verification bracket

**Executable custody · Selected · 2026-11-22.** Retain the two-check bracket. The actual CPU
worker uses live Python loading and can import captured modules or read assets during execution.
A sealed input or source digest alone does not bind those later loads. Reopen this choice only
for a concrete loader that binds the executing code, late imports and assets to the capture and
simplifies the complete handoff while preserving native descriptors, attempt fencing,
cancellation and acknowledgment. Such a proposal follows the existing custody decision route.
[Review I05](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I05) ·
[Decision routes](common-analytical-basis.md#decision-routes)

**Remaining acceptance · Scheduled · 2026-11-22.** Both PDF region modes and visual mapping
retain authenticated slices. Their second check now follows encoding, and scoped late-import
and encoding-time tamper controls have passed as recorded by the coordinator. Qualify that
integrated route on the final registered root. Keep exactly two full checks around actual work.
The CPU route's final check stays after result collection.
Retain current-attempt checks after collection and the independent request and reply fences.
Exercise the ordinary executor on the final registered root, including a function-local import
or asset changed during the call, an expired attempt, and refusal before publishing an invalid
reply. Keep the existing construction two-check assertion and actual learned-provider acceptance.
[Witness and completion handoff](#sbx-witness-handoff) ·
[Final-root qualification](cutover-and-qualification.md#development-reset-through-sbx-09)

The concurrent qualification runs were stopped by the operator. Retained selected results and
the remaining witness and provider checks are recorded at the
[qualification checkpoint](cutover-and-qualification.md#sbx-09-qualification-pause).

Keyed PDF rendering already acquires a selected region and original bytes and releases its
database lease before rendering. Visual mapping consumes one observation and PNG. Their remaining
custody work uses these routes. The concrete projected IPC opportunity belongs to candidate
page status and geometry replay in SBX-16, where decoding currently precedes column selection.
Carry full logical admission and exact-byte custody into that owner's projected-reader work.
[PDF replay](pdf-path.md#sbx-16)

**PDF regions and visual mapping · Tested · 2026-11-22.** Both region modes and visual
mapping retain their acquired verification and check inside actual work. Seventeen selected
profile and region controls passed (`uv run ci test`, `8e56875d62354c949fdbc820ba8d31cf`).
The threaded visual control detected a captured file modified at a function-local import and
refused the reply (`2c3342248b9749bb81903157f94d6fb4`, stable source snapshot).

**Worker and provider custody · Tested by selected scope · 2026-11-22.** The formal worker
consumes the authenticated source, parser configuration and nominal member contracts in its
own packet. Two spawned controls passed with a shared CPU pool and zero schema-capsule bytes,
including a pool initialized for another release (`uv run ci test retry`,
`65cdc5d8687e43aa998a56dd421561bc`). Sentence and HanLP execution custody retains stable
provider identity and asset location. The CUDA process hand-off retains the existing file
receipts. The 30 selected file and provider custody checks passed (`uv run ci test`,
`ba0426f784b249dcb506ede76fdb6f0f`), including stable custody across the metadata safety
window and refusal of changed file bytes.

**Implementation checkpoint · 2026-11-21.** The shared CPU plan verifies inside a successful
admission and after collection. The descriptor retains its immutable source and asset mapping in
the existing runtime cache. The child eliminated a redundant immediate read. The focused CPU,
port and source controls passed (`uv run ci test`, `3af37b0a12b64ccda4fcbb3d06088aad` and
`6b2500dde3244790a839a8e3f8d00fb9`). Canonical acquisition retains its authenticated slice and
descriptor and uses that bracket on each calculation. Construction, contextual and composed
characterization ports acquire their descriptor and verification at port resolution. A spawned
construction control asserted exactly two post-admission verification checks and zero source
compilations (`c2355bad832e4219b38a13f0a5c15fd9`, passed). Remaining family hooks and
integrated late-import and tamper controls are open.
The formal port retains its acquired code and grammar before admission. Its real CPU test
observed one full preparation pass and exactly two runtime checks despite deferred capacity.
A separate control refused a changed acquired grammar
(`uv run ci test`, `54cec804d4d74e6c841dff799604a9fd`, 42 selected cases passed).
Sentence and HanLP ports now retain their source and active runtime premises across physical
work. Twenty-six selected CPU cases passed in their implementing checkout, including deferred
admission checks (`uv run ci test`, `26b9c652d124418198c17ad80de22296`). Three actual CUDA
controls passed after the port changes (`454279c5a2924784bdfb32b794ca6a62`).
Discovery retains one authenticated source slice and its validated publication value. PDF
capture and selected views share the acquired original value and bracket their actual work.
Thirty-three selected CPU and private native controls passed (`c921f6be868c4268a9c98edcdbd2b22a`).
All four PDF transform modes retain their own admission, source and configuration premises.
Twenty PDF preparation, custody and worker-tamper controls passed
(`7da5fc5ff00b40ddbceeaa255bac6f7e`). Contextual-native spawned CPU checks passed
(`f3cf88b763ae43f7b1ecd65063e6c2a5`). The learned primary port retains source and question-file
premises across the provider exchange. Seventeen focused controls passed
(`cda975ebe9e544f08a417f0defa4d4c0`). The live learned tests against the old registered root
failed release correspondence before provider execution (`2bfa687618314088bd140ba61d885de0`).
The actual learned-definition journey also stopped at that comparison on the old registered
root (`uv run ci test --native-host private --providers-only`,
`e528f0a381604f5a9c8039dcd8649749`).
The same journey passed on a private root authored from the captured checkout
(`a26f03bf6d004cc4bd3b46854bede4ae`). The real GLiNER provider retained its actual attempt and
exchange receipts, and the downstream component report consumed the exact selected source and
candidate episode. The unchanged repeat produced zero receipts. Integrated provider qualification
still needs the final registered root.

**Owns.** An authenticated slice per family-specific port, built at admission; the two checks per
computation; one descriptor per prepared port; the family `verify` hooks that re-read assets per
call.

**Consumer scope (complete).** The twelve family-specific port modules; `plan_cpu_call` and
`plan_cpu_reply`; `execute_python_call` and `_load` in the worker; `verify_prepared_product`.

**Failure behaviour.** A source file in the closure changed between admission and the end of a
computation refuses the result and requires restart, as now. The refusal behaviours that existing
tests assert are preserved.

**Evidence.** Modifying a closure file during a computation, including a module first imported
inside a function mid-call, refuses the result. A constructions call performs two slice checks
and no module compilation after admission, asserted by counting. The existing correspondence and
refusal tests pass with their expectations unchanged.

<a id="sbx-10"></a>
## SBX-10 — Derived data once, and one span vocabulary

**Owns.** The derived views held on carriers: the row view over a population, source-view
indexes, formal readings, the navigation index, topology columns. One span vocabulary in
`cs/semantic/positioned_rows.py` and `native_source_view.py` covering contains, overlaps with the
zero-width rule, nearest enclosing by width then ordinal, nearest preceding and following within
a partition, merge of touching spans, ordinal within parent and offset translation, used by the
families that build their own indexes today. Two rescans are replaced as they are met: the
per-piece rescan that merges formal pieces (`formal_positioned_lexicon`) and the per-sentence
scan over a block's tokens. The math extract publishes the formula contexts its successors
rebuild, with the stage key binding them to configuration, and the successors read them. Pure
payload views share the content and decoder key. Absolute-span, selection-dependent and
configuration-dependent views additionally bind those inputs and follow SBX-08's retention owner.

**Depends.** SBX-08 for carriers. The row view over tokens is written once, against partitions,
in SBX-03; this package does not build an interim one over packets.

**Evidence.** Along the chain from sentences to scoped relations on a fixture, each derived view
is built once per process, asserted by counting, and results are unchanged. The span vocabulary
returns the same rows in the same order as each index it replaces, on the existing tests of
those indexes. Normalization and scope read published formula contexts and build none.

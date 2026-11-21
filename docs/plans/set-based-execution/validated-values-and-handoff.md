# Validated values and hand-off

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns what happens to a value between PostgreSQL and a kernel, and between one
operation and the next, inside Python. It owns SBX-08 to SBX-10. None of its packages changes a
published value or needs a native revision. Source facts are **Inspected** at `7a415d18d`.

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

## Target

**A carrier retains established validation.** A source or product carrier can be constructed only
by its validating constructor, or by one named worker-side acceptance of bytes a parent validated and
sealed. Holding the type is then evidence of payload validation under that decoder and rule
contract within a process. Each occurrence acquires its placement, role, support and authority
through its own boundary. A changed validation premise belongs to that boundary's owner. Closing
construction supplies the custody end ("a hand-built wrapper is not authority") without repeating
unchanged payload validation.

**Validated once, derived once.** A carrier holds its bytes and its decoded, frozen value. Its
derived payload views (row view, indexes, inventory, identity) are computed once and held with it.
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
product against its own carriers. The packet format is unchanged.

**One bracket.** Each port builds its authenticated slice once at admission, covering the files
of its code closure, and checks it before submitting a computation and after collecting the
reply. Family-specific verification is rebuilt on that mechanism.

*Alternatives rejected.* Keeping per-access validation and adding caches inside each wrapper:
leaves construction open, so the validation cannot be dropped. A cache keyed by object identity:
does not survive `replace` and does not share across consumers. Importing the whole closure
eagerly at admission in place of the post-computation check: import side effects and cycles, and
it does not detect a file changed during the run.

<a id="sbx-08"></a>
## SBX-08 — Validated carriers

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

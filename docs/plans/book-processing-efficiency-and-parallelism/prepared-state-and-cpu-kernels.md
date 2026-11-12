# Prepared state and CPU kernels

**Implemented first increment · 2026-11-11; scoped qualification is owned by the coordinator.** Owns BEP-01–03 design; the [coordinator](../book-processing-efficiency-and-parallelism_2026-11-11.md) owns package state and O01/O02/O04 disposition.

## Baseline and boundary

The [demand owner](../../../python/corpus-structure/src/corpus_structure/orchestrate/characterization.py) calls full load_release for each natural region. The [release owner](../../../python/corpus-structure/src/corpus_structure/semantic/releases.py) distinguishes full current-compiler verification from historical open_release. [Layer validation](../../../python/corpus-structure/src/corpus_structure/semantic/characterization.py) recursively validates dependencies in a fresh context; report payload/reference access repeats decoding/hashing. Existing pure compilation/archive caches and selective source reads remain useful.

BEP-01–03 change preparation lifetime and physical placement, preserving source and semantic authority. H12/H14/H18–20 favor carrying established immutable properties; H15–17 favor operation-shaped inputs with bounded lifetimes.

## BEP-01 · Verified execution preparation

Input: exact release/configuration/runtime context and current authorization. Output: owned preparation reused by all internal stages of the book invocation; standalone demands prepare once at their own boundary. Audit the complete loader path through registry, reader and stage construction so removing one outer call does not leave inner full rederivation.

Keep database admission, source authorization and permissions uncached. Historical archive hydration is not new execution admission. Validity covers every result-affecting compiler/runtime/configuration/source determinant; changed premises create new preparation or refusal. Bind child-process preparation to the same exact immutable structural inputs, initialized once per worker address space. Separate release/compiler preparation from changing source-instance values and method settings that do not affect that artifact. Bind those values through BEP-02; do not key full release rederivation on each region's text or unrelated execution-policy changes. Each prepared artifact depends on the inputs that can actually alter it.

Prefer an internal execution-context argument/lifetime to a process-global verification cache. Existing public semantic request meaning remains intact. A worker initializer may reconstruct a local usable PreparedRelease from immutable archives; do not pickle callbacks, connections or a live reader. Retire redundant loader calls only after their consumed guarantees have a real replacement.

Acceptance: multiple regions share stable preparation; changed runtime/release/configuration and untrusted archives do not inherit validity. Reader/admission checks still observe current DB state. Static call-path inspection plus focused call-count/negative controls can establish this without a performance benchmark.

## BEP-02 · Owned immutable regional inputs

Input: authorized exact source scope, selected upstream pins and BEP-01 preparation. Output: one bounded regional preparation reused across dependent producers: sufficient native items/ancestors, projection/recipe identity, decoded immutable dependency views, indexes and scoped validation results.

Keep the fresh-value LayerReport.payload API for public callers. Internal immutable views must not expose mutable shared dictionaries through it. A digest or caller-constructed report is not proof of validation. Existing protected products/manifests can carry established guarantees only under exact source/content/release/closure and authorization premises. Newly authored or imported results still cross their validation boundary; native publication remains independently enforced.

Reader ownership stays with the coordinator; connections are released before computation. Use existing selective/bulk reads and manifests, not whole-book hydration. Release substantial bodies after their final regional consumer; retain compact pins for composition. The BEP-07a combined-state bound includes cached inputs, queued packets and completed replies.

Acceptance includes mutation isolation, forged/incorrect dependencies, different archived releases, wrong-source refusal, eviction/reload, and overlap without sharing connection-bound readers. Existing TC-E06 indexes are retained, not duplicated by a second cache authority.

## BEP-03 · Pure CPU input and result seam

Input: BEP-02 immutable operation-shaped values and exact attempt/source/configuration identity. Output: private typed draft/result for coordinator validation/completion; CPU processes own no database effects, resident model descendants or publication.

BEP-00 settles the smallest sufficient packet for formal, construction and scientific kernels by inspecting actual source and dependency use. Include original ordered extents and required native evidence; do not substitute text equality for exact pins. Round-trip the packet and result using representative formulas/protected atoms before wiring concurrent dispatch. Payload bytes count against admitted-state bounds.

Use ProcessPoolExecutor with multiprocessing.get_context("spawn"), initializer and initargs. The process main thread executes one parser-bearing operation at a time, preserving SIGALRM/nested deadline semantics. Spawn prevents accidental inheritance of DB/CUDA/thread state. Futures report completion; submit requires external bounded admission and Future.cancel does not interrupt running computation. See [Python3.14 process executor](https://docs.python.org/3.14/library/concurrent.futures.html#processpoolexecutor) and [contexts](https://docs.python.org/3.14/library/multiprocessing.html#contexts-and-start-methods).

The [formal forest](../../../python/corpus-structure/src/corpus_structure/semantic/formal_forest.py), [construction method](../../../python/corpus-structure/src/corpus_structure/methods/construction_characterization.py) and [deadline owner](../../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py) define the actual seams. Preserve protected-atom source guards, factorized ambiguity, formal correspondence and unknown/unsupported distinctions. A worker thread causing OffMainThread/unsupported is a regression.

Use compact immutable bytes/descriptors initially. Memory mapping/shared memory is conditional on BEP-I07's demonstrated movement burden, with existing artifact custody and explicit cleanup. Keep source-specialized grammar preparation distinct from stable declaration compilation; a generic cached parser cannot silently change lexical ambiguity or protected positions.

Cancellation is cooperative with bounded deadline fallback. If a pool must be terminated, its database-free kernels contain the effects; the coordinator fences discarded late results and owns subsequent recovery. Acceptance covers start/shutdown failures, malformed packets, parser timeout, lost claims, out-of-order completion and exact source/choice preservation.

## Delivered execution boundary · 2026-11-11

**Interface-checked.** The private semantic execution_preparation module owns full-loader-created
VerifiedExecutionPreparation and RegionalPreparation. Public demand/book/run wrappers prepare once;
private internal paths carry the same invocation through stages and capture/enrichment. Standalone
source execution owns an equivalent CPU scope. Historical archives and current DB admission remain
separate. Regional source bytes reconstruct independent mutable working views; canonical protected
layers and private immutable decoded premise views survive between stage readers. Exact transitive
proofs retain original release owners, validate new roots and release their charged state on close.

The semantic cpu_execution module owns the policy, private trusted-parent archive capsules,
spawn initializer, bounded admitted-input lifetime and narrow source/dependency reader. All three
actual adapters use that path: formal evidence, constructions and contextual evaluation. Admission
reserves a submission plus packet/reply capacity before hydration. Parent claim checks and exact
request correlation remain active through input preparation, waiting and result validation. Secondary
historical worker preparations live only for the call. Worker replies retain canonical layer bytes
and original cost fields. No worker owns a database connection, claim or publication.

The initial policy is one worker/submission,256MiB canonical retained bodies,64MiB input packet
and8MiB reply. These are conservative finite placement ceilings, not RSS bounds or optimal operating
counts. An oversized indivisible input refuses; temporary pressure from an active transfer waits.
Operation-wide stop is sufficient for the current synchronous driver. BEP-05 must add independently
addressable cancellation before admitting concurrent durable logical claims. Final counts and full
provider/database admission remain in BEP-07. The native publication limit remains unchanged.

The [assembled review](../../design_review/reviews/design_review_book-execution-foundations_2026-11-11.md)
accepts this scoped boundary. Actual verification receipts and applicability are recorded only in
the coordinator, including original unsuccessful attempts. This is not a claim of full-book or
provider-lane parallelism.

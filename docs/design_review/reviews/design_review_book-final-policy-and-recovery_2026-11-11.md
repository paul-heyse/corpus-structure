# Final characterization policy and recovery: assembled assessment

## 1. Scope and decision

**Design / target · 2026-11-11 · BEP final-architecture reviewer. Accept scoped,
Interface-checked**, the assembled policy, native demand anchor, recovery and bounded-read
ownership described below. Code existence is **Implemented**; this assessment establishes no
fresh functional, actual-provider, recovery or full-book test passage. The reviewer authored
ADR-0087's approved-target transcription and independently inspected the implementation;
this is not independent reconsideration of the operator's target selection.

This continues the existing BEP engagement and its combined efficiency-oriented principles and
local parallelism focus. It consumes the [ready-execution audit reconciliation](../audit/README.md#book-ready-execution-refresh)
(published at `0ce41be43bc786f3bfd7b40812f7d70cd9de156b`, source `380fecc74`) and the
[ready-coordination review](design_review_book-ready-coordination_2026-11-11.md), reconciling
the affected boundaries against current dirty source over `7e76ac31cb654a3272b3fa4ef8a342da6059877e`.
It initiates no broad production or test audit. The governing criteria are core 3.3,
heuristics 1.0, code-intelligence 1.4, test-assessment 1.2 where test evidence is discussed,
and the repository binding. The [BEP coordinator](../../plans/book-processing-efficiency-and-parallelism_2026-11-11.md)
alone owns scheduled finding disposition, qualification and completion.

The workload is the retained capture 496/cut 614: 316 natural SourceViews and 518 pages on one
local host, complete selected primary families, skewed prose/formula contexts, concurrent CPU
and native work, exact retained consumers and interruption/recovery. Scope includes explicit
demands, ingest enrichment, default analytical preparation and supported characterization resume.
NLP accuracy, domain interpretation, new providers, released native migration correctness and
complete full-book execution are not requalified here.

## 2–4. Ownership, identity and composition

`CharacterizationExecutionPolicy` is the shared validated capacity value. CLI resolution supplies
complete `MethodSettings`, including Nemotron handoff configuration, to the operation; internal
fallbacks preserve the selected policy. Inference-affecting device/precision/thread settings
freeze before task registration. Current D1 remains CUDA/BF16; the other selected NLP profiles
remain CPU. GLiNER's early validation rejects a thread setting inconsistent with its frozen
semantic profile. Task hashes explicitly include native thread identity for `PRIMARY_PRODUCERS`.
It is absent from the general dependency manifest, avoiding incidental invalidation of unrelated
methods through SQL dependency-scope selection.

**Final source reconciliation · Interface-checked 2026-11-11.** The low-level
`owned_source_execution.require_release` checks open lifetime and release affinity and returns
the original prepared object. It grants no verification token and does not construct a
`VerifiedExecutionPreparation`; live native authorization and the public full-verification
route remain distinct. This supplies the regional reader's required lifetime interface without
promoting a low-level caller's prepared contract into newly verified authority.

`contracts.py` now captures seven actual execution sources: recovery, execution policy,
execution preparation, ready admission, CPU execution, CPU annotations and prepared work. They
enter `analysis_implementation_inputs` as Python implementation artifacts. The positive
`semantic_implementation_inputs` selection does not include them, so their changes affect
`runtime:` identity rather than the semantic-release determinants. The runtime-binding route
consumes that captured implementation footprint and still compares semantic inputs separately.
This closes omitted implementation provenance without turning workstation scheduling into a
new semantic release. Source-sensitive runtime refusals require final-source qualification;
older or interrupted results cannot be relabelled as covering this footprint.

The operation owns transient coordination; ordinary native runs/tasks/attempts retain durable
effect authority. The versioned `CharacterizationDemand` distinguishes frozen source/release,
selected/active layers, method/profile identity and freshness seed. The first actual stage run
stores that demand once; children reference its anchor. Options are evaluated after stage
admission, preventing interleaved waiting regions from each persisting a separate first anchor.
Native anchor resolution checks the participating run's project/release/realization binding.
Managed artifacts are delivered copies, and optional receipt failures cannot replace native work.

| Consequential distinction | Authority and retained meaning | Consumer consequence |
| --- | --- | --- |
| Physical capacity versus inference identity | Shared policy for admission; frozen native profile and primary task inputs for result-affecting settings | Capacity changes can resume compatible work; profile changes cannot silently reuse it |
| Private computation versus published evidence | Parent reduction plus existing native completion fences | A future or lane response is not a published layer or admitted knowledge |
| Original source, active analysis and retained closure | Exact product/source pins and ordinary layer/view contracts | Reuse/composition cannot substitute equal text, discard validation dependencies or strengthen coverage |
| Fresh demand versus recovered work | Once-frozen freshness seed in the native anchor | Recovery can reuse settled fresh products without converting a new demand into an old one |
| Live activity versus durable outcome | Managed observations versus native task/run state | Capacity wait is not provider failure; old activity does not establish a live owner |

The profile's relevant fidelity obligations remain: original provider/device/batch attribution,
explicit missing/partial/failed coverage, exact served evidence closure and separation of reference
answers from production work. This scope changes physical custody and recovery, not linguistic
fact-family semantics or graph analysis. No relation is relabelled or new semantic truth claimed.

## 5. Revealing scenarios and resolved integration issues

Changing region/worker/queue capacity resolves through one policy rather than caller-specific
patches. Changing native threads changes frozen primary identity; resumed incompatible profiles
refuse. Native provider jobs are bounded **per compatible lane**: the default two slots support
one exchange and one pending job. They are not a global two-job limit across independent providers.

A terminal child can resolve the original demand. Recovery checks current method/provider/thread
compatibility, reconstructs exact settled layers and active selections, preserves the original
freshness seed and creates runs for unfinished stages. Terminal records remain terminal. Ordinary
run cancellation retains its scope; managed-operation SIGINT/cancellation closes the owned plans,
CPU/provider work and custody. Actual end-to-end proof remains required below.

<a id="F01"></a>
**Execution-owned primary reads.** Initial assembled inspection found that downstream analytical
`BoundReader.primary_characterization` accumulated complete paged reports without charging their
canonical bodies to execution capacity. Merely routing an already-present regional owner did not
close the default analytical path, which supplied no such owner. The final inspected correction
provides a fresh registration reader/`RegionalPreparation` per input digest and an owned region
per claimed batch when none is supplied. Existing characterization regions are borrowed and
preserved. The claim's reader and completion preparation share that owner through settlement;
scope exit releases it before the claim permit. Selection for the inspected current consumers
enumerates metadata/exact refs, rather than retaining full primary bodies across book selection.
This avoids both a reader-destructor lifetime and an unbounded execution-wide cache.

The final ancestor-dependency branch also uses a fresh or borrowed region per focal source.
`ancestor_source_views` must hydrate that focal body to establish its ancestor pointers; the
per-reference `ancestor_refs` helper encloses that hydration and returns only detached source
references. The long-lived metadata selection reader no longer accumulates those bodies while
discovering the book's dependency population. Repeated ancestor lookups retain their actual
dependency meaning, while each temporary reader/body scope ends before the next focal read.

`RegionalPreparation.primary_layers` reserves page credit before native hydration. Its retain
callback checks exact pin/canonical correspondence, charges newly retained bodies once and keeps
their cumulative charge until the region closes. Native authorization still executes on cache
hits. A failed accumulation raises rather than returning a successful prefix; page credit releases
in `finally`, while previously retained bodies remain charged until scope exit. The correction is
**Interface-checked**, with dedicated admission/cache/cumulative-failure tests inspected but not
executed by this reviewer. Current disposition and actual regression receipts belong to BEP.

The **256 MiB aggregate limit is per native full-read response/page**, not a limit on the complete
closure returned across pages. The independent **2 GiB encoded execution-owned-state budget**
charges retained bodies, CPU packets/replies and drafts across their lifetimes. Individual
canonical layers and existing views retain 64 MiB full-product bounds. Native provider IPC and
bounded page-reading operations retain their smaller limits. These are not process RSS bounds.
SQL accounts for aggregate reference/payload framing, and savepoint-scoped paging preserves the
caller's snapshot after a size refusal. Complete closure may cross pages without truncation.

## 6–9. Principles, gates and alternatives

FP-01–FP-06 are satisfied at the inspected boundary: configuration resolution, source meaning,
native publication, transient coordination and retained recovery have distinct owners with
explicit mappings. FP-07/A4 is satisfied **qualitatively for this scoped realization**: natural
units bound retained state, completed work is reusable, native paging preserves exact closure,
and lifecycle scopes release bodies rather than growing a whole-book cache. H12/H14/H17/H18/H19
support reuse and assurance; H21/H23/H24/H25 support combined capacity, atomic publication and
proportionate recovery. Actual selected-policy feasibility remains a qualification obligation.

| Independent judgment/gate | Scoped assessment and limit |
| --- | --- |
| A1 Change locality | Satisfied: counts/bytes share one policy; profile changes retain their own frozen identity |
| A2 Domain authority | Satisfied: native source/layer/run semantics remain governed; scheduler state is not a second meaning |
| A3 Composition/local reasoning | Satisfied: caller resolution, private work, parent completion and native anchor recovery compose without a new service |
| A4 Execution fit | Satisfied at static design scope; no measured speedup or full-book capacity claim |
| G1 Authority; G3 Validity | Pass at inspected contract scope: native authorization/fences remain; caches cannot authorize caller-authored content |
| G2 Semantic fidelity; G6 Transformation/reuse | Pass at inspected scope: exact pins, original profiles, frozen freshness and complete closure are preserved |
| G4 Hidden behavior | Pass at inspected scope: policy and inference identity are explicit; no silent device fallback |
| G5 Consistency/recovery | Pass for the inspected ownership route; actual interruption/resume remains unqualified here |
| G7 Truthful claims | Pass: partial/unavailable state and proposal standing remain explicit; this review claims no native passage |
| G8 Library leverage | Pass: native JSONB/TOAST, immutable options, savepoints and existing worker/custody mechanisms compose without duplicate infrastructure |
| CI-G1/CI-G2 | Pass for inspected attribution/coverage/pin-preservation boundary; linguistic correctness is not reassessed |
| CI-G3 | No new reference-input route found in these changes; protected-reference qualification remains with the coordinator |

Keeping one native JSONB/TOAST layer is simpler than unconditional rechunking: it preserves digest,
closure and atomic visibility without a new storage/identity protocol. Larger coherent caps alone
cannot prove materialization. The [capacity investigation](../evidence/2026-11-11_bep-layer-capacity/README.md)
attributes actual complete CPU recomputation for SourceView 480 and the largest-by-text captured
view 561; it explicitly distinguishes current recomputation from the original failed body and
does not claim native publication or whole-book passage. A concrete unsupported materialization
reopens the owning decision; no rechunking is inferred from this review.

The first actual run is a smaller recovery authority than a synthetic parent run, durable DAG or
progress database. Managed artifacts alone would expire; copying full demands into every child
would duplicate authority. Existing run options plus references preserve recovery with fewer
lifecycles. No library swap, new coordinator or added proof machinery is recommended.

## 10–12. Qualification, disposition and evidence limits

No further architecture rule change is recommended beyond the approved ADR-0087 target. The
review is evidence for the BEP coordinator, not an independent mutable progress ledger. F01's
source correction is assessed above; the coordinator owns its execution disposition and receipts.
Source inspection cannot certify final-provider behavior, native migration/admission, numerical
quality or actual book/recovery completion.

The final refresh inspected the low-level lifetime guard, per-reference ancestor discovery and
seven runtime implementation inputs against the frozen production source. Prior static
conclusions still apply: none changes source/layer identity, anchor/freshness semantics,
publication authority, cancellation scope or per-lane/per-response interpretations. The first
two changes complete bounded lifetime attachment; the third strengthens attributable runtime
custody. No new material gap was found in those changes. This statement extends the scoped source
assessment only; it does not adopt a running native panel or a corrected test fixture as passed
qualification. Final-source native recovery, actual analytical integration and the book campaign
remain coordinator-owned until their real results settle.

Required meaningful recovery qualification should interrupt a real operation after fresh products
settle while work remains, then resume from an original terminal child. Check the unchanged native
anchor/seed and terminal records, reused exact settled fresh pins, new runs for unfinished work,
and final source/family/consumer closure. Also exercise all-settled recovery and incompatible
profile refusal through the real route. The final actual-provider/native test union, analytical
integration regression, selected-policy full-book execution and pinned native/CLI/MCP/export/
detached consumers remain with BEP-09 and the coordinator; none is marked passed by this review.

Reviewer checks on 2026-11-11: **passed**, scoped `git diff --check` for `orchestrate/{ready.py,semantic.py}`,
`semantic/{contracts.py,execution_preparation.py,characterization_store.py,operations.py}` and this
review; **passed**, `uv run ci docs check` (final refresh managed result
`6c1199f748014534989db47b00751c6e`); **not_run**,
functional/native/provider/recovery/full-book tests. Inspected test code is supporting design
evidence, not an executed provider result. Root final maintenance and qualification remain separate.

### Scoped source fingerprint

The final 20-file source snapshot below has SHA256
`dfc05d2369cecdb690b0d66822b486bfabff5ead9a8b921ce6a26bae4dcb4f6a`.
Compute it from sorted repository-relative paths as UTF-8 lines
`path + NUL + sha256(file_bytes).hexdigest() + LF`. This includes dirty content; later mutations
require assessing the affected conclusions. Additional consumer/test inspections described above
support reach and limits but are not included in this focused implementation fingerprint.

```text
docs/adr/0087-book-characterization-policy-and-recovery.md
docs/plans/book-processing-efficiency-and-parallelism/resources-devices-and-operations.md
python/corpus-structure/src/corpus_structure/core/execution_policy.py
python/corpus-structure/src/corpus_structure/cli/characterization_options.py
python/corpus-structure/src/corpus_structure/cli/orchestrate.py
python/corpus-structure/src/corpus_structure/cli/regenerate.py
python/corpus-structure/src/corpus_structure/orchestrate/characterization.py
python/corpus-structure/src/corpus_structure/orchestrate/characterization_recovery.py
python/corpus-structure/src/corpus_structure/orchestrate/commands.py
python/corpus-structure/src/corpus_structure/orchestrate/ready.py
python/corpus-structure/src/corpus_structure/orchestrate/semantic.py
python/corpus-structure/src/corpus_structure/orchestrate/source_reader.py
python/corpus-structure/src/corpus_structure/semantic/operations.py
python/corpus-structure/src/corpus_structure/semantic/execution_preparation.py
python/corpus-structure/src/corpus_structure/semantic/characterization_store.py
python/corpus-structure/src/corpus_structure/semantic/contracts.py
python/corpus-structure/src/corpus_structure/semantic/sql/characterization.sql
python/corpus-structure/src/corpus_structure/semantic/cpu_execution.py
python/corpus-structure/src/corpus_structure/methods/characterization_resources.py
python/corpus-structure/src/corpus_structure/serve/characterization_replay.py
```

---
id: ADR-0088
title: Run GPU-default NLP in shared hosts with explicit workflow intent
status: superseded
date: 2026-11-12
supersedes: [ADR-0087]
superseded-by: ADR-0091
design: [§B1, §B2, §B4, §B5]
evidence: Proposed
revisit: Common runtime qualification reveals a hard dependency conflict, or shared-host failure isolation prevents useful independent work from retaining its completion rights.
---

## Context

The operator approved the GPU pivot and audit closure on2026-11-12. The
[BEP coordinator](../plans/book-processing-efficiency-and-parallelism_2026-11-11.md#approved-audit-closure-and-gpu-pivot)
owns implementation and qualification. Its E04/E06–14 remain open. Current defaults use CPU
for most NLP; current CUDA requests share one lane and one resident slot. This is application
serialization, not a Torch requirement. It does not establish the cause of earlier book slowness.
CLI graph injection also accidentally changes workflow meaning, bypassing primary characterization.

The standard's explicit semantic model and scoped authority (FP-03/04/05), execution fit (FP-07/A4),
whole-intent interfaces (H8), amortized preparation (H12), bounded live state (H17/H21), dependency-only
ordering (H22) and proportionate lifecycle (H24/H25) shape the replacement. No speedup or memory
optimum is claimed. The prior shared Cursor-group memory incident has no repository attribution.

## Options

1. Change device defaults only. Simplest edit, but the shared CUDA lane would serialize providers
   and replace resident models. This fails the intended independently submitted GPU workload.
2. Keep one process per provider. Preserves isolated locks/environments, but multiplies contexts
   and does not obtain same-context stream overlap. MPS adds a separate deployment responsibility.
3. Use two compatible runtime hosts, model threads and explicit streams (selected). This retains
   the substantive Python3.14/3.12 boundary, shares resident contexts and removes GPU-wide locks.
   It requires deliberate lock reconciliation, multiplexed transport and honest shared failure handling.
4. Use one universal runtime or a new serving framework. No demonstrated need warrants merging
   interpreter boundaries or replacing existing native claims, publication and recovery ownership.

## Decision

**Proposed accepted target · 2026-11-12; implementation not established.** D1 retains CUDA/BF16
and120second inference; HanLP, GLiNER, Maverick, DiPO and spaCy learned inference default to
CUDA/FP32. Preserve checkpoints, thresholds, token/source mapping, precision and attention recipes.
Missing GPU support refuses the selected profile without automatic CPU fallback. Lark, symbolic
kernels, tokenizer-only preparation, validation and reduction remain CPU responsibilities.

One frozen provider profile owns requested model/artifact/runtime/device-class/dtype/backend/
numerical meaning. Resolved placement names the admitted device and owner; startup observations
validate actual execution against the request. Do not duplicate independently editable device
fields or parse old CPU profiles using new CUDA defaults. Historical CPU/native receipts retain
original shape, hashes, ordinals, precision and device. ADR-0085's actual-observation semantics
and ADR-0086's D1 requirements survive; CUDA profiles receive their own native qualification.

Use two supervised GPU hosts: Python3.14 for D1/GLiNER/HanLP/spaCy and Python3.12 for Maverick/DiPO.
Reconcile locked runtimes explicitly; matching Torch versions alone does not prove compatibility.
Load declared residents serially before serving concurrent calls; configure process-global thread,
cache/environment and math settings once. Give different models bounded worker threads and explicit
streams. Retain one active batch per mutable instance and a DiPO module-scoped gate for its patches.
HanLP retains its native gradient contexts: blanket inference_mode would break CRF marginal decoding.
spaCy uses its own Thinc/CuPy device/backend/stream context; a Torch stream context alone is insufficient.

Native requests/replies bind provider/profile, host generation and request identity. One transport
reader routes out-of-order replies; writes and short state updates serialize, inference does not.
Bound admission before executor submission. Preserve actual member populations, native batches,
source maps and request-local completion. A fatal host failure fences all unfinished replies from
that generation; already collected results retain their ordinary publication rights. Cancellation
of one logical member does not kill useful siblings; a wedged host can require bounded termination.

Acquire external PDF/Nemotron custody once for the operation's GPU host group, lazily after capture.
Borrow it explicitly across threads rather than copying ambient ContextVar flags. Never hold the
NLP lease while asking Nemotron to perform capture. Restore external custody only after all owned
CUDA hosts have drained/terminated; unproven cleanup remains unproven. No per-model global GPU lock.

SourceRunRequest explicitly selects default analysis, retained-view analysis, capture/enrichment,
M1 or a configured graph. Source selection distinguishes pack-default/slice/scope/whole-document
and native/integrated product roles; membership stays independent. Validate complete-input rules
before engine acquisition, resolve once into ResolvedSourceRun, and execute through one application
owner returning SourceOperationResult. Graph/registry injection supplies implementation, not intent.
An omitted domain resolves from the selected release. Share settings/policy construction below CLI.
Registration and subsequent execution share one fully verified preparation; all native admission,
source permissions, claims, renewal and publication checks remain live. Historical open_release
never grants execution verification.

Initial target counts are four regions, four stage runs, eight claims and four outstanding jobs per
provider, with two CPU parser workers/submissions. Keep CPU native threads1 and provider host threads4/
inter-op1. Preserve2GiB encoded owned-state capacity, CPU input256MiB/reply64MiB, native frames8MiB,
layer/full-read64MiB, view64MiB and aggregate native response256MiB per page. These are not RSS/VRAM
quotas or optimal counts. Admit before hydration/serialization; retain credit until the last consumer.
Native JSONB/TOAST, one logical layer per natural SourceView, original digest/closure and atomic
publication survive. No semantic truncation repairs an oversized product; rechunking requires a
concrete unsupported materialization and owning decision.

Retain the first actual native stage run's immutable versioned demand anchor and once-frozen
freshness seed, with later children referencing it. Resume creates new runs only for unfinished
work and reuses exact compatible settled products; terminal history stays terminal. Capacity changes
are distinct from inference/profile changes. No synthetic control run or progress service is added.
Managed result expiry does not remove native authority. Status derives capture/family/final readiness,
actual lineage and settled pins from native state; timestamped live activity is not durable readiness.
Run cancellation remains run-scoped; managed-operation cancellation covers its whole owned admission.
Existing uncertain-publication replay and native attempt/holder fences remain the only effect authority.

## Consequences

The CPU-hybrid selection and global CUDA serialization of ADR-0087 are replaced. Its complete settings,
coherent capacities, exact source/receipt identity, native storage, recovery, cancellation and explicit
effect fences survive as restated here. No dependency installation, model/GPU qualification or throughput
measurement follows merely from accepting this decision. Common runtime locks, spaCy/CuPy compatibility,
GPU numerical profiles and shared-host lifecycle are implementation prerequisites.

The existing BEP series owns every remaining consumer migration and removal of superseded dispatch.
The book run, book interruption/resume and full-book consumer utility are explicitly deferred by the
operator. Capture496/cut614/product1627 (316views/518pages) remains authoritative for that later work.
Bounded actual native/provider/CLI/MCP/export/replay qualification is required for this closure.
Do not rerun recognition, activate a default release, select project results, promote, push or edit
TC plans. Preserve failed/interrupted receipts and unknown memory attribution.

## Mechanism sources

- [Torch stream/thread contract](https://github.com/pytorch/pytorch/blob/v2.15.0/c10/cuda/CUDAStream.h#L40-L46)
- [CUDA stream dependencies and lifetimes](https://docs.pytorch.org/docs/2.15/notes/cuda.html#cuda-streams)
- [CuPy current streams](https://docs.cupy.dev/en/stable/user_guide/basic.html#current-stream)
- [spaCy GPU selection](https://spacy.io/api/top-level#spacy.require_gpu)

Inspected2026-11-12. These library contracts support the target, not measured application overlap.

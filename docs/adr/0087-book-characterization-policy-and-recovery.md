---
id: ADR-0087
title: Share final characterization policy and retain native demand anchors for recovery
status: superseded
date: 2026-11-11
supersedes: []
superseded-by: ADR-0088
design: [§B1, §B2, §B4, §B5]
evidence: Proposed
revisit: A supported natural SourceView cannot materialize within the selected coherent bounds, or retained native demand anchors cannot reconstruct exact unfinished work without a second authority.
---

## Context

ADR-0083/0084 establish invocation-owned preparation, ready coordination, private CPU/native work
and existing task/publication custody. Their initial operating counts are explicitly provisional.
ADR-0086 requires current D1 CUDA/BF16. The operator approved the final BEP-07–09 target on
2026-11-11: D1 remains CUDA/BF16 with a 120 second inference deadline, all other selected NLP
providers remain CPU, and one shared execution policy reaches every characterization caller.
The run 610/task 2528 publication failure exposed the old 8 MiB canonical-layer cap. Transport
capacity alone cannot repair that native publication contract.

D3 owns native storage/admission, D4 owns provider/method meaning, D6 owns operation lifetime and
policy, and D8 owns settings, reporting and recovery interfaces. The
[BEP coordinator](../plans/book-processing-efficiency-and-parallelism_2026-11-11.md) owns BEP-E01,
implementation and final qualification. This records the approved target, not a finding closure,
new provider qualification or completed full-book execution.

## Options

1. Retain provisional limits and caller-specific policy, and recover from delivered request
   files. This has the smallest immediate change but leaves the known native size refusal,
   inconsistent caller settings and recovery dependent on expiring managed artifacts.
2. Retain one logical SourceView layer in native JSONB/TOAST, coordinate bounds through one
   validated policy, and retain a versioned demand once in an actual native run (selected).
   This composes PostgreSQL's existing storage/publication and immutable run options with the
   existing coordinator. It enlarges admitted encoded state and requires coherent read/write
   bounds, but avoids a second storage format, scheduler or durable progress authority.
3. Rechunk every layer and add a synthetic parent run or progress database. Partitioning can
   serve a demonstrated materialization problem, but doing it before such a failure adds
   identity, closure, publication and recovery machinery. Existing real runs already supply
   durable custody; a new control run would duplicate lifecycle without computing a stage.
4. Accelerate every provider or add resident replicas. Those profiles would require their own
   native numerical/runtime/custody qualification and multiply residency. The selected hybrid
   uses the already required D1 GPU route and finite CPU lanes; more GPU profiles are outside
   this operating selection.

The selected design applies scoped authority and execution fit (FP-04/FP-07, A4), shared capacity
and live-state bounds (H17/H21), retained preparation/reuse (H12/H14), atomic visibility (H23)
and proportionate recovery (H24/H25). Counts are a reasoned operating choice, not measured optima
or an RSS guarantee; no performance magnitude is claimed.

## Decision

**Proposed accepted target · 2026-11-11.** One validated `CharacterizationExecutionPolicy` is
the settings/API authority. Resolve it once before admission, carry it through explicit requests,
ingest enrichment, default analytical preparation and supported resume, and report the resolved
policy. Settings select the shared policy; `--execution-policy FILE` resolves overrides
through the same validation. Count/byte overrides are result-neutral placement choices. Do not put a second set of limits in each caller.

The selected defaults admit two natural regions, two CPU workers, two active stage runs,
four logical claims and two provider jobs per compatible lane. Retain one compatible resident per provider/profile,
one exchange and at most one pending native batch per lane, one foreground DB operation,
independent renewal and bounded dedicated supervisors. CPU kernels use one native thread;
supported provider startup applies four native/intra-op threads and one inter-op thread before
native work. Current D1 alone uses CUDA/BF16 with 120 second inference; other selected NLP
providers use CPU. Complete `MethodSettings`, including Nemotron endpoint/handoff settings,
must reach every entry point and the one custody owner through startup, failure, cancellation
and teardown. Missing CUDA/BF16 refuses without fallback. Inference profile/device/precision
and thread changes are frozen under their appropriate configuration/provenance before task
registration; counts/byte placement overrides cannot silently select a different inference profile.
GLiNER retains its frozen semantic profile: its intra-op thread count must match the selected
policy, and its supported inter-op count is one. Mismatches refuse before provider startup or
task admission; a changed thread profile requires a new demand rather than compatible resume.

Layer publication and full-layer reads permit 64 MiB per canonical layer; the existing 64 MiB
per-view bound remains, and aggregate full-read response admission is 256 MiB per native page. CPU input is 256 MiB and
CPU reply 64 MiB. The shared encoded owned-state budget is 2 GiB, charged across live regional
bodies, queued packets, completed replies, reductions and publication drafts through their last
consumer. Native provider IPC and bounded page-read limits retain their existing smaller bounds.
No layer cap automatically enlarges an unrelated transport. Admission precedes hydration or
serialization and preserves renewal progress. These values replace the initial operating slice
in ADR-0084; its ownership, member cancellation and native settlement contracts remain in force.

Retain native JSONB/TOAST, one logical layer per natural SourceView, original digest meaning,
exact source/closure and atomic publication. No semantic truncation or successful partial-layer
substitution repairs an oversized product. First reproduce and exercise native publication/read
for SourceView 480 under BEP-E01. Rechunking is conditional on a concrete materialization failure
under this coherent contract; a failure requires a further owning decision rather than an
automatic new format. Neither this decision nor a larger constant establishes BEP-E01 closure.

Freeze a versioned semantic characterization demand, exact source/release/dependency selections
and freshness seed once per operation. Store the complete demand once in `options` of the first
actual native stage run created for the operation; later actual runs retain only its anchor
reference. Keep existing native immutability and lifecycle. Do not create a synthetic control run,
new DB progress service or duplicate full demands in every child. Before any actual run exists,
there is no invented durable run identity. Delivered managed artifacts are useful copies of the
demand/report; their expiry cannot remove the native recovery authority.

`ci run resume RUN --characterization` resolves that anchor from any participating run and
reconstructs the frozen operation even when the selected prior child is terminal. It creates
the required new runs for unfinished work and reuses exact compatible settled products under
existing rules; terminal records remain terminal. Reuse the frozen freshness seed, rather than
manufacturing a new demand on recovery. Result-neutral capacity can change; inference changes
follow ordinary invalidation and attribution. Native uncertain-publication replay retains its
existing owner. Status reports original bindings, anchor/created-run correlation, exact settled
views and unavailable/failed scope using current managed reports. Live capacity/prerequisite
observations do not become durable task statuses or imply a still-live owner.

Existing `ci run cancel RUN` stays run-scoped. Cancellation/SIGINT of the enclosing managed
operation stops its whole owned admission, removes queued work, fences stale replies, drains or
terminates owned children and restores device custody. Useful members outside the cancelled run
retain their completion rights. Retained composition/source-only reads perform no fresh NLP.

## Consequences

All affected callers must cut over to the shared implementation and pass complete settings.
Remove superseded caller-specific limits, serial/ambient execution paths and mechanism-specific
tests while preserving independent semantic, invalid-input, lifecycle and original-custody checks.
The native demand anchor supplies retained recovery without elevating transient reporting or
an expiring delivery artifact to authority. Larger coherent limits permit the intended native
route but require correct combined-state accounting; they promise no maximum process RSS.

BEP-09 prepares a new unselected candidate release and freezes source before execution. Reuse
capture 496/cut 614 with its 316 SourceViews and 518 pages; run all six selected primary stages over
the full book after BEP-E01 and prerequisites settle. Preserve original source, failed/interrupted
attempts, exact old device/batch provenance and inherited recognition limits. Verify applicable
native/read/CLI/MCP/export/detached consumers with no fresh NLP during retained reads. Existing
source-only protected references remain separate from production inputs. No PDF recognition,
activation, project-default selection, push or TC-plan reconciliation follows from this decision.

Implementation, actual selected-provider and whole-book qualification, integrated review and
the required final test union remain the BEP owner's obligations. This ADR does not assert their
completion or measured accuracy, throughput or capacity improvement. A concrete unsupported
materialization or recovery case triggers reconsideration at the owning boundary.

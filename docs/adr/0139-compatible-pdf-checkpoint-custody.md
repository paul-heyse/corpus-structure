---
id: ADR-0139
title: Adopt compatible PDF checkpoints with original contributor custody
status: accepted
date: 2026-11-18
supersedes: [ADR-0127, ADR-0099]
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: A PDF stage cannot authenticate retained content and physical retirement without fabricated producer custody or duplicate conversion.
---

## Context

The accepted PE-S35/39 target defers conversion uptake until producer retirement and resumes
from verified attempt spools. A single sealing publisher is insufficient provenance when content
comes from earlier attempts. The [DDO coordinator](../plans/declared-data-operations_2026-11-12.md)
owns integration and acceptance. This record carries ADR-0099's original/source, native action,
publication and GPU custody contracts, extends contributor attribution and states the native-only
DDO cutover already selected by that plan. It does not retain the superseded legacy task/run branch.

## Options

1. Reconvert every interrupted build. This keeps one publisher but discards authenticated useful
   work and couples recovery to provider determinism.
2. Relabel previous files as the sealing attempt's output. This loses actual producer attribution
   and permits reuse before the previous producer has stopped writing.
3. Retain exact contributor attempts and authenticate spool recovery, selected. It adds explicit
   provenance and retirement checks while preserving one converter and publication implementation.

## Decision

**Proposed accepted target.** OriginalDocumentRef authenticates persisted project/document key,
MIME, content hash and immutable source bytes. It is distinct from ExternalSourceRef and has no
fabricated cut, view, run or published-product fields. The URI remains custody; capture recipe,
configuration and actual assets belong to the operation rather than original-fact identity.
Generic factual support/trust preserves this branch without a synthetic computational episode;
ADR-0096's separately published source factual-support contract remains.

PDF staging uses a genuine DDO task, request generation, current claim and live demand interest.
Current-owner/publication checks enforce task, attempt, holder, scope and exact native PDF
contracts. No synthetic legacy run or parallel converter is retained. A frozen PDF-domain facet
comes from actual owner declarations, native calls and implementation bindings and authorizes only
those actions. A broad capability flag or copied execution model grants no arbitrary native action.

Every build/attempt/holder owns its mutable spool. A callback acknowledges only a verified,
fsynced file durably entered in that attempt's manifest. Conversion makes no per-page database
publication there. Later uptake occurs after physical producer retirement. A new attempt verifies the original producer's retirement, file identity, manifest and
complete material producing premises. An acknowledged page can cross a request generation
or release when the producing basis, page scope, assets, output contract and retained evidence
are compatible under current authority. Original release, task, attempt and contributor
identity remain attributed.

Recovery returns a sealed build, finishes an equal-premise frozen build, re-adopts a complete
verified record spool, or restores verified pages and computes missing page-local stages before
global assembly/enrichment. A changed or unproven material premise requires fresh work
for the affected unit. Complete ordered coverage remains required at certification. This requires
no assertion that fresh GPU conversion is byte-identical to earlier conversion. Rasters and
assemblies remain private producer state under the spool retention/cleanup owner.

A sealed receipt retains its actual sealing task/attempt/holder and every attempt contributing
frozen content, with validated product custody. A later DDO attempt can adopt the exact sealed
result while keeping its current admission fence separate from sealing and contributor facts.
Replay performs no conversion or independent vote. The common completion envelope binds the
actual PDF receipt to the native publication proof. Lease expiry alone is not physical retirement.

Process-host native residency under ADR-0125 can suspend for PDF GPU work. Accepted NLP calls
drain and actual host processes retire before capacity/sleep leases release to the PDF borrower.
Later NLP work can acquire a new generation. Unproven NLP or PDF retirement quarantines ownership
and byte credit; NLP teardown does not prove PDF death. There is no global lock serializing
independent NLP CUDA submissions. Physical configuration, including a local endpoint, stays
explicit and separate from meaning. ADR-0126 owns terminal outcomes versus attempt failures.

## Consequences

One PDF implementation preserves original assets, exact claims and all producer attribution
through interruption. Context, generated-call, native guard and execution-envelope integration
remain necessary; DTO preparation alone establishes no working pipeline. Original bytes, sealed
product, contributors and later admission stay independently inspectable. Captured old data does
not justify a historical runtime reader. The coordinator retains native resume, failure, actual
provider and whole-book obligations; acceptance does not deploy or close DDO-07, and establishes
no measured improvement.

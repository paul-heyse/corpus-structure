# Boundaries and composition

**Implemented source inspected, 2026-11-03.** [Baseline](README.md#baseline).
Paths omit `python/corpus-structure/src/corpus_structure/`.

<a id="da-018"></a>

## DA-018 — Historical extension-version correction retained

The earlier phase0 extension-pin correction retains its October29 evidence date. No fresh
provider/version campaign was run. This refresh supplies no reason to reinstate that diagnosis.

<a id="da-019"></a>

## DA-019 — Historical test-sweep lease correction not refreshed

The former phase0 test-lease finding remains historical. The independent test account owns its
current coverage; this production audit does not renew that baseline.

<a id="da-020"></a>

## DA-020 — Analytics-setting propagation diagnosis corrected

consolidate_cut receives actual AnalyticsSettings and forwards thread/memory/scratch to AnalysisScope
(`semantic/domain_operations.py:2058–2088`). Finalization forwards settings
(`orchestrate/commands.py:387`), and both CLI routes pass settings.analytics
(`cli/regenerate.py:262`; cli/orchestrate.py:287). This is source correction, not performance qualification.

<a id="da-045"></a>

## DA-045 — Exposed method-reader connection premise corrected

**Source-inspected 2026-11-04, M1-20261104-r4.** The method-facing `Reader` now exposes owned
operations rather than a raw connection (`core/method.py`). `ScopedSourceReader` borrows a read
snapshot for each operation; `BoundReader` supplies the database adapter. Registration retains
its transaction ownership without handing that capability through the method protocol. The
previous exposed-connection diagnosis no longer describes this supported interface. This is
an ownership correction, not Python sandboxing or a claim about arbitrary reflective code.

<a id="da-047"></a>

## DA-047 — Cited advertised operational surfaces corrected

**Source-inspected 2026-11-05.** Orphan availability is explicit (`orchestrate/commands.py:48,414,456`, `orphaned=None`), and
CLI exposes only implemented complete/full scope (`cli/orchestrate.py:140–146`). The earlier
empty-orphan and advertised-by_unit examples no longer sustain a current surface defect. This is
source inspection of those examples, not qualification of every advertised command.

<a id="da-052"></a>

## DA-052 — Proposal production now shares an executable producer binding

**Source-inspected 2026-11-05.** `methods/llm/producer.py:10–57` owns the finite supported producer contract, including
agent.opus and agent.general, protocol/version, unit, execution kind, mode and model. Queue,
snapshot, lease and automation paths consume that owner. The literal agent.opus remains an
explicit default (`orchestrate/semantic.py:986`), not the former exclusive routing authority.
The finite implemented support set is honest; arbitrary new providers still require qualification.

<a id="da-059"></a>

## DA-059 — Model-receipt facts now retain their operation account

**Source-inspected correction, 2026-11-10, `8e69e2b5f`.** FP-02/04/06, DP-02/08/19/21.
`cli/model.py` composes model preview/apply/candidate/deploy through `managed_operation`, records
acquired target and deployment checkpoints, and returns the same OperationAccount as the retained
manifest. `cli/managed.py:279–396,476–478` retains classified failure, cleanup, known effects,
predecessor/reached revision, release and acquired target; failure publication no longer depends
only on the immediate envelope. Deploy retains this account after releasing candidate registration
holds (`cli/model.py:1330–1396`). The earlier omission manifestation is corrected, not freshly
runtime-qualified here. Independent exact apply/deployment tests challenge stale and partial effects;
the current CLI/PTD plans retain execution disposition and original receipts.

<a id="da-060"></a>

## DA-060 — Evidence promotion now requires established cleanup custody

**Source-inspected correction, 2026-11-10, `8e69e2b5f`.** FP-04/05, DP-02/03/19/21/22.
`cli/managed.py:82–88` distinguishes settlement time, explicit unsettled custody and operation-account
cleanup. `cli/operations.py:315–321` refuses evidence promotion unless `manifest.custody_settled()`.
A terminal failed result with uncertain cleanup therefore cannot become finalized evidence through
this route. The old November8 loss-of-custody example is corrected. This is source evidence; no
artifact promotion, cleanup fault or qualification command ran during this refresh.

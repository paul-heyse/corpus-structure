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

## DA-059 — Managed model receipts omit facts present in immediate reports

**Implemented source inspected, 2026-11-08.** FP-02/04/06, DP-02/08/19/21,
G2/G7. Exact apply checks the preview's workspace, toolchain and file digests
before writing. It reports stale inputs as `ModelError`
(`schema/model_change.py:459–494`). The CLI records a generic `failed` outcome,
the exception class and paths written so far. The outer refusal adapter emits
the actionable reason to the original caller after the managed result has been
settled. A later read by ID can see the recorded paths and class, but cannot
recover which input was stale or the reason for the refusal
(`cli/model.py:774–815`; `cli/failures.py:75–115`).

The managed fallback also settles escaping exceptions with their class alone
(`cli/managed.py:310–339`). In the inspected apply route, a protective refusal
before any writes and an execution failure have the same retained outcome even
when recovery calls for different action. Existing exact-preview fences,
progress receipts and richer immediate output still protect and inform the
original invocation. Some owners settle richer outcomes explicitly. The
demonstrated footprint is model apply and its managed fallback, with other
callers unassessed.

The successful deploy path similarly stores effects and release in its
managed result, while the immediate report also carries target profile,
acquired target and predecessor. Success releases the candidate holds.
If the candidate is collected while the deployment result remains
available, the result ID alone cannot identify the target it affected
(`cli/model.py:1004–1044`; `cli/managed.py:342–356,611–649`).
This concerns managed operation receipts. The semantic deployment
history and exact target fences still have their own authority.
[CLI operations custody](../../adr/0069-cli-operations-custody.md)

<a id="da-060"></a>

## DA-060 — Evidence retention loses unresolved cleanup custody

**Implemented source inspected, 2026-11-08.** FP-04/05, DP-02/03/19/21/22,
G2/G3/G5/G7. The review exporter publishes its selection before capture
starts. Cleanup uncertainty marks custody unsettled, and the managed
exception handler can then record a terminal timestamp and failed outcome
while leaving that flag in place
(`cli/review.py:84–111,120–131`; `cli/managed.py:237–243,328–335`).

Artifact delivery requires a terminal timestamp and verifies the
publication. `ci evidence retain` can promote the copied selection
without checking or carrying forward `custody_unsettled`. It writes a
finalized record saying the invocation settled as failed, even though
`ci results show` still reports custody as unresolved
(`cli/managed.py:554–590,859–877`; `cli/operations.py:298–379`).
The lease and publication checks protect the copy. The retained record
loses the distinction between execution outcome and known cleanup,
which can affect later recovery or reliance on the receipt.
[Evidence retention decision](../../adr/0069-cli-operations-custody.md)

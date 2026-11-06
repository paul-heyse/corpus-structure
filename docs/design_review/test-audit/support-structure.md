# Support structure and boundary fidelity

**Interface-checked by source inspection, 2026-11-05.** See the [baseline](README.md#baseline).
Sharing types, validators and valid setup is useful; an expectation assessing their correctness
must retain a challenge independent of the relevant mistake.

<a id="dta-016"></a>

## DTA-016 — Actual stdio and production serializer controls correct the substituted-boundary gaps

**FP-02/05/06, DP-23; companion §1/3/5/6.**
`test_runtime_entrypoints.py` now exercises the SDK StdioTransport over a real child for normal,
early-exit, tool-error and cancellation modes, with explicit clone coordinates and child/process
group settlement. In-memory controls retain their distinct contract scope.

`test_pdf_record_reader.py` uses a ScalarReader subclass that supplies ordered scalar input while
retaining production `PublishedPdfReader.iter_native_json`; the emitted-chunk bound at460–461
is asserted on actual production formatting, including large Unicode and negative-zero data.
Exact reconstruction, native SQL/cursor and failure/early-close/cancellation controls provide
additional evidence. The reference serializer's separate assertions do not impersonate that
production bound. The old two named manifestations are corrected in source; no fresh transport
or database pass is claimed. Rendering discrimination is separately diagnosed in DTA-023.

<a id="dta-005"></a>

## DTA-005 — Selected assembled scenarios now use production composition

**FP-03/04, DP-01/06; A2/A3; companion §1/2.** Current serving/statistics scenario
owners use `prepare_packs` for assembled claims; `test_pack_acquisition.py` independently
observes composed preparation and forbids inappropriate reacquisition. Synthetic releases remain
valid kernel isolation. TA-05/08/09's selected correction is supported by current source;
new scenarios are judged by their actual claim, not a rule requiring every fixture to use the
complete production composer.

<a id="dta-009"></a>

## DTA-009 — New reference scenarios specialize private globals in other test modules

**FP-01/03/06, DP-17; companion §2/3.** The six selected TA support-owner extractions
are corrected; that closure is not generalized to subsequent tests. Current
`evaluate/test_record_references_native.py:53–65` changes
`semantic.test_private_records.observation_inputs` before dynamically acquiring its
`private_source` fixture. `evaluate/test_record_policy_authority_native.py:131–228` also replaces
that host's `SimpleNamespace` and another test host's `expected_reading`, `assign_origin` and
`create_reference_set`. Whether specialization occurs depends on private import bindings and
a descriptor name rather than an explicit scenario contract. A behavior-preserving helper/import
refactor can therefore change or defeat the case's setup policy across modules.

Methods fixtures (`methods/test_m1_readings.py:15–39`, `test_m1_record_frontends.py:28–30`,
`test_m1_source_profile.py:22–24`) and PDF fixtures also retain test-host imports. Imports alone
do not establish the same consequential coupling everywhere. Monkeypatch restoration is scoped,
shared realistic setup avoids divergent stand-ins, and independent expected readings remain
valuable. The established problem is the private-global specialization footprint, not all reuse
or a demand for a universal configurable fixture framework.

There is also a concrete collection effect: `tests/semantic/test_publication.py:149` computes
`R = fixture_model()[1].release_id` at import time. Consumers importing its helpers can activate
composed preparation during collection even before they select a case. This is demonstrated
dependency activation, not a measured collection bottleneck. Explicit stable preparation and
pytest fixture lifetimes are available; no additional discovery framework is selected.

<a id="dta-012"></a>

## DTA-012 — Historical macro configuration ownership is now explicit

**FP-04/06, DP-01/06; companion §1/2/8.** `tests/math_support.py:10–14` and
`tests/llm/conftest.py:7–10` explicitly identify frozen independent historical configuration.
They are not maintained mirrors of today's production pack. The former ambiguity is corrected;
matching macro values are not a reason to merge an independent oracle into production.

<a id="dta-008"></a>

## DTA-008 — Previously missing method-contract fields remain corrected

**FP-02/04, DP-24; companion §1/5.** Native agent-hold, operation-binding and
source/document descriptors now declare `unit_type` and `Config` where their ordinary contracts
consume them. The previous tolerant-fallback manifestation is corrected. SimpleNamespace itself
is not a defect. This is source evidence, not a rerun of native deployment or product acceptance.

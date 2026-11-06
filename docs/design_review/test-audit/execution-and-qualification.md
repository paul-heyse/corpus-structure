# Execution and qualification

**Interface-checked by source inspection, 2026-11-05.** Baseline and limits are in the
[account](README.md#baseline). No runtime or timing result was produced by this refresh.

<a id="dta-002"></a>

## DTA-002 — Interrupted shared authentication effects now have an owned recovery path

**FP-05/07, DP-19/20/21; companion §6/8.** `scripts/native_auth.py` now journals
cluster/role/token identity before effects, fences helper generations, waits for owned tagged
backends and selectively recovers owned authentication rows/roles under exclusive leases.
`tests/scripts/test_native_auth.py` contains independent fake-state and actual subprocess controls;
opt-in native crash controls cover killed owner and partial/delayed effects. The former absence
of recovery is corrected. Existence of those controls is not a fresh run: opt-in native outcomes
remain governed by their original receipts and selected scope. No role/service changes occurred
in this audit.

<a id="dta-003"></a>

## DTA-003 — Acquired identity is corrected; deployment completeness remains consumer-specific

**FP-05/06, DP-21/22; companion §6.** Current native events bind requested and
acquired identities to the executing item. The classifier requires item-bound native identity;
missing context cannot satisfy a current native required-node union. Session context cannot
attest a test. This corrects the old ambient-settings diagnosis.

A narrower question remains: `scripts/native_test_support.py:690–730` can mark provenance
complete while deployment revision or policy is unavailable;
`scripts/test_receipts.py:376–420` tests identity completeness without requiring those fields.
Restricted observations normally inherit deployment metadata from the maintenance acquisition.
Identity-only evidence may be sufficient for a generic native claim; scenario seeds are
legitimately optional. Revisit when a qualification consumer relies on this flag for full
deployment/policy reproducibility, and reconcile TA-04's broader provenance wording at that
boundary. No incorrect full qualification or misrouted write is established here.

<a id="dta-017"></a>

## DTA-017 — The default application target now refuses accidental acquisition

**FP-02/05/06, DP-19/20; companion §5/6.** Package `tests/conftest.py:169–180`
installs an autouse refused application target after preserving original native settings.
Explicit clone coordinates resolve original purpose credentials before replacing the database.
`test_semantic_runtime_settings.py:118–140` challenges the sentinel while retaining valid explicit
targets. The old unfenced-default exposure is corrected; no historical or current misrouted write
is inferred.

<a id="dta-018"></a>

## DTA-018 — Focused math controls construct unused downstream scope preparation

**FP-03/06/07, DP-10/23; A4; H5/6/12/20; companion §8.** TA-01/05's serving seed
and fresh committed clones correct the named repeated-publication footprint. That correction
is preserved. A different current manifestation is `tests/math/conftest.py:19–21`, whose
`spike_pages` always calls full `analyse_all`. `tests/math_support.py:129–148` prepares values,
extracts mentions/relations and resolves scopes; production `methods/math/scope.py:300–337`
obtains the NLP pipeline, matchers, segments and binding sites.

`tests/math/test_property.py:92–105` consumes readings/source content, while
`tests/math/test_spans.py:158–195` consumes readings/values/extraction without scopes. Focused
selection therefore activates a downstream linguistic dependency unrelated to those claims,
adding preparation and failure coupling. This is static unnecessary-work evidence, not a
measured dominant cost. Whole-group session reuse is useful and scope tests need the complete
scenario. The existing `coverage_rows` route and `test_workers.py:52–65` demonstrate a narrower
reading-only boundary. No blanket fixture-scope increase, cache or weaker scientific evidence
is prescribed.

A second current example is `tests/semantic/test_private_records.py:696`: a schema/projection
control consumes only `private_source.prepared`, while that fixture (lines78–371) also publishes
a native PDF, source views, run/method/task and claim state. The pure assertions inherit native
prerequisites and failure coupling without observing those effects. Sibling integration cases
need the complete fixture; shared preparation benefits them. The concern is this focused
consumer, not the validity or size of the complete native scenario.

<a id="measurements"></a>

## Qualification limits

The Rust classifier does not inspect all cleanup/group-settlement fields used by Python
classification (`scripts/test_receipts.py:577–624`). Shared-supervisor cancellation protects the
ordinary assembled route, and current empty Rust selection establishes no functional coverage.
This is a latent local-classifier consistency limit, not a demonstrated current erroneous
qualification. Revisit if Rust gains executable cases or an independent consumer relies on that
local result.

## Measurements

No current timing measurement was taken. The prior account's 2026-10-30 receipt retains its
original source and conditions in Git; none of its percentages is a current workload claim.

<a id="dta-021"></a>

## DTA-021 — Fixture self-tests rely on another test to establish their premise

**Interface-checked by source inspection, 2026-11-05; FP-05/06, DP-23; companion §4/6.**
`tests/test_db_fixtures.py:35–43` separates the rollback-producing write from its absence
observation. Selecting the observation alone cannot distinguish rollback from never making
the write. Lines46–61 similarly pass a clone name between tests through module-global
`_committed`; selecting the drop control alone fails its prerequisite assertion even when
cleanup works. These are package-relative paths, not repository-root tests.

The problem is the evidence dependency across separately selected tests, not shared immutable
preparation. The committing test independently checks committed visibility through another
connection and isolation from the session clone. Native fixture controls elsewhere exercise
ownership and disposal explicitly. No suite-wide fixture failure or actual leaked clone is
inferred. Pytest fixture dependencies/finalization can express owned setup and teardown, but
the audit does not select a repair or require another lifecycle framework.

<a id="dta-022"></a>

## DTA-022 — Native qualification observation runs without an active receipt consumer

**Interface-checked by source inspection, 2026-11-05; FP-06/07, DP-10/14/21; A4;
H6/12/20; companion §8.** `scripts/native_test_support.py:655–732` returns only if the
qualification plugin cannot be imported. The ordinary pytest configuration makes `scripts`
importable, so observation still executes identity/catalog queries, conditionally reads the
deployment revision, rolls back the driver transaction, hashes supplied policy and constructs
context when no qualification stream exists. `scripts/qualification_plugin.py:22–28,43–47`
then discards the event. The SQLAlchemy physical-connect event at native support lines639–652
repeats this work for fresh connections, including the existing NullPool routes.

This is demonstrated unconsumed observation work in ordinary native execution, not a measured
bottleneck. The observation correctly reuses the acquired connection, preserves ownership,
and supplies necessary provenance during receipt-enabled runs. The sealed session template
already amortizes deployment. A later correction must distinguish those useful guarantees
from observation whose output has no consumer; neither more pooling nor weaker native evidence
follows automatically. Existing SQLAlchemy event hooks and pytest/plugin lifecycle facilities
provide the mechanism boundary; another instrumentation subsystem is unnecessary.

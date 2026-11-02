# Support structure and boundary fidelity

**Interface-checked by source inspection, 2026-11-02.** See the [baseline](README.md#baseline).
Sharing types, validators and valid setup is useful; an expectation assessing their correctness
must retain a challenge independent of the relevant mistake.

<a id="dta-016"></a>

## DTA-016 — Some boundary claims exercise a substituted implementation

**FP-02/05/06, DP-23; companion §1/3/5/6.** This diagnosis is narrower than the previous
“actual journeys stop short of production” claim. `test_runtime_entrypoints.py:37` now exercises
the real pooled lifespan and lease/read/propose route, and `test_serving.py:611–895` exercises
CLI query, continuation, explanation and export. Native/ADBC export controls are real. Current
`core/db/store.py:222–245`, `semantic/refusals.py:60–77` and `cli/failures.py:24–56` translate pool
acquisition timeout. The 2026-10-30 observed uncaught PoolTimeout is retired, not freshly reproduced.

Two bounded evidence gaps remain. `test_runtime_entrypoints.py:263–301` only initializes the
stdio subprocess; complete semantic tool journeys use an in-memory FastMCP client. This provides
strong tool/native integration evidence but cannot detect post-initialize wire/lifespan faults.
A search over package/root tests and scripts found no complete post-initialize stdio tool call.
No defect in the current wire implementation is established.

A more direct manifestation is `test_pdf_record_reader.py:66–181,240–245`: `NativeRows` overrides
`iter_native_json` with a fixture serializer, so the large-Unicode chunk-bound assertion judges
that serializer rather than `PublishedPdfReader.iter_native_json`. A regression in production
chunk sizing can therefore pass this named bound test. Counterevidence is substantial:
`test_native_export_uses_one_ordered_sql_cursor` in the same module (`:349–466`) uses the production
serializer over real ordered event SQL and checks exact reconstructed data and negative zero,
including a large value. It does not assert the emitted chunk bound. This is an assurance gap,
not a claim that the production serializer currently violates the bound.

<a id="dta-005"></a>

## DTA-005 — Product composition and native scenario composition remain separate evidence paths

**FP-03/04, DP-01/06; A2/A3; companion §1/2.** A production composer exists and has direct
controls (`test_pack_acquisition.py` checks no compilation during acquisition and exactly one
composed-root preparation). However `test_statistics_cut.py:46–68` manually composes core/domain,
rules, proposal and analytical dependencies; `test_serving.py:376–446` assembles a pack and facts
for native readers. These tests can establish their contracts while missing a wiring defect in
product composition. The real-pack head-word mismatch in DTA-015 illustrates that distinction.

Small synthetic releases are appropriate isolation, not universally defective setup. The issue
is substituting that evidence for an assembled product claim. Current CLI serving and generated
operation controls materially strengthen the earlier baseline. No requirement to migrate every
fixture to the product composer follows.

<a id="dta-009"></a>

## DTA-009 — Test modules own shared scenarios with consequential defaults

**FP-01/03/06, DP-17; companion §2/3.** Helpers remain imported across test modules. For example,
PDF reconciliation, payload validation and native publication import `test_pdf_integrated`;
orchestration streaming/cancellation imports `semantic.test_pdf_staging`. Changes in these hosts
propagate to consumers of their case-defining defaults, and importing a host can bring unrelated
preparation into focused collection.

The `fixture` helper in `test_domain_operations.py` still composes flags into one scenario;
`two_reports` also changes Person identity scope. This is hidden semantic coupling rather than
an objection to parameterization. Relevant source includes that helper and its callers in
`test_occurrence_context.py`. New `native_record_fixtures.py` and narrower fault/resource helpers
are positive counterexamples. Shared real setup prevents divergent stand-ins; its benefit is
preserved. Old importer counts and fixture line lengths are not current measurements.

<a id="dta-012"></a>

## DTA-012 — Historical fixture configuration still has an ambiguous ownership explanation

**FP-04/06, DP-01/06; companion §1/2/8.** The former multi-module/caching footprint has shrunk.
The current concrete residue is the independent historical macro map in `tests/math_support.py:54–75`
and its counterpart in `tests/llm/conftest.py:54–75`. The latter still says it is written there
“until that file exists” (`:8–10`), although the domain methods file exists and the map feeds
`view_of` (`:104`). It is unclear from that owner whether it is a frozen reference configuration
or a maintained mirror of today's pack. A change can therefore be applied on the wrong premise.

The math helper explicitly declares independent historical-oracle configuration: deliberate
independence is valid and must not be deduplicated into production merely because values match.
No present macro drift or runtime penalty is established. The old grammar-cache attribution and
removed evaluate/consolidate fixture manifestations are not carried as current facts.

<a id="dta-008"></a>

## DTA-008 — Prior missing method-contract fixture fields corrected

**FP-02/04, DP-24; companion §1/5.** The earlier diagnosis concerned descriptors relying on
`tolerant record_method` fallback, not use of SimpleNamespace itself. Current descriptors in
native execution, native operation binding, PDF consumer and source-selection tests declare
`unit_type` and `Config`. The concurrent agent-hold/operation/packet repairs add those fields
through the same ordinary contract. The specific missing-field manifestation is corrected;
its previous counts and native_range-fallback claim are retired.

This is source evidence of corrected fixture contracts, not a report that this audit reran
native tests or closed UM qualification. Actual deployment/catalog checks and independent
malformed native input controls retain distinct roles.

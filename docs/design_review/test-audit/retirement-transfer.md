# Retirement and transfer

**Interface-checked by source inspection, 2026-11-02.** Use the [account baseline](README.md#baseline).
ADR-0047 retires older result/runtime formats while retaining current custody, scientific meaning,
source evidence and independent expectations. A removed obsolete success case is not by itself
an assurance loss. Preservation is judged against surviving behavior.

<a id="dta-004"></a>

## DTA-004 — Some independent reference obligations still lack a current assembled counterpart

**FP-04/05, DP-23; CI-12 by analogy; companion §1/4/7.** Independent reference material is a
strength and must not be treated as a second production authority. The previous broad lost-oracle
table combined different cases and is narrowed here. `tests/semantic/test_trace_reference_fixture.py`
checks source/reference structure; it does not by itself execute all trace negative patterns
against a current served result. Searches of current test consumers must distinguish those
structural checks from the behavioral obligations in `fixtures/trace` and `fixtures/toy`.
The wider claim that all original toy/trace outcomes are absent is not established.

There is positive transfer: `test_consolidation.py:66–89,340–347` compares assembled content under
reversed inputs and lexical Decimal representations. The former absence of fact-order controls
is corrected. Exact occurrence/fact/reference and rule/cascade controls elsewhere carry real
mechanism coverage; they do not establish a complete original-corpus negative-set journey.
Current provider/assembled acceptance remains at UM-CA10/UM-15, not in this diagnosis.

<a id="dta-014"></a>

## DTA-014 — Prior broad dormancy diagnosis withdrawn; current transfer is assessed separately

**FP-01/03/04/07, DP-16/22/23; companion §1/2/8.** Most old manifestations were removed:
`tests/{validate,consolidate,pool}`, legacy DB/schema registries, old DB tests, legacy alignment/
parity and stored-frame tests. Their deletion is visible in the diff from `599d479`. The former
585/2,429 count and elapsed-time shares are withdrawn; no current proportion was collected.

The independent challenge corrected a proposed narrower diagnosis. `core/keys.py:31–33` explicitly
assigns the frozen conformance vector its role, and `tests/core/test_conformance.py` directly
challenges that implementation. `tests/evaluate/test_equivalence.py` exercises ValueComparator,
which delegates to current MathematicalEvidence/compare_math (`evaluate/equivalence.py:47–54,
186–202`). Although a search of product `src` and `domains` finds no runtime caller of key_claims
or ValueComparator beyond definitions, that absence alone does not establish waste or an invalid
local contract test. Independent reference and pure contract tests are legitimate.

The old broad defect is therefore not reestablished at this baseline. Any assurance transfer gap
must identify the specific supported semantic operation missing its independent counterpart,
as in DTA-004/011, rather than declaring all retained references dormant. Current pure schema/
boundary preparation and scientific algorithms are supported under ADR-0047. This correction
preserves the ID and prior evidence in Git; it authorizes no source or test deletion.

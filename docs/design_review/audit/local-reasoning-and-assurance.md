# Local reasoning and assurance

The [current broad baseline](README.md#baseline) applies to the current source diagnoses below.
This is navigation by responsibility, not another finding register:

- [Semantic definitions and their consumers](semantic-model-and-authority.md).
- [Outcomes, policy and outstanding claim ownership](structure-and-invariants.md).
- [Native custody, admission and recovery](native-integrity.md).
- [Served standing, evidence size and evaluation provenance](served-claims.md).
- [Composition and preparation lifetimes](boundaries-and-composition.md).
- [Necessary versus repeated work](execution-fit.md).

Tests were read where relevant to the evidence claim; the separate
[test account](../test-audit/README.md) retains its own baseline, stated there. Production source
reasoning is not an independent oracle for semantic correctness. Static code inspection is not
actual database, provider, CLI/MCP or release qualification. No full test campaign follows from
this diagnostic refresh.

<a id="da-021"></a>

## DA-021 — Historical correction, not requalified

Evidence citation tooling corrected the earlier free-text citation diagnosis at ad4593f,
2026-10-29. This refresh does not rerun the evidence catalog. That dated correction remains
historical, recoverable in Git before this refresh.

<a id="da-022"></a>

## DA-022 — Historical correction retained

`scripts/check_pins.py` covers workspace Python and Cargo manifests. Inspection of the command
surface during this refresh found no reason to reinstate the former narrow-manifest diagnosis;
`just deps` was not run. The original tested correction remains dated 2026-10-29.

<a id="da-023"></a>

## DA-023 — Historical correction retained

The current repository binding maps binding decisions to principles; the earlier empty-map
premise no longer applies. This is source inspection, not a whole-binding correctness claim.

## Current representative assurance inspection

**Source-inspected 2026-11-05.** `python/corpus-structure/tests/evaluate/test_operation_assessment.py:64–156`
uses literal role/value/location expectations and missing-output cases; source-first and output-first
frames retain different populations. These examples challenge production semantics rather than
merely accepting production validation. They were read, not executed. No inference about every
fixture, oracle or test follows. The separately edited test account keeps independent ownership
and freshness; the dated historical statements above were not renewed by this production audit.

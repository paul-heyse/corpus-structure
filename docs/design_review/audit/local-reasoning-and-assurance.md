# Local reasoning and assurance

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`
([update](README.md#update-2026-11-18-5139eaba3); [baseline and limits](README.md#baseline)).
This page is navigation by responsibility, not another finding register:

- [Current model owners](domain-model-map.md) and
  [semantic definitions and their consumers](semantic-model-and-authority.md).
- [Outcomes, policy and claim ownership](structure-and-invariants.md).
- [Native custody, admission and recovery](native-integrity.md).
- [Served identity and evaluation policy](served-claims.md).
- [Composition, hosts and superseded machinery](boundaries-and-composition.md).
- [Necessary versus repeated work](execution-fit.md).
- [The domain model and execution together, with the test account](model-and-execution.md).

Whether the tests would detect a wrong implementation of the mechanisms described in this
account is the subject of the separate [test account](../test-audit/README.md), which was
refreshed by another engagement on 2026-11-18
([its refresh](../test-audit/README.md#tdm-refresh-2026-11-18)). Production source reasoning is
not an independent oracle for semantic correctness, and static inspection is not database,
provider, CLI, MCP or release qualification. No test campaign follows from this update.

Two assurance observations belong to the test account and are linked, not repeated: several
reuse and skip mechanisms were tested only on the path where reuse is correct
([DTA-044](../test-audit/evidence-and-discrimination.md#dta-044)), and several commits that
introduced them record `runtime not_run`.

<a id="da-021"></a>
<a id="da-022"></a>
<a id="da-023"></a>

| ID | Status at `5139eaba3` | Note |
|---|---|---|
| DA-021 | Corrected, holds | Evidence citations are resolved by `tools/evidence/src/corpus_evidence/citations.py` (file present; not run) |
| DA-022 | Corrected, holds | `scripts/check_pins.py:3–18` covers the uv workspace and Cargo |
| DA-023 | Corrected, holds | The binding's map of binding decisions is populated (`docs/design_review/design_principles/binding/corpus-structure.md:258–263`) |

Earlier text is in Git at `fbd3f2a98` and before.

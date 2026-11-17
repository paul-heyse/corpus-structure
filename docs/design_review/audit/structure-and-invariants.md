# Structure and invariants

**Source `fbd3f2a98`, 2026-11-17** ([baseline and limits](README.md#baseline)). This refresh
established no new finding with its primary home on this page. The run, task and stage
machinery most of these identities described was removed with the legacy execution compiler on
2026-11-16; request, generation, attempt and holder fences now live in
`semantic/sql/data_operation_task_checks.sql` and the claim, renew and release functions of
`semantic/sql/data_operations.sql` (`:624–637, 1245–1353`). Those fences were read as context
for other findings, not audited as a subject.

<a id="da-012"></a>
<a id="da-013"></a>
<a id="da-014"></a>
<a id="da-015"></a>
<a id="da-016"></a>
<a id="da-017"></a>
<a id="da-040"></a>
<a id="da-041"></a>
<a id="da-044"></a>
<a id="da-053"></a>

Earlier text is in Git at `fbd3f2a98`.

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-012 | Changed footprint | The bounded correspondence question now has an enumerated instance: closed sets declared in two models ([DA-072](semantic-model-and-authority.md#da-072)) and facts written by hand beside the declaration ([DA-070](semantic-model-and-authority.md#da-070), [DA-071](semantic-model-and-authority.md#da-071), [DA-074](native-integrity.md#da-074)) |
| DA-013 | Not re-examined | — |
| DA-014 | Not re-examined | Cited sources are gone |
| DA-015 | Not re-examined | — |
| DA-016 | Not re-examined | Cited `orchestrate/policy.py` is gone |
| DA-017 | Not re-examined | Cited sources are gone |
| DA-040 | Not re-examined | Source establishments are now in `semantic/prepare.py`, `types.py` and `sql/closure.sql` |
| DA-041 | No longer applicable | Replaced by the request, generation, attempt and holder fences named above |
| DA-044 | No longer applicable | Cited owners gone; the representative policy now sits in `semantic/rich_decisions.py:39` and `rich_rule_evaluation.py:97`, not examined |
| DA-053 | Changed footprint | `semantic/claim_lifetime.py:132–186` still serializes settle and retain and is used by the demand executor |

# Structure and invariants

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`
([update](README.md#update-2026-11-18-5139eaba3); [baseline and limits](README.md#baseline)).
Every identity on this page was re-read at that source by reading the code that replaced its
cited subject. The run, task and stage machinery that most of them described was removed with
the legacy execution compiler on 2026-11-16. Request, generation, attempt and holder fences
now live in generated programs: the task guard built from the declared lifecycle
(`semantic/data_operation_protocol.py:117–128`), the claim program
(`semantic/data_claim_native.py`), the release program
(`semantic/data_attempt_release_native.py`) and the renew program
(`semantic/data_operation_renewal.py`). Source paths omit
`python/corpus-structure/src/corpus_structure/`.

<a id="da-040"></a>

## DA-040 — Unbounded decimal expansion in the regenerated native canonicalizer and in the Python codec

**Update, 2026-11-18, source `5139eaba3`.** Partly corrected; the decimal case persists. The
2026-10-29 finding was that value admissibility was enforced late and only in part at
boundaries (establishment, NaN, unbounded decimal expansion). The hand-written body of
`identity.sql` at `d78c98765` was equally unbounded (`:8–26` of that file), and the conversion
transcribed it faithfully into the generated program.

**FP-02, FP-05; DP-03.**

*Corrected.* Establishment is checked against the declared `source_admissible` subset at the
agent schema (`semantic/proposals.py:111–114`; `semantic/types.py:344–346`;
`model/semantic/core.yaml:597–601`).

*Persisting.* The native canonicalizer `decimal_canonical`, now a generated typed program,
checks only the lexical pattern of its input (`semantic/data_operation_value_native.py:124–127`),
casts the exponent to `bigint` (`:131–133`) and then expands with
`repeat('0', cast(…, integer))` (`:112–113, 139–149`). Nothing bounds the exponent. The Python
codec `decimal_text` expands with `format(value, "f")` and no bound
(`semantic/value_codec.py:15–20`). A bound exists only in other modules
(`semantic/structural_parsing.py:194`; `semantic/formal_evidence.py:191`).

**Consequence (inferred from source, not executed).** The inputs the original finding used,
such as `1e400000000` and `1e2147483648`, would still fail with an allocation error or a
numeric-range error instead of the classified value refusal, and a smaller exponent that
passes the pattern produces a very large string before any check. A value that should be
refused as inadmissible is instead a resource failure.

**Not established.** The NaN manifestation was not established either way: the boundary puts
`allow_inf_nan=False` into the annotation when finite fields apply
(`semantic/boundary.py:189–191`), so the rebuilt annotation should keep it
(`semantic/types.py:488–496`), but nothing was executed.

## Prior identities on this page

<a id="da-012"></a>
<a id="da-013"></a>
<a id="da-014"></a>
<a id="da-015"></a>
<a id="da-016"></a>
<a id="da-017"></a>
<a id="da-041"></a>
<a id="da-044"></a>
<a id="da-053"></a>

Earlier text is in Git at `fbd3f2a98` and before.

| ID | Status at `5139eaba3` | Note |
|---|---|---|
| DA-012 | Superseded by [DA-072](semantic-model-and-authority.md#da-072) and [DA-086](semantic-model-and-authority.md#da-086) | The question was whether operational closed sets correspond to a declaration. The earlier model is still live with its own copies (DA-072), and task-state literals remain in the kernels beside the declared lifecycle (DA-086) |
| DA-013 | Partly corrected | The CLI now separates database failures with phase and effects, typed refusals and programming errors (`cli/failures.py:1, 37–44, 58–88`; `semantic/refusals.py:23–93`). Domain code still mostly refuses with prose: 3,163 `raise ValueError(` in 265 files of `semantic/`, against 13 constructions of the typed operation refusal (search counts). A plain `ValueError` is not in the expected-refusal set, so the boundary does not classify it. [DA-079](boundaries-and-composition.md#da-079) is one current instance |
| DA-014 | No longer applicable | The native locator function and the HTML path were removed (`48be40472` and earlier). The function survives only in frozen `semantic_alembic` revisions; whether that chain is still deployed was not checked. The unused `LocatorIndex` branch is footprint of [DA-080](boundaries-and-composition.md#da-080) |
| DA-015 | No longer applicable | `consolidate/finalize.py` was removed (`9268b15bf`) |
| DA-016 | No longer applicable | `orchestrate/policy.py` and the pack `policies.yaml` were removed (`a49758618`) |
| DA-017 | No longer applicable | `orchestrate/semantic.py` was removed (`8b7b369a9`). Only the earlier model keeps `AgentReuse.BY_UNIT` (`core/vocab.py:790–794`), which belongs to DA-072 |
| DA-040 | Partly corrected; the decimal case persists | [Section above](#da-040) |
| DA-041 | No longer applicable | The run and task machinery is gone (`64455a0f1`, `8b7b369a9`), and the cause does not recur: the replacement declares a lifecycle with terminal and receipt-required sets, records failures in an immutable table keyed by the exact attempt, and reports lost attempts with a reason (`model/semantic/data-operation-native.yaml:5–13`; `semantic/data_operation_renewal.py:61–93, 178–192`). Whether a request-level aggregate states "partial" was not checked |
| DA-044 | Corrected, holds at new sites | Scientific representatives are a named policy, `min-fact-id-1`, carried with a component identity (`semantic/rich_decisions.py:35–39`; `semantic/rich_rule_evaluation.py:93–97, 923–930`). The display choice is a deterministic minimum, and its comment states it is a presentation choice (`:873–889`). Where entity attributes take their evidence in the successor was not traced |
| DA-053 | Corrected, holds at new sites | Claims are owned by `ClaimOwner` immediately after the claim transaction commits and are renewed, settled or retained through the owner (`orchestrate/data_operations.py:1203–1208, 1237, 1255, 1341, 1378`; `semantic/claim_lifetime.py:79–186, 255–406`). A small inferred residual: input hydration runs inside the claim transaction, after the 300-second lease starts and before renewal can begin (`orchestrate/data_operations.py:1091–1208`); it is bounded by the packet byte limit and was not shown to exceed the lease |

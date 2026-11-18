# Served claims

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`
([update](README.md#update-2026-11-18-5139eaba3); [baseline and limits](README.md#baseline)).
DA-076, DA-077 and the earlier identities on this page were re-read at that source. Source
paths omit `python/corpus-structure/src/corpus_structure/`.

A related integrity question has its home on another page: the source-demand path reads the
working tree's `slices.yaml` while the release archives its own copy
([DA-028](semantic-model-and-authority.md#da-028)).

<a id="da-076"></a>

## DA-076 — The implementation identity of a served read is a hand-kept file list that leaves out modules that shape the answer

**Update, 2026-11-18, source `5139eaba3`.** Stands unchanged. No commit in
`d78c98765..5139eaba3` touched `_query_custody.py`, `serve/rich_queries.py` or
`semantic/demand_queries.py`. The ordinary-edit case that the consequence describes occurred
in the range: the unlisted answer-path modules `semantic/archive_reader.py` (`3ba5daa84`),
`semantic/releases.py` and `semantic/data_operation_protocol.py` changed without moving the
identity. A further overlap appeared: the listed `semantic/native_source_view.py`
(`semantic/demand_queries.py:117–124`) is also an input of the native kernel digest through
the PDF search renderer list, so the edit that restamped the kernel digest at native revision
N29 ([DA-068](execution-fit.md#da-068)) invalidated served cursors and the kernel together.

**FP-04; DP-02, DP-04; CI-10, CI-13.**

Every served read carries an `implementation` digest. It appears in cursors, in
`resource_handle` replays and in the selected-query cache keys, and it is what lets a resumed
page claim it comes from the same code. The digest covers only the files named in the hand
lists of `_query_custody.py:17–135`, whose docstring says it "neither discovers dependencies"
(`:1–5`); `semantic/demand_queries.py:117–124` keeps a second, separate list. The identity is
the listed file digests, nine library versions and the request JSON schema
(`serve/rich_queries.py:71–105`); it does not include the native kernel.

Modules on the rich answer path that are not listed include `semantic/releases.py` and
`semantic/archive_reader.py` (which reconstruct the prepared release used for graph
validation), `semantic/data_operation_admission.py` (the bound model),
`semantic/record_contracts.py` and the generated wire module. A static import closure of
`serve/rich_queries.py` reached about 380 first-party modules against 36 listed (2026-11-17);
many of those are on other paths, so the closure is an upper bound, not the size of the gap.

The six rich statistics query names are also written twice, once for dispatch and once to
choose which sources enter the identity (`serve/rich_queries.py:39–66`). A query added to the
first and not the second would omit the module that computes it.

**Consequence.** Inside one MCP process this is harmless: custody refuses any reload
(`_query_custody.py:136–260`). Across processes it is not. A CLI cursor, a `resource_handle` or
an explicit pin survives an edit to an unlisted module, and the resumed request replays
ordinals over a population derived by different code. A continued page can then skip or
duplicate rows with no refusal. Code is edited constantly in this project's working loop, so
the case is ordinary. The reverse also holds: a comment edit in any listed file invalidates
every cursor.

**Contrary evidence.** ADR-0124 deliberately defines the identity as naming the running code,
with stat-based drift detection, and that mechanism is implemented and sound. The gap is what
the list covers. Whether the identity is meant to cover the answer's whole code closure or only
code likely to change answers is not stated in the ADR. On the native side the gap is narrow:
answer-shaping native SQL comes from generators that are not on the list, but their effect
reaches an answer only after a kernel deployment, and a read acquired under another kernel is
treated as not present (`semantic/data_read_boundary_native.py:98, 126`). Pinned cuts also
carry the release id, which covers the native capture. The residual gap is Python-side answer
code.

**Footprint.** Established for the omission and the duplicated list; the paging consequence is
likely.

<a id="da-077"></a>

## DA-077 — The archived scientific policy is a description of the comparison kernel, not derived from it

**Update, 2026-11-18, source `5139eaba3`.** Stands unchanged. Neither
`semantic/scientific_evidence.py` nor `semantic/rich_policy_binding.py` has a commit in
`d78c98765..5139eaba3`, so the cited lines hold.

**FP-04; DP-02, DP-04; CI-13; H19.**

`require_scientific_policy` requires a release's archived `operation/scientific-policy.json` to
equal a recipe rebuilt in code (`semantic/scientific_evidence.py:246–255`). The recipe is a
hand-written description of the kernel, for example `"bounds": [0.25, 3]` and the
`numeric_method` strings (`:192–243`). The kernel uses its own literals
(`rng.uniform(0.25, 3, …)`, `:1301`).

**Consequence.** The identity and the behavior can move independently:

- a kernel edit leaves the recipe and every archived release unchanged, so existing releases
  keep validating while computing differently;
- a wording edit to the recipe makes every release refuse.

The recipe is also rebuilt on each call, including several schema generations, for each rule
evaluation, each scientific evaluation, each new comparator per distinct macro set and each
reference comparison scope (as read on 2026-11-17), and for each rich context binding
(`semantic/rich_policy_binding.py:22–30`), although both the archived artifact and the process
code are fixed.

**Contrary evidence.** Archiving the policy and refusing on mismatch is the right shape, and
the DA-034 correction (one shared owner, separate policies) still holds.

**Footprint.** Established for the duplication and the per-call rebuild; the number of
comparators per document is not known.

## Prior identities on this page

<a id="da-035"></a>
<a id="da-036"></a>
<a id="da-037"></a>
<a id="da-038"></a>
<a id="da-039"></a>
<a id="da-050"></a>
<a id="da-051"></a>
<a id="da-061"></a>
<a id="da-064"></a>
<a id="da-066"></a>

Statuses were established on 2026-11-18 at `5139eaba3` by reading the code that replaced each
cited subject. Earlier text is in Git at `fbd3f2a98` and before.

| ID | Status at `5139eaba3` | Note |
|---|---|---|
| DA-035 | No longer applicable | `serve/journey.py` was removed (`bcff594c2`). The successor was checked only lightly: whether coverage absence can now be stated was not traced |
| DA-036 | No longer applicable | `semantic/query.py` was removed (`957ff2231`). Served rows carry a per-population standing label, a constant such as `native-selected-operation` (`serve/contribution_facets.py:79, 296`; `serve/source_decision_journey.py:298`); whether successor reads give a per-fact selection status that distinguishes rejected, ambiguous or deselected facts was not examined |
| DA-037 | No longer applicable | `evaluate/semantic.py` was removed (`7fc25ca02`). The status is firm for the removed subject only: whether the replacement evaluation separates not-matched from not-comparable was not examined (`evaluate/operation_fitting.py:103` does name an incomparable reason). `evaluate/split_decisions.py` has no importer ([DA-080](boundaries-and-composition.md#da-080)) |
| DA-038 | No longer applicable | `serve/read.py` and `serve/queries.py` were removed (`bcff594c2`). A low-weight residue: nine serving modules import the private `_cursor` and `_decode` from `semantic/demand_queries.py:43–54`, and `serve/demand_journey.py:3–10` re-exports them. That is a shared primitive that is private only in name, not the original duplicated route |
| DA-039 | No longer applicable | `serve/explain.py` and the statistics `queries.py` were removed (`5aae3c780`, `bcff594c2`). Successor reads are bounded: rich reads have `limit` and `max_bytes` (`serve/rich_queries.py:130, 144`), and operation explanation is one operation with one bounded observation page (`semantic/operation_reporting.py:150–212`) |
| DA-050 | No longer applicable | `cli/explain.py` (`bcdc8d214`) and `serve/journey.py` are gone. Reads bind an exact demand (`cli/selected_results.py:23`) and continue through a pinned `resource_handle` (`serve/demand_context.py:140`; `semantic/demand_queries.py:296`). Not every follow-up surface was surveyed |
| DA-051 | Corrected, holds | Recognition declares its identity assurance and admits a managed generation only when the artifact digests match (`ingest/pdf_recognition.py:65–73, 152–171`). External results record actor and model assertions, labelled as assertions, and check them natively (`semantic/external_receipts.py:24–25`; `semantic/external_execution_native.py:266–267`). Not traced end to end |
| DA-061 | Corrected, holds | `8dc0bac00` corrected both parts: the recipe holds a list of witnesses keyed by original digest and pointer (`model/semantic/section-text-recipe.json`, two entries), and the Reader resolves the recipe from the retained release (`ingest/pdf_hierarchy.py:354–380, 382–427`). The production path still refuses when the installed bytes differ (`:346–351`), which is a refusal, not suppression |
| DA-064 | Corrected, holds | A skip requires every cue to be negative, otherwise the result is `unassessed` (`semantic/visual_routing.py:235–239`); a blank page requires verified original bytes (`:228–232, 744–761`) |
| DA-066 | Corrected, holds | Selection by occurrence and cell, with `after` and `limit`, is pushed into the native read (`semantic/visual_read_native.py:75–170`), and the Reader charges only the returned rows (`serve/pdf_visual_evidence.py:5–45`). The cost of the native scan was not examined |

# Served claims

**Interface-checked by source inspection.** The page was read as a whole on 2026-11-17 at
source `fbd3f2a98` ([baseline and limits](README.md#baseline)). DA-076 and DA-077 were re-read
on 2026-11-18 at source `d78c98765` ([refresh](README.md#refresh-2026-11-18)); the
earlier-identity table keeps its 2026-11-17 date. Source paths omit
`python/corpus-structure/src/corpus_structure/`.

<a id="da-076"></a>

## DA-076 — The implementation identity of a served read is a hand-kept file list that leaves out modules that shape the answer

**Refresh, 2026-11-18, source `d78c98765`.** Stands unchanged. No commit in
`1afa63f88..d78c98765` touched `_query_custody.py` or `serve/rich_queries.py`. Current sites:
the hand lists at `_query_custody.py:17–127` (docstring `:1–5`), the second list at
`semantic/demand_queries.py:117–124`, and the statistics query names written again at
`serve/rich_queries.py:39–66`. The identity is the listed file digests, nine library versions
and the request JSON schema (`serve/rich_queries.py:71–105`); it does not include the native
kernel. `semantic/releases.py`, `semantic/archive_reader.py`,
`semantic/data_operation_admission.py` and the generated wire module remain unlisted. The
conversion strengthened the contrary evidence for native SQL, as recorded below.

**FP-04; DP-02, DP-04; CI-10, CI-13.**

Every served read carries an `implementation` digest. It appears in cursors, in
`resource_handle` replays and in the selected-query cache keys, and it is what lets a resumed
page claim it comes from the same code. The digest covers only the files named in
`_query_custody.py:17–127`, whose docstring says it "neither discovers dependencies" (`:1–5`);
`semantic/demand_queries.py:117–124` keeps a second, separate list.

Modules on the rich answer path that are not listed include `semantic/releases.py` and
`semantic/archive_reader.py` (which reconstruct the prepared release used for graph
validation), `semantic/data_operation_admission.py` (the bound model),
`semantic/record_contracts.py` and the generated wire module. A static import closure of
`serve/rich_queries.py` reaches about 380 first-party modules against 36 listed; many of those
are on other paths, so the closure is an upper bound, not the size of the gap. The native SQL
kernel is not part of the identity.

The six rich statistics query names are also written twice, once for dispatch
(`semantic/rich_queries.py:460–470`, as read on 2026-11-17) and once to choose which sources
enter the identity (`serve/rich_queries.py:39–66`). A query added to the first and not the second would omit the
module that computes it.

**Consequence.** Inside one MCP process this is harmless: custody refuses any reload
(`_query_custody.py:136–200`). Across processes it is not. A CLI cursor, a `resource_handle` or
an explicit pin survives an edit to an unlisted module, and the resumed request replays
ordinals over a population derived by different code (`serve/rich_queries.py:170–187`;
`semantic/selected_query_cache.py:163–165`). A continued page can then skip or duplicate rows
with no refusal. Code is edited constantly in this project's working loop, so the case is
ordinary. The reverse also holds: a comment edit in any listed file invalidates every cursor.

**Contrary evidence.** ADR-0124 deliberately defines the identity as naming the running code,
with stat-based drift detection, and that mechanism is implemented and sound. The gap is what
the list covers. Whether the identity is meant to cover the answer's whole code closure or only
code likely to change answers is not stated in the ADR.

The conversion narrowed the gap on the native side (2026-11-18). Answer-shaping native SQL now
comes from generators that are not on the list (`semantic/demand_result_native.py`,
`semantic/data_operation_read_native.py`, `semantic/data_operation_projections.py`), but their
effect reaches an answer only after a kernel deployment, and a read acquired under another
kernel is treated as not present (`semantic/data_read_boundary_native.py:84–92`). Pinned cuts
also carry the release id, which covers the native capture. The residual gap is Python-side
answer code, as before.

**Footprint.** Established for the omission and the duplicated list; the paging consequence is
likely.

<a id="da-077"></a>

## DA-077 — The archived scientific policy is a description of the comparison kernel, not derived from it

**Refresh, 2026-11-18, source `d78c98765`.** Stands unchanged; the DuckDB rewrite did not
touch it. Current sites: the recipe at `semantic/scientific_evidence.py:192–243`, the
comparison at `:246–255`, and the kernel literal at `:1301`. A third comparison site was
found, which also rebuilds the recipe on each call: `semantic/rich_policy_binding.py:22–30`
(the artifact is written at `semantic/rich_knowledge_sources.py:81–82`).

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
reference comparison scope (`semantic/rich_scientific.py:182, 260–264`;
`scientific_evidence.py:940–943, 1129–1133`, as read on 2026-11-17) and each rich context
binding (`semantic/rich_policy_binding.py:22–30`), although both the archived artifact and the
process code are fixed.

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

Earlier text is in Git at `fbd3f2a98`.

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-035 | No longer applicable | `serve/journey.py` is gone; paging is `serve/demand_journey.py` and `semantic/demand_queries.py` |
| DA-036 | No longer applicable | Standing is carried in native frontier and use rows |
| DA-037 | No longer applicable | Caller gone; `evaluate/split_decisions.py` now has no production importer ([DA-080](boundaries-and-composition.md#da-080)) |
| DA-038 | No longer applicable | Cited read modules are gone |
| DA-039 | No longer applicable | Explanation is `semantic/operation_reporting.py:150–212`; rich relation depth is bounded in the request |
| DA-050 | No longer applicable | Pinned continuation uses `resource_handle` and the read pins |
| DA-051 | Changed footprint | Recognition identity assurance stands (`ingest/pdf_recognition.py:71, 149–171`); external packets carry actor and model assertions. Not traced end to end |
| DA-061 | Changed footprint | The formula Reader now resolves the recipe from the retained release (`ingest/pdf_hierarchy.py:353–380`). The single-witness representation was not examined |
| DA-064 | Corrected | The only route builds unassessed page signals; the skip-without-trigger branch is unreachable, and a skip requires a verified blank body (`semantic/visual_routing.py:587, 623–630, 744–761`) |
| DA-066 | Likely corrected | Selection and continuation are pushed into the native read (`serve/pdf_visual_evidence.py:34–74, 399–423`); the native scan was not examined |

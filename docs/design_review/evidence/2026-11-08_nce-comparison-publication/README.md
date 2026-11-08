# Protected comparison and gap delivery

This driver serves [NCE-09-A2](../../../plans/next-corpus-enrichment/rooted-assembly-and-navigation.md#nce-09-audit).
It keeps source-only authoring separate from the candidate, its publication, and its
ordinary Reader, CLI, fresh MCP and detached delivery. All comparison authoring in
this workflow belongs to development. A comparison can have independently supported
source-qualified facets and explicitly unestablished applicability.

## Select and freeze

Use the whole-book native source inventory to select two exact source passages before
reading candidate reports. Physical pages 151 and 173 are the first lead. They
repeat one terminology convention for mutually independent random variables in
discrete and continuous contexts. A second lead on physical pages 30–32 compares
union additivity in Property 4 and Theorem 1.4. The theorem explicitly reduces
to the property in the disjoint case. Confirm exact native projection before
binding either comparison. Keep the physical page, original view and exact passage
pins. A source-first author can record unresolved facets.

In a protected directory, prepare a JSON specification with `project_id`, `release_id`,
`configuration`, and `frame`. The configuration is a `StructuralComparisonConfig`
binding both selected passage IDs and the exact retained predicate-reading references.
The `StructuralEvaluationFrame` has the same `inputs`, operation `qualified_comparison`,
direction `source_first`, rubric `independent-structural-comparison-1`, an empty product
list, and explicit source groups, source opportunities and exposure history. Include
`assign_origin` with `origin_group`, `source_uris` and `provenance` only when the
source needs its native development partition registered. The full book remains one
origin. Write one reference opportunity per assessed source facet or passage.

Set `driver` to `docs/design_review/evidence/2026-11-08_nce-comparison-publication/comparison_publication.py`.
Use a protected destination. Locate source pieces by physical page and a source
literal. For a targeted scoped run, prepare a selection file with exactly two
`StructuralPassageSelection` entries under `passages` and the selected
`project_id`, `release_id`, `question`, `scope`, `inventory_id` and `policy_id`.

```sh
uv run python "$driver" locate SOURCE_RUN 30 'disjoint subsets'
uv run python "$driver" prepare-scope selections.json scoped.json
uv run python "$driver" run scoped.json scope scoped-attempt
uv run python "$driver" readings SCOPED_RUN LEFT_PASSAGE_ID
uv run python "$driver" readings SCOPED_RUN RIGHT_PASSAGE_ID
```

The two reading selectors belong to the coordinator's comparison configuration.
Keep them separate from the source-only packets supplied to the authors.

```sh
uv run python "$driver" freeze comparison.json frozen.json
uv run python "$driver" packet comparison.json frozen.json source-only.json
uv run python "$driver" submit frozen.json a-receipt.json A AUTHOR_A a.json
uv run python "$driver" submit frozen.json b-receipt.json B AUTHOR_B b.json
uv run python "$driver" submit frozen.json c-receipt.json C ADJUDICATOR c.json \
  --parents a-receipt.json b-receipt.json
```

Give each independent author the source packet, which includes the released public
statement shape. Authors supply their own `StructuralAuthoredReference` bytes. The adjudicator
receives the exact A/B bodies and the retained parent receipts. A supported public
statement must cite both frozen passages and specify the exact independently supported
whole statement at `["public_statement"]`. For an absent or unclear facet, preserve
its limits in the authored statement. Keep disagreements and unsupported cases in
protected custody. Derive independent expectations directly from the frozen source.
The native publication owner accepts only an exact supported C match.

## Publish and read

```sh
uv run python "$driver" run comparison.json candidate candidate-attempt \
  --freeze-receipt frozen.json
uv run python "$driver" run comparison.json publish published-attempt \
  --freeze-receipt frozen.json --c-receipt c-receipt.json --product-id PRODUCT_ID
uv run python "$driver" run dossier.json dossier dossier-attempt
uv run python "$driver" verify gap.json PRODUCT_ID actionable --side left --side right \
  --selection review.json
uv run ci review export review.json --exact-closure --json
uv run ci review inspect --result RESULT_ID --json
uv run ci review verify BUNDLE_PATH --manifest-sha256 RETAINED_DIGEST --json
```

Use the `completed.json` receipts to bind the candidate product, published result and
dossier. A failed publication retains its attempted run. Resume finalization by exact
run ID when its source-ready receipt establishes that recovery is applicable.

The dossier specification contains `project_id`, `release_id` and a
`StructuralDossierConfig` in `configuration`. Select the actual published comparison
as an exact predecessor, and include the separately retained authentic definition
root, its source passages, and the comparison passages. To verify an actionable gap
for both sides, leave both comparison-side selections empty while retaining the
comparison predecessor. For left-only and fully bound controls, use independently
qualified side readings and their existing applicability and relationship predecessors.
A gap request pins the exact comparison and dossier runs, cuts and selected task IDs.
Pass `--journey journey.json` to also verify the source-decision journey through the
same two producers. The journey carries an exact native opportunity and selects the
corresponding comparison reading by its retained contribution ID. The emitted
review selection includes both backing structural products.

Retain only safe receipt identities, outcomes and independently established public
statements. Keep source-only author packets, protected pass bytes and speculative
drafts outside tracked evidence. A controlled case establishes the workflow at its
controlled scope. Preserve publication refusal or missing
source prerequisites with the same audit finding.

## Controlled workflow

On 2026-11-08, `uv run ci test --json -- python/corpus-structure/tests/semantic/test_protected_comparison_gap_native.py`
passed in managed result `284b284ad0e34380b9c7c0e0822e58cd`. The isolated native
fixture used two distinct occurrences of one literal. It preserved separate
controlled A/B/C records, published the exact protected comparison, and returned
both actionable sides from a dossier that inspected the comparison. The joined
Reader traced the represented source through the observed comparison to empty
dossier membership. Detached verification accepted the exact source closure and
refused a consistently resealed support substitution. The conflicting scope
request also refused. This qualifies the controlled workflow.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**next-corpus-enrichment**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Controlled protected comparison and detached gap delivery](records/nce.protected-comparison-controlled.json) | NCE-09 | passed | NCE-09-A2, NCE-10-A2 | 2026-11-07 |
<!-- evidence-index:end -->

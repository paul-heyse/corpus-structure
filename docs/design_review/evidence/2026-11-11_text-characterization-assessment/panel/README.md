# Frozen source-first chapter-and-facet panel

**Source preparation and protected frame creation passed · 2026-11-11.** Reference set **40**
contains **21 units, 61–81**, with **26 opportunities** across all12 chapters and all nine
assessment facets. This is a purposive source panel, not exhaustive semantic annotation or a
probability sample. Full-book page/family execution coverage has a separate denominator.

Source is completed capture run496, cut614, project `nce-grinstead-snell-full-book`, original
document45 and integrated task1627, digest
`35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb`.
The source release is `release:c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189`.
All316 direct source views were inspected only as original native text/hierarchy, comprising
7,551 source blocks. Source display recognition remains partial and inline/cell coverage unknown.
No source-health strengthening follows from this panel.

## Frozen inputs and source-only boundary

- [Manifest](manifest.json): precise selected view/occurrence identities, questions, declared families,
  original text and ordered real extents. Its SHA-256 is frozen in reference-set provenance.
- [Sample](sample.json): V3 source-first frames, frozen question text, source scopes, original pins,
  source group, development partition and exposure declaration.
- [Reference-set receipt](frozen-reference-set.json): actual native set/unit identities and frames.
- [Author packet index](author-packets.json): 21 protected source-only packets,949,821 bytes total.
  Each `author-unit-ID.json` was acquired through the protected `author_packet` operation and
  contains original source context and frozen question metadata, with no selected producer outputs.
- [Source inventory summary](source-inventory-summary.json): all316 source view titles/hierarchy
  and scope sizes; the local full-text selection cache is ignored rather than committed again.

The selection script reads `source_units`, `load_source_view(analysis=False)`, original native
pieces/parents and exact source bindings. It never invokes `annotation_inputs`, `layout_for`,
a tokenizer, an NLP model or characterization output reads. Regular native examples are selected
from intact prose blocks in source order before outputs exist. Semantic and challenge examples
are selected from source-side cues, with no success/alignment filtering. Chapter markers and source
ordering are explicit selection metadata, never production dispatch rules.

The panel includes six native sentence questions, six token-boundary questions, one short native
dependency question, source-semantic role/scope/binding/choice/provider questions, source-side
coverage and preservation questions, and three actual formal-source questions:
`\omega_1` (`formal.identifier`), `.3\le x<.7` (`formal.interval`) and
`X_1+X_2+X_3+X_4` (`formal.math`). Future layer/choice IDs and actual runtime failure judgments
are deliberately deferred to output-first assessment.

All opportunities freeze `source_state: uninspected`. Fresh independent authors judge the source
states; they are not required to call a semantic facet stated merely because source text exists.
No expected answer was generated during panel preparation.

## Operations

Preparation used `uv run python prepare_panel.py inventory`, then `select` and `frames` from
this folder's script path. Only selected packets and inventory headers are committed; ignored
source caches and superseded draft packets remain local. Re-running selection is not authority
to change the already frozen set.

Protected creation **passed**:

```sh
uv run ci golden operation-create --from-run 496 --source-cut 614 \
  --label tc10-chapter-facet-panel-1 --split dev \
  --guideline characterization-reference-1 \
  --guideline-text domains/statistics/characterization-reference-guideline.md \
  --partition development \
  --sample docs/design_review/evidence/2026-11-11_text-characterization-assessment/panel/sample.json \
  --project nce-grinstead-snell-full-book --json
```

It returned set40 and units61–81 before book-primary execution or output inspection.
`author_packet` acquisition subsequently **passed** for all21 units. Independent A/B authoring,
C adjudication and semantic grading are **not_run** by this source-preparation assignment.

Protected packets can be re-read without inference, for example:

```sh
uv run ci golden operation-packet --unit 61 --pass A \
  --project nce-grinstead-snell-full-book --json
```

Read-only correspondence verification **passed**: native set40 frames equal the submitted
sample, frozen provenance matches the exact manifest SHA-256, all21 author packets are
source-first with no selected outputs, all26 opportunity identities are distinct, and the
selected population covers all nine facets and all12 chapters. Script compilation and scoped
`git diff --check` also **passed**. These establish source custody and selection, not reference
answer quality or producer correctness.

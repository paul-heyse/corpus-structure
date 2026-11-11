# Source-only binder/site supplement

Prepared on 2026-11-11 against authentic source capture 496, completed cut 614, project `nce-grinstead-snell-full-book`, archived release `c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189`. This adds two source-only questions under guideline `characterization-reference-2` and rubric `chapter-facet-task-semantics-1`.

The earlier anaphoric-antecedent questions numbered 15/22 in reference sets 40/41 retain their original frozen wording and opportunities. `context.binding` declares binder-to-variable-site hypotheses; it does not define a directed-anaphoric-antecedent assessment contract. Preserve that assessment-contract unavailability separately from a language error. This supplement adds applicable source opportunities without rewriting either earlier set.

The selected original passages begin “Let X be…” in distinct sections:

| SourceView | Original section | Original block |
|---|---|---|
| 477 | Probability | `#/texts/21771` |
| 479 | Random Numbers | `#/texts/5005` |

The equal-spelled `X` appears in distinct source-local declarations. The two opportunities retain whole original blocks and their ordered real extents, plus neighboring original blocks/hierarchy as context. Selection used only the pre-existing original source inventory and authenticated retained source reads; no producer output, parse, reference pass or expected binding relation was read or authored. Chapter SourceViews were unproduced when selected, according to the coordinator's execution boundary; no current producer-status query was used to select for success.

The questions require family `context.binding`, task `binding`, role scheme `contextual-source-hypotheses-1`, relation `declared_binding_site`. Independent authors identify the literal binder cue and explicit variable sites, their directed relation and hypothesis standing, scoped to the inspected source-local declaration. The frozen source states remain `uninspected`; they do not pre-assign the independent answer. Authors may preserve unresolved/inapplicable source and choose an honest witness or explicitly closed slot boundary. No scientific or anaphoric relation is substituted for this contract.

The source base is exact task 1627 / `integrated` / digest `35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb`. Original display coverage remains partial and inline/cell coverage unknown. Source presence and this small purposive supplement do not establish book-wide binding accuracy or complete source recognition.

Reproduction uses `prepare_supplement.py prepare`, then the existing protected owner:

```sh
uv run ci golden operation-create --from-run 496 --source-cut 614 \
  --label tc10-source-binder-supplement-1 --split dev \
  --guideline characterization-reference-2 \
  --guideline-text domains/statistics/characterization-task-reference-guideline.md \
  --partition development \
  --sample docs/design_review/evidence/2026-11-11_text-characterization-assessment/task-panel/binder-supplement/sample.json \
  --project nce-grinstead-snell-full-book --json
```

Protected creation **passed on 2026-11-11**: actual reference set **42**, units **103** (view 477) and **104** (view 479). [frozen-reference-set.json](frozen-reference-set.json) is the exact CLI receipt. Protected packet delivery also **passed** with `prepare_supplement.py packets`: [author-unit-103.json](author-unit-103.json) and [author-unit-104.json](author-unit-104.json), indexed in [author-packets.json](author-packets.json), total 102,078 bytes.

The frame/manifest attestation **passed on 2026-11-11**: both native-receipt frames equal their submitted sample frames, receipt provenance authenticates the exact manifest SHA-256, both opportunities remain uninspected, source-only view/layer/output bindings remain null/empty, and both protected packets expose no selected producer outputs. `uv run python -m py_compile .../prepare_supplement.py` **passed**. No independent expected answers are included in this folder.

Independent authors read the actual protected packet's `source_frame.evaluation_frame`, supplied original source context and the public `SemanticTaskReference` contract in `evaluate/task_semantics.py`. They copy the new frame envelope and independently author the precise source-local task, without importing a prior author's or a producer's relation. The task question and asserted family are distinct from the author's judged source state and expected relation.

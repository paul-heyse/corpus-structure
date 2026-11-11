# Source-only binary formal control

Frozen on 2026-11-11 as **reference set 44, unit 107**. This is one additional control against authentic source capture 496/cut 614, project `nce-grinstead-snell-full-book`, release `c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189`, guideline `characterization-reference-2`, rubric `chapter-facet-task-semantics-1`. Earlier reference sets 40–43 remain unchanged.

The exact source occurrence is the complete formula-labeled item `k-1`, native pointer `#/texts/10583`, SourceView 577 (“Negative Binomial Distribution”), projection offsets 457–460, projection digest `f8e2d8c6b44ab52b2b65704a97eba031eddcd51d360d23a67c6f4752f00442cc`. It has two distinct written operands and one operator, so no multi-operator association or implicit-parenthesis decision is needed. Source selection used only the existing original inventory and exact source binding; it did not inspect producer output or select for success. According to the coordinator's execution boundary, this chapter source was unproduced when the frame froze.

The source-only question requires `formal.math`, task `formal`, role scheme `formal-children-v1`. Independent authors assess the typed written operator, directed ordered operand identity and variable occurrence under an honest witness/complete-slot scope. The question contains no expected operator value, normalized atom identity or AST. It does not ask for algebraic solving, commutation or scientific interpretation. The frozen opportunity remains `uninspected` until independent authors judge the supplied source.

[manifest.json](manifest.json) records the single selected opportunity; [source-view-577.json](source-view-577.json) supplies the original formula coordinates and neighboring original prose/hierarchy. [sample.json](sample.json) is the submitted V3 source frame and [frozen-reference-set.json](frozen-reference-set.json) the exact protected native creation receipt. Source health remains inherited: display partial, inline/cell unknown; this control makes no complete formula-recognition or book-wide accuracy claim.

Reproduction:

```sh
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/task-panel/binary-formal-control/prepare_control.py prepare
uv run ci golden operation-create --from-run 496 --source-cut 614 \
  --label tc10-source-binary-formal-control-1 --split dev \
  --guideline characterization-reference-2 \
  --guideline-text domains/statistics/characterization-task-reference-guideline.md \
  --partition development \
  --sample docs/design_review/evidence/2026-11-11_text-characterization-assessment/task-panel/binary-formal-control/sample.json \
  --project nce-grinstead-snell-full-book --json
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/task-panel/binary-formal-control/prepare_control.py packets
```

Protected frame creation **passed, 2026-11-11**. No primary-product or reference-pass read, normalization, parsing, NLP call or expected-answer authorship occurred in this preparation. This is the bounded final binary formal control; no additional inventory was created.

Protected source-only author-packet delivery **passed, 2026-11-11**: [author-unit-107.json](author-unit-107.json), 52,912 bytes, indexed in [author-packets.json](author-packets.json). Exact frame/sample identity, manifest SHA-256, original three-character formula extent, uninspected state and absence of producer-output bindings **passed**. `uv run python -m py_compile .../prepare_control.py` **passed**.

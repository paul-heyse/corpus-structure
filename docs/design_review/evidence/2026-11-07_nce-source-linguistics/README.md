# NCE source and linguistic replay

The [next corpus enrichment coordinator](../../../plans/next-corpus-enrichment_2026-11-07.md)
owns acceptance. This replay selects the two archived GS120 organized products that contain
the three native-only captions. It compares their regenerated views to the original
projections, then uses the ordinary artifact candidate producer and its native replay. It
separately selects the original retained annotations for the probability integral, Huygens
historical contrast and constant-density cases. Those cases keep their original source
expectations. Caption reachability and independently supported semantic attachment remain
distinct outcomes. [Frozen caption and reference controls](../2026-11-06_wce-completion-repair/source-references/README.md) · [Frozen benefit account](../2026-11-06_wce-gs120/assessment/benefit-account/README.md)

The initial NCE development revision was `semantic_nce_evidence_guards`. Candidate
`9dbcdb9368b549cd8ba15fb485185db0` followed the installed preview, apply, register and
deploy route. The development deployment passed on 2026-11-07 with managed result
`ed6a7e3d17614853a6e4a4051d453a6e`. It admitted release
`release:d16c5b3f09a4b73c52369a9a999fc31847be91ce4602d4a13d5ade5af215311a`
on `corpus_structure_dev`, dedicated PostgreSQL 18 on port 5434. Project activation and
result promotion remain separate operations.

Reproduce the bounded work through [the replay driver](replay.py). The driver uses the
project's scoped execution owner to register an exact method graph and selected original cuts.

```sh
uv run python docs/design_review/evidence/2026-11-07_nce-source-linguistics/replay.py \
  build/nce-source-linguistics/attempt-01 \
  --release release:d16c5b3f09a4b73c52369a9a999fc31847be91ce4602d4a13d5ade5af215311a
uv run ci review export build/nce-source-linguistics/attempt-01/selection.json --exact-closure --json
uv run ci results export EXPORT_ID --role bundle --json
uv run ci review verify BUNDLE_PATH --json
```

The first deployment invocation `23749c3958044fa5bc40bc72e98f4985` settled migration and
archive, then exposed a stale expected descriptor hash at admission. The CLI now takes its
expected descriptor from the installed revision's hash-bound admission artifact. Preview
`751d21a149fe45be9aadf256faf560fc` exposed a separate refusal-reporting problem when the
report compiler depended on the invalid declarations. The installed CLI now delivers the
original preparation diagnostics even when typed report compilation also fails. The initial
native authoring failure `93d2e82030954dcc818dc1ce13b49d7f` was retained. A rollback-only
PostgreSQL compilation diagnosis identified the PL/pgSQL expression that needed correction.

## Development results

- **NCE-01, passed.** Source runs 208/cut 289 and 209/cut 291 regenerated views 157–159.
  Artifact run 210/cut 293 nominated all three frozen supported pairs by exact code.
  Two more caption occurrences became available in view 159. The exact guard retry
  passed, and the three malformed projection controls were refused.
  [Source views](caption-replay.json) · [Pair controls](caption-controls.json) · [Native guard](caption-guard.json)
- **NCE-02 initial slice.** Scoped run 217/cut 303 and definition run 218/cut 305 used the
  original retained linguistic products. The full probability subject now attaches to
  the integral. Huygens' assumption and historical contrast remain visible and the
  performed definition was withheld. That definition run retains the local constant-density
  mention. Run 222, cut 313 recovers its exact antecedent from original view 147 while the
  named operation preserves the local mention at 296–314. The retained dependency parse
  places part of the equation outside the nominal subtree. The bounded rule uses the matching
  noun phrase, the attached “such that” restriction and the original sentence boundary.
  [Linguistic controls](linguistic-controls.json) · [Antecedent replay](antecedent.json) · [Native host guard](predicate-guard.json)
- **Initial qualifier replay, partial.** Native run 219 exposed an incorrect provisional
  host for Event F. Run 220, cut 309 retains the complete compound antecedent with unresolved
  host candidates and withholds the attachment. The variance, parameter and zero-wait cases
  retain located frame context. The normal-density statement explicitly names “with parameters
  µ and σ” at 14593–14616, followed by “defined” at 14620–14627. The retained parser attaches
  σ as the passive subject. The existing `defining/nominal_follows` rule recognizes the
  defining host, and a separate parameterization witness needs to bind both parameter tokens
  and pass native admission. The variance premise and correlation definition occupy adjacent
  sentences in one exercise item. They need a dedicated premise-to-host witness for the
  shared X and Y. The zero-wait phrase clarifies the population counted in that clause.
  Its relation to Little’s law, the equilibrium premises and the proof require separate
  evidence. This initial replay lacked a cross-block layout witness. The completion replay
  below covers the explicit list fixture and the normal parameter note.
  [Additional qualifier cases](additional-qualifiers.json)
- **Consumer delivery, passed.** The CLI and fresh MCP returned the same retained frame.
  `uv run ci review verify BUNDLE_PATH --json` passed on the exact-closure export and
  replayed frame evidence from the original annotation reports.
  [MCP receipt](mcp-receipt.json) · [Detached receipt](review-receipt.json)

## Antecedent decision

The retained spaCy token heads and source boundaries supply a unique match for this case.
The proposal keeps the complete source restriction even when the equation spans tokens whose
dependency heads differ. The rule preserves the local mention when two nominals compete,
the prior sentence is outside the selected passage, or the occurrences are in distinct
native pieces. The definition proposal keeps its private standing.
[spaCy Span API](https://spacy.io/api/span/) · [Bounded replay](replay_antecedent.py)

The final development replay passed on 2026-11-07. Run 222 and cut 313 returned the same
component through `uv run ci structure list` and fresh MCP. The detached bundle verified
exact source closure and carries the original named operation with both spans.
[Delivery receipt](antecedent-delivery.json)

```sh
uv run ci test --json -- \
  python/corpus-structure/tests/methods/test_definition_applicability.py \
  python/corpus-structure/tests/ingest/test_definition_rules.py \
  python/corpus-structure/tests/semantic/test_structural_source_annotations.py \
  python/corpus-structure/tests/semantic/test_structural_native_replay.py
```

The pinned GLiNER2.5 checkpoint ran the JointIE schema with typed endpoints and at most
one tail per mention. Both tested thresholds missed the frozen link and proposed a reversed
link in the missing-antecedent control. The model remains a candidate source for a separately
evaluated fallback. Lark's positioned grammar is available when a delimited formal language
owns the condition. SymPy and Z3 require source-bound operands and assumptions before they
can test a mathematical interpretation. The retained PDF prose here already supplies a
complete location for the restriction.
[GLiNER2.5 probe](probe_antecedent_model.py) · [Observed results](gliner2-antecedent-observations.json)
· [GLiNER2.5 JointIE](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/tutorial/15-joint_ie.md)
· [Lark parser configuration](https://lark-parser.readthedocs.io/en/stable/classes.html)
· [SymPy assumptions](https://docs.sympy.org/latest/modules/assumptions/refine.html)
· [Z3 solver guide](https://microsoft.github.io/z3guide/docs/logic/intro/)

## Qualifier scope completion

**Tested in development, 2026-11-07.** Scoped relations v5 replayed the same original
Event F, positive-variance, normal-parameter and zero-wait selections and added the frozen
inline formula occurrence view. Run 224, cut 315 contains the five expected attachments and
exact Z. Population inclusion has its own qualifier kind. The normal positivity note cites
the admitted parameterization relation as its cross-block witness. The three conditional
premises retain their exact source wording as escape conditions. The list inheritance
mechanism passed a two-item native fixture and refused changed membership and clipped scope.
The retained “following two densities” lead-in in view 146 produced zero inherited qualifiers.
Its coordinate and native pointer are in the replay receipt.

Run 223 failed in the enclosing predicate admission function because PostgreSQL grouped a
JSON containment expression incorrectly. The rollback-only preflight passed on all five
original views after the fix. The exact forward candidate deployed to development as
`semantic_nce02_scope_guard`. The current Reader, installed CLI and fresh MCP agreed, and
both current and archived v4 detached bundles verified. Fresh MCP registration initially
refused the stale generated report-schema artifact. Regeneration restored registration.
The initial detached exports refused a canonical decimal string in an unrelated table
setting. Inline formula replay now validates the retained source binding and parser
settings it uses.
[Replay and managed receipts](qualifier-scope.json) · [Finalized record](records/nce.qualifier-scope-development.json)

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 5 current, 0 superseded.


**NCE**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Exact native caption projection and artifact candidates](records/nce.caption-native-replay.json) | NCE-01 | passed | NCE-01 | 2026-11-07 |
| [Exact retained antecedent for constant-density naming](records/nce.constant-density-antecedent.json) | NCE-02 | passed | NCE-02 | 2026-11-07 |
| [Retained clause and definition replay](records/nce.predicate-native-replay.json) | NCE-02 | partial | NCE-02 | 2026-11-07 |
| [Additional frozen qualifier opportunities](records/nce.qualifier-coverage.json) | NCE-02 | partial | NCE-02 | 2026-11-07 |
| [Native qualifier scope and exact inline formula replay](records/nce.qualifier-scope-development.json) | NCE-02 | passed | NCE-02 | 2026-11-07 |
<!-- evidence-index:end -->

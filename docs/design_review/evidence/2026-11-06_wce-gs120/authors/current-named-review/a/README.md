# Independent A assessment of the current named construction

Assessed 2026-11-06. **Frozen independent assessment:** run 152, cut 204, task 605,
operation version 5, all 35 emitted definition/explanation components. This is an
assessment of the current registered output, with direct reading of the neutral source
packets and native `orig`/converted fields. No B/C current assessment or
implementation-replay verdict was read before freezing this output.

The method emits useful source locations and many correctly directed naming/formula
pairs. All 70 term/content spans reproduce their passage slices exactly. That does
not establish semantic completeness: many content spans are anaphoric mentions, and
many term spans omit their identifying arguments or qualifiers. Source scope and
speech act matter especially for exercise instructions and model-local names.

`assessment.json` contains all 35 unaltered observed components, the corresponding
raw task components, independently authored expected subjects/content/roles,
attachment direction, speech acts, local conditions, recognition comparisons,
narrower useful relations, and unresolved facets. `author_expectations.py` holds the
manually authored judgments separately from observed payloads. Its source quotes
are literal native-source excerpts; its semantic descriptions are interpretations.
The original inspection bytes and raw task structural product are preserved locally.
The full original 33 MB task file remains at its pinned immutable input path.

## Material findings

| Ordinal / component ID prefix | Source evidence | Assessment |
| --- | --- | --- |
| 13 / `10701a2dec` | source 122, `#/texts/13–15`: “the probability that X is less than Y is given by” | Output subject `Y` is wrong; the integral explains `P(X<Y)`. Preserve the exercise's explanation/proof request and independence premise. |
| 32 / `822bb6359a` | source 147, `#/texts/3`: “a set of constant density” | Output term `a set` loses the distinguishing name; the antecedent is a fixed-density level set. The later ellipse claim is an exercise request. |
| 23 / `33bf7dfe98` | source 136, `#/texts/122`: “We define the line L” | Output `the line` drops the defined identifier `L`; the construction remains local to the card-game graph. |
| 22 / `d571556863` | source 135, `#/texts/35`: “instead of defining the expected value as a weighted average, Huygens assumed…” | Embedded historical contrast is promoted to a direct definition; retain attribution and mention versus assertion. |
| 10 / `7150bdfe22` | source 116, `#/texts/84` | Converted final numerator exponent is `1`; native `orig` says `n-1`. The element also includes trailing prose. Correct subject is the CDF **of S_n**, not an arbitrary CDF. |
| 14 / `b16b87cce0` | source 124, `#/texts/42–44` | Converted expectation display adds fragments absent from its native original. The actual following absolute-convergence condition is omitted from the defining content. |
| 20 / `789223b603` | source 131, `#/texts/174–176` | Converted conditional-expectation formula adds a duplicate dotted-symbol expression absent from native `orig`. Native original contains one equation. |

These are source/output defects, not production fixes. They were reported to the
coordinator during assessment. No component count is treated as a measured benefit.

The finer distinctions in the per-component record also matter: `females`/`males`
name balls **within an urn model**; the maximum-likelihood example requests a
maximizer without computing one; a run is illustrated by a maximal block rather
than defined as any three heads; martingale is an informal fair-game naming here;
Little's law points backward to an equation whose proof is explicitly deferred;
`DieTest` is a program name, not evidence of program execution. The record preserves
these boundaries instead of resolving them into stronger claims.

## Custody and validation

The source inventory comprises 48 views across physical pages 191–310, with parent
SHA256 `763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`.
The assessment pins the two frozen outputs, source manifest, packet inventory,
native-parent map, all 12 excerpt packets and original parent PDF. Each component
has native product/task/digest identity, packet JSON pointers, original and converted
native quotations, physical pages and page pixel pins. Human reading covered the
contexts relevant to every emitted component; the inventory's 120-page extent is
not a claim of exhaustive human annotation of all source text.

**passed**, 2026-11-06:

```sh
uv run python docs/design_review/evidence/2026-11-06_wce-gs120/authors/current-named-review/a/validate_assessment.py
```

`receipt.json` records the actual Python version, UTC check time, exact artifact
hashes and command. `validation.log` retains its output. The validator checks the
fixed literal 35-ID list, original payload preservation, 70 exact role spans,
80 native item quotes/provenance pointers, all independent expectation fields,
48-view/120-page inventory and 18 input pins. It imports no production validator
and does not use the output as a semantic oracle. A validator pass means custody
and assessment-record completeness, **not** that the method's semantics passed.
`build_assessment.py` only packages the separately authored judgments with the
frozen observations.

**not_run:** PDF image inspection; production method/provider execution; database
writes; exhaustive definition/explanation recall annotation; `test-all`; `hygiene`;
root-owned `turn-end`. Native `orig` resolved the consequential conversion
conflicts assessed here. Remaining limitations, including linearized fraction
geometry, unstated existence conditions and neighboring corrupted formulae, are
retained per component. No external scientific or historical verification was
performed. These are exposed development sources, not held-out evidence.

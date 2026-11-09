# Private parser source and execution evidence

**Tested source custody · 2026-11-08.** The book panel binds authenticated
projection text from development run 404, cut 514, to the identical view
selections in finished run 407, cut 517, result revision 1. Each case carries
the exact completed-source reference, selected-view key, half-open Unicode
character range, text digest, sentence boundaries and intersecting source
pieces. The author opened only selected source and source metadata. Native
parser qualification and the comparison of matched predictions are separate.
[Book reference panel](raw/reference-book.json) ·
[Development baseline](../2026-11-08_pm2-foundation/README.md#frozen-development-baseline)

| Case | View and scope | Independent source distinction |
| --- | --- | --- |
| Foundation definition | 383, `[811,907)` | Keep the outcome restriction inside defining content and retain the term extent. |
| Foundation coherent | 383, `[811,1018)` | Distinguish the plural class of variables from a particular outcome. |
| Variance host | 393, `[104508,104649)` | Keep the positive-variance premise, defining host, and intervening formula seam separately inspectable. |
| Constant-density reference | 393, `[107620,107792)` | Preserve the antecedent's full density restriction separately from a native mention's shorter candidate. |
| Fair-coin modality | 389, `[18091,18193)` | Separate the fairness condition, subordinate state, and modal assignment. |
| Gambler participants | 405, `[27850,28039)` | Distinguish the person and her pronoun from capital and the two terminal values. |
| Gambler temporal context | 405, `[27850,28039)` | The temporal limit qualifies playing. The next sentence reframes the terminal values. |
| Roulette separator | 387, `[47179,47345)` | The projected gap within the losing-outcome phrase needs explicit coverage. |

The first four cases are exposed preservation controls. The remaining cases
were selected and authored from source before opening parser predictions.
The book is an exposed development corpus. The panel is a bounded single-author
reference with independent expected distinctions. Protected grading and
paired comparison remain with the milestone evaluation owner. The historical
run 407 and set 32 evaluation mismatch remains a distinct refusal control.
[Historical preservation examples](../../../examples/README.md) ·
[Assessment contract](../../../plans/production-milestone-two/textbook-assessment-and-adoption.md#freeze-the-reference-and-comparator)

The alternate vocabulary fixtures cover modal coordination and nested passive
frames, distinct and ambiguous referents, and causal layout and singleton
discourse. They include exact text and source-relative ranges. The native
transfer test bound one scope per provider through a second released vocabulary.
The private Reader retained all three successful product families alongside a
deliberate profile mismatch. The fixture measures transfer of the same path
and failure isolation in those scopes.
[Alternate vocabulary fixtures](raw/reference-operations.json) ·
[Native transfer receipt](records/pm2.alternate-vocabulary.json)

The source-only checks used `BoundReader.source_view` against cut 514. They
authenticated each selected source reference from cut 517 through
`ops.validate_structural_source` in the same read snapshot. The source scan
and exact read used `uv run python -` and a reader-purpose database connection.
Source authoring was complete before native predictions were opened.

## Private native execution

The successor release `release:94b070c1899a8a26a5d99fe16d56a3dbbb6c9c32da45b6b779972d435a73d716`
declares the three private parser methods. The request binds that release's
private input realization to five authenticated source views from finished
run 407. The request's byte ceiling bounds reading those existing projections.
Each provider has its own inference limits and exact startup identity.
[Installed book request](raw/book-parser-request.json)

```sh
uv run ci run parsers --request docs/design_review/evidence/2026-11-08_pm2-parsers/raw/book-parser-request.json --json
uv run ci contributions list --run "$parser_run_id" --selected-task-id "$parser_task_id" --include-details --json
```

For view 393, the installed sentence segmenter places the independently authored
variance range `[104508,104649)` inside larger canonical sentences. The HanLP
scope expands to `[104505,104970)`. Treat it as a diagnostic of the current
source preparation. The older variance attachment is a separate preservation
control. The run also submits ten canonical sentences in view 383 to exercise
the ordinary HanLP eight-sentence limit and subdivision.

**Tested native execution · 2026-11-08.** Run 416 sealed cut 520 with 18
explicit scopes and two coherent child scopes. The children examine five sentences
each. The retained ten-sentence parent reports the limit, and cross-boundary
relationships remain unexamined. Exact reads of view 383 select task 2076 or
2079 and return distinct operation identities. Run 417 at cut 521 reuses both
origin tasks for the same input. The source-only cut and a changed projection
digest both refused completed-source authentication. The development project
has no active release or selected result.
[Native execution and Reader receipt](records/pm2.private-parser-stage.json) ·
[Reader and fallback summary](raw/book-reader-summary.json)

## Provider observations

- **HanLP.** On the fair-coin source, the new route retains separate fairness
  and assignment predicates. Both the condition and modal cue nominate the
  assignment host. The expanded variance diagnostic retains the defining
  predicate and yields no cue for the inherited variance premise. The existing
  attachment remains a separate capability. The two-scope Large/Base CPU
  comparison holds the heads and exact tokens fixed. The strong definition
  witness continues to use the released spaCy evidence.
  [Prior variance attachment](../../../examples/README.md#a-condition-stays-attached-to-its-predicate) ·
  [Large/Base receipt](records/pm2.hanlp-large-base.json)
- **Maverick.** The ordinary and supplied gambler arms cluster “A gambler,”
  “She,” and the possessive “her.” The ordinary inventory misses “her capital.”
  The supplied arm retains it as a distinct unclustered candidate. The constant-density
  arm locates the demonstrative and a candidate for its full antecedent, with a
  trailing punctuation difference and an additional overlapping mention that
  spans both descriptions. Treat that co-membership as a proposal. The existing
  local-reference control retains the independently reviewed antecedent extent.
  [Prior exact antecedent replay](../../../examples/README.md#a-local-phrase-recovers-its-antecedent)
- **Dipo.** The review distinguishes exact EDU coverage, ordered child splits,
  and the associated relation and nuclearity. The learned and supplied arms
  agree on the gambler temporal scope. The roulette scope retains the separator
  and its two physical pieces even as its reviewed and predicted EDU boundaries
  differ. [Dipo assessment](dipo-assessment.md) · [Paired execution receipt](records/pm2.dipo-panel.json) · [Encoder window receipt](records/pm2.dipo-encoder-window.json)

## Development deployment and qualification

**Tested development deployment · 2026-11-08.** The parser release passed
`uv run ci release check --project nce-grinstead-snell-full-book --target development --release release:94b070c1899a8a26a5d99fe16d56a3dbbb6c9c32da45b6b779972d435a73d716 --json`
on `semantic_pm2_parser_methods`. After the migration, `uv run ci source views 404 --json`
and `uv run ci source views 407 --json` returned identical inventories of 29 views.
The retained HanLP task in cut 520 remained readable. A fresh execution of the two
HanLP scopes from the exact replay request sealed run 418 at cut 522. Both tasks,
2098 and 2099, produced their own results, confirmed with
`uv run ci contributions list --run 418 --method extract.pm2_hanlp --limit 1000 --json`.
[Development deployment receipt](records/pm2.parser-development-deployment.json)

`uv run ci check --json` passed on the parser changes and the deployment repair.
The original `uv run ci test --json` campaign `f3375d394226433b9e60baf5254a8e36`
failed with 16 ordinary failures and one blocked opt-in native case. The exact
ordinary retry `55c3a312111c441baa2afb81cea15b77` passed 13 of those 17 identities.
The opt-in case passed independently in `212d318f4d754d4bbfbb2456c8e05ff7`.
The restart left two files empty in the original fault receipt, so
`uv run ci test coverage` could not reconcile the original campaign. The
bounded `scripts/test_receipts.py classify --projection unresolved` check on
the intact ordinary receipts observed 5,481 of 5,484 required identities
covered across different source contexts. A fresh `uv run ci test --lane fault --json`
passed all eight fault cases in `664af5eed5b4438c9b712d24a8647c36`.
Two retained annotation fixtures still lack the required `availability` field,
and the generated typed surface carries a stale physical fingerprint. Those
files and the physical model inputs are unchanged by this parser work. The
focused native checks establish the private parser scope. Repository-wide
qualification remains open. `uv run ci evidence check --json` reported a
pre-existing Chandra digest mismatch in `chandra.repaired-shadow-controls`.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 6 current, 0 superseded.


**pm2-parsers**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Matched native HanLP Large and Base comparison](records/pm2.hanlp-large-base.json) | PM2-03 | passed | PM2-03, PM2-06 | 2026-11-08 |
| [Private parser transfer and profile-refusal isolation](records/pm2.alternate-vocabulary.json) | PM2-03–05 | passed | PM2-03, PM2-04, PM2-05 | 2026-11-08 |
| [Parser methods on the development revision](records/pm2.parser-development-deployment.json) | PM2-03–05 | passed | PM2-03, PM2-04, PM2-05 | 2026-11-08 |
| [Private native parser execution and exact readback](records/pm2.private-parser-stage.json) | PM2-03–05 | passed | PM2-03, PM2-04, PM2-05 | 2026-11-08 |
| [Pinned Dipo encoder window and effective position controls](records/pm2.dipo-encoder-window.json) | PM2-05 | passed | PM2-05, PM2-06 | 2026-11-08 |
| [Dipo paired discourse cases and private completed-cut readback](records/pm2.dipo-panel.json) | PM2-05 | passed | PM2-05, PM2-06, PM2-08, PM2-11 | 2026-11-08 |
<!-- evidence-index:end -->

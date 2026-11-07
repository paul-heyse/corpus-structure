# Independent GS120 source reference for WCE-R03 and R15–R19

Source-only authoring at `3187254d3`, 2026-11-06. The input population is the existing shared
development corpus, Grinstead–Snell physical pages 191–310. This frame uses the 12 neutral
recovered source packets, with 48 source views. Authoring used native retained text, projected
text, source coordinates, and layout fields. Producer outputs, retrieval nominations, model
scores, and protected judgments did not enter the authoring.

[Source reference](source-reference.json) freezes packet, parent, and excerpt digests, each
selected passage's original source identity, and exact native and projected spans. Offsets are
zero-based and half-open. Native-only text remains available for judgment with an explicit
projection limit. The reference is a bounded independent source opinion. Any protected admission
still needs its own exact frame, independent A/B passes, and C adjudication.

## Composition opportunities

- Table 6.1, physical page 234, contains two merged sample-size bands. The Winning=1 row gives
  counts and relative frequencies under both. The four selected value cells each carry exact row,
  measure, and band expectations. The negative cases deliberately substitute the other band's
  repeated measure and sample-size headings. Native row-header flags alone omit the Winning=1
  row role. The accepted relation uses the table's original layout and independent textual cues.
- The normal-variate transform at physical page 221 uses the already-defined standard-normal Z
  outside its defining span. The expectation and variance derivation on physical page 282 binds
  the nonstandard X to local µ and σ, and distinguishes σ from σ². The X/Z identity negative
  preserves the difference between two related variables. The gamma cases retain local λ/n and
  λ/β bindings with exact shape values and the chi-squared n/2 relationship. They leave
  cross-passage symbol equivalence unestablished.
- The body reference and matching note 9 on physical page 221 establish a bibliographic
  relationship. They supply no table, row, or band applicability. None of the 17 distinct native
  tables in the retained 48 views has a native footnote link. The exact Table 6.1 caption,
  method prose, and table region have no observed scoped table note. This census concerns the
  retained table links. A broader inspection of every source note's semantics was not performed.
  No authentic positive row-note relationship is claimed here.

Assess the fixed-endpoint arms on these same opportunities before measuring discovery. The
source judgments define the expected roles. Algorithm-specific scores or winners may differ,
including when the same case has an unambiguous source answer. Table 6.1 supplies real competing
surface labels with exact disjoint layout evidence. Its wrong-band alternatives remain
source-excluded where that evidence is available.

[Marginal-role reference](marginal-role-reference.json) is the separate WCE-R18 fallback if
Table 6.1's authenticated exclusions settle the header question. Physical page 202's Table 5.2
has unnamed last-row and last-column counts. Its adjacent Table 5.3 gives a corresponding
schematic, and the intervening prose assigns the roles of its symbols. Nine exact source cases
separate observed counts, row marginals, column marginals, and the grand total. Their meaning
depends on one shared layout and prose relationship. An integer or empty header by itself cannot
establish the corresponding role.

## Artifact lineage opportunities

The three declared reference-by-caption strata contain all 67 cross-product pairs within the
selected chapters and artifact kinds. Thirteen exact pairs have source support, and 54 pairs
combine different artifacts. Positive judgments bind the quoted reference and caption and their
source context. Cross-pair judgments follow the contrary artifacts in the inspected strata.
The pair universe precedes prediction and includes pairs that a blocking route may miss.

All selected figure endpoints have projected spans. The native captions for Tables 5.8, 5.9,
and 6.1 are authentic and native-only. Retain their source-supported pairs in the denominator
when a production route omits these captions. Compare by original source and anchored occurrence,
and keep unrepresentable, unexamined, and absent nominations separate. Neither revision identity
nor alternate artifact aliases are established by the selected passages. Alias state is unknown.
Graphical contents and material beyond the selected strata remain unassessed.

## Reproduce the freeze

From the repository root:

```sh
uv run python docs/design_review/evidence/2026-11-06_wce-completion-repair/source-references/freeze_reference.py |
  cmp - docs/design_review/evidence/2026-11-06_wce-completion-repair/source-references/source-reference.json
uv run python docs/design_review/evidence/2026-11-06_wce-completion-repair/source-references/freeze_reference.py --marginal-roles |
  cmp - docs/design_review/evidence/2026-11-06_wce-completion-repair/source-references/marginal-role-reference.json
```

Both commands passed on 2026-11-06. They reconstruct the frozen anchors, packet digests, and
candidate-independent source populations. Product and provider execution is outside this frame.

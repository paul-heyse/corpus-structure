# `fixtures/trace`: the worked trace as segments, targets and vendored pages

The phase 0 acceptance fixtures for the four trace units of [`docs/design/trace.md`](../../docs/design/trace.md)
(foundations §3.7, package P0-F-3; coordinator decision 6; D9 §1, §4). They are written from
trace.md's tables and D8 §5.3, independently of `fixtures/s0`, so the acceptance test checks
proposals against targets they did not produce. Consumers: I1a (segments), F4's row test
(segments), C1 and C3 (targets), ingest's trace tests (vendored pages), F-Q6 (authored inputs).

| Path | What |
|---|---|
| `<unit>.segments.json` | The expected segments of the five trace annotation units: `T1-leadin`, `T1-dfn1`, `T2`, `T3`, `T4` |
| `T1.target.json` … `T4.target.json` | Each trace unit's target batch with its citation frame, `must_not`, `questions`, phase marks and sources |
| `corpus/siegrist_random/random/special/{LocationScale,Normal,LogNormal,Gamma}.html` | The original bytes of the four spike pages (98 KB), at their corpus paths |
| `index/siegrist_sections.tsv` | Those pages' rows of the Siegrist corpus index, header included |
| `corpus/NOTICE` | Siegrist's CC BY 2.0 attribution |
| `build_segments.py`, `build_targets.py` | Provenance: the scripts that wrote the JSON once (`uv run python fixtures/trace/<script>`) |

The committed JSON is the authority; the scripts are kept only as provenance. Neither imports
spike code: they read the frozen S1 renditions in the design-spikes evidence as data and use the
product locator generator (`corpus_structure.core.locators`).

The reader and the support models are `python/corpus-structure/tests/fixtures/support.py`.

`archived-renditions.json` retains the four historical rendition inputs from the HTML writer
at `7e6289a`, captured on 2026-10-31 in an isolated exported source tree. Each input records its
original SHA-256. Archived-reference and scientific tests read these inputs after retirement of
the application HTML writer. Existing target assertions remain independently authored and unchanged;
these snapshots establish no PDF parsing or fidelity result.

## Segments (`<unit>.segments.json`, model `TraceSegments`)

| Field | Content |
|---|---|
| `trace_unit`, `page`, `source_uri`, `unit_key` | The trace unit, the page, the corpus source URI and the unit segment's generated locator |
| `ancestors` | The segments above the unit, document first |
| `segments` | Every segment of the unit's subtree, parents before children (`Segment.walk` order): `kind`, generated `locator`, `start`, `end`, author `attrs`, `parse_status` (`parse_reason` when not `ok`) |
| `counts` | Segments per kind |
| `markup` | The S1 inline markup inside the unit (`dfn`, `em`, …), which trace.md names as the `dfn` term |
| `trace_md` | What trace.md states about the unit (kind, id, counts of math spans and sentences, classes, `dfn` terms); `build_segments.py` asserts each against the S1 rendition |

Kinds, counts and attributes are trace.md's; offsets, texts, attributes and parse statuses are the
S1 rendition's (the diagnostic attributes `tag`, `sid`, `sourceline` and `roles` dropped; the
provisional sentences added), so I1a's comparison is also a rendition-identity check against S1.
trace.md's statements all held, with these readings:

- T1's lead-in sits in section *General Theory* (h3) and `#dfn1` in its subsection *Definition*
  (h4), not in one "page body" section as trace.md's Segments line has it.
- trace.md's "`dfn` term 'location-scale family'" is inline markup in S1, not a paragraph
  attribute; `#dfn1`'s paragraph carries three `dfn` terms (location-scale family, location
  parameter, scale parameter).

## Targets (`T<n>.target.json`, model `TraceTarget`)

| Field | Content |
|---|---|
| `trace_unit`, `page`, `units` | The trace unit, its page, and the unit keys of its annotation units (T1 has two) |
| `batch` | The target entities, statements and claims as an `AuthoredBatch`. Local refs are trace.md's refs (`S1`, `C4`, `LSF.loc`, …). `unit_ref` is the unit key; T1's is the `#dfn1` key, not consulted because T1 anchors its statements by sentence ids (`unit_ref_note`) |
| `frame` | The `CitationFrame`: the trace unit's sentences numbered `s1…` in document order across its annotation units, as the S0-R2 packets number them (T1: `s1`–`s3` the lead-in, `s4`–`s6` `#dfn1`) |
| `deferred` | T3 only: D1, the phase-2 derived claim, in trace.md's terms (`establishment`, `derived_from`, `rule`), held outside the batch because the current claim models lack those fields; **P0-F-2e** adds them, then D1 moves into the batch |
| `must_not` | Each "Must not appear" line of trace.md as one or more partial patterns (`MustNot`) |
| `questions` | Each D8 §5.3 query of the unit (`Question`) |
| `phases` | Phase marks: everything phase 0 except T3's D1 (phase 2, D5 §9) |
| `sources` | Where each claim's formula text and bindings come from: trace.md, or the v1 batch (`results/s0r2/reference_model_v1/<T>.json <local_ref>`) where trace.md abbreviates |

Evidence quotes are the targets' own, copied from the cited sentences; `build_targets.py` and the
tests check each occurs in its frame text.

### Support models (`support.py`)

- **`TargetRef`** `{"ref": r}`: the item the target's local ref `r` keys to. Patterns and question
  rows name target items this way, so every comparison is by key equality, never key value
  (D1 §10.1, D9 §4).
- **`EntityPattern`** `{"kind": "entity", "type"?, "label"?, "identity"?}`: an entity that must not
  appear; identity slot values are literals or `TargetRef`s.
- **`ClaimPattern`** `{"kind": "claim", …}`, every field optional (absent matches anything):
  `subject` and `object` (a `TargetRef`, an `EntityPattern` matching by type, or a `ValuePattern`);
  `predicate`; `modality` (absent in a claim means `asserted`); `param_values` (entries of the
  `param_values` qualifier that must all match); `param_value` (any one entry); `condition` (a node
  occurring anywhere in the condition tree); `lacks_condition` (a node that must be absent; with the
  other fields, "C3 without the `claim C1` condition").
- **`ValuePattern`** `{"t"?, "latex"?, "v"?}`, at least one field; LaTeX compares by token form
  (D1 §6.2).
- **`ConditionPattern`** `{"op", "ref"?, "x"?, "set"?}`: `ref` is a `claim` node's target ref.
- **`MustNot`** `{"line", "pattern"}`: `line` is trace.md's text; a line that two shapes can
  violate (T1's `b ∈ ℝ`, T2's "location" as a value, T4's lognormal mean) has one entry per shape.
- **`Question`** `{"question", "query", "params", "returns", "returns_with_suppositions",
  "returns_from_phase_2"?, "note"?}`: the D8 §5.3 query name and its parameters (a locator for
  `statement`, a label for the profile queries), and the target refs its rows must include
  without and with `include_suppositions`. A supposed premise that a returned claim's conditions
  reference is returned either way (D8 §5).
- **`Deferred`**, **`Phases`**: as above.

The matcher that applies the patterns and compares query rows is C3's (P0-C-3, the acceptance
test), not this package's.

## Vendored pages

The pages sit at their corpus paths under a corpus root, `corpus/`, as in
`docs/statistics_corpus/corpus/`, so their source URIs, content hashes, document keys and locators
are the corpus's, and the tests that use them run without the gitignored corpus and never skip.
The index is at `index/siegrist_sections.tsv`, beside `corpus/` rather than inside it, so the
Siegrist profile's `index.file: "../index/siegrist_sections.tsv"` (relative to the corpus root,
D2 §12.1) resolves unchanged; its four rows and header are copied verbatim from
`docs/statistics_corpus/index/siegrist_sections.tsv`. The bytes match
`docs/statistics_corpus/MANIFEST.sha256` (2026-10-28), and a `corpus`-marked test repeats that
check whenever the corpus is present.

## Checked now

`uv run pytest python/corpus-structure/tests/fixtures`: every segments and target file validates
against the support models and the core `AuthoredBatch` and `CitationFrame`; every locator parses,
prints back unchanged and names the file's page; counts equal the segments and trace.md's counts;
every quote occurs in its frame text; every ref a question, pattern or phase mark names is a
target ref; the vendored pages, index rows and NOTICE are present, with sizes equal to the
index's `bytes`; with the corpus present, the bytes match the manifest.

## Pending acceptance (gated)

Repository policy fails rather than skips, so these are not written yet. They are F3's acceptance
(foundations §3.7; tests row P0-F-3) and are written when their prerequisites land:

| Check | Gated on |
|---|---|
| Every `fixtures/s0` and target frame resolves on the production rendition (`core.frame.resolve_frame`), and a frame entry whose text differs from the production sentence (a rendering convention, a `[n]` marker) is refused, not matched approximately | P0-I-1a |
| Production segments of the five trace units equal `<unit>.segments.json` (kinds, locators, offsets, attributes, parse statuses) | P0-I-1a (its own acceptance) |
| A0's stored form of each `fixtures/s0` batch gives `reference_v1`'s evidence offsets (the rendition-identity check against the spike) | P0-A-0 on P0-I-1a renditions |
| U12's `c1` is in I2a's standing context for `special/Gamma.html#mom1` | P0-I-2a |
| The unsplit T1 cannot be re-addressed to the `#dfn1` packet's served frame (`core.frame.readdress`) | P0-I-2a (served packet numbering); the packet itself is A1's |
| Both `Z` declarations of T1 key alike | P0-A-0, keys (scheme 1 after P0-F-2e) |
| Targets and the trace units' `fixtures/s0` batches, derived on the production rendition and keyed, have equal key sets over the phase 0 targets; no fixture claim matches a `must_not` pattern; every difference is explained and resolved | P0-A-0, P0-I-1a, key scheme 1 (P0-F-2e) |
| The `fixtures/s0` batches validate against the compiled schema | P0-S-1 (its own acceptance) |

### Source-grounded agreement decisions (2026-10-29)

F3-02 is reconciled for the deterministic trace journey:

- The lead-in's `Z` is scoped to General Theory; the definition's redeclaration is scoped to its
  Definition subsection. They are distinct local entities (F3-01), and the trace describes both.
- T3's source introduces the expression `a + b X` without assigning it a named symbol. The s0
  fixture removes the invented symbol, retaining the expression as its label; provenance names
  this correction. The original v1 evidence is unchanged.
- T3's `N.mean`/`N.var` and T4's `N.mean`/`N.sd` are not declared by their source claims. They are
  removed from positive targets; the forbidden T4 identity is expressed as an entity pattern.
- Parameter labels are surfaces; family plus canonical name governs identity. Different labels
  therefore preserve the same entity keys.
- T1 C7/C8 have independent valid evidence choices in the source. Acceptance checks their cited
  source text and locations rather than requiring identical choice of evidence between authors.
- T1's lead-in unsupported items are separate coverage information, outside the trace's positive
  claim list. They remain subject to the generic unsupported-query acceptance.

## Current counterpart scope and deliberate changes

The TA-09 counterpart journey transfers the independently authored T1–T4 target distinctions,
questions and supported `must_not` obligations through current source-view publication and
served queries. Historical locators/renditions remain coordinate witnesses; their successful
reading does not establish current PDF recognition. T3's deferred D1 derivation remains a future
witness until that specific rule is admitted, with disposition in the test-architecture plan.

An intentional segmentation or parameter-meaning change needs an independently adjudicated
source/target difference and an explicit affected-consumer list. Keep these original targets
and provenance; select a versioned counterpart rather than regenerating an oracle from current
production results. A type/locator check alone cannot close a negative/query obligation.

Current controlled paragraphs are newly authored semantic counterparts, with independently
stated positive/negative answers. They do not claim recognition or byte replay of the original
HTML. Original target/quote and coordinate witnesses remain retained for their declared scope.

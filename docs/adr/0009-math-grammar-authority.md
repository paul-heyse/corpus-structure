---
id: ADR-0009
title: Read math through one extended Lark grammar; source facts as profile data; offset-preserving quote location
status: accepted
date: 2026-10-28
supersedes: []
superseded-by: null
design: []
evidence: Tested
---

## Context

The design spikes S0 and S1 (`docs/plans/design-spikes-s0-s1_2026-10-28.md`) parsed the same
material in several places by different string code:

- **Math was read four ways:** the M01 delimiter scanner; pylatexenc nodes for M09/M13-style
  symbol extraction; and, for value comparison, a token-rewrite layer that bent LaTeX into what
  SymPy 1.14's Lark grammar accepts.
- **Defects from the rewrite layer:** dropped subscripts on `\sigma`, `\Phi(x)` read as
  multiplication, and a crash on relations. These were instrument-review findings F2, F3 and
  F5a, recorded in the spike evidence `results/s0/instruments_tests.md`.
- **Fixed-width fuzzy windows:** quote location (D4 §4.3) used rapidfuzz windows of the quote's
  length. A quote whose length differed from the source span got a span cut mid-word.
- **Source facts in code:** Siegrist-specific facts lived in adapter code (S1-F: unit selector,
  reference links, sections, math delimiters), so they would not transfer to a second source.

The affected owners are D1 §6.2 (canonical form) and D4 §4.3 (quote location), with M01, M09,
M11 and M13 in D4. The affected consumers are the batch validator, value equivalence (D7 §5),
claim keys (D1 §10.1, through canonical form), and M13 scopes.

## Options

1. **Keep string handling and patch each defect** (the simplest viable option). Every new
   LaTeX construct or source needs another rewrite and another regex, so defects recur by
   construction. It loses.
2. **Write our own math grammar from scratch.** This gives full control, but re-implements what
   SymPy's grammar and transformer already do. It also cuts us off from SymPy's conversion,
   which value equivalence needs.
3. **Extend SymPy's Lark grammar by directives** (`%extend`/`%override` in a separate file),
   with our own transformer subclass. Most constructs are reused; our additions are visible
   and reviewable as a file diff. SymPy marks the parser experimental, so it is coupled to
   SymPy's grammar. A pinned SymPy contains that coupling.
4. **Finite-state normalization with pynini** for math and labels. It is strong for rewrite
   cascades and for generating variants, but it does not track offsets and cannot represent
   nested math structure. It also adds a C++ dependency with no current consumer.

For quote location, the choice was among rapidfuzz alone, regex fuzzy matching alone, and a
cascade combining the two. Regex `BESTMATCH` over a whole sentence times out on long quotes;
rapidfuzz alone cannot align quotes that drop or add words.

## Decision

- **Math.** One grammar is the single authority for reading math: SymPy's shipped Lark LaTeX
  grammar, unedited, plus a separate extension file. The extension has:
  - typed start symbols (formula, relation, member, set);
  - subscripts and superscripts as rules, not regex terminals;
  - explicit ambiguity, resolved only from declared context (macro roles, slot type), and
    otherwise reported as ambiguous;
  - positions for symbol occurrences;
  - structured failure reasons.

  Validation, canonical form (D1 §6.2), SymPy conversion (M11), symbol mentions (M09) and M13
  all read through it. The grammar holds no source-specific names: operator and set macros come
  from the rendition's macro table, which is data. SymPy stays pinned as a hold.
- **Source profile.** Source-specific HTML facts are source-profile data, not adapter code:
  - math delimiters and display environments;
  - the macro source;
  - selectors for units, references, sections and layout.

  The M01 delimiter scanner is generated from the profile's delimiters.
- **Quote location** (D4 §4.3) is a cascade that keeps source offsets:
  1. exact in the cited sentence, then in the unit;
  2. exact up to spacing, done as a regex over the original text;
  3. exact after expanding the rendition's macros on both sides;
  4. a rapidfuzz alignment refined by regex `BESTMATCH` inside its window, under a timeout.

  Every span is snapped outward to word boundaries. Each result records its step and edit
  counts.
- **Prose constructs** (M13 binders, statement cues) are spaCy `Matcher` patterns over tokens,
  with the binder lexicon as pack data and math tokens carrying their parsed kind.
  `DependencyMatcher` is used only where clause attachment matters.
- **Not adopted:** fuzzy matching for entity or family identity; recursive regex for nested
  math; pynini for now.

## Consequences

- **Easier:**
  - a new LaTeX construct is a grammar rule, and a new source is a profile;
  - value comparison, keys and scopes see the same structure;
  - quote errors leave inspectable evidence.
- **Harder:**
  - SymPy upgrades need review of the extension against the shipped grammar;
  - Earley parsing is slower than string handling, so parsers are cached per macro table.
- **Measured, spike evidence 2026-10-28** (`docs/design_review/evidence/2026-10-28_design-spikes/`):
  - **Lark probe:** S0 batch values recognized 51 of 52, against 37 for the shipped grammar;
    spike-page math spans 729 of 918, against 466.
  - **Regex probe, 499 quotes with seeded errors:** no mid-word cuts, against 64 before;
    respelled macros 16 of 16 exact, against 0; dropped-word quotes 43 of 99 exact, against 0.
  - **Regex delimiter pattern:** equal to the scanner on 517 blocks.
- **Implementation state:** the grammar module, the validator check, the cascade and the M13
  patterns are spike packages I-R1 and S0-R1 in the plan series. The production realizations
  belong to D4's methods when they are built. Acceptance does not establish them.
- **Revisit:**
  - a SymPy release that changes its Lark grammar or transformer;
  - a source whose math is not LaTeX (consider pynini normalization into LaTeX then);
  - S5 measuring grammar coverage below the ANTLR backend's (`OPEN-D4-3`).

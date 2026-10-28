# S1 · Ingest and segmentation

**Brief, 2026-10-28.** Run first. CPU only.

## Question

Does the evidence model of [D1 §3](../../../design/D1-knowledge-representation.md#3-evidence)
fit Siegrist's HTML: one canonical text per rendition, a contiguous segment tree, spans as
offsets, author markup kept as attributes, math kept as LaTeX? And does sentence segmentation
survive inline LaTeX (`OPEN-D1-1`)?

## Why it matters

Every later stage cites spans into the canonical text, and goldens are anchored to it. If units,
proofs or math cannot be represented as contiguous segments, or offsets drift, everything
downstream is unreliable and D1 §3 must change before D3 fixes the tables.

## Inputs

- The four spike pages, then all 78 first-pass pages (`first_pass = yes` in
  `docs/statistics_corpus/index/siegrist_sections.tsv`).
- The author-markup counts in that index (`units`, `definition_units`, `dfn_terms`,
  `details_blocks`, `display_math`): these are the oracle for structure.
- D1 §3.1 canonical-text rules and §3.2 segment kinds.

## Procedure

1. **Throwaway adapter.** In `code/s1_adapter.py`, using lxml (and pylatexenc only to detect and
   delimit math, never to rewrite it), produce for each page:
   - the canonical text, following D1 §3.1 (block separators, LaTeX kept verbatim between its
     delimiters, entities decoded, whitespace collapsed, NFC);
   - the segment tree with kinds from D1 §3.2 (`document`, `section`, `unit`, `paragraph`,
     `list`, `list_item`, `details`, `math_display`, `math_inline`, `heading`), each with
     `start`, `end`, `parent`, `attrs` (element id, classes, `<dfn>` terms with their offsets,
     link targets);
   - the excluded content, with the rule that excluded it (navigation, scripts, app widgets,
     footer, MathJax configuration).
   Record every choice you had to make that D1 §3 does not settle.
2. **Invariants.** Check for every segment: `start <= end`; children inside parents; siblings
   ordered and non-overlapping; `canonical_text[start:end]` reproduces the element's text under
   the normalization rules. Report violations by kind.
3. **Structure counts.** Per page, compare your counts of units, definition units, `<dfn>`
   terms, `<details>` blocks and display math with the index. Explain every mismatch (adapter
   error, index rule difference, or genuine ambiguity).
4. **Contiguity.** Find any authored unit whose content is not contiguous in reading order (for
   example a unit interrupted by an app or figure, or `<details>` placed elsewhere). D1 assumes
   contiguity.
5. **Sentence segmentation (`OPEN-D1-1`).** On the four spike pages, split paragraphs into
   sentences with spaCy `en_core_web_sm` four ways:
   - (a) raw canonical text;
   - (b) inline math replaced by a placeholder token (e.g. `⟨m12⟩`), with offsets mapped back;
   - (c) (b) plus a rule that never splits inside display math;
   - (b′) no masking: a spaCy component before the parser merges each inline math span into one
     token (`doc.retokenize()`, `POS=PROPN`) and sets `is_sent_start = False` inside display
     math (D4 M03's candidate).
   Judge 60 paragraphs sampled across the pages: count bad splits (inside math, after
   abbreviations such as "i.e.", before "Then") and missed splits for each variant.
6. **Core units.** Locate the twelve core units of the [README](README.md#the-spike-sample) and
   write `sample.json`: for each, the page, segment keys (computed as D1 §10.1 with the adapter
   config hash), `start`, `end`, and the text's first 80 characters.
7. **Timing and size.** Wall time for all 78 pages; canonical text size per page; share of
   characters inside math.

## Data to collect

| File | Content |
|---|---|
| `results/s1/canonical/<page>.txt` | Canonical text of the four spike pages |
| `results/s1/segments/<page>.jsonl` | One segment per line: key, kind, start, end, parent key, attrs |
| `results/s1/counts.tsv` | Page × (units, definition units, dfn terms, details, display math): ours, index, delta |
| `results/s1/invariants.json` | Violations by invariant and kind, with examples |
| `results/s1/sentences.tsv` | Paragraph id × variant × (sentences, bad splits, missed splits) |
| `results/s1/exclusions.tsv` | What was excluded per page, by rule |
| `sample.json` | Core-unit locators |

## How to interpret

| Finding | Reading |
|---|---|
| Counts match the index on at least 95% of pages, invariants hold | D1 §3 confirmed; the adapter rules become the M01 specification |
| Systematic count mismatch for one markup type | Either the index rule or our rule is wrong; report which and propose the M01 rule |
| Non-contiguous units exist | D1 §3.2 needs multi-range segments or a `continues` relation; quantify how often |
| Variant (a) has more than a handful of bad splits per page, (b) clearly fewer | Adopt math masking for sentence splitting (M03); `OPEN-D1-1` closed |
| Bad splits remain in (b) and (c) | Propose a rule-based splitter or unit-level processing without sentences |
| Math is a large share of characters | Supports math masking for GLiNER2 too (input to S2) |

## Report

`S1-report.md` from the [template](report-template.md). Its "Design implications" section must
state, for M01 and M03, the rules you would specify, and answer `OPEN-D1-1`.

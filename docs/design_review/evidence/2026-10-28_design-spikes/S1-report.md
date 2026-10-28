# S1 · Ingest and segmentation — report

**Run:** 2026-10-28, by Claude Opus 5.5 (root) with fresh subagents for the sentence gold and the
trafilatura/NIST probes. **Brief:** [S1](S1-ingest-and-segmentation.md); **plan:**
[S1 plan](../../../plans/design-spikes-s0-s1/S1-ingest-segmentation.md). **Status:** passed.

## Answer

Yes: D1 §3 fits Siegrist HTML. On all 78 first-pass pages the adapter produces one deterministic
canonical text per rendition with no structural invariant violations, every one of 19,432
element texts reproduced by an independent XPath path, 28,948 of 28,956 math spans parsing
strictly (the 8 `partial` are the source's unbalanced delimiters), and structure counts equal to
the index on 77 of 78 pages (the exception is the index counting a commented-out unit). Units
are contiguous; nothing requires multi-range segments. Sentence segmentation survives inline
LaTeX only when math is not presented to spaCy as text: merging each inline formula into one
token before the parser (D4 M03's b′) gives F1 1.0 on a 49-boundary gold that two independent
markers produced identically, against 0.80 for raw text (20 splits inside math) — `OPEN-D1-1`
closed in favour of b′. The HTML forced seven rules D1/D4 do not state (HTML-01…07), all
specified below.

## What was run

All commands from the evidence folder with `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python …`.

| Step | Command | Outcome | Records |
|---|---|---|---|
| E0 environment | `code/e0_environment.py` | passed | `results/environment.json` |
| S1-A adapter, 4 pages | `code/s1_adapter.py special/{LocationScale,Normal,LogNormal,Gamma}.html` | passed | `results/s1/canonical/`, `segments/`, `markup/`, `renditions.json` |
| S1-A variants | `code/s1a_variants.py` | passed | `results/s1/variants_s1a.json`, `variants_s1a.md`, `blocks/` |
| S1-B sample, invariants, determinism, sentences | `code/s1b_sample.py` | passed | `sample.json`, `results/s1/invariants.json`, `locators.json`, `sentences/*.provisional.jsonl` |
| S1-C gold sample | `code/s1c_gold_sample.py` | passed | `results/s1/gold/sample.json`, `worksheet.md` |
| S1-C gold marking | two fresh subagents (Opus 5.5), worksheet only | passed | `gold/marker_a.json`, `marker_b.json`, notes |
| S1-C agreement, scoring | `code/s1c_score.py agreement`, `… score` | passed | `gold/gold_agreement.json`, `gold.json`, `results/s1/sentences.tsv`, `sentences_errors.json`, `sentences_proxies.json` |
| S1-D 78 pages | `code/s1d_corpus.py` | passed | `results/s1/{counts,parser_diff,coverage,links,sizes,repairs,macros}.tsv`, `corpus_summary.json` |
| S1-E trafilatura | `code/s1e_trafilatura.py` (executor subagent) | passed | `results/s1/baseline_trafilatura.*` |
| S1-F NIST | `code/s1f_nist.py` (executor subagent) | passed (8 pages) | `results/s1/nist_probe.md`, `results/s1/nist/` |

Environment (2026-10-28): Python 3.14.10; lxml 6.1.3 with libxml2 2.14.6, libxslt 1.1.43;
html5lib 1.1; cssselect 1.6.0; cssselect2 0.10.1; trafilatura 2.3.1; pylatexenc 3.0b2; spaCy
3.8.18 with en_core_web_sm 3.8.0 and en_core_web_trf 3.8.0 (CPU; torch 2.14.1 CPU build);
tokenizers 0.23.3 with Qwen3.5-9B (rev c2022362…) and GLiNER2.5-base-v1 (rev 54785d51…)
tokenizers. Full list in `results/environment.json`.

## Results

### Evidence model (78 pages)

| Check | Result |
|---|---|
| Structural invariants (start ≤ end, inside parent, siblings ordered, unique keys) | 0 violations |
| Independent text path: `string(.)` of each source element after removing excluded elements through the cssselect→XPath route, versus `canonical_text[start:end]` without rendered insertions | 19,432 checked, 0 mismatched |
| Determinism (four pages, two runs) | identical text and keys |
| Math spans | 28,948 `ok`, 8 `partial` (the unbalanced delimiters; reasons recorded) |
| Profile engines (cssselect2 `Matcher` versus cssselect→XPath) | identical node sets for every rule on every page; 0 role conflicts |
| Unclassified content (`division` segments) | 0 |
| Counts against the index | 77/78 pages equal on units, definition units (`p.dfn`), `dfn` terms, `details`, `\[` display math; `ExponentialLogarithmic`: −1 unit, −1 display math (the index counts a commented-out unit) |
| `dfn` terms item by item against `siegrist_defined_terms.tsv` | 0 differences |
| Locators of D2 §12.2 (`trace`, `core12`) | all 13 resolve to exactly one segment |

### Variants

| Variant | Result | Choice |
|---|---|---|
| V1 libxml2 vs html5lib | 4 of 78 pages differ: where a `<p>` is left unclosed before `<details>`, libxml2 keeps `details` (summary and proof) inside the paragraph; html5lib closes the paragraph as HTML5 does. Identical on the four spike pages | Propose html5lib for M01, or a libxml2 repair rule closing `<p>` before block elements; S0 uses the libxml2 rendition (identical text on its pages) |
| V2 NFC vs NFKC | no character changes on any page | NFC (D1 §3.1 confirmed) |
| V3 math whitespace | collapsing changes 1–5 multi-line formulas per spike page | keep verbatim |
| V4 nested h3/h4 vs h3 only | h3-only removes 4–9 sections per spike page; matters for scope extents (S0) | nested (D1 §3.2) |
| V5 profile engines | identical everywhere | either engine; cssselect2 adds conflict detection |
| V6 math detection | scanner and pylatexenc 3.0b2 with a prose-safe `ParsingState` agree on 28,943 spans; all differences are at the unbalanced delimiters, where pylatexenc runs one false span to the next closer and the scanner resynchronizes at the next opener. The default state swallowed 3 lines at prose `%` and opened false math at currency `$` (e.g. "$1000 units)", "$50 each") | keep the scanner for delimiting; pylatexenc 3 (strict, prose-safe) validates spans |
| V7 app units | 0–8 per spike page | keep, hinted `claim_bearing: false` |
| R1 `a.ref` | bracketed markers caused 4–6 mid-sentence splits; empty text reads broken | `[n]` exactly as the page's script renders it, one token that never starts a sentence (0 splits) |
| R2 `<q>` | small | quotation marks |
| R3 list markers | browser "a. " caused 8 false splits | "(a) " |
| R4 `details` summary | — | keep as a `heading` inside `details` |
| R5 figures | — | keep captions |

### Sentence segmentation (`OPEN-D1-1`)

Gold: 85 blocks (60 stratified by math density, display math, list items, `details` and traps,
plus the 25 blocks of the twelve core units), 134 sentences, 49 internal boundaries; two
independent markers agreed on every block.

| Pipeline | raw (a) | opaque mask (b1) | word mask (b2) | merged b′ | Unicode-rendered (d) |
|---|---|---|---|---|---|
| P1 `sm` parser | 0.80 | 0.70 | 0.89 | **1.00** | 0.70 |
| P1 + rule c (no split in display math) | 0.89 | 0.80 | 0.99 | **1.00** | 0.77 |
| P2 `sm` senter | 0.76 | 0.52 | 0.79 | 0.92 | 0.70 |
| P3 sentencizer | 0.99 | 0.73 | 0.99 | 0.99 | 0.91 |
| P4 `trf` parser (+c) | 0.99 (1.00) | 0.90 (0.91) | 0.97 (0.98) | 0.98 | 0.97 |

F1 on boundaries; full counts in `results/s1/sentences.tsv`. Raw text's errors are splits inside
math (20 of P1's 24 false splits); the opaque placeholder loses 16 boundaries; rendering math
to Unicode adds false splits after list markers and mid-clause. No combination made an
abbreviation error, so the abbreviation special cases have nothing to change. D4's proxy metrics
(lower-case or math-initial sentences) flag 3 of the 20 blocks P1-raw gets wrong: they cannot
stand in for a gold.

### Sizes (78 pages)

| | Units (2,479) | Paragraphs outside units (2,030) |
|---|---|---|
| Words: median / p90 / max | 71 / 178 / 1,201 | 38 / 100 / 409 |
| Qwen3.5-9B tokens: median / p90 / p99 / max | 143 / 372 / 736 / 2,197 | 52 / 154 / 305 / 575 |
| Over M06's 384 words | 17 | 1 |
| Over 512 GLiNER2 backbone tokens | 153 | 2 |
| Over 3,000 / 6,000 Qwen tokens (D4 §4.1 caps) | 0 / 0 | 0 / 0 |
| Math share of characters (median) | 0.43 | 0.08 |

Math is 35% of all canonical characters and costs about twice as many Qwen tokens per
character as prose (0.43 versus 0.20).

### Macros, links, repairs

- 29 distinct `\newcommand` definitions; the common ones (`\N`, `\R`, `\E`, `\var`, `\P`, `\sd`)
  are identical across pages, but several names have page-specific bodies (`\mse` →
  `\text{mse}` or `\text{MSE}`, `\kur` → `\text{kurt}` or `\text{kur}`, leading `\,` variants).
- Links: 1,799 to other pages, 589 ancillary (apps, data, biographies), 26 same-page anchors,
  9 external.
- Orphan text (text directly in a container): 44 runs (18 in `details`, 17 in units, 9 at
  section level), the same under both parsers; mostly display formulas placed bare in a unit.

## S1-E trafilatura baseline

`code/s1e_trafilatura.py` (executor subagent, 2026-10-28): passed on all 78 pages; trafilatura
2.3.1 XML output (`include_tables`, `include_formatting`, `favor_recall`) aligned with our
canonical text by normalized characters, our rendered insertions masked. Variants: plain; the
profile's exclusions as `prune_xpath`; that plus the empty `a.ref` anchors removed from the source.
Records: `results/s1/baseline_trafilatura.{tsv,md}`, `baseline_trafilatura_summary.json`.

| Our content missing from trafilatura | plain | pruned | pruned, empty refs removed |
|---|---|---|---|
| All (1,516,448 non-whitespace characters) | 5.28% | 5.34% | 2.73% |
| Headings (h2–h4) | 92.95% | 97.69% | 97.69% |
| `details` content | 11.33% | 11.33% | 3.10% |
| `details` summaries | 100% | 100% | 100% |
| Display math | 2.83% | 2.83% | 0.61% |
| `ol.sub` items | 2.16% | 2.16% | 1.20% |
| Captions | 99.06% | 99.06% | 99.06% |
| Tables | 0% | 0% | 0% |

Short proofs that end in an empty cross-reference link are dropped whole; headings next to
`div.unit` siblings are dropped. Unpruned, it keeps the `div.latex` macro block and navigation;
pruning with the profile's exclusion XPaths removes them. Every math span it keeps is verbatim.
Units, `details` and sections do not survive as structure; 26 list-nested tables come out as bare
cells. **Conclusion:** trafilatura is not usable as M01's fallback canonical text on a profiled
source; at most it can draft a provisional rendition (`profile: none`, `parse_status: partial`)
to help write a new profile. What the profile buys: the reference rendering (about 2.6 points of
content) and the structure S0 depends on (units, sections, summaries, captions).

## S1-F NIST generality probe

`code/s1f_nist.py` (same subagent): passed on 8 NIST 1.3.6 pages; records `results/s1/nist_probe.md`,
`results/s1/nist/`. The premise did not hold: the local NIST copy is now MathJax LaTeX (225 old
equation images are commented out; 4 live images on 3 pages). Findings:

- Of the Siegrist profile only the `scripts` and `images` rules match anything; both selector
  engines agree on every rule.
- Siegrist assumptions live in adapter code, not profile data: the corpus root, `div.unit`,
  `a.ref`, `ol.sub`, `div.latex`; sections are synthesized only from body-level headings (NIST
  gets none: its subsections are layout-table rows with two `h2` cells); tables are always content
  (NIST uses them for layout); `pre` loses its line breaks (the t-tables); `img alt` is lost; a
  `<ul>` used for indentation without `<li>` becomes orphan paragraphs.
- Image equations: excluded, the symbol vanishes ("…with degrees of freedom"); with `alt` surfaced
  it reads "nu", while the next item renders the same symbol from an entity as "ν". Other non-LaTeX
  math: `sub`/`sup` markup and ASCII math. NIST writes display formulas with inline delimiters
  (16 of 27 inline spans are a whole block).
- trafilatura on NIST is close to complete (headings, tables, `pre` with line breaks).

## Assumptions

- The project id in document keys is `corpus-structure`; `source_uri` is the corpus-relative path.
- Key parts are hashed as a JSON array in D1 §10.1's listed order.
- Segment kinds beyond D1 §3.2 used: `figure` (51, a container whose `caption` child is D1's
  kind); `division` reserved for unclassified blocks (none occurred).
- Text of a list item that also holds a nested list or table is its own `paragraph` segment
  (`inline_text_of`), so sentences never cross into the nested block.
- The sentence gold was marked by two fresh subagents rather than by the root plus a 20-block
  second marking (the plan's design): both marked all 85 blocks, which gives a reliability figure
  for the whole gold.
- pylatexenc 3.0b2 (prerelease) replaced 2.11 in the spike environment by operator suggestion;
  its legacy APIs behaved as 2.x where used.

## Design implications

| Design item | Proposed change or answer | Evidence |
|---|---|---|
| `OPEN-D1-1` | Closed: M03 = spaCy `en_core_web_sm` parser with inline math (and rendered reference markers) merged into one token before parsing and no boundary inside display math | Sentence table; gold agreement 85/85 |
| D4 M03 "Measured by" | Drop the lower-case / math-initial proxies as quality measures; keep them as diagnostics only | `sentences_proxies.json` |
| HTML-01 (D1 §3.1) | Bare `\begin{align}`/`align*` blocks are `math_display` segments with their environment kept verbatim | Gamma and 105 more blocks |
| HTML-02 (D1 §3.1, M01) | Math is delimited by M01's scanner, which resynchronizes at the next opener; each span is validated strictly with pylatexenc (prose-safe state) and an unbalanced span is `partial` with its reason | 8 partial spans; V6 |
| HTML-03 (D1 §3.1, M01) | Rendered-only text is part of canonical text by declared convention: `a.ref` as the page script renders it (`[n]`), `<q>` with quotation marks, ordered sub-list markers "(a) ", `details` summaries as headings; each insertion is recorded as markup so it can be stripped | R1–R5 |
| HTML-04 (D1 §3.2) | Confirmed: sections are synthesized from `h3`/`h4`, nested; the consequence for scope extents is S0's | V4 |
| HTML-05 (M01) | Parse with html5lib (or close `<p>` before block elements under libxml2); report orphan text as `paragraph` with `orphan: true` | V1 parser diff, repairs |
| HTML-06 (M01, M09, M11) | Page macros are per-rendition data (`parse_detail.macros`), with the pack's map only as fallback: bodies differ between pages for the same name | `macros.tsv` |
| HTML-07 (D4 M01) | The source profile is a set of CSS selectors with role payloads (D2 §12.1 plus `ul.map`, `align` environments, `p.stat`, `p.Proof`); either engine evaluates it identically | V5, coverage |
| D1 §3.2 | Add `figure` as a container kind (its `caption` is already a kind) | 51 figures |
| D4 §4.1, `OPEN-D4-4` | No unit exceeds the local 3,000-token cap; units, not sentence groups, fit the LLM packets on this corpus | Sizes |
| D4 M06, `OPEN-D2-2` | 153 units exceed 512 GLiNER2 tokens and math doubles token cost: M06 needs `extract_long`, and masking would shorten inputs (for S2) | Sizes |
| D1 §3.1 | NFC confirmed; NFKC changes nothing on this corpus | V2 |
| HTML-07 (D4 M01) | trafilatura is not M01's fallback; it may draft a provisional rendition for writing a new profile. The cssselect→XPath form of the profile is portable (trafilatura's `prune_xpath` accepted it unchanged) | S1-E |
| D4 M01 source profile | Move the Siegrist logic now in adapter code into profile data: roles `layout` (tables for layout), selector-based `section` rules with a heading source, `verbatim` (`pre`), per-selector list markers, a macro-source selector, per-selector rendering for `aref` and `img_alt`. Generic defaults: `pre` keeps whitespace, `img[alt]` is never silently lost, a list without items is a block | S1-F |
| D1 §3 (math) | Math segments carry `attrs.notation` ∈ {`latex`, `html`, `image`, `plain`}; image math uses its `alt` as text with `parse_status: partial` and `src` in attrs; display versus inline may come from layout, not only delimiters | S1-F |

## Follow-ups

- S2: compare raw, masked and Unicode-rendered math inputs (variant d's rendering is in
  `code/s1_sentences.py`).
- S5: the per-page macro tables and the 8 partial spans are its inputs; pylatexenc 3's
  `_`/`^` special nodes are the M09 candidate.
- If html5lib becomes the M01 parser, re-run S1-D under it as the default (its trees are already
  compared in `parser_diff.tsv`).
- A real image-equation source is still untested (NIST's local copy turned out to be MathJax);
  a second-corpus spike should pick one if non-LaTeX math matters.
- `sectionize` reading the profile's `sections` key (it currently uses body-level headings only)
  before any second source is ingested.

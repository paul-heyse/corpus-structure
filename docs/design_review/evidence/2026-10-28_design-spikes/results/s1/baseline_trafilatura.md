# S1-E: trafilatura as a profile-free baseline (2026-10-28)

Question (plan §7.1): is a generic main-content extractor a usable M01 fallback for HTML sources
without a source profile, and what does the Siegrist profile buy on a source that has one?

**Data.** `baseline_trafilatura.tsv`: one row per page and variant (78 first-pass pages × 3), with
our non-whitespace characters per segment kind (`tot_*`), those missing from trafilatura's output
(`miss_*`), characters trafilatura adds by the profile exclusion rule they come from (`kept_*`),
math span and delimiter counts, and element counts on both sides.

**Command.** `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1e_trafilatura.py`
(from the evidence folder): **passed** (2026-10-28; 78/78 pages, trafilatura returned a document
for every page and variant). trafilatura 2.3.1, lxml 6.1.3; the adapter at HEAD with
`DEFAULT_CONFIG`.

## Method

- trafilatura: `bare_extraction(raw, output_format="xml", include_tables=True,
  include_formatting=True, favor_recall=True, include_comments=False)` (the §3.1 settings; the
  2.3.1 signature accepts them unchanged). Its XML `Document.body` is read as text in document
  order with a space at every block boundary (trafilatura's own `xmltotxt` was not used because
  it inserts list and cell markers).
- Variants: `plain`; `pruned` (`prune_xpath` = the cssselect XPath translations of the profile's
  six exclusion selectors: scripts, `div.latex`, `header ol.map, footer`, `button`, `img`,
  `ul.map`); `pruned_noref` (pruned, and the 1,200-odd empty JS-filled `a.ref` anchors removed from
  the source first; added once `pruned` showed what they cause).
- Our side: the canonical text with the characters our rendering conventions add masked out
  (`[n]` for `a.ref`, `(a) ` list markers, the quotation marks around `<q>`), so only source text
  is compared.
- Alignment: both sides NFC with whitespace collapsed; rapidfuzz Indel opcodes over whitespace
  tokens, refined by character-level Indel opcodes inside every replace block. Counts are
  non-whitespace characters. A character missing from trafilatura is attributed to every segment
  kind containing it (the kinds overlap: a display formula inside a proof counts in both).
- "Short definition unit": a unit hinted `definition` with fewer than 300 characters.

## Results

Totals over the 78 pages; ours = 1,516,448 characters.

| Our content | Characters | Missing, `plain` | Missing, `pruned` | Missing, `pruned_noref` |
|---|---:|---:|---:|---:|
| **All** | 1,516,448 | 80,086 (5.28%) | 81,037 (5.34%) | 41,445 (2.73%) |
| Headings `h2`/`h3`/`h4` | 16,639 | 92.95% | 97.69% | 97.69% |
| `details` (proofs, solutions) | 469,142 | 11.33% | 11.33% | 3.10% |
| `details` summaries ("Details:") | 12,727 | 100% | 100% | 100% |
| Display math | 166,727 | 2.83% | 2.83% | 0.61% |
| Inline math | 367,999 | 3.94% | 3.94% | 0.85% |
| `ol.sub` list items | 286,027 | 2.16% | 2.16% | 1.20% |
| Other list items | 6,916 | 3.34% | 3.34% | 3.34% |
| Tables (33) | 8,498 | 0% | 0% | 0% |
| Definition units | 57,524 | 0.78% | 0.78% | 0.78% |
| Short definition units | 21,612 | 0.61% | 0.61% | 0.61% |
| All units | 1,004,750 | 5.89% | 5.89% | 1.95% |
| Prose outside units | 495,059 | 1.11% | 1.14% | 1.13% |
| Figure captions (51) | 2,886 | 99.06% | 99.06% | 99.06% |

Per page (missing %): `pruned` median 4.97, range 1.32–15.07 (Maxwell, Logarithmic, Pareto
highest); `pruned_noref` median 2.53, range 1.17–9.25 (poisson/Splitting highest).

In `pruned_noref`, three kinds account for 31,838 of the 41,445 missing characters: headings
(16,254), summaries (12,727) and captions (2,857 incl. caption math). What remains is 133 whole
list items (in the cases inspected, short `ol.sub` exercise sub-questions directly after a
statement paragraph), 55
whole paragraphs and 12 whole `details`.

### What the empty `a.ref` links cause

In `pruned`, 330 whole `details` blocks and 376 whole paragraphs (mostly the paragraph inside a
`details`) are missing, typically a short proof ending in an empty cross-reference anchor, e.g. a
proof ending "so the result follows from" plus an empty `a.ref` on dist/Discrete.html. On that
page, removing the empty anchors or filling them with text each restores the paragraph, while
renaming `details`/`summary` to `div`/`p` does not. Removing them for every page (`pruned_noref`)
halves total loss (81,037 → 41,445) and cuts proof loss from 11.33% to 3.10%. So the loss is
the JS-filled anchor (HTML-03), not the `details` element. Mechanism observed, not traced
inside trafilatura.

### Headings, summaries, captions

trafilatura emits 4–5 `<head>` elements over the whole corpus, against our 854 `h2`/`h3`/`h4`
headings and 1,592 summaries. A minimal document reproduces this: `<h3>` + `<p>` siblings keep
the heading as `<head rend="h3">` under `favor_recall`, but the same headings beside
`<div class="unit">` siblings are dropped. Siegrist's flat body (headings beside units) is exactly
that shape. The 7% of heading text "present" in `plain` is the `h2` title matched against the
breadcrumb's last item (`header ol.map`), so it is not a kept heading. Without `favor_recall`,
trafilatura also drops every list on Normal (69 items, 27% of its text). Captions go because
`<figure>` content goes with images (`include_images=False`).

### Boilerplate kept

| Excluded by our profile | Characters kept, `plain` | `pruned` |
|---|---:|---:|
| `div.latex` macro block (as a leading `<p>` of `\(\newcommand…\)`) | 20,899 | 0 |
| `header ol.map` breadcrumb (as a leading `<list rend="ol">`) | 1,187 | 0 |
| `ul.map` chapter lists, `footer`, scripts, buttons | 0 | 0 |
| Unattributed insertions (alignment noise: "Details:" ×4, punctuation) | 165 | 165 |

`prune_xpath` with the profile's exclusion XPaths removes every kept boilerplate character.
`ul.map` and the footer are dropped by trafilatura's own heuristics.

### Math

- Every math span whose text trafilatura retains is verbatim: 28,907 of 28,956 spans are found as
  exact substrings in `pruned_noref` (28,416 in `plain`/`pruned`). The rest lie in lost content.
  0 spans are altered: none has most of its characters aligned as present without matching
  verbatim.
- Delimiters, ours → `pruned_noref`: `\(` 27,138 → 26,841; `\[` 1,712 → 1,705; bare
  `\begin{align` 106 → 105. `&amp;` inside `align` is decoded as ours is. No escaping or
  rewriting of backslashes in the XML body. (`xmltotxt` with `include_formatting=True` does
  rewrite math for Markdown, so the body tree or XML output must be used, not txt/markdown.)

### Structure

Cross-tab, `pruned_noref`: for each of our text-bearing segments, the trafilatura element holding
exactly the same normalized text.

| Ours | trafilatura element | Not matched exactly |
|---|---|---|
| `paragraph` 5,828 | `p` 5,752 | 76 |
| `list_item` in `ol.sub` 4,074 | `item` 4,031 (`p` 1) | 42 |
| other `list_item` 105 | `item` 96 | 9 |
| `list` 1,510 | `list rend="ol"` 1,451, `rend="ul"` 14 | — |
| `table` 33, `table_cell` 1,085 | 7 `<table>` with `row`/`cell` (465 cells match) | 26 tables nested in `ol.sub` items come out as raw `th`/`td` children of `<item>`, with no rows (617 cells) |
| heading `h2`/`h3`/`h4` 854 | — | 854 |
| summary 1,592 | (`head` text-equal 86, but not positionally) | 1,506 |
| `unit` 2,479, `details` 1,593, `section` | no element | all |
| `caption` 52 | — | 52 |

trafilatura keeps the `class` attribute on 2,409 `p` elements (`math` 1,800, `app` 412, `dfn` 181,
`stat` 10, typos included), so the statement-kind hint classes survive. The unit, details and
section boundaries they belong to do not: a proof's paragraphs become ordinary `p` siblings of
the statement. A source typo element (`dffn`) passes through as an unknown tag.

## Conclusions (proposals, not decisions)

1. **Not usable as M01's fallback canonical text on this kind of source.** Even pruned and with
   the anchors removed, it loses all headings and summaries (so `section` synthesis, and the
   `proves` evidence span D5 §3.5 cites, are impossible), dissolves `div.unit` and `details` (no
   statement/proof boundary), and drops 1–9% of content per page with no record of what or why.
   D1 §3.2's `parse_status` cannot be filled from its output. (HTML-07; D4 M01.)
2. **Usable as an unprofiled triage/witness.** Retained text is verbatim, including all retained
   math. Paragraph and list-item boundaries match ours for ~99% of retained blocks. With
   `prune_xpath` it keeps no boilerplate. Proposed M01 role for unprofiled HTML: produce a
   provisional rendition flagged `profile: none`, with paragraph/list/table structure only,
   whole-document `parse_status = partial` ("heuristic extraction: headings and containers not
   preserved"), and a coverage figure against a structural walk of the same page. Its job is to
   find what a new source profile must declare, not to feed claims. (D4 M01 source-profile model.)
3. **What the profile buys on Siegrist**, by measurement: (a) 2.6 points of content (5.34% →
   2.73%) from one rendering rule, the `a.ref` convention; (b) all 854 headings, hence sections
   (HTML-04); (c) 1,592 summaries and 1,593 `details` boundaries, hence proof attribution; (d)
   2,479 unit boundaries with their ids; (e) 51 captions; (f) 26 list-nested tables as tables;
   (g) exclusions that are declared and recorded per element, not heuristic (the 22,086 boilerplate
   characters trafilatura keeps unpruned are exactly two profile rules). The profile's
   *exclusion* rules alone are cheap to state and fully effective as `prune_xpath`. Its value is
   mostly in *structure* rules (unit, details, sections) and *rendering* rules, which a generic
   extractor cannot supply.
4. **HTML-07 input.** The exclusion half of a profile written as CSS translates mechanically to
   XPath that a third-party engine (trafilatura's `prune_xpath`) accepts unchanged. This is a
   point for keeping the cssselect→XPath route (V5) as the profile's portable form, whichever
   engine M01 uses internally.

# S1 · Ingest and segmentation: plan

**Proposed (2026-10-28).** Part of the [S0/S1 plan series](../design-spikes-s0-s1_2026-10-28.md),
which owns shared decisions, the execution queue and finding disposition. The question is the
[S1 brief](../../design_review/evidence/2026-10-28_design-spikes/S1-ingest-and-segmentation.md)'s;
this document extends its scope and specifies how to answer it.

## 1. What S1 must establish

S1 builds a throwaway version of M01 (`ingest.html`), M02's size features and M03
(`segment.sentences`) and measures whether D1 §3 holds on Siegrist HTML:

- one deterministic canonical text per (document, adapter configuration), with D1 §3.1's
  separators, entity decoding, whitespace and NFC rules, and LaTeX verbatim between delimiters;
- a contiguous segment tree with D1 §3.2's kinds, every segment's text reproducible from
  offsets, author markup kept in `attrs`;
- sentence segments that do not break inside math and do not cross their block (OPEN-D1-1).

Its products are the evidence for those claims, the canonical text S0 annotates, `sample.json`,
and concrete rule specifications for the M01, M02 and M03 cards of D4, including the source
profile. Where the HTML forces a rule D1 does not yet state (rows HTML-01…07 of the
coordinator's findings table), S1 proposes the rule with its evidence.

Every variant below is included because its result can change one of those rules, or the text
that S0, S2 and S3 consume. Each variant states what it would change.

## 2. What the HTML looks like

A read-only inventory of all 78 first-pass pages (2026-10-28, stdlib parser and regexes) is
the starting point. S1-D re-establishes every figure with the selected parser and reports
differences.

| Area | Finding | Consequence for the adapter |
|---|---|---|
| Body structure | Flat: 2,479 `div.unit`, 2,021 `p`, 600 `h4`, 176 `h3` as body-level siblings; no `section` elements; per-page boilerplate `div.latex`, `header` (with `ol.map` and the `h2` title), `footer` (`ol.map`), `ul.map`/`li.sister` chapter lists, a trailing `<script>` | `section` segments must be synthesized from headings (HTML-04); boilerplate is excluded by declared rules |
| Units | 53% have no id; ids repeat three times; one id sits on an `ol`; the regex index counts a commented-out unit (2,480 vs 2,479) | Locate units by offsets and content hash; parse with comments removed |
| Unit content | First child is `p.math` 1,861, `p.app` 422, `p.dfn` 183, `p.stat` 10, `p.dfm` 2, `p.dfin` 1; typos `p.exericse`, `p.Proof`; every `details` is the unit's last block | Definition classes are `dfn`, `dfm`, `dfin` (the index counts only `dfn`); `p` class is a statement-kind hint; units are contiguous |
| `dfn` | 1,010 bare `<dfn>`, 620 outside units | `dfn` terms are author markup wherever they occur |
| `details` | 1,593, all inside units; summaries "Details:" (1,586), "Details", "Proof", "Notes:", "Answer", "Answwer:", one missing | Summary text is evidence for D5 §3.5's `proves` claim; its rendering is a convention (§4.3) |
| Math | 27,136 inline `\(…\)`, 1,710 well-formed `\[…\]`; display math sits in `p` (1,408), `li` (270), directly in a unit or `details` (31); 106 bare `\begin{align}`/`align*` blocks without `\[` (HTML-01); 71 spans contain `&amp;`; 11 unbalanced delimiters (HTML-02); no `$$`; no tags inside math | The math scanner must handle environments, decode entities first and resynchronize after errors |
| Malformed markup | ~26 misnested or unclosed `<p>` (8 `<ol>` inside `<p>`, 5 `<p>` before `details`, 12 before `</div>`); stray end tags; `<dffn>` typo | Parsers repair these differently, and the repair decides where orphaned text lands (HTML-05) |
| Rendered-only text | 1,200 empty `a.ref` links whose numbers JavaScript fills ("As a special case of , Stirling's…"); 69 `<q>`; `ol.sub` markers and `start="2"` continuations referenced in text ("which gives (b)") | Canonical text differs from what a reader sees unless a convention says otherwise (HTML-03) |
| Other | 33 tables (all in units), 51 figures, 508 app / 220 biography / 86 data ancillary links; no JSON-LD, Microdata, RDFa, Open Graph or Dublin Core; `meta name="author"`, `"keywords"` | Tables become table segments; document metadata comes from `title` and `meta` |

The four spike pages reproduce their index rows under the index's own regexes. Normal also has
a `p.dfm` definition (`pdf1`), LogNormal an unclosed `p.math` (unit without id), Gamma one bare
`align` block and one figure.

## 3. HTML extraction mechanisms

Five libraries were assessed against the responsibilities above, from the
[lxml overview](../../libraries/lxml.md) and the
[parsel, cssselect, cssselect2, trafilatura and extruct overview](../../libraries/parsel_cssselect_cssselect2_trafilatura_extruct.md),
checked against Context7, the lxml 6.1.3 changelog and the libxml2 2.14 release notes.

### 3.1 Selection

| Responsibility | Selected mechanism | Compared against | Not selected, with reason |
|---|---|---|---|
| Parse to a tree | `lxml.html.HTMLParser(remove_comments=True, remove_pis=True)` (recovering by default) with `lxml.html.document_fromstring(raw_bytes, parser=…)` | `lxml.html.html5parser.document_fromstring` (html5lib, WHATWG tree construction) — variant V1 | `lxml.html.soupparser`: no capability the two lack on this corpus |
| Repair inventory | Source-level detection: non-whitespace text that ends up as the `tail` of a block element (`ol`, `ul`, `div`, `details`, `table`) or directly under `body`/`div.unit`, joined to `sourceline`; html5lib's `HTMLParser().errors` for stray end tags | — | libxml2 `error_log`: empty for implied `<p>` closures under libxml2 2.14 (2026-10-28 probe), so it cannot be the inventory |
| Reading-order walk | `lxml.etree.iterwalk(root, events=("start", "end"))`, calling `skip_subtree()` on excluded elements while keeping their `.tail` (the semantics of `drop_tree()`) | — | Parser `target` interface: avoids the tree, but locators, `sourceline` and the independent text path need it |
| Source-profile rules | CSS selectors paired with role payloads, compiled with `cssselect2.compile_selector_list` into a `cssselect2.Matcher`, matched in one traversal over `cssselect2.ElementWrapper.from_html_root(root)`; each match returns `(specificity, order, pseudo, payload)` | The same selectors through `cssselect.HTMLTranslator().css_to_xpath` (`lxml.cssselect.CSSSelector(...).path` recorded) evaluated by lxml's XPath — variant V5 | Hand-written XPath lists: harder to read as a profile, and overlapping rules go undetected |
| Coverage audit | Every body element matched by no role rule is listed (tag, classes, page, `sourceline`) | — | — |
| Independent text path | `lxml.etree.XPath("string(.)", smart_strings=False)` per segment element (and `itertext()`), normalized by the same function, compared with `canonical_text[start:end]`; on mismatch, XPath `//text()` smart strings (`getparent()`, `is_tail`) locate the text node responsible | — | — |
| Math delimiting | Brace-aware scanner over decoded block text for `\(…\)`, `\[…\]` and bare `\begin{align|align*}…\end{…}` | pylatexenc `LatexWalker(text).get_latex_nodes()` → `LatexMathNode` (`pos`, `len`, `delimiters`, `displaytype`) — variant V6 | `latex2text`: rewrites math, which D1 forbids |
| Macro definitions | `div.latex` excluded from canonical text; its `\newcommand`s parsed with pylatexenc into a per-page macro table on the rendition | — | — |
| Profile-free baseline | `trafilatura.bare_extraction(html, output_format="xml", include_tables=True, include_formatting=True, favor_recall=True, include_comments=False)`, with and without `prune_xpath` set to the profile's exclusion XPaths — §7.1 | Our profiled adapter | — |
| Document metadata | XPath for `title`, `meta[@name='author']`, `meta[@name='keywords']` into document attrs | — | extruct: the pages carry no syntax it reads; deferred with a trigger (coordinator §8) |
| Spike-script querying | lxml XPath and `CSSSelector` | — | Parsel: a thin layer over the same lxml and cssselect whose `::text`/`string(.)` add nothing here, and whose `huge_tree=True` default relaxes libxml2's limits |
| Cleaning | Exclusion is a declared profile rule set | — | `lxml-html-clean` (a transitive dependency of trafilatura through jusText): a blocklist cleaner whose maintainers disclaim it for security use; not invoked |

**Why cssselect2's `Matcher` for the profile.** D4 M01 keeps a source profile (exclusions, unit
selector, statement-kind hints, rendering conventions) as data in the domain pack's
`methods.yaml`. Written as CSS selectors with role payloads, the profile is readable by the
operator and by Opus when proposing changes, and the `Matcher` evaluates all rules in one
traversal and returns every rule that matches an element with its specificity, so two roles
claiming one element are reported, not silently ordered. cssselect's translation of the same
selectors into XPath is an independent evaluation on lxml's native engine: the two must select
identical node sets. Whether M01 keeps both, or only the XPath route (fewer dependencies), is
decided by this agreement and by whether conflict detection found anything; it is not assumed.

**Why both parsers.** libxml2 2.14 made its HTML tokenizer HTML5-conformant but does not
implement HTML5 tree construction; html5lib does. Where Siegrist's markup is malformed (HTML-05)
the two trees can differ in which block an orphaned sentence belongs to. That changes segment
kinds and parents, and so which statement a claim belongs to.

### 3.2 Facts to re-establish in the evidence folder

The 2026-10-28 probe (coordinator §2) is not evidence. S1-A records, with commands:
`LIBXML_VERSION` and `LXML_VERSION`; that `ElementWrapper.from_html_root` accepts an
`lxml.html` root; cssselect2 and cssselect agreement on the profile; trafilatura's treatment of
`\(` delimiters and `details`. If cssselect2 fails on lxml trees, the profile is evaluated
through cssselect/XPath only and conflict detection is done by evaluating every rule and
intersecting node sets.

## 4. The adapter

`code/s1_adapter.py` turns a page's bytes plus an adapter configuration into a rendition:
canonical text, segments, author-markup records, excluded-content records and rendition
attributes. Its configuration is a single JSON document whose canonical hash is the adapter
config hash in the rendition key (D1 §10.1).

### 4.1 Pipeline

1. **Decode and parse.** Bytes are parsed with the configured parser (§3.1). Document metadata
   is read. The page's `div.latex` is parsed into the macro table before exclusion.
2. **Match profile rules.** The `Matcher` assigns roles: `exclude:<rule>`, `unit`,
   `definition`, `statement_hint:<kind>`, `details_summary`, `render:<convention>`,
   `block`/`inline` overrides. Conflicts and unmatched elements are recorded.
3. **Walk.** `iterwalk` emits canonical text in reading order. Block elements open and close
   segments; excluded elements are skipped with their tails kept; inline elements contribute
   text; `dfn`, links and other markup become `author_markup` records with offsets.
4. **Delimit math.** Within each block's text, the math scanner marks `math_inline` and
   `math_display` spans (entities already decoded), never rewriting what is inside.
5. **Synthesize sections.** Headings open `section` segments that close at the next heading of
   the same or higher level (variant V4 decides which levels).
6. **Normalize.** Whitespace collapse and Unicode normalization apply as configured; offsets
   are code points of the final text, computed after normalization so no offset map is needed
   downstream.
7. **Emit.** Segments with keys, `parse_status` and attrs (including `sourceline` and the
   matched rule), author-markup records, excluded-content records with their rule, rendition
   attributes.

### 4.2 Canonical-text rules to specify

Starting point is D1 §3.1. The adapter makes every rule explicit, including those D1 leaves
open:

| Rule | Starting proposal | Open by |
|---|---|---|
| Block separator | `\n\n` between block elements; `\n` between list items; `\t` / `\n` for table cells / rows | — |
| Display math inside a `p` or `li` | Stays inside its block, delimited `\[ … \]`; a `math_display` child segment | — |
| Bare `align` environments | `math_display` segments with their `\begin…\end` kept verbatim (HTML-01) | — |
| Unbalanced delimiters | The scanner closes the span at the block end and marks the math segment `parse_status = partial` with the reason (HTML-02) | V6 |
| Whitespace | Collapsed to one space within a block; inside math either kept or collapsed | V3 |
| Unicode | NFC | V2 |
| Rendered-only text | Per convention | §4.3 |
| Excluded content | `div.latex`, `header`, `footer`, `ol.map`, `ul.map`, scripts, buttons, icon images | V7 for app units |

### 4.3 Rendering conventions (HTML-03)

Each convention is rendered in two or three ways on the four spike pages and measured for its
effect on sentence segmentation (S1-C) and on quote location (the instruments' tests). The
adopted choice becomes an M01 rule.

| Case | Options | What decides |
|---|---|---|
| Empty JS-filled `a.ref` links | (a) nothing; (b) a fixed placeholder such as `[ref]`; (c) the link target's anchor text or unit id | Sentence splits around the gap; whether annotators and LLMs read "As a special case of , …" as broken text; quote stability |
| `<q>` | (a) bare text; (b) wrapped in “ ” | Fidelity to the rendered page versus source text; quote matching |
| `ol.sub` item markers | (a) no marker text, marker in attrs; (b) marker text "(a) " computed from `type` and `start`, continuing across `start="2"` | Proof references "(b)" must resolve; marker text inside canonical text changes offsets and sentence starts |
| `details` summary | (a) a `heading` segment inside `details`; (b) excluded | D5 §3.5 cites the summary span as `proves` evidence |
| Figures and images | (a) `alt`/caption text as a `caption` segment; (b) excluded | Content loss versus noise; matters more for NIST (§7.2) |

### 4.4 `sample.json` and keys

For each core unit: page, document key, rendition key, segment keys (D1 §10.1, with the adapter
config hash), `start`, `end`, a SHA-256 of the unit's canonical text, the sentence ids of the
adopted sentence variant, and the first 80 characters. Units are found by a locator that uses
the page, the unit's opening text and, where needed, its position (T2's "again"; `rel2` on two
pages), and records how each was found. Keys use `canonical_json` exactly as D1 §10.1 specifies
(sorted keys, no insignificant whitespace, UTF-8, NFC strings).

## 5. Variants of the adapter

Run on the four spike pages first (S1-A), then on all 78 where the variant concerns
corpus-wide structure (S1-D).

| Id | Variant | Measured as | Changes |
|---|---|---|---|
| V1 | Parser: libxml2 versus html5lib | Tree diff by element path, kind and text on all 78 pages; each difference placed against the repair inventory (§3.1) and classified: same content, different parent / text moved between segments / content lost | Which tree M01 specifies; how orphaned text after a repaired `<p>` is assigned (own `paragraph` or reattached) |
| V2 | Unicode: NFC versus NFKC (the old adapter's choice) | Inventory of code points that differ, inside and outside math, with examples | D1 §3.1's NFC rule confirmed or amended |
| V3 | Whitespace inside math: kept versus collapsed | Number of math spans whose text changes; effect on quote location for quotes copied from rendered math | D1 §3.1's "nothing inside math is rewritten" against "whitespace collapses within a block" |
| V4 | Section synthesis: `h3` only versus nested `h3`/`h4` | Section segment counts and sizes; for each core unit, which section contains it and its standing assumptions | The `section` extent used by OPEN-D1-2/4 and M13; S0 analyses scopes under both |
| V5 | Profile evaluation: cssselect2 `Matcher` versus cssselect → XPath | Node-set equality per rule and page; rule conflicts; unmatched elements | The profile language and engine for M01 (HTML-07) |
| V6 | Math detection: brace-aware scanner versus pylatexenc `LatexWalker` | Span-level agreement; categorized disagreements; behaviour at each of the 11 unbalanced delimiters (where each resynchronizes, what text is mis-typed as math or prose) | The M01 math rule and `parse_status` for math segments (HTML-02) |
| V7 | App units (`p.app`, 422 units): kept and flagged versus excluded | Unit counts against the index; characters affected | Whether apps are content (with a statement-kind hint) or excluded |
| R1–R5 | Rendering conventions | §4.3 | M01 rendering rules (HTML-03) |

## 6. Sentence segmentation (OPEN-D1-1)

### 6.1 Variants

Two dimensions: the spaCy component that sets boundaries, and how math is presented to it.

| Component | Mechanism |
|---|---|
| P1 | `en_core_web_sm` dependency parser (the brief's baseline) |
| P2 | `en_core_web_sm` with `senter` enabled and the parser disabled |
| P3 | Rule-based `sentencizer` on a blank English pipeline |
| P4 | `en_core_web_trf` parser (CPU) |

| Math handling | Mechanism |
|---|---|
| (a) | Raw canonical text |
| (b1) | Inline math replaced by an opaque placeholder `⟨m12⟩`, offsets mapped back |
| (b2) | Inline math replaced by a word-like placeholder (`MATHTOKEN12`), offsets mapped back; tests whether the placeholder's shape changes the parser's behaviour |
| (b′) | D4 M03's candidate: a component before the parser merges each inline math span into one token with `doc.retokenize()` (`POS=PROPN`) and sets `is_sent_start = False` inside display math; offsets stay in canonical text |
| (c) | (b1), (b2) or (b′) plus: never split inside display math, never let a sentence cross its block |

A tokenizer special-case set for abbreviations ("i.e.", "e.g.", "cf.") is applied on and off
to the best two combinations. Every combination runs on every paragraph and list item of the
four spike pages (268 `p`, 187 `li`).

### 6.2 Gold and scoring

The brief asks for judgment of 60 paragraphs; S1 builds an explicit boundary gold instead, so
variants are scored, not eyeballed:

- **Sample:** 60 blocks stratified by inline-math density (none, low, high), display math
  present, list item, inside `details`, and the known traps ("i.e.", "Then" after display
  math, a sentence ending in math), plus every block of the twelve core units.
- **Gold:** the root marks sentence boundaries as character offsets with a short written rule
  set (what counts as a sentence across display math and list markers). A fresh subagent marks
  a 20-block overlap independently from the same rules; disagreements are resolved and the rule
  set amended, and the agreement on the overlap is reported as the gold's own reliability.
- **Scores per combination:** boundary precision, recall and F1 against the gold; errors
  categorized as split inside math, split after an abbreviation, split before "Then"/"where",
  missed split after display math, sentence crossing a block. Counts are reported with their
  denominators.
- **Proxies:** D4 M03 proposes proxy metrics (share of sentences starting lower-case or with a
  math token). Their correlation with gold errors is measured on the sample; if they track the
  errors, they are applied to all 78 pages as the corpus-wide estimate, otherwise the report
  says they are not usable.

The adopted combination is the one with the best F1 among those that never split inside math;
ties go to the simpler mechanism. The answer to OPEN-D1-1 states it and the residual error
categories.

## 7. Baselines and generality

### 7.1 Profile-free baseline (trafilatura)

On all 78 pages, trafilatura's XML output (§3.1 settings) is compared with our canonical text,
with and without the profile's exclusions passed as `prune_xpath`. Alignment is by normalized
character runs (whitespace collapsed, both sides NFC). Reported per page: characters of our
content missing from trafilatura's output, by segment kind (proofs in `details`, display math,
`ol.sub` items, short definition units, tables); boilerplate trafilatura keeps (the 2026-10-28
probe saw `div.latex` and navigation lists); whether math delimiters survive verbatim; how its
`<head rend>`, `<list>`, `<item>` and `<table>` structure compares with our segment tree.

This answers two design questions: whether a generic extractor is a usable M01 fallback for HTML
sources without a profile, and what the profile buys on a source that has one.

### 7.2 Second-source generality probe (NIST)

Five to eight NIST e-Handbook section 1.3.6 HTML pages (46 local files; equations are images)
go through a generic profile (structural rules only) and through trafilatura. Reported: which
M01 rules were Siegrist-specific, how image equations and their `alt` text appear in canonical
text, and what D1 §3 would need for math that is not LaTeX. This informs the D4 M01
source-profile model and D0's claim of a generic core; it is the lowest-priority S1 package and
never blocks S0.

## 8. Corpus-wide measurements (78 pages)

| Measurement | Method | Reported as |
|---|---|---|
| Structure counts versus the index | Units, definition units, `dfn` terms, `details`, display math per page, ours and index | `counts.tsv` with deltas; every delta explained as adapter error, index rule difference (comment, `dfm`/`dfin`, bare `align`) or genuine ambiguity |
| `dfn` terms item by item | Our terms (text, page, containing unit or paragraph) against `siegrist_defined_terms.tsv` | Matched, missing, extra, with reasons |
| Invariants | `start <= end`; children inside parents; siblings ordered and non-overlapping; independent text path equals the offset substring | `invariants.json`: violations by invariant and kind, with examples |
| Contiguity | Any unit or statement whose content is not contiguous in reading order, including text displaced by parser repair | Count and list; D1 §3.2 assumes none |
| Determinism | Two runs from clean state | Byte-identical canonical text and identical key sets |
| Statement-kind hints | Id prefixes and `p` classes per unit | Proposed hint map for M01/M02 with counts |
| Macro tables (HTML-06) | `\newcommand` sets per page | Identical across pages, or which pages differ and how |
| Links and keywords | Internal links (page and unit-anchor targets), ancillary links, `meta keywords` | Inventory reported as author evidence available to M14 and `refers_to`; not used further here |
| Sizes | Per unit and paragraph: characters, words, math share, Qwen3.5-9B tokens, GLiNER2 backbone tokens | Distributions; units over M06's 384-word limit; units over D4 §4.1's 3,000- and 6,000-token caps; tokens per character inside versus outside math (inputs to OPEN-D2-2, OPEN-D4-4) |
| Wall time | Incidental | One line in the report, not a criterion |

## 9. Packages

| Package | Scope | Outputs | Done when |
|---|---|---|---|
| S1-A | Adapter, selected mechanisms, profile rules, variants V1–V7 and conventions R1–R5 on the four spike pages; conventions and section synthesis adopted for S0 | `canonical/`, `segments/`, `renditions.json`, `exclusions.tsv`, `profile.css.json` (selectors and roles), `variants_s1a.md` | S0 can be given its canonical text; each variant has a measured result and a stated choice or an explicit deferral to S1-D |
| S1-B | Locator, `sample.json`, invariants with the independent path, determinism, provisional sentences (P1 with (b′)) | `sample.json`, `invariants.json`, `sentences/<page>.provisional.jsonl` | Twelve units located with how each was found; zero unexplained invariant violations |
| S1-C | Sentence gold, second marking, combination matrix, proxies | `sentence_gold.jsonl`, `sentence_gold_agreement.md`, `sentences.tsv`, `sentences/<page>.<variant>.jsonl` | Adopted combination named with F1 and error categories |
| S1-D | 78-page run of the adopted configuration plus V1, V5, V6, V7 corpus-wide; all §8 measurements | `counts.tsv`, `parser_diff.tsv`, `repairs.tsv`, `coverage.tsv`, `dfn_terms.tsv`, `macros.tsv`, `links.tsv`, `sizes.tsv`, `contiguity.tsv` | Every count delta explained |
| S1-E | trafilatura baseline | `baseline_trafilatura.tsv`, examples in the report | §7.1 questions answered |
| S1-F | NIST probe | `nist_probe.md` | §7.2 questions answered or the probe reported `not_run` with the reason |
| S1-G | Report | `S1-report.md` | §10 satisfied |

The brief's data files (`canonical/`, `segments/`, `counts.tsv`, `invariants.json`,
`sentences.tsv`, `exclusions.tsv`, `sample.json`) all appear above.

## 10. What the report must state

`S1-report.md` follows the template. Its "Design implications" table must include:

- **M01 specification:** parser and options; the source profile as CSS rules with roles; each
  canonical-text rule of §4.2 including rendering conventions; exclusion rules; math rules
  (environments, decoding, resynchronization, `parse_status`); section synthesis; macro-table
  handling; document metadata; the repair handling for orphaned text. Each rule cites the
  measurement that chose it.
- **M02 features** confirmed or changed, with the statement-kind hint map.
- **M03 specification:** adopted combination, its scores and residual error categories; the
  answer to OPEN-D1-1.
- **D1 §3 changes** proposed for HTML-01…05 and any invariant or contiguity violation found.
- **Inputs handed on:** macro tables and math-span inventory to S5; math token costs to S2
  (OPEN-D2-2); size distributions to S3 and OPEN-D4-4; trafilatura and NIST evidence to the M01
  source-profile model (HTML-07); the spike environment's Python 3.14 resolution, including
  the spaCy model wheels and the CPU transformer stack, as evidence for OPEN-D9-1.

Interpretation follows the brief's table: counts within the explained deltas on at least 95% of
pages and no invariant violations confirm D1 §3; systematic mismatches name the index rule or
ours; non-contiguous units call for multi-range segments or a `continues` relation, with their
frequency.

## 11. Choices left to execution

- The exact placeholder strings in (b1) and (b2), the abbreviation list, and the sentence-gold
  rule wording.
- The stratification thresholds for inline-math density, chosen from the observed distribution
  on the four pages.
- Which NIST pages form the probe (preferring pages with lists, tables and image equations).
- Whether V1, V5 or V6 need all 78 pages once the four-page results are in: if a variant shows
  no difference on the pages with known malformations, the corpus-wide run can be limited to
  those pages, and the report says so.

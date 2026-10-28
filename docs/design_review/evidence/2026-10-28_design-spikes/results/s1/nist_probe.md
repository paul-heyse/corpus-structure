# S1-F: NIST e-Handbook generality probe (2026-10-28)

Question (plan §7.2): which M01 rules are Siegrist-specific; how image equations and their `alt`
text appear in canonical text; what D1 §3 needs for math that is not LaTeX; how section structure
maps.

**Pages (8 of the 37 section 1.3.6 files).** `eda361` (`ol` with `\[…\]` display math), `eda3652`
(`ul`/`ol` lists), `eda3661` Normal and `eda3662` Uniform (inline LaTeX, plots with `alt`,
statistics tables), `eda367` (list with a live equation image), `eda3671`, `eda3672`, `eda3675`
(critical-value tables in `<pre>`, live equation images).

**Data.** `nist/probe.json` (per page: segment kinds, headings and their ancestors, math, `pre`
blocks, marginal notes, exclusions, Siegrist rule hits, trafilatura comparison);
`nist/<page>.generic.txt`, `nist/<page>.generic_alt.txt` (canonical texts);
`nist/<page>.trafilatura.xml` (trafilatura's XML body).

**Command.** `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1f_nist.py`
(from the evidence folder): **passed** (2026-10-28; 8/8 pages parsed and serialized, cssselect2
and XPath engines identical on every rule and page). `s1_adapter.py` is imported unchanged.
`adapt()` itself cannot be called because it hard-codes the Siegrist root and YAML loader, so
`adapt_generic()` repeats its driver steps.

**Generic profile** (in `code/s1f_nist.py`): exclusions `script, noscript, style`, `button`,
`img`; title `head > title`; `sections: [h1…h6]`; no unit, block hints or details rules; math
delimiters `\(…\)`, `\[…\]`, bare `align`/`align*`.

## Premise check: equations are mostly not images any more

The local copy has been converted to MathJax. Every page loads `tex-mml-chtml.js`, and the old
equation GIFs sit in HTML comments next to their LaTeX replacement, e.g. a commented
`<img src="eqns/unipdfg.gif" alt="f(x) = 1/(B - A) for A <= x <= B">` followed by
`\( f(x) = \frac{1} {B - A} … \)`. Across the 37 files: 225 commented equation images. Live
equation images exist on 3 files, 4 in total (`eqns/nu.gif` "nu", `eqns/infty.gif` "infinity",
`eqns/tstar05.gif` "t*(.05)(nu)" twice). The other live images are plots (`gif/*.gif`, with
descriptive `alt`) and navigation bars (no `alt`). With `remove_comments=True`, the commented
images and their `alt` text never reach the tree. The image-equation question is therefore small
on this source, and the probe also covers the other non-LaTeX notations it uses.

## Results

| Page | Canonical chars | Segments (main kinds) | Math (inline/display) | trafilatura missing % |
|---|---:|---|---|---:|
| eda361 | 3,080 | 9 cells, 19 paragraphs, 6 list items | 0 / 4 | 1.48 |
| eda3652 | 4,348 | 11 cells, 17 paragraphs, 11 list items | 0 / 0 | 0.73 |
| eda3661 | 4,213 | 43 cells, 29 paragraphs, 5 list items | 9 / 0 | 6.04 |
| eda3662 | 3,734 | 39 cells, 35 paragraphs, 4 lists, 0 items | 16 / 0 | 8.67 |
| eda367 | 947 | 5 cells, 3 paragraphs, 6 list items | 0 / 0 | 5.05 |
| eda3671 | 5,659 | 34 cells, 13 paragraphs, 3 list items | 2 / 0 | 2.45 |
| eda3672 | 5,786 | 6 cells, 8 paragraphs, one 4,174-char `pre` | 0 / 0 | 1.07 |
| eda3675 | 1,902 | 6 cells, 3 paragraphs, one 1,096-char `pre` | 0 / 0 | 2.81 |

All 31 math spans scan `ok` and validate under pylatexenc 3.0b2 (no partial spans, no anomalies).
The default macro context suffices (`\mbox`, `\hat`, `\bar`, `\sqrt`). The pages have no
`div.latex` and an empty macro table.

### Siegrist-specific rules: what fails or does nothing

Siegrist profile rules evaluated on the NIST trees: only `exclude:scripts` (5–6 per page) and
`exclude:images` (2–9) match anything. `div.latex`, `header ol.map, footer`, `ul.map`,
`button`, `header h2` (title), `div.unit`, all seven `p.*` block hints, `details`,
`details > summary`, `section_hints` and `details_kinds` match nothing.

Adapter code that assumes Siegrist (proposed changes; `s1_adapter.py` not edited):

| Code | Assumption | Effect on NIST | Proposed M01 change |
|---|---|---|---|
| `adapt()` | corpus root `SIEGRIST`, profile from `code/profile/<name>.yaml` | cannot be called for another source | take `(bytes, source_uri, profile)` |
| `sectionize()` | levels from `config["sections"]` (`h3h4`/`h3`), only over the body's direct children | the profile's `sections` key is ignored; NIST's `h2`s sit 6 levels deep in layout tables, so 0 sections | levels come from the profile; a section rule may be a selector (see below), not only heading tags |
| `Builder.__init__`, `inline()` | `unit` class and `a.ref` + Basic.js numbering are hard-coded | inert | make both profile rendering rules (`render.aref` with its selector) |
| `list_marker()` | only `ol.sub` gets markers | NIST `ol` items get no number, though the text cites "properties 2 and 3" | marker rule per selector in the profile (`ol` → "1. "), with `type`/`start` |
| `macro_table()` | `div.latex` | empty table | macro-source selector in the profile (`math.page_macros`) |
| `BLOCK_KIND` / `TRANSPARENT` | tables are content | the whole page body is a layout `table`: every block is a `table_cell` descendant; the breadcrumb is the first cell | a profile role `layout` (transparent container) for `table`/`tr`/`td`, separate from data tables |
| `process_run()` | whitespace collapses in every non-math run | `pre` tables lose every row break: 0 newlines kept in eda3672's 4,174-char table | `pre` (and a profile `verbatim` role) keeps whitespace and line breaks |
| `inline()` on `img` | images contribute nothing even when not excluded | `alt` text is lost | `render.img_alt` convention (below) |
| `<ul>` without `<li>` | lists contain items | eda3662/eda3671 use `<ul>` as an indent for displayed equations: 5 lists with no items (4 + 1), their text recorded as 5 `orphan` paragraphs with container `list` | profile rule `ul:not(:has(> li))` → block (indented paragraph) |

What carried over unchanged: lxml parsing with comment removal (HTML 4 uppercase tags,
unclosed `<p>`, `&nu;`/`&alpha;` entities), the cssselect2/XPath engines, the iterwalk
build/serialize, the math scanner and pylatexenc validation, keys, exclusion records.

### Image equations and `alt` text

- **Generic profile (images excluded, as in D2 §12.1):** the image disappears with its `alt`. The
  sentence reads "Upper critical values of Student's t-distribution with degrees of freedom"
  (eda367). The exclusion record keeps only the rule and element, not `alt` or `src`.
- **`generic_alt` probe (`img[alt]` → inline text):** the same item reads "… with nu degrees of
  freedom". The next item on that page renders the same symbol from `&nu;` as "ν", so one page
  carries two notations for one symbol. In eda3675 the table header becomes
  "ν t*(.05)(nu) ν t*(.05)(nu)". Plot `alt`s ("plot of the standard normal probability density
  function") land as a separate block after the paragraph that introduces the plot, reading as a
  caption.
- **Commented images:** their `alt` (an ASCII rendering such as "SUM[p(j)] = 1") is discarded with
  the comment. Correct: it is not rendered content, and the live LaTeX replaces it.

### Other non-LaTeX math on these pages

- HTML-markup math: `t<sub>1-α,ν</sub> = -t<sub>α,ν</sub>` linearizes to "t1-α,ν = -tα,ν." The
  `sub`/`sup` survive only as `author_markup` records with offsets (eda3672: 4 `sub`; eda367:
  2 `sub`, 1 `sup`).
- ASCII math in prose: "0 <= p(x) <= 1" (eda361), "(A + B)/2" (eda3662 statistics table).
- Display-ness by layout, not delimiter: NIST writes displayed formulas with inline `\( … \)`
  delimiters, alone between `<p>`s or inside an indent `<ul>`. All 27 inline-delimited spans on
  eda3661/eda3662/eda3671 become `math_inline`. Yet 16 of them are the whole text of their
  block, and others sit two to an indent block separated by `<BR>`.

### Section structure

- The page is one handbook section: its number and title are two `h2`s in separate cells of a
  nested table ("1.3.6.6.2." | "Uniform Distribution"). The `<title>` holds both. The hierarchy
  above it is the breadcrumb (first layout cell: "1. Exploratory Data Analysis 1.3. EDA
  Techniques …"), kept as content by both the generic profile and trafilatura.
- Subsections are layout rows: a 15%-wide first cell holds the label in `<i>` (eda3661: 12 rows,
  from "Probability Density Function" to "Software"), the 85% cell the body. In canonical text
  this reads as "Probability Density Function⇥The general formula …", a table row, not a
  section. The generic profile yields 0 `section` segments on all 8 pages.
- A NIST profile would need: `tr:has(> td[width="15%"])` → `section` with its heading from the
  first cell; the two `h2` cells → one `heading` (number in attrs); breadcrumb → document attrs
  (parent sections, cross-page) and excluded from text; layout tables transparent.

### trafilatura on NIST

trafilatura does much better here than on Siegrist. It keeps both `h2`s as `<head rend="h2">`,
the layout tables as `table/row/cell`, the lists, `pre` as `<code>` *with* its line breaks, and
every math span verbatim (31/31). Its "missing" 0.73–8.67% is reordering, not loss: every large
missing run in `probe.json` reappears as an insertion (it emits the `h2` title cells and, on
eda3661/eda3662, the "Common Statistics" table at another position). It keeps the breadcrumb.
It does not recover sections from the marginal-note rows, and it drops images and their `alt`
(`include_images=False`).

## Conclusions (proposals, not decisions)

1. **D0's generic-core claim holds for the walk, not for the profile.** Parser, rule engines,
   build/serialize, math scanning/validation and keys ran unchanged on a second, much older HTML
   dialect. Every Siegrist profile rule except scripts/images matched nothing. Structure on NIST
   comes from different mechanisms: layout tables, marginal-note rows, `ul` as indent, `pre`
   tables. (D4 M01 source profile; HTML-07.)
2. **D4 M01 source-profile model: roles beyond selectors-for-tags.** The profile needs, besides
   `exclude`/`unit`/`block_hints`: `layout` (transparent containers), `section` rules by selector
   with a heading source (cell, child, attribute), `verbatim` (whitespace-preserving blocks),
   list-marker rules per selector, macro-source selector, and per-selector rendering conventions
   (`aref`, `img_alt`). The adapter's code paths for `unit`, `a.ref`, `ol.sub`, `div.latex` and
   `h3`/`h4` move into profile data. `sectionize` should read the profile, and the profile's
   `sections` key, currently ignored, becomes binding. (D4 M01; HTML-04, HTML-07.)
3. **Generic defaults that M01 should ship regardless of profile.** `pre` keeps whitespace;
   `img[alt]` is never silently lost (rendered or recorded with `alt` and `src` in the exclusion
   record); a `ul`/`ol` with no `li` is a block, not a list. (D4 M01; D1 §3.1.)
4. **D1 §3 for math that is not LaTeX.** D1 §3.1 now says math is LaTeX between its delimiters.
   Proposed additions:
   - math segments carry `attrs.notation`: `latex` | `html` (`sub`/`sup`/`i` + entities) |
     `image` | `plain`;
   - an `image` math segment's canonical text is its `alt` (empty if none), with `src` and the
     alt's provenance in attrs and `parse_status = partial` ("image equation: alt text only");
   - `html` math is detected by a profile rule (e.g. inline runs containing `sub`/`sup`), and its
     text is the linearized characters, with the markup kept as `author_markup`;
   - `math_display` versus `math_inline` is decided by layout (alone in its block) when the
     profile says so, not only by delimiter.

   S5 decides whether any non-LaTeX notation gets a LaTeX-normalized rendition (that would be a
   derived view, never canonical text). (D1 §3.1, §3.2; HTML-03.)
5. **trafilatura as fallback.** On classic table-layout HTML it is a reasonable unprofiled
   witness, keeping headings, tables and `pre`. On Siegrist it is not (S1-E). Its quality
   depends on page shape in ways not predictable in advance, which supports S1-E's proposal: a
   provisional, flagged rendition used to draft a profile, not a canonical-text producer.
   (HTML-07.)

**Limits.** 8 of 37 pages from one section, chosen for lists, tables and images. The live
equation-image cases are 4 images on 3 pages. The `generic_alt` variant is a pre-walk tree edit
in the probe script, not an adapter feature.

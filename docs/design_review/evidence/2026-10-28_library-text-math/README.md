# Library realization: text and math (M01, M02, M03, M09, M11, M13, D4 §4.3)

**Date:** 2026-10-28. **Worker:** library-research (contract `.agents/roles/library-research.md`).
**Baseline:** `main` at `71bb064` (untracked `docs/libraries/html5lib.md` and `pgevector.md` present
and read; nothing else dirty).

## Question

How should the production versions of the text-and-math methods use their libraries from the start?
The spikes already established what works. The production methods are HTML ingest (M01), segment
profiling and token counts (M02, D4 §4.1 caps), sentences (M03, variant b′), the one math grammar
(M09, M11, ADR-0012), symbol scoping (M13) and quote location (D4 §4.3). This note names mechanisms,
conditions, version caveats and things to avoid, plus proposed changes to the D4 cards and the
D1 §3/§6 contracts (`L-nn`). The coordinator decides adoption.

## Sources and versions

Every probe ran in the spike environment
(`docs/design_review/evidence/2026-10-28_design-spikes/pyproject.toml`, `uv.lock`).

| Library | Version | Overview read end to end | Context7 | Source checked |
|---|---|---|---|---|
| lxml (libxml2) | 6.1.3 (2.14.6) | `docs/libraries/lxml.md` (§3.1, §4.5, §8.5, §11) | `/websites/lxml_de` html5parser page | installed `lxml/html/html5parser.py` (lines 27–31, 55–76, 260) |
| html5lib | 1.1 | `docs/libraries/html5lib.md` (§2.4–2.5, §3.3, §4.1–4.4, §8.2, §9.2–9.5) | `/html5lib/html5lib-python` | installed `html5lib/treebuilders/etree_lxml.py` (185–363), `html5lib/_ihatexml.py` (210–270) |
| cssselect / cssselect2 | 1.6.0 / 0.10.1 | `parsel_cssselect_cssselect2_trafilatura_extruct.md` §1, §3, §4 | resolved (`/scrapy/cssselect`) | spike `s1_adapter.py` |
| regex | 2026.9.29 (in the spike only as a transitive dependency of dateparser and curated-tokenizers) | `docs/libraries/regex.md` | `/mrabarnett/mrab-regex` (named lists, timeout) | probe |
| pylatexenc | 3.0b2 (stable 2.11) | `docs/libraries/pylatexenc.md` | `/phfaist/pylatexenc` (v2 macro API, new-in-3) | spike `s1_adapter.macro_table`, `validate_span` |
| lark | 1.3.1 | `docs/libraries/lark.md` | `/lark-parser/lark/1.3.1` (`classes.rst`: options, `cache` LALR only) | installed `lark/lark.py` (`save`), `lark/lexer.py` |
| SymPy | 1.14.0 | `docs/libraries/Sympy.md` §1–2, §11.1, §15, §17.6 | `/sympy/sympy` `parsing.rst` (Lark backend experimental, `grammar_file`, `transformer`) | installed `sympy/parsing/latex/lark/latex_parser.py`, `grammar/latex.lark` lines 1–11, `transformer.py` |
| spaCy, en_core_web_sm | 3.8.18, 3.8.0 (the overview targets 3.8.16) | `docs/libraries/spacy.md` | `/websites/spacy_io` linguistic-features (preset boundaries; `None` vs `False`) | installed `spacy/pipeline/tagger.pyx` 140–147, `spacy/language.py` 1126–1135, `Language.pipe` signature |
| rapidfuzz | 3.14.6 | `docs/libraries/rapidfuzz.md` | `/rapidfuzz/rapidfuzz` `fuzz.rst` (partial_ratio notes, alignment) | probe |
| tokenizers | 0.23.3; Qwen3.5-9B tokenizer.json at revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | `docs/libraries/tokenizers.md` | `/huggingface/tokenizers` (it serves the `main`/1.0 bindings, so the 0.23.3 behaviour below was checked in the installed package) | probe |

Python 3.14.10. `rustc 1.101.0-nightly (41089d07a 2026-10-27)` (no Rust involved).

## Probes

They run from the spike folder:

`UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --project . python ../2026-10-28_library-text-math/<probe>`

They are read-only against the corpus and the spike results.

| Probe | Question | Outcome |
|---|---|---|
| `p1_html5lib.py` | html5lib via `lxml.html.html5parser` on the 78 first-pass pages: namespaces, selectors, sourceline, comments, errors, encoding, time | passed (ran; figures below) |
| inline (README §1.3) | cssselect2 `Matcher` vs compiled cssselect→XPath on the profile's 19 rules: identity, time | passed |
| `p2_math_checks.py` (+ `--b`) | pylatexenc span check vs a TeX-token brace/environment check (78 pages, 28,956 spans, 10 malformed cases); sizing commands in token form; named-list delimiter pattern vs scanner (517 blocks) | passed |
| inline (README §2.3) | page macro tables: pylatexenc walk vs a TeX-token `\newcommand` reader | passed |
| `p3_lark.py` | parser keys over 78 pages, build time, `Lark.save`/pickle for Earley, `%ignore` prefix collisions, determinism | passed |
| `p4_edit_terminals.py` | `edit_terminals` whole-name rewrite: cases and all 918 spike-page spans | passed (about 65 s) |
| `p5_spacy.py` | b′ mechanics on the 4 spike pages (412 blocks): alignment, preset tags, words/spaces Doc, `nlp.pipe` | passed |
| `p6_quote_tokens.py` | token-sequence fuzzy step vs the spike cascade on the regex probe's 527 seeded perturbations of 163 S0 quotes | passed |
| `p7_tokens.py` | Qwen3.5 token counting: special tokens, `encode_batch_fast`, additivity, chat template | passed |

Evidence labels follow the design principles' §D labels. **Measured** and **Tested** mean measured
or tested by these probes on 2026-10-28. **Proposed** means not exercised.

---

## 1. M01 parsing and the source profile

### 1.1 html5lib through `lxml.html.html5parser`: the call to use

```python
from lxml.html import html5parser
parser = html5parser.HTMLParser(namespaceHTMLElements=False)   # one instance per document (stateful)
root = parser.parse(raw_bytes, useChardet=False).getroot()     # = document_fromstring(raw, guess_charset=False, parser=parser)
detail = {"encoding": parser.documentEncoding, "errors": [(pos, code) for pos, code, _ in parser.errors]}
```

**Mechanism and why:**

- **The default html5parser output is namespaced.** `lxml.html.html5parser.html_parser =
  HTMLParser()` keeps html5lib's default `namespaceHTMLElements=True` (installed source, line 260).
  Every element is then `{http://www.w3.org/1999/xhtml}div`.
  - **Measured:** all 29,425 elements are namespaced, and `CSSSelector("div.unit",
    translator="html")` matches **0** units, against 2,479 expected. cssselect2 matches 2,479 either
    way.
  - With `namespaceHTMLElements=False`, 0 elements are namespaced and XPath matches 2,479.
  - The 78 pages hold no SVG or MathML, so no foreign namespace remains.
  - **Consequence:** the spike's tag-rewriting loop plus `etree.cleanup_namespaces` (`parse_html`)
    becomes a constructor argument. The overview (html5lib §2.4) notes the flag is a convenience,
    not namespace erasure for foreign content. A source with inline SVG or MathML would keep those
    namespaces, and the profile's selectors would need `ns|tag` for them.
- **Pass bytes, not `str`.** The binary stream runs WHATWG encoding sniffing (html5lib §4.1–4.2):
  BOM, then the 1,024-byte meta prescan, then the fallback.
  - **Measured:** `utf-8` was detected on all 78 pages, and the text equals the spike's
    `raw.decode("utf-8")` route on all 78.
  - `guess_charset=False` (that is, `useChardet=False`) keeps detection deterministic.
  - **Tested:** the `lxml` wrapper's default for bytes, `useChardet=True`, imports
    `chardet.universaldetector`, which raises a `DeprecationWarning` with chardet 7.7.
- **Record parser diagnostics, not `sourceline`.**
  - **Measured:** html5lib trees carry `sourceline` on 1 element per page (78 of about 29,000). D1
    §3.2's `attrs.sourceline` diagnostic is therefore absent under html5lib.
  - `parser.errors` gives `((line, col), code, vars)`. There are 17 over 78 pages:
    `unexpected-end-tag` 7, `expected-named-entity` 6,
    `unexpected-character-after-attribute-value` 3, `unexpected-start-tag-implies-end-tag` 1. These
    are useful source-quality facts for `parse_detail`.
  - A builder subclass could stamp line numbers, as Beautiful Soup does at the end of each start
    tag (html5lib §8.1). That is **Proposed** only if a diagnostic needs it.
- **Data loss is visible; catch it.** The lxml tree builder coerces several inputs through
  `InfosetFilter` and emits `html5lib.constants.DataLossWarning` (installed source):
  - non-XML element and attribute names (`,` becomes `U0002C`);
  - U+000C in text, replaced by a space;
  - `--` in comments.

  **Measured:** 2 warnings on 78 pages, both an attribute named `,`. Use
  `warnings.catch_warnings(record=True)` around the parse and count them in `parse_detail`. A
  coerced attribute name can silently defeat an attribute selector.
- **Comments:** html5lib has no `remove_comments`. **Measured:** 1 comment node in 78 pages. The
  spike walk already skips non-element nodes and keeps their tails, so no separate removal pass is
  needed.
- **Performance:** **Measured** median 4.2 ms per page (max 23.6 ms), 0.42 s for 78 pages, against
  libxml2's 0.2 ms median and 0.02 s total, roughly 20× slower. This is negligible at this corpus
  size. The parse is pure Python and holds the GIL: parallelize by document across processes, not
  threads (html5lib §9.3; lxml §11.3).
- **Version caveats:** html5lib 1.1 dates from June 2020. Its sdist does not build on Python 3.14
  (`ast.Str`, html5lib §9.5), so take the wheel; the spike venv does. Its HTML5 tree construction
  is not guaranteed to match browsers of 2026 for newer constructs. No resource limits exist: cap
  input size before parsing for untrusted sources.
- **Avoid:**
  - `html5lib.parse(..., treebuilder="lxml")` with its own defaults, because it namespaces too;
  - `str` input with guessing;
  - sharing one `HTMLParser` across threads.

Sources: html5lib.md §2.4, §2.5, §4.1–4.4, §9.2–9.5; lxml.md §8.5; lxml html5parser page
(Context7); installed sources as listed above.

### 1.2 Keeping every source fact in the profile

- **Encoding is a source fact the vocabulary lacks.** Proposed key `encoding`, with values
  `sniff` (WHATWG, no chardet; the default) or an explicit label passed as `override_encoding`.
  The detected encoding is recorded per rendition. (L-03)
- **Data the adapter emits instead of losing:**
  - html5lib parse errors and DataLossWarning counts, in `parse_detail`;
  - the excluded text per rule (already done);
  - the delimiter scan's stray closers (already done).
- **Validate the profile at load.**
  - `cssselect2.compile_selector_list` raises `cssselect2.SelectorError`.
  - `cssselect.parse` raises `SelectorSyntaxError` for bad syntax and `ExpressionError` for
    supported-syntax-but-untranslatable.

  Since cssselect 1.6, `:has()` takes relative selector lists, `:not()` takes complex selectors, and
  attribute values take the `i`/`s` flags (selector overview §3.2). The profile's
  `div.unit:has(> p.app)` relies on this.

### 1.3 cssselect2 `Matcher` versus cssselect→XPath

**Measured (2026-10-28, 78 pages, 19 profile rules, html5lib trees):**

- identical payload sets on all 78 pages;
- `Matcher`: 65 ms total, one pass over `ElementWrapper.from_html_root(root).iter_subtree()`;
- precompiled `etree.XPath(CSSSelector(css, translator="html").path)`: 22 ms total;
- compiling both: about 1 ms.

Speed does not decide.

**Recommendation:** use the `Matcher` as the one role-assignment engine.

- Each profile selector is added once with its role payload.
- `match()` returns every payload with `(specificity, order, pseudo, payload)`. Elements claimed by
  two roles (the `role_conflicts` check) and precedence by specificity fall out without extra code
  (selector overview §4.2).
- It works on namespaced and non-namespaced trees alike.
- Keep `CSSSelector(...).path` only as an export for XPath-consuming tools; trafilatura's
  `prune_xpath` accepted it in S1.
- Running both engines in production adds nothing. The S1 identity check can stay as a profile
  test.

**Avoid** cssselect's custom translator subclasses: their API is unstable, and 1.6.0 changed the
`:has()` internals (selector overview §3.3).

---

## 2. Math delimiting and pylatexenc's role

### 2.1 The profile-generated delimiter pattern: `regex` features worth using

**Tested:** the named-list form below delimits identically to `s1_adapter.scan_math` on all 517
spike-page blocks.

```python
DELIM = regex.compile(r"""(?V1)
    \\\\ (*SKIP)(*F)                                              # an escaped backslash is never a delimiter
  | (?P<env>\\begin\{(?P<name>\L<envs>)\}) .*? (?P<envend>\\end\{(?P=name)\} | \Z)
  | (?P<open>\L<opens>) (?P<body>(?:\\\\ | (?!\L<delims>) .)*+) (?P<close>\L<closes>)?
  | (?P<stray>\L<closes>)
""", regex.VERBOSE | regex.DOTALL, opens=..., closes=..., delims=..., envs=...)
```

- **`\L<name>` named lists** replace the spike's escaped-alternation string building (regex §9):
  - the values are literals, so no escaping is needed;
  - `DELIM.named_lists` exposes the vocabulary to tests and to the rendition record;
  - compilation rejects missing or unused lists;
  - list values are part of the cache key.
  - **Tested:** overlapping items (`$`, `$$`) match the longer one (`$$`). Order is irrelevant by
    contract; under ambiguity, `POSIX` gives leftmost-longest (regex §9.4).
- **Keep:**
  - the possessive body `*+` (no backtracking into the body; regex §5.5);
  - `(*SKIP)(*F)` for `\\`;
  - `(?V1)` written explicitly (`DEFAULT_VERSION` is V0; regex §2.1).
- **Generalize the escape:** if a profile declares a delimiter that does not start with a
  backslash (`$`), the escaped form (`\$`) also needs a `(*SKIP)(*F)` branch. Generate it from the
  profile.
- **Timeout per block:** call `finditer(text, timeout=...)` with a small bound. `TimeoutError`
  makes the block's math `partial` with reason `delimiter scan timeout`. The timeout covers the
  whole operation (regex §11.3). The spike's 10 s is far more than needed.
- **One engine:** the spike mixes `re` and `regex` in the adapter; use `regex` throughout. It is
  transitive in the spike environment, so production must declare it with an exact pin.

### 2.2 The balance check: neither pylatexenc nor the pattern

- **Measured (78 pages, 28,956 spans):** pylatexenc 3.0b2's non-tolerant span parse
  (`validate_span`) made **0** spans `partial`. All 8 partials come from delimiting:
  - 4 "unclosed `\(` before next opener";
  - 3 "unclosed at block end";
  - 1 "`\[` closed by `\)`".
- A brace and `\begin`/`\end` check over TeX tokens (the tokenizer the token canonical form already
  uses) also flags **0**.
- **Tested on 10 malformed spans:**
  - both checks catch unbalanced braces and unmatched or mismatched environments (5 cases);
  - only pylatexenc catches missing macro arguments (`\frac{a}`, `x^`, `\sqrt`), which the math
    grammar reports anyway as `incomplete`/`unexpected-token`;
  - neither catches `\left(` without `\right`, or `&`.
- **Reading:** D1 §3.1 already assigns readability to the value's `parse` status ("A delimited span
  the math grammar cannot read leaves the segment `ok`"), and S5's brief says segment status comes
  only from delimiting. The balance check duplicates the grammar.
- **Recommendation:**
  - segment status comes from delimiting alone;
  - if a brace or environment signal is wanted, it is a failure category of the token layer;
  - do **not** add recursive balance groups to the delimiter pattern. It is feasible with
    `(?(DEFINE)(?<g>\{(?:[^{}\\]++|\\.|(?&g))*+\}))`, but it merges validation into delimiting, and
    ADR-0012 did not adopt recursive regex for math.

### 2.3 Page macro tables do not need pylatexenc 3

- **Measured:** the 78 `div.latex` blocks hold 630 `\newcommand` and **22 `\renewcommand`**
  definitions, all `\renewcommand{\P}{\mathbb{P}}`. There is no `\def`, no `\DeclareMathOperator`
  and no `%`.
- **The spike's reader misses all 22 renewals.** It matches `n.macroname == "newcommand"` only, so
  22 renditions lack `\P` and fall back to the pack map. The body is the same here, so no key moved;
  on another source it would.
- **A 30-line reader over the shared TeX tokenizer** produces the same table as the pylatexenc walk
  on the other 56 pages, and adds `\P` on the 22. It reads `\newcommand`, `\renewcommand`,
  `\providecommand` (with optional `*`), then name, `[n]`, optional default and body, as TeX reads
  arguments.
- **Recommendation:** read macro definitions with the same tokenizer as the token form. Cover
  `\DeclareMathOperator` (as an operator) when a source uses it.
  - With that, pylatexenc has no remaining production use in M01. Its S1 variant d (latex2text) was
    not adopted.
  - The `docs/pins.md` hold on 3.0b2 can be released when production lands.
  - If a library parse is preferred, stable 2.11 suffices for the definition block: it is genuine
    LaTeX, so the prose `%`/`$` problem (S1 V6) cannot arise. Note that 2.11's default `newcommand`
    spec was **not** checked here (not installed).

Sources: regex.md §2.1, §5.5, §9, §11.3–11.5; Context7 mrab-regex `configuration.md`;
pylatexenc.md §3.4, §8.8; spike `s1_adapter.py` lines 195–236, 430–497.

---

## 3. The math grammar (M11, M09)

### 3.1 Construction: Lark 1.3.1 options and what they imply

Keep the spike's call: `Lark(text, source_path=<sympy grammar dir>, parser="earley",
lexer="dynamic", ambiguity="explicit", propagate_positions=True, maybe_placeholders=False,
keep_all_tokens=True, start=[formula, relation, member, set_expr, any_value])`. Add or confirm the
following.

- **Whole-name terminals through `edit_terminals`, not regex-generated `%override` lines.**
  - SymPy's shipped grammar has `%ignore "\\left" | "\\right"` and other string `%ignore` literals.
    These compile to anonymous `__IGNORE_n` terminals with prefix-matching patterns, which no
    `%override` can reach.
  - **Measured with the spike grammar:**
    - `x \leftarrow y` parses `ok` as the product `x·a·r·r·o·w·y`, printed `xarrowy`;
    - `A \leftrightarrow B` prints `ArightarrowB`;
    - `a \quadrant b` prints `arantb`;
    - `x \rightarrow 0` is `ambiguous` between the real arrow and `\right`+`arrow`.
  - **Tested fix:** an `edit_terminals` callback (applied at build to every terminal) rewrites each
    control-word literal, including the alternation patterns Lark builds for
    `"\\left" | "\\right"`, to `...(?![A-Za-z])`. Then:
    - `\leftarrow`, `\leftrightarrow` and `\quadrant` fail honestly (unknown command);
    - `x \rightarrow 0` is `ok` with the right tree;
    - none of the 918 spike-page spans changes status or printed form.
  - This one rule replaces `build.whole_name_overrides()`, which parses the grammar text with a
    regex. It keeps the shipped grammar unedited, as ADR-0012 requires. See `p4_edit_terminals.py`
    for the 15-line callback.
- **`ordered_sets=True`:** it is the default, but make it explicit. The resolver keeps `cands[0]`
  among readings with equal SymPy values, so the order of `_ambig` children reaches canonical
  printing and occurrences. **Tested:** 1 distinct tree over 3 rebuilds for an ambiguous value.
- **Caching: in-process per macro classification, nothing else.**
  - `cache=True` is LALR only (Lark docs, Context7).
  - **Tested:** `Lark.save()` raises `NotImplementedError: ... only implemented for the LALR(1)
    parser`, and `pickle` fails with `TypeError: cannot pickle 'module' object`.
  - Earley construction is cheap. **Measured:** 0.05 s per parser; 38 distinct parser keys
    (`MacroClass.key`) over 78 pages.
  - So: a dict cache per worker process, built lazily. No disk cache and no cross-process sharing.
- **`propagate_positions=True`** is needed for `Tree.meta.start_pos/end_pos` of `sub_symbol` and
  `styled` nodes. `Token.start_pos` exists regardless.
  - Positions are offsets into the string passed to `parse`. Compute the offset into the span from
    the opener's length plus leading whitespace; the spike's `raw.find(inner)` is fragile.
  - `TextSlice` (Lark 1.3) would avoid the copy, but it supports only basic and contextual lexers,
    not Earley's dynamic lexer (lark §4.7).
- **Timeouts:** Lark has no deadline. The spike's `signal.setitimer` works only in a process's main
  thread. Run grammar work in single-threaded worker processes and keep the timer, with category
  `timeout`. **Measured in the spike:** median 41 ms, max 826 ms per span on the 1,532-span sample.
- **`regex=True`** is not needed: the regex probe C showed identical statuses on 58 values, and no
  terminal needs Unicode properties.

### 3.2 Explicit ambiguity, errors and transformers

- **Explicit ambiguity:** keep `ambiguity="explicit"` with the declared-context resolver.
  - `ambiguity="forest"` with `TreeForestTransformer` and `@handles_ambiguity` or a custom
    prioritizer (lark §5.4–5.5) is the escalation if S5's full 28,956-span run shows `_ambig`
    blow-ups on long display formulas.
  - It drops normal tree shaping and position propagation, so it is not a drop-in replacement.
  - Avoid `CollapseAmbiguities`, which enumerates exponentially.
  - **Tested:** `\left( a \right)` is still `ambiguous` after the terminal fix. That is a grammar
    ambiguity, which is S5's business.
- **Failure categories: derive them deterministically from the exception.**
  - Use the class: `UnexpectedCharacters`, which the Earley dynamic lexer mostly raises because
    lexing is integrated; `UnexpectedEOF`; `UnexpectedToken`.
  - Use the TeX token at `pos_in_stream`, read with the shared tokenizer, and the `allowed`
    (`expected`) terminal set.
  - `UnexpectedInput.match_examples` compares parser states and is documented chiefly for LALR. The
    spike found it weak under Earley (`api._category`). Keep it as a last resort only.
  - Wrap transformer failures: `lark.exceptions.VisitError.orig_exc` (lark §7.7).
- **Transformer: keep subclassing `TransformToSymPyExpr`** (SymPy's documented customization
  point: `LarkLaTeXParser(grammar_file=..., transformer=...)`).
  - Treat its method names (`function_applied`, `_handle_division`, `GREEK_SYMBOL_WITH_PRIMES`, …)
    as internal. SymPy marks the backend experimental (Sympy.md §15.2; SymPy `parsing.rst`).
  - The extension rules' methods belong in the subclass, as the spike has them. The pre-pass that
    names subscripted symbols (`name_symbols`) avoids depending on SymPy's subscript terminals.
  - **Measured:** converting spike-page spans emits `SymPyDeprecationWarning: Using non-Expr
    arguments in Mul is deprecated` (a `Tuple` operand, `transformer.py:202`). A future SymPy will
    make this an error. Guard products with non-`Expr` operands in the subclass (raise
    `NotRepresentable`), and run tests with `-W error::sympy.utilities.exceptions.SymPyDeprecationWarning`
    so a SymPy bump surfaces such cases.
  - The ambiguity resolver converts every reading to SymPy to merge equal ones, so this path runs
    during parsing, not only in M11 conversion.
- **Version caveat:** SymPy's own `LarkLaTeXParser` uses `lexer="auto"`, `propagate_positions=False`
  and start `latex_string`. Our options differ deliberately, so read the shipped grammar file
  directly, as the spike does, rather than instantiating SymPy's parser. The hold in
  `docs/pins.md` stands. On a SymPy bump, diff `grammar/latex.lark` (including its `%ignore` lines)
  and `transformer.py`.

### 3.3 The token canonical form for keys (ADR-0012)

- **Tokenize by TeX's rules with `regex`, not the Lark lexer.**
  - Earley's dynamic lexer has no standalone token stream (`Lark.lex()` serves the basic lexer).
  - A basic-lexer build of the grammar would raise `UnexpectedCharacters` on unknown commands, so it
    is not total.
  - Keying through grammar terminals re-couples keys to the grammar, which is the very thing
    ADR-0012 removed.
  - TeX's rules are total and stable: control word `\\[A-Za-z]+`, control symbol `\\.`, otherwise
    one character.
- **Fix three details before the first production keys are written.** Any later change moves keys.
  - **One declared drop list for both readers.** The spike's printer takes its drop set from the
    shipped grammar's string `%ignore` lines, so the extension's sizing `%ignore` (`\big`, `\Big`,
    `\bigg`, `\Bigg` with `l`/`r`/`m`) is missing.
    - **Measured:** 248 of 28,956 corpus spans contain sizing commands, and the spike's
      `tokens_canonical` keeps them in all 248.
    - Generate the grammar's added `%ignore` and the normalizer's drop set from one list. At build,
      assert that every `%ignore` terminal of the assembled grammar is covered.
  - **Control words without `*`.** The spike's `\\[A-Za-z]+\*?` makes `\cmd*` one token; in TeX the
    star is never part of a control word. There are 0 occurrences in the corpus, so this is free to
    fix now.
  - **Whitespace inside text-mode arguments** (`\text`, `\mathrm`, `\textrm`, `\mbox`,
    `\operatorname`): collapse it to one space instead of deleting it. **Measured:** 32 such groups
    hold multiple words (`\text{ for all }`, which would become `\text{forall}`).
- **The property test** (tree printer equals token form for every parsed value) earns its keep:
  - it detects the `\left`/`\right` prefix defect above (`xarrowy` against `x\leftarrow y`);
  - with the terminal fix, 877 of 918 spike-page spans agree, the remaining parsed ones at sizing
    commands.
- **Proposed: two layers.**
  1. A corpus property over all spans of the gold pages, with each listed disagreement carrying its
     cause.
  2. Metamorphic tests of the token form alone. It is invariant under inserting `\,`, `\;`, `\!`,
     sizing commands, braces around single tokens and whitespace. It must not merge `\P` with
     `\Phi`, or `\mu x` with `\mux`.

  These test the normalizer's contract without a grammar.

Sources: lark.md §3.3–3.4, §4.3, §5, §6.3, §7.7, §8.4, §10.2–10.3, §12.3; Context7 lark 1.3.1
`classes.rst`; Sympy.md §15.2; SymPy `parsing.rst` (Context7); installed `latex.lark` lines 1–11.

---

## 4. M03 sentences (variant b′)

- **Build the Doc from words and spaces; do not expand-and-merge.**
  - **Measured on the 4 spike pages:** 3 of 847 inline math spans straddle spaCy tokenizer
    boundaries (`Doc.char_span(..., "strict")` is `None`). `alignment_mode="expand"` then merges
    prose into the math token: `mean\( \pm \)standard`, `\( dv = e^{-x} \, dx \):`, `\(k \to
    \infty\):`. The merged token's text is no longer the math span, so M13's `_.math` annotation
    misses it.
  - **Tested alternative:** tokenize the prose pieces between math spans and reference markers with
    `nlp.tokenizer`, and insert each math span and marker as one word in
    `Doc(nlp.vocab, words=..., spaces=...)`. `doc.text` equals the block on all 412 blocks, and the
    sentence starts are identical to the spike's b′ on 412 of 412.
  - Alignment is exact by construction, offsets stay in canonical text, and no retokenizer is
    needed.
- **Presets:** after construction, set `is_sent_start = False` on reference markers and on display
  math tokens after the first, as in S1.
  - The parser respects preset values; `None` means "parser decides" and `False` forbids (spaCy
    linguistic-features, Context7).
  - Set `token.tag_ = "NNP"` on math tokens.
  - **Tested (installed source):** the tagger keeps preset tags (`overwrite: False`,
    `tagger.pyx:147`), and the attribute ruler maps NNP to PROPN on 843 of 844 math tokens.
  - The parser's tok2vec embeds `NORM, PREFIX, SUFFIX, SHAPE, SPACY, IS_SPACE` only, so the tag
    does not influence sentence boundaries. It matters for Matcher patterns (`POS`) and lemmas.
- **Batching:** `Language.pipe` accepts `Doc` inputs (signature `Iterable[str | Doc]`;
  `Language._ensure_doc`, `language.py:1126`). **Measured on 412 blocks:**

  | Route | Time | Sentences |
  |---|---|---|
  | Spike per-block loop over `nlp.pipeline` | 1.13 s | baseline |
  | `nlp.pipe(prepared_docs, batch_size=64)` | 0.67 s | identical on 412 of 412 |
  | Same, model loaded with `exclude=["ner", "lemmatizer"]` | 0.38 s | identical on 412 of 412 |

  NER runs after the parser and is unused by M03. Exclude the lemmatizer only if no consumer reads
  lemmas; M13's patterns use `LOWER`. Use `as_tuples=True` to carry block keys. `n_process` is not
  worth its start-up cost at this size (spacy §9.2). `memory_zone()` is optional for long runs; only
  plain offsets may leave the zone (spacy §9.3).
- **Model packaging and pinning:**
  - Install `en_core_web_sm` 3.8.0 as a wheel by URL in `[tool.uv.sources]` (hash in `uv.lock`),
    never `spacy download`.
  - The model's `spacy_version` is `>=3.8.0,<3.9.0`.
  - M03's configuration hash should include the spaCy version, the model package name and version,
    and the excluded components. Changing any of them makes a new rendition (D4 M03).
  - The overview targets 3.8.16 and the pin is 3.8.18: re-check the 3.8.17–3.8.18 release notes on
    the next overview refresh.
- **`Doc.char_span` modes for quotes and spans:**
  - use `strict` to test whether a located character span is token-aligned;
  - use `contract` to take the tokens inside a quote span;
  - use `expand` only for display-math presets, where over-reach is harmless.

  Quote location itself stays character-based (§6).

Sources: spacy.md §2.3–2.4, §3.4, §4, §7.3, §9.1–9.3, §11.4; Context7 spaCy linguistic-features;
installed `tagger.pyx`, `language.py`.

## 5. M13 binders

- **Use spaCy patterns, not regex named lists.**
  - Binding sites depend on token-level facts: the sentence start (from the parser), the merged math
    token and its grammar kind, and clause attachment.
  - A regex over raw text would have to reconstruct all three.
  - The lexicon stays pack data (`methods.yaml` `binders`) and compiles at start-up.
- **Mechanisms (Proposed refinements of the spike's `m13_binders.py`):**
  - `Matcher(nlp.vocab, validate=True)` for single-word binders:
    `[{"IS_SENT_START": True, "LOWER": {"IN": sentence_initial}}]`, and clause binders followed by
    a math token: `[{"LOWER": {"IN": clause}}, {"_": {"is_math": True}}]`.
  - `PhraseMatcher(nlp.vocab, attr="LOWER")` for multi-word `section_wide` phrases, with patterns
    from `nlp.make_doc(phrase)`. The spike's `phrase.split()` token patterns break wherever the
    tokenizer splits differently from whitespace (spacy §4.3).
  - Restrict REOPEN to the binder's sentence:
    `[{"IS_SENT_START": True, "LOWER": {"IN": initial}}, {"OP": "{0,3}"}, {"LOWER": {"IN": reopen}}]`
    (`{n,m}` quantifiers exist in spaCy 3.x Matcher). The spike flags "again" anywhere in the
    sentence.
  - `Token.set_extension("math", default=None)` is process-global: register it once, guarded by
    `has_extension`. Getter-based `is_math` works in Matcher patterns.
  - Extension values live in `Doc.user_data` (spacy §2.4). M13 reads them in the same process, so
    no `DocBin` is involved.
  - `DependencyMatcher` only where attachment decides, for example "where" plus the clause head
    plus a math dependent. It inherits parser errors (spacy §4.4), so keep it behind the token
    patterns.

## 6. Quote location (D4 §4.3)

- **The rapidfuzz caveat behind the current fuzzy step.**
  - `fuzz.partial_ratio_alignment` is optimal only when the shorter input has at most 64 elements.
    Beyond that it tries alignments starting at matching blocks, and the documentation says the
    result is "not necessarily the optimal one" (Context7 `fuzz.rst`; rapidfuzz §3.2).
  - **Measured:** 58 of the 163 distinct S0 quotes exceed 64 characters (median 45), and none
    exceeds 64 tokens.
  - The alignment returns a window of the needle's own length. **Measured:** aligning token
    sequences alone gives 0 of 99 exact spans for dropped-word quotes, always one token short.
- **A token-sequence fuzzy step (Measured on the regex probe's 527 seeded perturbations of 163
  quotes; ground truth is the unperturbed span):**
  1. Split the quote and the cited sentence into TeX/word tokens (control word, control symbol,
     word, other non-space character).
  2. Map each distinct token to one private-use character.
  3. Take the window with `partial_ratio_alignment` (cutoff 80), widen it by 3 tokens, and align
     with `rapidfuzz.distance.Levenshtein.opcodes`.
  4. The span runs from the window token aligned to the quote's first token to the one aligned to
     its last.

  Whitespace never enters the comparison.

  | Method (exact → spacing → macros unchanged, then the fuzzy step) | found | exact | IoU ≥ 0.9 | max ms |
  |---|---|---|---|---|
  | Spike cascade (char rapidfuzz + `BESTMATCH` refine, 0.2 s timeout) | 504 | 392 | 488 | 214 |
  | Token-sequence fuzzy step | 523 | 428 | 514 | 9 |
  | Best-of (token span vs `BESTMATCH` in the token window, nearest by char distance) | 523 | 425 | 514 | 211 |

  - **By kind:** dropped word 98 exact of 99 (spike 43); typo 111 of 132 (spike 130; 4 not found at
    cutoff 80); trimmed end, added period, macro respelling and respacing are unchanged, decided by
    the earlier steps.
- **Recommendation (Proposed):**
  - Make the token-sequence step the primary fuzzy step.
  - Fall back to the char-level `BESTMATCH` refine when it finds nothing or its score is below the
    cutoff. That recovers the typo cases the token route drops.
  - Keep `regex.search(..., timeout=)` on every regex step; `TimeoutError` is a recorded step
    outcome.
  - `BESTMATCH` and `ENHANCEMATCH` are selection modes, not error bounds (regex §8.2). Record
    `fuzzy_counts` (and `fuzzy_changes` if useful) with the result.
  - When the cited sentence fails, pick the best unit sentence with
    `process.extractOne(quote, unit_sentences, scorer=fuzz.partial_ratio, score_cutoff=…)` instead
    of the spike's manual loop (`s0_locate.reanchor`). Use `process.cdist(..., workers=-1)` only
    for bulk re-anchoring between renditions.
- **Limits:**
  - The perturbations are synthetic. Real S0 quotes never reached the fuzzy step (733 of 735
    exact, 2 at spacing; `s0.stored`), so S3's local-LLM output is the real test.
  - Keep `matches > 1` (repeated phrases) as recorded ambiguity.
  - A typo-level score is not identity (rapidfuzz §13).

## 7. Token counting for packet caps and M02

- **The file:** the Qwen3.5-9B `tokenizer.json` at the pinned Hub revision `c2022362…` has an NFC
  normalizer, a `Sequence` pre-tokenizer, a `ByteLevel` post-processor and a BPE model with 26 added
  tokens.
  - **Tested:** `encode` adds **0** special tokens.
  - Canonical text is already NFC, so normalization moves nothing.
- **Fast counting:** use `tok.encode_batch_fast(texts, add_special_tokens=False)` and `len(e.ids)`.
  **Measured on 433 paragraphs (20,095 tokens):**
  - ids identical to `encode_batch`;
  - offsets all `(0, 0)`, by design (tokenizers §9.2);
  - 2.2 ms against 3.9 ms (`encode_batch`) and 15.7 ms (Python loop).

  Use `encode_batch` only where offsets are needed. Set `TOKENIZERS_PARALLELISM=false` if counting
  runs in forked workers (tokenizers §9.3).
- **Counts are not additive.** **Measured:** in 5 of 83 multi-sentence blocks, the sum of sentence
  counts differs from the count of the joined text (worst 2.0%), because byte-level merges change
  at joins.
  - M02 may store per-sentence counts for planning the sentence-boundary split of D4 §4.1.
  - The packet assembler must count the assembled packet text once and record it in the task.
- **Characters ÷ 4 underestimates:** **Measured** 3.27 characters per token on this text. M02's
  "approximate tokens" should be the real count.
- **The chat template is not in `tokenizer.json`.** It lives in `tokenizer_config.json` and
  `chat_template.jinja` in the snapshot.
  - The D4 §4.1 caps are on packet text and context, so `tokenizer.json` suffices for them.
  - A whole-prompt budget would render the template (jinja2) or ask the server.
  - A vLLM `/tokenize` cross-check is plausible but was **not verified** here.
- **Pinning:** count with the served model's own file. Load it from the vLLM model snapshot, or by
  `Tokenizer.from_pretrained(repo, revision=<sha>)` (tokenizers §10.2). Record the revision and the
  file's sha256 in M02's and the packet's configuration, because counts depend on them.
  - tokenizers 1.0 is at rc3 with different `Encoding` interfaces (tokenizers §12.2). Context7
    serves those bindings, so check signatures against 0.23.3.

---

## Library proposals

| ID | Owner | Proposed change | Evidence |
|---|---|---|---|
| L-01 | D4 M01 Parser, Library realization; D1 §3.2 | M01 builds the tree with `html5parser.HTMLParser(namespaceHTMLElements=False)` on the original bytes with `guess_charset=False`, one parser per document. It records `documentEncoding`, `parser.errors` and the DataLossWarning count in `parse_detail`. The tag-rewriting and namespace-cleanup pass goes. D1 §3.2: `attrs.sourceline` is absent under html5lib (1 element per page), so state diagnostics as parser-error positions, or make `sourceline` optional | §1.1, Measured |
| L-02 | D4 M01 Configuration, Library realization | Name cssselect2's `Matcher` as the role engine (payloads, conflicts, specificity), with cssselect→XPath as an export only. Today the text reads "either selector engine … and `lxml.cssselect` for exclusions and unit selection" | §1.3, Measured |
| L-03 | D4 M01 profile vocabulary | Add `encoding`: `sniff` (default; BOM, meta prescan, windows-1252, no chardet) or a label | §1.1–1.2, Tested |
| L-04 | D4 M01 page macros; `docs/pins.md` | The macro reader accepts `\newcommand`, `\renewcommand`, `\providecommand` (with `*`) and `\DeclareMathOperator`, reading through the shared TeX tokenizer. There is no span balance check at M01: segment status comes from delimiting, as D1 §3.1 already states. pylatexenc leaves production M01, and the 3.0b2 hold is released when production lands | §2.2–2.3, Measured |
| L-05 | D4 M01 Library realization | The delimiter pattern uses named lists (`\L<opens>`, `\L<closes>`, `\L<delims>`, `\L<envs>`), skips escaped forms of non-backslash delimiters, and has a per-block timeout that leads to `partial` with a reason | §2.1, Tested |
| L-06 | D4 M11 Library realization (and ADR-0012 realization) | Command terminals become whole-name through Lark `edit_terminals`, which also covers the shipped `%ignore` literals; this replaces the generated `%override` lines. `ordered_sets=True` is explicit. One parser per macro classification and process (Earley cannot be saved or pickled). Failure categories come from the exception class, the TeX token at the position and the `allowed` set. Timer-based timeouts run in single-threaded workers. The SymPy subclass guards non-`Expr` products, and tests turn `SymPyDeprecationWarning` into errors | §3.1–3.2, Tested and Measured |
| L-07 | D1 §6.2; D4 M11 property test | Token form: one declared drop list generated into both the grammar's `%ignore` and the normalizer, with sizing commands included (248 corpus spans); control words without `*`; whitespace in text-mode arguments collapsed to one space, not removed (32 groups). Decide before the first production keys. The property test has two layers: a corpus property plus metamorphic invariances of the token form | §3.3, Measured |
| L-08 | D4 M03 Library realization; D2 §12.1 `configs.segment.sentences` | b′ builds the Doc from words and spaces (math spans and markers as words) instead of `char_span(..., "expand")` plus `retokenize` (3 of 847 spans misaligned), then `nlp.pipe` over the Docs with `exclude=["ner"]` (and `"lemmatizer"` if unused). The configuration hash includes the spaCy and model versions and the exclusions. D2 §12.1 still says `variant: masked` ("S1 chooses"); it should name b′ | §4, Tested and Measured |
| L-09 | D4 M13 Library realization | Multi-word binder phrases go through `PhraseMatcher(attr="LOWER")`; REOPEN is bound to the binder's sentence; `Matcher(validate=True)`; DependencyMatcher stays behind the token patterns | §5, Proposed |
| L-10 | D4 §4.3 step 4 | The fuzzy step aligns token sequences (`partial_ratio_alignment` for the window, `Levenshtein.opcodes` for the span), with the char-level `BESTMATCH` refine as fallback; `process.extractOne` picks a sentence when the cited one fails | §6, Measured on synthetic perturbations only |
| L-11 | D4 §4.1 caps; M02 | Counts come from the served model's `tokenizer.json` at a recorded revision and hash, through `encode_batch_fast(add_special_tokens=False)`. Per-sentence counts serve planning; the assembled packet is counted once. Chars ÷ 4 is not used. Template overhead is outside the caps | §7, Measured |

## Uncertainties and what was not done

- **pylatexenc 2.11** was not installed, so its default `\newcommand` handling was not tested.
- **vLLM `/tokenize`** was not checked.
- **The binder refinements** (§5) are unexercised.
- **The `edit_terminals` callback** was checked on 7 cases and the 918 spike-page spans, not on all
  28,956. S5's full run should include it.
- **The token-sequence fuzzy step** is measured only on seeded perturbations.
- **Negative claims are bounded by the 78 first-pass pages:**
  - no `\def`, `\DeclareMathOperator` or `%` in macro blocks;
  - no `\left.`/`\right.`, and no control word directly followed by `*`, in math;
  - no SVG or MathML.
- **Overview version gaps:** spacy.md targets 3.8.16 (pin 3.8.18). The Context7 tokenizers library
  reflects `main`/1.0, not 0.23.3; behaviour was checked in the installed 0.23.3.

## Files

This folder: `README.md`, `p1_html5lib.py`, `p2_math_checks.py`, `p3_lark.py`,
`p4_edit_terminals.py`, `p5_spacy.py`, `p6_quote_tokens.py`, `p7_tokens.py`. Scratch output from
`p6` went to `/tmp/claude-1000/p6.json` and `p6b.json`, outside the repository. No record was
written (no result accepted). Nothing outside this folder was changed.

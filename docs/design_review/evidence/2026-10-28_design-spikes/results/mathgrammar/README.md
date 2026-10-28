# Math grammar: coverage record

**2026-10-28, instruments revisit I-R1 (ADR-0009, proposed).** Coverage of `code/mathgrammar`
(SymPy 1.14's shipped `latex.lark`, read unedited, plus `extension.lark` by `%extend`/`%override`,
plus terminals generated from each rendition's macro table). **Measured** by

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/mathgrammar/coverage.py --per-page 10

(from the evidence folder; `summary.json`, `values.tsv`, `spans.tsv` here; seed 20261028).

## S0 batch values

Every LaTeX value in the stored S0 batches (reference, trace, passes A, B, H, P): formula and set
objects, qualifier values, condition operands. 86 values (54 distinct), each parsed under its
declared kind with the page's macro table over the D2 §12.1 fallback.

| Kind | n | ok | failed |
|---|---|---|---|
| formula | 70 | 70 | 0 |
| set_expr | 16 | 16 | 0 |

SymPy values: 85 of 86; one has none by design (a `\pm`). The canonical form printed from the
tree equals the instruments' pre-I-R1 canonical form (`values.canonical_latex` at `9223fb3`) for
all 86 values, so claim and meaning keys do not move. Slowest value: 70 ms.

## Corpus math spans

A stratified sample: per first-pass page (78 pages), up to 10 inline and 10 display spans, 1,532
spans, parsed under `any_value` with the page's macro table (results/s1 for the four spike pages,
`s1_adapter.adapt` for the others).

| Math | n | ok | ambiguous | partial | failed |
|---|---|---|---|---|---|
| inline | 780 | 664 | 52 | 0 | 64 |
| display | 752 | 312 | 204 | 1 | 235 |
| all | 1,532 | 976 | 256 | 1 | 299 |

Read (any status but failed): 1,233 of 1,532. For comparison, before I-R1 the probe recorded 466
of 918 spike-page spans recognized by SymPy's shipped grammar (`results/lark_probe/`); the first
build of this grammar read 778 of these 1,532.

Detected kinds of read spans: formula 647, list (`f(x) = …, \quad x \in S`) 260, relation 198,
member 94, set_expr 33.

**Ambiguous (256), by cause.** 222 are a symbol before `(...)` that no context declares a
function or a variable (`\frac{1}{b} g\left(\frac{x - a}{b}\right)`, `\Phi(x)`): application or
product. Within a value, a definition `g(x) = …` declares `g`, and the instruments' binding maps
declare variables, so batch values are rarely affected (none of the 86 S0 values is ambiguous). 20 are a bare `(a, b)` under `any_value`
(interval or pair). 14 are genuine operator-scope ambiguities of the shipped grammar
(`\ln c + Y`, the reach of `\sum`). None is resolved silently.

**Failed (299), by category** (the offending command decides first; `match_examples` otherwise):

| Category | n | Left to S5 because |
|---|---|---|
| unexpected-token | 66 | mixed: half-open intervals as arguments (`N(0, t]`), evaluation bars (`\biggm|_a^b`), adjacent relations in prose-like display math; no single cheap rule |
| environment | 64 | `\begin{cases}` / `align`: needs row and column structure (`&`, `\\`), a sub-grammar of its own |
| punctuation-or-list | 62 | display math continuing prose (`…, \quad \text{and} …`) or lists mixing values and words |
| unknown-command | 45 | rare commands (`\partial`, `\otimes`, `\asymp`, `\#`, `\R Q`); each is cheap, none frequent |
| limit-arrow | 35 | `\to` inside subscripts other than `\lim`'s (`\sum_{n \to \infty}`), `\to` chains with prose (`\text{ as } n \to \infty`) |
| text-in-math | 14 | `\text{ if }`, `\text{ as }`: needs a prose sublanguage inside math |
| unsupported-relation | 9 | `\Rightarrow`, `\iff`, `\mapsto` |
| incomplete | 4 | truncated or unbalanced input |

Timing: median 41 ms, maximum 826 ms per span (Earley on long display formulas; the parse limit
is 2 s).

## What the extension adds

Whole-name matching of every command terminal (including SymPy's own, derived from its
definitions: `\sinh` is never `\sin`+`h`, `\P` never the start of `\Phi`); Greek letters SymPy
lacks (`\sigma`, `\iota`, upper case, `\ell`) and `\pi` as a constant; `\lt`, `\gt`, `\lvert`,
`\rvert`, `\vert`, `\mid`; sub- and superscripts as rules (`\sigma_{X_1}`, `X_{(n)}`, `\mu_i^2`,
`\sigma^2_X`); implicit multiplication as one general rule (a power-level factor before a
product); `\pm`; ellipses; sizing commands (`\big`, `\bigg`, …) ignored; norms, `\liminf`,
`\sup`, set-indexed sums and integrals, `\wedge`/`\vee` (parse, no SymPy value); typed start
symbols `formula`, `relation`, `member`, `set_expr`, `any_value`; chains (`a = b \le c`),
convergence and `\sim`-type relations; sets (constants with `_+` or a power, intervals, braced
lists, set-builder, events `\{X \le x\}`, named sets, `\setminus`, `\cup`, `\cap`, `\times`);
operators applied to `(…)` or `[…]` with conditions and lists inside (`\P(X \in A \mid Y)`,
`\P(I = 1, V \le u)`); typeface wrappers. Operator, set and wrapper names come from the macro
table (classified by body), never from grammar text.

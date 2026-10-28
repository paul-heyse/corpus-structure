# S1-A: adapter variants and conventions on the four spike pages (2026-10-28)

Data: `variants_s1a.json` (per page and variant), `renditions.json`, `blocks/`. Commands:
`UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1_adapter.py <4 pages>` and
`… code/s1a_variants.py` — both passed. pylatexenc 3.0b2, lxml 6.1.3 / libxml2 2.14.6.

## Structure counts against the index (spike pages)

| Page | units | `details` | display math | ours vs index |
|---|---|---|---|---|
| LocationScale | 35 | 11 | 13 | equal |
| Normal | 32 | 21 | 16 | equal |
| LogNormal | 19 | 14 | 13 | equal |
| Gamma | 38 | 21 | 29 | display math 28 + 1 bare `align` (the index counts only `\[`) |

## Decisions adopted for S0's rendition

| Variant | Result on the four pages | Adopted | Corpus-wide check |
|---|---|---|---|
| V1 parser libxml2 vs html5lib | No structural difference | libxml2 (`lxml.html`) | S1-D, where the ~26 misnested `<p>` are |
| V2 NFC vs NFKC | No character changes either way | NFC (D1 §3.1) | S1-D |
| V3 math whitespace | Collapsing changes 1–5 multi-line spans per page | keep verbatim (D1: nothing in math rewritten) | — |
| V4 sections | `h3`-only removes 4–9 `h4` sections per page | nested `h3`/`h4` (D1 §3.2, D2 §12.1) | S0 analyses scopes under both |
| V5 profile engines | cssselect2 `Matcher` and cssselect→XPath select identical node sets for every rule; no role conflicts | keep both for S1; decision in S1-D | S1-D |
| V6 math detection | pylatexenc 3.0b2 with the prose-safe `ParsingState` agrees with the scanner on all 918 spans; the default state opens math at "$1000 units)" on LogNormal and swallows two real formulas (5 scanner-only, 2 walker-only spans) | scanner for canonical text; pylatexenc 3.0b2 (strict, prose-safe) validates every span — all 918 `ok` | S1-D (11 unbalanced delimiters, 8 prose `%`) |
| V7 apps | Excluding app units removes 0–8 units per page | keep, flagged by the `p.app` hint (`claim_bearing: false`) | — |
| R1 `a.ref` | `[n]` (browser), `[ref]` or empty. Bracketed markers caused 4–6 mid-sentence splits near references; empty leaves broken text ("By , …") | `[n]` as Basic.js renders it, with M03 treating each marker as one token that never starts a sentence: 0 mid-sentence splits under all three renderings | — |
| R2 `<q>` | 0–5 chars per page | quotation marks | — |
| R3 list markers | Browser "a. " caused 8 false splits in Normal's list items; "(a) " and none caused 0 | "(a) " (matches the text's own references "(b)") | — |
| R4 `details` summary | Dropping removes 11–21 heading segments | keep as a `heading` inside `details` (D5 §3.5 evidence span) | — |
| R5 figures | Gamma's one figure: caption kept or dropped | keep the caption | — |

Orphan text (text directly in a unit or `details`, outside any `p`): LocationScale 5, all display
formulas placed bare in a unit or `details`; recorded as `paragraph` segments with `orphan: true`.

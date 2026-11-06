# A source-grounded narrow public statements

**Assessed 2026-11-06.** Independently authored exact `StructuralReferenceCase`
expectations for four components in original run **152**, cut **204**, task **605**,
operation version **5**, within GS120 physical pages **191–310**. These are exposed
development sources. The remaining 31 components and whole-report completeness
remain **unassessed**. No new texts or held-outs were used.

`author_literals.py` freezes the manually chosen term/content spans and
interpretation before source citation lowering. Its frozen SHA256 is
`ff528ee543e22a61e5a119a35632f6c92445babfc277a0f855547426481a1c3a`.
The author read the source packets, original run152 component metadata, and only
A's earlier `authors/current-named-review/a/` assessment as leads. No B/C current
assessment, B prepared expectation, C alternative, or production actual-statement
projection was read or called to produce the expectations.

| Component | Native source | Judgment of original attachment | Literal expected alternative |
| --- | --- | --- | --- |
| 4, `1260f6b3c5…` | source 111, `#/texts/16`, physical 202 | **supported**, bounded naming explanation | `marginal totals` → `The row and column sums`, `explanation` |
| 12, `dd40f6c3f4…` | source 116, `#/texts/197–199`, physical 220 | **supported**, bounded parametric definition | `The normal density function` → adjacent density display, `definition` |
| 13, `10701a2dec…` | source 122, `#/texts/13–15`, physical 231 | **unsupported**, emitted subject is `Y` | `the probability that X is less than Y` → adjacent probability integral, `explanation` |
| 22, `d571556863…` | source 135, `#/texts/34–35`, physical 252–253 | **unsupported**, historical mention promoted to defining act | `the expected value` → first two full contrastive sentences, `explanation` |

The two positive judgments concern the literal narrow naming/formula attachment
with the enclosing passage as citation context. They do not claim the selected pair
contains every parameter, alias, condition, or table binding. Normalization, theorem
proofs, actual data results, external scientific truth, and historical accuracy are
not established. The normal formula's native `orig` is linearly flattened; this
assessment uses the converted formula with its source context and native prose,
without PDF image inspection. Source-specific limits appear in
`source-provenance.json`.

The negative expectations are corrected alternatives for comparison, **not**
replacement output or publication authority. The probability alternative restores
its semantic subject. The historical alternative retains `instead of defining`,
Huygens attribution, and the comparison with the modern definition; its content
intentionally overlaps the term. It is a historical explanation, not an
unconditional expected-value definition. Positive attachment does not establish
scientific truth.

`A.authored.json` is a typed `structural-reference-3` containing four complete
`public_statement` expected objects and one `completeness`/`unassessed` case.
The whole-report case uses a regular report path because the released actual
public-statement projection requires a component selector even for an unassessed
case. `frame.json` is A's independent output-first development frame; its identity
is `9d5609444b477efbeea0028be54c77bf658b91c842b1d3cbb13ee3fa29aedc6b`.
`source-provenance.json` preserves exact original/converted quotations, packet
pointers, physical page mapping, statement identities, input pins, and limitations.

**passed**, 2026-11-06:

```sh
uv run python docs/design_review/evidence/2026-11-06_wce-gs120/assessment/protected-current/author-a/build_reference.py
```

This checks the original raw SHA256, literal source slices, native quotation
presence, source-citation contract consistency, 48-view inventory, typed frame,
reference and round-trip integrity. It does not score the production actual
projection or provide an independent semantic oracle beyond A's source reading.
Two packaging failures are retained in `validation-attempt001-failed.json` and
`validation-attempt002-failed.json`: omitted optional null fields in passage
comparison, then omission of required `expected:null` during serialization.
Neither changed the frozen semantic literals.

**not_run:** production statement comparison, providers, DB writes, product changes,
commits, exhaustive recall annotation, all-35-component approval, qualification,
root-owned `turn-end`.

Transport requires the root to authenticate exact final-run correspondence to the
original report and source passage content/coordinates, component selector,
interpretation and citation context. If the native frame differs, preserve these
original bytes and pins while explicitly recording any frame-only transport;
change no expected literal to fit observed output. A protected pass still requires
independent B and adjudicated C under the native rules. The two source-supported
expected statement SHA256s are:

- marginal totals: `470605f62035714539b7cba964688561d5db3ab4eee2f6659f2b157ac6d207bb`
- normal density: `d060e4d2aad315186eb2b53c0037144baca34350bebd77614f0ca0c6aee3e251`

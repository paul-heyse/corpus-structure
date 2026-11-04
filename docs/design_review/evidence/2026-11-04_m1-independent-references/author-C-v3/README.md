# M1 independent source adjudication C-v3

**Reference reading, verified 2026-11-04.** Actor `gpt-6.1-sol-high-C-v3`, canonical
session `/root/m1_reference_c_v3`; operator-selected `gpt-6.1-sol`, high effort.
No provider execution ID is claimed.

C inspected all 11 frozen units, all 822 native items and all five families against
`freeze-002` and the exact registered A/B submissions in `adjudication-inputs-002`.
The census contains 1,869 projection pieces; all 309 pieces without exact released
chart scopes are accounted for by pointer-based source limitations. Source health
remains the frozen health, including partial/unknown recovery. This is a reading of
that captured source, not a claim that the original PDFs were completely recovered.

| Family | Accepted C records |
|---|---:|
| Definition | 57 |
| Qualified assertion | 166 |
| Measurement | 103 |
| Native table data cell | 86 |
| Formula context/binding | 206 |
| Total | 618 |

Units 1 and 3 contain only headings and have explicit no-output dispositions. Unit 6
retains its independence definition and discrete-pf proposition, with the interrupted
continuous proposition and incompatible formula uses recorded as limitations.

`rawunit-1.json` through `rawunit-11.json` are the exact UTF-8 ReferenceRecordBatch
submissions. Each carries its actual A/B registered pass pair, release
`bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`, reference policy
`statistics-reference-reading-3` and prediction policy `m1-grouped-reading-logistic-1`.
`coverage.json` contains every native item, separate native table-cell dispositions,
the frozen source census, all A/B record dispositions and 161 pointer-based coverage
accounts. Those accounts include genuine unresolved/unrepresentable readings, chart
routing limits, original-location uncertainty and explicitly reconciled fragments;
161 is not an unresolved-occurrence denominator.

C's choices follow the source rather than a vote or mechanical union. Corrections
include complete definition antecedents, located ordinary-grammar classifications,
explicit source qualifications, additional declared-symbol readings and complete
ordered equation-array rows. Quantile-pair declarations remain pairs. Formula
first-use anchors exclude characters inside TeX macro names such as `sqrt` and
`infty`. Quoted numeric values remain text; no normalization or scientific result
was computed. Table row labels are based on actual row content and layout.

The continuous-pdf/discrete-pf Bayes and composition readings retain their paired
alternatives as limitations under the frozen one-accepted-interpretation policy.
Missing or transformed symbols, headerless equation arrays, blank table cells with
no legend, chart coordinates and an explicit either/or proposition are not forced
into simpler accepted meanings. The recovered confidence-example setup without
original-page provenance remains unresolved as a possible additional original
occurrence; equal wording alone does not establish duplication.

`serialize.py` contains C's authored source selections, corrections and local
serialization. Only shared record identity primitives are used; production
assemblers/decoders do not generate the expected readings. `input-integrity.json`
confirms exact source-packet equality with frozen author packets, frozen input
hashes and every A/B authored-UTF-8/native-content-digest pair.

**Passed:**

```sh
uv run python docs/design_review/evidence/2026-11-04_m1-independent-references/author-C-v3/validate.py validation-final.json
```

`validate.py` uses the read principal, opens only the exact archived release,
authenticates source coordinates for runs 11/12/13, and calls `decode_authored` on
the exact submitted bytes. All 11 final units passed; final byte hashes are in
`validation-final.json` and `manifest.json`. No database write or protected
registration was performed by C. The root owns C registration.

Failed attempts remain in `validation-attempt-001.*` and serialization logs. The
first validation attempt passed raw JSON-list objects to a strict Python tuple
validator; the corrected harness first validates JSON through the archived batch
schema, then authenticates its typed records. `validation-attempt-002.*` records
the earlier bounded pass before the final semantic revisions.

Production predictions, fitting features/grades, provider/model calls, CPU/consumer
evidence, tests and product qualification were not run or read. Accepted reference
standing does not establish production publication authority or extraction quality.

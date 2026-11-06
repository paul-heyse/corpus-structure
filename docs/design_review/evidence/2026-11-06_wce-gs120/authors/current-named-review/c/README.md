# Current named-output adjudication C

Assessed **2026-11-06** under accepted WCE02/12 execution. [assessment.json](assessment.json) covers all **35 exact component IDs** from run **152**, cut **204**, structural task **605**, operation version **5**, release `release:570cbc60d1d36c5a68dcb8c9fc66ac5ac6077110615b26b138f987b4bf85d44b`. Complete exported and raw task component payloads remain separate: the export adds only `effective_version: null`; other raw component fields match exactly. The product remains `private_proposals`, with publication `not_requested`.

This is **output-first adjudication**, with current A/B accounts seen before C's independent source-context reading. Prior baseline-nine output adjudication, selected source-only common/recovered cases, and earlier selected PDF-page exposure remain declared. None of this is blinded or held out; development and assessment share source material. C read the actual relevant neutral passages and original/converted native items for every component. The supplied 48-view/120-page inventory establishes available source extent, not exhaustive manual annotation. No production projection, runtime/provider execution, database write, new PDF inspection, scientific verification, corpus efficacy claim or publication decision was used.

The result is **32 supported local partial attachments, two unsupported exact attachments, and one ambiguous exact attachment**. This is an attachment disposition, not a count of complete, clean or scientifically verified definitions. Anaphoric naming, example membership, model-label assignments and program naming can be useful local relationships. Qualifiers and completeness remain separate; recognition can fail even when a source element attaches to the correct local subject.

| Component ID prefix | Source reading and C disposition |
|---|---|
| `10701a2dec9c` | **Unsupported exact pair.** Source 122 `#/texts/13–15` says “the probability that X is less than Y is given by.” The emitted `Y` is only an operand. The corrected subject and same integral are independently quoted as an alternative; the wrong pair gets no positive attachment credit. |
| `d5715568638f` | **Unsupported exact performed definition.** Source 135 `#/texts/35` says “instead of defining the expected value as a weighted average, Huygens assumed…” The positive historical assertion concerns Huygens's assumptions/deductions. An embedded contrasted definition method is not a performed definition. The corrected historical subject/content/speech act are quoted separately. |
| `822bb6359ada` | **Ambiguous exact pair, no positive credit.** Source 147 `#/texts/3` names “a set of constant density,” while the emitted head is `a set`. C retains the full label and explicit fixed-density antecedent as a supported corrected alternative. The later ellipse characterization is an exercise request. |
| `7150bdfe222c` | **Supported local attachment; recognition unsupported.** Source 116 `#/texts/84` is the CDF display for Sn. Converted final exponent `1` differs from native original `n−1`, and narrative is included. The subject/display association survives; the corrupted formula is not certified. |
| `b16b87cce059` | **Supported local attachment; recognition unsupported.** Source 124 `#/texts/43` has one weighted-sum equation in `orig`; converted text adds prose fragments. The actual absolute-convergence condition is separate. |
| `789223b6033f` | **Supported local attachment; recognition unsupported.** Source 131 `#/texts/175` has one conditional weighted-sum equation in `orig`; converted text adds a dotted-symbol/duplicate expression. No second source quantity is inferred. |

The other distinctions remain granular in every record: memorylessness, maximum-likelihood estimates, utility functions, Little's law and distribution names require antecedent resolution; `females` and `males` are labels in an urn model; the initial three heads **exemplify** a run rather than define all runs as triples; the auxiliary line is specifically L; martingale is informal fair-game naming in this passage; `DieTest` names a program without establishing that it was run. Exercise formula and naming support does not turn “Show that” into a completed proof.

A's original prose expectations and B's six categorical facets are preserved verbatim rather than converted into invented votes. C supplies six judgments: term/subject, content role, direction/attachment, interpretation/speech act, scope/conditions, and recognition fidelity to native text. Per-case differences retain B's `unassessed` recognition versus C's bounded native comparison, partial/anaphoric content distinctions, exercise speech-act limits and exemplification versus a broad naming category. A prose labels such as “partial” are not silently relabelled as categorical agreement. Repeated source quotations remain one physical source.

## Typed expectations for narrow attachments

[author_expectations.py](author_expectations.py) contains C's manually authored source subjects, source-item selectors, interpretation, narrow state, local meanings, speech acts and qualifier limits. [build_assessment.py](build_assessment.py) only packages those judgments with frozen observations and mechanically locates literal source bytes; it imports no production projector or validator.

Each `entries[i].narrow_public_attachment` contains:

- `state`: `supported`, `unsupported` or `ambiguous` for the exact emitted local attachment.
- `expected_term` and `expected_content`: typed `passage_id`, `start`, `end`, `text` extents independently selected from neutral native source items.
- `expected_interpretation`, source anchor addresses, local meaning, speech act and qualifier limits.
- Separate completeness, recognition, exact-pair identity and positive-credit fields.

For all 32 supported cases the independently selected extents and interpretation match the actual pair exactly. For the other three, expected fields identify corrected source meaning; `positive_credit_for_exact_emitted_pair` is false, and corrected alternatives remain separate. The full source-owned display can be selected as an attachment endpoint while its recognition fidelity is unsupported: that expectation does **not** endorse every formula token. Native `orig` alternatives are preserved as native original quotations and never assigned fabricated converted-passage spans.

The source anchors preserve exact new packet hashes, source release/run/cut/recipe/projection/native-product identities, original and converted item text, provenance, physical-page mappings, and native piece bridges. Original charspans and converted offsets are separate coordinate systems. Bounding boxes locate containing items/cells, not exact selected substrings. Unknown source health remains unknown. Prior C common32 and recovered32 files are pinned as exposed source-context references; they are selected accounts, not a recall gold census.

## Literal validation and remaining boundary

**passed**, 2026-11-06:

```bash
uv run python docs/design_review/evidence/2026-11-06_wce-gs120/authors/current-named-review/c/validate.py > docs/design_review/evidence/2026-11-06_wce-gs120/authors/current-named-review/c/validation-receipt.json
```

[validation-receipt.json](validation-receipt.json) binds the final assessment and validator: 27 frozen input hashes, all 35 IDs, 70 observed endpoints, 70 typed expected endpoints, six corrected alternatives, 250 quotation anchors, 704 native-piece correspondences and 7,975 checks. It checks A/B transcription and literal expected/actual consistency, not the truth of C's judgments. A/B passed receipts are bound to their frozen assessment hashes; C did not rerun their validators.

[authoring-attempts.json](authoring-attempts.json) retains the initial literal-lookup failures: `males` first matched inside `females`, and the first `Y` differed from the selected probability-phrase operand. Source selection now respects lexical boundaries and keeps observed endpoints separate from corrected expectations. [validation-attempt001.json](validation-attempt001.json) and its empty stdout retain the initial validator parse failure; a parenthesis typo was corrected without changing source or semantic judgments.

This artifact applies to the pinned **run152/task605** baseline. Root must authenticate identical component payload and source custody before transporting these references to a final run under native160. That future transport is not pre-certified here. No imported consensus, full-record completeness, scientific correctness, graphical fit, general benefit, full-corpus precision/recall, operational qualification or publication authority follows. Root retains evidence records, protected imports, plan/status updates and integrated acceptance.

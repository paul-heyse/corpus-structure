# Source-grounded output-definition adjudication C

Assessed 2026-11-06 under accepted WCE02/12 execution. [adjudicated-assessment.json](adjudicated-assessment.json) covers all nine frozen private `definition_components` from run **139**, cut **178**, structural task **544**, release `release:c472a775cd781a8f1fb49ae346048a883e344d68d3cccb184a2dee7cfa6424f5`. This is an output-first census of that emitted family, not a source-first census or a held-out evaluation. Predictions and A/B judgments were seen before source inspection. None of these cases is held out; the source is shared development and assessment material. No corpus efficacy, precision, recall, calibration, independent scientific verification or publication claim follows.

C read the actual surrounding packet passages and native items, and complete original PDF text on parent physical pages **197, 220, 227, 250, 268, 269, 280, 295**. [original-pdf-context.json](original-pdf-context.json) preserves those page texts, PDF hashes and extraction commands. Original pages [220](original-page-220.png) and [280](original-page-280.png) were also visually inspected for the defining formula and theorem/example layout. Other graphical meaning is unassessed. Prior author-C source-only adjudication was consulted as an exposed contextual lead; this assessment is a separate output-first adjudicator, not another blind source-only inventory or independent physical witness.

The source supports **one local definition** and **one partial explanatory theorem application**. Five other emitted definitions and two other emitted explanation attachments are unsupported under their emitted meanings. This conclusion does not discard useful source relationships or require every useful fragment to be a complete textbook record.

| Component ID prefix | Emitted pair | C content / attachment | Useful retained distinction |
|---|---|---|---|
| `48aa526ace3f` | normal density function → formula | supported / supported | Explicit local definition. Parameters µ, σ and positive σ are stated nearby but absent as explicit qualifiers. |
| `919aa952ce14` | distribution → Equation 5.2 | unsupported / unsupported as definition | Poisson distribution has a formula reference. Source-requested normalization checks remain an obligation, not a completed proof. Approximation-use conditions are separate. |
| `1761a117bba5` | density → Law of Large Numbers | unsupported / unsupported as density explanation | Density symmetry and the contrast about Cauchy averages are separate useful source assertions; the latter needs a different subject. |
| `20d49e0702e9` | expected value → Law of Large Numbers | unsupported / unsupported as definition | The law justifies an average-outcome interpretation over many experiment repetitions. Historical rationale differs from defining content. |
| `e7f252c8cd01` | standard deviation → Chapter 8 | unsupported / unsupported as general explanation | Local spread explanation survives. Chapter 8 is a forward reference for precision of an average-concentration statement under independent trials and finite variance. |
| `55e6ed613a1e` | X → Theorem 6.15 | supported as partial explanatory reference / supported narrow application | The source explicitly uses the theorem for V(X), where X is uniform on [0,1]. It does not explain every property of X. |
| `4c5e5520d738` | hand → Epstein book | unsupported / unsupported as definition | Hand is a valid contextual entity; the bibliography refers to the broader simplified bridge point-count problem. |
| `6e3d760fdcb3` | opening bid → Epstein book | unsupported / unsupported as definition | Separate local characterization: player point count of 13 or more. The probability model and broader book referral have distinct scopes. |
| `911d85f50433` | hand → programNFoldConvolution | unsupported / unsupported as definition | Point-count distribution C is computed using a named program, single-card distribution and n=13 under the acknowledged independent-draw simplification. No program execution is claimed. |

Every selected term is supported as a **contextual referent**, independently of being a definiendum. A/B differ on the two `hand` term-role judgments because B rejects the definiendum role while A retains the contextual entity. C records both distinctions. The original PDF separates `program` and `NFoldConvolution`; the frozen converted token `programNFoldConvolution` is preserved exactly, without a silent repair.

The substantive A/B disagreement concerns `55e6ed613a1e`: A rejects the generic X-to-theorem explanatory edge; B supports the narrow variance-application reference. C retains the explicit partial application and rejects an unrestricted explanation of X. Content is supported as an applied reference, not as standalone explanatory prose. The dataset preserves both reviewers' actual facet labels and reasons; it does not report unanimous rejection of eight attachments.

A calls all scope/condition facets unsupported; B calls them ambiguous. C separates supported collection membership, stated local conditions, incomplete explicit qualification, and undeclared intended semantics beyond the collection string. Thus local qualification completeness is unsupported while the intended broader scope meaning is ambiguous. Missing conditions do not become source silence, universal assertions, or proof that an otherwise supported local attachment is absent.

Each component keeps its complete frozen export and raw task payloads and identifier, A/B perspectives, C's four facets, disagreement dispositions, missing facets, exact source anchors, and retained relations with their own subjects and types. The export adds only `effective_version: null`; raw task 544 omits that field. All other component fields match exactly. Anchors carry immutable packet/source execution identities, exact half-open Unicode spans, native converted-item offsets, original-item text and provenance, and physical-page mappings. Original native charspans and bounding boxes locate source items; they are not equated with converted-string offsets or exact selected substrings. Upstream unknown health states remain unknown.

Literal verification is **passed** on 2026-11-06:

```bash
uv run python docs/design_review/evidence/2026-11-06_wce-gs120/authors/output-definition-review/c/validate_literals.py > docs/design_review/evidence/2026-11-06_wce-gs120/authors/output-definition-review/c/literal-validation-receipt.json
```

[literal-validation-receipt.json](literal-validation-receipt.json) records the actual result and binds the final assessment and validator. The validator checks all nine identities, eighteen emitted endpoints, exact context quotations/native provenance, A/B judgment transcription, input hashes and reproducible original PDF text for eight pages. The earlier A/B passed receipts are retained and hash-bound; their validators were inspected, not rerun by C. Literal validity does not validate C's semantic judgments.

The first check is retained in [literal-validation-failed001.json](literal-validation-failed001.json): its direct raw-task/export equality assumption failed because of the export-only null version field. The final validator checks that exact difference explicitly and preserves both representations; no source or frozen component was edited to obtain a pass.

Remaining limits: referred Chapter 8 and Epstein contents are uninspected; full law hypotheses and an explicit x-domain are unstated in these inspected local statements; formula truth, normalization proofs, computational results, unselected source and graphics, other component families and full-corpus effectiveness are unassessed. The root retains planning, status, evidence-record and integrated acceptance ownership.

# Evaluation

Corpus Structure assesses each operation against its own source and expected
output. A supported link and an upstream missed cue answer different questions.
These examples are from the current probability textbook corpus.

| Layer | Question | Observed result or limitation |
| --- | --- | --- |
| Source capture | Did capture preserve the original material and location? | On physical page 416, the native math includes the matrices while the projected text stops at the array opener. [Capture review](design_review/evidence/2026-11-08_nce-full-book/review/README.md#findings-across-page-ranges) |
| Extraction | Did extraction locate the right spans and roles? | On page 47, a role record locates the defining occurrence of `probability`. The attachment selected a later occurrence and omitted the operative formula and condition. [Extraction review](design_review/evidence/2026-11-08_nce-full-book/review/definition-window-retry.md#semantic-findings) |
| Attachment and scope | Did the condition reach its intended host? | The source review supports the positive-variance attachment to the neighboring defining predicate on page 289. [Attachment review](design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-checks-on-cut-441) |
| Linking | Did the selected target match the source cue? | The Section 5.1 citation carries an explicit witness. The review checked nine retained decisions against the printed cues and target spans. [Citation review](design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#contextual-section-citations) |
| Assembly | Does the view include related supported material and exclude unrelated material? | Both normal-density dossier policies kept the two root-qualified members and excluded the independently supported marginal-totals component. [Dossier record](design_review/evidence/2026-11-06_wce-completion-repair/records/wce.repair-rooted-dossier.json) |
| Coverage gaps | Which source items were missed, and at which operation? | Four additional printed citations were absent from the upstream cue population. Book-wide citation recall remains open. [Source-side misses](design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-citations-outside-the-contextual-population) |

[Worked examples](examples/README.md) · [Whole-book assessment](design_review/evidence/2026-11-08_nce-full-book/review/README.md) · [Evaluation design](design/D7-evaluation-goldens-outer-loop.md)

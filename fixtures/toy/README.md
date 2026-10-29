# Ownership fixtures

The two HTML pages are authored for this test and carry no external corpus dependency.
`index.tsv` names pages relative to the source profile's root. `ownership.json` and
`registers.json` are independent authored batches and citation frames for their clause paragraphs.
Frames use the locator generator and sentence texts of the HTML; expected ownership outcomes are
stated here independently of consolidation and serving:

- ORG-101 owns P-17 over the two distinct intervals 2020 and 2022.
- Filing references F1 and F2 describe one 2021 fact and fuse, preserving their proposal support.
  Its distinct identity interval keeps the inert-pair example separate from the share examples.
- Shares 0.5 and 0.8 disagree on meaning and remain two ambiguous alternatives.
- Reports attributed to Alpha and Beta remain separate claims under the pack's reported modality.
- ORG-101, ORG-202 and org-101 remain three organizations, despite sharing the label Acme.
- The notice paragraph is materialized with its pack kind but is not routed for extraction.

There are nine materialized ownership claims including the two ambiguous members. Ordinary
accepted-only queries return seven; at 2020-07-01 the 2020 interval applies and the 2022 interval
does not, while claims without validity remain unknown. No derivation or scoring is premised.

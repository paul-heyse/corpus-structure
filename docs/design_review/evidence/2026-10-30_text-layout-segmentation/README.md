# Text layout and segmentation investigation

**Measured, 2026-10-30.** Bounded warm CPU comparison on the four vendored trace pages
(LocationScale, Normal, LogNormal, Gamma): 412 blocks / 10,810 tokens. This is not full-corpus
or ingestion-to-database qualification. `result.json` retains medians of three runs; the probe
uses the installed pinned spaCy 3.8.18 / en_core_web_sm 3.8.0. Model loading is outside timing.

Run from the repository root:

```sh
uv run python docs/design_review/evidence/2026-10-30_text-layout-segmentation/probe.py
```

## Layout disposition

The tokenization-plus-Doc baseline took 0.01468s; prepared reconstruction took 0.00705s.
JSON serialization took 0.00207s and deserialization 0.00505s for 667,164 bytes. Thus encoding,
decoding and reconstruction already take about 0.01416s before storage/transfer or native
validation. This measurement supplies no compelling saving for durable layout retention.
Select operation-owned layout preparation with explicit cold reconstruction through the same
producer. Do not add a PostgreSQL field, migration or persistent cache based on this result.
The ingestion batch consumes compact layouts immediately and drops them after segmentation;
no unused layout collection is retained on `IngestResult`.
No claim is made that separate processes avoid tokenization without transporting a layout.

## Segmentation disposition

The current pipeline took 0.3843s. The dependency-valid reduced `tok2vec, parser` pipeline took
0.3313s and differed from stored sentence boundaries in zero blocks. `analyze_pipes` reported
no unmet component requirements; the model's parser consumes the shared tok2vec representation.
This is promising, but four-page parity does not establish full source-profile equivalence.
Retain the current configured profile pending wider independent boundary qualification.

The explicitly enabled trained `senter` has its own embedded Tok2Vec network and
`overwrite=False`; it ran in 0.0209s but changed 45 blocks. A configured rule `sentencizer`
with `overwrite=False` ran in 0.00855s and changed 17 blocks. Those changes affect rendition
and anchor identity. Neither replacement is activated or relabelled as existing segmentation.
Their output differences require source-boundary assessment and a fresh declared configuration
and release before production adoption. No tokenizer, model download or extraction dependency
was introduced.

The probe reuses the same atom-aware prepared layout across profiles to isolate segmentation;
its timings include owned Doc reconstruction and boundary extraction. It is a bounded choice
investigation, not an independent grade or a statement that old segmentation is intrinsically
more accurate. Existing independently authored sentence/offset fixtures remain acceptance tests.

# Corpus Structure

**From documents to connected, source-grounded knowledge.**

[![Docs build](https://github.com/paul-heyse/corpus-structure/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/paul-heyse/corpus-structure/actions/workflows/docs.yml)

Corpus Structure is a document-intelligence pipeline for finding structure in a collection
of documents. The intended application is organizational knowledge, including policies,
procedures, technical documentation, and the relationships between them. The current
development corpus is a probability textbook.

The pipeline locates definitions and predicate roles, attaches conditions, resolves
references, and assembles related material into views that retain their source evidence.

The central idea is **progressive enrichment**. A located observation or supported connection
can be useful while a larger interpretation is still unresolved. The system preserves those
differences so a reader can inspect what was observed, what was selected, and what has been
assessed.

[Documentation](https://paul-heyse.github.io/corpus-structure/) · [See an example](docs/examples/README.md) · [Explore the architecture](docs/design/README.md) · [Read the evaluation](docs/evaluation.md) · [Run locally](#run-locally)

## How it works

<picture class="pipeline-diagram">
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/pipeline-dark.svg">
  <img src="docs/assets/pipeline.svg" alt="Four operations produce located observations, qualified components, witnessed connections, and assembled views. Provenance and assessment apply throughout.">
</picture>

[Full-size diagram](docs/assets/pipeline.svg) · [Full-size dark diagram](docs/assets/pipeline-dark.svg)

The pipeline locates observations in source material, attaches roles and qualifiers,
connects related material through typed links, and assembles comparisons and dossiers.
Each operation leaves an inspectable output. Later stages reuse supported structure
while unresolved material remains visible. Assessment can focus on any stage.

## A real result

In a correlation exercise, the source establishes positive variance before defining
correlation in the next sentence. The pipeline retains the assumption and attaches
it to the defining predicate. A separate source assessment supports that attachment
in this occurrence. [Inspect the condition and its evidence](docs/examples/README.md#a-condition-stays-attached-to-its-predicate)

### A printed reference becomes a typed link

On physical page 260 of Grinstead and Snell’s *Introduction to Probability*, the text
refers to **Section 5.1**. The pipeline retained that occurrence and selected a
`cites-section` edge to **Important Distributions** on physical page 191. The edge carries
an explicit source-cue witness. The dated output review checked the cue and target
against the printed book.

[Follow the citation to both source pages and the retained evidence](docs/examples/README.md#a-printed-reference-becomes-a-typed-link).

## What you can inspect

| Capability | Inspectable result |
| --- | --- |
| Source capture | Native document items, projected passages, and source locations |
| Extraction | Defining expressions, predicate roles, conditions, and modality |
| Contextual linking | A located cue, the selected typed connection, and its witness |
| Comparison and assembly | Differences between qualified readings and dossiers organized around a selected root |
| Granular evaluation | Separate assessments of source capture, attachments, links, and applicability |

The development corpus includes all **518 physical pages** of the book, with **29 selected
source views** for downstream work. The contextual review checked nine retained section
citations and separately identified four additional printed references that did not enter
retrieval. Coverage and maturity vary by operation. The [output review](docs/design_review/evidence/2026-11-08_nce-full-book/review/README.md)
and [current checkpoint](STATUS.md) document the boundaries.

## Engineering approach

- **Preserve local meaning.** A role or condition can remain independently useful before the whole passage is interpreted.
- **Keep relationships typed.** Similarity, citation, identity, and applicability support different operations.
- **Retain source evidence.** A result can be followed back to its supporting occurrences and the published source.
- **Assess the operation being improved.** Capture, interpretation, attachment, and link selection can be examined separately.

The [architecture map](docs/design/README.md) connects these choices to design and code. The
[examples](docs/examples/README.md) also show antecedent recovery, dossier assembly, and what happens when a
candidate link lacks sufficient support.

## Run locally

- **Inspect results.** Start with the [static examples](docs/examples/README.md).
- **Reproduce the documented experiment.** Follow the [source, release and environment instructions](docs/examples/README.md#reproduce-the-contextual-example).
- **Develop locally.** Use the [developer setup](docs/develop.md) for the checkout, tool check and code routes.

Built by Paul Heyse as part of an ongoing exploration of structured document intelligence.

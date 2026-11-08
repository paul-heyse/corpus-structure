---
id: ADR-0003
title: Publish the documentation with derived navigation and search
status: superseded
date: 2026-10-28
supersedes: []
superseded-by: ADR-0071
design: [§2]
evidence: Implemented
revisit: A meaningful design change requires duplicate architectural statements or publication metadata, section moves break durable citations, or documentation builds require product qualification.
---

## Context

The architectural collection, decisions and process pages are Markdown in the tree. Reading them
through a static site with search lowers the cost of finding the owner of a question, provided
publication never becomes a second authority (library-context ADR-0041).

## Options

1. Plain Markdown and repository search: minimal tooling, weaker navigation as the corpus grows.
2. **mdBook navigation, Pagefind search and offline lychee link checks** (chosen): sources stay
   usable directly; no hosted service or Node application.
3. A semantic documentation platform: more automation, but another maintained model without a
   current consumer.

## Decision

- `docs/site.toml` owns selection, ordering, current work, URL settings and tool pins;
  `docs/book.toml` owns rendering choices. `scripts/docs.py` (stdlib) stages, renders, indexes
  and link-checks under ignored `build/docs/`, replacing the last good site only on success.
- Search defaults to Current; lifecycle comes from ADR status and the standard manifest.
- A docs-only CI workflow produces a site artifact; there is no public deployment.
- Documentation-tool pins use focused `just docs-test` and `just docs-check`, independently of
  product qualification.

## Consequences

Mechanical checks establish publication integrity, not architectural quality or historical truth.
Further section splits follow real reading needs.

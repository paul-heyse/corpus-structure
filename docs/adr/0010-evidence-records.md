---
id: ADR-0010
title: Record finalized evidence as typed records with generated indexes, a rebuildable catalog and generated report figures
status: accepted
date: 2026-10-28
supersedes: []
superseded-by: null
design: [§2]
evidence: Implemented
---

## Context

The design spikes produce evidence that later work revisits: S2–S7 consume S0/S1 results,
revisits re-run earlier packages, and reports cite figures. Before this decision, evidence was
held in three ways:

- results lived as files under `docs/design_review/evidence/<folder>/` with no record of what
  each established, why, from which inputs, or what consumed it;
- every question about results needed new ad-hoc code;
- report figures were copied by hand, so a re-run could silently leave a report stale.

The evidence README's index table was hand-maintained and empty. The operator asked
(2026-10-28) for an organized, referenceable store of finalized evidence that serves navigation,
record keeping and analytics. It covers finalized results only, not every run, and has one
operator with no concurrent writers.

## Options

1. **Conventions only** (the simplest option): README prose per folder. It has no validation, no
   staleness detection, nothing queryable, and indexes are still hand-kept. It loses.
2. **A database as the authority** (SQLite or DuckDB holding the records). It gives queries and
   transactions, but a committed binary database does not diff or review, and nothing here
   writes concurrently.
3. **Text records in Git as the authority, with everything else derived** (chosen):
   - one JSON record per finalized result, validated by a pydantic schema;
   - generated README indexes;
   - a DuckDB catalog rebuilt from the records, with per-folder views;
   - reports whose figures are queries.
4. **Other engines:**
   - DataFusion overlaps DuckDB without persistence or an agent-oriented CLI;
   - markdown-it-py is unnecessary because the system generates Markdown and parses none.

## Decision

- **Records.** A finalized result of an investigation gets one record,
  `docs/design_review/evidence/<folder>/records/<id>.json`, conforming to the `Record` model (schema version 1) in
  `tools/evidence/src/corpus_evidence/model.py`. Its JSON Schema is exported to
  `tools/evidence/record.schema.json`.
  - **Contents:** what was asked and which items it informs, the method, commands and agents,
    inputs and outputs with content hashes, headline results, outcome, conclusion and consumers.
  - **Revision:** a revised result supersedes the earlier record.
  - **Scope:** records are written when a result is accepted, not per run. The record is the
    authority for what the result is; the files it names are its evidence.
- **Command:** the `corpus-evidence` workspace package (`just evidence`) derives everything else:
  - `finalize` fills the hashes;
  - `check` validates records, file presence, unchanged outputs, references, supersession
    consistency and current indexes;
  - `index` regenerates each folder README's records block and the evidence README's folder
    table;
  - `catalog` rebuilds `build/evidence.duckdb`: base record tables, a `records_for(item)` macro,
    and each folder's optional `catalog.sql` views under its own schema;
  - `render` produces Markdown from Jinja2 templates whose figures come from the catalog.
    Undefined names are errors, and the output names the records it used.
- **Authority and retention:** the catalog and generated blocks are never authorities. Records
  live and retire with their folder under ADR-0001.

## Consequences

- **Easier:**
  - finding what supports an item (`records_for`);
  - knowing whether an output changed after it was accepted;
  - adding a folder's analysis views beside its data;
  - regenerating report figures after a re-run.
- **Harder:** a finalized result now needs its record written and finalized. That cost is
  deliberately limited to accepted results.
- **No new gate:** `just evidence` is not part of `hygiene`. It runs when evidence is finalized
  or reported.
- **Dependencies:** duckdb 2.0.0, jinja2 3.1.6 and pydantic 2.14.1, pinned exactly.
- **Implemented 2026-10-28:**
  - seven tests in `tests/evidence/`;
  - 25 backfilled records for the 2026-10-28 design spikes, covering finalized results only;
    agreement figures follow the S0-G re-run;
  - `just evidence` reported 0 errors.
- **Revisit:**
  - finalized records should outlive their folder's retirement, which would supersede
    ADR-0001's evidence clause;
  - a second operator or concurrent writers;
  - catalog builds becoming slow enough to need incremental loading.

## Amendments

- 2026-10-28 (P0-P-4): `just evidence check` also resolves record ids cited in `docs/design/` and `docs/adr/` and warns on superseded or unknown ids; the DuckDB catalog's tables are derived from the `Record` model rather than hand-written. No decision changed.

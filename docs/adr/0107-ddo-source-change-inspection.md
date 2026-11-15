---
id: ADR-0107
title: Captured source drives migration, change explanation and explicit navigation
status: accepted
date: 2026-11-14
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
revisit: A supported source-update consumer needs syntax or semantic behavior outside the captured-source contract.
---

## Context

The operator selected a focused execution of Python I01–I07 and Ast-grep I01–I06, including planned change/currentness, documentation and navigation consumers. Closed extraction and finite preview/apply already exist. The same proposed snapshot must determine edits, effective facts and explained change. Required consumers are implemented with their prerequisites; their absence in the baseline is not a reason to defer accepted functionality.

## Options

1. Extend the existing AST/symtable discovery and invoke the ast-grep CLI for an additional candidate facet. This retains duplicated recognition and subprocess/source reconstruction for repeated snapshot queries.
2. Use embedded ast-grep for supplied-source structural candidates, existing LibCST for lexical evidence/edits, Griffe for interfaces/documentation and bounded Astroid refinement. Selected: library responsibilities compose around one captured source universe and existing publication owner.
3. Add raw Tree-sitter incrementality or make ty's internal engine the semantic authority. Neither supplies the governing domain, support or publication contract; both add another interpretation lifecycle. These routes are unselected.

## Decision

Use ast-grep-py 0.51.2 for finite structural discovery over captured/proposed Python bytes, sharing each parsed root across native queries. LibCST 1.9 supplies binding evidence and programmatic codemods with coordinated imports and explicit annotation application. Griffe/griffelib 2.4.1 supplies final callable/documentation and supplying/exposed facts. Astroid 4.3.4 remains preparation-local structural refinement with explicit unknowns and no ambient loading or unrestricted inference.

Archive a versioned interface/documentation projection separately from recipe determinants. Canonical effective projections own semantic drift and reuse; Griffe breakages are auxiliary asymmetric explanations. Explicit proposed-source comparison and native selected-product currentness share change semantics and retain their distinct readiness premises. Source apply never starts corpus execution; later demanded execution preserves support and equal-value cutoff.

Expose explicit ty 0.0.102 public LSP navigation over captured/proposed sources. Disable diagnostics/uv integration, negotiate capabilities and terminate the invocation-owned session. Results are snapshot-attributed tooling observations, with external/unsupported locations explicit. They do not authorize edits, execution or reusable identity. Pyrefly remains the checker. Ordinary archived reads serve prepared products without hidden source analysis.

## Consequences

One existing preview/apply owner retains exact-byte staleness, source membership, locking and retry. Required unknown consumers prevent applicable edits; missing optional demand context yields unknown semantic impact. Real M1/contextual/structural/inherited consumers and removal of superseded machinery belong to integration. Rich accepted-knowledge conversion and persistent deployment remain outside this increment. Benefits are qualitative Proposed, not measured.

The [DDO coordinator](../plans/declared-data-operations_2026-11-12.md) owns implementation, qualification and remaining obligations. Acceptance establishes the decision; it does not establish completion or provider/native passage.

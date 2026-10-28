---
id: ADR-0017
title: A domain is a LinkML pack compiled into every consumer
status: superseded
date: 2026-10-28
supersedes: []
superseded-by: [ADR-0020]
design: [§B5]
evidence: Tested
revisit: LinkML's generators block a compiler, or a domain needs logical inference over the schema.
---

## Context

The core must hold nothing domain-specific (DESIGN §1.1, §1.3). A domain declares its classes,
predicates, qualifiers, identity and extraction hints; the consumers are the schema tables, GLiNER2
schemas, the JSON Schema for LLM and agent batches, the validation rules and the annotator reference
(D2 §7). In the old repository, the cost of a new distinction was a code, codec and migration change
([design rationale](../design/rationale.md) §2, P1). Spike S4 checks that schema v0 compiles to each
consumer.

## Options

1. **LinkML YAML packs with `ci:` annotations**, compiled into every consumer. A mature schema
   language with generators, `SchemaView` for programmatic reading, annotations for our own
   semantics, readable by models and people, versionable in Git.
2. **OWL with SHACL.** Expressive for logic and validation over RDF, but heavier to author, built for
   open-world reasoning the design does not need, and not a natural source for GLiNER2 or LLM
   schemas.
3. **Pydantic models as the schema.** The old repository's failure: meaning in code.
4. **JSON Schema alone.** No class hierarchy, no rich slot semantics, no generators to other targets.

## Decision

Option 1, as D2 states it. One pack per domain (`domains/<name>/schema/`) carries meaning and
extraction behaviour together, so a description edit, which changes encoder and LLM behaviour, is
visible as a schema version. Every consumer is compiled from the same source, so none can drift.
Native LinkML features replace `ci:` annotations wherever they exist (rationale §4.3).

**What the pack owns, and what it does not** (2026-10-28, from the schema-rules library note). The
pack owns the domain vocabulary: classes, predicates, qualifiers, enums, identity and extraction
hints. The domain-independent D1 shapes (values, condition nodes, bindings, batch items) are
hand-written Pydantic models in `core`, with `core.yaml` as their contract-tested mirror, because
LinkML's Pydantic generator rejects the binding shape every batch uses and emits no discriminated
unions (D2 §6). The batch JSON Schema is built from Pydantic models generated per predicate from
the pack, not by `gen-json-schema` (D2 §7.3). This keeps the decision's point, that no domain meaning
lives in code, while using each tool where it is exact.

**Proposed until S4 reports** (operator decision, 2026-10-28). S4's findings on `oneOf` branches,
structured-output constraints and annotation round-trips (OPEN-D2-1, OPEN-D2-6) may change how the
compilers are stated. Acceptance follows S4 and the design/target review that precedes phase 0
execution.

## Consequences

- A new distinction is a schema edit and a migration mapping (D2 §8); a new domain is a new pack.
- The compilers are product code that must keep pace with LinkML releases (`docs/pins.md` once
  pinned).
- **Evidence (S4, 2026-10-28; operator accepted the report):** the pack in native LinkML form compiles
  to the schema tables, both batch forms, the GLiNER2 schemas, the rules and the annotator reference;
  135 batches validate ([S4 report](../design_review/evidence/2026-10-28_design-spikes/S4-report.md),
  records `s4.*`).
- **Revisit** if LinkML's generators block a compiler, or a domain needs logical inference over
  the schema.

---
id: ADR-0150
title: Start SBX development from an empty current-model database
status: accepted
date: 2026-11-21
supersedes: [ADR-0143]
superseded-by: null
design: [§B2, §B5]
evidence: Proposed
revisit: An explicit development data retention obligation changes the authorized reset scope.
---

## Context

The SBX population, reference and request changes replace stored representations across several
operation families. The earlier decision required regenerating derived values from retained
originals. The operator authorized discarding the development data through SBX-09, including
the originals. The project can validate the new contracts with newly admitted fixtures.
[Cutover owner](../plans/set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09)

## Options

1. Start with an empty development target. A cold root exercises the current schema, and small
   fixtures exercise real publication, authority and recovery at lower cost than reproducing the
   old corpus.
2. Rebuild the existing development data. This would make old corpus selections available again
   immediately and would require recapturing sources, repeating provider work and rebuilding the
   derived identities across the replacement families.

## Decision

Install the SBX-09 development baseline from one registered cold root after the integrated
replacement passes its native and ordinary execution checks on fresh fixtures. Replace
`corpus_structure_dev` on the dedicated development cluster with an empty installation. Retire
superseded representations, compatibility code and the active development migration chain.
The reset requires no conversion or regeneration of discarded rows.

Native publication, current-use authority, genuine producing history and recovery govern
all new inputs and results. Historical managed artifacts retain their original evidence standing.
The stage target and subsequent identity, read and PDF registration and installation work
belong to SBX-20. Whole-book qualification belongs to SBX-22.

## Consequences

The first development installation starts with no project data. Work that needs a source admits
it through the current model. The qualified root and fresh fixture runs supply the acceptance
evidence for the reset itself. Implementation and verification remain with the owning plan.
[SBX coordinator](../plans/set-based-execution_2026-11-21.md)

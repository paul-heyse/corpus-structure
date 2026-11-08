---
id: ADR-0072
title: Add optional library-led discovery briefings
status: accepted
date: 2026-11-08
supersedes: []
superseded-by: null
design: [§2]
evidence: Implemented
revisit: Repeated briefings require the same evidence extraction or routinely need stronger attribution than representative source inspection can supply.
---

## Context

ADR-0008 establishes the codebase-first assessment workflow. A selected library family can
also prompt a question about promising capabilities before there is a concrete opportunity.
Broad overviews explain capabilities, while applicability accounts are organized around
specific opportunities. A family-level account needs a home for usage and research priorities.

## Options

1. **Use overviews and ad hoc source reads.** This requires little setup but leaves the local
   interpretation scattered and gives it no refresh owner.
2. **Add optional briefings using existing tools.** This provides a separate entry and keeps
   the effort proportional to the selected family. The author judges coverage and corroborates
   ambiguous observations.
3. **Build a package and source census first.** This could support repeated investigations over
   the same scope, but adds analyzer preparation, attribution and maintenance work before
   there is a demonstrated consumer for the census.

## Decision

Add `leverage-library-discovery` as an optional entry to the
[library-leverage framework](../library_leverage/library-leverage-framework.md). Keep one
contextual briefing per investigated family in its library account. The briefing owns
representative usage interpretation and proposed research priorities. ADR-0008 governs the
assessment stages and their judgments.

Use release references, locked dependency tooling, installed metadata and bounded source
inspection as available. Distinguish dependency selection, installed availability, source
observations and recorded execution. Consider dedicated automation when repeated work
establishes the need.

## Consequences

The skill and [evidence guide](../library_leverage/references/discovery-and-evidence.md) give
engineers and agents a common route from library questions to focused research. The operator
selects the first pilot. Discovery benefits remain Proposed until use supplies evidence.

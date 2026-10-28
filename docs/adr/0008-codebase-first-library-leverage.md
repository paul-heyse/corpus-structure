---
id: ADR-0008
title: Discover library leverage through three evergreen assessment stages
status: accepted
date: 2026-10-28
supersedes: []
superseded-by: null
design: [§2]
evidence: Implemented
revisit: Stages duplicate judgments, reusable knowledge disappears with current matches, or focused research becomes an impractical general catalogue.
---

## Context

Programming agents need a codebase-first way to recognize useful library opportunities, assess
specific capabilities and compare complete alternatives. Broad overviews supply awareness;
focused capability analysis should accumulate beyond the lifetime of its originating use.

## Options

1. Use only broad overviews and existing reviews, leaving opportunity discovery implicit.
2. Combine discovery, applicability and comparative selection in one skill.
3. Keep three distinct skills and evergreen accounts with shared patterns (chosen), supporting
   clear assignments and different knowledge-retention needs without a fixed investigative script.

## Decision

[DESIGN §2](../design/DESIGN.md#section-2) and the
[framework](../library_leverage/library-leverage-framework.md) own the workflow and its binding.
Install `leverage-codebase-audit`, `leverage-library-assessment` and `leverage-opportunity-review`
as tracked process skills, exposed through the existing `.agents/skills` symlink.

Start from codebase responsibilities and intended activities. Separate concrete opportunities,
reusable library opportunity types and contextual fit, and comparative judgments of complete
options with bounded target recommendations. Research and review can challenge prior premises.

All stages use base patterns plus useful patterns collected in assessment outputs. Both codebase
identification and library applicability assess whether the current framing needs expansion.
Additional patterns are usable immediately within scope; promotion into base guidance is manual.

Keep current accounts in place with stable identities, source/library baselines, dated evidence
and meaningful limits. Codebase opportunities retire on evidence; useful library types and output
patterns survive after all current matches disappear. Reconcile links before retirement and keep
history in Git. Installation creates unassessed entry pages, not actual assessment findings.

Accepted plans own scheduled disposition and closure. Existing formal review cadence remains;
the leverage workflow neither replaces required reviews nor authorizes implementation. No new
gate, runtime adapter, mandatory probe or broad audit follows from ordinary library use.

## Consequences

**Implemented guidance:** the scaffold supplies active skills, shared references, base patterns
and distinct codebase/library/review folders. Discovery and design-quality benefits remain
**Proposed**. First use supplies actual assessment baselines; installing the workflow establishes
no product qualification or library applicability. Existing projects allocate their own ADR when
adopting this additive process; template updates do not overwrite accepted project decisions.

---
name: leverage-codebase-audit
description: Identify and refresh concrete codebase opportunities for library leverage using a shared recognition framework. Maintain an evergreen account of responsibilities, evidence and constraints; use for a requested broad or focused opportunity inquiry, leaving applicability and comparative selection to the other leverage skills.
---

# Identify codebase opportunities

Build a current, evidence-grounded account of where library capabilities could improve the
codebase's responsibilities or enable a worthwhile intended activity. Start from the codebase
and its consumers. An opportunity may involve existing machinery, an underused dependency,
a domain algorithm, a whole workflow or a credible functional gap.

## Output in this repository

Maintain the living opportunity account under docs/library_leverage/codebase/, starting from its
[entry page](../../../docs/library_leverage/codebase/README.md) and adding useful topic pages.
The first real audit records its inspected baseline; installation alone establishes no assessed
account. Shared additional-pattern definitions belong
in docs/library_leverage/assessment-patterns.md, created with the first useful addition.

## Establish scope and the current account

Read the [repository framework](../../../docs/library_leverage/library-leverage-framework.md), [shared language](../../../docs/library_leverage/references/shared-language.md) and
bound opportunity-pattern framework at
[Codebase opportunity patterns](../../../docs/library_leverage/patterns.md). Read the current codebase collection if one
exists, together with the shared additional-pattern output when present. The working pattern set
includes base and output patterns; use relevant additions on the same footing as base patterns.
Resolve the requested broad or focused scope from the assignment; a focused inquiry
need not audit the entire repository.

Establish the intended outcomes, relevant responsibilities, owners, consumers, existing mechanisms
and constraints. Architectural owners and accepted decisions explain the present design;
relevant open work explains planned consumers when needed. Distinguish existing promises,
accepted planned capabilities and proposed additions. A mechanism named by the current design
can still be a subject for later comparison under the governing criteria.

Record the inspected source baseline, included dirty changes, date, criteria edition and
meaningful coverage limits. Distinguish this source state from the eventual publication revision.
For a refresh, use changes in contracts, consumers, dependencies and intended work to direct
attention. Follow their significance into unchanged code; the diff and previous account are leads,
not a search boundary or verdict. Inherited observations retain their original dates and limits.

## Recognize opportunities

Use the pattern framework to broaden and focus thinking. Examine complete operations and
responsibility boundaries as well as local implementations. Useful questions include:

- What generic work does the codebase carry, including inside its domain-critical algorithms?
- Where does a supported change require repeated mechanical edits or independent decisions?
- Which boundaries hide collective intent, repeat preparation or force conversion and hydration?
- Where do wrappers reconstruct capability, coordinate lifecycles or fight an existing model?
- Which equivalent responsibilities have fragmented, and which differences are intentional?
- Which desired activities are absent or difficult to compose, and who would benefit?

Assess whether the working patterns adequately frame the responsibilities and opportunities
encountered. When a useful framing is missing or insufficient, record or refine an additional
pattern in the shared assessment output during this pass. Explain its reusable shape, scope,
counterconditions and what the existing patterns missed, using the collection-writing guidance.
Apply it to affected observations and research questions. A pass may find the current patterns
sufficient; adding patterns is not a quota or a prerequisite to recording an opportunity.

New definitions belong in assessment outputs, with stable additional-pattern IDs, rather than
in this skill or the base framework. They are usable immediately. The operator can later select
helpful framings for manual promotion; that decision does not gate their current use.

Connect observations to a concrete need and plausible value. Include system-level opportunities
without assuming that higher altitude is inherently better. A local change can remove a broad
burden. Existing strengths, legitimate exceptions and reasons for custom behavior help reveal
the actual contract gap.

Read representative paths, callers and tests to establish the mechanism and footprint. Tests and
current usage are evidence of dependencies, not automatic authority for preserving every quirk.
Follow consequential boundaries until the observation is understandable. An exhaustive file census,
complete flow trace or line-by-line catalogue is unnecessary.

The optional [search cues](references/tells.md) can nominate places to inspect. Names, loops,
private API use, duplicated forms and old versions are clues; none establishes an opportunity
by itself. Record coverage honestly. A missing library match or unknown capability does not
invalidate a well-grounded opportunity.

## Explain the opportunities

Give each opportunity a stable ID and meaningful title. Explain the intended operation and
consumer, current mechanism or missing support, why improvement matters, relevant patterns,
representative source evidence, known footprint, preservation constraints and material uncertainty
or counterevidence. Use the [collection-writing guide](../../../docs/library_leverage/references/collection-writing.md) for
flexible examples. Group manifestations by a coherent need and cause without collapsing distinct
semantic obligations.

A library nomination can help the next researcher, but the opportunity must remain intelligible
without that candidate. Applicability research belongs to `leverage-library-assessment`;
comparative selection belongs to `leverage-opportunity-review`. This stage need not prove a
principle violation, choose a remedy or design an implementation package.

## Maintain the living codebase collection

The entry page explains the relevant system picture, opportunity synthesis, inspected baseline,
coverage and routes to topic pages. Segment by coherent responsibilities or operations; add pages
when they have useful content rather than instantiating every concern family. Keep each opportunity
in one primary home with stable references.

Refresh explanations in place and challenge earlier premises. Retain an opportunity while its
underlying relevance remains, including while work is scheduled. A recommendation, accepted
ADR or rejected library does not resolve it. Retire on evidence of resolution, corrected premises,
supersession or loss of relevance, recording why in Git and never reusing its ID.

Coordinate incoming applicability and review links before removal. Reusable library opportunity
types survive even when their originating codebase opportunity and all current matches retire.
Preserve useful lessons and revision-specific provenance without leaving broken live references
or keeping the old codebase occurrence solely to support the library collection.

Accepted plans own scheduling and closure evidence. Link to those owners without copying mutable
execution status. The audit owns opportunities at its stated baseline and does not certify
architectural alignment or replace any separately required diagnostic audit.

## Deliver a usable account

Return the updated collection, inspected baseline, important opportunities and limits, and focused
questions for library research. Include the route to any additional patterns collected or refined;
the codebase entry page points to their shared output. A strong account makes the responsibility,
potential value and constraints clear enough for an applicability researcher to begin. It also lets a later review
challenge the observation rather than merely select its nominated library.

Warning signs include linter-style lists without responsibilities, assumed needs copied from
similar systems, generic calls to use libraries more, or broad claims from unexamined areas.
This skill changes assessment documents, not product code, dependencies or accepted scope.

---
name: leverage-library-assessment
description: Assess focused library capabilities against identified codebase opportunities, maintaining reusable library opportunity types and contextual applicability in an evergreen collection. Use for deliberate applicability research or refreshing prior assessments; comparative selection belongs to leverage-opportunity-review.
---

# Assess library opportunity applicability

Determine which concrete library capabilities could address identified codebase opportunities,
under what conditions and with what residual work. Preserve reusable capability knowledge as it
accumulates, independently of the lifetime of its current codebase matches.

## Output in this repository

Maintain the library assessment collection under docs/library_leverage/libraries/, starting from
its [entry page](../../../docs/library_leverage/libraries/README.md) and grouping research by library.
A library's account holds its reusable types and separately identified contextual fit; create its
entry page with the first real assessment. Shared additional
patterns belong in docs/library_leverage/assessment-patterns.md, created with the first addition.

## Establish the research question

Read the [repository framework](../../../docs/library_leverage/library-leverage-framework.md) and the
[shared language](../../../docs/library_leverage/references/shared-language.md). Start from the selected codebase opportunities,
their baselines and constraints, and the existing library assessment account. Use the relevant
parts of the bound opportunity-pattern framework to sharpen what mechanism would help.
Read the shared additional-pattern output when present and use relevant additions on the same
footing as base patterns. The working set can expand through this applicability assessment.

Codebase opportunities screen the research. When the account is missing, develop or request a
focused opportunity with `leverage-codebase-audit`; a complete-codebase audit is unnecessary for
a focused assignment. A retained library type can be refreshed for a version or semantic question
without inventing a current codebase match.

Resolve which capabilities and libraries deserve attention from the supplied scope, opportunity
and existing research. Consider existing dependencies early while following plausible mechanisms
beyond them when useful. Broad library overviews supply orientation, not an obligation to profile
the entire library. A substantial assessment can cover several related types; depth follows the
need and consequential uncertainty.

## Research mechanisms and conditions

Use Context7 as the first documentation lookup, then primary documentation, release information,
tagged source, installed implementation or upstream tests where consequential details remain.
Match the evidence to the release, build, runtime and configuration actually considered. Distinguish
installed availability from an upgrade-dependent route and released behavior from development work.

Investigate the actual operation and how the relevant features compose. Public APIs, configuration,
extension points, bulk/lazy/native interfaces and companion integrations can matter together.
Identify what the library discharges and which domain policy, adaptation, enforcement or lifecycle
obligation remains with the caller. Follow the useful capability family beyond its familiar entry
point, without turning the inquiry into an exhaustive library inventory.

Characterize semantic differences that could change applicability: identity, nulls, ordering,
precision, approximation, errors, effects, concurrency, resource ownership or completeness as
relevant. Inspect contrary evidence. An empty search, an absent overview section or failure of
one route does not establish that the library cannot serve the need.

Static evidence can establish an interface route. Use a targeted probe when it would settle a
meaningful uncertainty, under the host's evidence and execution rules. Do not claim application
testing or quantitative benefit from documentation inspection.

## Assess the adequacy of the patterns

Compare the codebase opportunity's framing with the functionality and compositions uncovered.
Does the existing analysis overlook a responsibility, semantic distinction or useful shape of
leverage that becomes apparent through this comparison? Assess whether an existing output
pattern should be refined or an additional reusable pattern would improve investigation.

Record useful additions in the shared assessment output during the pass, using the
collection-writing guidance. Explain their scope, counterconditions, origin and distinction from
existing patterns; apply them to the affected opportunity analysis and candidate capabilities.
Coordinate consequential corrections to the codebase account. An addition need not await a
future audit or manual promotion before being used. No addition is required when the existing
framings suffice.

Keep the pattern definition in outputs and cite it from type and applicability records. Do not
automatically edit this skill or the base framework. Useful patterns survive retirement of their
originating matches; the operator can later select them for inclusion in the base guidance.

## Maintain two kinds of knowledge

**Reusable library opportunity types** explain focused needs, recognizable code shapes, concrete
mechanisms and composition, discharged/residual obligations, important conditions and limits.
Keep their explanations independent of local source paths, pins, current opportunity IDs and
repository decisions. Their handles describe capabilities at a useful granularity.

**Contextual applicability assessments** connect those types to specific codebase opportunities
at identified revisions. Explain fit, prerequisites, configuration or extension, actual semantic
gaps and unsettled premises for the selected library realization. Give a reasoned applicability
conclusion without deciding that this candidate is the best complete option.

Use the [collection-writing guide](../../../docs/library_leverage/references/collection-writing.md) for proportional content
and examples. Separate these two kinds of knowledge within a small document, or split into type
pages and an applicability account when that improves independent use. Maintain a useful index
of retained types, including types with no current matches.

## Refresh and accumulate

Record source/library baselines, dates, actual coverage and inherited limits. Reuse sound analysis
while revisiting premises changed by versions, codebase guarantees or new evidence. Preserve
useful negative results with their exact scope and explain what could change the conclusion.

Retain a useful library type after its originating opportunity or every current match retires.
Deepen its recognition, mechanisms and semantic conditions as new inquiries teach more. Remove
obsolete current matches; transfer only justified general lessons into the reusable account.
Correct, merge or retire false, redundant or obsolete types deliberately, preserving meaningful
supported-version distinctions and stable references. Growth means better usable knowledge.

The collection owns capability analysis and contextual fit. Communicate corrections to opportunity
premises through the coordinator; preserve the evidence needed for a reviewer to disagree or
investigate another route. Comparative preference belongs to `leverage-opportunity-review`.

## Deliver a usable assessment

Return the refreshed type and applicability routes, inspected baselines, material discoveries and
limits, any additional patterns collected or refined, and consequential questions for comparative
review. Route the library entry page to the shared pattern output. A strong assessment lets a
reviewer understand both the concrete candidate fit and reusable conditions without reading whole manuals.

Warning signs include a general displacement catalogue, name-based matching, unqualified version
claims, a type dependent on retired local context, or suitability inferred solely from an API's
existence. Preserve unresolved semantics explicitly. This skill changes assessment documents;
it does not install dependencies, alter product code or accept an implementation target.

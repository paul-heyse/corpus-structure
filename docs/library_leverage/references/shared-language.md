# Shared language and collection contracts

This is the single authored reference for the three library-leverage skills. The project's
framework binds collection paths, the pattern framework, design criteria and evidence conventions.
Keep repository-specific bindings with that framework; the vocabulary is portable.

## Concepts

**Working pattern set.** The base opportunity patterns together with additional patterns recorded
in assessment outputs. An additional pattern is a reusable recognition or reasoning framing,
with a stated scope and the same role as a relevant base pattern. It is usable immediately;
manual inclusion in the base framework or skill is a separate maintenance decision.

**Need.** An intended operation or outcome, expressed without prematurely choosing its mechanism.
Retain the distinctions that could change suitability: relevant inputs, outputs, scope, guarantees,
effects, failure behavior and workload. A phrase such as "validation" locates a topic but is
usually too broad to establish a match.

**Codebase opportunity.** A concrete responsibility, operation, related footprint or credible
functional gap worth investigating. It has a stable identity, evidence and constraints. A useful
opportunity need not establish a design violation or already have a known library replacement.

**Library opportunity type.** A reusable account of a focused library capability or composition,
the need it can serve, recognizable implementation shapes, mechanisms and conditions. A type
generalizes a researched opportunity without generalizing away consequential semantic limits.

**Applicability assessment.** A contextual judgment connecting a codebase opportunity to one or
more library types. It explains which promises can be discharged, remaining obligations, local
prerequisites and uncertainty. Capability existence, contextual fit and comparative superiority
are different claims.

**Comparative judgment.** A reasoned recommendation among complete options for an opportunity
or coherent group. It can select library functionality, composition, existing code or deliberate
custom work; it can also reject a premise or retain an unresolved choice.

## Recognition dimensions

The common patterns explain shapes of potential leverage. The following dimensions help locate
and describe opportunities without requiring tags on every record.

Read the shared additional-pattern output with the base framework. Assess its sufficiency during
codebase identification and again when comparing opportunities with library functionality.
When their interaction reveals an omitted framing, record or refine an additional pattern and
reconsider affected analysis. Comparative review can do the same. A useful inquiry may require
no additions; pattern names must not constrain which opportunities can be investigated.

- **Concern:** data integrity and modeling; collections and computation; algorithms; text and
  formats; time; I/O; networking; resilience; concurrency; persistence; application structure;
  cross-cutting operations; security and identity; engineering support; domain-specific work.
- **Relationship:** reinvention, under-use, fragmentation, friction, historical drift or a gap.
- **Altitude:** expression, function, component, subsystem or architecture. Footprint directs
  investigation and integration reasoning; it does not determine value.
- **Capability shape:** call, type, declaration, extension, managed resource, engine, tooling or
  a model adopted for a responsibility.
- **Fit:** semantics, runtime/version/build, execution model, data shape and scale, ordering,
  precision, identity, effects, resource lifetime, failures, observability, integration and change.

## Identity and references

Use stable codebase IDs such as `CBO-001` with meaningful titles. Never reuse a retired ID;
consult the account's Git history when allocating after retirement. Give library types namespaced
handles such as `example-library/selective-access`. Review sections retain the codebase IDs;
introduce a separate recommendation identity only when a group needs one.

Additional output patterns use stable IDs such as `LOP-X001`, distinct from base `LOP-01` IDs.
Keep one primary definition in the framework-bound shared output, created with its first useful
addition. Assessment records cite that definition. Preserve provenance and an ID mapping if the
operator later selects a pattern for promotion; never silently rename prior references.

One opportunity or type has one primary home. Patterns and concern labels provide secondary
routes. A split or merge preserves predecessor references and its rationale in Git. Handles
survive changes in document grouping; update live links when moving their homes.

Cite consumed publication revisions and anchors for mutable accounts, along with the actual
source or library realization inspected. Keep enough premise in the consuming record to make
its argument readable, and link to full supporting analysis. A short summary with a citation
does not create another editable authority over that analysis.

## Baselines, evidence and conclusions

Each collection states its inspected scope, date, source state or library versions, included
dirty changes and relevant criteria edition. A publication commit differs from the source
baseline. For partial refreshes, distinguish newly examined material from inherited claims with
their original dates and applicability limits. An empty scaffold establishes no assessment.
Identify the consumed base edition and additional-pattern output revision with this same baseline.
An addition changes the available guidance; it does not establish that older work was reconsidered.

Use the host project's evidence vocabulary. Here, `Proposed` labels an intended
application; `Interface-checked` identifies an inspected mechanism; `Implemented`, `Tested` and
`Measured` retain their specific scopes and evidence. Label distinct claims separately: inspected
library support does not make the recommended application tested. Quantitative claims require
attributable measurements; static reasoning can support a qualitative structural comparison.

Explain whether a candidate fits, fits with conditions, is ruled out for this context or remains
unsettled. These are assessment conclusions, not another evidence ladder. Name the premise that
could change them. Missing research is unknown, and ruling out one route does not prove the
library has no other suitable capability.

## Ownership and retention

- The codebase audit owns current opportunities. The library assessment owns reusable types and
  contextual fit. The review owns comparative choices. Accepted plans own scheduled work and
  closure evidence; link to them without copying mutable execution status.
- Codebase opportunities retire when their underlying relevance ends on evidence. Rejected
  candidates and accepted recommendations alone do not resolve them.
- Library types accumulate useful knowledge. Keep a sound type when it has no current match.
  Correct or merge misleading/duplicate analysis; retire obsolete content deliberately, preserving
  meaningful supported-version distinctions and useful lessons.
- Useful additional patterns likewise survive retirement of their original occurrences. Any of
  the three skills can discover or refine them in the shared output. Maintain one definition,
  reconcile related patterns and preserve references when correcting, merging or promoting them.
- Contextual matches retire with their relevance. Reconcile incoming links before removing an
  opportunity. Preserve useful provenance through its publication revision, original path and
  anchor; keep the reusable type independent of that old record.
- Current accounts are edited in place. Git holds history; keep current baselines, limitations
  and useful revisit questions rather than a growing pass diary or mandatory archive tree.

Collection ownership identifies the primary writer and authority. A coordinator can arrange
cross-collection corrections and publish a coherent refresh within authorized scope. Independent
agents preserve their own evidence and communicate consequential corrections promptly; finishing
a review need not wait for another scheduled pass. Never silently relabel a source conclusion.

Coordinate the shared additional-pattern output in the same way. The discovering pass publishes
its useful additions and collection entry pages route to that account. New pattern definitions
belong in outputs; discovering agents leave base framework and skill edits to separately selected
manual promotion or maintenance. All stages can use an output pattern before that decision.

## Coordination and boundaries

Brief useful outcomes, source/input baselines, scope and permitted writes. Separate assignments
by coherent questions and reconcile shared assumptions and material disagreements. Use a single
writer for shared indexes when work is concurrent, under the host project's isolation rules.

These skills assess and recommend. They do not authorize installation, dependency changes,
product edits, accepted requirements or implementation-plan changes. Apply the host's existing
decision and review routes when selected recommendations proceed. Use targeted probes only when
they settle meaningful uncertainty and follow the host's evidence and execution rules.

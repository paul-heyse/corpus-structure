---
id: ADR-0081
title: Compose immutable analysis layers over an exact published document
status: accepted
date: 2026-11-10
supersedes: []
superseded-by: null
design: [§B1, §B2, §B4, §B5]
evidence: Proposed
revisit: A required layer or consumer cannot preserve exact source, choice or publication standing through these contracts.
---

## Context

The operator selected the enriched-document target and authorized TC-00–02 execution on
2026-11-10. Existing native document/source-view custody and private observation/contribution
operations provide the foundation, but finite frame/cue reports cannot express all required
operators, binders, overlapping memberships and correlated alternatives. D1/D2 own those
meanings, D3 their physical realization, D4 production, D6 lifecycle and D8 reads.
The [entry target review](../design_review/reviews/design_review_text-characterization-entry_2026-11-10.md)
accepts the proposed foundation without a source/admission rule reversal. Implementation and
qualification remain with the [TC coordinator](../plans/text-characterization_2026-11-10.md).

## Options

1. Add arbitrary analysis JSON to current reports and reconstruct meanings in consumers. This
   is a small initial write but duplicates interpretation and makes group/source queries decode
   broad payloads. It cannot supply a sufficient typed native endpoint/choice contract.
2. Mutate a latest document, or copy the complete source into every layer. Both simplify local
   navigation at the cost of mixed revisions or duplicated custody and full-book materialization.
3. Introduce a separate graph service or framework. Edge storage is useful, but no current
   requirement warrants another publication, recovery, identity and operational lifecycle.
4. Compose immutable canonical layer/view products over the existing document, with generated
   indexed relational projections and protected task completion (selected). PostgreSQL and
   SQLAlchemy retain transactional/set processing; current release and source owners remain
   authoritative. Compact payloads plus explicit dependencies serve bounded reads and export.

## Decision

**Proposed accepted target.** The base is the full exact `PublishedDocumentBinding`, including
original product, placement and producer release. SourceViews are scoped projections beneath it.
Analysis layers and composed views use the generic `ProductReference` triple, independent of
physical row identity. Internal annotation/member/term/choice IDs are local to a layer and
externally qualified by its pin; canonical payloads never contain their own final digest.
Source occurrence identity binds base/projection and ordered real native/projection coordinates,
independently of the analysis. Equal text does not merge occurrences or parallel relationships.

A trusted `characterization.yaml` module is explicitly acquired, reserved and archived through
the existing release route. Its typed model and operations govern source occurrences, annotations,
membership/roles, terms, binders/operators, choices/dependencies and per-family coverage. Provider
scheme, released witnessed construction and private contextual proposal retain distinct bases.
Semantic disjunction is not analytical uncertainty. Unsupported/unknown/failed/partial and
successful empty are distinct outcomes. A view cannot advertise a family more strongly than its
selected evidence permits. Models and rules create new immutable layers when dependencies change.

`physical.yaml` owns stored canonical products and queryable relationship projections; reads are
derived from those declarations. Native protected completion checks payload/projection agreement,
exact source placement, admitted producer and inputs, local/reference identity, term/choice/source
closure and released mechanical support constraints before coherent visibility. It does not repeat
linguistic recognition. Existing run/task/attempt/holder fencing and original terminal task outcome
correspondence remain intact. A valid published report can retain a failed family and useful
siblings; actual task failure is not silently converted into successful layer completion.

Publication here means immutable **private analysis**, never knowledge admission. Consolidation
and declared admission policy remain the only route to stronger standing. Preparation/inference
occurs outside publication locks. Source and independently useful settled layers survive later
failure under their actual outcomes; no mutable latest selector mixes revisions.

Pin-native readers select indexed memberships in sets before hydrating necessary source/native
items and semantic dependencies. They preserve complete group membership and outside-selection
references, plus independent work/output limits and continuation pins. Detached export streams
an exact settled view closure with original inventories/statuses; whole-run completion is not a
prerequisite and is not inferred. Shared terms serialize once by ID; neither reads nor replay
rerun NLP or rederive meaning. Source-only view composition is a real released production method
over authentic document pins. Test-only independently authored layers enter via admitted test
producers and protected completion, without an ordinary arbitrary-layer upload port.

## Consequences

FP-01–07 and CI-01–06/08/10–13 favor one source authority, typed attributed analyses and complete
pins. Indexed set selection, compact shared payloads and streaming avoid repeated full-document
copies and per-fragment round trips (H5/8/15/16/23/27). Native projection and source validation
adds purposeful publication work; bounded reads can reuse immutable validity premises while
preserving trust-boundary authentication. These are qualitative expectations, not measurements.

The new target requires generated contracts, native guards/projections and real reader/export
integration. Independent semantic expectations and native tampering/stale-attempt controls remain
necessary qualification work. TC-03 onward linguistic production and TC-09 policy/consumer migration
are not delivered or accepted as implementation by this decision. Existing source/admission rules
are preserved; any actual conflicting rule must receive explicit disposition before reliance.
Acceptance records the architecture in force, not implementation, tests, adoption or finding closure.

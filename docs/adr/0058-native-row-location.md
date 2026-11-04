---
id: ADR-0058
title: Separate native row location from quoted row labels
status: accepted
date: 2026-11-04
supersedes: []
superseded-by: null
design: [§B1, §B5]
evidence: Proposed
revisit: A consumer needs independently projected row extents, or pinned cell geometry cannot authenticate structural row membership.
---

## Context

The M1 statistics table contract required a literal `row_identity`. The actual retained table
has valid native row/cell geometry but no marked row-header cells. Requiring a quoted label for
every cell confuses structural location with author content. The existing required native table
and cell addresses already identify the source cell and its native row extent. They establish
neither global entity identity nor the scientific meaning of a row.

Read-only preparation and assembly in the M1 evidence show182eligible cells in26bounded contexts.
There are76blank data cells; only five complete data rows have no blanks. These observations
motivate a model correction, not a claim of accurate reading or accepted table assertions.
D1 owns the distinction; the M1 coordinator owns implementation and qualification.

## Options

1. Keep the required literal and retain unresolved candidates. Safe under the old contract, but
   excludes faithfully located cells when the source has no quoted row label. A missing parser
   flag also cannot decide whether an author label exists.
2. Copy each complete row's literal vector into every cell reading. Rejected: repeats data,
   couples cell work to wide rows and cannot faithfully represent the observed blank positions
   through nonempty literal spans. Dropping blanks or inserting synthetic strings changes meaning.
3. Use existing native table/cell custody for structural row location; record quoted labels as
   a distinct role. Selected. It reuses authenticated source geometry without another row store,
   invented pointer or redundant persisted extent scalar.

## Decision

The statistics table reading keeps required native `table` and `cell` roles. Their exact pinned
cell supplies structural row membership. Replace required literal `row_identity` with literal
`row_label`. The label is meaning-changing but need not be present: honest inspected `unstated`
or `inapplicable` states are possible; `unresolved` still prevents accepted whole readings.

Explicit native row-header paths can supply separately located quoted labels. A missing
`row_header` flag does not establish source absence. Native-only assembly retains that unknown;
actual independently attributed model proposals can supply candidate alternatives under the
existing inspection/value-reading policy. No first-column guess, fabricated `row N` literal or
implicit global identity is introduced. Blank values, missing column headers, units and note
attachment retain their separate obligations.

Version the domain/reference contract before fresh authoring. Keep native table+cell occurrence
membership unchanged. Old records retain their released role meaning; no reference payload or
calibration membership is rebound. The generic projection ABI can remain2 because its roles are
release-derived. All five family quality gates and exact evidence requirements remain unchanged.

## Consequences

Consumers obtain row geometry through the existing native cell address and treat a quoted label
as source content. New records and references use `row_label`; logical solver variables named
`row_identity` remain decisions in their declared model, not domain-field aliases.

The accepted target remains Proposed until implemented and verified. This decision grants no
row-label absence, table fidelity, calibration or release claim. M1-02/08/13/14 and the coordinator
finding for the row-label correction retain current implementation/qualification state.

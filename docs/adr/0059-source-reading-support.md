---
id: ADR-0059
title: Scope M1 support reports to attributed source-reading facts
status: accepted
date: 2026-11-04
supersedes: []
superseded-by: null
design: [§B1, §B5]
evidence: Proposed
revisit: A domain supplies a released scientific proposition projection or needs a named cross-record comparison model.
---

## Context

M1 promised qualified corpus support/opposition reporting through existing owners. ADR-0057
accepts source-reading field assertions, not arbitrary scientific propositions inferred from
quoted text. A positive metadata assertion says that a reading has a field; it does not endorse
that field's quoted scientific statement. Author polarity also cannot supply opposition without
a proposition identity and qualification comparison policy. Predicate quotes may include negation.

The implemented ordinary fact/support/evidence relations, pinned record projection and native
source custody already supply useful attribution. No released scientific proposition projection
or opposition relation was identified in the current M1 owner. D5 owns interpretation and report
meaning; D8 owns presentation and limits. The M1 coordinator records the target amendment.

## Options

1. Reuse metadata-fact polarity or author polarity as scientific support/opposition. Rejected:
   changes semantic authority, can double-negate quoted predicates, and merges unaligned subjects,
   conditions or attributions. Counts would imply a comparison model that does not exist.
2. Defer all support reporting. Rejected: hides useful existing fact/support/native-source custody
   and leaves consumers reconstructing provenance independently.
3. Report exact pinned source-reading field support and explicitly expose unmodeled scientific
   comparison. Selected. Reuse common query and custody owners without new persistence or a
   second interpretation/comparison engine.

## Decision

Implement `source-reading-support-1`: a ledger under the existing completed-result binding,
with reading/admission, field assertions, their actual support occurrences/evidence/citation
roles and declared assessments. Retain alternatives separately. Supporting a field reading does
not mean endorsing the quoted proposition. Author modality/polarity, reading confidence and source
reliability remain distinct. Known citation identities are retained; missing lineage stays unknown.
Repeated windows or equal strings do not establish independent corroboration.

`scientific_support_opposition` has availability `unmodeled` and a reason when there is no released
scientific proposition projection. An empty opposition list or zero count cannot represent that
state. Do not synthesize a contradiction relation, treat alternatives as opposing scientific
claims, or add literal-agreement grouping without a separately declared comparison contract.

The M1 report promise is amended to this source-reading boundary. Broader scientific comparison
is explicitly unimplemented follow-on scope, with a released proposition/identity/qualification/
opposition projection as its trigger. This amendment does not close that broader capability.
It changes none of the five family reading-quality, calibration, evidence or release gates.

Use one domain report for query, CLI, MCP and export. Project and hydrate bounded relation sets,
not one explanation request per field. Ordinary pages retain actual producer coverage and errors;
large raw parse/annotation diagnostics are an explicit bounded request, with availability and
inclusion distinguished. Retained report identity remains pinned when raw details are deferred.

## Consequences

Consumers gain useful, truthful attribution without a new store, ledger register or corpus-truth
probability model. Scientific support/opposition remains visible as unmodeled rather than falsely
complete. A later proposition adapter must preserve located source mappings, scoped identity and
qualification compatibility before that meaning can be reported.

This accepted target remains Proposed until the adapter and its transport/native journeys pass.
M1-12/14/15 in the existing coordinator own implementation, qualification and the explicit
follow-on boundary. No source-quality or scientific-consensus claim follows from this decision.

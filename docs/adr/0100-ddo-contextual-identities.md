---
id: ADR-0100
title: Qualified subject context governs DDO request and product identity
status: accepted
date: 2026-11-13
supersedes: []
superseded-by: null
design: [§B1, §B4, §B5]
evidence: Proposed
revisit: A supported consumer needs portable cross-project sharing or subject qualification beyond the declared source and analyzed scope.
---

## Context

DDO-CA-05 found that frozen demands admit identical local subjects in different original-source
or analyzed contexts, while request keys omit that qualification. Native attachment safely refuses
the second context. Product publication has the same collision for equal-body outputs. The
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md#completion-audit--2026-11-13)
owns implementation and qualification; ADR-0092/0093 retain their governing model/support decisions.

## Options

1. Require callers to invent globally qualified local subject strings. This is superficially
simple but duplicates native custody facts and leaves no enforced correspondence.
2. Salt only request keys with context. Publication still collides; hiding context in parameters
or trust evidence also obscures semantic authority.
3. Carry one explicit immutable subject context through binding, request and publication.
Selected. It adds a shared projection but makes native authentication and independent vectors
local and prevents different consumers inventing qualification rules.

## Decision

Current DDO bindings carry explicit project scope, local subject, original source and analyzed
scope in an immutable SubjectContext. Canonical request and native product identity include that
same context. Native attachment reconstructs it from the authenticated demand and obligation;
publication uses the authenticated request/source context. Local subject headers remain available
for display and association. Trust, arbitrary runtime provenance and admission episodes do not
become context salts. Existing tagged semantic encoding remains version 1; the required meaning
field changes keys without changing primitive encoding.

Frozen historical SQL/model/archive interpretations retain their old identities. Current native
admission requires complete context without an old-key fallback. Pure historical identity helpers
do not authorize current contextual publication. No retained live data is rewritten here.

## Consequences

Two scopes or originals sharing a local name can coexist through request attachment and equal-body
publication. Project qualification follows the existing native custody namespace; cross-project
sharing would need an explicit admitted representation rather than accidental digest collision.
Affected Python/native constructors and independent vectors must migrate together. Normal frozen
forward authoring supplies the new native projection; persistent adoption remains DDO-11.
This decision accepts the contract, not verified implementation or closure of DDO-CA-05.

## Amendments

2026-11-13: The implementation makes the existing JSONB analyzed-scope meaning explicit:
JSON numbers use canonical decimal meaning; boolean/string/null and structural distinctions
remain. A context-only encoder preserves that interpretation without changing typed operation
parameter or product-body numerical semantics. This clarifies the existing scope contract,
not a different semantic role for subject context.

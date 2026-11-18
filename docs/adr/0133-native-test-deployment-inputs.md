---
id: ADR-0133
title: Key native test deployments by effective construction and policy
status: accepted
date: 2026-11-18
supersedes: [ADR-0101]
superseded-by: null
design: [§B4]
evidence: Proposed
revisit: Clone replay cannot preserve a required native policy, or the selected reuse verification misses a result-affecting deployment input.
---

## Context

Focused runs reuse a verified native head, but the key currently fingerprints a migration
tree the build does not execute. The operator accepted RC07 and RC10 in the
[test-domain coordinator](../plans/test-domain-model-and-execution_2026-11-17.md#rule-changes).
This decision corrects the inputs to reuse and permits temporary SQL expression checks on the
infrastructure rollback route.

## Options

1. Continue per-process heads: simple but repeats the full chain and contends across workers.
2. Keyed heads with verified reuse and claim-specific clones: selected. It amortizes deployment
   without replacing actual policy replay or independent cold deployment controls.
3. Reuse without verification, or daily verification: weaker stale-input detection, rejected.
4. Require a full semantic head for driver-only tests: repeats unrelated preparation and needs
   unnecessary semantic prerequisites. Use extension-ready infrastructure instead.

## Decision

PgAdmin remains the one authenticated lifecycle owner. Narrowed runs reuse a sealed head under
its deployment key; qualification uses a fresh run-private head. Publication seals a client-free
build and renames it under distinct build/usage leases, retaining acknowledged nonce/OID disposal
authority. Retain the newest three reusable heads by OID when unleased; never force-drop or gain
backend termination rights. Unauthenticated residue is not disposal authority.

Resolve the migration chain through the production upgrade's `semantic.migrations.ALEMBIC_DIR`.
Include the chain files and executed upgrade bodies, including their function-level imports.
Follow package imports at module level; reach build-time policy and construction work from the
construction entry. Use verified revision-pinned content digests for pinned artifacts and
hash bytes for unpinned artifacts. Size and modification time carry no key authority. Keep
lockfile, interpreter and server/template identity. Observe provisioning already applied to
the server through effective policy, including role identities, capability flags, and relevant
membership identities and options. Provisioning source alone cannot establish applied policy.
Cross-run reuse is verified
once per consuming process on its first useful clone, before effects, against production's frozen
revision catalog expectations. This is not equality with a new build. Heads freshly built in the
same run retain their exemption. A failed check discards that clone, records the deployment-key
gap, and obtains a run-private replacement before retry. Verification never requires a dedicated
session clone. Explicit-revision expectations load only their inherited artifact after validating
revision metadata; historical-discovery callers retain their historical route.

Policy capture/replay/equivalence, real purpose authentication and unavailable-replay refusal
remain per clone. Use read-only or rolled-back shared semantic clones only for compatible claims;
rollback consumers receive connections and a forced-read-only reader engine, not a writable
shared semantic engine. Committing, racing, cancellation, notification and separate-login
visibility claims retain their required fresh committed isolation.

Driver-only tests use explicitly named infrastructure clones from extension-ready cs_template,
shared for connection exercises and rolled-back SQL expression checks that reference no semantic
object and install only temporary objects. Durable writes use isolated infrastructure clones.
Infrastructure acquires neither semantic deployment nor incidental semantic roles. Installed
semantic objects and actual semantic guards use the semantic read or rollback class applicable
to their claim. Cold bootstrap, CLI initialization and
historical migrations still execute the real chain. ADR-0031's native admission, restricted
writer/admitter TEMP and protected publisher workspaces remain unchanged.

## Consequences

Native preparations follow their validity scope. Keying, verification and lease coordination
remain necessary but eliminate unrelated acquisition. New test-only pgTAP installation must not
change production extension prerequisites or substitute for actual-purpose observations.
TDM-06 and TDM-16 own implementation and scoped evidence; TDM-18 owns integrated qualification.
A real first-use comparison remains the authority for accepting frozen heads.

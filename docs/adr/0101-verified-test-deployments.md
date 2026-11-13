---
id: ADR-0101
title: Reuse verified native test deployments and choose isolation by claim
status: accepted
date: 2026-11-13
supersedes: [ADR-0032]
superseded-by: null
design: [§B4]
evidence: Proposed
revisit: Clone replay cannot preserve a required native policy, or the selected reuse verification misses a result-affecting deployment input.
---

## Context

Repeated frozen-head migration per pytest process no longer fits focused or full development
runs. The operator accepted RC01/RC05 and I01/I02/I10 in the
[test-system coordinator](../plans/test-system-target-design_2026-11-13.md).
Current session-cloned deployment remains implemented; this record selects its replacement.

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

The key covers migration source, frozen-artifact metadata, module-level package import closure,
the actual deployment construction dependencies, lockfile/interpreter and server/template/role
identity. The coordinator's lifecycle companion owns exact inputs. Cross-run reuse is verified
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
shared only for connection exercises without durable effects; durable writes use isolated
infrastructure clones. They acquire neither semantic deployment nor incidental semantic roles.
Actual semantic guards still use semantic fixtures. Cold bootstrap, CLI initialization and
historical migrations still execute the real chain. ADR-0031's native admission, restricted
writer/admitter TEMP and protected publisher workspaces remain unchanged.

## Consequences

Native preparations follow their validity scope. Keying, verification and lease coordination
remain necessary but eliminate unrelated acquisition. New test-only pgTAP installation must not
change production extension prerequisites or substitute for actual-purpose observations.
Implementation and verified closure remain with TS-01/02/05/08 and TS-23 in the coordinator;
acceptance establishes neither measured speedup nor successful qualification.

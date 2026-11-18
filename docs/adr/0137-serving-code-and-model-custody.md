---
id: ADR-0137
title: Separate serving code custody from model source identity
status: accepted
date: 2026-11-18
supersedes: [ADR-0124]
superseded-by: null
design: [§B3]
evidence: Proposed
revisit: A supported serving loader or filesystem cannot establish imported-code custody and conservative metadata-based invalidation.
---

## Context

PE-S06/PE-RC08 changes the serving identity guarantee from repeated comparison with disk
content to an identity naming authenticated imported code, with metadata invalidation and
content confirmation. The accepted execution plan already establishes this target. D8 and §B3
own the affected serving contract. No earlier ADR specifies the replaced disk-check guarantee.

## Options

1. Rehash disk sources for every request. This repeats invariant work and by itself does not
   establish that those bytes are the code the process imported.
2. Cache an identity without drift checks. This avoids repeated reads but silently tolerates
   unsupported disk and module changes.
3. Bind identity to authenticated imported sources and confirm content when metadata changes
   (selected). This uses the shared file-custody primitive, while making its local-filesystem
   assumptions explicit. It avoids a separate watcher or filesystem service.

## Decision

Derive serving implementation identity from the declared entry points and authenticated
imported-code closure, with result-affecting library versions and the exact query and profile
contracts. Preserve shared metadata-based detection and content confirmation for Python file
and module drift. Unsupported changed code requires restart. An incomplete determining
closure withholds reuse pending complete evidence.

Compose each immutable capture of named model sources once. Hold lazy projections with their
own identities. A new capture yields a new compiled model on the next observed request and
older explicitly pinned captures remain independently held. Cache wrapper versions and codecs
belong to storage compatibility; query and ordering behavior govern continuation identity.
Native read authority is acquired whenever the read contract requires it.

The identity names running code. Drift detection depends on observable metadata changes;
a content change preserving inode, size and both timestamps is outside this guarantee.
Ordinary unprivileged writes on the intended local filesystems update change time; a delayed
memory-mapped update is detected when a subsequent stat observes it. This does not establish
continuous monitoring or protection against a privileged attacker.

## Consequences

Serving avoids repeated full-source reads while retaining unsupported-edit refusal and exact
query/profile identity. Supported import paths must establish custody before identity is used;
unknown loader provenance cannot be treated as authentic. Implementation and targeted drift,
module replacement, equal-content refresh and pin controls remain open under
[PE-S06](../plans/declared-data-operations/interfaces-and-evaluation.md#pe-s06--serving-implementation-identity-pe-f09-g-pe-rc08).

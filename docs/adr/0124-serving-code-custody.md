---
id: ADR-0124
title: Serving identity names imported code and refuses detected drift
status: accepted
date: 2026-11-17
supersedes: []
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

Compute serving implementation identity once per process, query contract and source set from
source digests authenticated at import, first-use library versions, the query contract and
profile. Per request, check module identity and each source's device, inode, size, mtime_ns
and ctime_ns against authenticated custody. Rehash changed or racily clean records. Equal
bytes refresh metadata; changed bytes, modules loaded outside custody or a conflicting pinned
identity refuse with a restart instruction. Use the shared stat/read/digest/stat custody
implementation, rather than another serving-specific invalidation mechanism.

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

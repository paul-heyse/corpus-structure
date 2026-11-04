---
id: ADR-0056
title: Use persistent development storage with operator administration
status: accepted
date: 2026-11-04
supersedes: []
superseded-by: null
design: [§B4]
evidence: Implemented
revisit: The project enters a deployment phase requiring a different operator or tenancy boundary.
---

## Context

The operator explicitly directed that design-phase agents use the permissions needed for their
work and should not require disposable databases. Repeated temporary restores exposed avoidable
extension, object-owner and database-ACL setup friction. The dedicated local18/corpus cluster
already separates this project from the workstation's other PostgreSQL cluster.

## Options

1. Require each agent to create a temporary database and recreate permissions. Rejected for normal
   development: adds setup, repeated parsing/restoration and disposal without a required consumer.
2. Give application principals all administrative rights. Unnecessary: their normal operations
   already work, while maintenance has an explicit connection purpose.
3. Use persistent development storage and an adequately privileged operator. Selected.

## Decision

`corpus_structure_dev` on dedicated18/corpus, socket port5434, is the persistent default working
database. It retains source products, projects and development results across agent turns. The
operator login `paul` has SUPERUSER, CREATEDB and CREATEROLE on that dedicated cluster, so ordinary
maintenance, restore, ownership and migration work can run directly through maintenance credentials.
Provisioning preserves that development-administrator setup. Application read/write/admission/
evaluation/fitting roles retain the privileges for their intended operations.

`ci schema native-candidate` defaults to the configured working database, uses maintenance
credentials and always rolls back candidate preparation. Explicit alternate targets remain
available. System/template databases are excluded; fresh atomic output and exact native comparison
remain useful operation guarantees. A separate disposable authoring database is not required.

Use isolated test databases when a test's mutation or cross-session isolation actually requires
one. That test mechanism is not a general agent or functional-development prerequisite. No new
permission approval loop or database-disposal requirement follows from ordinary implementation.

## Consequences

Agents can work against retained real data and operate the database as intended. The existing
source archive was restored into the persistent working database at native106, retaining all11
selected source views; normal purpose connections were exercised. Legacy corpus_pdf_20261102
and its run6 remain available without an in-place migration. This database selection is a developer
workflow change, not M1 scientific result or default-release adoption.

D3 and agent instructions own the current workflow. M1 retains its functional, reference and
quality targets, with requirements refined as needed under the operator's design-phase direction.
Historical disposable-database evidence keeps its actual scope; it imposes no future workflow.

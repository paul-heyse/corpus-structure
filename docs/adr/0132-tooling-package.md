---
id: ADR-0132
title: Keep library-discovery tooling in a separate workspace package with its own CLI
status: accepted
date: 2026-11-17
supersedes: []
superseded-by: null
design: [§2]
evidence: Proposed
revisit: The tooling needs to mutate repository or database state, needs managed result custody, or is wanted outside this repository.
---

## Context

[ADR-0072](0072-library-led-discovery.md) added optional library-led discovery and declined to
build a package and source census first, with the revisit trigger "repeated briefings require the
same evidence extraction or routinely need stronger attribution than representative source
inspection can supply". The
[tooling review](../functional_reviews/library-discovery-tooling_2026-11-17.md) found both
halves met across four discovery accounts, and the operator accepted its direction on
2026-11-17. ADR-0072's decision already says to "consider dedicated automation when repeated
work establishes the need", so it stays in force unchanged.

Two things are newly chosen. The tooling needs a home, and it needs a command-line entry point.
[ADR-0069](0069-cli-operations-custody.md) makes installed `ci` the routine interface for
repository and product operations and places invocation artifacts under managed result custody.
The operator wants this tooling separate from the production package, which owns `ci`.

Current implementation: none. `tools/evidence` (ADR-0010) is the existing non-product workspace
member. The [plan series](../../tooling/docs/plans/library-discovery-tooling_2026-11-17.md) owns
the target and its packages.

## Options

1. **Commands under `ci`.** No new package or entry point, and existing output conventions apply
   directly. It places library-inspection code and its dependencies (Griffe extensions, a
   Markdown parser) inside the production package, which the operator ruled out, and it would
   put read-only inspections under managed result custody that has no consumer for them.
2. **An independent uv project under `tooling/`.** Fully outside product dependency resolution
   and usable from another repository. It duplicates pins for libraries the root lock already
   holds, and none of the existing lint, type, pin or test lanes would see it.
3. **A uv workspace member rooted at `tooling/` with its own console script.** One set of pins in
   the root lock; ruff, pyrefly, the pin check and the managed test route cover it after small
   configuration edits; the product never imports it. It is tied to this repository.

## Decision

Keep repository tooling that inspects third-party libraries in a separate, non-product uv
workspace member rooted at `tooling/`: distribution `corpus-tooling`, import package
`corpus_tooling`, console script `tooling`, with discovery commands under `tooling library`.
Later tooling of the same kind joins this package and CLI. Its plans live in
`tooling/docs/plans/`.

This is a scoped decision beside ADR-0069, which is unchanged: `ci` remains the routine
interface for repository and product operations. The `tooling` commands are read-only
inspections of dependency selection, installed distributions, library source and repository
source. They perform no product action and take no managed result custody. Each returns one
typed result on stdout; a durable copy is whatever the agent saves beside a library account or
in an evidence folder. A tooling command that would mutate repository or database state, or
that needs custody, is outside this decision and needs its own.

The product package does not import `corpus_tooling`, and `corpus_tooling` does not import the
product package. Conventions worth sharing with `ci` (the `--json` contract, per-call consoles)
are re-expressed in the tooling package.

## Consequences

Agents have two installed commands with different purposes; AGENTS.md's path table names both
homes. Tooling dependencies are resolved with the product and inherit the root's overrides.
The discovery guide and skill point to the commands once they exist.

One conditional package in the plan series (a version-to-version comparison) would download a
second copy of a library into a cache; it is not implemented, and it stays inside this decision
only because it changes no repository or environment state.

Acceptance records the decision. Implementation and verification remain with the plan series,
which owns the disposition of the review's O01–O10.

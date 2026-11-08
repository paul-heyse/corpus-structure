---
id: ADR-0071
title: Publish the checked documentation on GitHub Pages
status: accepted
date: 2026-11-08
supersedes: [ADR-0003]
superseded-by: null
design: [§2]
evidence: Implemented
revisit: Hosting requires a different public collection or documentation builds require product qualification.
---

## Context

A public visitor needs a stable route from the README to searchable documentation,
worked results and their evidence. The existing docs-only workflow produces a checked
static artifact. The operator approved publishing its existing authored collections on
GitHub Pages while keeping the ordinary artifact available. [GHV-05](../plans/github-visitor-experience/publication-and-rollout.md#GHV-05)

## Options

1. **Retain artifact delivery alone.** This preserves local and Actions verification
   but gives visitors no stable public entry point.
2. **Deploy the existing checked artifact through Pages.** Reuse the same source selection,
   publisher and checks, with a distinct deployment job and project prefix.
3. **Build a separate public site.** This would duplicate navigation and selection,
   with no second site needed for the approved publication scope.

## Decision

Use the existing mdBook, Pagefind and offline lychee pipeline. Markdown and its owning
documents remain authoritative. The site configuration owns publication selection,
ordering, URL settings and tool pins. Select authored evidence indexes explicitly and
link generated bundles at the source revision. Keep stable section IDs and Current
as the default search scope.

The documentation workflow checks and uploads one static artifact. Eligible successful
runs on `main` package those same files for Pages at `/corpus-structure/`. Deployment
uses the `github-pages` environment and its own permissions. The build needs neither
product infrastructure nor LFS hydration. The ordinary artifact remains available
if deployment fails.

## Consequences

The public site adds a stable route into source-linked output and the documentation
collections. Documentation qualification remains focused and separate from product
qualification. The plan records hosted and live results independently of local checks.

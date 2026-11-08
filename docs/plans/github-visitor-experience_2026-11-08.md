# GitHub visitor experience and Pages implementation

**Status · 2026-11-08. Complete.** This coordinator owns GHV-01–06, scheduled findings
and combined acceptance. It consumes the [functional review](../functional_reviews/github-visitor-experience_2026-11-08.md)
at `b8697ab5f` and the two-part ChatGPT Pro proposal named `github_view_improvement.md`,
identified by Git blob `2ce8a30811ce0d63f41d3296cc8291f62d08e627`. The draft is a
local authoring input. The crosswalk below retains its actionable scope for a clean
checkout.

## Outcome and decisions

An engineer arriving at the repository can tell what Corpus Structure produces, inspect
a real transformation back to its source, and choose between architecture, evaluation
and reproduction routes. The GitHub README and the existing documentation site use the
same committed examples and diagram. Source evidence and architecture owners retain
their respective authority. A visitor can follow the example without the product
environment, a model, or a database.

The operator confirmed two decisions on 2026-11-08.

- **GHV-R01 · Public deployment.** Supersede the artifact-only policy in
  [ADR-0003](../adr/0003-publish-docs-site.md). Deploy the checked existing documentation
  collections to GitHub Pages and retain the ordinary CI artifact. Preserve the current
  architecture, process, plan, review, and authored evidence routes. GHV-05 owns the
  superseding ADR and activation sequence.
- **GHV-R02 · Conditional adoption.** Schedule each follow-on investigation, record its
  decision, and implement options that satisfy their adoption criteria. The social
  preview is an explicit deliverable. Conditional additions have separate closure
  criteria from the first delivery.

## Foundations and execution fit

The review tested the publisher at `2147ac24a`. With LFS downloads disabled, its broad
evidence glob matched generated bundle READMEs stored as pointers. A temporary exclusion
revealed an ignored source-inventory link. With both workarounds the isolated build,
prefix build and desktop/mobile browser checks passed. The review also verified the
Dartmouth PDF hash and recorded the historical Reader query's release-compatibility
refusal. These receipts establish a feasible static route and two repair obligations.
At review time, live deployment and the new visitor interface were `not_run`.
[Publication evidence](../functional_reviews/github-visitor-experience_2026-11-08.md#O04) · [Reader and source evidence](../functional_reviews/github-visitor-experience_2026-11-08.md#O02)

Use existing publication selection, link transport, search scopes and last-good
artifact replacement. The workload is periodic Markdown and asset changes, with a
static read for each visitor. Generate images when their source changes and reuse
them in ordinary docs builds. Package one checked site per deploy and keep LFS
downloads, browsers, and native corpus work out of routine publication. Keep
source spans, typed links, and dated assessment distinctions in the examples.
These boundaries follow FP-04, FP-05, FP-07 and the heuristics for reusing valid
preparation and limiting repeated work. [Design principles](../design_review/design_principles/core/design-principles.md) · [Efficiency heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md)

## Execution queue

| Package and owner | Input and readiness | Closure |
| --- | --- | --- |
| [GHV-01](github-visitor-experience/publication-and-rollout.md#GHV-01) · Documentation publisher | Committed checkout with LFS disabled and review O04 | Authored evidence and stable links build identically in relevant hydrated and LFS-disabled checkouts. Both publication findings have closure evidence. |
| [GHV-02](github-visitor-experience/visitor-content-and-evidence.md#GHV-02) · README and documentation owners | Current status, architecture and evidence sources | Visitor-first entry routes, dated capability boundaries and a responsibility-based code map work in GitHub and the built site. |
| [GHV-03](github-visitor-experience/visitor-content-and-evidence.md#GHV-03) · Examples and evidence | Exact reviewed records and original PDF | Static citation, qualifier and uncertainty examples and the illustrative example are usable. Reproduction instructions and a bounded Reader/detached compatibility result are recorded. |
| [GHV-04](github-visitor-experience/visuals-and-follow-ons.md#GHV-04) · Visual sources and assets | Stable output labels from GHV-02/03 and reviewed tooling pins | One diagram source/SVG pair and one social template/PNG pair render reproducibly. Their actual consumers and accessibility are checked. |
| [GHV-05](github-visitor-experience/publication-and-rollout.md#GHV-05) · Publishing policy, CI and GitHub settings | GHV-01 qualification, initial visitor assets, superseding decision, authorized remote revision and settings access | The checked artifact is deployed from `main`, live journeys pass and About metadata, homepage and social preview are verified. |
| [GHV-06](github-visitor-experience/visuals-and-follow-ons.md#GHV-06) · Follow-on decisions | Representative core prose, examples and assets | Each option has an evidence-based disposition. Adopted additions are delivered and checked. Deferred options have a concrete revisit trigger. |

GHV-01 and GHV-02/03 can start independently. GHV-04 can prepare its layout and
rendering path while the content is refined. Integrate the README, primary example
and diagram together. About description and topics can accompany that delivery.
GHV-05 can prepare the ADR and workflow while GHV-01 is being repaired. Enable
deployment only after qualifying the actual artifact. GHV-06 can run after
representative content exists and can settle after public launch.

## Proposal coverage and findings

The first part of the draft provides the editorial target. The second gives enabling
mechanisms and an authoring workflow. The review supplies the evidence and adoption
conditions used when the two differ.

| Proposal content | Review and disposition |
| --- | --- |
| First part §§1–3 and §6 · Purpose, progressive enrichment, landing structure, capability table, demonstrated work, maturity | [O01](../functional_reviews/github-visitor-experience_2026-11-08.md#O01) → GHV-02. |
| First part §4 and second part §2 · Compact functional diagram, deeper illustration and statistical branch, D2, Mermaid, Excalidraw, Lucide, Playwright | [O03](../functional_reviews/github-visitor-experience_2026-11-08.md#O03), [O06](../functional_reviews/github-visitor-experience_2026-11-08.md#O06) → GHV-03/04 for required examples and assets, GHV-06 for optional tooling and embellishments. |
| First part §5 and §7 · Citation, qualification, uncertainty, evidence and reproduction; visitor paths and code-reading map | [O02](../functional_reviews/github-visitor-experience_2026-11-08.md#O02), [O04](../functional_reviews/github-visitor-experience_2026-11-08.md#O04) → GHV-02/03. Use plain Markdown as the common reading path. |
| First part §7 and second part §4 · Publish existing docs, Actions/Pages, repository settings | [O04](../functional_reviews/github-visitor-experience_2026-11-08.md#O04), [O05](../functional_reviews/github-visitor-experience_2026-11-08.md#O05) → GHV-01/05. |
| First part §§8–9 · About, topics, homepage, badges, attribution, social image and recorded walkthrough | [O05](../functional_reviews/github-visitor-experience_2026-11-08.md#O05), [O06](../functional_reviews/github-visitor-experience_2026-11-08.md#O06) → GHV-02/04/05, with the recording decided by GHV-06. |
| Second part §§1, 3 and 5 · Surface limits, editorial tooling, source/output layout, one regeneration command, acceptance | [O03](../functional_reviews/github-visitor-experience_2026-11-08.md#O03)–[O06](../functional_reviews/github-visitor-experience_2026-11-08.md#O06) → GHV-02/04/05 and the combined checks below. GHV-06 owns prose and Markdown tool adoption. |

| Item | Component | Consequence and intended correction | Disposition · dependency | Closure check |
| --- | --- | --- | --- | --- |
| GHV-F01 · O04 generated READMEs | Publisher selection | The recursive glob treats LFS pointers and generated payloads as authored chapters. Select authored indexes and nested reviews consistently. | Closed · GHV-01 | Both fixture forms stay linkable without becoming chapters. The clean hosted build passed. |
| GHV-F02 · O04 source inventory | Source-population evidence | A link to an ignored checkout file fails hosted link resolution. Explain the local input and retain the tracked reference. | Closed · GHV-01 | The corrected owner and tracked inventory link passed in the clean hosted build. |

The O02 historical Reader refusal is a constraint on GHV-03's optional native
inspection. The coordinator records the outcome of that investigation separately
from the two publication repairs.

## Qualification and handoff

Use the [repository review cadence](../design_review/design_principles/binding/corpus-structure.md#reviews-in-this-repository)
for the changed publication boundary and the assembled delivery. Check public
collection membership, source and assessment fidelity, and failure recovery. Run
`just docs-test` for publisher changes and `uv run ci docs check` after final
maintenance. Run the project-prefix build in a clean LFS-disabled checkout with
the same source used by hosted CI. Verify GitHub README rendering and the locally
served artifact at desktop and mobile sizes. Confirm live Pages navigation, search
scopes, evidence and asset links, hidden paths and About settings separately.
[Publishing checks and rollout](github-visitor-experience/publication-and-rollout.md#qualification)

The [acceptance record](#GHV-acceptance) distinguishes local, hosted and live checks.
The current checkpoint links here for package and finding disposition.

**Plan validation · 2026-11-08.** In an isolated LFS-disabled checkout of
`b8697ab5f` with the authored plan files, the project-prefix `scripts/docs.py check`
failed on GHV-F01, then on GHV-F02 after a temporary pointer README exclusion.
With both temporary workarounds, `uv run --no-sync ci docs check --json` and
the prefix check passed with 704 canonical pages. These are scoped publication
checks of the plan documents. GHV-01 still owns the actual repairs.


## Execution · 2026-11-08

The operator selected direct pushes and current stable publication, rendering, host
and Actions tooling. The workspace pytest/xdist hold, language pins and product
dependencies retain their existing scope. The refresh selects Pagefind 1.6.0,
D2 0.9.0, just 1.59.0, cargo-binstall 1.26.2, Ruff 0.17.4 and isolated Playwright
1.64.1 with Chromium 1248. mdBook 0.5.4, lychee 0.24.2, uv 0.13.7 and
gh 2.103.3 were already current. ADR-0071 governs the publication change.
Hosted PR execution is `not_run` under the operator's direct-push decision.

The [previous hosted run](https://github.com/paul-heyse/corpus-structure/actions/runs/42477372679)
failed fetching mdBook through cargo-binstall. GHV-05 now uses verified upstream
archives on hosted Linux x86-64, retaining the portable local bootstrap. A local
run of `just bootstrap-docs --hosted-bin-dir DIR` with the destination on PATH
passed with the same archive inputs and isolated pytest 9.1.1.

GHV-03 retried the [exact retained Reader query](../functional_reviews/github-visitor-experience_2026-11-08.md#O02).
It was blocked by `incompatible_query` on the producing release. The retained
run reports support the static example. The available contextual verification
bundles are for other selections, so the historical live read remains outside
the verified public walkthrough.

### GHV-06 dispositions

| Candidate | Disposition and revisit condition |
| --- | --- |
| Rendered example card | Deferred after comparing the source, edge, witness and receipt in the four-row Markdown example. All four are visible in reading order and their evidence links remain actionable. Revisit when a case benefits from visual correspondence that text cannot convey. |
| Lucide | Deferred. The numbered operation names and distinct output labels already identify each stage. Revisit if a repeated object needs an icon across several figures. |
| Recorded walkthrough | Deferred. The exact historical Reader query was refused and the useful public journey consists of static links. Revisit with a verified interactive read that shows a distinct operation. |
| Vale | Deferred. The editorial pass aligned naming across the README, architecture, examples and assets. Revisit if inconsistent names recur after edits. |
| Markdownlint | Deferred. The existing publisher and link checks cover the observed Markdown failures. Revisit for recurring formatting defects those checks miss. |
| D2 upgrade | Adopted in GHV-04 at 0.9.0 under the current-tooling decision. |
| Mermaid and Mermaid CLI | Deferred. One portable asset serves both surfaces. Revisit for a distinct small GitHub diagram or recurring cross-surface export. |
| Excalidraw | Deferred until there is a distinct interactive authoring use. |
| Generated illustration | Deferred. The maintained diagram, labeled policy illustration and social preview cover the identified editorial uses. Revisit for a distinct illustration requirement. |

<a id="GHV-acceptance"></a>

## Acceptance · 2026-11-08

GHV-01–06 closed for the approved visitor and publishing scope. The historical
Reader check remains `blocked` by the producing release compatibility limit
documented above. The published static walkthrough reaches the retained
evidence and original pages.

- `uv run ci doctor`, `uv run ci check --only deps --json`, `actionlint .github/workflows/docs.yml`,
  and `just turn-end` passed. Turn-end used rustc 1.101.0-nightly (2d20b42b8).
- `just docs-test` passed 45 tests in a clean shallow checkout with its temporary
  directory inside the checkout. It exercises both generated README forms and
  checksum refusal. `uv run --no-sync ci docs check --json` and the clean
  `scripts/docs.py check --base-url /corpus-structure/` passed with 702 canonical
  pages. The artifact retained the required hidden paths and contained no
  symlinks or generated raw evidence payloads.
- `just docs-visuals` passed with D2 0.9.0 and Playwright 1.64.1. The final SVG
  renders inside its link in mdBook and GitHub. The uploaded social preview
  was verified through GitHub's Open Graph URL and matched the committed
  1280 × 640 PNG byte for byte.
- The [hosted run for `c3832fae6`](https://github.com/paul-heyse/corpus-structure/actions/runs/42481768331)
  passed bootstrap, docs checks, both artifact uploads and deployment.
  Chromium verified the [live project site](https://paul-heyse.github.io/corpus-structure/)
  at 1280 × 800 and 390 × 844, including the source-linked citation, SVG,
  Current, Reference and Everything search, and hidden documentation paths.
  The README diagram and badge were visible on GitHub at both widths. The badge
  reports passing. The About description, seven selected topics, and homepage
  were checked through the repository API. Hosted PR execution was `not_run`.
- The earlier [isolated pytest failure](https://github.com/paul-heyse/corpus-structure/actions/runs/42480850068)
  and [shallow fixture failure](https://github.com/paul-heyse/corpus-structure/actions/runs/42481002593)
  remain in the hosted record. The final search waits for Pagefind's first
  index and filter load after the live browser check exposed an intermittent
  empty first query.

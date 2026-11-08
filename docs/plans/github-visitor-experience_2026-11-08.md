# GitHub visitor experience and Pages implementation

**Status · 2026-11-08. GHV-01–06 complete and live. GHV-07–11 proposed.**
This coordinator owns the [follow-on increment](#GHV-follow-on), the original
rollout and the combined acceptance of each increment. It consumes the [functional review](../functional_reviews/github-visitor-experience_2026-11-08.md)
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

## Packages and audited state

| Package and owner | Input and readiness | Closure |
| --- | --- | --- |
| [GHV-01](github-visitor-experience/publication-and-rollout.md#GHV-01) · Documentation publisher | Committed checkout with LFS disabled and review O04 | Authored evidence and stable links build identically in relevant hydrated and LFS-disabled checkouts. Both publication findings have closure evidence. |
| [GHV-02](github-visitor-experience/visitor-content-and-evidence.md#GHV-02) · README and documentation owners | Current status, architecture and evidence sources | Visitor-first entry routes, dated capability boundaries and a responsibility-based code map work in GitHub and the built site. |
| [GHV-03](github-visitor-experience/visitor-content-and-evidence.md#GHV-03) · Examples and evidence | Exact reviewed records and original PDF | Citation, qualifier, X/Z, illustration and reproduction boundary verified. |
| [GHV-04](github-visitor-experience/visuals-and-follow-ons.md#GHV-04) · Visual sources and assets | Stable output labels from GHV-02/03 and reviewed tooling pins | One diagram source/SVG pair and one social template/PNG pair render reproducibly. Their actual consumers and accessibility are checked. |
| [GHV-05](github-visitor-experience/publication-and-rollout.md#GHV-05) · Publishing policy, CI and GitHub settings | GHV-01 qualification, initial visitor assets, superseding decision, authorized remote revision and settings access | Deployment and settings verified. The assembled review accepted the serialized release scope. |
| [GHV-06](github-visitor-experience/visuals-and-follow-ons.md#GHV-06) · Follow-on decisions | Representative core prose, examples and assets | D2 adopted. The completed comparison supports deferring the card, icons and recording. |

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
| GHV-F03 · O02 uncertainty example | GHV-03 public examples | The original example lacked separate X and Z receipts. | Closed · GHV-03 | The published example shows the rank-one X candidate and zero selected edges, then links the separate witnessed Z replay. The live links and both receipts passed anonymous verification. [X control](../design_review/evidence/2026-11-06_wce-completion-repair/composition/native-retained004/false-bridge-control.json) · [Z scoped replay](../design_review/evidence/2026-11-07_nce06-closeout/development-results.json) |
| GHV-F04 · O06 follow-on evidence | GHV-06 visual and editorial owners | The original dispositions lacked a visual treatment and storyboard comparison. | Closed · GHV-06 | The two viewport comparisons and exact citation storyboard support deferral. [Pilot and disposition evidence](../design_review/evidence/2026-11-08_github-visitor-follow-ons/README.md) |
| GHV-F05 · O04 publishing review cadence | GHV-05 publication owner | The original release missed the pre-activation review. | Closed · GHV-05 | The post-launch assembled design/target review accepted the boundary for one release at a time before the corrective rollout. The timing miss remains recorded. [Independent review](../design_review/reviews/design_review_github-pages-publication_2026-11-08.md) |

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

The [card and storyboard comparison](../design_review/evidence/2026-11-08_github-visitor-follow-ons/README.md)
records the tested treatments and evidence journey.

| Candidate | Disposition and revisit condition |
| --- | --- |
| Rendered example card | Deferred. The card compacted the mobile layout. Both treatments kept the cue, result, witness and all three links easy to locate. Revisit if a denser example becomes hard to scan. |
| Lucide | Deferred. The comparison surfaced no stage distinction requiring an icon. Revisit if the shared diagram gains operations that readers cannot distinguish from their names and outputs. |
| Recorded walkthrough | Deferred. The run 327 storyboard repeated the static cue, target and witness links. Revisit when a verified interaction adds a distinct inspection step. |
| Vale | Deferred. The editorial pass aligned naming across the README, architecture, examples and assets. Revisit if inconsistent names recur after edits. |
| Markdownlint | Deferred. The existing publisher and link checks cover the observed Markdown failures. Revisit for recurring formatting defects those checks miss. |
| D2 upgrade | Adopted in GHV-04 at 0.9.0 under the current-tooling decision. |
| Mermaid and Mermaid CLI | Deferred. One portable asset serves both surfaces. Revisit for a distinct small GitHub diagram or recurring cross-surface export. |
| Excalidraw | Deferred until there is a distinct interactive authoring use. |
| Generated illustration | Deferred. The maintained diagram, labeled policy illustration and social preview cover the identified editorial uses. Revisit for a distinct illustration requirement. |

<a id="GHV-acceptance"></a>

## Acceptance · 2026-11-08

The rollout verified the published visitor and publishing scope below. The historical
Reader check remains `blocked` by the producing release compatibility limit
documented above. See the [completion audit](#GHV-completion-audit) for current
package state and remaining obligations.

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


<a id="GHV-completion-audit"></a>

## Completion audit · 2026-11-08

Audited GHV-01–06 as claimed complete at `5bddd141b`, the source
and live Pages revision at the time of the audit. The review used the coordinator, all three
supporting plans, the operator's direct-push and conditional-adoption decisions,
the current publisher, the retained evidence and the real GitHub consumers.
Concurrent Chandra edits were outside this audit.

| Package | Audited disposition |
| --- | --- |
| GHV-01 | Complete. Discovery parity held after authentic hydration of all 50 omitted pointer READMEs. The authored scoped assessment remains published. Both original findings stay closed. |
| GHV-02 | Complete. The README and documentation index expose the reader routes, capability and maturity boundaries, evaluation, and source-linked example. The architecture map and dated D0 retain their distinct roles. |
| GHV-03 | Partially complete. The citation, qualifier, illustration and documented reproduction boundary stand. Reopen the separate X and Z evidence route under GHV-F03. |
| GHV-04 | Complete. The opt-in renderer regenerated both committed assets byte for byte from an isolated checkout. The shared SVG is served and the hosted social PNG matches. |
| GHV-05 | Live delivery verified. Reopen qualification for the scoped review cadence under GHV-F05. The authorized omission of a hosted PR run does not reopen release verification. |
| GHV-06 | Partially complete. D2 adoption and the conditional decisions for Vale, Markdownlint, Mermaid, Excalidraw and generated illustration stand. Reopen the bounded comparisons under GHV-F04. |

Fresh checks on 2026-11-08 used the exact release source or its hosted outputs.

- `just docs-test` passed 45 tests in the isolated checkout. `just docs-visuals`
  passed and both output SHA-256 values matched their committed assets.
- A `docs.discover` inventory comparison in the isolated checkout passed for
  all 701 selected source pages. The audit replaced the 50 omitted pointers
  with their SHA-256-verified local LFS objects between the two reads. The
  rendered site has one additional generated architecture directory page.
- `gh run view 42481958715` confirmed successful build, both uploads and
  deployment. `gh run download 42481958715 --name github-pages` and tar
  member inspection passed. The 1,626-file archive contains the required
  hidden paths, example and SVG, with no symlinks, Git internals or generated
  raw evidence payloads. [Hosted run](https://github.com/paul-heyse/corpus-structure/actions/runs/42481958715)
- The live Chromium reader smoke passed at 1280 × 800 and 390 × 844 for the
  citation, assessment, SVG, all three search scopes, and hidden documentation
  paths. The live examples HTML confirmed that the X/Z section links only
  to the checkpoint. GitHub's repository API and the hosted Open Graph image
  confirmed the configured homepage, description, topics and exact social PNG.
  [Live examples](https://paul-heyse.github.io/corpus-structure/docs/examples/README.html)

The checks establish the delivered visitor routes, navigable source evidence for the
primary cases and repeatable publication. Visitor comprehension and discoverability
metrics were outside the agreed acceptance. The [closure below](#ghv-audit-closure) records the subsequent corrections.


<a id="ghv-audit-closure"></a>

## Audit gap closure · 2026-11-08

The three reopened findings are closed. GHV-F03 shows the retained X
candidate separately from the witnessed Z declaration. The GHV-F04 pilot
compared the actual Markdown and card at both widths and storyboarded the
exact citation journey. The GHV-F05 independent review records the missed
pre-activation review and accepts the assembled boundary for serialized
releases. If overlapping eligible releases become necessary, revisit deploy
admission. [Public examples](../examples/README.md) · [Comparison record](../design_review/evidence/2026-11-08_github-visitor-follow-ons/README.md) · [Independent review](../design_review/reviews/design_review_github-pages-publication_2026-11-08.md) · [Runbook](../publishing.md#github-release)

- `uv run ci evidence finalize 2026-11-08_github-visitor-follow-ons ghv.follow-on-comparison`
  and the two-viewport Playwright comparison passed. The static walkthrough
  remains the published route.
- `just turn-end`, `uv run ci docs check` and the clean LFS-disabled
  project-prefix build passed for `5a4356d45c`. The two publication checks
  each rendered 704 canonical pages with zero link errors.
- The [Documentation run](https://github.com/paul-heyse/corpus-structure/actions/runs/42483802051)
  passed `just docs-test`, build, both uploads and Pages deployment for
  `5a4356d45c92467dc1bad9595fe807207f480de8`. Playwright passed at 1280 × 800 and 390 × 844
  on the local prefix and live site. It checked the example, X and Z
  assessments and anonymous receipt payloads, diagram, the three search
  scopes and hidden paths. The live receipt links carried the deployed
  revision, the X payload matched its Git LFS hash, and neither raw receipt
  was served from Pages.

<a id="GHV-follow-on"></a>

## Follow-on increment · Show the retained semantic results

**Proposed · 2026-11-08.** The ChatGPT Pro draft
`github_view_improvement_additional_recommendations.md` (Git blob
`d00c3774b1d34721ff14649bf143df80c91ed41c`) reviewed `5bddd141b`. It is a
local authoring input. This crosswalk carries its recommendations into the
series without requiring the draft in a clean checkout.

The [live release](https://github.com/paul-heyse/corpus-structure/actions/runs/42484094468)
at `8b694c67b` already exposes the separate X and Z receipts. The original
site, metadata, social preview and GHV-06 comparisons remain qualified at
their recorded boundaries. The current homepage and examples still emit
edit URLs with a staging `src/` prefix. The dossier preflight still labels
the completed journey pending, the README badge still leads to Actions
without an opening Pages link, and the architecture map still directs the
reader to D0 first.

The next visitor should be able to see how the project preserves a condition,
recovers an antecedent and assembles supported material. The opening explains
organizational policies, procedures and technical documents as the intended
application, and the probability textbook as the current development corpus.
Use the illustrative enterprise policy to explain the target. The operator
excluded a synthetic corpus run and an interactive result inspector. This
increment uses retained outputs and static presentations.

### Foundations and boundaries

[ADR-0071](../adr/0071-github-pages-publication.md) remains the publication
decision. Markdown and retained evidence own the claims. The publisher owns
selection, navigation and link transport. A small downloadable projection
can serve the reader without bringing corpus data, Git LFS hydration or
product services into the build. An additional example should change its
authored page, excerpt and asset declaration. It should require no change to
the search integration or product schema.

Use native mdBook hierarchy over the existing page inventory. A new reference
page should retain its path and search scope and appear under the group of its
collection. Keep Pagefind index preparation at build time and defer index
loading until search opens. These boundaries follow FP-01, FP-04, FP-05,
FP-07 and H12, H16 and H26. They avoid maintaining a second site, a second
page inventory or a new corpus-serving path.
[Principles](../design_review/design_principles/core/design-principles.md) · [Efficiency heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md)

### Package queue and source coverage

| Package | Draft coverage and readiness | Acceptance |
| --- | --- | --- |
| [GHV-07 · Correctness and entry routes](github-visitor-experience/publication-and-rollout.md#GHV-07) | §§2A–C, 5 architecture introduction and 9 priority 1. Start from the live publisher and dossier receipt. | Edit actions reach their source, dossier state matches the finalized result, and the opening routes reach Pages and current architecture. |
| [GHV-08 · Retained exhibits and evaluation](github-visitor-experience/visitor-content-and-evidence.md#GHV-08) | §§3, 6, 7 and 9 priority 2. Authenticate the three retained results and use the corrected dossier evidence route. | Readers can identify what changed, see the corresponding output and assessment, and download the selected fields. The organizational target and measured scope are distinct. |
| [GHV-09 · Transformation diagram](github-visitor-experience/visuals-and-follow-ons.md#GHV-09) | §§4, 8 visual treatment and 9 priority 3. Consume GHV-08's operation and output names and GHV-07's architecture trace. | The same maintained diagram describes the handoffs on GitHub and Pages, remains legible at mobile width and in both themes, and links to full size. |
| [GHV-10 · Visitor navigation](github-visitor-experience/site-navigation-and-presentation.md#GHV-10) | §§5, 9 priorities 3–4. Implement against the opening routes from GHV-07 and the examples and evaluation targets from GHV-08. | Five public entry routes precede collapsible references. Existing page URLs, anchors and search scopes continue to work. |
| [GHV-11 · Identity, sharing and search](github-visitor-experience/site-navigation-and-presentation.md#GHV-11) | §§8 and 9 priority 5. Integrate after navigation and diagram assets are known. | The live metadata and theme agree with the public identity. Search explains a delayed or failed initialization and provides a keyboard-accessible recovery route. |

Draft §1 describes delivered capabilities and conditional tooling decisions.
The condition exhibit serves a different purpose from the citation card
compared in GHV-06. Use accessible text and emphasis to show the attachment
instead of adopting a separate image card. Draft §§6 and 9 priority 6 discuss
the synthetic run and inspector that the operator excluded.

### Correction dispositions

| Item | Owner and disposition | Closure evidence |
| --- | --- | --- |
| GHV-F06 · Draft §2A edit paths | Open · GHV-07 publisher | Root and nested actions use real GitHub paths. The generated directory has no edit action. |
| GHV-F07 · Draft §2B dossier summary | Open · GHV-07 evidence page | Finalized native and delivery results appear alongside the dated preparation history. |
| GHV-F08 · Draft §2C live entry link | Open · GHV-07 README | Documentation opens Pages. Docs build opens the workflow. Examples, architecture and evaluation remain directly reachable. |
| GHV-F09 · Draft §5 architecture introduction | Open · GHV-07 architecture map | Current code trace comes first. The design collection retains its links and the dated D0 target has a separate route. |

### Integration and release

Land GHV-07 first. Establish the GHV-08 exhibits and common labels before
finalizing GHV-09 and GHV-10, which have independent acceptance checks.
Integrate GHV-11 after both. Keep edits to the shared publisher and site
configuration ordered across these packages.

Use the [review cadence](../design_review/design_principles/binding/corpus-structure.md#reviews-in-this-repository).
Apply the operator's holistic publishing focus to the pre-change design/target
review of the new evidence and navigation surfaces, and to the assembled
boundary before release. Use the prior [publishing review](../design_review/reviews/design_review_github-pages-publication_2026-11-08.md)
where its premises still hold. Review the edit-action repair as a bounded
change within the existing publisher. The new pre-change review should
challenge adding a reference page without moving URLs and publishing an
excerpt without exposing raw evidence. The assembled review should also
assess failure recovery for search and the deployment sequence.

Use the [follow-on qualification](github-visitor-experience/publication-and-rollout.md#GHV-follow-on-qualification)
for local, hosted and live acceptance. The implementation checks are
`not_run` at plan authoring. Record release evidence and finding closures
here when the work is implemented and verified.

**Plan validation · 2026-11-08.** `just turn-end` and `uv run ci docs check`
passed on an LFS-disabled export of `8b694c67b` with the seven authoring
files overlaid. The documentation check rendered 705 canonical pages with
zero link errors. This checks publication of the plan documents.

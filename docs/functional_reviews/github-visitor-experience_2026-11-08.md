# GitHub visitor experience and documentation publishing

**Proposed · 2026-11-08.** This review assesses the operator-supplied
`github_view_improvement.md` against commit `2147ac24a`. The audience is an engineer,
collaborator, or hiring reader arriving at the GitHub repository. The operator selected
public Pages hosting for the existing documentation collections, with a visitor-first
entry path. The review distinguishes public presentation, evidence inspection, and
native reproduction. Current product authority remains with the architecture and
enrichment plans. [Status](../../STATUS.md) · [Design standard](../design_review/design_principles/standard.toml)

Start with a better README, one source-linked result, a compact diagram, and a visitor
route through the existing docs. These deliver value on GitHub while Pages is prepared.
The hosted site is worth doing, but the clean checkout used by the current workflow
exposes two publication defects to resolve before enabling deployment.

<a id="O01"></a>

## O01 · Give the repository a visitor-first introduction

**Recommend for the first delivery.** Open with **Corpus Structure — From documents to
connected, source-grounded knowledge.** Explain progressive enrichment with concrete
outputs: located observations, qualified components, typed links, and inspectable
comparisons or dossiers. A component can be useful before a complete interpretation is
available. Show the example and diagram before environment or agent instructions. Place
“See an example”, “Architecture”, “Evaluation”, and “Run locally” near the top. Keep the
setup and development workflows accessible through a concise README section and the
existing operating guides. Retain the project's authorship line if it helps the intended
audience. A documentation workflow badge can indicate a real check once the corresponding
workflow is verified. [Current README](../../README.md) · [Documentation routes](../README.md)

Describe what someone can inspect, with dated links beside demonstrated capabilities.
The 518 physical pages and 29 selected source views describe different populations.
The reviewed contextual edges cover nine retained cues. The review also documents four
additional printed references that were absent from the resolver's input. The current
corpus supports development and operation-level assessment, with coverage and
generalization bounded by the evidence. Link source intake, qualification, comparisons,
dossiers, and delivery to their own supporting accounts. Keep contribution and test counts
in the evidence. [Whole-book output review](../design_review/evidence/2026-11-08_nce-full-book/review/README.md) · [Scoped outputs](../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#contextual-section-citations) · [Enrichment disposition](../plans/next-corpus-enrichment_2026-11-07.md#full-book-execution)

<a id="O02"></a>

## O02 · Show a real result the visitor can verify

**Recommend one primary example in the README and a second in the documentation.**
Use accessible Markdown for the facts and links. The primary walkthrough can read as
follows.

| Step | Retained result |
|---|---|
| Locate | The printed cue “Section 5.1” occurs on physical page 260 at `#/texts/4682[69:80)`. |
| Connect | The contextual producer selected a `cites-section` edge to “Important Distributions” on physical page 191, at `#/texts/3495[0:27)`. |
| Explain | An explicit source-cue witness supports the preferred edge. The dated output review compared the cue and target with the book. |
| Inspect | The selected edge starts with `27b19068cdac`, from run 327, cut 447, task 1528. Producer selection and the editorial assessment have separate standing. |

Link both physical pages and the reviewed row. The Dartmouth PDF at the source below
matched the SHA-256 in ADR-0070 on 2026-11-08 using `curl -fsSL URL | sha256sum`.
Its title page identifies the GNU Free Documentation License. Link to the original
and attribute the edition. Use brief quoted identifiers and an editorial description
for the first pass. Establish the terms of the exact source before reproducing longer
passages or page crops. [Physical page 260](https://math.dartmouth.edu/~prob/prob/prob.pdf#page=260) · [Physical page 191](https://math.dartmouth.edu/~prob/prob/prob.pdf#page=191) · [Source decision](../adr/0070-full-book-method-development.md) · [Retained citation](../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#contextual-section-citations)

Use the page 289 correlation exercise to show local meaning. The observed positive-variance
condition at `#/texts/5253[3:57)` is attached to the defining predicate at `[89:96)`
by edge `1407260e0e7e6a`. A deeper example can contrast the withheld affine-`X` link
with the recovered and linked `Z` occurrence. Describe these as separate cases with their
own evidence. An enterprise policy illustration belongs deeper in the docs and needs an
explicit illustrative label. [Qualification example](../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-checks-on-cut-441) · [Retained X and Z outcomes](../../STATUS.md#delivered-and-assessed)

Offer three levels of use. A public reader follows the static result and evidence. A
development checkout with the producing release can attempt inspection by exact run and task
using the existing Reader query. A full reproduction follows the whole-book evidence procedure,
which needs the authenticated PDF, the matching released recipe and model artifacts, a
prepared PostgreSQL development target, the complete heading inventory, and contextual
retrieval prerequisites. The published whole-book recipe uses CUDA Docling layout and
formula models, CPU RapidOCR, and a separate managed Nemotron service for the combined arm.
Document that distinction before offering a reproduction command. The public example
should remain useful if a retained development run is no longer available. [Reader contract](../../python/corpus-structure/src/corpus_structure/serve/contextual_navigation.py) · [Native reproduction](../design_review/evidence/2026-11-08_nce-full-book/README.md)

**Live Reader check, 2026-11-08.** The installed query refused run 327 with
`incompatible_query`. A live walkthrough needs a compatible checkout and producing
release or a separately verified detached delivery. Keep the static example as the launch
path. The exact read attempted was:

```sh
uv run --no-sync ci query contextual_neighborhood --run 327 --param task_id=1528 \
  --param target_id=semantic-target:74075a3e8394b041988ff23c987052c7a37a6de18a0932ee3ced483fb44dde53 \
  --max-rows 1 --json
```

<a id="O03"></a>

## O03 · Maintain one functional diagram for both surfaces

**Recommend D2 with bundled ELK and a committed SVG.** Lay out “Extract observations”,
“Compose local meaning”, “Connect the corpus”, and “Assemble knowledge”. Name the data
product at each transition. Treat source anchors as shared support across the stages,
with assessment attached to the operations it examines. Use one self-contained
contrast-safe palette, short labels, useful alt text, and a text explanation. Review the
render at normal README width and on mobile. Open the full-size SVG from a link.
Declare the SVG as a publication asset if the publisher would otherwise send the
click-through to GitHub. Use the same editable source for both views.
[D2 ELK and layout choices](https://d2lang.com/tour/layouts/) · [Publisher asset handling](../publishing.md#authoring-and-transport)

Use **D2 0.7.1** as the first renderer pin. The locally installed binary and bundled ELK
rendered SVG from stdin on 2026-11-08 using `d2 --layout=elk - -`. A fresh Linux
x86-64 authoring host can unpack the upstream `d2-v0.7.1-linux-amd64.tar.gz` into a
user tool directory. GitHub reports SHA-256
`eb172adf59f38d1e5a70ab177591356754ffaf9bebb84e0ca8b767dfb421dad7` for that archive.
Use `d2 --layout=elk INPUT.d2 OUTPUT.svg` from one opt-in regeneration recipe. The docs
build can consume the committed SVG with its current dependencies. Upstream **0.9.0**
is an upgrade candidate if a needed rendering feature or fix warrants it. Current
upstream documentation describes native PNG export, which is outside the proposed SVG
path and should be verified against the selected version before relying on it.
[Pinned D2 release](https://github.com/d2lang/d2/releases/tag/v0.7.1) · [D2 0.9.0](https://github.com/d2lang/d2/releases/tag/v0.9.0) · [Export contracts](https://d2lang.com/tour/exports/)

GitHub-native Mermaid is a good fit for small GitHub diagrams. A shared committed
asset gives the main figure a single cross-surface rendering and avoids adding a
Mermaid renderer to mdBook. Mermaid CLI **12.2.0** via its pinned npm package or official
container becomes relevant if repeated Mermaid exports justify maintaining Chromium
for that route. Excalidraw **0.18.1** is a candidate for interactive workshops and adds
an editor workflow that this figure can do without. Start with typography and geometry.
If icons improve scanning, vendor only selected Lucide SVGs at tag **1.70.0**, commit
`b826f0c527e1498f5e46f41ca0277ccab144bf31`, with the upstream ISC and applicable Feather
MIT notices. This requires no JavaScript icon package.
[GitHub Mermaid](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) · [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli/tree/12.2.0) · [Excalidraw](https://github.com/excalidraw/excalidraw/tree/v0.18.1) · [Lucide static usage](https://lucide.dev/guide/static/getting-started) · [Lucide notices](https://lucide.dev/license)

The technical labels should reflect the delivered routes. Docling and Slim `2.148.0`
with Core `2.106.0` own PDF conversion in the demonstrated setup. Nemotron Parse 3.5
has separately retained parse and layout receipts. `gliner2[local]==2.1.0` is the
package pin, while GLiNER2.5 identifies the retained model arm. Keep Chandra's verified
explicit inspection and proposed governed promotion distinct. An expanded architecture
view may show finite interpretation and fitting, followed by pgmpy's graphical-model
and Pyro's probabilistic-modeling research questions. Neither is a prerequisite for
the public diagram or proof of a shipped Bayesian scoring path.
[Product pins](../../python/corpus-structure/pyproject.toml) · [Nemotron model card](https://huggingface.co/nvidia/Nemotron-3.5-Parse) · [GLiNER2](https://github.com/fastino-ai/GLiNER2) · [Chandra disposition](../plans/chandra-2-post-nemotron_2026-11-08.md) · [pgmpy](https://github.com/pgmpy/pgmpy) · [Pyro](https://github.com/pyro-ppl/pyro) · [NCE research scope](../plans/next-corpus-enrichment_2026-11-07.md)

<a id="O04"></a>

## O04 · Curate the documentation entry points and publish the existing site

**Recommend visitor routes first and Pages after clean-checkout qualification.**
Use Overview, Examples, Architecture, Evaluation, and Running locally as the prominent
routes. Keep current process, review, plan, and evidence pages discoverable. Prefer
reordering or adding entry pages through the existing site configuration. Reconcile
the blanket “everything is Proposed” sentence in the architecture map with its mixed
maturity notice and owner labels. Present D0 as a dated target, with an introduction
that directs the reader to the current explanation. Build the code-reading guide around
a few questions raised by the examples.
[Architecture map](../design/README.md) · [D0](../design/D0-target-overview.md) · [Site selection](../site.toml)

| Reader question | Current entry points |
|---|---|
| Where do source locations come from? | [PDF section views](../../python/corpus-structure/src/corpus_structure/ingest/pdf_section_views.py) · [Source-view SQL](../../python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql) |
| How are observations and links produced? | [GLiNER method](../../python/corpus-structure/src/corpus_structure/methods/gliner.py) · [Contextual links](../../python/corpus-structure/src/corpus_structure/semantic/contextual_links.py) |
| How do readers inspect and assess results? | [Operation assessment](../../python/corpus-structure/src/corpus_structure/evaluate/operation_assessment.py) · [Reader queries](../design/D8-agent-and-query-interfaces.md) · [MCP CLI](../../python/corpus-structure/src/corpus_structure/cli/mcp.py) |

The existing artifact-only decision is explicit in ADR-0003. If Pages is selected for
implementation, supersede that decision and update publishing operations. Reuse the
offline mdBook `0.5.4`, Pagefind `1.5.2`, and lychee `0.24.2` pins. They match this
host, and there is no version change justified by the observed failures. Keep
`just bootstrap-docs` as the existing installation route. Use the publisher's
`--base-url /corpus-structure/` check with the artifact to be deployed. A local preview
can retain the root default. The deployment should upload the same output that passed
the build and link check.
[ADR-0003](../adr/0003-publish-docs-site.md) · [Publishing commands](../publishing.md)

**Tested, 2026-11-08.** A detached checkout at `2147ac24a` with LFS downloads disabled
failed `UV_LOCKED=0 uv run --no-project --offline --no-python-downloads python scripts/docs.py build --base-url /corpus-structure/`.
The recursive evidence README glob selects generated bundle READMEs, including 50
that are LFS pointer files in this checkout. The first failed title lookup is under
`2026-11-05_pce-portable-review/raw/combined_003`. A second build with those 50 paths
temporarily excluded reached link resolution and failed on a stale local link to
`docs/statistics_corpus/SOURCES.tsv` in the source-population evidence README.
Prefer selecting authored evidence indexes and reviewed narrative explicitly, with
generated bundle payloads still reachable through evidence links, and correct the
source-inventory link at its owner. Select the same pages in hydrated and LFS-disabled
checkouts so local and hosted navigation agree. Fetching the complete LFS corpus would add work
to every docs build and still leave the stale link. Before deployment, check for
other checkout-only paths, unresolved references, raw payloads, and asset links in
the exact generated artifact. The initial two failures do not establish the complete
set of clean-checkout issues.
[Source-population evidence](../design_review/evidence/2026-11-04_m1-source-populations/README.md) · [Workflow checkout settings](../../.github/workflows/docs.yml)

With both temporary adjustments applied in the isolated checkout, `uv run --no-sync ci
docs check --json` and the project-prefix build passed on 2026-11-08. The bounded
artifact contained 700 canonical pages, including this review, and no symlinks.
Playwright via `.venv/bin/python` passed landing navigation, Current and Everything
search, and retrieval of hidden paths at 1280 × 800 and 390 × 844 when serving that
artifact locally under `/corpus-structure/`. These checks cover the existing site
and the temporary adjustments. Hosted publication and the proposed visitor UI
remain `not_run`.

The candidate Actions sequence is `configure-pages` **v6.0.0**
(`45bfe0192ca1faeb007ade9deae92b16b8254a0d`), `upload-pages-artifact` **v5.0.0**
(`fc324d3547104276b827a68afc52ff2a11cc49c9`), and `deploy-pages` **v5.0.1**
(`368f82528645a54fb793d4d04e342629a3f51346`). The pinned upload action supports
`include-hidden-files: true` and excludes `.git` and `.github` even then. The
artifact needs `.claude`, `.agents`, and `.nojekyll` preserved. Keep PR builds
read-only and separate from Pages packaging/deploy. Deploy a successful default-branch
build through the `github-pages` environment, with `pages: write` and `id-token: write`
on the deploy job and concurrent deployments serialized. Verify the output URL,
navigation, asset paths, and default and expanded search scopes after deployment.
If deployment fails, preserve the checked artifact and defer the homepage update
until a subsequent successful live check.
[Custom Pages workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) · [Configure action](https://github.com/actions/configure-pages/blob/45bfe0192ca1faeb007ade9deae92b16b8254a0d/action.yml) · [Upload action](https://github.com/actions/upload-pages-artifact/blob/fc324d3547104276b827a68afc52ff2a11cc49c9/action.yml) · [Deploy action](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/action.yml)

<a id="O05"></a>

## O05 · Set GitHub metadata and add a social preview

**Recommend description and topics with the README, homepage after live Pages verification,
and the social preview as a follow-on.** Suggested description: “Document intelligence for
building connected, source-grounded knowledge with structured extraction, semantic linking,
and granular evaluation.” Start with `document-intelligence`, `information-extraction`,
`knowledge-representation`, `natural-language-processing`, `semantic-search`, `gliner`,
and `docling`. Consider the proposed `knowledge-graph` and `entity-resolution` topics
if the landing page gives a visitor a concrete route into those capabilities.

Installed **GitHub CLI 2.45.0** has the needed `gh repo edit --description`,
`--add-topic`, and `--homepage` flags. On 2026-11-08,
`gh api repos/paul-heyse/corpus-structure` returned public visibility, admin access,
empty About fields, and `has_pages=false`. The Pages endpoint returned HTTP 404.
Use the Settings UI to select Actions or the Pages REST API with `build_type=workflow`
and its required authorization. Repository admin access and API token permissions
are distinct checks. Prepare a simple **1280 × 640** PNG under **1 MB** and use
Settings → Social preview for upload. No GitHub CLI update or additional GitHub App
is needed for the documented workflow.
[GitHub CLI reference](https://cli.github.com/manual/gh_repo_edit) · [Pages source settings](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) · [Pages REST API](https://docs.github.com/en/rest/pages/pages#create-a-github-pages-site) · [Social preview requirements](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)

<a id="O06"></a>

## O06 · Keep optional visual and editorial tooling tied to a use

Use Playwright to inspect both viewport sizes and the deployed project path. Add a
maintained HTML/CSS-to-PNG route when producing the social preview or when a card
meaningfully improves the example. Keep the underlying example accessible as text,
with the image as a companion. Pin **Playwright Python 1.64.1** separately for visual
authoring, using an isolated uv invocation or a locked script if regeneration
becomes routine. The installed copy arrives through Docling Slim's HTML-render
extra, and its Chromium 1248 is already cached. A standalone bootstrap can run
`UV_LOCKED=0 uv run --no-project --with playwright==1.64.1 python -m playwright install chromium`.
On a clean Linux host use `install --with-deps chromium` when the needed OS libraries
are absent, with package-manager access. Pin the viewport and scale, use local fonts
and images, wait for `document.fonts.ready`, and capture with
`locator.screenshot(animations="disabled")`. Use the committed assets in routine CI.
Context7 confirmed the versioned Playwright source and helped locate the D2 and
Lucide interfaces. The local Playwright smoke passed an in-memory element capture
through `.venv/bin/python` on 2026-11-08.
[Browser installation](https://playwright.dev/python/docs/browsers) · [Locator screenshot](https://playwright.dev/python/docs/api/class-locator#locator-screenshot) · [Pinned Python source](https://github.com/microsoft/playwright-python/tree/v1.64.1)

Use editorial review for launch. **Vale 3.26.0** is an optional release binary if
terminology drift recurs. Start with advisory JSON output and a small visitor-page
vocabulary. **markdownlint-cli2 0.24.0** requires Node 22 or later and is a candidate
only if Markdown formatting causes recurring maintenance problems. Installed Node
26 satisfies that package's declared engine. A recorded walkthrough is lower
priority than static source inspection. If there is demand for a video, use the
already installed FFmpeg 6.1.1 for export with captions and a transcript. A generated
illustration is optional for a future editorial use. No new local system installation
is required to prepare the recommended first tranche on the inspected host.
[Vale releases](https://github.com/vale-cli/vale/releases/tag/v3.26.0) · [Markdownlint CLI](https://github.com/DavidAnson/markdownlint-cli2)

## Delivery and acceptance

The first tranche combines O01–O03, the visitor routes of O04, and About metadata
from O05. A reader should be able to say what the pipeline produces and follow the
citation from its occurrence through the typed edge to the source and assessment.
The qualifying secondary example should identify the exact predicate attachment and
its limits. Check the diagram at ordinary desktop and mobile widths and confirm
the explanation remains readable as plain Markdown.

The next tranche finishes O04 and sets the homepage. Run `uv run ci docs check`
in the prepared checkout, `just docs-test` for publisher changes, and a clean
LFS-disabled project-prefix build with the same input as hosted CI. Smoke-test
navigation, asset retrieval, default Current search, and Reference/Everything
on the served artifact. Repeat the public checks at the deployed URL and verify
the About link there. Add the social image after its actual PNG has been checked.
Record hosted deployment and browser outcomes separately from local documentation
validation. O06 and the deeper visual and video proposals remain conditional.

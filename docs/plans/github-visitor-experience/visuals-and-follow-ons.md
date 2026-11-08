# Shared visuals and follow-on investigations

**Status · 2026-11-08. Complete.** Owns the GHV-04 and GHV-06 designs. The
[coordinator](../github-visitor-experience_2026-11-08.md) owns execution state.
Consume the visitor wording and exact examples from [GHV-02/03](visitor-content-and-evidence.md).
Use the visual and tooling findings in the [functional review](../../functional_reviews/github-visitor-experience_2026-11-08.md#O03).

<a id="GHV-04"></a>

## GHV-04 · Maintained diagram and social image

The visual assets owner commits an editable `docs/visuals/pipeline.d2` and
`docs/assets/pipeline.svg`. The main figure communicates four operations and
their outputs.

| Operation | Displayed result |
| --- | --- |
| Extract observations | Located observations with source spans |
| Compose local meaning | Qualified components with roles, conditions and modality |
| Connect the corpus | Typed relationships and their witnessed selection |
| Assemble knowledge | Inspectable comparisons, dossiers and gaps |

Show intake as a compact input. Use provenance as shared support and connect
assessment to the relevant capture, role, attachment, link and scope operations.
Prefer short functional labels, a neutral background with navy, blue, teal,
purple and gold accents, and a layout that stays legible at README width. Put a
text explanation and useful alt text alongside the same SVG on both surfaces.
Link the image to its full size and declare it in publication assets to keep the
full-size link local on the site. GitHub and mdBook consume the committed SVG.
[Publisher asset transport](../../publishing.md#authoring-and-transport) · [GitHub Markdown renderer](https://github.com/github/markup)

Render with `d2 --layout=elk INPUT.d2 OUTPUT.svg` using D2 `0.9.0`.
The upstream Linux x86-64 release archive is `d2-v0.9.0-linux-amd64.tar.gz`
with published SHA-256 `5669ddc46b99e942cc96078f4a4e36d5e62103348f4c05179ede27802fdd87a9`.
Use the existing binary when the version matches, or unpack the checksum-verified
upstream binary into a user tool directory. Bundled ELK supplies layout without
another package for this SVG route. Use the main figure as the starting point for
the deeper architecture explanation. Identify the demonstrated Docling,
Nemotron Parse 3.5 and GLiNER roles. Put finite interpretation and fitting in
their implemented scope and pgmpy and Pyro in explicitly labeled research
extensions. Keep Chandra inspection separate from proposed promotion.
[Pinned D2 release](https://github.com/d2lang/d2/releases/tag/v0.9.0) · [ELK layout](https://d2lang.com/tour/layouts/) · [Product roles and research boundaries](../../functional_reviews/github-visitor-experience_2026-11-08.md#O03)

Commit `docs/visuals/social-preview.html` and `docs/assets/social-preview.png`.
Use the title, a short tagline and a simplified source-to-structure motif. The
preview is `1280 × 640` and under `1 MB`. Keep the template's assets and
licensed fonts local. Use Playwright Python `1.64.1` with its matched Chromium
for element capture. Set the viewport and device scale, wait for
`document.fonts.ready`, and disable animation in `locator.screenshot`.
Use a dedicated locked uv script for the Python render path, separate from the
product lock and Docling HTML-render extra. Document the isolated bootstrap
`UV_LOCKED=0 uv run --isolated --no-project --with playwright==1.64.1 python -m playwright install chromium`.
Install system libraries through Playwright's `install --with-deps chromium`
route only on a host that lacks them and has package-manager authority.
[Browser installation](https://playwright.dev/python/docs/browsers) · [Screenshot API](https://playwright.dev/python/docs/api/class-locator#locator-screenshot) · [Social preview settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)

Add one opt-in `just docs-visuals` recipe to run both renderers and report missing
or mismatched prerequisites with the authoring setup route. Ordinary builds use
the committed outputs without D2 or a browser. Inspect an asset candidate before
replacing its committed counterpart. Re-run the recipe from a fresh prepared
authoring environment and check that the diagram and preview have stable
content and dimensions. Qualify the SVG, its click-through and its text equivalent
in GitHub and the prefix-mounted site at desktop and mobile widths. Check the
preview size, format, text and legibility before handing it to GHV-05 for upload.

<a id="GHV-06"></a>

## GHV-06 · Adopt optional additions where the pilot supports them

The visual and editorial owners use the shipped Markdown examples, primary SVG
and initial visitor prose as controls. Record a disposition against each row
in the coordinator, with the observed benefit and added work or a concrete
revisit trigger. Adopt a tool only for the supported use. Record the exact pin,
install command, system prerequisites and local or CI scope when adopting.

| Candidate | Decision test and implementation if adopted |
| --- | --- |
| Rendered example card and Lucide SVGs | Compare an HTML/CSS card or a small icon set with the plain example and SVG at desktop and mobile widths. Adopt when it improves the reader's ability to identify the source, result and witness without losing readable text or duplicating evidence authority. Reuse GHV-04 capture for a card. Vendor only used icons at Lucide `1.70.0`, commit `b826f0c527e1498f5e46f41ca0277ccab144bf31`, with the applicable ISC and Feather MIT notices. [Static usage](https://lucide.dev/guide/static/getting-started) · [Lucide notices](https://lucide.dev/license) |
| Recorded walkthrough | Compare the static walkthrough with a short storyboard on an exact verified result. Proceed when a visible interaction helps explain source inspection and the evidence can be shared. Export with the current stable FFmpeg, and include captions, transcript and a static evidence link. [Review of recording tooling](../../functional_reviews/github-visitor-experience_2026-11-08.md#O06) |
| Vale and Markdownlint | Try Vale `3.26.0` as an advisory release binary only if recurring terminology errors survive editorial review. Limit it to visitor pages, local vocabulary, and JSON feedback. Try pinned `markdownlint-cli2@0.24.0` on Node 22+ only for recurring formatting issues the current build misses. Adopt only when the trial catches the observed issues without disproportionate noise. Keep both out of the routine build for this scope. [Vale release](https://github.com/vale-cli/vale/releases/tag/v3.26.0) · [Markdownlint CLI](https://github.com/DavidAnson/markdownlint-cli2) |
| Renderer upgrade or extra diagram tooling | The operator selected current stable tooling, so GHV-04 updates D2 to 0.9.0. Retain one renderer for the shared SVG. Use GitHub-native Mermaid for a focused GitHub diagram when warranted. Evaluate Mermaid CLI `12.2.0` only for a separate recurring export that justifies browser tooling. Consider Excalidraw `0.18.1` for a distinct interactive authoring use. [D2 release](https://github.com/d2lang/d2/releases/tag/v0.9.0) · [GitHub Mermaid](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) · [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli/tree/12.2.0) · [Excalidraw](https://github.com/excalidraw/excalidraw/tree/v0.18.1) |
| Generated illustration | Consider only for a distinct editorial purpose the maintained diagram and examples do not serve. Label it as illustrative, and validate its accuracy and readability alongside the evidence-backed content. |

**Closure.** Every row has an adoption or deferral supported by an actual
condition or bounded comparison. Regenerate and inspect the affected outputs
for adopted tools, or exercise the real editorial error for an adopted checker.
The required social image and main diagram close through GHV-04.

The [completed pilot](../../design_review/evidence/2026-11-08_github-visitor-follow-ons/README.md)
retains the viewport comparisons and exact citation storyboard. The
[coordinator](../github-visitor-experience_2026-11-08.md#ghv-06-dispositions) owns the resulting decisions.

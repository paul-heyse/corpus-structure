# Publishing documentation

**Implemented** (ADR-0071). Verify locally with `uv run ci docs check` in a prepared
checkout and record the dated outcome in STATUS. Hosted CI results are a separate context.

## Commands and dependencies

`just bootstrap-docs` installs documentation binaries through cargo-binstall and prepares the
isolated pytest environment. Prerequisites are Git, uv, just and cargo-binstall; bootstrap may use
the network. Python comes from `.python-version`, pytest from `uv.lock` when present, and
documentation tools from [site.toml](site.toml). No product package or build is needed.

- `just docs`: render, index and check offline links/fragments, then replace `build/docs/site/`.
- `uv run ci docs check`: ADR and agent checks plus the same complete publication. The
  underlying `just docs-check` serves documentation-only environments without installed `ci`.
- `just docs-test`: focused script regressions through isolated pytest.
- `just docs-serve`: build, then serve the final artifact at http://127.0.0.1:8000.

Ordinary commands are offline after bootstrap. Preview has no watcher: stop, rebuild and serve
again after edits. Missing tools/cache report failure. The last successful site survives a failed
build. Run one publishing command at a time. Delete ignored `build/docs/` to reset generated
output.

## Authoring and transport

Collections and current-work selections live in site.toml. Add a document under its collection;
use a scalar title or an H1 outside fenced examples. Do not edit generated navigation. The active
standard manifest and ADR lifecycle control scope; current-work selection is a reading priority,
not a status table. The site publishes only the retained working set (ADR-0001): a retired
document leaves the tree and its collection, never moves to an archive collection. Every
collection pattern must match at least one file. Evidence selection includes the
collection index, direct authored indexes and explicitly listed deeper authored
pages. Generated review bundle READMEs remain linked at the repository revision.

Published Markdown links become local HTML. Omitted tracked files/directories link to GitHub at
the build revision. A dirty preview says those links show committed content. Optional ignored
capability indexes are visibly local references. Ordinary linked images are copied; evidence raw
files are not recursively copied. An evidence download must be an explicit asset selection.

A live section move retains its ID, governing decisions and old heading as a short relocation
pointer with `<!-- relocated-section -->` immediately after it. The authoritative owner carries
the prose. The shared resolver ignores fenced examples and relocation pointers, checks unique
ownership and supplies the generated section directory. A retired document gets no stub.

## Search and artifacts

The bundled Pagefind Component UI defaults to Current on each opening. Select Reference or
Everything explicitly; the publisher offers History only when a published page has that scope.
Search assets are local and URLs resolve from the module location, supporting root or subpath
hosting: `UV_LOCKED=0 uv run --no-project --offline python scripts/docs.py build --base-url /corpus-structure/`
checks a deployment prefix. The docs-only workflow checks the project prefix and
uploads that directory as the ordinary artifact. Eligible successful main runs also
deploy the same directory through the `github-pages` environment. The hosted Linux
bootstrap verifies release archive hashes and extracts only the three declared
binaries. Local bootstrap uses the portable cargo-binstall route.

## Visual authoring

Use D2 0.9.0 with bundled ELK and the locked Playwright 1.64.1 render script.
On a prepared checkout, run `just docs-visuals` to regenerate the shared SVG and social
PNG. Install the matching Chromium if needed:

```sh
UV_LOCKED=0 uv run --isolated --no-project --with playwright==1.64.1 python -m playwright install chromium
```

The preview uses the local DejaVu Sans font on the Linux authoring host. Inspect the
outputs before committing them. Routine publication uses those committed assets.

## GitHub release

Select GitHub Actions as the repository's Pages source. A push to main or a main
workflow dispatch starts the eligible deployment. Verify the deployed revision,
prefix navigation, and search before setting the repository homepage. If deployment
fails, inspect the failed job and retry the corrected main revision. The ordinary
artifact is available for inspection after a successful build.

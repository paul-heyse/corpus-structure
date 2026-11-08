# Visitor navigation and site presentation

**Status · 2026-11-08. Complete.** Develops GHV-10 and GHV-11. The
[coordinator](../github-visitor-experience_2026-11-08.md#GHV-follow-on)
owns disposition and combined acceptance. Consume the corrected entry
routes from [GHV-07](publication-and-rollout.md#GHV-07), the exhibit and
evaluation entry from [GHV-08](visitor-content-and-evidence.md#GHV-08),
and the diagram variants from [GHV-09](visuals-and-follow-ons.md#GHV-09).

<a id="GHV-10"></a>

## GHV-10 · Put the visitor journey before reference material

Keep page discovery and search scope in the existing publisher. Give
`docs/site.toml` a navigation-only ordering over the discovered pages.
Resolve explicit navigation entries and group roots against the same
published page list. Generate the native indented chapter links in
`SUMMARY.md` and use mdBook folding. The navigation name can differ from
the authored heading without changing search metadata. Retain the
repository-relative output path, root landing alias, existing heading
fragments and generated architecture section anchors.
[Site policy](../../site.toml) · [Publisher](../../../scripts/docs.py) · [mdBook summary syntax](https://rust-lang.github.io/mdBook/format/summary.html)

### Opening routes

| Sidebar label | Destination |
| --- | --- |
| Overview | Root README and homepage alias. Keep it first. |
| Examples | Existing examples page with the retained exhibits. |
| Functional architecture | Existing architecture map, starting with the current code trace. |
| Evaluation | The assessment entry introduced in GHV-08. |
| Develop locally | A short `docs/develop.md` route for setup, `uv run ci doctor`, contributor workflow and code entry points. |

Start the documentation landing page with the same routes. Move its
process guidance below them. On the README, distinguish **Inspect results**,
**Reproduce the documented experiment** and **Develop locally**. Retain
`#run-locally` as a stable entry to the choices. The reproduction route
keeps the exact source, release, environment and historical Reader limit.
The developer page links to the existing setup and contribution owners.

### Reference groups

Use the existing pages below as the linked group roots. Emit each remaining
page once under its collection's group, with stable order within the group.
A new page inherits its collection's group and search scope. The generated
architecture directory belongs under Architecture contracts.

| Sidebar group | Root | Remaining collections or pages |
| --- | --- | --- |
| Architecture contracts | `docs/design/DESIGN.md` | Architecture and Design standard |
| Implementation reference | `docs/README.md` | Documentation |
| Evidence and experiments | `docs/design_review/evidence/README.md` | Evidence, Reviews and Design principle audit |
| Contributor and agent workflows | `AGENTS.md` | Process and the remaining Start here pages |
| Plans and decisions | `docs/plans/README.md` | Work plans and Decisions |
| Library references | `docs/libraries/README.md` | Library overviews and Library leverage |

Resolve group roots and opening pages before grouping their collection
peers. Refuse unknown or duplicate navigation targets and unassigned
published pages. Keep Current as the default search scope, with Reference,
Everything and any published History available under the existing rules.
Keep both local ChatGPT Pro input drafts out of publication discovery
during local previews. Carry the existing exclusion approach forward for
the additional recommendations draft.

**Closure.** The native sidebar shows the five opening items in order
with collapsible reference groups below them. An exact inventory check
against the baseline accounts for the two new authored pages, retains
every previous canonical page once, and preserves its URL and search scope.
Browser checks cover folding and following a deep link from desktop and
mobile. Existing fragment and hidden-path checks continue to pass.

<a id="GHV-11"></a>

## GHV-11 · Align identity and make search recovery visible

### Identity and social sharing

Set the book title to **Corpus Structure** and use the existing public About
description as the default. Add a small SVG favicon and use shared theme
styles for headings, callouts and exhibits. Apply the diagram treatment
from GHV-09 to the actual selected light and dark documentation themes.
Check text, highlights and diagram labels for readable contrast.

Use the HTML annotation step to write a canonical URL, a single page
description, and Open Graph title, description, URL and image. Use each
published page's title with the public project identity. Allow authored
descriptions for the opening visitor pages and use the book description as
the default. Use the absolute Pages base from the site's publication policy
independently of the local build prefix. Canonicalize `index.html` and
`README.html` to the Pages root. Exclude the 404 and other presentation
aliases from canonical page metadata and search. Escape attribute values and
preserve source-revision annotation.

Copy the existing social PNG and the favicon as explicit assets even when
their only reference is in the document head. Publish the PNG at
`/corpus-structure/docs/assets/social-preview.png`. Keep the existing
GitHub repository social preview. The checked site remains a single
artifact. [Publisher](../../../scripts/docs.py) · [mdBook theme options](https://rust-lang.github.io/mdBook/format/theme/index.html)

### Search initialization and recovery

Keep Pagefind Component UI and the existing lazy index loading. Leave a
search control and a status region available even if the component bundle
cannot initialize. On first open, announce loading, make the search input
read-only and keep scope selection disabled. Set Current and enable
interaction when the index and filters are ready.

Observe the component instance's `error` event as well as rejected loads.
In Pagefind 1.6.0, an import failure can emit `bundle_load_failed` and
return from the load, so a resolved `triggerLoad()` promise alone cannot
establish readiness. Report initialization failure in accessible text and
provide a keyboard-reachable **Reload to retry** action. Keep the failed
state distinct from an empty result set. Closing or reopening the modal
during loading must preserve a consistent state. A successful later open
uses the prepared index and resets the scope to Current.
[Pagefind component events](https://pagefind.app/docs/custom-components/) · [Pinned load implementation](https://github.com/pagefind/pagefind/blob/v1.6.0/pagefind_ui/component/core/instance.ts#L630)

**Closure.** Publisher tests cover root and nested canonical URLs, the
homepage alias, metadata escaping and image publication under the project
prefix. Browser checks delay index initialization, fail the UI bundle and
the first index load separately, exercise the retry with the keyboard, and
verify that the first successful query works with Current selected.
Reference and Everything remain usable. Run the combined
[follow-on qualification](publication-and-rollout.md#GHV-follow-on-qualification)
against the release source.

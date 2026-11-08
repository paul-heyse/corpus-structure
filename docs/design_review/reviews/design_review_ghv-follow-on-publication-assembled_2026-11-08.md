# GitHub visitor follow-on assembled publication review

**2026-11-08 · Design/target · Holistic · Independent reviewer `ghv_target`. Decision · Accept scoped.**

The assembled source at `60faba22e294fe96fcccfbd49a6dd7feb764fae8` implements
GHV-07–11 and the authorized statistics corpus route. One checked Pages
artifact serves the exhibits, navigation and search. The corpus index
identifies original sources kept in Git LFS. The judgment covers serialized
releases and static reader journeys. Product execution, historical Reader
recovery and overlapping releases are outside this scope.
[Pre-change review](design_review_ghv-follow-on-publication-target_2026-11-08.md) · [Diagnostic baseline](../audit/README.md#ghv-follow-on-publication-refresh) · [Owning plan](../../plans/github-visitor-experience_2026-11-08.md#GHV-follow-on)

| Scenario | Assembled mechanism and observation |
| --- | --- |
| Add a reference page | Discovery owns membership and scope. Native mdBook nesting keeps the output path. Navigation assigns pages once and rejects unknown, duplicate or unassigned targets. Authored titles remain separate from navigation labels. |
| Suggest an edit | The action uses the configured branch and encoded page path. The generated directory omits it. Source and receipt links retain the build revision. |
| Publish assessed excerpts and originals | The JSON retains textual attachment, private antecedent standing, exact dossier membership and separate excluded material. The evaluation separates nine checked decisions from four upstream misses. The manifest identifies LFS objects. Only the corpus README is selected for Pages. |
| Open search on a slow or failed connection | The control is mounted before the component import. Input and scope wait for filters and Current. A rejection or error event exposes the reload control. Generation checks protect close and reopen. |
| Recover a release | Use the checked artifact and serialized promotion. Inspect the live revision after uncertain promotion before retrying corrected main. |

### Findings resolved in the reviewed source

- **F01 · Raw corpus images could cross the Pages boundary.** The generic
  image rule could copy a corpus image or its LFS pointer. The reviewed
  source excludes the corpus subtree from implicit image copying and
  tests revision-bound transport. [Publisher](../../../scripts/docs.py) · [Test](../../../tests/scripts/test_docs.py)
- **F02 · The empty status region was hidden.** The prior rule could
  introduce the region at the same time as its announcement. The reviewed
  CSS collapses the empty margin while retaining the live region.
  [Search styles](../../theme/search.css) · [ARIA status technique](https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA22)

### Judgments and qualification

A1 passes because a collection-local addition needs no second inventory.
A2 passes because editable routes, evidence and illustrative claims have
separate authority. A3 passes through mdBook, Pagefind and Git LFS. A4
passes for one static build, the small excerpt and index, lazy search and
serialized promotion. FP-01–FP-07 are satisfied within this boundary.

G1/G2 pass for source ownership and fidelity, G3 for checks before
promotion, G4 for explicit asset and release effects, G5 for the selected
recovery scope, G6 for stable paths and aliases, G7 for bounded claims and
visible failures, and G8 for native mechanisms. CI-G1/G2 pass for typed
and attributable evidence. CI-G3 is outside serving retained assessments.
Rule impacts are none.

**Tested · 2026-11-08.** Read-only Python inspection of the `b0950d4b8`
prefix artifact checked 709 distinct TOC destinations, the five opening
routes, metadata and edit actions, and four image assets. At `60faba22e`,
discovery and summary construction found 710 canonical pages including
the generated directory. The corpus README was the only corpus chapter.
A `git cat-file --batch` comparison matched all 1,409 corpus pointers to
the manifest. `sha256sum` confirmed the exact Grinstead–Snell PDF. The
coordinator reported 49 docs tests passing at the reviewed revision and
both browser sizes and failure recovery on the preceding visitor build.
Exact release and anonymous retrieval remain release qualification.

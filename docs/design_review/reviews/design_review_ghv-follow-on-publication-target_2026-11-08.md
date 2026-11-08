# GitHub visitor follow-on publication target review

**2026-11-08 · Design/target · Holistic · Independent reviewer `ghv_target`. Decision · Accept scoped.**

Use the existing static publisher for the three retained exhibits, a
discoverable reading order and an honest search failure state. The workload
is serialized single-operator releases and independent static reads.
Historical Reader recovery and overlapping releases are outside this scope.
The trigger for revisiting admission is a need for concurrent eligible
releases. [Scoped refresh at `051b37aa4`](../audit/README.md#ghv-follow-on-publication-refresh) · [Prior publication review](design_review_github-pages-publication_2026-11-08.md) · [Standard](../design_principles/standard.toml)

| Operation | Inputs and owner | Required fidelity |
| --- | --- | --- |
| Publish exhibits | Retained producer outputs, independent assessments and authored explanations | Preserve selected locators, run and cut, receipt identities, assessment boundaries and the illustrative policy label. |
| Derive navigation and metadata | Discovered pages and presentation policy | Preserve path, scope and authored title. The home aliases share one canonical URL. |
| Prepare and serve search | Checked HTML and bundled Pagefind | Prepare one index, load it on demand and distinguish initialization failure from zero results. |
| Promote a release | Checked artifact and guarded Pages job | Promote the selected revision and verify what is live before a later release or retry. |

A new reference page inherits membership and scope from discovery. Native
mdBook nesting retains its output path. The sidebar JavaScript rebases the
shared links using the page's path to root. The no-script iframe uses
`toc.html`. Offline link checks alone cannot establish the dynamically
inserted links. Verify a deep project-prefix page in the browser and derive
sharing titles from the authored page rather than the navigation label.
[Pinned sidebar](https://github.com/rust-lang/mdBook/blob/v0.5.4/crates/mdbook-html/front-end/templates/toc.js.hbs)

The variance attachment retains textual scope and its separate assessment.
The antecedent retains the demonstrative, full antecedent extent and
private product standing. The dossier retains two root-qualified members
and excludes separately supported material outside the root. The nine
checked citation decisions and four upstream misses have different
populations. The explicit JSON subset serves inspection without copying
full records into Pages. [Variance and citation assessment](../evidence/2026-11-08_nce-full-book/review/scoped-outputs.md) · [Antecedent receipt](../evidence/2026-11-07_nce-source-linguistics/records/nce.constant-density-antecedent.json) · [Dossier receipt](../evidence/2026-11-06_wce-completion-repair/records/wce.repair-rooted-dossier.json)

Pagefind can emit an import error and resolve the load promise. Its
backend can also be assigned before filters are ready. Keep controls gated
until filter readiness and the Current selection. Preserve a visible,
keyboard-accessible recovery control, including when the UI module fails.
Guard close and reopen against stale completion. [Pinned Pagefind instance](https://github.com/pagefind/pagefind/blob/v1.6.0/pagefind_ui/component/core/instance.ts#L630)

A1 is satisfied by collection-local navigation and explicit assets. A2
preserves receipt identity, evidence status and load states. A3 composes
mdBook, Pagefind and the checked deployment route. A4 uses one static
build, a small projection and lazy indexing data. FP-01–FP-07 are
satisfied within that target. G1/G2 pass for authority and retained
meaning, G3 for publication checks, G4 for explicit effects, G5 for
serialized recovery, G6 for preserved aliases and scope, G7 for bounded
claims, and G8 for native mechanisms. CI-G1 and CI-G2 pass for attributed
typed claims and explicit evidence closure. CI-G3 is outside serving
retained assessments.

**Tested · 2026-11-08.** Read-only SHA-256 comparisons matched the finalized
scoped report, antecedent and delivery, and dossier preflight and result.
`gh run view 42484094468` confirmed the deployed baseline. Candidate
browser journeys and archive inspection were `not_run`. Rule impacts are
none. The assembled review and exact-revision qualification follow.

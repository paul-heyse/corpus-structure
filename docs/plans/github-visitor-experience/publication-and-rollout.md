# Documentation publication and GitHub rollout

**Status · 2026-11-08. Complete.** Owns the GHV-01 and GHV-05 designs. The
[coordinator](../github-visitor-experience_2026-11-08.md) owns findings and
execution status. The [functional review](../../functional_reviews/github-visitor-experience_2026-11-08.md#O04)
records the inspected failures and the isolated workaround results.

<a id="GHV-01"></a>

## GHV-01 · Repair the publication inputs

The documentation publisher owner compares the selection in a clean Git
checkout with LFS disabled and a hydrated checkout at the same revision.
Replace the broad evidence README glob with a positive selection in
`docs/site.toml`. Select the evidence collection index and each authored
top-level evidence index by pattern. Explicitly select nested authored reviews
that belong in the site, including the whole-book review. Inspect the
current membership difference before finalizing the selection. Retain every
authored narrative chapter that serves the existing site. Generated bundle
READMEs remain reachable through existing links to tracked paths at the build
revision. Keep the membership independent of file hydration and leave raw
evidence in its current custody.
[Site config](../../site.toml) · [Existing publisher](../../../scripts/docs.py) · [Whole-book review](../../design_review/evidence/2026-11-08_nce-full-book/review/README.md)

Correct the source-population evidence owner by naming `SOURCES.tsv` as a
checkout-local inventory in text and keeping the existing link to the tracked
`available-originals.json`. Use that inventory as the public route. Keep
strict link and fragment validation, stable section IDs, search scopes, and
atomic replacement of the last-good artifact. Inspect the candidate for
additional checkout-only inputs, LFS pointers or raw payloads being copied, and
unresolved links before handing it to GHV-05.
[Source-population evidence](../../design_review/evidence/2026-11-04_m1-source-populations/README.md) · [Tracked inventory](../../design_review/evidence/2026-11-03_m1-population/available-originals.json) · [Publication and custody](../../publishing.md)

Use the declared mdBook `0.5.4`, Pagefind `1.6.0`, and lychee `0.24.2` pins
and the existing `just bootstrap-docs` on an unprepared host. Keep this lane
product-independent and LFS-disabled. Exercise the discovery/link regression
with an authored nested review, a generated bundle README in both hydrated and
pointer form, and a selected evidence link. Check that the authored pages are
indexed and the bundle stays linkable without becoming a chapter. Confirm the
source-population page from a checkout with the ignored directory absent.
[Existing publisher tests](../../../tests/scripts/test_docs.py)

**Closure.** Both GHV-F01 and GHV-F02 have focused evidence and the committed
artifact passes the clean checkout checks below without the review's temporary
workarounds. Compare the intended canonical page inventories, using the same
source revision. A failed build retains the previous good artifact and blocks
deployment.

<a id="GHV-05"></a>

## GHV-05 · Publish the existing site and complete GitHub settings

Record the operator-confirmed publication change through a superseding ADR
for ADR-0003 and update DESIGN §2 and publishing operations in the same
decision slice. Keep Markdown and the site configuration authoritative for
authored content and publication membership. Keep existing ordinary CI artifact
delivery. Follow the repository's scoped design and assembled review cadence
for the changed publishing boundary.
[ADR-0003](../../adr/0003-publish-docs-site.md) · [DESIGN §2](../../design/DESIGN.md#section-2) · [ADR procedure](../../../.claude/skills/adr/SKILL.md)

Extend the existing documentation workflow. The build uses LFS-disabled
checkout, focused docs tests and the project-prefix check, and uploads the
checked directory as the ordinary CI artifact. Keep its documentation path
filters and include any new render recipe source paths relevant to those
checks. PRs exercise that build with read-only permissions. Only successful
push or manual builds from `refs/heads/main` run the Pages packaging steps
and reach deployment. Upload the same checked directory as the Pages artifact
with hidden files enabled. Keep `.agents`, `.claude`
and `.nojekyll` in the artifact and inspect its member list for generated raw
payloads, repository internals, and symlinks. The Pages deploy job depends on
that successful build and uses `github-pages`, serialized deployment and
`pages: write` plus `id-token: write`. In that job, run `configure-pages`
against the enabled site before deploying the artifact. The build already
checks the agreed project prefix, so it can complete without Pages credentials.
[Current workflow](../../../.github/workflows/docs.yml) · [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

Pin the reviewed action commits. Use `actions/configure-pages` v6.0.0 at
`45bfe0192ca1faeb007ade9deae92b16b8254a0d`,
`actions/upload-pages-artifact` v5.0.0 at
`fc324d3547104276b827a68afc52ff2a11cc49c9`, and `actions/deploy-pages`
v5.0.1 at `368f82528645a54fb793d4d04e342629a3f51346`. The pinned upload
action's `include-hidden-files: true` preserves the hidden documentation
paths while omitting `.git` and `.github`. Use the deployment output URL for
verification and homepage configuration.
[Configure action](https://github.com/actions/configure-pages/blob/45bfe0192ca1faeb007ade9deae92b16b8254a0d/action.yml) · [Upload action](https://github.com/actions/upload-pages-artifact/blob/fc324d3547104276b827a68afc52ff2a11cc49c9/action.yml) · [Deploy action](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/action.yml)

Use the installed `gh` 2.103.3 where it provides the needed repository edit
flags. Confirm the effective account and repository before effects. Apply the
About description with the README.

> Document intelligence for building connected, source-grounded knowledge with
> structured extraction, semantic linking, and granular evaluation.

Add `document-intelligence`, `information-extraction`,
`knowledge-representation`, `natural-language-processing`,
`semantic-search`, `gliner`, and `docling`. Add the proposed
`knowledge-graph` and `entity-resolution` topics only if the final landing
page gives a concrete evidenced route into those capabilities. Use the
repository settings to select GitHub Actions as the Pages source, or its
REST equivalent with `build_type=workflow` and adequate permission. Upload
the checked social preview from GHV-04 through Settings → Social preview.
Set About homepage after the live checks pass. Re-read repository metadata and
inspect the uploaded preview. The rollout needs settings authority and an
authorized remote revision on `main`.
[GitHub CLI flags](https://cli.github.com/manual/gh_repo_edit) · [Pages settings](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) · [Pages API](https://docs.github.com/en/rest/pages/pages#create-a-github-pages-site) · [Social preview upload](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)

Qualify locally first, confirm the authorized remote revision and Actions
source configuration, and then verify the default-branch deployment. If
authorization or remote source is missing, record the exact blocker. If
deployment fails, keep the checked artifact, diagnose the failed job, and
retry an eligible `main` run once its prerequisite is corrected. For a
public regression, use the normal workflow to deploy a known-good authorized
revision, or leave the homepage unset during initial rollout until a
verified deployment is available.

## Qualification

1. **Publisher checks.** Run `just docs-test` when the publisher changes, then
   `uv run ci docs check` on final source. Run the CI-equivalent prefix
   build from a clean LFS-disabled checkout. Use the actual candidate
   deployment directory for the next checks.

   ```sh
   UV_LOCKED=0 uv run --no-project --offline --no-python-downloads python scripts/docs.py check --base-url /corpus-structure/
   ```

2. **Reader journeys.** At 1280 × 800 and 390 × 844, check the GitHub README and
   the locally served prefix artifact. Follow the example to the evidence,
   check the shared SVG and its full-size link, and find architecture,
   evaluation and reproduction. Open Pagefind with Current selected, then
   exercise Reference and Everything. Check actual hidden path retrieval.
3. **Hosted qualification.** Record the default-branch deployment. The operator selected direct pushes, so a
   hosted PR run is `not_run`; check the deployment guard locally. Verify the live prefix, working navigation and
   search, evidence and asset links, hidden paths, and the About metadata
   and preview. Record the deployed revision, outcome and URL in the
   coordinator. Local checks establish only the local artifact boundary.

The [assembled design/target review](../../design_review/reviews/design_review_github-pages-publication_2026-11-08.md)
records the missed original pre-activation review and the accepted serialized
release scope. The [coordinator](../github-visitor-experience_2026-11-08.md#ghv-audit-closure) records deployment.

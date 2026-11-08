# GitHub visitor edit action target review

**2026-11-08 · Change/target · Holistic within the edit control · Independent reviewer `ghv_target`. Decision · Accept scoped.**

The edit action should use the existing `Page.path` as its editable source
identity. The live examples at `8b694c67b` point into the staging `src/`
directory. mdBook concatenates the source directory and chapter path for
its template. Adapt the native `rel="edit"` control using the repository,
branch and encoded page path. Omit it on the generated directory. A new
nested chapter uses the same mapping and the home alias uses the README.
Historical receipt links continue to carry the build revision.
[Scoped refresh](../audit/README.md#ghv-follow-on-publication-refresh) · [Pinned renderer](https://github.com/rust-lang/mdBook/blob/v0.5.4/crates/mdbook-html/src/html_handlebars/hbs_renderer.rs)

A1 is satisfied by local adaptation. A2 is satisfied by distinct editable
and immutable link identities. A3 is satisfied by retaining mdBook's
affordance. A4 is satisfied by the existing annotation pass. G1–G8 pass
for this design through its source owner, faithful action, generated-page
boundary, explicit effects, existing release route, stable aliases,
truthful label and native renderer. Product fact and evaluation gates are
outside this slice.

**Tested · 2026-11-08.** Live HTML inspection with `curl -fsSL` confirmed
the staged destination at the deployed baseline. Candidate qualification
was `not_run` in the review. The implementation check covers root, alias,
nested and generated pages. Rule impacts are none. The enclosing
publication boundary has its own review.

# Managed model and corpus reads

**Status:** Managed reads are present. CLIR-CA04–05 and CLIR-CA09 own the open corrections
and journey verification. The [coordinator](../cli-reporting_2026-11-07.md#completion-audit)
owns scope and integrated acceptance. This plan consumes [O03](../../functional_reviews/cli-reporting_2026-11-07.md#O03)
and [O04](../../functional_reviews/cli-reporting_2026-11-07.md#O04).

<a id="CLIR-03"></a>
## CLIR-03 · Inspect bound model artifacts

Add `ci model change inspect PREVIEW_ID` for target, authority, reviewed effects and
semantic impact. Provide named `patch` and `discovery` views. Include changed paths and
total versus selected hunks and mark absent or unavailable impact and discovery separately.
Use the existing digest-checked `ChangePreview` as the authority for the patch and proposed
effects. A read-only candidate route, `ci model change inspect-candidate CANDIDATE_ID`,
shows the native candidate's preview/release identity, target and registration standing
where established. Show the next authorized command without taking the effect. Registration
and deployment retain their existing checks and exact candidate binding.

Use `ResultStore.lease` across the full authenticated access. Authenticate action,
settlement and role, then use the managed descriptor and the owner decoder's digest and
identity checks. A bounded render can occur after releasing the lease once all its
inputs are copied and authenticated. Keep the lease through any approved streamed
read. Expose role, missing, expiry, substituted artifact, unavailable content and
verified empty states only as established by the owner. A physically retained item can
be readable under current policy even when it cannot become a new dependency. Hold and
retirement rules remain with the store. Generic content browsing requires multiple
compatible roles and a defined authorization and access model. [Managed read boundary](../../../python/corpus-structure/src/corpus_structure/cli/managed.py#L545) ·
[Model artifact verification](../../../python/corpus-structure/src/corpus_structure/cli/model.py#L56)

Select hunks before rendering. Rich 15.0.0 `Syntax(code, "diff", line_range=...,
highlight_lines=...)` gives bounded annotated excerpts. Supply a bounded source slice
with correct line numbering when `line_range` alone would leave a large render input.
Route text through the terminal-safety policy before highlighting. Validate whether a named
script consumer needs exact patch bytes. If selected, specify the explicit stream contract,
byte limits and authorization, and gate it on [CLIR-06](streams-and-diagnostics.md#CLIR-06).
[Source presentation](../../libraries/python_introspection/rich.md#6-advanced-source-code-presentation) ·
[Pinned Syntax source](https://github.com/Textualize/rich/blob/v15.0.0/rich/syntax.py)

Verify digest mismatch, wrong action or role, expired dependency, substitution and
collection during the read. Compare selected hunks and discovery with the bound preview.
Show that neither preview nor candidate inspection registers, applies or deploys anything.

<a id="CLIR-04"></a>
## CLIR-04 · Inspect corpus evidence and compose typed selections

Add `ci review inspect --result RESULT_ID` alongside existing detached path inspection.
Require exactly one source. Resolve the role from the managed manifest, keep a lease for
verification, and root member opens at the authenticated bundle directory descriptor.
Reuse the detached verifier's digest, relationship and member checks through a shared
owner read interface. Preserve ordinary and evaluated scope, original source completeness,
witnesses and assessment coverage. On large bundles, account for full verification cost
and lease duration. Add a manifest-only view only for a named decision that can use
unverified metadata, explicitly label it and keep verified inspection available.
[Review CLI](../../../python/corpus-structure/src/corpus_structure/cli/review.py) ·
[Bundle owner](../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py)

For `review export` and `review export-evaluated`, compose a selection through the
existing positional operand, using `-` for stdin and the existing path for intentional
file input. Prefer Typer 0.28.0 `get_binary_stream("stdin")` for bounded bytes into
Pydantic `ReviewSelection.model_validate_json`. `FileText` is suitable if the owner
accepts decoded text and the byte bound is enforced before decoding. A path parameter
with `allow_dash=True` only admits the token. Bound bytes on both input routes before
validation. Validate once before authority acquisition or exposure. Keep the existing
managed replay selection and the evaluated route's independent authority and exposure
receipt. Check the model preview's existing `-` read for the same unbounded-input defect
if it shares the resulting boundary. [Typer file streams](../../libraries/python_introspection/typer.md#6-file-streams-and-unix-style-command-composition) ·
[Typer file API](https://typer.tiangolo.com/tutorial/parameter-types/file/) ·
[Pydantic JSON validation](https://docs.pydantic.dev/latest/api/base_model/#pydantic.BaseModel.model_validate_json)

Use `source inspect` as the precedent for bounded typed corpus reads. Choose views for
a named operator decision with the existing run, cut, release and evidence identities.
Keep owner ordering and continuation, and keep ordinary inspection and evaluator-only
interpretation separate. Use existing fitting applicability for protected data
availability. Where an applicable read depends on a new enrichment producer, link its
existing owner and prerequisite. [Source inspection](../../../python/corpus-structure/src/corpus_structure/cli/source.py) ·
[Fitting routes](../../../python/corpus-structure/src/corpus_structure/cli/eval.py) ·
[Enrichment ownership](../next-corpus-enrichment_2026-11-07.md)

Verify the same authorized report from detached and managed input, including nested
member integrity and a substitution attempt. Test bounded valid stdin, malformed and
oversized selections, a missing prerequisite and distinct sources of incomplete coverage.
Verify evaluated input still requires the correct authority and exposure and that retained
replay can recover the admitted selection.

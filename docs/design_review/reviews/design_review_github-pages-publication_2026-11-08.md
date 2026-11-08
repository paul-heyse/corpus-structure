# GitHub Pages publication design review

**2026-11-08 · Design/target · Holistic · Independent reviewer `publishing_review`.**
**Decision · Accept scoped.** Reuse the checked documentation artifact for Pages.
The source and receipt authorities are visible in both reading surfaces. The
single-operator release route keeps build and promotion separate.

## 1. Scope and evidence

The assembled source is `248b05cd2`. The [diagnostic refresh](../audit/README.md#documentation-publication-refresh--2026-11-08)
was published at `be4796200`. The [standard](../design_principles/standard.toml)
selects core 3.3, efficiency heuristics 1.0, code-intelligence 1.4 and the binding.
The required pre-activation review was missed. This review covers the assembled
boundary after the original activation and precedes the corrective release.

The target is a stable journey from GitHub or Pages to source-linked examples.
The workload is one operator releasing static documentation on eligible `main`
pushes or dispatches, with independently served reads. Product execution,
historical Reader recovery and ordering between overlapping eligible releases
are outside this judgment. [GHV-05 and completion audit](../../plans/github-visitor-experience_2026-11-08.md#GHV-completion-audit)

## 2–4. Responsibilities, contracts and composition

| Owner | Contract and effect |
| --- | --- |
| Authored Markdown and evidence producers | Markdown narrates the example. Retained results and independent assessments establish scoped claims. The examples attribute candidate retrieval, selection and the witnessed declaration separately. |
| Site policy and publisher | Explicit membership, prefix and tool versions govern derived HTML, navigation and search. Links to omitted tracked objects carry the source revision. Untracked targets receive a local-preview label. |
| Documentation job | A checkout with LFS disabled feeds the isolated tests and checked prefix build. Both uploads use the same directory. The build has read-only repository permissions. |
| Deploy job and Pages | Eligible main events promote the run's artifact after the documentation job succeeds. The deploy job holds Pages write and OIDC permissions. GitHub owns deployment state and serving. |

The `X` example gives the candidate rank and zero selected edges in run 207,
cut 287. The `Z` example preserves the run 253, cut 350 declaration identity.
The original assertion for the same contribution checks the exact formula and
declaration spans and the `declares` kind. The two outcomes have separate
receipts. [Examples](../../examples/README.md) · [Exact Z assertion](../evidence/2026-11-07_nce-comparison-model-links/replay_links.py)

Discovery, rendering, indexing and offline links produce one checked tree for
both uploads. Static reads need no product execution or evidence hydration.
[Site policy](../../site.toml) · [Publisher](../../../scripts/docs.py) · [Workflow](../../../.github/workflows/docs.yml) · [Pages workflow contract](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

## 5. Change and failure scenarios

- **Authored evidence beside generated output.** A dated top-level index
  enters via its declared pattern. A deeper authored page needs one explicit
  selection. The generated bundle README stays an omitted source reference
  in hydrated and pointer checkouts. Existing fixtures cover both forms. The
  prior completion audit authenticated the pointer objects and observed
  identical selection.
- **Failed build or deployment.** Render, index or link failure precedes local
  replacement and prevents the deploy job. A Pages failure after a successful
  ordinary upload leaves that artifact available subject to retention. An
  action can fail while polling after it has requested promotion. Verify the
  live revision before retrying from corrected main.
  [Publisher tests](../../../tests/scripts/test_docs.py) · [Pinned deploy action](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/deployment.js)

## 6–7. Gates and findings

| Gate | Scoped verdict |
| --- | --- |
| G1 Authority | Pass. Receipts, assessment, publication membership and deploy state have distinct owners. |
| G2 Fidelity | Pass. Candidate retention and witnessed selection carry separate exact identities. |
| G3 Validity | Pass. Invalid publication selections and failed checks prevent promotion. |
| G4 Effects | Pass. Build and replacement effects are explicit. Promotion has a separate guarded job. |
| G5 Recovery | Pass for serialized operation. The checked tree precedes both uploads and recovery checks what is live. |
| G6 Reuse | Pass. One checked snapshot supports both artifact consumers. |
| G7 Evidence | Pass. The examples retain the Reader refusal and distinguish native results from editorial illustration. |
| G8 Library fit | Pass. Local logic composes the established tools around repository-specific membership and transport. |
| CI-G1–G3 | CI-G1 passes for attributed, typed X/Z claims. CI-G2 passes for the inspected snapshot, with live verification assigned to release qualification. CI-G3 does not apply to publication of retained assessment. |

FP-01–FP-06 are satisfied by the named owners, revision contract and separate
build and deployment concerns. FP-07 is satisfied for serialized static
publication.

<a id="F01"></a>

**F01 · Overlapping eligible releases can reach deployment out of source
order.** The concurrency group serializes deploy jobs. An older slower build
can still arrive after a newer build. GitHub supplies no source-order guarantee,
and the pinned deploy action submits its run's artifact and SHA without a
client-side freshness check. This is a workflow inference. The review observed
no public regression. The runbook now requires one release in flight and
verification of its live revision before initiating another eligible run.
Recover by dispatching the current corrected main. Revisit admission if
overlapping eligible releases become required.
[GitHub concurrency contract](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency) · [Publishing operations](../../publishing.md)

## 8–9. Alternatives and execution fit

Artifact-only delivery drops the public reading route. A separate site could
support a distinct audience, with a second publication selection and
authority-to-reader path. For the shared collection, mdBook renders, Pagefind
indexes, and lychee checks local links before reuse by both uploads. A
workflow-wide concurrency group could limit simultaneous work but cannot by
itself establish source freshness. The current single-operator workload does
not justify an additional freshness mechanism.
[ADR-0071](../../adr/0071-github-pages-publication.md)

## 10–11. Verification and rule impacts

**Tested · 2026-11-08.** Anonymous `curl -fsSL` retrieval passed for both raw
receipts at `5bddd141b`. `sha256sum` matched the X payload to its Git LFS
pointer. `jq` confirmed the X selection outcome and Z contribution identity.
`gh run view 42481958715` confirmed the prior build and deployment succeeded.
The completion audit records the previous archive inspection and hydrated
inventory comparison. Hosted failure injection was `not_run`. The recovery
judgment rests on source and the deployment contract.

**Rule impacts · None.** The runbook clarifies the scoped release sequence.
The coordinator owns GHV-F05 disposition. F01's revisit trigger is overlapping
eligible releases.

## 12. Decision

| Judgment | Scoped verdict |
| --- | --- |
| A1 Locality | Satisfied. An authored page changes its owner and, for deeper pages, one selection. |
| A2 Domain model | Satisfied. Membership and revision govern transport. The receipts preserve different semantic outcomes and identities. |
| A3 Composition | Satisfied. The deploy job consumes the checked tree through a run artifact and delegates hosting to Pages. |
| A4 Execution fit | Satisfied. One build supports both artifact consumers and leaves raw evidence at its source. One release at a time fits the current workload. |

**Accept scoped** for the static documentation boundary and serialized release
operation. Exact-revision release qualification is a separate check.

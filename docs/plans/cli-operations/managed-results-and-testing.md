# Managed invocation results, tests and repository maintenance

**Proposed.** Companion to the [CLI operations coordinator](../cli-operations_2026-11-07.md).
Owns CLI-02 and CLI-03. The receipt supervisor owns process evidence and classification.
Domain data, observability archives and published evidence have separate custody.

<a id="CLI-02"></a>
## CLI-02 · Create, retrieve and expire managed results

Allocate an opaque invocation ID and private workspace at dispatch. Use ignored `build/ci/`
under the resolved development checkout and a deployment-owned persistent state directory on
an installed host. Announce the ID early, including on the diagnostic stream in JSON mode.
Publish a small manifest with action and scope, effective redacted target, applicable source and
runtime bindings, stage and outcome, relevant authoritative IDs, related invocations and named
artifact roles. Domain selection IDs remain the IDs used for semantic reads. A copy or external
delivery of the same result preserves its ID. Retry and recomputation create a new invocation
with its own context and a reference to the original.

Use `ci results list` with bounded page and scope, `show RESULT` for artifacts and retention,
`watch RESULT` over available status or receipt events, and `export RESULT` for named deliverables
with optional destination. No read exposes producer-private staging. Bounded pages control emitted
work. Directory enumeration can still grow with the retained population, so start with scoped
workspace discovery and short retention. Add an index if observed repeated lookup or sorting
becomes costly enough to justify its coordination and recovery obligations. Distinguish expired
from unknown when an existing lifecycle record can do so. A compact expiry marker becomes useful
if an actual consumer needs that distinction beyond cleanup.

**Publication and concurrency.** Use same-filesystem staging and Python 3.14 `os.replace()`
for one complete manifest update. Reuse the existing Linux `renameat2(RENAME_NOREPLACE)` bundle
publisher for a complete directory, factoring shared mechanics at its publication boundary if
needed. Stage on the destination filesystem for external copies and refuse an occupied destination.
A manifest can expose settled artifacts only after publication. For the supported local Linux
state root, use Python 3.14 `fcntl.flock()` with stable per-result lock identity to coordinate
producer, export, hold updates and cleanup, or reuse an existing equivalent coordination
primitive at that boundary. Check eligibility again while holding the owner lock. Preserve
lock identity across competing discovery and deletion, including abandoned producer recovery.
Only managed paths proven inside the owned root may be removed. Treat path substitution and
untrusted manifest paths as refusal conditions. Stage and identify incomplete publication
so a later inspection or retry can recover. Atomic rename gives visibility atomicity. A
power-loss durability promise would require its own storage assumptions and verification.
[Python `os.replace`](https://docs.python.org/3.14/library/os.html#os.replace) ·
[Python `fcntl.flock`](https://docs.python.org/3.14/library/fcntl.html#fcntl.flock) ·
[Linux `renameat2`](https://man7.org/linux/man-pages/man2/rename.2.html) ·
[Existing publication owner](../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py)

| Class | Minimum retained result and protection under CLI-RC02 |
|---|---|
| Active or unsettled work | Keep producer scratch, staging and transport until process settlement and cleanup are established. A dead owner alone does not settle surviving children. Keep a bounded diagnostic excerpt where needed. |
| Ordinary success | Receipt, named deliverables and authoritative references. Expire after **one day** from settlement if unreferenced. |
| Failure or interruption | Identity, exact stage, exit and cleanup outcome plus the evidence needed for diagnosis or reconciliation. Expire after **one week** from settlement if unreferenced. |
| Model or migration candidate | Keep exact candidate and predecessor bindings while a pending approved change or dependent result uses them. An unreferenced success uses the one-day window. A stale preview can be inspected while retained and needs a fresh preview before application. |
| Active review, qualification and delivery | Hold dependencies until the consumer settles and its required evidence is published or released. Protect any live export. Publish the necessary durable evidence through the existing evidence owner. |
| Committed evidence, source and functional data | The existing owners govern custody. GC cannot select these classes. |

`ci results gc` previews by default. `--apply` reuses the same eligibility rule and performs
the effect. A host can schedule the same operation if recurring cleanup warrants it. `show`
explains holds and expiry. Explicit evidence retention promotes only the necessary closure and
keeps its references. Compact raw test data only after demonstrating the retained representation
still supports classification, replacement and audit. Rich's terminal capture is presentation.
[Durable evidence custody](../../design_review/evidence/README.md)

**Acceptance.** Retrieve settled and running invocations from a second process. Deliver to an
optional destination and verify identity and content. Race GC with an active export, producer,
or dependency hold, and with interrupted publication. Use controlled time to prove both expiry
boundaries and exact collection eligibility. Protected candidates and durable evidence remain
accessible. A missing local delivery never triggers an implicit provider or extraction rerun.

<a id="CLI-03"></a>
## CLI-03 · Route tests and maintenance through owned recipes

`ci test` selects the complete applicable suite for the resolved checkout with zero operands.
The installed adapter invokes the established `just test-all` and, where applicable, the separate
`just test-native-faults` owner. Extend the recipes and existing `scripts/test_receipts.py`
interface to accept an internally allocated result workspace and preserve direct recipe defaults.
Use one managed invocation containing separate native lane receipts. Keep the existing
supervisor's responsibility for child process groups, exit records and cleanup. Treat a missing
required lane prerequisite as blocked and a valid empty selection as its own outcome. A lane
selector or declared pytest selector is a deliberate narrower run. After a command-specific
`--`, accept bounded pytest passthrough. Keep CLI parsing strict elsewhere and keep the user's
argument vector intact through `just` and the supervisor. Reserve receipt paths, required plugins
and qualification policy for their owner.

**Native tooling.** Reuse pytest-xdist **3.8.0** `-n auto` and `--dist=loadgroup` for the ordinary
parallel lane, strict markers and config, and the existing exclusion of shared-cluster faults.
Keep the owner-defined exclusive fault invocation at `-n 0` after ordinary work has settled and
the native harness can acquire its existing exclusive lease. Diagnose parallel failures in the substrate owner and preserve the
actual resolved lanes and selectors in receipts. Reuse `cargo nextest list --release --workspace --message-format json` and
`cargo nextest run --release --workspace --profile qualification --no-tests=warn` through
the supervisor. Preserve `INSTA_UPDATE=no`. The profile currently writes to a shared JUnit
path per target directory. Bind report collection to the invoking campaign by isolating the
report path or serializing report-producing nextest work and receipt capture at that boundary.
Preserve shared compilation caches. The supervisor's existing process-group use of Python 3.14 `subprocess.Popen(start_new_session=True)`
and its settlement record are the child boundary. Forward cancellation through the additional recipe process layer to the
receipt supervisor before any forced teardown. The inner supervisor owns its separate
worker process groups. An empty native selection or startup warning cannot establish passing
functionality. Record actual toolchain versions with applicable results.
[xdist 3.8.0 distribution source](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/docs/distribution.rst) ·
[nextest run options](https://nexte.st/docs/running/) ·
[Python process supervision API](https://docs.python.org/3.14/library/subprocess.html#subprocess.Popen) ·
[Existing recipes](../../../justfile) · [Receipt supervisor](../../../scripts/test_receipts.py)

`ci test retry RESULT` uses the prior receipt, existing `write_unresolved()` and a check against
current collection, source and context. A broader affected selection is explicit and explained.
`ci test coverage RESULT…` uses the existing `classify()` and declared required manifests.
Report the original attempt outcome separately from exact replacement coverage and unresolved
identities. Preserve native context, failures and interruption records. A retained classifier
input needs a hold while it is required for qualification. Use truthful stage and count events
for parent progress and a direct remedy in final output.
[Test policy owner](../test-audit-resolution_2026-11-05.md) ·
[Test assessment companion](../../design_review/design_principles/core/test-assessment.md)

`ci check` and named check routes map to established readiness, type, lint, hygiene, documentation,
model, evidence and verification recipes. Split read-only variants where needed. Existing
`ruff` applies fixes and `turn-end` formats and regenerates metadata. Give formatting, generation,
ADR creation and deliberate evidence promotion explicit effects. Keep ownership and defaults in
the recipe and tool layers. Results are managed where retrieval or reconciliation matters.
Return a small typed outcome for short actions. Do not copy all tool streams.

**Acceptance.** Demonstrate native argv through the installed CLI and the actual recipe owner,
including a zero-argument campaign, an explicit narrower selection, and an unavailable exclusive
prerequisite. Exercise a failed ordinary attempt, applicable replacement and exclusive lane.
Verify the declared union without rewriting the failed receipt. Cancel an installed invocation
and confirm child-group settlement or explicit cleanup failure. Retry by ID from a second process. Exercise concurrent campaigns to
verify receipt isolation and exclusive native prerequisites. Check with a deliberately fixable source issue and demonstrate that only the explicit fix path
writes it.

# Managed test review

**Status:** Proposed design companion; not started. **Created:** 2026-11-18.
This companion owns the design and acceptance of TDM-19. The
[coordinator](../test-domain-model-and-execution_2026-11-17.md#tdm-19) owns its state and
the disposition of [I06](../../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I06)
and [I07](../../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I07).

## Baseline and rationale

**Interface-checked by source inspection, 2026-11-18.** `ci test coverage` compares a required
selection with observations across attempts, `ci test failures` explains one attempt's failure
phases and native provenance, and `ci results inspect` reports operation standing and cleanup.
The N13 original and its retries show why the operator needs to see these together. The attempts
cover different source and context, and the unresolved nodes need a different action from a result
with unsettled custody. The existing commands serve narrower questions independently. The composed
view can reuse their classifications and custody checks without a second record store.
[CLI testing owner](../../../python/corpus-structure/src/corpus_structure/cli/testing.py) ·
[Result inspection owner](../../../python/corpus-structure/src/corpus_structure/cli/result_inspection.py) ·
[ADR-0069](../../adr/0069-cli-operations-custody.md)

## TDM-19 — Review an original selection and its attempts

**Proposed.** Add read-only `ci test review ORIGINAL [ATTEMPT...]`, with result IDs in caller order.
The original supplies the required lanes and selection. Assess supplemental attempts using the
existing coverage rules. Use shared Typer options for a bounded page and continuation and for
`--json`. Compose the typed reports in the CLI, extracting reusable report builders where a command
currently owns one. Keep the existing authenticated receipt-reader boundary, including the
supervisor's descriptor route. Reuse a read or classification where the projections share it.
The composed command calls no sibling command and reads no rendered terminal output.

The report shows the original denominator and its availability, each attempt's lane outcomes and
source/context identities or their absence, a bounded page of unresolved logical identities with
reasons, and custody and cleanup standing. Keep selection, native provenance and functional
outcomes distinct. Mixed-source or mixed-context attempts can add observed identity coverage;
qualification still follows the existing source, context and lane rules. Missing receipts and
unfinished lanes retain their actual standing. Handle unavailable, unauthorized, or malformed
results through the existing typed error boundary. Leases, permitted live observation roles,
settled reads, redaction, and paging use the existing result owner. Prefer bounded projections to
loading full diagnostics for every attempt. [Managed result owner](../../../python/corpus-structure/src/corpus_structure/cli/managed.py) ·
[Receipt classifier](../../../scripts/test_receipts.py)

Show an applicable existing action, such as watching active work, resolving custody, or issuing
an exact retry from the appropriate attempt. Review itself performs no execution, cleanup, or
custody transfer. A successfully delivered review can describe a failed or interrupted attempt.
Read and delivery failures retain the CLI's existing nonzero outcomes. Use Rich static tables for
the human view and one typed JSON document on stdout, including when stdout is piped. Update the
existing command reference through its owning route as part of CLI delivery.

**Acceptance.** Use retained or representative managed receipts for an original with exact
retries and remaining failures, incomparable attempts, an interrupted attempt with cleanup
settled, and a running or custody-unsettled attempt. Compare the applicable findings and next
actions with `coverage`, `failures`, and `results inspect`. Exercise missing receipt fields,
redaction and bounded continuation, and check that no result state or custody changes. Assert that
human and JSON views preserve the distinctions and that piped JSON is a single document, with
attempt outcomes distinct from command exit status. The package can start on existing receipts
after TDM-00's baseline read. Final TDM qualification exercises the implemented command in TDM-18.

## Reporting foundation and conditional extensions

Use incremental pytest-reportlog, qualification events, and managed manifests for review,
analysis, and retries. Preserve JUnit for its existing exchange consumers. The
[reporting probe](../../design_review/evidence/2026-11-18_tdm-test-reporting/README.md) was
**Tested, 2026-11-18**, with pytest 9.1.1 and xdist 3.8.0. `pytest-json-report` supplied useful
phase details and item metadata, but the distributed snapshot omitted successful collection
items and the probe's session metadata sentinel was absent. SIGINT could label a setup-only item
passed, controller kill yielded no final snapshot, and worker loss could leave only setup detail.
Incremental events preserved available phases and synthetic worker-loss events. This was an
isolated compatibility probe; managed integration and performance were `not_run`.

The [coordinator's conditional dispositions](../test-domain-model-and-execution_2026-11-17.md#candidates-and-deferrals)
own when further work becomes relevant. Apply these acceptance boundaries if a trigger is met.

- **Phase timing.** Compose a bounded view from retained phase and scheduling observations. Keep
  setup, call, teardown, worker affinity, and campaign elapsed time distinct. Mark incomplete or
  incomparable scope, and distinguish overlapping phase totals from elapsed time.
- **Live progress.** Extend `ci results watch` if its existing view leaves a concrete diagnostic
  gap. Use an interactive Rich stderr console with automatic stream redirection disabled. Check
  terminal and pipe cases for clean JSON stdout and unchanged exit semantics.
- **Completion.** Use Typer completion over bounded, authorized local result metadata if repeated
  ID selection warrants it. Selecting a completion performs no operation.
- **External JSON exchange.** Compare an allowlisted, versioned export from a settled receipt
  with an opt-in `pytest-json-report` supplement for an identified missing field. Keep captured
  streams and credential-bearing diagnostics under the existing redaction and custody rules.
  Validate phase and attempt meaning in serial and xdist and the continued availability of
  inspection and exact retry when the final report is absent. Keep supplement fields separate
  from source, native deployment, and completion authority.

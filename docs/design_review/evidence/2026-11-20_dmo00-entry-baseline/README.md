# DMO-00 entry baseline

**Observed and interface-checked · 2026-11-20 UTC.** Source was `b233dfb3f309813e67de468f1155cea9015034d7`
on `main`, with no pre-existing product-source edits. The working tree already held 39 older
evidence-log changes and three untracked library references. Python was 3.14.10. Installed library
versions and the bounded redacted command projections are in [observations](raw/observations.json).
The [DMO-00 coordinator](../../../plans/domain-model-operability_2026-11-20.md#dmo-00) owns dispositions
and package readiness. This folder records observations and their limits.

## Current target observations

The initial `ci context show` and both `ci db status` calls for `deployment` refused because
`CORPUS_DEPLOYMENT__URL` was unset. Retry used an invocation-local explicit route from the archived
N42 deployment receipts. `ci` acquired the matching database name, OID, system identifier, Unix
socket and port as the reader and as maintenance. The status route is read-only for both purposes.
The configured target, acquired identity, private installed revision and checkout head are distinct.

| Target | Acquired identity and native revision | Current application standing |
| --- | --- | --- |
| Stage `deployment` | `corpus_structure_ddo_stage` OID `130661481`, PostgreSQL 18.7 on `/var/run/postgresql:5434`, installed `semantic_ddo_pe_n42`. Checkout head also N42. | `ci release check --release …` verified both Standard and Integrated archives. Neither of those releases is active in a stage project. `udm22-integrated-n42` exists at generation 0 with no selected release. The explicit archive checks establish archived bytes and projections, without selecting a project release. |
| Canonical `development` | `corpus_structure_dev` OID `131763263`, same cluster and PostgreSQL 18.7, installed `semantic_ddo_pe_n29`. Checkout head N42. | `nce-grinstead-snell-full-book` selects the N29 release at generation 5. Checked with the native reader's declared project projection in a read-only transaction. |

The draft plan named `siegrist-pdf` as the book. Its project-selecting check refused. The prior
activation and census named `nce-grinstead-snell-full-book`, and the corrected `ci release check`
reached `unsupported archive format` with the current reader. The retained first-adoption record
explains the N29 format boundary and carries its earlier version-matched archive check. The
bounded native query in this investigation verified the live project row and physical binding,
with no archive-integrity claim for N29 on current source. DMO-09 owns verified originals and
archive handling at adoption. The same read-only native projection established the exact absence
of a stage selection for these releases after the Integrated active check refused. Stage
archive reads used `ci release check` without `--native-proof`. [N29 adopted baseline](../2026-11-19_udm20-21-canonical/README.md)

## Retained behavior and collected provider scope

| Retained result | Boundary actually observed |
| --- | --- |
| `5cb34f8319ca4c71aaa504eccda86df1`, `aa866a00932f49129fb709da4ce09ad1` | Historical N42 Standard and Integrated deployment/admission passed. The live archive and project observations above answer separate questions. |
| `cfbf7d53d411497b85442167f7d2b70e` | Demand registered, then failed at transform executable acquisition before inference. The retained acquisition probe linked the mismatch to observed source reach. |
| `a145dbfebc9f4fc991ef7c511bb1cba2` | Rich journey passed in its recorded scope. |
| `8fefb2735f17470aaf9d8df805600379` | M1 published with real GLiNER. Readback exceeded its broad query bound. The original selected test remains failed. |
| `4fad3ac113214a0e87d4d94cd679da1e` | Event frame, fit and authorization published. Scorer attachment exhausted the watchdog. One test failed and two authority tests were unrun. |
| `dc348ca3780f4a96ad7dd8378389cc98`, `5b739336836c439b93d8fc47cd151d2e` | Actual N36 same-demand recovery passed and published three receipts. An unchanged repeat passed with zero new receipts. |

Managed inspections re-read those results at their original scope. The earlier causal evidence
holds the source attribution and runtime observations. `ci test collect --providers-only --json`
passed collection as `d425e078371747689bb112244292fbd7`. The retained scheduling projection has
24 selected identities, 11 requiring native acquisition, and zero workers. `ci test review`
correctly refused to treat this collection receipt as functional coverage. The scheduling view
supplies the inventory independently. Native/provider test execution, inference and qualification
were `not_run`. [Causal evidence](../2026-11-20_udm-operability-causality/README.md)

## Contract inspection

Preserve D1 key encoding and ADR-0100's current analyzed-scope identity until the proposed domain
is compared with independently authored Python and PostgreSQL vectors. Adopt PostgreSQL-native
numbers as the operator-approved transport direction. Preserve Draft 7 and the existing
SQL-request/client-result placement. D8 currently delivers `selected-source-search-exact-json-v1`
with `exact_json`, a native cut identity and a byte bound. A changed result shape or identity
equivalence needs a concrete rule decision in the responsible package. ADR-0141 is the accepted
continuation authority and supersedes ADR-0137. ADR-0139 and ADR-0140 retain current recovery and
original-producer custody. No new authoritative decision landed in this entry investigation.

## Evidence checks

`uv run ci evidence finalize 2026-11-20_dmo00-entry-baseline dmo00.entry-baseline` and
`uv run ci evidence index` passed. The scoped evidence check verified the new record, output hash
and provider inventory. `uv run ci evidence check` failed with the five existing DDO evidence
errors (`d6f5f26150c24b268fd46ad1c2ac4f82`). It reported no issue in the DMO-00 folder.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**Other**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Live DMO-00 target, rule and provider inventory baseline](records/dmo00.entry-baseline.json) | DMO-00 | passed | DMO-00, DMO-01, DMO-02, DMO-04, DMO-05, DMO-06, DMO-07, DMO-08, DMO-09 | 2026-11-20 |
<!-- evidence-index:end -->

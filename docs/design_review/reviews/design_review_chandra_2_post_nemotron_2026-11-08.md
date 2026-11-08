# Chandra 2 after Nemotron target review

**Proposed corrections · 2026-11-08.** Independent design/target review by the design reviewer
at `fab8f1e8d`, condensed for publication by the execution coordinator. Combined focus on
Docling, Chandra, PDF authority, custody, bounded readers and local GPU execution. The reviewer
reconciled the relevant portions of the existing diagnostic account with the reviewed source.
The expected workload is one or a few pages or crops from an exact published PDF. The
[coordinator](../../plans/chandra-2-post-nemotron_2026-11-08.md) owns dispositions.

**Decision.** Proceed with CH-01 qualification and revise the CH-02–03 contracts below.
Evidence-only delivery fits ADR-0040. The selected structure and knowledge rules require no
change. A future authority change belongs to CH-04. Fresh provider and functional checks were
`not_run` in this static review. The prior live panel remains bounded comparative evidence.

<a id="F01"></a>
## F01 · Archived source and current effect authority

An existing native request opens the source's release, requires its installed runtime and
creates the child under that same release. Observation publication needs the current task
attempt and same-release original custody. Authorize the exact integrated pin under its
producing archive, then create a current inspection task with that immutable dependency.
Check the protected link, original match and source run at admission. A different integrated
product over identical bytes is a decisive refusal control. Qualify original-image retrieval
across the same release boundary. [Native request](../../../python/corpus-structure/src/corpus_structure/semantic/native_requests.py) ·
[Fenced publication](../../../python/corpus-structure/src/corpus_structure/semantic/sql/pdf_observation.sql)

<a id="F02"></a>
## F02 · Provider role and selector authority

The incumbent selector adds every supplied observation before dispatch to its Nemotron
mapper. An additive role needs protected provider compatibility and an explicit
incumbent A/B/C allowlist before inputs, coverage or correspondence are created.
Keep the Chandra parser in the inspection path. Verify refusal of an otherwise successful
Chandra input and preservation of all three Nemotron roles. [Selector](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_reconciliation.py) ·
[Authority](../../adr/0040-forward-pdf-only-contracts.md#decision)

<a id="F03"></a>
## F03 · Request, attempt and replay identities

The incumbent receipt lookup keys source digest, recipe and page, while the observation
envelope requires a submitted PNG. Keep the authorized selection, effective image and recipe,
attempt, raw output and mapping identities distinct. Settle a pre-submission failure through
task custody without fabricating an image. Retain real image and available raw bytes before
interpretation. Distinguish cancellation, provider refusal, unspecified completion, malformed
or capped structures, provider-asserted blank and independently confirmed source blank.
A mapper change can replay raw bytes. A change in actual inference inputs needs a new
identity. [Receipt reuse](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_recognition.py) ·
[Observation guards](../../../python/corpus-structure/src/corpus_structure/semantic/sql/pdf_observation.sql)

<a id="F04"></a>
## F04 · Shared GPU and effective frame

The existing Nemotron sleep/wake helper has no shared exclusion. Establish one device owner
for participating Standard, Nemotron and Chandra work and settle cancellation, drain and
restoration before handing it off. Bound raster dimensions and pixels before allocation.
Record the exact submitted frame and qualify relevant downstream preprocessing. Prefer the
pinned Docling direct-image entry point if it preserves the effective contract. It avoids a
second conversion but leaves preparation to the caller. Exercise independently known corners
on an asymmetric rotated crop. [GPU handoff](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_capacity.py) ·
[Docling image entry point](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/stages/vlm_convert/vlm_convert_model.py#L483-L530)

<a id="F05"></a>
## F05 · Bounded downstream evidence read

Selected ancestry walks upstream. Verify the explicit downstream observation's direct
dependency on the exact integrated source. Bind both pins to continuations and raw artifact
access, apply scope before expanding children, and account for the complete response budget.
Use one Reader for CLI, MCP and the opt-in packet. Bind evidence to packet identity and
keep ordinary anchor resolution over admitted pieces. Preserve repeated occurrences and
the distinction between parser attachment and proposed caption association. [Native Reader](../../../python/corpus-structure/src/corpus_structure/serve/native_source.py) ·
[Packet owner](../../../python/corpus-structure/src/corpus_structure/semantic/proposals.py)

<a id="F06"></a>
## F06 · Upgrade the executable PDF binding

The execution catalog, adapter check and native validation contract are versioned separately
from the package pins. Qualify the actual new schema, callbacks and fresh writer together.
The archive decoder already preserves the producing context. Exercise archived and current
publication separately and qualify the workspace Typer override with both CLIs.
[Adapter admission](../../../python/corpus-structure/src/corpus_structure/semantic/native_adapter_contracts.py) ·
[Native callbacks](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_records.py) ·
[Docling release](https://github.com/docling-project/docling/releases/tag/v2.148.0)

## Architectural disposition

A1 and A3 remain unresolved until the current effect, archived source and shared Reader compose.
Direct reuse fails A2 because provider roles and the meanings of completion and replay differ.
A4 remains unresolved until device handoff, input bounds and scope-before-expansion hold.
G1/G2 and CI-G1 fail for direct reuse. G3/G5 and CI-G2 require integrated verification.
Explicit effects satisfy G4 in intent. The plan's bounded claim and use of Docling, PDFium and
existing custody support G7/G8. Retain independent source expectations for CI-G3. Reassess
the findings at the assembled CH-03 review against the implemented journey.

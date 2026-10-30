# Runtime preparation and production adoption

**Status:** Planned; no production change or new qualification is claimed.  
**Created:** 2026-10-30. **Packages:** PE-10–PE-12.  
**Disposition owner:** [production-efficiency coordinator](../production-efficiency_2026-10-30.md).

## Target and integration boundaries

This document realizes [F08](../../design_review/reviews/production-efficiency_2026-10-30.md#F08),
[F09](../../design_review/reviews/production-efficiency_2026-10-30.md#F09) and
[F10](../../design_review/reviews/production-efficiency_2026-10-30.md#F10), then integrates all
selected packages into current production behavior. PE-00 owns accepted authority changes;
PE-01 owns model-defined operation, interpretation, source, dependency, ownership and outcome
contracts. Current architectural owners remain D3/D4/D6/D7/D8 and ADR-0030–0034; where accepted
changes alter them, update the decision/owner through PE-00 before relying on the changed rule.

The target removes repeated preparation and item-by-item coordination while retaining complete
logical populations, native effect fences and scoped authority. It does not turn the method
catalog into a universal scheduler, establish another configuration registry or force every
analysis to consume one large intermediate representation.

<a id="PE-10"></a>
## PE-10 — Separate logical scheduling from provider preparation; acquire frames in sets

**Input:** PE-01 model-owned source/task/packet dependency contracts and PE-00's accepted RC03.
**Output:** skipped work has a complete cheap logical identity and explicit outcome, admitted work
has the exact provider packet/custody it needs, and acquisition follows sets of effective origins.

### Logical population and identity

`orchestrate.semantic.propose_agents` currently determines scope/limit skips but still calls
`queue_agent` with singleton units; `queue_agent` constructs a provider packet before recording the
skip. RC03 was accepted for planning on 2026-10-30: model the skipped task's identity from its
actual dependencies rather than requiring unconsumed rendered packet bytes. PE-00 owns the
enduring decision; PE-01 defines which source, release, method/configuration, policy/classification
and scope/limit decision inputs determine that identity. Do not simply omit a hash from the old
protocol or make a Python-only special case for a method name.

Create the complete logical producer population first, preserving skipped task reasons and unknown
coverage. Render expensive provider packets only for admitted execution. Before an admitted task
can use a packet, its source/configuration/binding and native claim/attempt rules still apply.
A different packet, macro interpretation, method configuration, known-reference set or applicable
source context cannot reuse an old executable task by sharing the skipped identity. Skips and
completed-empty source work remain distinct outcomes; neither establishes knowledge absence.

Share immutable preparation at run/configuration/document scope: method descriptor/configuration,
source-coordinate index, rendition content, guideline and bound document references. Use existing
prepared products and functions; ordinary immutable records/maps suffice. Do not add a second
cache service. Source-snapshot and release identity bound the preparation. The complete declared
global reference universe and its truncation refusal remain; a narrow packet request must not
silently prune necessary context. Recheck mutable effect premises at their actual transaction/
lease boundary, rather than removing native schedule/attempt/source fences.

Migrate queue construction and MCP packet serving together. Both consume the same packet recipe
and interpret recorded task identities consistently. Current supported continuation/refusal
outcomes must expose wrong binding, stale source and unsupported identity versions; old artifacts
are never silently relabelled as the new protocol.

### Bulk acquisition

In `semantic.domain_operations._cut_input`, collect distinct effective origin task IDs for the
sealed cut. Fetch frames, ordered sentence coordinates and relevant rendition content in bounded
set-based reads. Assemble the existing immutable frame products indexed by origin; do not repeat
an existence query followed by two frame queries for every report. Preserve packet hashes,
original task identity, sentence ordering, source offsets and cross-release/cut refusal.

Use SQLAlchemy Core selections/joins and existing native lookup routines. Batch preparation and
reads need not imply bulk unprotected lifecycle UPDATEs: protected state transitions retain the
actual concurrency/fencing obligations. Current `packet_bound_source_tasks` and hash-verified
frame backfill are shared custody owners. Missing required frames refuse with their existing
remediation; arbitrary observations do not define the source universe.

### Completion

All current scheduling, queue/MCP serving, cut consolidation and source-frame consumers use these
boundaries. Show that excluded units do not construct provider packets, while logical tasks,
reasons and unknown coverage remain represented. Exercise changed source/configuration/policy,
explicit empty output, reused origins, missing frames, limit boundaries and wrong packet hashes.
Establish that frame/reference acquisition does not add per-report database requests as report
count grows. A bounded production measurement can quantify scheduling improvement; this work is
not an explanation of the retained mathematical-processing duration.

Sources: [SQLAlchemy Core expressions](https://docs.sqlalchemy.org/en/21/core/selectable.html),
[transactions](https://docs.sqlalchemy.org/en/21/core/connections.html), and capability orientation
in [SQLAlchemy](../../libraries/sqlalchemy.md), [FastMCP](../../libraries/fastmcp.md) and
[Pydantic](../../libraries/pydantic.md). Preserve the installed typed API/refusal boundaries rather
than constructing a parallel packet schema.

<a id="PE-11"></a>
## PE-11 — Open trusted products cheaply and initialize only the selected command

**Input:** PE-01 product/runtime identity and trust contracts; existing finalized archive authority.
**Output:** a genuine warm archive hit observes a cheap trusted header before fetching payloads,
and CLI/MCP registration loads metadata without importing unrelated production kernels.

### Archive opening and verification

`semantic.archive_reader` currently selects the full release, hashes its archive/manifest and then
looks up the engine-scoped cache. First query the minimal snapshot-observed finalized header and
runtime determinants needed for the existing cache key. Use the protected immutable release identity
and finalization identity already available. Reuse an entry only within the same database/engine,
compatible runtime/dependency scope and finalized archive authority. No cache hit conveys current
project selection, authorization, privileges, mutable instance data or permission to write.

On a genuine hit, return the existing supported product without transferring and hashing the
complete archive again. On a miss, obtain exact archived payloads, verify their identities and
supported runtime recipe, reconstruct the supported product and populate the same bounded cache.
Do not add a certificate table, second cache hierarchy or a caller-controlled `trusted=True` flag.
When the transaction cannot establish the protected finalized authority, use the existing fully
checked path or refuse; an unfinalized/untrusted archive is not promoted by a cache entry.

Preserve full verification at explicit verification, persistence/replay, run start and admission
where their current contracts require it. Inspect each `load_release`/`verify_release` consumer:
change a call only if it is opening an already admitted immutable product under preserved premises.
Do not replace every verification with opening. Native deployment/principal posture, mutable
source revisions and new activation remain independently checked. Historical readers keep their
recorded supported ABI; read access never authorizes new writes/admission.

A warm hit must not fetch the large payload merely to prove the same protected immutable archive
again. Cache invalidation/reopening follows complete determinants and database identity; uncertain
or changed dependencies conservatively miss/refuse. Preserve overlap/concurrency and bounded
retention already supported by the product opener.

### Entry-point preparation

Keep Typer command metadata/registration cheap. Use the existing `Typer`, `add_typer`, command
functions and ordinary owner-local imports; avoid a plugin discovery framework or custom external
Click tree. Annotated command signatures must still be available to Typer for help/argument
validation. Move scientific, NLP, analytical and database business imports into the owning
command invocation or explicit MCP lifespan after command selection.

For the import-only correction, preserve root/group help, command names/options/aliases,
completion behavior as currently supported, JSON/refusal rendering and settings construction timing.
Where other packages deliberately replace a contract or command surface, PE-12 schedules the
coordinated consumer change; this package does not require compatibility shims for that old surface. The root callback's settings
factory remains explicit and is not invoked by help. First-use dependency failures surface through
the owning command's existing typed boundary. Database pool, extension and purpose-principal
checks retain their real safety roles; this package removes unrelated eager imports, not those
checks. A long-lived MCP session and a one-shot CLI invocation have different useful preparation
lifetimes and are measured separately.

### Completion

Demonstrate the warm trusted archive path's minimal query/payload behavior, unchanged cold opening,
explicit verification and refused corruption/runtime mismatch. Cover separate database engines,
changed runtime determinants, absent finalization, overlapping opens and historical read-only
support. Demonstrate unchanged help/dispatch/refusals and that an unrelated scientific command's
kernel is not imported by a cheap command. Measure cold command initialization separately from
first-use analysis and warm service requests; do not claim that import savings make computation
faster. The review's 1.51s/325,196KiB observation remains a dated baseline, not a guaranteed budget.

Sources: [SQLAlchemy connections](https://docs.sqlalchemy.org/en/21/core/connections.html),
[Typer command groups](https://typer.tiangolo.com/tutorial/subcommands/add-typer/),
[Typer context](https://typer.tiangolo.com/tutorial/commands/context/), and repository orientation
in [Typer](../../libraries/typer.md), [Pydantic settings](../../libraries/pydantic-settings.md)
and [FastMCP](../../libraries/fastmcp.md). The pinned Typer vendors Click; external Click
integration is not assumed. Consult Context7/installed sources before choosing any nontrivial
registration mechanism beyond these existing APIs.

<a id="PE-12"></a>
## PE-12 — Adopt the combined production target and qualify its actual consumers

**Input:** implemented PE-00–PE-11 products and consumers, not merely their declarations. PE-09's
capacity decision and required resident/spooled implementations must be settled. **Output:** the
current product routes consistently through the model-defined efficient realization and the
coordinator records functional coverage, measured benefits and remaining limitations separately.

### Adoption and retirement

Prepare a fresh semantic release/realization where interpretation, segmentation, task identity,
compiled products or native mappings change. Carry the exact library/model/configuration and
input dependencies. Breaking changes and clean regeneration are available; do not preserve an
incidental old path by inventing hot upgrades, dual writers or automatic interpretation upcasters.
Preserve historical evidence and the existing externally served historical reader. New source
work must never overwrite old selected answers or grades. No database disposal is authorized.

Migrate actual producers and consumers together: ingestion and its retained annotations; math,
context/scope, scientific decisions and matching; native consolidation/inference/publication;
run scheduling and MCP packet delivery; independent automated reference operations; query,
explanation, analytics and export; and CLI/session startup. An efficient helper unused by current
entry points is not completion. Remove superseded current preparation, conversion and dispatch
paths once their consumers migrate; preserve useful independent historical/read-only artifacts
without retaining them as alternate current authority.

Selection advances only after the required new working inputs and complete outputs exist, through
the current native parent/generation fence. Interrupted preparation remains unselected. Resume
recorded source/batch identities where that meaning is unchanged; an incompatible new protocol
uses fresh work and a typed diagnostic rather than manufacturing equivalence. Activation and
selected completed result remain separate meanings.

### Assembled acceptance and evidence

Use actual production document-to-answer journeys, cold/warm/incremental operation, changed macros
or bindings under identical text, a new domain/property/analysis recipe, dense/skewed candidates,
empty/unsupported/unknown inputs and resource interruption to challenge the combined design.
Preserve source/anchor fidelity, exact quantities, membership and relationship multiplicity,
scientific assumptions, independent automated references and release-bound interpretation.
A changed segmentation or supported analytic result is an explicit modeled version change,
not a performance equivalence claim. No human grading step or accuracy threshold is introduced.

At implementation time use targeted functional checks for coherent changed behavior. At complete
functional scope, the root assembles the applicable production/native/provider/nonfunctional
required union under the repository's existing routes. `just test-all` and applicable hygiene are
broad routes; retain failed/interrupted receipts and independently establish final source/context
applicability. Warning-aware Pyrefly errors/warnings/suppressions are resolved at the coherent
endpoint before expensive overlapping checks. Lint-only maintenance does not invalidate those
results or require another type/test campaign. This acceptance work does not authorize a new
project to redesign testing code or an audit-premise refresh.

Measure only benefits tied to the selected production remedies: unnecessary packet work removed,
transport freezes per attempt, warm archive payload work, production cold entry-point preparation,
analysis latency and required capture's combined live state. Keep structural elimination,
functional completion and measured improvement distinct. Compare equivalent inputs and declared
semantics, recording cold/warm context, actual CPU/worker configuration and competing load when
material. No page-count-only speed target, mandatory benchmark matrix or global optimality claim
is introduced.

Close package obligations only with actual current-consumer adoption and applicable evidence.
Update D3/D4/D5/D6/D7/D8 and accepted successor decisions for the realized enduring contracts;
update the coordinator and STATUS from the actual tree. Preserve source finding IDs and use the
coordinator as their only scheduled disposition owner. Broad domain-model completeness and a
separate completion audit are not inferred from this efficiency implementation.

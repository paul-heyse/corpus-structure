# Domain-governed analysis contracts and preparation

**Status:** Implemented; focused acceptance2026-10-30; later physical realizations remain Proposed · **Created:**2026-10-30.
[Coordinator](../production-efficiency_2026-10-30.md) owns package state, finding disposition,
rule decisions and assembled completion. This document owns PE-00/PE-01 and their shared contracts.
Consumes review F01–F11 where their remedies exchange context, ownership or derived data.

## Foundation assessment

The production baseline is7fadeff; review534e956 adds source-grounded findings and bounded
measurements. Existing strengths are reusable: LinkML `MathematicalExpression` already records
form, typed bindings and source-bound macros (`model/semantic/core.yaml:244–323`); `OperationContract`
records inputs, results, applicability, universe, outcomes, dependencies, precision and projections
(`semantic/contracts.py:258–274`). Execution contracts have result dimensions, implementation
bindings, transitions and effect profiles. Fixed release-scoped PostgreSQL projections already
supply operation/edge/effect/property-role/scientific policy rows. Extend this route rather than
create a competing workflow/configuration language.

Gaps exposed by the intended consumers are concrete. `MathContext` distinguishes functions,
variables and constants, while the current expression-binding family does not directly describe
every function declaration that can authorize that context. Consumers independently translate
bindings and often supply constants only. `MathResult` mixes grammatical reading, occurrences,
resolved alternatives and stronger mathematical work. Captured/candidate products already have
snapshot and lifetime contracts, but their physical resident representation and trusted ownership
must support composition without reconstructing the same input.

The target strengthens these foundations. It does not introduce an ontology for every library
object or make each semantic distinction a durable task/table. Domain decisions use modeled
contracts; generic libraries retain their execution mechanisms. Source and meaning remain
separate from operation-shaped physical representations.

<a id="PE-00"></a>
## PE-00 — Record the target and consequential decision changes

**Owner:** root architecture/model integration. **Input:** coordinator RC01–RC04 accepted for
planning by the operator's approval of the authoring plan on2026-10-30. **Output:** enduring
architectural decisions and owner updates before dependent implementation relies on replacements.

Use the ADR workflow to supersede an accepted decision where necessary; accepted bodies stay
immutable. RC01 permits distinct physical recognizers/structural frontends beneath one authoritative
interpretation model, retaining token/source fidelity. RC02 permits an explicitly versioned
segmentation configuration with changed rendition/anchor identities. RC03 separates logical skipped
invocation identity from rendered provider packets. RC04 extends captured analytical realization
from resident-only to resident or detached spool under the same semantic contract.

Update D1/D2/D4/D5/D6/D8 and affected D3/D7 ownership when their meaning changes. Identify actual
ADR clauses before choosing supersession; not every internal refactor requires a new ADR. Record
which changes are implemented versus accepted target. Do not revise audit premises, amend existing
pivot scope or treat a rejected recognizer experiment as authorization to weaken interpretation.

**Completion:** each selected replacement has one durable owner and route, contracts needed by
its dependents are settled, and original decisions/evidence remain recoverable. Documentation
acceptance is not native or operational qualification.

<a id="PE-01"></a>
## PE-01 — Compile shared analysis inputs, outcomes and derived projections

**Owner:** semantic model/compiler with actual producer/consumer owners. **Input:** existing
contracts and PE-00 decisions that affect the relevant boundary. **Output:** model-derived typed
runtime products consumed by PE-03–PE-12. PE-02/PE-05 investigations can begin from the agreed
contracts before all compiler/native work is implemented.

### Interpretation authority and analytical demand

Define a shared interpretation-context contract containing the applicable release/profile,
source/custody binding, effective macros, declared mathematical kind, eligible symbol declarations,
assumptions and their scoped authority. Distinguish a source-local symbol declaration from a
resolved semantic entity binding. A context symbol need not already have a consolidated entity.
Represent function-versus-variable authority deliberately, using existing binding/entity relations
where adequate and adding typed distinctions where absent. No display-name heuristic or provisional
scope guess may authorize pruning. Builtin function declarations belong to the versioned admitted
profile; source declarations retain source evidence and extent.

Normalize expression bindings through one model-derived context adapter. Early source reading can
consume legitimate source/lexical declarations; it cannot consume later M13 conclusions circularly.
If introducing earlier binder preparation, declare its inputs/results and weaker uncertainty before
using them. A source annotation saying "definition" does not determine the kind of every expression.

Model the demands for lexical/structural information, occurrences, interpreted alternatives,
symbolic value and scientific decision as distinct owned contracts or declared operation features.
Use existing `OperationContract` and implementation bindings to express legal combinations and
prerequisites. A syntax result cannot claim semantic OK merely because stronger work was omitted.
Preserve a dimension for the requested computation and the resulting interpretation/evidence state;
reuse existing result/outcome domains rather than add one ambiguous universal analysis status.

### Dependencies and representation

Separate immutable prepared context, relative syntax/occurrence data, mathematical values and
condition/policy-bound decisions. Their dependency recipes must cover grammar/transformer/profile
versions, kind, macros, eligible bindings, scope and assumptions where relevant. Scientific reuse
also binds conditions, precision, sampling and decision policy. Record absent lookups where they
can affect later interpretation. Start conservatively complete; narrow dependencies only when
substitutability is justified.

A shared value does not share source occurrence identity. Apply source-relative coordinates and
custody at each occurrence boundary. Conversely, do not add an entire run/source identity to a pure
syntax key when it cannot affect that stage's result. Keep timeout, unsupported, partial, ambiguous,
unanalysed and scientific-undecided outcomes distinct; a transient timeout is not timeless evidence.

Prefer operation-local prepared products and the existing bounded memo first. No universal cache
registry or persistent mega-IR is selected. Declare ownership/lifetime for token indexes, candidate
indexes, prepared operands, frozen transport and resident/spooled analytical inputs. Any durable
projection must have a real reuse/query/recovery purpose and model-derived identity. Ordinary
semantic variation becomes release rows in existing fixed projections where supported; a new
physical table needs an actual data/access responsibility, not merely a new concept name.

### Construction and enforcement

LinkML and trusted execution definitions own semantic shapes, applicability, relationships,
result dimensions and dependency recipes. Normalize once through existing SchemaView/compiler
products; derive canonical Pydantic adapters and reusable TypeAdapters for runtime boundaries.
Use cattrs/frozen archive products where that is the current supported representation. Unknown or
unsupported required semantics refuse at preparation/admission with authored location and remedy.

Pure kernels receive a prepared model-bound handle; do not add a SQL lookup, graph reconstruction
or full release verification per span or comparison. Resolve invariant policy once per valid batch
and carry it through operations preserving its premises. Effects still check current authority,
snapshot, fencing and actual native enforcement before publication. Existing SQLAlchemy MetaData,
Core projections, pglast-reviewed routines and Alembic forward revisions remain the physical route.
Version compiler/boundary recipes and execution bindings when their supported products change;
deploy reviewed forward native revisions when needed, never edit accepted migration bytes.
Native body digests establish custody, not independent semantic correctness. A declaration
without producer, enforcer and migrated consumers does not complete this package.

### Consumer obligations

| Shared product | Producers / consumers to migrate |
|---|---|
| Interpretation context and demand | Source-span/M09/M11 readers, rule projections, scope/declaration preparation, scientific operand/reference readers, grammar/transform interfaces |
| Text/source index | Rendition segmentation, binder/scope lookup, document references, citation placement; exact offset and rendition binding retained |
| Comparison inputs/eligibility | Semantic entity/claim/group alignment, identity and alternative handling, citation scorer inputs; global required universe preserved |
| Owned publication input | Append/derived transport builders, consolidation publication/retry, candidate derivation; inference's revision-sensitive work remains fenced |
| Captured analytical input | Snapshot capture, resident/spooled storage, export and DuckDB/Arrow consumers, result ownership and cleanup |
| Invocation/read preparation | Logical skip/schedule inputs, rendered packet lifecycle, finalized archive opening and actual CLI/MCP resource boundaries |

**Acceptance:** the same expression under different authorized function/variable/scope contexts
cannot collide; requesting occurrences cannot silently report an unevaluated semantic conclusion;
unsupported demands refuse before effects; adding a legitimate domain binding/policy changes its
authoritative declaration and derived products rather than literals in every reader. All named
production consumers use the normalized contract and retire independent context/role/outcome
translations. Independent cases must challenge meaning, not only generated schema agreement.

## Library realization and implementation boundaries

Use existing LinkML `SchemaView.class_induced_slots` and normalized release definitions to resolve
ranges/defaults; Pydantic `TypeAdapter` and explicit validation context at the actual typed boundary;
existing model-derived Core/native row projections for persisted obligations. Extend the current
contract schema, not a parallel hand-maintained dictionary of stage policy. Relevant orientation:
[LinkML](../../libraries/data_model/linkml.md), [Pydantic](../../libraries/data_model/pydantic.md),
[SQLAlchemy](../../libraries/postgresql/sqlalchemy.md). Concrete algorithm APIs and version limits belong to
the consuming plans, preventing this foundation from freezing a backend-neutral abstraction that
cannot express their useful capabilities.

Generic immutable ownership can be an ordinary type/library contract. Meaningful distinctions
must be declared and connected, but preparation does not require persistence, a new service or
runtime scheduling state for every capability. Physical execution may fuse several logical
methods while preserving their separate observations, outcomes and provenance.

## Execution receipt —2026-10-30

PE-00 is recorded by ADR-0035. PE-01 uses the trusted `AnalysisProfile` definitions and the
canonical `semantic.analysis_contracts` preparation boundary. Execution compiler5 and native0035
are implemented; historical archives retain explicit read support. Scoped role/declaration and
demand/dependency validation is connected to production source, rule, scientific and analytical
consumers. Source/read/invocation inputs and publication ownership use the same admitted family
contracts. Publication rebinds changed row products and refuses stale content before effects.

Current algorithms remain in place: no new parser, token/candidate index, spooled capture,
packetless scheduler, shared symbolic-value cache or transport-retry optimization is claimed.
Those implementations retain PE-02–PE-11 ownership. No audit premises, old pivot status, stored
grades or operational databases were changed.

The coordinator §9 owns acceptance/disposition and exact remaining boundaries. Relevant commands:
`uv run pyrefly check --min-severity warn --summary=none`; focused `uv run pytest -q` selections
recorded under `build/pe01-root/` and `build/pe01-native/`; `just turn-end`; `just adr-lint`;
`uv run ruff check --quiet`; `just docs-check`; `git diff --check`. Lint-only maintenance preserves
applicable functional/type receipts. Full-series integrated/provider/performance qualification
remains PE-12.

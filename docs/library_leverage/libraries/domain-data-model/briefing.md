# Domain data model: integrated library discovery

**Discovery, 2026-11-10; benefits Proposed.** LinkML/runtime, OAK, Pydantic,
pydantic-settings, pySHACL, RDFLib, Valuesets, jsonschema, msgspec, attrs and cattrs.
This account investigates unused and underutilized capabilities together, under the
repository's integrated domain-model target.

## Objective and authority

Make explicit domain meaning govern construction, interpretation, operations and
consumption with fewer independent semantic decisions and proportionate machinery.
The [knowledge owner](../../../design/D1-knowledge-representation.md),
[compiler owner](../../../design/D2-schema-and-guidelines.md),
[database owner](../../../design/D3-database.md) and
[ADR-0024](../../../adr/0024-semantic-release-preparation.md) establish the authority:
local LinkML modules own application semantics, pinned external ontologies own referenced
terms, and PostgreSQL owns transactional instances. Native schemas such as Docling retain
their scoped external ownership. Different representations need not become different
editable meanings.

This is detailed discovery, as selected by the operator on 2026-11-10. Leads below are
research priorities, not adoption decisions, diagnosed defects or scheduled packages.
The [DMA coordinator](../../../plans/domain-model-alignment_2026-11-08.md) and
[PTD coordinator](../../../plans/postgresql-typed-domain_2026-11-09.md) retain disposition.

## Baseline and evidence

| Item | Inspected scope |
| --- | --- |
| Source | `1aad0c596118b0236e0506ac1f357956fee7f3a1`, main, 2026-11-10 |
| Worktree | Concurrent PTD repairs in operation-call generation/report schemas, operations, native candidate, analytics, inference, contextual preparation, ADBC cleanup, export/description and their tests; new frozen completion migration and PTD evidence. Read as provisional source where relevant, preserved and excluded from this publication's qualification |
| Environment | Root uv workspace, default groups including dev; Linux x86_64/glibc2.39, Python3.14.10 |
| Installed and selected | LinkML/runtime1.12.1, term-validator0.4.5, OAK0.7.4, Pydantic2.14.1/core2.50.1, settings2.16.1, pySHACL0.40.1, RDFLib7.6.0, Valuesets0.4.2, jsonschema4.26.0/referencing0.37.0, cattrs26.2.1; attrs26.1.0 transitive; msgspec absent from this interpreter |
| Overview coverage | All nine supplied documents, 16,876 lines including addenda, read end to end by three researchers during planning. Reused unchanged during execution; [coverage](coverage.md) preserves the full territory |
| Follow-up | Representative current declarations/callers/tests, installed implementation and dated prior assessments; exact claims and limits in the five topic briefings |

Selection was inspected with `uv tree --locked --offline --no-python-downloads --invert`
and the ten relevant installed package names passed through `--package`. Metadata was read
using `uv run --locked --offline --no-sync --no-python-downloads python -B` and
`importlib.metadata.distribution`. No target imports or environment synchronization were
needed for that metadata read. All principal packages except attrs/msgspec are direct product
dependencies; attrs is reachable through cattrs and other packages. Advertised extras are
availability, not proof they were selected or executed. Independently locked provider/evidence
projects and platform-specific extras were not separately assessed.

Overview addenda cover later Pydantic2.14.2, settings2.16.2 and pySHACL0.40.2 behavior.
Those are candidate-version facts, not guarantees of the installed versions. Prior
[semantic](../unified-model-semantics_2026-11-01.md) and
[boundary](../unified-model-boundaries_2026-11-01.md) assessments retain November1 scope;
October library accounts retain their own dates. Their old absence/defect premises are not
automatically current. No new runtime, native, provider or performance qualification is claimed.

## Integrated research priorities

| Lead | Current interpretation and proposed broader leverage | Detail |
| --- | --- | --- |
| DDM-01 | Substantial LinkML adoption; inspect consumers rebuilding effective meaning and extend existing compiled products where semantics coincide | [Declarations](briefings/semantic-declarations.md#ddm-01) |
| DDM-02 | Native attributed-relationship, collection and presence declarations could express more application structure; qualification and all lowerings must remain faithful | [Declarations](briefings/semantic-declarations.md#ddm-02) |
| DDM-03 | Pydantic boundaries are already deeply adopted; broaden reusable executable contracts into remaining independently authored boundaries | [Boundaries](briefings/executable-boundaries.md#ddm-03) |
| DDM-04 | Directional serializers, generated cattrs hooks or direct codecs could remove repeated conversion at particular archive/transport boundaries | [Boundaries](briefings/executable-boundaries.md#ddm-04) |
| DDM-05 | Existing pinned ontology expansion could serve real term-binding consumers and retain richer vocabulary metadata | [Vocabularies](briefings/vocabularies-and-ontology.md#ddm-05) |
| DDM-06 | Unused ontology search/mapping/change capabilities could support candidate formation and explain vocabulary updates | [Vocabularies](briefings/vocabularies-and-ontology.md#ddm-06) |
| DDM-07 | Shared relationship paths and reusable graph constraints could broaden selected conformance without redefining asserted truth | [Graphs](briefings/qualified-graphs.md#ddm-07) |
| DDM-08 | Existing structured graph diagnostics could retain additional useful detail and join it to located validation consumers | [Graphs](briefings/qualified-graphs.md#ddm-08) |
| DDM-09 | Local checked JSON Schema validators are a strength; investigate portable resource composition and richer structured errors across additional report consumers | [Contracts](briefings/portable-contracts-and-settings.md#ddm-09) |
| DDM-10 | Settings snapshots are coherent; deepen source diagnostics or propagation only where a concrete operation requires it | [Contracts](briefings/portable-contracts-and-settings.md#ddm-10) |
| DDM-11 | Repeated ontology parsing/prefix preparation could share an operation-scoped adapter when a multi-enum consumer warrants it | [Vocabularies](briefings/vocabularies-and-ontology.md#ddm-11) |
| DDM-12 | Unit/quantity-kind identifiers could strengthen a specific currently withheld comparison while retaining source basis | [Vocabularies](briefings/vocabularies-and-ontology.md#ddm-12) |
| DDM-13 | PDF recipe reconstruction parses twice and prepares adapters repeatedly; investigate one complete derived wire contract | [Boundaries](briefings/executable-boundaries.md#ddm-13) |
| DDM-14 | Nested structural-product validation could compose more directly through the generated outer model | [Boundaries](briefings/executable-boundaries.md#ddm-14) |

First investigate DDM-01/03/09 together: how far one effective declaration already governs
Python construction, generated calls and portable reports, and where consumers still interpret
it independently. DDM-02/07/08 form a second composition: declare the relationship once,
preserve qualified occurrences in projection and report exact constraint outcomes. DDM-05/06
need a named vocabulary or grounding consumer before ontology machinery expands.
DDM-04 is a bounded representation investigation; adopting another Python model library is not
its objective. DDM-10 supports operation clarity rather than moving semantic policy into settings.
DDM-13/14 are concrete bounded entry points for DDM-03. DDM-11 depends on an actual multi-enum
source; DDM-12 depends on a justified measurement comparison, not simply available unit metadata.

Attention order is qualitative, not an implementation queue. Schema validity, graph conformance,
native concurrency enforcement, source custody and scientific correctness are distinct
obligations. A successful codec or ontology lookup does not discharge the others.

## Judgment and handoff

Apply core3.3, heuristics1.0 and code-intelligence1.4 selected by
[standard.toml](../../../design_review/design_principles/standard.toml).
FP-04/05 and A2 favor explicit meaning and actual enforcement; FP-01/03/06 favor coherent
owners and reusable operations; FP-07/A4 favor valid-lifetime preparation and fewer unnecessary
conversions or whole-input rechecks. Benefits remain qualitative and Proposed.
Relevant [patterns](../../patterns.md) include LOP-02/03/06/07/09/12, with
[X003/X004/X006/X009](../../assessment-patterns.md) guarding independent enforcement,
complete compiled products, closed acquisition and archive opening. No new pattern is needed.

For each useful lead, establish a concrete responsibility through codebase-audit where needed,
then assess contextual fit and compare complete options through the existing leverage stages.
Reuse the [PostgreSQL discovery](../postgresql/briefing.md) for native/relational boundaries;
this pass does not duplicate its assessments or reopen PTD selection.
Discovery changes research documentation and navigation only. Public APIs, dependencies,
runtime defaults and database state receive no changes from this publication.

Functional tests, provider runs, native probes and benchmarks: **not_run**, because source and
reference evidence sufficed for the discovery questions. Publication checks are recorded in STATUS.

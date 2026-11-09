# PostgreSQL libraries: typed-domain design discovery

**Discovery published 2026-11-09; benefits Proposed.** One family account for SQLAlchemy,
pglast, SQLGlot, Psycopg, psycopg-pool, Alembic, pgpq, ADBC PostgreSQL and pgvector Python,
including native PostgreSQL features needed to understand their usefulness.

## Objective and authority

Identify unused and underutilized capabilities that make the released domain model govern
construction, validation, persistence, operations and consumption more directly. Judge reduction
of independent semantic decisions and total machinery, rather than feature count or source lines.
The [knowledge owner](../../../design/D1-knowledge-representation.md),
[compiler owner](../../../design/D2-schema-and-guidelines.md) and
[database owner](../../../design/D3-database.md) govern meaning and realization.
ADR-0024 makes Core metadata derived and PostgreSQL the instance authority; ADR-0067 preserves
source custody through current-only semantic replacement. Discovery does not change either.

## Baseline and evidence

| Item | Inspected scope |
| --- | --- |
| Source | Planning research at `fc72eb61f`; execution refresh at `51b3c28deb55bd3c14f1de61d86ea12e961a34e8`, 2026-11-09. The intervening commit changed STATUS, PM2 plans and retained evidence, not application source |
| Worktree | Concurrent PM2 coordinator and four companion-plan edits excluded from research conclusions; preserved. This publication changes only the discovery account, its routes and handoff |
| Selection | Root uv workspace on Linux x86_64/glibc2.39, Python3.14.10; default groups including dev. Manifest, lock and inverted `uv tree --locked --offline --no-python-downloads` agree |
| Installed | SQLAlchemy2.1.6, Alembic1.20.1, pglast8.7, SQLGlot30.27.0, Psycopg binary3.3.6, pool3.3.3, pgpq0.12.0, ADBC PostgreSQL/manager1.13.0, pgvector Python0.5.1; PyArrow26.0.0 |
| Native | PostgreSQL18.6/vector0.8.7 recorded by current owners/holds; no fresh server query or extension qualification in this discovery |
| Coverage | All nine overviews, 17,961 lines including addenda/corrections, read during planning by three researchers; unchanged capability material reused. [Section coverage](discovery/coverage.md) routes every substantive section |
| Follow-up | Representative current consumers, selected tests, installed sources and tagged primary references in topic documents. No new native runs, provider work or benchmarks |

Installed metadata was refreshed with `uv run --locked --offline --no-sync
--no-python-downloads python -B` and `importlib.metadata.version`; dependencies were not synchronized.
The uv inverse tree establishes direct product selection of all nine and additional SQLAlchemy
paths through Alembic/LinkML/OAK and SQLGlot through Splink. Those transitive consumers were not
reviewed as a separate integration. Independently locked evidence/provider projects are excluded.
Selected imports, advertised extras, written calls and recorded execution are different evidence.
Scoped no-hits below do not establish global absence or dynamic-call attribution.

The [completed PG series](../../../plans/postgresql-capability-leverage_2026-11-01.md)
records its November1 targeted319-case result. That evidence retains its original scope and date;
this account neither repeats that qualification nor refreshes the October29 applicability accounts.

## Current foundations and ranked questions

Generated metadata/typed columns, model-owned projection recipes, strict SQLGlot analysis,
source-qualified pglast syntax, frozen Alembic native operations, independent catalog admission,
shared ArrowWriteProfile/fresh encoders, same-session publication and cause/phase/effect outcomes
are already present. Imports alone would miss both this adoption and its remaining limits.

| Attention | Research direction | Why investigate; distinguishing question | Owner document |
| --- | --- | --- | --- |
| First | Model-derived boundary types and adaptation | Can precise value/identifier distinctions survive generated result construction without parallel schemas or implicit conversions? | [Types](discovery/domain-types-and-invariants.md) |
| First | Scope/lineage metadata and helper typing | Can native hooks replace reconstruction while retaining relationship kind, origin and explicit unknowns? | [SQL analysis](discovery/sql-analysis-and-source-fidelity.md) |
| First | Whole relational intent and exact retrieval | Can repeated eligibility/preparation be composed without changing candidate membership, channel evidence or failure behavior? | [Relational operations](discovery/relational-operations-and-preparation.md), [retrieval](discovery/typed-retrieval-and-vector-search.md) |
| Next | Directional type fidelity and conversion | Which concrete consumer still needs conversions beyond the already prepared COPY/Arrow boundaries? | [Transfer](discovery/typed-copy-and-arrow-transfer.md) |
| Next | Native evolution and observation | Can supported hooks remove version-sensitive glue while keeping actual catalog observation independent? | [Evolution](discovery/schema-evolution-and-catalog-admission.md) |
| Supporting | Session generation and truthful outcomes | Does introducing a useful adapter/type require new invalidation or lifetime handling, and can existing owners supply it? | [Lifetimes](discovery/transactions-pools-and-outcomes.md) |

Attention is qualitative, not an execution queue or adoption ranking. New native types depend
on migration/OID/resolver/session lifetimes; richer analysis depends on model-declared helper
semantics; fused retrieval depends on preserving full inventory checks. These interactions must
be evaluated together rather than solved with isolated wrappers.

## Interpretation and handoff

Topic documents distinguish adequately used mechanisms, candidate underuse, unused capabilities,
conditional territory and unresolved attribution. An underuse candidate names an actual local
responsibility; its advantage remains Proposed. Broad unused territory without a selected consumer
is conditional, not a diagnosed defect. Static types, codec validation, native constraints,
semantic authority, lineage and scientific evidence discharge different obligations.

Use [base patterns](../../patterns.md) and
[additional patterns](../../assessment-patterns.md), especially
LOP-02/03/05/06/07 and X002/X003/X004: derive mechanical forms, deepen adopted mechanisms,
retain relational intent, eliminate unnecessary conversion and distinguish frozen derivation
from independent enforcement. No new pattern or analyzer is needed for these observations.
FP-04/05 and A2 guide domain authority; FP-07/A4 and the heuristic companion guide whole-operation
fit qualitatively. No quantitative improvement is claimed.

Next use codebase-audit for a concrete responsibility needing a stable opportunity, then
library-assessment for its contextual fit; comparative review chooses complete alternatives.
The [older PostgreSQL account](README.md), [SQLAlchemy](../sqlalchemy/README.md),
[Psycopg](../psycopg/README.md), [Alembic](../alembic/README.md) and
[ADBC](../adbc-driver-postgresql/README.md) supply reusable types, not present-day absence evidence.
Existing plans retain finding disposition. This discovery selects no implementation, dependency
move, API change or migration and creates no duplicate finding register.

The execution refresh identified concrete seams in primitive-only typed-column rendering,
transient vector literal construction, statement-local repeated retrieval eligibility, post-lineage
metadata extraction and database-description metadata/lifetime handling. Selected SQLGlot schema UDF
lookup is not automatically wired into type annotation; that limits a possible deeper-use lead.
The topics retain these counterconditions alongside the broader capability inventory.

Functional tests/native probes/benchmarks: **not_run**, because source/reference evidence suffices
for the discovery questions. Documentation publication validation is reported in STATUS with its
actual command/outcome. Narrow future probes should settle the question they name, not serve as
ceremony for every capability.

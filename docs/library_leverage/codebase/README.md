# Codebase opportunities for library leverage

The living account of concrete responsibilities, operations and gaps where established library
capabilities could improve the codebase. The [codebase audit skill](../../../.claude/skills/leverage-codebase-audit/SKILL.md)
maintains it under the [framework](../library-leverage-framework.md), using the
[base patterns](../patterns.md), the [additional assessment patterns](../assessment-patterns.md),
the [shared vocabulary](../references/shared-language.md) and the
[writing guidance](../references/collection-writing.md).

This account identifies opportunities. It neither assesses library applicability
([library assessments](../libraries/README.md)) nor selects options
([comparative reviews](../reviews/README.md)), and it authorizes no product, dependency or plan
change.

<a id="baseline"></a>

## Inspected baseline

| | |
|---|---|
| Source baseline | commit `9f8df02` (T0, 2026-10-29T14:02-04:00) plus one dirty document, `docs/plans/semantic-model-pivot/domain-operations.md` |
| Reconciled through | commit `f697233` (2026-10-29T14:13-04:00, clean tree). Concurrent SP-06/SP-07 exclusion work landed 48 commits during the pass, changing `semantic/domain_operations.py`, `query.py`, `ontology.py`, `proposals.py` and migration 0027. Every cited claim was rechecked at `f697233`, and line numbers cite it |
| Date | 2026-10-29 |
| Criteria | framework edition 0.2; base patterns LOP-01–LOP-12 edition 0.2; [additional patterns](../assessment-patterns.md) LOP-X001–X004, created by this pass; design standard core 3.3 with heuristics, used for judging substantial shapes |
| Kind | First audit; there is no preceding account |
| Publishing commit | The commit that adds this account, distinct from the source baseline |

## Scope

The operator chose this scope on 2026-10-29. The audit gives a **forward view on the
semantic-model pivot**, which has delivered SP-00–SP-07 and SP-C01–SP-C05 in scoped profiles.

- **Primary (surviving and growing):**
  - `python/corpus-structure/src/corpus_structure/semantic/` (about 13.6k Python lines) and its SQL:
    `semantic/sql` plus 27 `semantic_alembic` SQL files;
  - the foundations it imports or executes: `schema/relational.py`, `schema/rulelang.py`, the
    method run path, `evaluate` comparison, `intervene/semantic_server.py`, the semantic CLI routes
    and `core/db/store.py`.
- **Forward consumers — the pivot only:**
  - [SP-08](../../plans/semantic-model-pivot/queries-and-consumers.md#SP-08) consumer migration;
  - [SP-09](../../plans/semantic-model-pivot/regeneration-and-acceptance.md#SP-09) regeneration,
    retirement and cutover;
  - [SP-10](../../plans/semantic-model-pivot/regeneration-and-acceptance.md#SP-10) assembled
    qualification.

  Phase-0 and roadmap capabilities are out of scope unless SP-08 names them, for example
  evaluation readers and exports.
- **Migration lens (legacy):** `serve/`, the legacy `core/db`, `core/keys`, `consolidate/assemble.py`,
  legacy `pool/`, the `schema` pack and stage generators, and `orchestrate/queue.py`. An opportunity
  is recorded only where:
  - SP-08 or SP-09 will rebuild the responsibility on the semantic path, or
  - surviving code imports the legacy code.

  Opportunities about code that is simply deleted are not recorded.
- **Engineering support:** the native test harness, the qualification route, release composition,
  bootstrap and principals. Causes already diagnosed by the
  [test audit](../../design_review/test-audit/README.md) are linked, not restated.

**Labels:** **current** (existing promised behaviour), **accepted planned** (SP-08–SP-10) or
**proposed**.

## Method

- **Three read-only contributors** followed complete operations:
  - model and release preparation;
  - storage, publication, query and analytics;
  - domain operations, pivot consumers and workflows.

  They worked from planning maps of responsibilities, library usage, hand-written machinery,
  forward consumers, ADR choices, pins and prior findings, handed over as unverified leads.
- **Coordinator verification.** The coordinator read the decisive source behind every candidate,
  merged candidates by coherent need and cause, and reconciled them against the concurrent commits.
- **No execution.** No tests, probes or measurements were run; every cost statement is qualitative.
- **Nominations only.** Library nominations come from the [overviews](../../libraries/README.md) and
  installed sources, as leads. Applicability research is left to the next stage.

## System picture

**One release governs interpretation.** A LinkML semantic release, compiled by
`semantic/prepare.py` into an immutable `PreparedRelease`, governs interpretation
([ADR-0024](../../adr/0024-semantic-release-preparation.md)). It is archived and reloaded exactly,
and every consumer receives it.

**PostgreSQL 18 is the transactional authority.**
- MetaData is derived from the physical model.
- A frozen Alembic history deploys DDL and definer-owned publication routines.
- Restricted roles publish through protected staging and COPY
  ([ADR-0025](../../adr/0025-semantic-publication.md)).

**The read and analysis paths are derived.**
- Reads go through REPEATABLE READ snapshots (`semantic/query.py`).
- Analysis runs in one DuckDB scope over an exported snapshot imported through ADBC, with pgpq for
  Arrow publication ([ADR-0026](../../adr/0026-columnar-semantic-operations.md)).

**Domain operations run on that platform.** Cut materialization, consolidation, released rules
([ADR-0018](../../adr/0018-policy-routed-escalation.md)) and qualified inference are built on it.

**The direction is consumer adoption, then retirement, then qualification:**
- SP-08 moves the remaining consumers — serving, CLI, MCP, intervention, evaluation and exports —
  onto this platform;
- SP-09 regenerates realizations, retires the legacy model and paths, and cuts defaults over;
- SP-10 qualifies the assembled union.

**Where the opportunities cluster:**
- **The read boundary that consumers will share.** No composable read boundary exists; each SP-08
  consumer would otherwise rebuild selection, continuation, size bounds, decoding and explanation.
- **The release's lifecycle and contract.** There is no composer, every session reloads and
  re-verifies, consumers re-derive what the product could expose, and identity dependency sets are
  chosen by hand.
- **Backward dependencies from surviving code into retiring code.** The rule policy, comparison
  kernels, DuckDB kernels and physical lowering all reach into the legacy model.
- **Frozen artifacts whose derivation route has been lost.** Migration DDL and the transport routine
  are copied by hand rather than derived.
- **Workflows SP-09 and SP-10 must make reproducible.** The bootstrap and principal selection, the
  test template and the qualification route.

## Opportunity synthesis

1. **SP-08 needs a composable semantic read boundary.**
   - [CBO-001](consumers-and-operations.md#cbo-001): one consumer boundary for selection,
     continuation, size bounds, value reconstruction and explanation.
   - [CBO-007](consumers-and-operations.md#cbo-007): exports composed from capture.
   - [CBO-012](consumers-and-operations.md#cbo-012): consistent refusal mapping and MCP conventions.

   Together these would stop every surface from rebuilding these on the new model. The decisive
   constraints are snapshot-pinned continuation, unknown versus absent, strict release validation,
   and the prohibition on a generic introspection service.
2. **The release lifecycle is the platform's spine.**
   - [CBO-002](release-preparation.md#cbo-002): one product composer serves SP-09 and every test
     ([DTA-005](../../design_review/test-audit/support-structure.md#dta-005)).
   - [CBO-003](release-preparation.md#cbo-003): verification tied to a valid lifetime would stop
     every session from re-preparing and re-comparing.
   - [CBO-013](release-preparation.md#cbo-013): a richer product contract would remove consumer
     re-derivation.
   - [CBO-009](release-preparation.md#cbo-009): derived identity dependency sets would remove the
     risk that a lock bump makes the active release unloadable after cutover.
3. **SP-09 retirement has backward dependencies to resolve first** (pattern
   [LOP-X001](../assessment-patterns.md#lop-x001)):
   - the released rule policy ([CBO-005](consumers-and-operations.md#cbo-005));
   - the comparison kernels ([CBO-006](consumers-and-operations.md#cbo-006));
   - the DuckDB kernels ([CBO-018](storage-and-analytics.md#cbo-018));
   - the physical lowering ([CBO-008](storage-and-analytics.md#cbo-008)).

   Each surviving kernel is valuable, and only its operand model or host package is retiring.
4. **Frozen derived artifacts need an authoring-time derivation route**
   ([LOP-X002](../assessment-patterns.md#lop-x002)).
   - Migration DDL and drift ([CBO-008](storage-and-analytics.md#cbo-008)): Alembic comparison is
     configured but never invoked.
   - The transport routine ([CBO-014](storage-and-analytics.md#cbo-014)): five hand copies, with a
     stale generator.
5. **The reproducible workflows SP-09 and SP-10 depend on.**
   - The command path and principals ([CBO-004](engineering-workflows.md#cbo-004)).
   - Template databases ([CBO-010](engineering-workflows.md#cbo-010), linked to
     [DTA-002](../../design_review/test-audit/execution-and-qualification.md#dta-002)).
   - Outcome classification ([CBO-011](engineering-workflows.md#cbo-011), linked to
     [DTA-003](../../design_review/test-audit/execution-and-qualification.md#dta-003)).
6. **Local mechanisms worth investigating:**
   - codec copies around a deliberate mirror ([CBO-015](storage-and-analytics.md#cbo-015),
     [LOP-X003](../assessment-patterns.md#lop-x003));
   - instance traversal ([CBO-016](consumers-and-operations.md#cbo-016));
   - the catalog's second structural form ([CBO-017](release-preparation.md#cbo-017));
   - meaning recomputation ([CBO-019](storage-and-analytics.md#cbo-019));
   - eager known-input loading ([CBO-020](consumers-and-operations.md#cbo-020));
   - the SchemaView lifecycle ([CBO-021](release-preparation.md#cbo-021));
   - naive inference ([CBO-022](storage-and-analytics.md#cbo-022));
   - the main-thread deadline ([CBO-023](consumers-and-operations.md#cbo-023));
   - the ontology workaround ([CBO-024](release-preparation.md#cbo-024)).

<a id="forward-view"></a>

## Forward view on the pivot

This is a reading aid for timing, not a schedule. The
[pivot coordinator](../../plans/semantic-model-pivot_2026-10-29.md) owns scheduling and closure.

| Boundary | Opportunities whose value is highest before or during it | Why then |
|---|---|---|
| **Before SP-08 builds consumers** | CBO-001, CBO-003, CBO-007, CBO-012, CBO-013, CBO-016, CBO-023 | Each new consumer otherwise copies selection, continuation, decoding, refusal mapping and release lookups, or pays per-session reload. These are cheapest to settle before the surfaces exist |
| **Before SP-09 retires and cuts over** | CBO-002, CBO-004, CBO-005, CBO-006, CBO-008 (lowering), CBO-009, CBO-018 | Surviving code still depends on retiring modules. The command path, composer and principal model must exist. Identity sets change release ids, and regeneration is the cheapest moment to accept that |
| **For the SP-10 union** | CBO-008 (drift), CBO-010, CBO-011, CBO-014, CBO-015 | Controlled-revision evidence, outcome classification, a cheap native harness and conformance of the mirrored codec are what assembled qualification rests on |
| **Independent of timing** | CBO-017, CBO-019, CBO-020, CBO-021, CBO-022, CBO-024 | Local improvements whose value does not depend on a pivot boundary |

<a id="opportunities"></a>

## Opportunities

| ID | Opportunity | Label | Main patterns | Page |
|---|---|---|---|---|
| [CBO-001](consumers-and-operations.md#cbo-001) | SP-08 consumers have no composable semantic read boundary | accepted planned | LOP-05, LOP-09, LOP-12 | consumers |
| [CBO-002](release-preparation.md#cbo-002) | No product release composer; layering uses two unrelated mechanisms | accepted planned | LOP-12, LOP-02, LOP-09 | preparation |
| [CBO-003](release-preparation.md#cbo-003) | Every read session rebuilds and re-verifies the immutable release | current | LOP-07, LOP-09 | preparation |
| [CBO-004](engineering-workflows.md#cbo-004) | SP-09 regeneration has no command route; restricted principals exist only in tests | accepted planned | LOP-12, LOP-08 | workflows |
| [CBO-005](consumers-and-operations.md#cbo-005) | Released rule policy evaluates through the retiring rule environment | current | LOP-X001, LOP-02, LOP-10 | consumers |
| [CBO-006](consumers-and-operations.md#cbo-006) | Comparison and alignment kernels take the retiring value model | current / accepted planned | LOP-X001, LOP-06 | consumers |
| [CBO-007](consumers-and-operations.md#cbo-007) | Exports and analytical capture cannot be composed from the application store | accepted planned | LOP-12, LOP-05, LOP-08 | consumers |
| [CBO-008](storage-and-analytics.md#cbo-008) | Physical schema written twice; drift checked by names; lowering in retiring code | current / accepted planned | LOP-X002, LOP-03, LOP-10 | storage |
| [CBO-009](release-preparation.md#cbo-009) | Identity dependency sets are hand-chosen, duplicated and drifted | current | LOP-09, LOP-02 | preparation |
| [CBO-010](engineering-workflows.md#cbo-010) | Native test databases have no reusable template or revision-pair route | current / accepted planned | LOP-07, LOP-12 | workflows |
| [CBO-011](engineering-workflows.md#cbo-011) | Qualification route cannot classify outcomes for the required union | accepted planned | LOP-12, LOP-03 | workflows |
| [CBO-012](consumers-and-operations.md#cbo-012) | Refusal mapping and MCP conventions re-decided per surface | current / accepted planned | LOP-09, LOP-03 | consumers |
| [CBO-013](release-preparation.md#cbo-013) | Prepared-release contract leaves range meaning, adapters and name maps to consumers | current | LOP-X004, LOP-07, LOP-09 | preparation |
| [CBO-014](storage-and-analytics.md#cbo-014) | Transport routine hand-copied per revision; generator stale | current | LOP-X002, LOP-02, LOP-11 | storage |
| [CBO-015](storage-and-analytics.md#cbo-015) | Typed-value codec spread across encode, decode and meaning sites | current | LOP-X003, LOP-09 | storage |
| [CBO-016](consumers-and-operations.md#cbo-016) | Release-typed instance traversal reimplemented per consumer | current | LOP-X004, LOP-03 | consumers |
| [CBO-017](release-preparation.md#cbo-017) | Execution catalog is a second structural form with hand reference integrity | current | LOP-02, LOP-03 | preparation |
| [CBO-018](storage-and-analytics.md#cbo-018) | DuckDB composition by regex renaming and private legacy kernels | current | LOP-X001, LOP-10 | storage |
| [CBO-019](storage-and-analytics.md#cbo-019) | Native value meaning recomputed; each publish revalidates the realization | current | LOP-07, LOP-04 | storage |
| [CBO-020](consumers-and-operations.md#cbo-020) | Each cut loads and decodes the whole input realization | current | LOP-05, LOP-04 | consumers |
| [CBO-021](release-preparation.md#cbo-021) | The compiler works against SchemaView's lifecycle | current | LOP-10, LOP-07 | preparation |
| [CBO-022](storage-and-analytics.md#cbo-022) | Inference runs a naive fixed point | current | LOP-01, LOP-04 | storage |
| [CBO-023](consumers-and-operations.md#cbo-023) | Math deadline confines comparison and decisions to the main thread | current | LOP-08 | consumers |
| [CBO-024](release-preparation.md#cbo-024) | Ontology path works around enum composition order and reparses ontologies | current (tests only) | LOP-11, LOP-07 | preparation |

IDs are ordered by value for the pivot's remaining work at this baseline. They are stable and are
never reused.

## Questions for library research

These were the most consequential questions for `leverage-library-assessment`. Each opportunity
lists its own. The first [library assessment](../libraries/README.md#applicability) (2026-10-29,
source `d739b88`) answered them per opportunity. It also added dated notes to the affected CBO
entries where premises changed or were corrected. Those notes include a correctness gap in
CBO-013 and a template-ACL premise failure in CBO-010.

1. **SQLAlchemy Core and psycopg** (CBO-001, CBO-020): release-checked predicate composition over
   `typed_value`/`value_role`, streaming with response budgets, set-oriented explanation and value
   reconstruction under a snapshot.
2. **LinkML / linkml-runtime 1.12** (CBO-002, CBO-013, CBO-017, CBO-021):
   - `SchemaView` `importmap` composition, `type_ancestors` and `materialize_derived_schema`;
   - `ReferenceValidator` dangling-reference checks;
   - generating static catalog products for a trusted schema.
3. **Alembic** (CBO-008, CBO-010): whether `compare_metadata`/`command.check` against a
   head-migrated database is clean or explainable; `CreateTable`/autogenerate emitting the next frozen
   revision; revision-pair upgrades.
4. **rule-engine 5.1** (CBO-005): deriving object schemas from release-generated types and a public
   typed traversal replacing `_object_type`.
5. **DuckDB 2.0 and pyarrow 26** (CBO-007, CBO-018): Parquet writers preserving `cs.*` metadata,
   subset capture, and scoped relation binding without SQL-text rewriting.
6. **FastMCP 4.1.3** (CBO-012, CBO-023): error-translation and response-limiting middleware for
   both servers; execution of synchronous tools.
7. **pytest-postgresql 9.1.1 and pytest reporting** (CBO-010, CBO-011): noproc mode with restricted
   roles and migrated templates on the shared cluster; built-in per-test outcome and skip-reason
   reporting; hang bounds.
8. **Settings and principals** (CBO-004): per-principal connection modelling with pydantic-settings,
   composed with the single-pool rule.
9. **Identity determinants** (CBO-009): which libraries change prepared bytes or run outputs, and
   how to derive the set (`importlib.metadata`).
10. **curies** (CBO-013): exact match with archived-prefix expansion and compaction semantics.
11. **Hypothesis** (CBO-015): generative parity between the Python and native codecs.

## Coverage and limits

**Read in depth:**
- `prepare.py`, `types.py`, `contracts.py`, `conditional_rules.py`, `ontology.py`, `metadata.py`;
- `publication.py`, `arrow_publication.py`, `routines.py`, `identity.py`, `releases.py`,
  `migrations.py` with `env.py`;
- the selection, token, value and explanation parts of `query.py`; `analytics.py`; `inference.py`;
  the claims path in `operations.py`; `core/db/store.py`;
- the cited parts of `domain_operations.py`, all of `consolidation.py`, `orchestrate/semantic.py`
  (to about `:330`), `intervene/semantic_server.py`;
- the heads of `evaluate/equivalence.py` and `align.py`; the semantic CLI modules cited.

**Not read in depth:**
- `intervene/semantic.py` and `submission.py`;
- `serve/read.py`, `explain.py` and `queries.py` bodies (migration lens);
- `evaluate/goldens.py` and `agreement.py`;
- the methods/llm cascade and spaCy ingest;
- most migration SQL beyond transport, publication and exclusions;
- `execution-model.yaml` and `core.yaml` in full;
- `tools/evidence` and `scripts/` beyond role provisioning.

**Absence claims and their search scopes:**

| Claim | Search scope |
|---|---|
| No product release composer | `prepare_release(` and `SourceBundle(` in `src` |
| No reader for the OWL, SHACL or `json_schema/` artifacts | `src` and tests |
| No caller of `deploy_routines` | `src`, tests and `semantic_alembic` |
| No semantic `compare_metadata`/`command.check` | `python/`, excluding `.venv` |
| No export command | `cli/` and `serve/` |
| No production caller of `capture_packet` | `src` |
| No production per-principal connection selection | `corpus_sem_` and `username=` in `src` |
| No semantic query or explain MCP tools | the full tool list in `semantic_server.py` |
| `valuesets` not imported | `src` |

None of these settles the question beyond its stated paths.

**Examined and not recorded as opportunities:**
- the two canonical-form contracts, which differ deliberately;
- the single SERIALIZABLE retry owner;
- semantic versus legacy claims, which are different contracts;
- the decimal and float-hex boundaries in analytics, which are explicit policies;
- Siegrist profile compilation and spaCy loading, both immaterial;
- `graphlib` and union-find use, which are appropriate;
- Arrow publication's row-wise identity, which the receipt contract requires.

**Open questions:**
- the valid lifetime of release verification (CBO-003);
- whether `compare_metadata` is clean today (CBO-008);
- how FastMCP executes synchronous tools (CBO-023);
- whether authored rule text is the real rule contract (CBO-005);
- whether any SP-08 consumer needs the eager graph artifacts (CBO-003).

**Concurrency limit:** changes after `f697233` are not reconciled.

## Maintenance

- Refresh this account in place; Git holds earlier accounts.
- Retire an opportunity only on evidence of resolution, corrected premises, supersession or loss of
  relevance. A rejected library or an accepted plan alone does not resolve it.
- Reconcile incoming applicability and review links before removal.
- The [pivot coordinator](../../plans/semantic-model-pivot_2026-10-29.md) and later plans own
  scheduling and closure evidence; link to them without copying their status.
- Additional patterns live only in [assessment-patterns.md](../assessment-patterns.md).

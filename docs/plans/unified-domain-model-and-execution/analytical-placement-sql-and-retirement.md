# Analytical placement, the remaining SQL text, and retirement

**Status:** In progress. The release-side authored SQL and publication-port retirements are integrated.
**Created:** 2026-11-19.

This companion owns the designs of **UDM-16** (DuckDB conditions of use, declared settings, the
certification folds, the uncalled kernels), **UDM-17** (SQLite stores on typed statements and the
last hand-written PostgreSQL item), **UDM-18** (release-bound pack inputs read from the release,
the scientific policy derived from its declaration, and two small recurring causes) and **UDM-19**
(retirement of the two migration trees, dead modules and functions, and the stale preview
explanation). Package state, the queue, finding dispositions, the shared contracts and the
flexibility frame are the
[coordinator's](../unified-domain-model-and-execution_2026-11-19.md). The terms **fact
authority**, **compiled model**, **declared openness**, **cache tier**, **qualification union**
and **the flexibility frame** are used here as the coordinator defines them, and terms such as
*release*, *stage* and *native revision* are in its
[glossary](../unified-domain-model-and-execution_2026-11-19.md#glossary).

**Baseline and evidence.** Recommendation and section references such as R12 or §5 mean the
[design review of 2026-11-18](../../design_review/reviews/design_review_unified-domain-model-and-execution_2026-11-18.md),
which read source at `5139eaba3`. This plan was authored against commit `cb4e09667`, whose
production source is identical. Source facts are **Interface-checked by source inspection,
2026-11-19** at `cb4e09667`; where a fact comes from an investigation report and was not re-read
for this companion, the sentence says so. Library behaviour is quoted from the
[DuckDB library report](../../design_review/evidence/2026-11-18_production-review-inputs/library-duckdb.md),
whose probes ran on synthetic data on 2026-11-18 against `duckdb==2.0.0`; nothing was run for this
plan. Every design statement is **Proposed**. No speedup is claimed. The investigations drawn on
are the [cache and placement map](../../design_review/evidence/2026-11-19_udm-plan-authoring/caches.md)
and the [identity advice](../../design_review/evidence/2026-11-19_udm-plan-authoring/identity.md).
`src/…`, `tests/…`, `semantic_alembic/…`, `alembic/…` and `target_alembic/…` are relative to
`python/corpus-structure/`; module paths below are relative to the production package
`src/corpus_structure/` unless they begin with `tests/` or are marked as root paths.

## Why this work exists

The four packages share one theme: each removes a place where the system's behaviour depends on
something that no declaration states. The other companions of this series do that for the model,
for validity and for identity. What is left for this one is smaller and more scattered, and the
[baseline](#baseline-at-cb4e09667) gives the facts behind each point.

The review examined every analytical computation and found its placement between PostgreSQL,
DuckDB and plain Python mostly right; what it found wrong is the conditions under which DuckDB
runs, with settings that are read by nothing (F03,
[DA-020](../../design_review/audit/boundaries-and-composition.md#da-020)). Application code
still writes SQL text in two places that
[ADR-0131](../../adr/0131-model-owned-postgresql-programs.md) did not cover, SQLite statements
built by concatenation (F04) and one PostgreSQL grant; the operator accepted rule impact RC02 on
2026-11-19, which extends "no maintained SQL text in application code" to SQLite scratch stores
and to DuckDB use. Two results are attributed to a release although an input that determined them
came from the working tree or from a hand-written description
([DA-028](../../design_review/audit/semantic-model-and-authority.md#da-028),
[DA-077](../../design_review/audit/served-claims.md#da-077)), and two smaller facts have the same
shape ([DA-040](../../design_review/audit/structure-and-invariants.md#da-040),
[DA-001](../../design_review/audit/semantic-model-and-authority.md#da-001)). Finally, the tree
carries code and data that nothing reads, and a preview explanation that always reports that no
SQL changed ([DA-080](../../design_review/audit/boundaries-and-composition.md#da-080)), which can
mislead an operator today.

None of the four packages needs a capability from another package of the series to begin; they
share a companion because they are independent of the central design and of each other. Two
parts join a native revision that another companion plans: the decimal bound of UDM-18 joins
revision A, and one removal in UDM-19 joins revision B only if it changes installed bytes.
Whether a change alters installed bytes is answered by generating the programs and comparing
them with the current frozen objects, which is possible today and waits for no other package.

## Baseline at `cb4e09667`

### DuckDB

Six production modules import DuckDB: `serve/companion_export.py`,
`semantic/artifact_identity.py`, `semantic/rich_relations.py`, `semantic/analytical_kernels.py`,
`ingest/pdf_stream_reconciliation.py` and `ingest/pdf_candidate_geometry.py` (exhaustive, from
the cache and placement map). Their connections are opened as follows.

| Site | Configuration today |
|---|---|
| `serve/companion_export.py:410` and `:552` | `duckdb.connect()` with no arguments: library defaults |
| `semantic/artifact_identity.py:481` and `:579` (the connection handed to Splink) | `duckdb.connect()` with no arguments: library defaults |
| `semantic/rich_relations.py:71–77` | constructor arguments for threads and memory limit; a fresh temporary directory for spill; its one caller passes `threads=1` and `memory_limit="2GB"` (`semantic/rich_consolidation.py:405–412`) |
| `ingest/pdf_stream_reconciliation.py:301–305` | `memory_limit="2GB"`, a `sort-scratch` directory beside the input file, `threads=1` |
| `ingest/pdf_candidate_geometry.py:87` | `config={"threads": 1}` and nothing else |

No site sets a time zone. `AnalyticsSettings` (`settings.py:128–139`) declares `threads` (default
4), `memory_limit` (default `"2GB"`) and `scratch_path` (default `build/tmp/analytics`) among its
eight fields; the cache and placement map found six of the eight read by nothing, these three
among them. The library's own defaults on the workstation (library report, section E) were 32
threads, a memory limit of 150.6 GiB and a spill directory of `.tmp` relative to the working
directory.

Two kernels have no production caller: `disagreements` and `fuse`
(`semantic/analytical_kernels.py:150, 170`, exposed as methods at
`semantic/rich_relations.py:112, 115`). Their callers are in
`tests/semantic/test_rich_relations.py` only, and the Arrow schemas `RICH_MEANINGS` and
`RICH_FUSION_INPUT` (`semantic/rich_relations.py:24, 27`) serve only those two methods (inferred
by the map from a search). `FileRelation` (`semantic/capture_storage.py:78`) is referenced only
by `tests/semantic/test_capture_storage.py`.

The certification folds do not use DuckDB today. Rows arrive as Arrow, are copied into a SQLite
staging store (`FrozenPayloadStore`, `semantic/pdf_payload_validation.py:51–68`), and are read
back in key order for two digest folds: `semantic/pdf_certification.py:241`
(`ORDER BY key COLLATE BINARY` over one family) and `:330`
(`ORDER BY family COLLATE BINARY, key COLLATE BINARY`). No other production statement uses a
SQLite collation.

### SQLite and the last PostgreSQL text

Four modules open SQLite connections: `semantic/data_operation_read_index.py:53`,
`semantic/pdf_payload_validation.py:58`, `serve/selected_source.py:476` and
`serve/demand_export.py:158`; `semantic/pdf_certification.py` uses the staging store's connection.
The review counts 58 execute sites in the five modules and the cache and placement map counts 69
raw calls; the scope is every SQLite statement in the five modules either way.

Statements are concatenated at two places in the read index. A lookup joins one
`json_extract(payload, '$.record.<field>')=?` predicate per field into the `WHERE` clause
(`semantic/data_operation_read_index.py:21–27`), and index creation joins field names into both
the index name and its expression (`:72–79`). The field names come from a fixed tuple of five
groups (`:63–69`) and from the caller of the lookup. `semantic/pdf_payload_validation.py:151–168`
assembles a `WHERE` clause from fragments and generated placeholders with every value bound (from
the map; not re-read). No SQLAlchemy construct is used over SQLite anywhere today.

One hand-written PostgreSQL item remains outside the kinds ADR-0131 permits.
`target_database_privileges_sql` (`semantic/target_installation.py:623–637`) builds a `DO` block
by concatenation: a `REVOKE TEMP ON DATABASE` from `PUBLIC` and the purpose roles and a
`GRANT TEMP ON DATABASE` to the publisher, with single quotes doubled by `str.replace`. The
review also counts 37 `literal_column(` sites in 16 files, mostly identifiers and three small SQL
literals, as the route past the compiler's refusal of raw text
(`semantic/native_program.py:128–129`); no list of the sites exists.

### Release-bound inputs and the scientific policy

Preparation archives five pack files by name as release artifacts under `operation/`
(`methods.yaml`, `guideline.md`, `slices.yaml`, `interpretation-questions.yaml` and
`pm2-definition-policy.json`, `semantic/regeneration.py:110–118`, re-read) and the pack's
evaluation split beside them. Nothing reads the archived `operation/slices.yaml`.
`prepare_source_demand` finds a pack directory by matching the live `semantic.yaml` name against
archived module names without comparing bytes (`orchestrate/source_operation.py:32–68`, cited
from the identity advice) and then reads the working tree's file (`:160–164`). The release's
archived inputs already have a reader, `open_release_inputs` (`semantic/releases.py:422`).

`scientific_policy_recipe` (`semantic/scientific_evidence.py:192–243`) is a hand-written
dictionary that includes prose fields and `"bounds": [0.25, 3]` (`:229`). The kernel repeats the
bounds as `rng.uniform(0.25, 3, …)` (`:1301`). `require_scientific_policy` (`:246–257`) compares
the dictionary byte for byte with the archived artifact, so an edit to the wording refuses every
existing release, and an edit to the kernel's bounds changes nothing the recipe records. The
decision rules themselves are already validated YAML (`model/semantic/scientific-policies.yaml`,
loaded at `:66–78`, cited from the identity advice).

### What exists and is read by nothing

The cache and placement map searched `src`, `tests`, the root `tests` and root `scripts` for
readers of each candidate. Its findings, with the lines this companion re-read marked:

- `semantic_alembic/` holds `env.py`, `script.py.mako` and 1,011 files under `versions/`
  (listing re-read). Nothing reads the directory. Every other appearance of the name is the
  database table `public.semantic_alembic_version` (`semantic/migrations.py:15`) or the root test
  `tests/scripts/test_native_deployment_key.py:170`, which asserts that the deployment key's
  chain contains no entry from that tree. The live chain is `target_alembic/` (`:14`).
- `alembic/` holds `script.py.mako` and three revisions (listing re-read), with no reader. The
  pinned `alembic` library is live and is used against `target_alembic/`. The earlier model's
  `model/revisions.yaml` still names two of the revisions in its change records.
- Evaluation modules with no production importer: `evaluate/equivalence.py`, `affine.py`,
  `artifact_pilot.py`, `sampling.py`, `split_decisions.py`, `split.py` (imported only by
  `split_decisions`) and `sets.py` (one docstring line, no importer and no test). Each of the
  others has tests.
- `evaluate/operation_fitting.py` is live as a module: its types and `fit_operation_event` are
  imported by `evaluate/selected_operation_events.py:34` and
  `evaluate/declared_operation_events.py:425, 441`. Three of its functions are dead:
  `read_native_frame` (`:530`), `fit_native_operation_event` (`:552`) and `read_native_fit`
  (`:585`) (definitions re-read). They have no caller in `src`, `tests` or `scripts`, and they
  select three database functions that are defined only in `semantic_alembic/versions/`. This
  corrects the review, which describes "the native fitting path" at `:530–620` without saying
  that the rest of the module is used.
- `methods/llm/producer.py` is imported only by `tests/ingest/test_managed_recognition.py:11`;
  `methods/llm/agent_opus.py` by nothing.
- `capture_sql_changes` (`schema/model_explanation.py:413–460`, re-read) lists and compares
  `.sql` files under `semantic/sql` in the package and under `domains/<pack>`. The directory
  `semantic/sql/` no longer exists, so the explanation is empty for any change to generated SQL.
  It is called at `cli/model.py:1465–1468` and tested at
  `tests/schema/test_model_explanation.py:146–200` and `tests/test_cli_model_inspect.py:679`.
- Three items the review lists were not verified for callers by the map and are confirmed at
  entry: `pdf_shape_guard_sql` (`semantic/pdf_contracts.py:578–588`), the Unicode parity check
  (`semantic/unicode_identity.py:233–246`), and the release-side authored-SQL machinery
  (`semantic/authored_sql.py:299–369`, `semantic/native_admission_release.py:461–500`). For the
  last, the map found that `admit_archived_sql`, `prepare_release_sql` and `analyze_release_sql`
  are still called from release activation and model deployment, although nothing supplies the
  `authored-sql/…` dependencies they process.
- `acquire_publication_port` (`semantic/data_operation_admission.py:375`, re-read) is defined and
  has no caller in `src`, `tests`, the root `tests` or root `scripts`.

The earlier core and system model still has 56 importers and the model-change preview runs on it.
Its retirement, with the preview's successor, is UDM-04 in the
[model authorities companion](model-authorities-and-openness.md), not this one.

## Target design

### One rule for where analytical work runs

PostgreSQL keeps every computation that is bound to its authority: validity, support walks,
authorization, paging and ranking. Plain Python keeps small object-graph work and numerics.
DuckDB is used where a computation is set-shaped, large, and reads an immutable identified
snapshot. That is a judgment made computation by computation and not a direction of travel.

**Conditions of use**, stated once and applied to every DuckDB site:

1. *Inputs are an immutable identified snapshot*: exported Parquet, Arrow produced by the
   PostgreSQL session that holds authority, or Arrow IPC files. PostgreSQL inputs never arrive
   through `ATTACH`, which would open a second credential path and a separate snapshot.
2. *The work is set-shaped and large*: joins, grouping, windows, anti-joins or a spilling sort
   over roughly ten thousand rows or more. Tens to hundreds of rows already held as Python
   objects stay in Python.
3. *The relation is built from expression objects with declared input shapes.*
4. *The connection is configured from settings* by the one owner described next.

**One connection owner.** A single function in the production package opens every DuckDB
connection from `AnalyticsSettings` and returns it configured: `TimeZone` set to `UTC`,
`threads` and `memory_limit` from the settings, and `temp_directory` an absolute path beneath
`scratch_path` that is private to the invocation. The seven sites call it and pass no literal.
Splink receives a connection opened the same way. The time zone is not a setting: a result's
time-zone label must not depend on the machine, so the owner fixes it. The remaining unread
fields of `AnalyticsSettings` are each wired to the use they were written for, as the review
directs, unless package entry shows a reader the map missed. All of this wiring belongs to
UDM-16; the cache owner of UDM-13 declares its own settings section, and the two packages share
only the file `settings.py`.

The three sites that set `threads=1` today and the four that take every core need one answer.
The proposed default is one thread, which preserves the present behaviour of the rich kernel, the
recognition replay and the geometry joins, and removes a known source of last-bit differences in
floating-point sums across thread counts (library report, section E). The companion export then
runs with fewer threads than today. The value is a setting the operator can raise. A second,
named thread count for export work is not built; it is a candidate whose trigger is an export
slow enough to affect an operator's working loop, and no measurement is planned for it.

**A builder that refuses text.** The 2.0 relational API accepts raw strings at nearly every entry
point: `filter`, `project`, `order`, `aggregate` and the join condition take `str`, and
`sql_expr`, `rel.query` and `con.sql` take arbitrary text (library report, section A). A
convention alone therefore cannot keep text out, which is why this plan goes one step further
than the review's reliance on code review. The target is a small project-side set of relation
helpers that accept only `Expression` objects (`col`, `lit`, `fn`, `when`) and column names
resolved from a declared schema, and raise `TypeError` on `str`. This is a refusal in code at the
one place relations are built, not a lint.

The helpers name set operations by what they do. `union`, `except_` and `intersect` render as
`UNION ALL`, `EXCEPT ALL` and `INTERSECT ALL` (library report, summary item 4): they are bag
operations and keep duplicates. The companion export's multiset comparison wants exactly that.
Model logic that means a set wants the opposite. The helpers therefore expose the bag forms under
names that say "all" and the set forms as the bag form followed by `distinct`, so the choice is
visible where it is made.

**Shapes from the model where they are model facts.** An Arrow schema that only one kernel builds
and reads is an implementation detail and stays a local `pa.schema`: the candidate boxes
(`ingest/pdf_candidate_geometry.py:60–72`), the recognition replay
(`ingest/pdf_stream_reconciliation.py:233–241`) and the rich view relations
(`semantic/analytical_kernels.py:21–60`). Names inside such a schema that are model slots derive
from the model: the projected entity attributes `("id", "key", "types", "label", "symbol")` at
`semantic/analytical_kernels.py:62` come from the rule-view `Entity` class
(`model/semantic/rule-view.yaml:23`). A renamed slot then fails when the relation is built,
because DuckDB raises `BinderException` for a missing column at bind time, before execution. The
same rule covers a hand-written Arrow schema that restates a model relation instead of a working
shape: UDM-16 lists the Arrow schemas of the six modules at entry, and each one that restates a
model relation takes its field names from the model.

Three typing traps follow from the library report's probes (section D) and are handled at the
boundary. Arrow dictionary columns arrive as text; a cast to an `ENUM('…')` type string derived
from the model is applied only for a vocabulary whose **declared openness** is closed, and open
and pack-extensible vocabularies stay text, so an analysis over data that uses a term not yet
settled does not refuse. Time-zone-aware timestamps come back labelled with the session's zone,
which is why the owner sets UTC. JSON typing ends at the boundary and is re-applied on output.
Outputs are finished with a safe cast to the declared output schema, and a union that would
silently widen an integer column to text is caught by comparing `rel.types` with that schema.

### The judgment table, as decided rows

The review's table (§5) is carried here as decisions. Identifiers follow the review's analytical
inventory. "Bound" means the work needs PostgreSQL's transaction, locks, principal or writes. The
table lists the rows on which some package of this series acts.

| Row | Computation | Decision | Condition or follow-up | Package |
|---|---|---|---|---|
| G2, G3, R1 | Support walk, watermark prerequisites, tree and dependency walks | PostgreSQL | Bound; generated from the declared edge table | UDM-07 |
| G5 | Change impact | Plain Python classification | The re-encoding of support semantics is removed and revocations are indexed by node | UDM-07 |
| G4 | Semantic graph | Plain Python | Small; built once per **compiled model** and held with it in the compiled-model **cache tier** (T1) | UDM-13 |
| D1 | Rich-rule occurrence views | DuckDB, conditional | Settings from the owner; entity attributes from the model; placement settled by a bounded observation on the stage (below) | UDM-16 |
| D1b | `disagreements` and `fuse` kernels | Retire | No production caller | UDM-16 |
| D2 | Companion export inventory and multiset comparison | DuckDB | Named bag operations; UTC and spill from the owner; the materialized difference is bounded and reports its count; the `cp:` grouping and provenance columns are read from the compiled model and not from literal lists | UDM-16; the column reading is UDM-01's |
| D3 | PDF candidate geometry joins | DuckDB | Local box schema; settings from the owner | UDM-16 |
| D4 | Recognition replay external sort | DuckDB | Spill directory from the owner | UDM-16 |
| D5 | Splink scoring | Keep | Library-owned SQL; connection from the owner | UDM-16 |
| I8 | Certification staging folds | Move to DuckDB, conditional | Binary key ordering must equal today's (below) | UDM-16 |
| X2 | Companion file verification | Plain Python with carried status | Status carried per file identity in the custody **cache tier** | UDM-13 |
| X5 | Detached selected-result export | Plain Python with typed statements over SQLite | Revisit if export size makes the per-row path material | UDM-17 |
| X8 | Selected-source package verification | Plain Python with typed statements over SQLite | One set-wise ancestry query replaces per-row queries | UDM-17 |

Every other row of the review's table is kept as the review decided and needs no work from this
series: G1, S4, G7, C1 and X1 stay in PostgreSQL because they are bound to it; X6, S6, S7, S8,
S1, X7, G6, G8, G9, G10, E1 to E6, SC, I1 to I3, I6, I7, M1, T1 and T2 stay in plain Python or as
placed; and S3 was returned to the audit by the review. The improvements the review noted for I1,
I2 and S3 stay with their owners.

Two rows are conditional, and each is settled inside UDM-16, before the series' final source.

*D1, the rich-rule views.* The views are a join-and-group shape over at most 100,000 members, and
every invocation pays a round trip from Python objects to Arrow and back. DuckDB pays for itself
only if the per-subject inputs are in practice large. UDM-16 settles this with one bounded
observation on the stage: the rich-rule work of the stage's bounded project is run once and the
input row count of each view invocation is recorded, from a probe kept in the package's evidence
folder if the code does not already record it. The decision it settles is the placement. Inputs
consistently in the tens or hundreds of rows move the views to plain Python within UDM-16, and
the DuckDB dependency of the rich path, including its only use from tool threads, goes with them;
inputs in the thousands or more confirm the row. The placement is fixed when UDM-16 completes.
The final runs observe and do not tune: if UDM-22 or UDM-23 shows the placement to be wrong,
the change is made within the series and the affected evidence is gathered again. This decides a placement; it is not a performance claim.

*I8, the certification folds.* The folds are a digest over rows in key order, and the digest is a
published identity. The move is sound only if DuckDB's default string ordering equals SQLite's
`COLLATE BINARY` for these keys, which is byte order of the UTF-8 encoding in both by
documentation. UDM-16 checks this once with keys chosen to separate byte order from any other
order (see its acceptance evidence). The move is also worth making only if it removes the per-row
SQLite copy: the staging store has other readers in payload validation, and if those keep the
store alive, moving two ordered reads out of it removes little. If either the ordering check
fails or the store must remain, the row is recorded as "stays on SQLite" and the two ordered
statements convert with the rest of the store under UDM-17, with the binary collation declared
on the ordering expression. Either outcome is acceptable.

### SQL text outside PostgreSQL programs

SQLite scratch stores become SQLAlchemy Core over SQLite. Each store declares its tables as
private `Table` objects on a `MetaData` of its own, and every statement is built from them. The
stores stay what they are: per-request scratch, keyed lookups and ordered batches. No ORM, shared
schema or migration machinery is introduced, and the stores do not enter the domain model: their
tables are an implementation detail of one module, like an operation-local Arrow schema.

The read index's JSON paths are the one place that needs care (the mechanism is under
[pivotal capabilities](#pivotal-capabilities)). Field names are no longer spliced into text. A
lookup on a group in the store's declared set of indexed field groups uses the group's index. A
lookup on a group the store did not index works today, without an index, and it keeps working: it
falls back to the unindexed path with each JSON path sent as a bound parameter. Nothing is newly
refused, and no caller text reaches the statement in either case.

The database-level `TEMP` grant becomes two typed statements. It is a bootstrap operation of
installation and not an installed program, so it is UDM-17's alone. The compiler already builds
`GRANT` and `REVOKE` nodes; the only dynamic part is the database name, which installation reads
from its own connection and passes as an identifier, so the `DO` block and the quote doubling
disappear. The role names come from the existing constants until the role vocabulary of UDM-03
exists and from the vocabulary afterwards; nothing here waits for it.

The `literal_column(` sites are listed at entry and reduced by reading: where one names a relation
or column it takes the name from metadata, and the three small SQL literals become typed
expressions. No lint is added.

### Results use the release's bytes

Every path that attributes its result to a release reads release-bound pack inputs from the
release archive. The rule covers `slices.yaml` and its archived siblings alike; the one
working-tree read known at the baseline is the slices read, and UDM-18 checks the siblings'
readers at entry. Source demand selects document scopes from `operation/slices.yaml` in the loaded
release through `open_release_inputs`, with an absent file meaning no scopes, as today. A
working-tree edit to a pack's slices then takes effect through a new release, exactly as a model
edit does. The identity advice found that only the slices read uses the pack directory that
source demand looks up by name.

The scientific policy's computation parameters (bounds, tolerances, seed rules, method names)
become instance data in `scientific-policies.yaml`, validated by one LinkML class. The kernel
reads the bounds from the validated declaration. The archived recipe is the canonical
serialization of that declaration together with its schemas, computed once per **compiled
model**. An edit to the kernel's parameters then changes the recipe, because they are the same
datum, and an edit to explanatory wording changes nothing that is compared.

### Alternatives rejected

*For DuckDB settings:* leaving the literal limits at the three sites and configuring only the four
default sites keeps two sources of truth for the same resource and leaves the settings half read.
*For keeping text out:* a lint over relation calls was rejected by the project's rule against new
alignment lints; relying on review alone was rejected because the API accepts strings everywhere.
*For SQLite:* keeping the text as an accepted low-risk exception was the alternative RC02 offered
and the operator declined; moving the stores to DuckDB was rejected because they are keyed point
lookups and small ordered reads, which is the shape DuckDB is wrong for (library report, section
F). *For slices:* comparing the live file's digest with the archived one and refusing on a
difference is safe but makes the ordinary edit loop refuse instead of using the release's bytes;
recording the live digest on the result attributes it to a release whose inputs it did not use.
*For the migration trees:* keeping them as history was considered and declined by the operator;
Git holds them, and the rule protecting plans and evidence does not name migration trees.

**What would reopen a choice.** A DuckDB release that lets relation methods refuse strings
natively would make the project helpers unnecessary. Rich-rule inputs observed in the final runs
that contradict UDM-16's bounded observation reopen D1 as described. A consumer named by the
operator for any evaluation module in UDM-19's list keeps that module.

## What this supersedes

- The DDO plan's PostgreSQL companion records the `TEMP` grant as remaining authoring
  ([postgresql-realization-and-retirement.md](../declared-data-operations/postgresql-realization-and-retirement.md)
  `:463–464`, "Remaining authoring includes the fresh-root current-database TEMP grant framing").
  UDM-17 takes that item, alone. The "typed replay and installation boundaries" of the same
  passage and the "remaining inline statements" of `:446–447` are the text handoff, which belongs
  to UDM-09 in the [programs and identity companion](programs-identity-and-revisions.md).
- [ADR-0131](../../adr/0131-model-owned-postgresql-programs.md) is scoped to PostgreSQL. RC02
  extends its rule to SQLite scratch stores and DuckDB use. The decision record is written at
  UDM-00; UDM-16 and UDM-17 realize it.
- The DDO plan's efficiency work treated analytical settings as outside its scope; nothing there
  is contradicted.
- The review's R13 lists the earlier model, the evaluation modules and the migration trees
  together. This series splits them: the earlier model is UDM-04; the rest is UDM-19, which does
  not wait for UDM-04; the two uncalled kernels and `FileRelation` are retired by UDM-16.

## Pivotal capabilities

**DuckDB 2.0.0 connection configuration.** `duckdb.connect(config={…})` sets the four values of
the connection owner at connection time without a `SET` statement. Limits: `memory_limit` bounds
the buffer manager and not the process. One connection used from several threads, or queried
while an Arrow reader is open on it, raises `ResourceInUseException`; a `RecordBatchReader`
source can be read only once, and a relation re-executes on every read. The owner therefore hands
out a cursor per thread and per reader, and kernels materialize an input that is read twice.
[DuckDB library report, sections C, D and E](../../design_review/evidence/2026-11-18_production-review-inputs/library-duckdb.md).

**DuckDB 2.0.0 expression API.** `col`, `lit`, `fn` and `when(…).then(…).otherwise(…)` cover
filter, project, the listed join kinds, aggregate, order, distinct and windows with integer
frames. Limits: recursion, `QUALIFY` and interval frames need text, and none is used by the kept
computations; `duckdb.enum_type` raises `NotImplementedException`, so a closed vocabulary is cast
with a type string derived from the model. Same report, section A.

**SQLAlchemy 2.1.6 Core over SQLite.** `Table` and `Index` accept SQL expressions, so an index
over `func.json_extract(payload, path)` is declared and not written. The limit that matters:
SQLite uses an expression index only when the query's expression matches the indexed expression,
and a path sent as a bound parameter does not match an index declared with a literal path. The
indexed lookup therefore renders the path with `bindparam(…, literal_execute=True)`, which keeps
the statement cacheable; a path rendered this way is a member of the store's declared field set,
and a path outside that set is an ordinary bound parameter.
[`bindparam`, SQLAlchemy 2.1 Core reference](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/doc/build/core/sqlelement.rst).
The index-matching claim is recalled from SQLite's documentation of indexes on expressions and is
confirmed by UDM-17's acceptance evidence, which reads the query plan.

## UDM-16 — DuckDB conditions of use, declared settings, the folds and the kernels

**Result basis (I05).** Keep PostgreSQL's authorization and mutable support work in its
acquired session. Derive analytical reuse from that session's immutable identified snapshot,
the typed expression and output contract, and settings or engine behavior that can affect
observed order, multiplicity, precision or interpretation. Fix the ordering of any digest fold
explicitly. Workspace and spill locations remain execution settings absent a declared material
dependency. A thread setting participates when it can change an admitted numerical result.
Use [DuckDB 2.0 expression objects and Arrow boundaries](../../libraries/analytical_infrastructure/duckdb_2.md)
already selected here. Keep independent null, bag/set, binary key and floating-order controls
before adopting any moved fold. Use the existing bounded placement observation to decide the
physical route. An equivalent route preserves the contract and retains producer provenance.

**Vision.** The package introduces the connection owner and the text-refusing relation helpers,
moves all seven connection sites onto them, wires the unread analytics settings, derives the one
model-owned name list from the rule-view class, bounds the companion export's materialized
difference, settles the two conditional rows, and deletes the two uncalled kernels and
`FileRelation`. Its product is that no DuckDB connection in the package can be opened with
library defaults and no relation can be built from a string.

The package owns five decisions: the default thread count; the layout of spill directories
beneath `scratch_path` (private per invocation and removed on exit, as the rich kernel's
temporary directory is today); how the export difference is bounded (a stated row limit with the
full count reported, so a large difference is summarized and not silently truncated); the
placement of the rich-rule views, from its bounded observation on the stage; and the outcome of
the fold row. All five are fixed when the package completes and none is left to the final runs.
Failure behaviour: a scratch path that cannot be created or is not writable refuses at connection
time with the path named, not at the first spill; a string reaching a relation helper raises at
construction; a time zone or thread setting cannot be overridden by a caller.

**Consumer scope (complete).** The seven connection sites in the baseline table; the six
importing modules and their Arrow schemas; `AnalyticsSettings` and its unread fields; the one
caller of the rich kernel (`semantic/rich_consolidation.py:405–412`), which stops passing
literals; the entity-attribute tuple at `semantic/analytical_kernels.py:62`; the difference
materialization at `serve/companion_export.py:582–600` (line range cited from the review); the
rich view relations if the bounded observation moves them to plain Python; and the two fold
statements at `semantic/pdf_certification.py:241, 330` if the row moves. The companion export's
`cp:` grouping and provenance columns (`serve/companion_export.py:419–424, 557–589`, cited from
the independent read of this series) are read from the compiled model by UDM-01; whichever of the
two packages lands second finishes that site. Tests: `tests/semantic/test_rich_relations.py`
loses the cases for the retired kernels (`:40, 52, 64, 163–186`) and
`tests/semantic/test_capture_storage.py` loses the `FileRelation` case (`:9, 48`).

**Removes.** `disagreements` and `fuse` at both definition sites; `RICH_MEANINGS` and
`RICH_FUSION_INPUT` if the entry check confirms nothing else reads them; `FileRelation`; every
literal resource limit at a connection site; the fresh `TemporaryDirectory` in the rich kernel in
favour of the owner's spill directory.

**Prerequisites.** None. Reading the rule-view class uses whatever access to the model exists
when the package runs; once UDM-01 delivers the held **compiled model** it reads that. The enum
cast for closed vocabularies waits for **declared openness** (UDM-02) and is not needed by any
kept computation today, so until then every vocabulary column stays text.

**Native revision.** None. Nothing installed in the database changes.

**What this keeps open.** Trying a new analytical kernel stays cheap: it takes a connection from
the owner and builds relations from expressions. Operation-local shapes stay local code, so a
kernel can change its working columns without a model edit. Vocabulary columns stay text unless
the vocabulary declares itself closed, so data that uses an unsettled term is analysed and not
refused. The package newly closes one thing, the route by which SQL text could enter a relation;
that is an integrity rule about how programs are built (RC02) and constrains no knowledge
content. Resource limits become settings and remain the operator's to change.

**Acceptance evidence.**

- With the process time zone set to a zone other than UTC, a time-zone-aware timestamp exported
  through each kept DuckDB route comes back labelled UTC, and the expected value is a literal
  written in the test. A connection opened with library defaults fails this on any machine whose
  zone is not UTC.
- The effective `threads`, `memory_limit` and `temp_directory` of a connection from the owner
  equal values set in a settings object built by the test, and the spill directory is absolute.
  Changing one setting in the test changes the observed value: this is the perturbation that
  shows the setting is read. A site that kept a literal fails when the test sets a different
  value.
- Passing a string as a filter, projection, order, aggregate or join condition to a relation
  helper raises before any query runs. Each entry point has its own case, because the library
  accepts strings at each.
- A hand-written input with a duplicated row gives a hand-written expected output for the bag
  form and a different hand-written expected output for the set form of each set operation.
- Renaming a slot of the rule-view entity class inside the test makes construction of the rich
  view relation fail at bind time; without the rename it succeeds.
- For the fold row: a hand-authored list of keys that includes ASCII case pairs, a multi-byte
  character, a key that is a prefix of another and a key containing a character above the basic
  multilingual plane, with the expected order written by hand as UTF-8 byte order, is sorted
  identically by the existing SQLite statement and by the DuckDB sort. Separately, a retained
  certification's recorded digest is reproduced. A different ordering changes a published
  identity, so a mismatch in either leaves the row on SQLite.
- The bounded observation's record states the row counts seen per view invocation on the stage
  and the placement they decided, so that the decision can be read against its evidence.
- A search of the production package finds no `duckdb.connect(` outside the owner. This is a
  search made once for acceptance and is not added to `ci check`.

## UDM-17 — SQLite stores on typed statements; the last hand-written PostgreSQL item

**Vision.** The package realizes the design under
[SQL text outside PostgreSQL programs](#sql-text-outside-postgresql-programs): each of the five
modules that speak to SQLite declares its tables once and builds every statement from them, the
`TEMP` grant becomes typed statements, and the `literal_column(` sites are reduced. The read
index keeps its behaviour, keyed lookups that must find exactly one record. The detached export
and the selected-source verification keep plain Python around typed statements, and the per-row
ancestry queries of the verification become one set-wise query (row X8).

The package owns the choice, per store, between an expression index over the JSON payload and
extracting the indexed keys into real columns at insert. The second removes JSON paths from the
statements and is simpler where the indexed groups are fixed; the first suits a store whose
lookups name groups dynamically. The choice is made by reading each store's callers. Failure
behaviour: a lookup on an undeclared field group is answered by the unindexed path and is not
refused; a failed grant or revoke at installation reports the statement and the database, as a
typed program's failure does.

**Consumer scope (complete).** Every SQLite statement in
`semantic/data_operation_read_index.py`, `semantic/pdf_payload_validation.py`,
`semantic/pdf_certification.py`, `serve/selected_source.py` and `serve/demand_export.py`,
re-counted at entry. The one PostgreSQL function `target_database_privileges_sql` and its callers
in installation. The `literal_column(` sites: 37 in 16 files by the review's count, listed in
full and re-counted at entry. The tests of the five modules keep their expectations; a test that
asserts on statement text, if any exists, is rewritten to assert on behaviour.

**Removes.** String-built SQLite statements in the five modules; the `DO` block and its quote
doubling; `literal_column` used to carry SQL literals.

**Prerequisites.** None. The role names in the grant read the existing constants now and the
role vocabulary once UDM-03 provides it.

**Native revision.** None. The grant is a database-level privilege applied by the fresh-root
bootstrap (`semantic/target_installation.py:950–951`, cited from the independent read) and is not
a desired object of the frozen native state. Its text appears in the frozen root upgrade file of
`target_alembic/`, which stays as it is, frozen migrations being a standing exception; only the
forward path changes.

**What this keeps open.** Scratch stores remain private and cheap to reshape: adding an indexed
field group is one declared entry, and a new store is one module with its own tables, outside the
domain model and outside any vocabulary. Nothing about what a store may hold is constrained, and
a lookup by a field group nobody declared, which is what an exploratory caller writes first, keeps
working without an index. The package newly closes one thing, the route by which a name could
reach statement text, which is an integrity rule about how statements are built (RC02).

**Acceptance evidence.**

- For each indexed field group of the read index, SQLite's own `EXPLAIN QUERY PLAN` for the
  lookup statement reports a search using that group's index. A path sent as a bound parameter,
  or an index expression that differs from the lookup's, produces a scan and fails this.
- A lookup on a field group the store does not declare returns the same record a declared lookup
  would, with the expected payload written in the test. The statement text seen by the
  connection's trace callback contains a parameter marker where the path stands and none of the
  group's field names, and its query plan is a scan. An implementation that refused the lookup, or
  that spliced the names into the text, fails this.
- A record whose field value contains a quote, a percent sign and a JSON-path metacharacter is
  stored and found by exact lookup, with the expected payload written in the test.
- The existing behavioural tests of the five modules pass unchanged in expectation.
- On a freshly installed target database, PostgreSQL's catalog shows `TEMP` held on the database
  by the publisher and not by `PUBLIC` or any purpose role. The expectation is a hand-written list
  of role and privilege pairs compared with `has_database_privilege`, not the generator's own
  output. The same check runs against a database whose name needs quoting.
- A search of the five modules finds no `execute` call whose statement argument is a string. This
  is a search made once for acceptance and is not added to `ci check`.

## UDM-18 — Release-bound inputs, the derived scientific policy, and two small causes

**Scientific policy slice Tested · 2026-11-19.** The LinkML `ScientificPolicy` declaration
owns sampling bounds and comparison decisions. Compilation projects the typed policy, records its
material settings in the prepared release and supplies the archived policy to the numerical
kernel. An independent check observed the changed sample range after a bounds edit and stable
recipe comparison after a descriptive edit. A private PostgreSQL candidate with the typed policy
passed native admission, explicit proof and archived readback on N34
(`be2952456037438093905160b12094d6`, `test_typed_scientific_candidate_admits_on_the_registered_kernel`).
The stage continues to select the UDM-12 cutover release. Native generation reported
`no_native_change` with the database endpoints unreachable (`3d5afd411ee4496f8a0b1be1c4ed08f2`).

**Scientific determinants (I01/I05).** Keep the release-bound bytes and actual producer evidence
for every result. Feed the policy, model assets, grammar and runtime or precision parameters that
can change the observation into UDM-10's producing identity. Demonstrate one setting that changes
meaning and one operational-only change with an independently expected reuse fate.

**Vision.** Four changes share a shape: a fact that determines a result gets one home, and the
code that used a second copy reads the home. The first two are designed under
[Results use the release's bytes](#results-use-the-releases-bytes).

*Slices and their siblings from the release (R17).* Beyond the design above, the name-matching
lookup of the pack directory goes if the entry check confirms that nothing else in
`prepare_source_demand` needs the directory. The review's recommendation names slices "and
siblings", so the entry step also searches for readers of the other archived pack inputs listed
in the baseline; any path that attributes a result to a release and reads one of them from the
working tree moves to the archive in the same way, and the completion note records the search
even if it finds none.

*The scientific policy (R14).* The recipe's bytes change once, so existing releases are prepared
again. That re-preparation is the one native revision A already forces, so releases are prepared
once for both.

*The decimal expansion bound (DA-040).* The bound becomes one declared limit of the value codec,
read by the Python codec (`semantic/value_codec.py:15–20`) and by the generator of the native
canonicalizer (`semantic/data_operation_value_native.py:112–149`; both ranges cited from the
review), so an oversized exponent is a classified value refusal on both sides and not an
unbounded expansion on one.

*The qualifier partition (DA-001).* The per-predicate qualifier lists are compiled, validated and
archived and are read by nothing. Either scientific grouping reads the compiled
`ComparisonProjection.partition` where it now keys on `qualification_meaning`, or the declaration
retires. The review leans to connecting it, because the statistics pack declares a non-trivial
partition, and marks the choice as the owner's. This plan carries it as an open premise below;
the default, if the owner does not choose otherwise, is to connect it.

The package owns the shape of the scientific policy class and the name and home of the codec
limit. Failure behaviour: a release without archived slices behaves as one with none; a policy
file that does not validate refuses at preparation with the LinkML diagnostic; a value beyond the
codec limit is refused with the same classification by the Python codec and by the installed
canonicalizer.

**Consumer scope (complete).** `orchestrate/source_operation.py:32–68` and `:160–164`;
`semantic/scientific_evidence.py:192–257` and the kernel's sampling at `:1301`; the policy YAML
and its loader at `:66–78`; the two value modules; and, if connected, the scientific grouping
that keys on `qualification_meaning`. Tests of source demand that place a `slices.yaml` in a
working-tree pack directory move to a prepared release that archives one.

**Removes.** The working-tree read of `slices.yaml` and the name-matching pack lookup; the
hand-written recipe dictionary and the literal bounds in the kernel; the two separate copies of
the decimal bound.

**Prerequisites.** None for slices, the policy or the partition. The policy class is authored in
LinkML directly and does not wait for the declaration grammar of UDM-02.

**Native revision.** The slices, policy and partition changes install nothing and need no
revision; the identity advice notes that the policy needs one only if the scientific layout in
the deployed descriptor changes, which this design does not require. The decimal bound changes
the generated canonicalizer and therefore installed program bytes, which generating the
canonicalizer and comparing it with the current frozen object confirms. It joins native revision
A and plans none of its own. If revision A has already been frozen when this part is ready, it
joins revision B.

**What this keeps open.** An exploratory slice added to a pack while a release runs costs what it
cost before: the running release keeps its archived slices and the new slice is available as soon
as a release is prepared with it; only attribution becomes exact. Scientific parameters remain
editable data, and wording can be revised without refusing any release. Connecting the partition
lets a pack's choice of distinguishing qualifiers take effect without code. The package newly
closes one thing, the admissible range of the value codec, which is a property of the codec's
integrity and not a limit on what knowledge may be recorded: a value beyond it is refused with a
classification, as other inadmissible values already are.

**Acceptance evidence.**

- A release is prepared with slices X. The working tree's `slices.yaml` is then changed to Y
  inside the test. A source demand under that release selects the scopes of X, and the expected
  scopes are written by hand. The present code selects Y and fails. With the pack directory
  removed entirely, the demand still succeeds.
- A release prepared from a pack with no `slices.yaml` yields a source demand with no scopes.
- Changing a bound in the policy declaration inside the test changes both the samples the kernel
  draws (observed as values outside the old range under a fixed seed) and the recipe; changing
  only a descriptive field of the declaration leaves the recipe's comparison passing against a
  release prepared before the edit. The present code fails both halves.
- A decimal with an exponent beyond the declared limit is refused by the Python codec and by the
  installed canonicalizer with the same classification; a value at the limit is accepted by both
  and both produce the same canonical text, which the test states literally.
- If the partition is connected: two facts that differ only in a qualifier the pack declares as
  distinguishing fall into different scientific groups, and two that differ only in a qualifier
  it does not declare fall into the same group; the expected grouping is hand-authored, and moving
  the qualifier between the two lists in the test moves the outcome.

## UDM-19 — Retirement

**Improvement integration.** Retire obsolete hand-computed preview explanations and partial shell
recovery actions when UDM-04/26 switch their consumers. Retire old custody or identity shortcuts
with the implementing owner (UDM-07/10/13/14/25). Preserve accepted archive provenance and useful
independent checks. UDM-19's own deletions retain the existing consumer and generated-byte checks.

**Vision.** The package deletes what nothing reads and retargets the one explanation that reads a
place that no longer exists. Its subject is the list in the baseline section
[What exists and is read by nothing](#what-exists-and-is-read-by-nothing), which is not repeated
here. No part of the package waits for another package. It is ordered inside itself by risk to
the operator: the preview explanation comes first, because it reports "no SQL change" for changes
to generated SQL today; the migration trees and the dead code follow; the one removal that might
change installed bytes is timed against revision B.

*The preview's SQL explanation.* `capture_sql_changes` stops walking `semantic/sql` and
`domains/<pack>` with Git and instead explains the difference between the two generated-SQL
snapshots the model-change preview already holds, the baseline's and the candidate's. The
explanation's consumers keep their interface. A change that alters a generated statement is then
reported, and a change that alters none is reported as none because none was found and not
because the place searched is empty. UDM-04 later gives the preview a successor that compares
two compiled models; this retarget does not wait for it.

*The migration trees.* Deleting `semantic_alembic/` and `alembic/` is decided (operator,
2026-11-19). The confirmation is performed on the head at execution and recorded in the commit.
The reader search is repeated over `src`, `tests`, the root `tests`, root `scripts`, the
`justfile` and tool configuration for both directory names, and every hit must be the database
table name, the pinned `alembic` library or the one root test named below. The chain used by
authoring, deployment and the deployment key must be `target_alembic/`, with neither directory
listed in packaging or build configuration. No evidence folder's runnable script may import from
either tree; evidence that merely cites a revision by name stays as written, and evidence is
never edited or deleted. The two directories are then deleted in one commit that names them, so
that recovery is one Git command.

The database table `public.semantic_alembic_version` keeps its name: it is a deployed object and
renaming it would be a native change for no gain. The root test
`tests/scripts/test_native_deployment_key.py:170`, which asserts that the key's chain has no
entry from `semantic_alembic/`, would pass vacuously after the deletion and is removed with the
tree it guards against. The test series records that its deployment key hashes the wrong
migration tree; the confirmation reads which tree that is, and if it is one of the two deleted
here, the finding is reported to the test series before the deletion and the key is not changed
by this package. The earlier model's `revisions.yaml` names `alembic/` revisions and retires with
the earlier model in UDM-04; nothing reads those fields to open a file, so the deletion does not
wait for it.

*Dead code.* The three native functions of the fitting module are deleted and the module stays,
with its entry in the hand-kept boundary list at `evaluate/declared_operation_events.py:46–57`
unchanged. The evaluation modules with no production importer are deleted with their tests,
after the operator confirms that none has a consumer outside the repository's code:
`evaluate/sampling.py` and `evaluate/split.py` are used by golden-set tests and may serve golden
generation, which is the case the review's "unless the operator names a consumer" exists for.
`evaluate/equivalence.py` imports the earlier model's `core/keys.py`. Deleting a module that
imports the earlier model does not need the earlier model to be retired first, so it is deleted
here, and UDM-04's list of `core/keys.py` importers drops it; the same holds for the tests of
every listed module. The two LLM producer modules are deleted, with the one test import of
`producer` moved or removed. `pdf_shape_guard_sql` and `acquire_publication_port` are deleted
once the entry search confirms that neither has a caller. The Unicode parity check is either
wired to the release check it was written for or deleted; this is an owner decision, and the
default is deletion, because a check that nothing calls gives no assurance.

*The release-side authored-SQL machinery* is removed together with its three calls from release
activation and model deployment, leaving the live submitted-SQL analyser. UDM-01 migrates one
site inside the removed range (`semantic/authored_sql.py:350`); whichever of the two packages
lands second drops that site.

Failure behaviour is simple: each deletion is preceded by its reader search on the execution
head, and an item that has gained a reader since `cb4e09667` is not deleted and is reported to
the coordinator.

**Consumer scope (complete).** Every item of the baseline list, with the callers and tests named
there, and in addition: the two directories (1,013 files and four files) and the root
deployment-key test; the tests of the seven evaluation modules
(`tests/evaluate/test_equivalence.py`, `test_affine.py`, `test_split_decisions.py`,
`tests/evaluate/golden/test_split.py`, `test_sets.py`,
`tests/semantic/test_artifact_identity.py:433–463`, `tests/semantic/test_trace_reference_fixture.py:11`,
`tests/math/test_scope.py`, as the map lists them); and the calls of the authored-SQL machinery
in release activation (`semantic/releases.py:569` onward) and model deployment
(`schema/model_deployment.py:678` onward). The package removes all of it.

**Prerequisites.** None. The operator's confirmation precedes the deletion of the evaluation
modules, and the owner's decision precedes the Unicode parity check; neither is a capability of
another package.

**Native revision.** None for the directories, the Python modules, the preview or
`acquire_publication_port`. Removing the release-side authored-SQL machinery touches a generator
of the release guard. Whether that changes installed bytes is answered by generating the programs
after the removal and comparing them, statement by statement, with the objects and privileges of
the head frozen revision. If they differ, the removal joins native revision B, before B is
frozen, and plans no revision of its own. If they do not, it is a Python change only.

**What this keeps open.** Nothing exploratory is closed. Every deleted item is recoverable from
Git by path, and an evaluation module with a real use is kept on the operator's word. The preview
explanation becomes more useful to exploration, because a model edit made to see what it changes
in the generated SQL is now answered. Retiring the migration trees removes no ability to deploy
or to author a revision, since both use `target_alembic/`.

**Acceptance evidence.**

- A model change that alters one generated statement, made inside the test, produces an
  explanation naming that program, with the expected program name and the changed fragment
  written by hand. A change that alters none produces an empty explanation. The present code
  returns empty for both and fails the first.
- After the deletions, the repository's ordinary routes that could have read the trees still
  work on a fresh target database: rollback-only authoring of a candidate, deployment, and the
  deployment key's computation. These are existing tests and commands; they are named in the
  package's completion note with their receipts.
- Importing every module of the production package succeeds, and a search made once for
  acceptance finds no reference to any deleted function or module.
- The fitting module's remaining public names are importable and its existing tests pass.
- The comparison of generated programs with the head frozen revision, before and after the
  authored-SQL removal, is retained with the package's completion note, whichever way it came out.

**Handover, not scope: catalog snapshots in the deployed tree.** Each frozen revision in
`target_alembic/` freezes the full catalog again: the 46 catalog files in the tree total 387 MB
(46 files confirmed by listing; sizes quoted from the identity advice), and the audit's figure
for N14 to N29 alone is about 206 MB as ordinary Git objects. This series does not change what a
revision freezes; UDM-11 reduces how often one is authored. How frozen revisions are stored
belongs to the owner of the deployed tree's lifecycle, and the coordinator records the
[handover](../unified-domain-model-and-execution_2026-11-19.md#handovers).

## Open premises

| Premise | Evidence that settles it | Work it constrains |
|---|---|---|
| The staging store can be removed from the certification path once the folds read Arrow directly | Reading the store's other readers in payload validation at entry | The I8 row of UDM-16; if not, the folds stay on SQLite and convert under UDM-17 |
| DuckDB's default string order equals `COLLATE BINARY` for certification keys | The hand-ordered key list and the reproduced digest in UDM-16's acceptance evidence | The I8 row |
| Rich-rule inputs are large enough for DuckDB to pay for itself | UDM-16's bounded observation on the stage: input row counts per view invocation for the stage's bounded project | The D1 row: the placement, fixed inside UDM-16 |
| The qualifier partition should govern scientific grouping (the review's lean) and not retire | The pack owner's decision; the default is to connect it | The partition part of UDM-18; the other three parts are unaffected |
| No evaluation module in UDM-19's list has a consumer outside the repository's code, golden generation in particular | The operator's confirmation | Deletion of `evaluate/sampling.py`, `split.py`, `split_decisions.py` and the others |
| The Unicode parity check is not wanted by the release check | The owner's decision; the default is deletion | One function in UDM-19 |
| Removing the release-side authored-SQL machinery changes no installed program byte | Generating the programs after the removal and comparing them with the head frozen revision | Whether that removal joins native revision B |

## State

| Package | State |
|---|---|
| UDM-16 | Not started |
| UDM-17 | Not started |
| UDM-18 | Scientific policy slice complete against private N34. The decimal bound landed with N30. Archived pack inputs and qualifier partition remain open. |
| UDM-19 | Not started |

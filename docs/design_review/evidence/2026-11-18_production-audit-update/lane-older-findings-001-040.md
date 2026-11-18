# Lane OLDER-A: older findings DA-001 to DA-040 (except DA-033) at `5139eaba3`

Audit lane, diagnosis only. No remedy is selected. Read-only; nothing in the working tree was
edited, run or queried.

## Method and limits

- **Source facts** come from the frozen snapshot `snap6/` of `5139eaba3`. `src/…` paths are
  relative to `snap6/python/corpus-structure/`; package paths omit
  `src/corpus_structure/`. `domains/` is not in the snapshot and was read with
  `git show 5139eaba3:domains/…` (read-only).
- **What each finding claimed** was taken from the audit pages in Git: `f9695d3db` (first
  account, DA-001…025), `85787108d` (go-forward refresh, DA-026…049, full diagnoses), and
  `fbd3f2a98` (last full text, mostly recorded corrections). I read the `85787108d`
  sections for DA-001…011 and DA-026…028/034 in full. For the other pages I read the
  diagnosis and consequence parts and skimmed the rest. I read the `fbd3f2a98` text of all
  seven pages in full.
- **Removal commits** come from `git log --diff-filter=D -1 5139eaba3 -- <path>`.
- **Counts** are `grep` counts over the snapshot, stated where used. They include benign
  matches.
- **Recurrence checks** looked for the same structural cause in the code that replaced each
  cited subject. Searches were by name and by concept. A search that finds nothing does not
  show the cause is absent.
- **Not done:** no execution, no database work, no probe reruns (P1–P6), and no test-account
  pages. Design documents were sampled: D2's opening, DESIGN §B6 and the binding map.

## Status table

Status words follow COMMON.md. "Holds" means a recorded correction was checked at
`5139eaba3` and still describes the code.

| ID | Claimed (one sentence) | Subject at `5139eaba3` | Status | Conf. |
|---|---|---|---|---|
| DA-001 | Which qualifiers distinguish facts was declared twice (`cs:key_role` per property vs `cs:qualifiers`/`cs:identity_qualifiers` per predicate), with opposite defaults and nothing relating them | Both declarations exist. The predicate lists are compiled and validated, but no reader uses them | **Changed footprint**: the second declaration is now inert | High |
| DA-002 | Closed vocabularies were restated across semantic, catalog, physical, native and code owners, and some had diverged (reference split; value kinds) | The legacy and released models still both declare them; the reference-set tables are gone | **Superseded** by DA-072 (the two models), DA-086 (literals) and DA-085 (JSON-string constraints); the split divergence no longer applies | Medium |
| DA-003 | Declared category roles had no effect, and the behaviour actually used was keyed on literals | The `enum_members(subset=)` pattern is now used widely, but some declared subsets are still unread and `"primary"` literals remain | **Partly corrected** | Medium |
| DA-004 | Validated models and release annotations were re-parsed as dicts and raw strings by each consumer | Old sites gone. Raw `cs:` annotation strings are still decoded per consumer in the rich modules | **Changed footprint** (annotation half); the conversion half was withdrawn on 11-05 | High |
| DA-005 | Context translations (candidates to rule view, etc.) were not owned contracts and lost meaning | `semantic/rule_views.py` | **Corrected, holds** | High |
| DA-006 | References carried no kind (retired 10-29) | Typed by `cs:reference_role` and foreign keys | **Corrected, holds** | High |
| DA-007 | Unresolved references and unsettled identities were prose or silent defaults, not typed states | Typed `RichEntityResolution`; `DdoRichIdentityResolution` members | **Corrected, holds** | Medium |
| DA-008 | The canonical text form erased case globally (retired) | Case is folded only where declared | **Corrected, holds** | High |
| DA-009 | Identity determinants were hand-listed in several places; identity recipes were unversioned mirrors (canonical JSON diverged, probe P4) | `semantic/determinants.py` is the one owner; the Unicode check has no caller; native `data.canonical_json` remains | **Partly corrected** | Medium |
| DA-010 | Source profiles sat outside the schema version (retired; the residue went to DA-028) | Closed acquisition manifest | **Corrected, holds** | Medium |
| DA-011 | The design collection restated executable contracts, and the copies drifted (compiler versions) | D2 opening and code agree (compiler 24 / boundary 13) | **Corrected, holds** for the version restatement; the whole collection was not examined | Medium |
| DA-012 | Operational closed sets had no go-forward authority (legacy `core.vocab`, unconstrained TEXT columns) | Legacy model still live; task-state literals remain | **Superseded** by DA-072 and DA-086 | Medium |
| DA-013 | Outcomes and refusals were prose; declared outcome domains were not emitted; adapters flattened causes | A typed CLI failure boundary exists, but semantic code still mostly raises plain `ValueError` | **Partly corrected**; DA-079 is a current instance | Medium |
| DA-014 | Source coordinates had two diverging grammars, two encodings and positional item keys | Native locator function and the HTML path removed; legacy `LocatorIndex` is reachable only through an unused parameter | **No longer applicable** (`48be40472` and earlier); residue belongs to DA-080 | Medium |
| DA-015 | No rule selected the current pass's M19 verdicts | `consolidate/finalize.py` removed | **No longer applicable** (`9268b15bf`) | High |
| DA-016 | Escalation and confidence policy declarations compiled without consumers | `orchestrate/policy.py` and pack `policies.yaml` gone | **No longer applicable** (`a49758618`) | High |
| DA-017 | `agent_reuse: by_unit` overrode the reuse key without defining it (retired) | Only legacy `core/vocab.py:790–794` keeps `AgentReuse.BY_UNIT` | **No longer applicable** (`8b7b369a9` removed `orchestrate/semantic.py`); residue belongs to DA-072 | High |
| DA-018 | Server extension versions were neither pinned nor reconciled (retired) | `core/db/extensions.py:3–17, 32–71`; `core/db/host_bootstrap.py:315–319`; `docs/pins.md` row | **Corrected, holds** (from source; not provisioned) | Medium |
| DA-019 | The test-database sweep could drop another session's template (retired) | Owned by the test account | **No longer applicable to this account**; not checked | — |
| DA-020 | Cluster coordinates, principal names and resource settings were repeated or unconsumed | Analytics resource settings are declared and unread; principal names are literals in 23–30 modules each | **Changed footprint** (resource settings); principal names are **superseded** by DA-074 | High |
| DA-021 | Design claims cited evidence records as free text (retired) | `tools/evidence/src/corpus_evidence/citations.py` | **Corrected, holds** (file present; not run) | Medium |
| DA-022 | The dependency check was narrower than AGENTS.md stated (retired) | `scripts/check_pins.py:3–18` covers the uv workspace and Cargo | **Corrected, holds** | High |
| DA-023 | The binding's map of binding decisions was empty (retired) | `docs/design_review/design_principles/binding/corpus-structure.md:258–263` | **Corrected, holds** | High |
| DA-024 | The final transaction held the run lock across measurement and evaluation (retired) | `semantic/publication.py` removed | **No longer applicable** (`47dc7b873`) | High |
| DA-025 | Keying repeated rendition-wide work for each statement (legacy) | Legacy `core/keys.py` survives with only helper consumers | **No longer applicable**; the surviving module belongs to DA-072 and DA-080 | Medium |
| DA-026 | No release product declared the operation bindings, so native and Python code bound platform roles by name | `effective_bindings.json` is compiled; native code has no `SourceStatement`; a raw-YAML `is_a` scan remains | **Partly corrected** | High |
| DA-027 | The model layers described the knowledge and execution records without governing them | Enforcement claims are typed and resolved, but almost all are `documentation` | **Stands** as a limit (changed footprint) | Medium |
| DA-028 | Runs and served queries executed the live pack files that the bound release archives | Query plugins gone. Source demand reads live `slices.yaml` although the release archives it | **Changed footprint** | High |
| DA-029 | Immutability was enforced unevenly across release, content, observation and grade rows | Triggers are derived from `ph:immutability`; the trust-in-definer premise is unchanged | **Corrected, holds** (mechanism changed); residual premise belongs to DA-033 and DA-074 | Medium |
| DA-030 | Principal separation did not cover the release lifecycle; purpose principals were derived by renaming the user | Explicit per-purpose credentials and a native principal check | **Corrected, holds** | High |
| DA-031 | Relation structure had two hand-maintained authorities, compared by name only | Alembic comparison with CHECK and index plugins, plus native table catalog checks | **Corrected, holds**, and extended to indexes | Medium |
| DA-032 | Native evolution was propagated by hand, frozen revisions were edited, and no deployment identity was recorded on results | Frozen bases; results carry kernel digests, not the deployment | **Partly corrected**; the open question goes with DA-068 | Medium |
| DA-034 | Scientific equivalence had two authorities, and selection used the sampled, casefolded one | One owner, `semantic/scientific_evidence.py`; legacy `ValueComparator` has no importer | **Corrected, holds**; successor issue is DA-077 | High |
| DA-035 | Coverage producers and consumers used different vocabularies, so absence could never be stated | `serve/journey.py` removed | **No longer applicable** (`bcff594c2`); successor checked only lightly | Low–Med |
| DA-036 | Selection status was an undifferentiated filter, not a served attribute | `semantic/query.py` removed | **No longer applicable** (`957ff2231`); served rows now carry `standing` | Medium |
| DA-037 | Grades conflated not-matched with not-comparable and conditioned their universe on extraction | `evaluate/semantic.py` removed; `evaluate/split_decisions.py` has no importer | **No longer applicable** (`7fc25ca02`); successor evaluation not examined | Low |
| DA-038 | The kernel's paged query route had no production consumer, and serving used private members | `serve/read.py` and `serve/queries.py` removed | **No longer applicable** (`bcff594c2`); low-weight residue noted below | Medium |
| DA-039 | Explanation and path queries were unbounded | `serve/explain.py` and the statistics `queries.py` removed | **No longer applicable** (`5aae3c780`, `bcff594c2`); successor reads are bounded | Medium |
| DA-040 | Value admissibility was enforced late and only in part at boundaries (establishment, NaN, unbounded decimal expansion) | Establishment uses the `source_admissible` subset; decimal expansion is still unbounded | **Partly corrected**; the decimal case recurs | Medium–High |

## Notes on the identities that need them

**DA-001 (changed footprint).** `compile_comparison_projection` validates the predicate lists:

- names must exist on the qualification class;
- provenance properties are refused;
- the identity list must be a subset of the qualifier list.

See `semantic/comparison_projection.py:92–171`. The result is archived as
`comparison_projection.json` (`semantic/prepare.py:941–950, 1077`) and re-read with checks
(`semantic/archive_reader.py:169–171`).

Nothing uses its comparison partition. `ComparisonProjection.partition`
(`comparison_projection.py:66–84`) has no caller (repository-wide search). `RichRulePolicy`
stores the projection and nothing reads it (`semantic/rich_rules.py:60`). Scientific grouping
instead keys on `fact.qualification_meaning`, which is derived from `key_role`
(`semantic/rich_scientific.py:205–217`).

The statistics pack still declares a non-trivial partition for `transformation_of`:
`cs:qualifiers: transform param_mapping` against `cs:identity_qualifiers: transform`
(`domains/statistics/semantic.yaml:461–462`). That is the same example the 10-29 finding
cited, so the earlier silent disagreement has become a validated declaration that governs
nothing. Today the effect is latent: that predicate is multivalued and not functional, so it
never reaches scientific comparison.

**DA-002 (superseded).** DA-072 now records the same cause: one closed set held by several
owners, here the earlier and released models. DA-086 records literal restatement and DA-085
the JSON-string physical constraints.

The split divergence no longer applies. No `reference_set` relation exists in `src/` (search),
and `ReferenceSplit` is LinkML-only with an `executable` subset
(`model/semantic/reference.yaml:220–224`), consumed at `semantic/types.py:361`.

Establishment now has a declared `source_admissible` subset (`model/semantic/core.yaml:597–601`).
Value-kind correspondence between the physical CHECK, the writer and the reader was not
re-traced.

**DA-003 (partly corrected).** Roles are now declared and read through `enum_members(subset=…)`
at:

- `semantic/types.py:346, 361, 363–364`;
- `semantic/rule_views.py:332–335`;
- `semantic/statement_types.py:213`;
- `semantic/proposals.py:113`.

Two parts remain:

- **Unread subsets.** The `ClaimModality` subsets `conflict_bearing`, `reserved` and
  `attribution_identifying` (`model/semantic/core.yaml:676–698`) have no reader outside legacy
  `core/vocab.py:996–1028` and `core/_model/qualifiers.py:85`. `cs:extract` is still
  allowlisted (`semantic/prepare.py:84, 237`), and no reader by name was found.
- **Literal behaviour.** The evidence role `"primary"` decides behaviour as a literal at
  `semantic/rich_knowledge.py:209`, `semantic/rich_identity_exclusions.py:91` and
  `semantic/rich_proposal_lowering.py:41`.

The original sites (`domain_operations.py`, `serve/read.py`, `orchestrate/semantic.py`) were
removed in `64455a0f1`, `bcff594c2` and `8b7b369a9`. DA-086 is the nearest current finding.

**DA-004 (changed footprint).** Release annotations are still raw strings in the registry
metadata, and each consumer decodes them itself. 36 `.get("cs:…")` sites in `semantic/` and
`serve/` (grep), including:

- `rich_scientific.py:210–211`, with the same `str(...).lower() == "true"` pattern the
  original cited;
- `rich_knowledge.py:238, 244, 279, 303, 361`;
- `rich_rule_evaluation.py:432, 867, 881`;
- `rich_queries.py:303`;
- `rich_graph_validation.py:602`.

Class-level `cs:case` and property-level `case_policy` are still separate notions under similar
names (`rich_knowledge.py:238` against `:264`). This partly overlaps DA-085, whose subject is
physical `ph:` JSON, not semantic `cs:` annotations.

**DA-007 (holds).** Decisions are typed: `basis` and `outcome ∈ {resolved, incomplete_key,
ambiguous_anchor, ungrounded_cycle}` (`semantic/rich_knowledge.py:61–70, 371–407`). They are
retained as `DdoRichIdentityResolution` members that rule evaluation consumes
(`semantic/rich_rule_evaluation.py:476–482`).

The outcome set is a Python literal written three times (`rich_knowledge.py:66`,
`rich_decisions.py:12`, `rich_rule_evaluation.py:479–481`), with no model declaration
(search). That is low weight and belongs with DA-086.

**DA-009 (partly corrected).**

- **Determinants: corrected.** One owner now holds the determinant lists, including sympy,
  numpy, python and the Unicode recipe (`semantic/determinants.py:1–34`). `prepare.py:30` and
  `orchestrate/execution_host.py:68` consume it. The breadth of implementation identity is
  DA-069.
- **Unicode parity: no production caller.** `require_unicode_identity_release`
  (`semantic/unicode_identity.py:233–246`) has had no production caller since `bcff594c2`
  removed the serving path that invoked it. Folding identity now looks Python-only. The one
  native fold found folds both sides inside PostgreSQL (`semantic/visual_read_native.py:62–68,
  113`), so no cross-language parity is needed there. This is inferred from a search of
  `*_native.py` for `casefold`/`lower`. The dormant check belongs with DA-080.
- **Canonical JSON: two implementations remain.** Native `data.canonical_json` is defined in
  the frozen revision SQL and used by generated programs (`semantic/runtime_binding_native.py:125–128`;
  `semantic/data_operation_value_native.py:76`). Python has its own `canonical_bytes`
  (`semantic/identity.py:13`). Probe P4's numeric-rendering difference was not rerun.

**DA-013 (partly corrected).** The CLI now separates three classes of failure:

- database failures with phase and effects;
- typed refusals (`SemanticRefusal`, `ValidationError`, `NativeResultViolation`);
- programming errors, which keep their identity.

See `cli/failures.py:1, 37–44, 58–88` and `semantic/refusals.py:23–93`. Domain code still
mostly refuses with prose: 3,163 `raise ValueError(` across 265 files in `semantic/` (grep),
against 13 `SemanticOperationRefusal(` constructions. A plain `ValueError` is not in the
expected-refusal set, so the boundary does not classify it as a refusal. DA-079 (an
unclassified busy refusal) is one current instance of the cause.

**DA-014 (no longer applicable).** The native `ops.source_locator_segment` function survives
only in frozen `semantic_alembic/versions/*` SQL. Whether that chain is still deployed was not
checked.

`semantic/proposals.py:21, 290, 325–329` keeps the legacy `LocatorIndex` branch behind an
`index` parameter that no caller passes (`proposals.py:614`). That is unused machinery and
belongs to DA-080.

**DA-020 (changed footprint).** Most `AnalyticsSettings` fields are unread:

- `threads`, `memory_limit`, `scratch_path`, `capture_mode`, `resident_limit_bytes` and
  `batch_size` (`settings.py:129–139`) are read nowhere (grep `analytics.<field>`; zero hits);
- only `adbc_driver_path` and `batch_size_hint_bytes` are read (`serve/companion_export.py:139,
  178`; `serve/database_description.py:236`).

The DuckDB rich-relation kernel takes `threads=1, memory_limit="2GB"` as literals
(`semantic/rich_consolidation.py:405–412`). So the resource settings are again declared and
unconsumed, which is the original cause at a new site. The 11-03 correction, where settings
were forwarded into `AnalysisScope`, went with `64455a0f1`.

Principal names are repeated: `corpus_sem_writer` appears in 30 files and 47 lines,
`corpus_sem_publisher` in 23 files and 46 lines (grep). DA-074 now records that.

**DA-026 (partly corrected).**

- **Corrected:** binding is a compiled release product (`semantic/statement_types.py` via
  `semantic/prepare.py:887–950, 990, 1133`), and no `*_native.py` names `SourceStatement`
  (search).
- **Remaining:** the raw-YAML inference that diagnosis item (1) named, which matches
  `is_a == "Qualification"` / `"SourceStatement"` on direct children only and refuses a second
  one (`semantic/regeneration.py:129–142`, with defaults at `:245–248, 292–294`), and the name
  defaults at `semantic/statement_types.py:87–88` and `semantic/proposals.py:49–50`.

**DA-027 (stands, limit).** Enforcement claims are tagged records resolved against binding,
schema, implementation slice or captured native asset
(`semantic/data_operation_compilation.py:1903–1990`). By string count in the snapshot:

- 334 occurrences of `"kind": "documentation"` in 55 files;
- the checked interpretations appear a handful of times each (binding, schema and
  native-admission once each beyond the compiler's table, implementation twice).

This is a count of literals, not of resolved claims. It is consistent with the 11-17 note of
about 245 documentation claims and 3 checked claims.

**DA-028 (changed footprint).** The release archives the pack's `slices.yaml` as
`operation/slices.yaml` (`semantic/regeneration.py:110–118`). Nothing reads that archived name
(search for `operation/slices`).

The production source-demand path reads the working-tree copy instead:
`prepare_source_demand` loads the release, then selects document scopes from
`(domains or DOMAINS)/<domain>/slices.yaml` (`orchestrate/source_operation.py:159–176`). It is
reached from `orchestrate/native_execution.py:38`.

Domain resolution also matches the live pack's `semantic.yaml` `name` against the archived
module names, without comparing bytes (`source_operation.py:54–60`). A release with archived
slices X can therefore execute live slices Y, which is the original cause. The `queries.py`
and plugin part of the finding no longer applies (`bcff594c2`).

**DA-029 (holds, changed mechanism).** Physical classes carry `ph:immutability` annotations:
58 `immutable`, 52 `intrinsic`, 1 `deployment`, plus `pending` and `physical` (grep across
three physical model files). Refusal triggers for `intrinsic`, `immutable` and `deployment`
are generated from them (`semantic/target_installation.py:351–369`). The same function still
names `ops.pdf_shared_stream*` by hand (`:370–375`), which DA-074 records. Classes with no
annotation were not enumerated.

**DA-031 (holds, extended).** Forward authoring compares the model metadata through Alembic
`produce_migrations` (`semantic/native_authoring.py:21–24, 789`). A CHECK plugin compares
bound expressions (`semantic/alembic_checks.py:1–5`), and an index plugin covers collation,
WHERE, USING and INCLUDE (`semantic/alembic_indexes.py:1–12`). Admission adds native table and
reader catalog checks (`semantic/native_admission_tables.py:1–7, 90, 252`). This narrows the
11-03 limit on indexes.

**DA-032 (partly corrected).** Results record `native_kernel_digest`,
`validating_kernel_digest` and `kernel_digest`
(`model/semantic/data-operation-physical.yaml:22, 484, 632`), and forward bases are frozen
(`semantic/migration_chain.py:19–26`). There is still no per-result deployment attribution, and
whether one is needed remains open. The digest's breadth is DA-068.

**DA-038 (low-weight residue).** Nine serving modules import the private `_cursor` and
`_decode` from `semantic/demand_queries.py:43–54`, and `serve/demand_journey.py:3–10`
re-exports them in `__all__`. They form an unsigned base64 JSON cursor codec. This does not
recreate the original duplicated route. It is a shared primitive that is private only in name.

**DA-040 (partly corrected).** Establishment is checked against the `source_admissible` subset
at the agent schema (`semantic/proposals.py:111–114`; `semantic/types.py:344–346`).

Unbounded decimal expansion recurs in the regenerated native program. `decimal_canonical`
checks only the lexical pattern (`semantic/data_operation_value_native.py:124–127`), casts the
exponent to `bigint` (`:131–133`), then expands with `repeat('0', cast(…, integer))`
(`:112–113, 139–149`). The 10-29 inputs `1e400000000` and `1e2147483648` would still fail with
an allocation error or 22003 rather than 23514. That is inferred from source, not executed.

The Python mirror `decimal_text` expands with `format(value, "f")` without bound
(`semantic/value_codec.py:15–20`). A bound exists only in other modules
(`structural_parsing.py:194`; `formal_evidence.py:191`).

The NaN manifestation was not re-established. `boundary.py:189–191` puts
`Field(allow_inf_nan=False)` into the annotation when `finite_fields` applies, so
`rebuild_annotation` at `types.py:488–496` should keep it. That was not executed.

**DA-035/036/039 successors (light check).** Served rows carry an explicit `standing`
(`serve/contribution_facets.py:79, 296`; `serve/source_decision_journey.py:298`). Rich reads
have `limit` and `max_bytes` (`serve/rich_queries.py:130, 144`). Operation explanation is one
operation plus one bounded observation page (`semantic/operation_reporting.py:150–212`).
Whether absence is now statable for coverage was not traced.

## Counts by status (39 identities)

The table above was counted by hand.

| Status | Count | IDs |
|---|---|---|
| Corrected, holds | 14 | 005, 006, 007, 008, 010, 011, 018, 021, 022, 023, 029, 030, 031, 034 |
| Partly corrected | 6 | 003, 009, 013, 026, 032, 040 |
| Changed footprint | 4 | 001, 004, 020, 028 |
| Stands | 1 | 027 |
| Superseded | 2 | 002 (DA-072/085/086), 012 (DA-072/086) |
| No longer applicable | 12 | 014, 015, 016, 017, 019 (transferred), 024, 025, 035, 036, 037, 038, 039 |

Partial supersession is also present: DA-020's principal names go to DA-074, DA-032's
question to DA-068, and DA-034's successor issue is DA-077.

## Causes that recur in current code, with current sites

- **DA-001:** an inert predicate qualifier declaration. `semantic/comparison_projection.py:66–84`
  (no caller); `semantic/rich_rules.py:60`; grouping instead at `semantic/rich_scientific.py:205–217`;
  pack declaration at `domains/statistics/semantic.yaml:461–462`.
- **DA-003:** declared but unread subsets at `model/semantic/core.yaml:676–698`; `"primary"`
  literals at `semantic/rich_knowledge.py:209`, `semantic/rich_identity_exclusions.py:91` and
  `semantic/rich_proposal_lowering.py:41`.
- **DA-004:** raw `cs:` annotation decoding per consumer at `semantic/rich_scientific.py:210–211`,
  `semantic/rich_knowledge.py:238–361`, `semantic/rich_rule_evaluation.py:432, 867, 881`,
  `semantic/rich_queries.py:303` and `semantic/rich_graph_validation.py:602`.
- **DA-009:** two canonical-JSON implementations: native `data.canonical_json`, used at
  `semantic/runtime_binding_native.py:125` and `semantic/data_operation_value_native.py:76`,
  against `semantic/identity.py:13`. The Unicode check at
  `semantic/unicode_identity.py:233–246` has no caller.
- **DA-013:** prose refusals at scale, with 3,163 `raise ValueError(` in `semantic/`; current
  instance DA-079.
- **DA-020:** resource settings declared and unread at `settings.py:129–139`; literals at
  `semantic/rich_consolidation.py:405–412`.
- **DA-026:** binding inferred from raw YAML at `semantic/regeneration.py:129–142, 245–248, 292–294`.
- **DA-028:** live working-tree pack input on the release-bound source path at
  `orchestrate/source_operation.py:54–60, 159–176`.
- **DA-040:** unbounded decimal expansion at `semantic/data_operation_value_native.py:112–160`
  and `semantic/value_codec.py:15–20`.
- **Low weight:** DA-007's outcome literal written three times; DA-014's unused `LocatorIndex`
  branch (`semantic/proposals.py:21, 290, 325–329`); DA-038's private cursor codec in nine
  serving modules.

## Not resolved, and why

- **DA-019:** moved to the test account; that account was not read in this lane.
- **DA-037:** the subject was removed, but whether the replacement evaluation
  (`evaluate/record_alignment.py`, `graph_comparison.py`, `operation_fitting.py`) separates
  not-matched from not-comparable was not examined. `operation_fitting.py:103` does have an
  explicit `incomparable_endpoint_anchors` reason. The status is firm for the removed subject
  only.
- **DA-035:** whether coverage absence is now statable in the successor reads was not traced.
- **DA-002:** writer, reader and CHECK correspondence for value kinds was not re-traced.
- **DA-009:** canonical-JSON numeric parity was not re-probed (P4).
- **DA-014:** whether the frozen `semantic_alembic` chain that still holds
  `ops.source_locator_segment` is still deployed was not checked.
- **DA-040:** the NaN item was not established either way without execution.
- **DA-029:** classes with no immutability annotation were not enumerated.

Incidental: `c25cada3f`, whose subject is a documentation recommendation audit, also deleted
the last `semantic/sql/*.sql` files, including `closure.sql`. A citation of "removed by" for
those files should name that commit.

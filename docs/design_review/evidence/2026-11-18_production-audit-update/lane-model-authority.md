# Lane: model authority, re-read at `5139eaba3`

**Interface-checked by source inspection, 2026-11-18**, frozen snapshot `snap6/` of `5139eaba3`.
Nothing was run except read-only `git` and text searches. Paths are relative to
`snap6/python/corpus-structure/src/corpus_structure/` unless they start with `docs/` or
`domains/`. History: `git diff|log d78c98765..5139eaba3`.

**Read fully:** the eight findings and the fact-ownership and library tables on the audit pages;
`contextual_admission_native.py:1–320, 555–793`; `definition_admission_native.py:1–45, 340–436`;
`native_admission_tables.py`; `native_admission_principals.py:1–60`;
`data_operation_storage.py:1885–1990`; `target_installation.py:202–400`; the full diffs of the model
YAML, `data_completion_settlement_native.py`, `data_operation_storage.py` (first 150 lines),
`native_products.py`, `data_operation_preparation.py`, `characterization_ports.py`,
`data_operation_protocol.py` (task guard). **Sampled:** `rich_admission_native.py` (600–640,
805–910, 1130–1195), `operation_event_native.py` (20–70, 1195–1290), `structural_admission_native.py`
(780–830, 1240–1275), `record_policy_completion_native.py`, `record_grade_native.py`,
`data_product_admission_native.py` (40–100, 436–470), `native_admission_release.py`,
`native_admission_functions.py`, `native_admission.py:30–95`, `native_authoring.py:279–345`,
`closure_native.py:160–185`, `data_operation_projections.py` (diff hunks, 78–170),
`source_admission_native.py:1110–1135`. **Not read:** generator bodies for equivalence with the
SQL they replaced; `archive_native.py`, `pdf_spool_native.py`, `visual_read_native.py` beyond
greps; tests.

**Files bearing on these findings that did not change** in `d78c98765..5139eaba3` (by
`git diff --stat`): `data_operation_compiler_native.py`, `data_validity_native.py`,
`change_impact.py`, `support_trust_native.py`, `data_operation_compilation.py`,
`data_operation_model.py`, `schema/` (all), `core/` (except one field in `core/execution_policy.py`),
`primary_operations.py`, `canonical_sentences.py`, `hanlp_products.py`, `native_call_generation.py`,
`native_call_contracts.py`, `native_call_sources.py`, `pdf_search_native.py`, `prepare.py`
(3 lines), `native_inventory.py`, `pdf_lowering.py`, `typed_generation.py`,
`data_operation_value_native.py`'s tag tuple, `domains/statistics/operations.yaml` and both
statistics schemas. The model YAML changed in two places only: a `public_disclosure` boolean on
the read boundary (`model/semantic/data-operation-physical.yaml:629`) and three protocol
definitions (`public_demand_selection`, `read_demand_selection`, `authority_selection`;
`model/semantic/data-operation-native.yaml:469–493`). **No family, role, guard or grant fact was
added to any declaration.**

## 0. The central question: where membership facts come from now

"From the captured model" means, in every regenerated module, that the generator receives the
captured SQLAlchemy `MetaData` and resolves relation and column names against it
(`contextual_admission_native.py:87–93`, `self.model.tables[name]`, `.c[field]`; a missing
relation or column fails at generation). The generator signatures take only `MetaData`
(`operation_event_native.py:208`, `record_policy_completion_native.py:206`,
`data_product_admission_native.py:127`, `structural_admission_native.py:1677`,
`contextual_admission_native.py:175`, `definition_admission_native.py:47`,
`artifact_admission_native.py:29`, `rich_admission_native.py:1927`, `source_admission_native.py:1278`,
`native_admission_release.py:343`). None imports or receives the effective operation model or the
protocol (search for `EffectiveDataOperationModel|compile_data_operations|bound_data_operation_model`
in the nine modules: no hit). So statements are typed and relations are model-derived; every
membership fact below is (c) a hand list, except where marked.

| Membership fact | (a) declaration / (b) existing typed object / (c) hand list | Where now (snap6) |
|---|---|---|
| Relation and column used by a guard | **(b)** captured `MetaData` | every `p.table`, `p.row` |
| Family of an operation (classification) | **(c)** | `data_operation_compiler_native.py:470–519`, unchanged |
| Family to validator dispatch | **(c)**, fails open | `data_validity_native.py:272–288`, unchanged |
| Which guards completion calls | **(c)** | `data_completion_settlement_native.py:548–563`, unchanged |
| Guard self-selection, contextual | **(c)**, one 12-key dict used three times | `contextual_admission_native.py:188–201`; `:215, 568, 736` |
| Guard self-selection, definition | **(c)** `_OPERATIONS` + positional `_FACTORIES` | `definition_admission_native.py:33–44, 345–350, 358, 386, 418` |
| Guard self-selection, artifact | **(c)** literal, three times | `artifact_admission_native.py:112, 147, 217` |
| Guard self-selection, rich | **(c)** three lists: validator (4), preparation dict (3), preparation guard (3) | `rich_admission_native.py:816–823`, `:606–622`, `:903–910` |
| Guard self-selection, operation event | **(c)** `_OPERATIONS` (4); one id is **(b)** `AUTHORIZATION_OPERATION` from the operation's owner module | `operation_event_native.py:25–30, 55–61, 350, 1287, 1359` |
| Guard self-selection, record grade | **(b)** `GRADE_OPERATION` constant from `record_policy_authority.py:39` | `record_grade_native.py:55, 534, 702` |
| Guard self-selection, record fit | **(c)** literal | `record_policy_completion_native.py:1140, 1170, 1471` |
| Structural report producers (variant, operation, entry point) | **(c)**, but **one Python table shared** by the Python validator and the native generator | `declared_structural_admission.py:276–`, read at `:451` and `structural_admission_native.py:1245–1263` |
| Producer per input role (contextual) | **(c)** `role_operations` | `contextual_admission_native.py:301–310, 369` |
| Prepared-factory entry points | **(c)**, 53 lines in 15 files (51 in 14 at `d78c98765`; search for `corpus_structure.*.acquire_port` in `semantic/` and `evaluate/`) | e.g. `contextual_admission_native.py:189–200`; `definition_admission_native.py:39–44`; `record_policy_completion_native.py:60–61` |
| Profile, forms, CPU-receipt count per operation | **(c)** `case` over ids | `contextual_admission_native.py:234–259`; `definition_admission_native.py:358–372` |
| Encoder failure codes | **(c)**, restating a Python set | `contextual_admission_native.py:653–660` vs `contextual_encoder_batch.py:19–26` |
| Product member families and fields | **(c)** `_FAMILIES`, restating the protocol | `data_product_admission_native.py:56–90` vs `data-operation-native.yaml` `coordinate … choice`, `product_member` |
| Task states in the task guard | **(a)** protocol lifecycle, now a typed program | `data_operation_protocol.py:117–` |
| Task states in kernels | **(c)** literals (21 quoted `pending`/`running` in 8 `*native*.py`, same as before) | e.g. `data_claim_native.py` |
| Default read roles in admission | **(c)** JSON literal, restating `DEFAULT_READ_ROLES` | `native_admission_tables.py:176–184` |
| Default read roles in function admission | **(b)** imports `DEFAULT_READ_ROLES` | `native_admission_functions.py:6, 149` |
| Purpose to role map | **(c)** twice | `data_operation_storage.py:1899–1907`; `closure_native.py:174–181` |
| Execute grants, non-protocol functions | **(c)** | `data_operation_storage.py:1908–1928`; `target_installation.py:227–249, 291`; `native_admission_release.py:397–407`; `native_authoring.py:165, 183` |
| Frontier-guard relations | **(c)** 12 names, trigger now typed | `data_operation_storage.py:1952–1982` |
| Shared-stream triggers | **(c)** name set beside an unread declaration | `target_installation.py:371` |
| Immutability triggers | **(a)** `relation.info["immutability"]` | `target_installation.py:352–354` |
| Kind universes allowed in public reads | **(c)** new literal | `data_operation_projections.py:91–103` |
| Collection semantics of a composition input | **(a)** declared role `collection: set`, newly read | `characterization_ports.py:746–749` |

## 1. Findings

### DA-070 — validity families. Status: **stands, changed footprint** (the guard lists were transcribed; no list was removed)

- **Decisive evidence.** Classification is still the 27-id tuple with no `else`
  (`data_operation_compiler_native.py:470–529`); lowering still stores it
  (`:916–926`); dispatch still `else_=True` (`data_validity_native.py:281–288`); column still
  `validity_family: {range: string, required: false}` (`model/semantic/data-operation-physical.yaml:88`).
  All three files unchanged since `d78c98765`. The plan still defines null as "no per-kind validator
  applies" (`docs/plans/declared-data-operations/products-and-support.md:423, 452`).
- **Changing commits.** `fc6df4742` (contextual), `1556c7638` (definition, artifact), `d4d62e410`,
  `b834ddfdb`, `084f02980`, `c024010b8` (rich), `4760982d8`, `6d5f45920` (operation event). Each
  converted hand PL/pgSQL to typed programs. In every case the `NOT IN ('…')` text became
  `.not_in(tuple)` or `.is_distinct_from("…")` with the same ids; no guard selects itself any other way.
- **Lists now.** Counted by reading each guard: twelve membership-bearing lists or literal chains
  hold family membership (the twelve rows "classification" to "record fit" in §0, plus the
  completion guard tuple, the evaluator-authorization subset `data_completion_settlement_native.py:576–587`
  and the live chain `:744–803`). Inside contextual the duplication fell from two inline copies to
  one dict; rich went from one inline list to three separate lists (validator, preparation dict,
  preparation guard). **Agreement:** contextual 12 = 12 (scripted set comparison of the classifier
  segment against the `factories` keys); definition 4 = 4, rich 4 = 4, operation event 4 = 4 and
  artifact 1 = 1 by reading. The operation-event authorization subset (3) deliberately omits the
  score operation. No disagreement today.
- **Fail-open shape unchanged.** Every guard returns (`Return()`) and every validator returns
  `true` for an unlisted operation (`contextual_admission_native.py:215, 568, 736`;
  `definition_admission_native.py:386, 418`; `operation_event_native.py:1287, 1359`;
  `artifact_admission_native.py:147, 217`; `rich_admission_native.py:816–823, 903–910`).
- **Consequence now.** As recorded on 2026-11-18: an omitted member skips its family's
  completion checks and dependency premises. The ADR-0131 conversion step for these modules has now
  happened, and the audit's "note for the next conversion step" was realized as predicted: the
  lists were transcribed a second time rather than declared first.
- **Contrary evidence.** Two patterns exist that select by a declared attribute instead of by id:
  rich admission refuses any operation that declares the effect `native-rich-knowledge-admission`
  unless it is `rich.admit` (`rich_admission_native.py:1136–1145, 1186–1192`, transcribed from the
  old SQL), and structural/record-grade/operation-event guards take their operation constant from
  the operation's own owner module (b-class). Guards also compare the listed operation's
  admitted definition (entry point, profile, recipe, forms), so a listed id with drifted attributes
  is refused.
- **Uncertainty.** Whether a dispatch entry naming a missing `ddo_<owner>_dependencies_valid`
  fails at install or first call: not established (unchanged).

### DA-071 — support-graph meaning. Status: **stands**

- `data_validity_native.py`, `change_impact.py` and `support_trust_native.py` have no commit in the
  range; the disagreement (episode expansion, `source:` prefix at `change_impact.py:427`) is unchanged.
- `data_operation_projections.py` changed by four commits (`32ec30618`, `6d699ab46`, `110e8aa1e`,
  `ed410b80f`). `_support_walk` (`:171`) keeps its edge semantics and its own `_reference_node`
  (`:156`); the changes add a CTE name parameter, gate authority leaves behind the new
  `boundary.public_disclosure` (`:84–89`), and add disclosure checks by kind universe (`:91–103`).
  Callers rose from four to six (`:396, 466, 530, 1157, 1685, 2232`).
- **Count.** Three encodings, as before. A fourth, narrow traversal not counted before (it was hand
  SQL) is now a typed program: the episode lineage walk in source admission follows only
  `support_derivation_id` edges (`source_admission_native.py:1129–1135`; transcribed from
  `sql/data_operation_source_admission.sql:253–255` at `d78c98765`). It is purpose-specific; whether
  it must agree with validity is an owner question.
- **Consequence now.** Unchanged; public reads now see authority leaves only when the read boundary
  declares disclosure, which is a declared attribute (sound).

### DA-072 — earlier core and system model. Status: **stands unchanged**

No commit touched `model/core.yaml`, `system.yaml`, `revisions.yaml`, `schema/` or the statistics
schemas. Modules importing `core.vocab|core._model|core.keys` (regular expression over `*.py`;
this method gives 41, not the earlier 39): 41 at both commits, identical set (`diff` of the file
lists). `native_call_generation.py:106` still emits `from corpus_structure.core.vocab import TaskUnitType`.

### DA-073 — release composition by flags. Status: **stands, slightly wider**

`primary_operations.py`, `canonical_sentences.py`, `hanlp_products.py` and
`domains/statistics/operations.yaml` unchanged. Two owners changed: `data_operation_preparation.py`
now requires an `asset_custody` key in a native selection and verifies file custody (`:305–330`;
closed key set, fail-closed); `characterization_ports.py:1141–1155` adds
`enriched_document_products.py` to the captured-composition family's sources **by hand** (commit
`590b67b7a`/`1fab40234`). That is one more conditional site in the family source functions, and a
hand statement of "which code determines this family" (shared with DA-068). The same commit reads
the declared role collection (`:746–749`), which is a sound derivation.

### DA-074 — roles, grants, guard membership. Status: **stands, changed footprint** (role literals moved from SQL into more Python modules; one splice by role text removed)

- **Roles.** No role entered the model; `ph:read_roles` is `'[]'` on all 84 annotations (search
  of `model/`, unchanged). Lines containing a `corpus_sem_*` name: in `*.py` 142 lines in 39 files at
  `d78c98765`, 166 lines in 47 files now; over all package files 171 lines in 46 files then, 166 in 47
  now (`git grep -c`; lines, not occurrences, so not comparable with the earlier 176). The seven SQL
  files that held role names are gone; their literals reappear in `closure_native.py`,
  `native_admission_principals.py`, `native_admission_tables.py`, `native_admission_release.py`,
  `source_record_recognition_native.py:224`, `pdf_descriptor_native.py:125`,
  `original_document_native.py:123`, `demand_result_native.py:209`.
- **`native_admission_tables.py` (new, `920f1b746`).** Holds the four actor roles as a tuple
  (`:27–32`) and the default read roles as a JSON string literal (`:176–184`), commented "the
  preexisting archive contract, including its array order". That literal equals
  `DEFAULT_READ_ROLES` in content and order (`alembic_privileges.py:25–30`), so it is derivable; it is
  not derived. Its sibling `native_admission_functions.py:6, 149` does import the constant.
- **`native_admission_principals.py` (new, `08284dc6f`).** Source and runtime principal tuples,
  application schemas `("sem","data","ops","kb")` and four private kernel signatures as text
  (`:8–16`), plus `corpus_sem_evaluator`, `corpus_sem_publisher`, `corpus_sem_admitter` inline
  (`:30, 140, 208, 221`).
- **Purpose to role.** Now written twice: the grant loop (`data_operation_storage.py:1899–1907`,
  five purposes) and `data.require_runtime_principal` (`closure_native.py:174–181`, four purposes,
  refuses an unknown purpose), the latter transcribed from `sql/closure.sql`.
- **Execute grants.** The name chain (`data_operation_storage.py:1908–1928`), the install table
  (`target_installation.py:227–249`, 11 rows, unchanged count), runtime-binding grant (`:291`),
  admission guard grants (`native_admission_release.py:397–407`), default writer grant in
  `_task_call_definition(s)` (`native_authoring.py:165, 183`).
- **Corrected sub-item.** The splice of generated comparisons at the literal text of a role check
  (`native_admission.py:412–416` at `d78c98765`) is gone: `sql/admission.sql` was retired by
  `9364a5b88` and the privilege checks are typed and iterate `PURPOSE_ROLES`
  (`alembic_privileges.py`, `privilege_admission_checks`).
- **Frontier guard.** Still the 12-name tuple; the trigger is now built by
  `native_before_trigger_sql` (`data_operation_storage.py:1952–1982`, `4760982d8`), so the string
  concatenation is corrected and the membership is not.
- **Shared-stream triggers.** Still by name (`target_installation.py:371`), now typed trigger
  construction; `ph:immutability: pending-content` still declared for exactly these two relations
  (5 immutability classes counted in `physical.yaml`: 46 immutable, 18 intrinsic, 3 physical,
  2 pending-content, 1 deployment) and still unread.
- **Contrary evidence.** Immutability triggers read the declared class (`target_installation.py:352–354`);
  protocol-function grants derive from purposes; privilege admission compares the complete ACL.

### DA-081 — program and facade registries. Status: **stands, wider** (new modules joined by hand; one text transform corrected, one marker-based recovery added)

- Facade tuple in `schema/model_change.py`: file unchanged, still seven entries.
- `native_protocol_sources`: 91 literal artifact names (90 before); required set in `_captured`
  (`data_operation_storage.py:581–692`): 94 (93 before). Both gained `native/contextual-neighborhood.py`
  by hand (`:505, 608`). `native_sql` still joins 39 named artifacts; the six artifacts it joins
  that the required set lacks are the same six (scripted extraction at both commits; the
  `demand-*` stems are required through a separate stem list at `:586–592`).
- Capture module list in `capture_native_authoring_inputs` (`native_products.py:134–160`): 18 → 28
  names, ten added by hand (companion projection ×2, `published_document.py`, `projection_recipe.py`,
  `archive_native.py`, `archive_transport.py`, `pdf_spool_native.py`, the three
  `native_admission_*` modules).
- Install table 11 rows, provider list 7: unchanged counts.
- **Corrected sub-item.** Authoring scratch tables are now retargeted on the parse tree
  (`ast.RangeVar` replacement, `native_authoring.py:305–327`, `759dd837f`) instead of by string
  replacement.
- **New mechanism.** The program compiler gained a `Comment` statement (`native_program.py:177`)
  used to emit catalog-check boundary markers (`native_admission_release.py:35–38, 371, 382`), and
  `catalog_checks` recovers the text between markers, with literal SQL fallbacks for older frozen
  guards (`native_admission.py:42–82`). Contrary: its docstring states the purpose is replay of
  authenticated frozen guard bytes, which needs text.

### DA-085 — per-consumer LinkML composition. Status: **stands unchanged**

`SchemaView(` construction sites are identical at both commits (16 sites, `git grep`); the model YAML
changes add no annotation encoding. Strengthening evidence: the regenerated generators see only the
compiled `MetaData`, never the effective operation model or the protocol (§0), so even the facts the
effective model holds per operation (entry point, profile, forms, effects) could not be read by them.

### DA-086 — literals for declared facts. Status: **stands, partly corrected for task states, wider in count**

- **Corrected:** the task guard is now a typed program built from the protocol lifecycle and the
  captured `ops.task` columns (`data_operation_protocol.py:117–`, replacing the template plus
  `sql/data_operation_task_checks.sql`). Kernels still test state literals (21 quoted
  `pending`/`running` in 8 `*native*.py` files at both commits).
- **Unchanged:** value-codec tag tuple, field-kind maps, `_PROFILES`/`_KIND_UNIVERSES`, Arrow
  schemas (files unchanged).
- **Transcribed into Python, so now visible to search:** kind-universe literals in `semantic/*.py`
  33 → 43 lines (pattern `universe.{0,40}"ordinary|evaluator|source|protected"`); the new lines are
  rich (3) and structural (6), formerly SQL text, and one new rule in `data_operation_projections.py:97`.
  Codec tags (`"mapping"`, `"string"`, `["integer","1"]`, `["null"]`) and operation role names
  appear in every regenerated module (survey per module: 0–13 tag literals, 0–12 role comparisons).
  JSON paths into `support_contract` (`["capabilities"]["prepared_factory"]["entrypoint"]`) are free
  strings; the typed read boundary types that column as `dict[str, Any]`
  (`native_definition_projection.py:31–42`), while `EffectiveOperation.capabilities` is a typed
  dataclass.
- **Newly identified (not new code):** product member families (`data_product_admission_native.py:56–90`)
  restate field names and required/optional sets the protocol declares; encoder failure codes
  restate `contextual_encoder_batch.py:19–26`; record-policy factories are written in
  `record_policy_completion_native.py:60–61` beside `GRADE_FACTORY` in `record_policy_authority.py:40`.

## 2. Openness: what closed, what stayed open

**Closed (fail-closed lists or refusals), with origin:**

| Site | Closed set | New or transcribed |
|---|---|---|
| `data_operation_projections.py:91–103` | public reads disclose only kinds of universe `ordinary` or `source` | **new** (`6d699ab46`, `ed410b80f`) |
| `data_operation_preparation.py:305–330` | native selection must have exactly `profile, fingerprint, assets, asset_custody`; file population must equal declared | **new** (`188ec73c2`) |
| `contextual_admission_native.py:301–310, 369` | input role `query` may come only from two operation ids, etc. | transcribed (old SQL line 81) |
| `contextual_admission_native.py:234–259` | profile, forms and receipt count fixed per id | transcribed |
| `contextual_admission_native.py:653–660` | four encoder failure codes | transcribed |
| `rich_admission_native.py:623–634` | rich preparation requires one of three named owners, else raise | transcribed |
| `closure_native.py:174–186` | unknown runtime purpose raises | transcribed |
| `data_product_admission_native.py:443–452` | endpoint scope `local`/`external` else raise | transcribed |
| `operation_event_native.py:488` | partition `development`/`feature_fit` | transcribed (not traced) |

The transcribed closures are where the model expresses variability that the kernel narrows: the
scoring operation declares its `query` input by kind and declares dependencies only on
`retrieve.contextual_vectors/selection` (`methods/contextual_scoring.py:99–130`), while the kernel
admits a query only from two listed producers. A third query encoder would be refused at
completion although the declared roles admit it. This is an inference from the two texts; no run.

**Open, optional or provisional states kept or added:**

| Site | State | Character |
|---|---|---|
| `validity_family` null; dispatch `else_=True`; guards `Return()` | "no validator applies" indistinguishable from "omitted" | kept, implicit (the fail-open of DA-070) |
| `data-operation-native.yaml:469–493` | `read_demand_selection` is `oneOf` intent or public selection; `authority_selection.protected_dependencies: undisclosed` | **added, declared** |
| `data-operation-physical.yaml:629` | `public_disclosure` boolean, required, default false | **added, declared**, read by projections |
| `data_operation_bindings.py` (`1d3640990`) | independent optional binding roles admit the anchor's empty row | kept, declared `optional` operator |
| `characterization_ports.py:746–749`, `methods/characterization.py` (`b0ae4d21a`) | composition inputs declared `collection: set` and ordered canonically | **added, declared** |
| `definition_admission_native.py:345–350` | unlisted id falls to the last factory by `else_` | implicit; masked because the guard refuses unlisted ids first |

So the recent explicit openness is declared in the model (protocol variants, a boolean, role
collection), while the kernel's openness is implicit and its closures are id lists. That split is
the pattern the operator asked to see.

## 3. Fact-ownership table (replaces the published one)

Mark: **N** new row, **C** changed since `d78c98765`, **U** unchanged.

| Fact | Declared in the model | Held as code (path:line) | Restated at | Derivable from today | Mark |
|---|---|---|---|---|---|
| Record and product shape | LinkML classes | — | Earlier-model copies (DA-072); DuckDB Arrow schemas `analytical_kernels.py:21–60`, `rich_relations.py:24–34` | Rich/view relations: none. PDF: `MetaData` | U |
| Relation and column used by native programs | Physical LinkML → `MetaData` | — | — | Already derived; generators resolve against captured `MetaData` | C (now all nine admission modules) |
| Field type and constraint | LinkML range, `ph:checks` JSON | — | `data_kind_contract` universe check (`data-operation-physical.yaml:71`) beside `_KIND_UNIVERSES` (`data_operation_compilation.py:341`) | `NativeKindProjection["universe"]` Literal (`native_definition_projection.py:23`) | U |
| Kind universe values in kernels | Physical check `:71` | — | 43 lines in `semantic/*.py` (survey), incl. new public-disclosure rule `data_operation_projections.py:97` | The typed Literal, as `support_trust_native.py:91` already does | C |
| Field kind to database/Python type | LinkML `uri`, `ph:sql_type` | — | `native_call_contracts.py:16–25`; `native_call_sources.py:28–37`; `pdf_search_native.py:98–104`; `native_program.py:657` | `schema/relational.py:79–89, 437–440` | U |
| Enum and value set | LinkML enums; protocol enums | — | Six enums in both cores; PDF outcome pair | One side from the other | U |
| Operation | — (ADR-0092 two routes) | `__data_operation__` in about 62 modules | — | None; admitted medium | U |
| Operation inputs, outputs, dependencies | — | Literal `roles`, `dependencies` | `change_impact.py:157–193`; producer-per-role `contextual_admission_native.py:301–310`; `STRUCTURAL_REPORT_PRODUCERS` `declared_structural_admission.py:276–` | Compiled `selected-dependencies`, `potential-producers` (`data_operation_model.py:713–725`); role kinds | C (kernel restatements located) |
| Role collection semantics | Operation role `collection` | — | — | Read directly (`characterization_ports.py:746–749`) | N (sound) |
| Validity family | Column only, no values (`data-operation-physical.yaml:88`) | `data_operation_compiler_native.py:470–519` | Dispatch `data_validity_native.py:272–280`; guard tuple `data_completion_settlement_native.py:548–563`; authorization subset `:576–587`; live chain `:744–803`; contextual `:188–201`; definition `:33–38`; artifact `:112, 147, 217`; rich `:606–622, 816–823, 903–910`; operation event `:55–61`; record grade `record_grade_native.py:55–57`; record fit `record_policy_completion_native.py:1140, 1170, 1471` | None; needs a declaration. Hosts: lowering beside the effective operation (`data_operation_compiler_native.py:905–926`); declared effects already select in rich (`rich_admission_native.py:1136–1145`) | C |
| Prepared-factory entry point | Per operation in the effective model (`capabilities.prepared_factory.entrypoint`) | — | 53 lines in 15 files, e.g. `contextual_admission_native.py:189–200`, `definition_admission_native.py:39–44`, `rich_admission_native.py:607–619`, `record_policy_completion_native.py:60–61`, `declared_operation_events.py:42–44`, `declared_structural_admission.py:276–` | `EffectiveOperation.capabilities` (`data_operation_model.py:288–296`). Caution: guards compare against the admitted row, acting as an independent pin | C (was contextual only) |
| Profile, forms, receipt count per operation | Effective model | — | `contextual_admission_native.py:234–259`; `definition_admission_native.py:358–372`; `artifact_admission_native.py` | `EffectiveOperation.profile`, `.capabilities.forms` (same caution) | C |
| Operation constants in owner modules | — | `AUTHORIZATION_OPERATION` (`evaluate/declared_operation_events.py:31`); `GRADE_OPERATION` (`record_policy_authority.py:39`); `ADMISSION_OPERATION` (`declared_structural_admission.py:11`) | `"operation_event.frame"` etc. inline (`operation_event_native.py:295, 315, 1206`); `"record_policy.fit"` inline | The owner constants | N |
| Encoder failure codes | — | `contextual_encoder_batch.py:19–26`; `Literal` (`methods/contextual_embeddings.py:333`, two codes) | `contextual_admission_native.py:653–660` | The Python set | N |
| Product member families, fields, required sets | Protocol `coordinate`, `role_member`, `endpoint`, `coverage`, `choice`, `product_member` (`data-operation-native.yaml:630–760`) | `_FAMILIES` (`data_product_admission_native.py:56–90`) | — | The protocol definitions' `properties`/`required` | N |
| Support-edge meaning; reference-to-node map | — | `data_validity_native.py:88–240` | `_support_walk` (`data_operation_projections.py:156, 171`); `_revocation_causes` (`change_impact.py:332–441`); narrow lineage walk `source_admission_native.py:1129–1135` | None; needs a declaration | C (fourth walk located) |
| Trust-scope key | — | `support_trust_native.py:100–118` | `change_impact.py:427` (disagrees) | The program, or one shared function | U |
| Public disclosure of a read | `public_disclosure` (`data-operation-physical.yaml:629`); protocol `read_demand_selection` | — | — | Already read (`data_operation_projections.py:84–89`) | N (sound) |
| Frontier-guard membership | — | 12 names (`data_operation_storage.py:1952–1965`) | Admission descriptor from the same list | None; needs a declaration | C (trigger typed) |
| Shared-stream trigger membership | `ph:immutability: pending-content` (`physical.yaml`, two relations) | Name set (`target_installation.py:371`) | — | `relation.info["immutability"]` | U |
| Immutability and archive triggers | `ph:immutability`, `ph:archive_role` | — | — | Already derived (sound) | U |
| Task states and transitions | Protocol lifecycle (`data-operation-native.yaml:5–14`) | Kernel literals (21 in 8 `*native*.py`) | — | Already read by the typed task guard (`data_operation_protocol.py:117–`) | C (guard corrected) |
| Role names | — | `alembic_privileges.py:25–33` | 166 lines in 47 `.py` files; new tuples `native_admission_tables.py:27–32`, `native_admission_principals.py:8–9` | Constants exist; none in the model | C |
| Purpose to role map | Purposes per protocol function | `data_operation_storage.py:1899–1907` | `closure_native.py:174–181` | Purposes: yes; roles: needs a declaration | C (second copy) |
| Execute grants, non-protocol functions | — | `data_operation_storage.py:1908–1928` | `target_installation.py:227–249, 291`; `native_admission_release.py:397–407`; `native_authoring.py:165, 183` | None | C |
| Table read grants | `ph:read_roles` (84 × `'[]'`) | Default `alembic_privileges.py:74–75` | JSON literal `native_admission_tables.py:176–184` | `DEFAULT_READ_ROLES` (identical order), as `native_admission_functions.py:149` does | C |
| Principal restrictions; application schemas; private kernels | — | `native_admission_principals.py:8–16` | — | Schemas: `MetaData` table schemas (plus `eval`); kernels: the program objects if they existed (DA-081) | N |
| Release composition | Flags (`domains/statistics/operations.yaml`) | `primary_operations.py:118–392` | Family source functions; new hand source `characterization_ports.py:1141–1155` | Partly (`python_operation_sources.py`) | C |
| Physical index and check | `ph:indexes`, `ph:checks` | — | — | Derived; admission compares (sound) | U |
| Wire shape | Protocol draft-7 | — | Wire-type map | Derived | U |
| Value-codec vocabulary | SourceValue variants in LinkML | `data_operation_value_native.py:44–50` | — | Two codecs, two authorities | U |
| Codec tags in kernels | Same codec | — | Tag literals in every regenerated module (survey) | `data_operation_value_native.py` constants | N |
| Search configuration | `ph:search_configuration` | — | — | Derived | U |
| Identity determinants | Operation literals | `_compile_identities` | — | Compiled (sound) | U |
| Scientific policy parameters | `scientific-policies.yaml` | — | Archived recipe text | Not examined | U |
| Code that determines an artifact | Implementation slices for Python operations | Capture list `native_products.py:134–160` (28); `LOWERING_FILES` | Each other in part | None for generators | C (+10 names) |
| Generated-facade and program-set ownership | — | `_NATIVE_OUTPUTS` (7); sources 91; required 94; `native_sql` 39; install table 11; providers 7 | Owner writers; `LOWERING_FILES` | Owners' path constants; no released-model registry | C |
| Catalog-check boundaries in the admission guard | — | Marker comments `native_admission_release.py:35–38, 371, 382` | Text recovery `native_admission.py:42–82` | The program objects, for current guards | N |
| Graph-projection catalog | — | `compiled_graph_projections` | — | Derived (sound) | U |

## 4. Data-model libraries and their roles (replaces the published table)

Versions unchanged in the range (`pyproject.toml` and `uv.lock` have no diff).

| Library | Source of truth for | Holds as derived (from what, where) | Same fact held independently | Mark |
|---|---|---|---|---|
| LinkML, linkml-runtime | Classes, enums, physical tables (`ph:`), projections, packs | — | Enums in both cores (DA-072); operation shapes in Python | U |
| SQLAlchemy `MetaData` | Nothing primary | Tables, columns, checks, indexes, `info` (`schema/relational.py:385–563`); the only model input of every regenerated generator | Role, guard and family membership beside it (DA-070, DA-074) | C |
| SQLAlchemy Core | Statement construction | All admission kernels, the task guard (`data_operation_protocol.py:117–`), triggers (`native_before_trigger_sql`), catalog checks over lightweight `pg_catalog` tables (`native_catalog.py`, `native_admission_tables.py`, `native_admission_principals.py`, `native_admission_functions.py`) | — | C (wider) |
| Alembic | Migration graph; privilege operations | Autogenerate; privilege policy from `info["read_roles"]` plus `DEFAULT_READ_ROLES`; typed privilege admission over `PURPOSE_ROLES` | Default roles again as JSON text (`native_admission_tables.py:176–184`) | C |
| pglast | — | Parses every native statement; parse-tree retargeting of scratch tables (`native_authoring.py:305–327`); kernel re-parse for grants (`data_operation_storage.py:1887–1897`); 62 `semantic/` modules use it (59 before) | — | C |
| SQLGlot | — | Projection lineage and type analysis | — | U |
| jsonschema | Protocol validation | Wire validation; nullable inference; kind schemas now pass `checked_json_schema` (`data_operation_storage.py:1146–1150`) | Protocol member families restated in `_FAMILIES` | C |
| pydantic | Earlier-model shapes; `BaseModel`s; `TypedDict` read boundary (`native_definition_projection.py`) | `TypeAdapter` for native selection custody (`data_operation_preparation.py:304`) and PDF records | `support_contract` typed `dict[str, Any]` beside the typed `EffectiveOperation.capabilities` | C |
| pydantic-settings | Deployment settings | — | Analytics fields unread (DA-080) | U |
| Frozen dataclasses with cattrs | Effective operation model | cattrs decodes the archive | Facts it holds per operation restated in kernels (entry points, profile, forms) | C |
| pyarrow | DuckDB relation schemas (hand-written) | PDF record and export schemas from `MetaData` | — | U |
| DuckDB | Nothing | — | Hand-written input shapes in three modules | U |
| valuesets; linkml-term-validator, oaklib, pronto; attrs, msgspec | As published | As published | — | U |

## 5. Structural cause and sound designs

**No new structural cause; one sharpened.** The kernel generators take the captured `MetaData` as
their only model input (§0). Relations and columns are therefore model-owned and refuse at
generation; everything that identifies *which operation* (family, producer, entry point, profile,
role, universe) is a free string. This is the mechanism behind DA-070, DA-074 and DA-086 inside the
kernel, and a sharper statement of DA-085's "not one object". It is also why the recent
conversion could change every statement's form without changing a single fact's source.

There is a design reason the generators should not simply read the operation model: one native
kernel serves many releases, and operations are lowered per release into
`sem.data_operation_definition` rows that the guards already look up. Reading the model at
generation time would put every operation edit into the kernel digest (DA-068), which the id lists
already do today. The existing alternative is selection by a lowered, declared attribute at run
time, as rich admission already does with a declared effect, and as `validity_family` was meant to
do. Lead only.

**Sound designs to preserve.**

- Typed resolution of every relation and column against captured `MetaData` in all regenerated
  modules; a missing name fails at generation.
- The typed task guard derived from the protocol lifecycle and the `ops.task` columns.
- Selection by declared effect (`rich_admission_native.py:1136–1145`) and owner-module operation
  constants (`GRADE_OPERATION`, `AUTHORIZATION_OPERATION`, `ADMISSION_OPERATION`).
- One shared Python table consumed by both the Python validator and the native generator
  (`STRUCTURAL_REPORT_PRODUCERS`), which removes one copy where two existed.
- Declared variability: protocol `oneOf` read selections, `authority_selection` with an explicit
  `undisclosed` state, the `public_disclosure` column, `collection: set` read from the role.
- Immutability triggers from `ph:immutability`; privilege admission over `PURPOSE_ROLES` with full
  ACL comparison; `native_admission_functions.py` importing `DEFAULT_READ_ROLES`.
- Parse-tree retargeting instead of string replacement for scratch relations.

**Uncertainty.** Counts are search counts with the stated patterns. The claim that a third query
encoder would be refused is inferred from source, not run. Whether the narrow lineage walk must
agree with validity, and whether any listed closure (partition values, failure codes) has a model
owner, are owner questions.

# Challenge of the drafted audit update at `5139eaba3` (focused advice)

Independent read of `audit_drafts/` against the frozen snapshot `snap6` (source `5139eaba3`)
and, for the baseline, a read-only `git archive d78c98765` export I made in
`prod2/chal/d78/`. My own scripts are in `prod2/chal/tools/` (`sqlcount.py`, `capmods.py`);
outputs `chal/new.txt`, `chal/old.txt`, `chal/capnew.txt`, `chal/capold.txt`. I formed each
view from source first and opened the lane reports afterwards, only to check whether they
already held a point. No tests, databases or providers were run. Paths are relative to
`snap6/python/corpus-structure/` unless they start with `docs/`.

## 1. Synthesis claims

**(a) SQL text, about 2,400 to about 180. Holds with correction.**
- *My method* (different from the drafter's): every Python string constant and the literal
  parts of every f-string, docstrings excluded, that matches a **case-insensitive**
  statement-shape regex (`select … from`, `insert into`, `update … set`, `create [or replace]
  function|table|trigger|…`, `grant|revoke …`, `do $`, `language plpgsql`, `raise exception`,
  `on conflict`, `pragma`, and others). Size is the lines the node spans. Result: **2,431 lines
  in 38 files** at `d78c98765` and **182 lines in 17 files** at `5139eaba3`. That agrees with
  the draft's 2,423 and 183.
- *What the figure leaves out.* It counts SQL inside Python modules only. At `d78c98765` there
  were also **16 `.sql` files under `src/` (1,293 lines)**, ten of them loaded (the committed
  DA-084 gives 1,008 lines for those ten). At `5139eaba3` there are **none**: `find src -name
  '*.sql'` is empty and `semantic/sql/` does not exist. So hand-written SQL in maintained
  production source fell from about 3,700 lines to about 180. The synthesis sentence should say
  which population it counts.
- *The fourteen modules DA-084 named* (the eleven `*_native.py` modules plus
  `pdf_publication_native.py`, `data_operation_cpu_basis.py` and `execution_evidence_leaf.py`)
  have no entry in my count at `5139eaba3`. **Holds: 0 lines**, down from 2,100 by my method.
- *73 of 78 `*_native.py` modules import the compiler.* **Holds** (my grep: 73 import
  `native_program`; the five that do not are `pm2_native`, `data_operation_wire_native`,
  `data_operation_source_native`, `data_operation_binding_native` and `alembic_native`).
- *The "two real items".* **The first holds; withdraw the second as a conversion residue.**
  `target_database_privileges_sql` (`src/corpus_structure/semantic/target_installation.py:623–637`)
  is hand-concatenated PL/pgSQL, and the plan names it. The second is not like it.
  `evaluate/operation_fitting.py:530–620` (`read_native_frame`, `fit_native_operation_event`,
  `read_native_fit`) has **no caller in `src`, `tests` or `scripts`**. The functions it calls,
  `eval.operation_event_fit_frame`, `eval.record_operation_event_fit`,
  `eval.read_operation_event_fit` and `ops.read_operation_event_parameters`, are defined only
  in `semantic_alembic/versions/*`. They appear nowhere in `target_alembic/`, which is the
  deployed tree (`src/corpus_structure/semantic/migrations.py:14`); N29's desired state has
  objects in the `ops`, `sem`, `kb` and `data` schemas and none in `eval`. So this is
  superseded machinery that calls functions the deployed target no longer defines. Its home is
  DA-080. It is also captured: `evaluate/operation_fitting.py` is in `_PATHS` of
  `evaluate/declared_operation_events.py:46–57`, so the dead code sits inside a hand-listed
  implementation boundary. Its `text(` calls are the same shape as the control calls the draft
  already accepts (`semantic/execution_admission.py:193`, `semantic/data_operation_storage.py:1135`).

**(b) Membership facts are hand lists and the model gained no family or role declaration.
Holds, with two additions to the contrary evidence.**
- I searched the LinkML tree (`src/corpus_structure/model/**`) for a family, role or purpose
  enum or annotation, and Python for a typed registry. `validity_family` is
  `{range: string, required: false}` with no value set (`model/semantic/data-operation-physical.yaml:88`).
  The only `ph:` grant fact is `ph:read_roles`: 84 annotations, every one `'[]'`. Role names
  are constants (`semantic/alembic_privileges.py:25–33`), not model facts. Per-function
  `purposes` are declared in the protocol (`model/semantic/data-operation-native.yaml:2809–`),
  but that block is not new and holds no family. The classifier receives `model` and does not
  use it (`semantic/data_operation_compiler_native.py:467–529`). Method declarations name no
  family: for example `methods/contextual_scoring.py:130–131` has `"effects": []`.
- *Missed contrary evidence.* A second declared-effect selection exists besides rich admission.
  Policy authorization refuses any operation that is not classified `command_class ==
  'policy'` but is `record_policy.authorize` or declares the effect
  `native-evaluator-policy-authorization`
  (`semantic/record_policy_completion_native.py:425–441`). `command_class` itself comes from
  eligibility predicates, not ids (`data_operation_compiler_native.py:530–550`). In addition,
  record policy, operation events, rich and structural admission each already declare a native
  effect name per operation (`methods/record_policy.py:70`, `methods/operation_events.py:328`,
  `methods/rich_knowledge.py:405`, `methods/structural_admission.py:132`). For those four
  families the lead "selection by a lowered, declared attribute" therefore has a declaration
  already in place. Contextual, definition and artifact operations declare none.

**(c) An unlisted operation is treated as valid. Holds at the sites cited; one wording fix.**
I read the classifier `CASE` with no `ELSE` (`:519–529`), the dispatch `else_=True`
(`semantic/data_validity_native.py:272–288`), the lowering that stores the classification
with no refusal on null (`data_operation_compiler_native.py:916–960`), and the contextual and
definition guards (`semantic/contextual_admission_native.py:215, 568, 736`;
`semantic/definition_admission_native.py:386, 418`). I found no upstream check that refuses an
operation whose family is null or makes these returns unreachable. The completion loop calls
every guard by name, and each selects itself (`semantic/data_completion_settlement_native.py:548–592`).
- *Wording.* "A family member that the model or a method module declares and that is missing
  from a guard's list" presupposes a declaration that does not exist; nothing outside the lists
  records membership. Say instead: "an operation meant to belong to a family but absent from
  its lists, an intent that nothing else records".
- *Precision.* `ddo_require_definition_producer` refuses an unlisted operation
  (`definition_admission_native.py:358`), but it is reached only after the completion guard's
  early return at `:386`, so the draft's conclusion stands.

**(d) 99 modules; N29 existed only to restamp the digest. The count holds; the N29 claim is
overstated.**
- *Count, by my own static method.* An AST walk of `native_protocol_sources` and of nine helper
  functions (`binding_native_sources`, `source_native_sources`, `wire_native_sources`,
  `operation_event_native_sources`, `source_value_native_sources`,
  `capture_projection_sources`, `search_projection_sources`, `visual_read_sources` and
  `source_admission_sources`) collects `"*.py"` literals and `Path(__file__).read_bytes()`
  reads. That gives 94 names, less one false positive (the artifact name `native/identifiers.py`),
  so **93**. Adding the six Python files of `_RENDERER_FILES`
  (`semantic/pdf_source_search.py:29–37`), none of which overlap, gives **99**. The same method
  gives **95** at `d78c98765`. The four additions match the draft. **Holds.**
- *N29.* I compared `target_alembic/versions/semantic_ddo_pe_n28_native.json` with `…n29…`
  object by object: 585 desired objects each, the same identities, nine changed, and the
  privileges are equal. **Every substitution maps one to one**, so the masking caveat can be
  dropped for this pair:
  - a single kernel-digest pair (`1f80f692…` to `ec36f60d…`) in seven functions (the
    descriptor, read presence, read result, publication, seal, episode correspondence and
    retain intent);
  - one renderer-pin pair in `ddo_pdf_search_pin`;
  - 17 changed digests inside `data.execution_contract_descriptor`. Eight of these are the
    body hashes of the eight changed functions. The others are the **`authoring/*` source
    digests**: N28 to N29 changes `authoring/native_admission.py`,
    `authoring/native_authoring.py`, `authoring/native_catalog.py` and
    `authoring/native-fixed-calls.json`, out of 48 authoring entries.

  The source commits between the N28 freeze (`cee496852`) and the N29 freeze (`d2ffba42e`)
  are `1b643e7ed` (typed catalog verification, which touched those authoring modules and
  `execution_admission.py`), `477c82762` (`native_source_view.py`, a renderer input, hence the
  kernel and pin move) and `8aec2ba7b` (formatting of an uncaptured file). The plan describes
  N29 as sharing "typed catalog verification framing between rollback-only authoring and
  deployed checks" (`docs/plans/declared-data-operations/postgresql-realization-and-retirement.md:459–461`).
  **Corrected reading:** N29 changed no generated statement. It existed to restamp provenance:
  the kernel digest after a renderer edit, and the authoring-source digests after an authoring
  edit whose generated output was byte-identical. That byte-identity is itself sound evidence
  that the catalog-verification conversion preserved behavior. The authoring-source list
  (`semantic/native_products.py:54–170`, recorded in the execution-contract descriptor) is a
  second provenance digest stamped into a deployed object. DA-068 and the identity inventory
  should name it (row 22 or a new row).

**(e) The per-acquisition check rebuilds the capture and ignores the prepared release.
Holds.** `require_data_operation_native` calls `native_source_digest()` with no argument twice
(`semantic/data_operation_storage.py:1139, 1142`); each call runs `native_protocol_sources()`
(`:712–722`, `:48–575`). `prepared` is used only for `require_native_execution` (`:1133`).
`native_digest_from_dependencies` (`:1080–1081`) exists and is not used here. Definition
admission adds a third build (`:1571`). The module has no memoisation.

## 2. Statuses of DA-068 to DA-086 that claim a correction

- **DA-086, "Partly corrected (task guard)". Withdraw the correction.** At `d78c98765` the guard
  was already rendered from the declared lifecycle: `render_data_task_guard` called
  `data_task_lifecycle(content)` and substituted `__DDO_TASK_*__` tokens
  (`chal/d78/…/semantic/data_operation_protocol.py:117–157`). The committed DA-086 already cited
  it as the sound counter-example: "the task guard trigger is rendered from it"
  (`docs/design_review/audit/semantic-model-and-authority.md`, DA-086 "Task states"). What
  `32ec30618` changed was template to typed program, so `ops.task` and `ops.data_request`
  columns now resolve against captured metadata. That is a DA-084 correction, not a DA-086 one.
  DA-086's status is **Stands (wider)**. My recount confirms its 21 quoted `pending`/`running`
  in eight `*native*.py` files at both commits.
- **DA-084, "Partly corrected". Holds**, with the item (a) corrections: one real item, not two,
  and the `.sql` population stated.
- **DA-080, "Partly corrected". Holds, with two corrections.** (1) `methods/llm/producer.py` *is*
  imported, by `tests/ingest/test_managed_recognition.py:11` (`producer_binding`, asserted at
  `:25, 40, 99`). It is kept alive only by a test, which is exactly DA-080's title; only
  `agent_opus.py` has no importer. (2) Add the dead native fitting path of item (a). I confirmed
  the preview explanation (`schema/model_explanation.py:423`; `cli/model.py:1465–1468`), the
  `pdf_shape_guard_sql` with no caller (`semantic/pdf_contracts.py:578`) and the migration
  location (`migrations.py:14`).
- The remaining "Stands" rows I checked hold: DA-068 (with the N29 correction), DA-070, DA-074
  (with the count correction in §5) and DA-083.

## 3. Older identities (sample of 21)

Removal commits confirmed by `git log --diff-filter=D` for DA-015 (`9268b15bf`), DA-016
(`a49758618`), DA-017 (`8b7b369a9`), DA-024 (`47dc7b873`), DA-035 (`bcff594c2`), DA-036
(`957ff2231`) and DA-037 (`7fc25ca02`). All match.

| Id | Draft | Verdict | Evidence |
|---|---|---|---|
| 029 | Corrected | Holds | `target_installation.py:351–369` generates from `immutability` |
| 030 | Corrected | Holds | `closure_native.py:172–187` purpose case with unknown-purpose raise |
| 060 | Corrected | Holds | `cli/operations.py:410–415`; `cli/managed.py:92–97` |
| 061 | Corrected | Holds | `ingest/pdf_hierarchy.py:346–351` refuses on differing recipe |
| 062 | Corrected | Holds | `source_value_native.py:60–66` |
| 063 | Corrected | Holds | `execution_admission.py:55–59` |
| 064 | Corrected | Holds | `semantic/visual_routing.py:235–239` |
| 015, 016, 017, 024, 041 | NLA | Hold for the removed subject (successor not re-audited by me) | removal commits above |
| 036 | NLA | **Overstated note** | the `standing` values are per-population constants (`"native-selected-operation"`, `"private_proposal"`, …; `serve/contribution_facets.py:79, 296`), not a per-fact selection status; whether successor fact reads distinguish rejected, ambiguous or deselected was not examined |
| 052 | NLA | Holds, note wrong | see DA-080 (1): `producer.py` has a test importer |
| 028 | Changed footprint | **Holds** | `orchestrate/source_operation.py:160–164` reads live `slices.yaml`; `:52–58` matches by `name` only; `regeneration.py:110–118` archives `operation/slices.yaml`; no reader of that name (grep of `"operation/` readers) |
| 040 | Partly corrected | Holds with wording | the d78 hand body `sql/identity.sql:8–26` was already unbounded and the generator transcribed it faithfully (`data_operation_value_native.py:112–149`). "Recurs" should read "persists, transcribed into the generated program"; the committed status was "Not re-examined" |
| 001 | Changed footprint | Holds | `comparison_projection.py:66–84` `partition` has no caller; `rich_rules.py:60` stores only (dynamic access not excluded) |
| 004 | Changed footprint | Holds | 36 `.get("cs:…")` sites in `semantic/` and `serve/` (my grep); `rich_scientific.py:210–211` |
| 020 | Changed footprint | Holds | six fields (`settings.py:129–139`) with no `analytics.<field>` reader; only `adbc_driver_path` and `batch_size_hint_bytes` are read |
| 065 | Possibly regressed | **Settle as changed footprint, not regression** | see below |

**DA-065, settled as far as static reading allows.** The type never required the witness: at
the enforcing commit `9e04d04d1` the Pydantic model already had `witness: … | None = None` with
the same one-way check, and the refusal "definition basis lacks exact retained annotation
witness" lived only in `sql/structural_products.sql`. The production producer always attaches
one. The only production caller of `components_from_named_matches` and
`components_from_following_display` passes a `witnesses` dict, never `None`
(`semantic/definition_component_products.py:519–573`). With a dict, `qualified` requires
`match in witnesses` (`methods/definition_applicability.py:466, 572–576`), so `matched_cue` or
`native_geometry` without a witness is reachable only through the test-only default.
Admission verifies the output against the attested producer: the published output must equal
the CPU reply bound to the exact input-basis digest and the producer fence
(`definition_admission_native.py:386–400`; `data_operation_cpu_basis.py:1095–1150`). **The
unwitnessed scenario is therefore not reachable through production admission today. What was
lost is independent native verification of the witness against retained annotations.** The
guarantee now rests on producer attestation (CI-01 weakened, not breached). The residue is
low-weight: the type binds `declaration_chain` to its witness both ways (`structural_products.py:956–964`)
but `matched_cue` and `native_geometry` one way only. Status: **changed footprint (assurance
moved to producer attestation)**.

## 4. Rebuilt tables

**Fact ownership (12 rows checked).**

| Row | Verdict |
|---|---|
| Field type / kind universe (`physical.yaml:71`; `data_operation_compilation.py:341`; `native_definition_projection.py:23`; `support_trust_native.py:91`) | Holds |
| Role collection semantics (`characterization_ports.py:746–749`) | Holds |
| Prepared-factory entry point | Holds; the cited `data_operation_model.py:288–296` is `ImplementationCapabilities`, so name that class |
| Operation constants in owner modules | Holds with correction: only `operation_event.authorize` has an owner constant; `frame` and `fit` have none, so "inline ids beside the owner-module constants that carry them" (`operation_event_native.py:295, 315`) should read "inline ids; only the authorize id has an owner constant" |
| Product member families (`data_product_admission_native.py:56–90`) | Holds |
| Public disclosure (`physical.yaml:629`) | Holds; the reader is better cited at `data_read_boundary_native.py:31–34, 103` than `data_operation_projections.py:84–89` |
| Frontier-guard membership (`data_operation_storage.py:1952–1965`, twelve names) | Holds |
| Shared-stream membership (`physical.yaml:1757, 1776`; `target_installation.py:371`) | Holds |
| Role names (199 in 47 files) | Count holds; the "changed" mark needs the §5 caveat |
| Purpose-to-role map (`data_operation_storage.py:1899–1907`; `closure_native.py:174–181`) | Holds |
| Table read grants (84 of 84 `'[]'`; `alembic_privileges.py:74–75`; `native_admission_tables.py:176–184`; `native_admission_functions.py:149`) | Holds |
| Which code determines an artifact (`native_products.py`, 28 names) | Holds. "Derivable from: none for generators" should add that this list is also digested into the deployed execution-contract descriptor (item d) |

Missing row: **"Native effect per family operation"**. It is declared for four families (§1b),
read by two guards, and not used for the family lists.

**Identity inventory (8 rows checked).** Rows 1 (count holds), 4 (`data_operation_storage.py:1080–1081`
holds), 13 (renderer list holds), 16, 19, 20 and 24 hold as cited. Row 22 is incomplete: it
should name the execution-contract descriptor's `authoring/*` digests (48 entries; four changed
at N29), or a 30th row should be added. The bullet "one edit can move several identities at
once, as the edit behind native revision N29 did" should say there were two edits, one for
each provenance digest.

**Cache inventory (8 rows checked).** `SELECTED_QUERY_CACHE` (cachetools 7.2.7 pinned,
`pyproject.toml:65`; `LRUCache` at `selected_query_cache.py:58–62`), companion projection
(`companion_projection.py:560, 619`; holds, and its "metadata by object identity" is correctly
noted, though "content-keyed" in the mark is half true), `_prepare_release_cached`
(`prepare.py:600`), `_bound_data_operation_calls` (`data_operation_admission.py:108`), CPU
descriptors (`data_operation_cpu.py:188`), `_OPEN_CACHE` (`archive_reader.py:34`), worker
releases (`5c5443d16` removed `_WORKER_REQUEST`; confirmed by the diff) and the repeated-capture
row ("twice per acquisition, three per definition admission", item e). **All hold.**

## 5. Decisions, false positives and omissions

- **Role-name count is an artifact of the conversion (overstated).** The 176 at `d78c98765`
  counted `.py` files only (39 modules, my grep agrees). Those modules also had **70 more
  occurrences in the 16 `.sql` files**, so the total was 246. At `5139eaba3` the total is 199,
  all in `.py` (47 files). Role literals **moved into more Python modules and fell in total**.
  The finding's substance (hand literals, no model declaration) stands; "rose from 176 to 199"
  does not. DA-086's kind-universe count already carries the matching caveat ("made the
  literals visible to search"); DA-074 and the synthesis need it too.
- **ADR-0131 framing.** The ADR's decision governs "physical types and call correspondence"
  (`docs/adr/0131-model-owned-postgresql-programs.md:32–33`), and its consequence clause is
  about "a model field or type change" (`:46`). It does not promise that family or role
  membership comes from the model. The drafts mostly respect this. Keep the synthesis from
  implying the conversion missed an ADR goal: it is a predicted consequence (from the earlier
  refresh) of converting before declaring, not a divergence from ADR-0131.
- **ADR-0092 supports DA-068 and is not cited.** "No broad runtime digest is a recipe fallback"
  (`docs/adr/0092-ddo-operation-authority.md:27`). Each native protocol operation's `behavior`
  is `"ddo-native-v1:" + kernel digest` (`data_operation_storage.py:993`), so its recipe moves
  with any of 99 modules. That is a broad digest acting as a recipe determinant, in tension
  with the ADR (inferred; the ADR's carve-out for "release-bound execution attestation"
  applies to the seal and receipts, not to the recipe).
- **Plan account.** The companion plan's remaining-work sentence (`…retirement.md:463–464`) is
  quoted correctly. The plan also documents N29's purpose (item d), which contradicts
  "existed only for this".
- **Sound work reported as a problem.** None outright. The N29 byte-identity should be listed
  as a sound outcome. The frozen-guard text anchors (`native_admission.py:42–84`) fail closed
  on count ≠ 1 and work on frozen bytes; DA-081 already notes this.
- **Missing structural item introduced or exposed in the range:** the dead `operation_fitting`
  native path, which calls functions absent from the deployed tree and sits inside a captured
  boundary (item a). Nothing else of comparable weight was found in what I read.

## Corrections ready to apply

1. `README.md`, synthesis, "What the conversion achieved": replace "fell from about 2,400 lines
   to about 180" with "fell from about 2,400 lines inside Python modules, plus 1,293 lines in
   16 `.sql` files, to about 180 lines and no `.sql` file".
2. `README.md`, synthesis, "What did not move": replace "and occurrences of role-name literals
   rose from 176 to 199" with "and role-name literals moved from SQL files into Python (199
   occurrences in 47 modules, against 176 in 39 modules plus 70 in `.sql` files at `d78c98765`)".
3. `README.md`, synthesis bullet "The one real correction of this kind": delete it, or replace
   it with "The task guard, already rendered from the declared lifecycle, is now a typed
   program over captured columns; it remains the one place where a declared fact governs a
   kernel check".
4. `README.md`, Identity bullet, and `execution-fit.md` DA-068 status, the "concrete instance"
   bullet and the N28-to-N29 section: replace "existed only to restamp this digest" with
   "changed no generated statement: it restamped the kernel digest (after a renderer edit,
   `477c82762`) and the execution-contract descriptor's authoring-source digests (after
   `1b643e7ed`)". Replace the masking caveat with "substitutions mapped one to one by this
   challenge". Add the authoring list (`native_products.py:54–170`) as a second stamped
   provenance digest, and cite ADR-0092 `:27`.
5. `README.md` status row DA-086, and its page header: "Partly corrected" becomes "Stands
   (wider)"; the note becomes "The task guard was already rendered from the lifecycle; its
   conversion to a typed program belongs to DA-084". Counts: Partly corrected 8, Stands 20.
6. `README.md` status row DA-065, and its page section: "Possibly regressed" becomes "Changed
   footprint"; the note becomes "Independent native witness verification was retired; the
   production producer always attaches a witness and admission checks the attested CPU reply,
   so the scenario is not reachable today". Counts: Changed footprint 9, Possibly regressed
   0. Delete that status word from the legend. Update `CHANGES.md` to match.
7. `boundaries-and-composition.md` DA-084: "The two real items" becomes "The one real item"
   (the TEMP grant). Move the `operation_fitting` paragraph to DA-080 as "Native fitting path
   with no caller, calling `eval.*` functions defined only in `semantic_alembic/`".
   README row DA-084: "two small items remain" becomes "one small item remains".
8. `boundaries-and-composition.md` DA-080, LLM producers: replace "imported by nothing in `src`
   or `tests`" with "`producer.py` is imported only by `tests/ingest/test_managed_recognition.py`;
   `agent_opus.py` by nothing". In the table, "five items added" becomes six.
9. `native-integrity.md` DA-074 and its README row: "role literals moved from SQL into more
   Python modules and rose" becomes "moved from SQL files into more Python modules; the total
   fell from 246 to 199".
10. `semantic-model-and-authority.md` DA-070: in "Contrary evidence", add the policy
    authorization effect selection (`record_policy_completion_native.py:425–441`) and the four
    declared per-family effects. In "early-return guards", reword "A family member that the
    model or a method module declares" as in §1c.
11. `structure-and-invariants.md` DA-040: "recurs in the regenerated canonicalizer" becomes
    "persists: the hand body of `identity.sql` at `d78c98765` was equally unbounded and was
    transcribed".
12. `served-claims.md` and the README row DA-036: replace "served rows carry a standing" with
    "served rows carry a per-population standing label; a per-fact selection status was not
    examined".
13. `domain-model-map.md` fact-ownership table: correct the owner-constant row and the cite for
    the public-disclosure reader, add the "native effect per family operation" row, and add the
    descriptor note to "Which code determines an artifact". `model-and-execution.md`: extend
    identity row 22 (or add row 30) and correct the N29 bullet.

## Not examined

Generator bodies for equivalence beyond the N29 byte-identity; DA-033, 042, 045, 048, 071–073,
075–079, 081, 082 and 085 beyond their status lines; whether `semantic_alembic`'s `eval`
functions still exist in any deployed database; dynamic imports (all "no caller" claims rest
on grep); the analytical delta table; library-roles table; test-side rows; DA-005–011,
018, 021–023, 031, 034, 044, 049, 051, 053, 055–059, 066, 067; the successors of the NLA
subjects; runtime behaviour of any guard (nothing was executed).
